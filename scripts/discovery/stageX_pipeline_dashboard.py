"""Stage X — Pipeline Editorial dashboard for Notion Control Room.

Reads ``~/.cache/rick-discovery/state.sqlite`` (table ``proposals``) and renders
a metrics summary into a dedicated subpage of the Notion Control Room page.

Idempotent by design: lookup by subpage title; create on first run, update
in-place thereafter (existing children are archived and replaced).

Usage:
    python scripts/discovery/stageX_pipeline_dashboard.py [--dry-run] [--state-db PATH]
                                                          [--cron-log PATH]
                                                          [--control-room-id ID]
                                                          [--subpage-title TITLE]

Failure here MUST NOT abort the rest of the discovery cron pipeline. Wrap with
``|| true`` (or run via ``set +e``) when wiring it.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_STATE_DB = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_CRON_LOG = Path("/tmp/discovery_publish.log")
DEFAULT_CONTROL_ROOM_ID = "30c5f443fb5c80eeb721dc5727b20dca"
DEFAULT_SUBPAGE_TITLE = "📊 Pipeline Editorial — Métricas"

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
RATE_LIMIT_SLEEP_S = 0.34  # ~3 req/s
LOG_TS_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\]")

# Schedule the cron fires at: minute 15 every 6h UTC → 00:15, 06:15, 12:15, 18:15
CRON_HOURS = (0, 6, 12, 18)
CRON_MINUTE = 15


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class CopyReviewRow:
    id: int
    titular: str
    notion_page_url: str
    copy_len: int
    copy_model_used: str
    copy_last_attempt_at: str
    copy_cost_usd_estimate: float


@dataclass
class CopyReviewPending:
    """Stage 7.5 review queue: pages with copy_status='copy_ready' awaiting
    David's authorisation (linkedin_status still NULL)."""
    available: bool = False
    rows: list[CopyReviewRow] = field(default_factory=list)
    total_cost_usd: float = 0.0


@dataclass
class Metrics:
    total: int = 0
    status: dict[str, int] = field(default_factory=dict)
    image_status: dict[str, int] = field(default_factory=dict)
    linkedin_status: dict[str, int] = field(default_factory=dict)
    last_24h_proposals: int = 0
    last_24h_notion_pages: int = 0
    last_24h_linkedin: int = 0
    cron_last_run: str | None = None
    cron_next_run: str | None = None
    has_linkedin_column: bool = False
    copy_review_pending: CopyReviewPending = field(default_factory=CopyReviewPending)
    generated_at: str = ""


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _bucket(value: Any) -> str:
    if value is None:
        return "(null)"
    s = str(value).strip()
    return s if s else "(empty)"


def collect_metrics(
    db_path: Path,
    *,
    cron_log_path: Path = DEFAULT_CRON_LOG,
    now: datetime | None = None,
) -> Metrics:
    """Collect dashboard metrics from the discovery state DB."""
    now = now or datetime.now(timezone.utc)
    m = Metrics(generated_at=now.isoformat(timespec="seconds"))

    conn = sqlite3.connect(str(db_path))
    try:
        cols = _column_names(conn, "proposals")
        m.has_linkedin_column = "linkedin_status" in cols

        m.total = conn.execute("SELECT COUNT(*) FROM proposals").fetchone()[0]

        for value, count in conn.execute(
            "SELECT status, COUNT(*) FROM proposals GROUP BY status"
        ):
            m.status[_bucket(value)] = count

        if "image_status" in cols:
            for value, count in conn.execute(
                "SELECT image_status, COUNT(*) FROM proposals GROUP BY image_status"
            ):
                m.image_status[_bucket(value)] = count

        if m.has_linkedin_column:
            for value, count in conn.execute(
                "SELECT linkedin_status, COUNT(*) FROM proposals GROUP BY linkedin_status"
            ):
                m.linkedin_status[_bucket(value)] = count

        cutoff_epoch = int((now - timedelta(hours=24)).timestamp())
        m.last_24h_proposals = conn.execute(
            "SELECT COUNT(*) FROM proposals WHERE ts >= ?", (cutoff_epoch,)
        ).fetchone()[0]
        m.last_24h_notion_pages = conn.execute(
            "SELECT COUNT(*) FROM proposals "
            "WHERE notion_page_id IS NOT NULL AND ts >= ?",
            (cutoff_epoch,),
        ).fetchone()[0]
        if m.has_linkedin_column:
            m.last_24h_linkedin = conn.execute(
                "SELECT COUNT(*) FROM proposals "
                "WHERE linkedin_status IN ('published','draft_ready') "
                "AND ts >= ?",
                (cutoff_epoch,),
            ).fetchone()[0]
    finally:
        conn.close()

    last_ts = parse_last_cron_run(cron_log_path)
    if last_ts is not None:
        m.cron_last_run = last_ts.isoformat(timespec="seconds")
    next_ts = compute_next_cron_run(now)
    m.cron_next_run = next_ts.isoformat(timespec="seconds")

    m.copy_review_pending = collect_copy_review_pending(db_path)

    return m


# ---------------------------------------------------------------------------
# Stage 7.5 — Copy review pending tab
# ---------------------------------------------------------------------------

# Columns required to render the "Copy review pending" tab. If any are missing
# in the proposals table the dashboard shows a placeholder note instead of
# failing — Stage 7.5 (Hilo A) owns the migration that adds these columns.
COPY_REVIEW_COLUMNS = (
    "copy_status",
    "copy_model_used",
    "copy_last_attempt_at",
    "copy_cost_usd_estimate",
)


def _fmt_attempt_at(value: Any) -> str:
    """Render copy_last_attempt_at — accepts epoch seconds or ISO strings."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat(
                timespec="seconds"
            )
        except (OverflowError, OSError, ValueError):
            return str(value)
    return str(value)


def _build_page_url(notion_page_id: str) -> str:
    """Return a usable Notion URL for the page id (dashes optional)."""
    pid = (notion_page_id or "").replace("-", "")
    return f"https://www.notion.so/{pid}" if pid else ""


def collect_copy_review_pending(db_path: Path) -> CopyReviewPending:
    """Query proposals for rows ready for David's copy review.

    Returns ``available=False`` when the Stage 7.5 columns are not present
    yet. This is the expected state until Hilo A lands its migration.
    """
    out = CopyReviewPending()
    conn = sqlite3.connect(str(db_path))
    try:
        cols = _column_names(conn, "proposals")
        if not all(c in cols for c in COPY_REVIEW_COLUMNS):
            return out
        out.available = True
        # ``linkedin_status`` may not exist either; coalesce defensively.
        linkedin_clause = (
            "AND COALESCE(linkedin_status, '') = '' "
            if "linkedin_status" in cols
            else ""
        )
        sql_base = (
            "SELECT id, titular, notion_page_id, "
            "       COALESCE(copy_model_used, '') AS copy_model_used, "
            "       COALESCE(copy_last_attempt_at, '') AS copy_last_attempt_at, "
            "       COALESCE(copy_cost_usd_estimate, 0.0) AS copy_cost_usd_estimate, "
            "       {copy_len_expr} AS copy_len_inline "
            "FROM proposals "
            "WHERE notion_page_id IS NOT NULL "
            "  AND COALESCE(copy_status, '') = 'copy_ready' "
            "  {linkedin_clause}"
            "ORDER BY id ASC"
        )
        copy_len_expr = "0"
        for candidate in ("copy_text", "copy_linkedin"):
            if candidate in cols:
                copy_len_expr = f"COALESCE(LENGTH({candidate}), 0)"
                break
        sql = sql_base.format(
            copy_len_expr=copy_len_expr, linkedin_clause=linkedin_clause
        )
        for row in conn.execute(sql):
            (rid, tit, page_id, model, attempt_at, cost, copy_len) = row
            out.rows.append(
                CopyReviewRow(
                    id=int(rid),
                    titular=str(tit or ""),
                    notion_page_url=_build_page_url(str(page_id or "")),
                    copy_len=int(copy_len or 0),
                    copy_model_used=str(model or ""),
                    copy_last_attempt_at=_fmt_attempt_at(attempt_at),
                    copy_cost_usd_estimate=float(cost or 0.0),
                )
            )
        out.total_cost_usd = sum(r.copy_cost_usd_estimate for r in out.rows)
    finally:
        conn.close()
    return out


def render_copy_review_markdown(pending: CopyReviewPending) -> str:
    """Render the markdown section for the Copy review pending tab."""
    lines = ["## Copy review pending (Stage 7.5)"]
    if not pending.available:
        lines.append("_(esperando Stage 7.5 core — columnas `copy_*` aún no presentes)_")
        lines.append("")
        return "\n".join(lines)

    n = len(pending.rows)
    lines.append(
        f"_Total esperando revisión: **{n}**_  "
        f"_Costo acumulado USD: **${pending.total_cost_usd:.4f}**_"
    )
    lines.append("")
    if n == 0:
        lines.append("_(sin pages pendientes)_")
        lines.append("")
        return "\n".join(lines)

    lines.append("| ID | Titular | Page | Copy len | Modelo | Último intento |")
    lines.append("| ---: | --- | --- | ---: | --- | --- |")
    for r in pending.rows:
        url_md = f"[abrir]({r.notion_page_url})" if r.notion_page_url else "—"
        titular = (r.titular or "").replace("|", "\\|")
        lines.append(
            f"| {r.id} | {titular} | {url_md} | {r.copy_len} | "
            f"{r.copy_model_used or '—'} | {r.copy_last_attempt_at or '—'} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_copy_review_blocks(pending: CopyReviewPending) -> list[dict[str, Any]]:
    """Render the Copy review pending tab as Notion blocks."""
    blocks: list[dict[str, Any]] = [_heading_2("Copy review pending (Stage 7.5)")]
    if not pending.available:
        blocks.append(
            _paragraph("(esperando Stage 7.5 core — columnas copy_* aún no presentes)")
        )
        return blocks
    n = len(pending.rows)
    blocks.append(
        _paragraph(
            f"Total esperando revisión: {n}  |  "
            f"Costo acumulado USD: ${pending.total_cost_usd:.4f}"
        )
    )
    if n == 0:
        blocks.append(_paragraph("(sin pages pendientes)"))
        return blocks
    headers = ["ID", "Titular", "Page", "Copy len", "Modelo", "Último intento"]
    rows = [
        [
            str(r.id),
            r.titular[:200],
            r.notion_page_url or "—",
            str(r.copy_len),
            r.copy_model_used or "—",
            r.copy_last_attempt_at or "—",
        ]
        for r in pending.rows
    ]
    blocks.append(_table(headers, rows))
    return blocks


def parse_last_cron_run(log_path: Path) -> datetime | None:
    """Best-effort: returns the last UTC timestamp present in the cron log."""
    try:
        # Read last 8 KB only — log can be large.
        with open(log_path, "rb") as f:
            try:
                f.seek(-8192, os.SEEK_END)
            except OSError:
                f.seek(0)
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None

    last: datetime | None = None
    for line in tail.splitlines():
        match = LOG_TS_RE.match(line)
        if not match:
            continue
        try:
            last = datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
    return last


def compute_next_cron_run(now: datetime) -> datetime:
    """Compute next firing of ``15 */6 * * *`` UTC after ``now``."""
    candidates = [
        now.replace(hour=h, minute=CRON_MINUTE, second=0, microsecond=0)
        for h in CRON_HOURS
    ]
    future = [c for c in candidates if c > now]
    if future:
        return future[0]
    # Wrap to next day, first slot.
    tomorrow = (now + timedelta(days=1)).replace(
        hour=CRON_HOURS[0], minute=CRON_MINUTE, second=0, microsecond=0
    )
    return tomorrow


# ---------------------------------------------------------------------------
# Markdown render (used for stdout / debugging; Notion gets structured blocks)
# ---------------------------------------------------------------------------

def render_markdown(m: Metrics) -> str:
    lines = [f"# {DEFAULT_SUBPAGE_TITLE}", "", f"_Total proposals: **{m.total}**_", ""]

    def _table(title: str, data: dict[str, int]) -> None:
        lines.append(f"## {title}")
        if not data:
            lines.append("_(sin datos)_")
            lines.append("")
            return
        lines.append("| Bucket | Count |")
        lines.append("| --- | ---: |")
        for k in sorted(data, key=lambda x: (-data[x], x)):
            lines.append(f"| {k} | {data[k]} |")
        lines.append("")

    _table("status", m.status)
    _table("image_status", m.image_status)
    if m.has_linkedin_column:
        _table("linkedin_status", m.linkedin_status)
    else:
        lines.append("## linkedin_status")
        lines.append("_(columna no presente en schema)_")
        lines.append("")

    lines.append("## Últimas 24 h")
    lines.append("| Métrica | Count |")
    lines.append("| --- | ---: |")
    lines.append(f"| Nuevas proposals | {m.last_24h_proposals} |")
    lines.append(f"| Nuevas pages en Notion | {m.last_24h_notion_pages} |")
    if m.has_linkedin_column:
        lines.append(f"| Nuevos posts LinkedIn | {m.last_24h_linkedin} |")
    lines.append("")

    lines.append("## Cron `15 */6 * * *` UTC")
    lines.append(f"- Última corrida: `{m.cron_last_run or 'desconocida'}`")
    lines.append(f"- Próxima corrida: `{m.cron_next_run}`")
    lines.append("")
    lines.append(render_copy_review_markdown(m.copy_review_pending))
    lines.append(f"_Última actualización: `{m.generated_at}`_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Notion blocks builder
# ---------------------------------------------------------------------------

def _rt(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": text[:2000]}}]


def _heading_2(text: str) -> dict[str, Any]:
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": _rt(text)}}


def _paragraph(text: str) -> dict[str, Any]:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _rt(text)}}


def _table_row(cells: list[str]) -> dict[str, Any]:
    return {"object": "block", "type": "table_row",
            "table_row": {"cells": [_rt(c) for c in cells]}}


def _table(headers: list[str], rows: list[list[str]]) -> dict[str, Any]:
    children = [_table_row(headers)] + [_table_row(r) for r in rows]
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": children,
        },
    }


def build_blocks(m: Metrics) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    blocks.append(_paragraph(f"Total proposals: {m.total}"))

    def _dim(title: str, data: dict[str, int]) -> None:
        blocks.append(_heading_2(title))
        if not data:
            blocks.append(_paragraph("(sin datos)"))
            return
        rows = [[k, str(data[k])] for k in sorted(data, key=lambda x: (-data[x], x))]
        blocks.append(_table(["Bucket", "Count"], rows))

    _dim("status", m.status)
    _dim("image_status", m.image_status)
    if m.has_linkedin_column:
        _dim("linkedin_status", m.linkedin_status)
    else:
        blocks.append(_heading_2("linkedin_status"))
        blocks.append(_paragraph("(columna no presente en schema)"))

    blocks.append(_heading_2("Últimas 24 h"))
    last24_rows = [
        ["Nuevas proposals", str(m.last_24h_proposals)],
        ["Nuevas pages en Notion", str(m.last_24h_notion_pages)],
    ]
    if m.has_linkedin_column:
        last24_rows.append(["Nuevos posts LinkedIn", str(m.last_24h_linkedin)])
    blocks.append(_table(["Métrica", "Count"], last24_rows))

    blocks.append(_heading_2("Cron 15 */6 * * * UTC"))
    blocks.append(_paragraph(f"Última corrida: {m.cron_last_run or 'desconocida'}"))
    blocks.append(_paragraph(f"Próxima corrida: {m.cron_next_run}"))

    blocks.extend(build_copy_review_blocks(m.copy_review_pending))

    blocks.append(_paragraph(f"Última actualización (UTC): {m.generated_at}"))
    return blocks


# ---------------------------------------------------------------------------
# Notion client
# ---------------------------------------------------------------------------

class NotionClient:
    def __init__(self, token: str, *, timeout_s: float = 30.0) -> None:
        if not token:
            raise ValueError("NOTION_API_KEY not set")
        self._client = httpx.Client(
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=timeout_s,
        )

    def __repr__(self) -> str:  # pragma: no cover
        return "NotionClient(token=***)"

    def _sleep(self) -> None:
        time.sleep(RATE_LIMIT_SLEEP_S)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._sleep()
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        self._sleep()
        r = self._client.post(path, json=body)
        r.raise_for_status()
        return r.json()

    def patch(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        self._sleep()
        r = self._client.patch(path, json=body)
        r.raise_for_status()
        return r.json()

    def delete(self, path: str) -> dict[str, Any]:
        self._sleep()
        r = self._client.delete(path)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Subpage lookup / write
# ---------------------------------------------------------------------------

def _child_page_title(block: dict[str, Any]) -> str:
    if block.get("type") != "child_page":
        return ""
    return (block.get("child_page") or {}).get("title", "") or ""


def find_subpage_id(client: NotionClient, parent_page_id: str, title: str) -> str | None:
    """Iterate the parent page's children blocks, return the first child_page
    block id whose title matches ``title`` (case-sensitive). None if absent."""
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        data = client.get(f"/blocks/{parent_page_id}/children", params=params)
        for block in data.get("results", []):
            if _child_page_title(block) == title:
                return block["id"]
        if not data.get("has_more"):
            return None
        cursor = data.get("next_cursor")
        if not cursor:
            return None


def archive_children(client: NotionClient, page_id: str) -> int:
    """Delete (archive) every child block of ``page_id``. Returns count deleted."""
    deleted = 0
    while True:
        data = client.get(f"/blocks/{page_id}/children", params={"page_size": 100})
        results = data.get("results", [])
        if not results:
            return deleted
        for block in results:
            block_id = block.get("id")
            if not block_id:
                continue
            try:
                client.delete(f"/blocks/{block_id}")
                deleted += 1
            except httpx.HTTPStatusError:
                # Some block types cannot be deleted; skip.
                continue
        if not data.get("has_more"):
            return deleted


def append_blocks(
    client: NotionClient, page_id: str, blocks: list[dict[str, Any]]
) -> None:
    """Append blocks in chunks of <=100."""
    for i in range(0, len(blocks), 100):
        chunk = blocks[i : i + 100]
        client.patch(f"/blocks/{page_id}/children", {"children": chunk})


def create_subpage(
    client: NotionClient, parent_page_id: str, title: str
) -> str:
    body = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "properties": {
            "title": {"title": _rt(title)},
        },
    }
    page = client.post("/pages", body)
    return page["id"]


def upsert_dashboard_subpage(
    client: NotionClient,
    parent_page_id: str,
    title: str,
    blocks: list[dict[str, Any]],
) -> tuple[str, str]:
    """Idempotent upsert. Returns (page_id, action) where action ∈ {created, updated}."""
    existing = find_subpage_id(client, parent_page_id, title)
    if existing:
        archive_children(client, existing)
        append_blocks(client, existing, blocks)
        return existing, "updated"
    new_id = create_subpage(client, parent_page_id, title)
    append_blocks(client, new_id, blocks)
    return new_id, "created"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state-db", type=Path, default=DEFAULT_STATE_DB)
    p.add_argument("--cron-log", type=Path, default=DEFAULT_CRON_LOG)
    p.add_argument("--control-room-id", default=DEFAULT_CONTROL_ROOM_ID)
    p.add_argument("--subpage-title", default=DEFAULT_SUBPAGE_TITLE)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute metrics + render markdown but do not touch Notion.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.state_db.exists():
        print(f"ERROR: state DB not found: {args.state_db}", file=sys.stderr)
        return 2

    metrics = collect_metrics(args.state_db, cron_log_path=args.cron_log)
    md = render_markdown(metrics)
    print(md)

    if args.dry_run:
        print("\n[dry-run] Skipping Notion write.", file=sys.stderr)
        return 0

    token = os.environ.get("NOTION_API_KEY", "")
    if not token:
        print("ERROR: NOTION_API_KEY not set", file=sys.stderr)
        return 2

    client = NotionClient(token)
    try:
        page_id, action = upsert_dashboard_subpage(
            client, args.control_room_id, args.subpage_title, build_blocks(metrics)
        )
    finally:
        client.close()

    print(
        f"\n[ok] dashboard {action}: page_id={page_id}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
