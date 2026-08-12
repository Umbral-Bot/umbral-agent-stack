"""Stage 4 — Push de candidatos promovidos a Notion (idempotente, dry-run first).

Reads items from ~/.cache/rick-discovery/state.sqlite where
``promovido_a_candidato_at IS NOT NULL AND notion_page_id IS NULL`` and
publishes them as new pages in the Notion "Publicaciones" database.

Default mode: dry-run (no HTTP query/create calls, no SQLite mutations).
Use --commit to actually query Notion for idempotency and create pages.

Mapping (canonical, see task 013-E spec, RESUELTO 2026-05-07):

    SQLite                 -> Notion property        (type)
    --------------------------------------------------------
    titulo                 -> Título                 (title)       required
    url_canonica           -> Fuente primaria        (url)         required
    url_canonica           -> idempotency_key        (rich_text)   required (lookup key)
    "linkedin"             -> Canal                  (select)
    publicado_en           -> Fecha publicación      (date, opt)
    "[ref:..|sqlite:..]"   -> Notas                  (rich_text)
    "Idea"                 -> Estado                 (status)
    True                   -> Creado por sistema     (checkbox)

Idempotency: lookup by ``idempotency_key`` exact-match (rich_text equals)
on the data_source. If a hit exists, persist its page_id and skip create.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
DEFAULT_RATE_LIMIT_MS = 350
SAMPLE_LIMIT = 10
RETRY_BACKOFFS_SEC = (1, 2, 4, 8)  # 4 retries
CONSECUTIVE_ERROR_ABORT = 3
CANAL_VALUE = "linkedin"
ESTADO_INICIAL = "Idea"

REQUIRED_PROPS: dict[str, str] = {
    "Título": "title",
    "Fuente primaria": "url",
    "idempotency_key": "rich_text",
    "Canal": "select",
    "Fecha publicación": "date",
    "Notas": "rich_text",
    "Estado": "status",
    "Creado por sistema": "checkbox",
}


class Stage4Error(RuntimeError):
    """Fatal Stage 4 condition (drift, schema mismatch, persistent 429, etc.)."""


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


@dataclass
class Item:
    rowid: int
    url_canonica: str
    referente_nombre: str
    canal: str
    titulo: str | None
    publicado_en: str | None


@dataclass
class RunSummary:
    pending_total: int = 0
    considered: int = 0
    created: int = 0
    skipped_existing: int = 0
    would_create: int = 0
    errored: int = 0
    retries_429: int = 0


@dataclass
class ItemOutcome:
    rowid: int
    url_canonica: str
    titulo: str
    classification: str  # created | skipped_existing | would_create | errored
    notion_page_id: str | None = None
    notion_url: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# SQLite helpers (with idempotent migration)
# ---------------------------------------------------------------------------


def open_sqlite(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise Stage4Error(f"SQLite no existe: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_notion_page_id_column(conn: sqlite3.Connection) -> bool:
    """Idempotently add notion_page_id column + index. Returns True if added."""
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(discovered_items)")}
    added = False
    if "notion_page_id" not in cols:
        conn.execute("ALTER TABLE discovered_items ADD COLUMN notion_page_id TEXT")
        added = True
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_discovered_notion_page "
        "ON discovered_items(notion_page_id)"
    )
    conn.commit()
    return added


def select_pending(conn: sqlite3.Connection, limit: int | None) -> list[Item]:
    sql = """
        SELECT rowid AS rowid,
               url_canonica, referente_nombre, canal, titulo, publicado_en
          FROM discovered_items
         WHERE promovido_a_candidato_at IS NOT NULL
           AND notion_page_id IS NULL
         ORDER BY promovido_a_candidato_at ASC, url_canonica ASC
    """
    if limit is not None:
        sql += f"\n         LIMIT {int(limit)}"
    rows = conn.execute(sql).fetchall()
    return [
        Item(
            rowid=int(r["rowid"]),
            url_canonica=r["url_canonica"],
            referente_nombre=r["referente_nombre"],
            canal=r["canal"],
            titulo=r["titulo"],
            publicado_en=r["publicado_en"],
        )
        for r in rows
    ]


def mark_persisted(conn: sqlite3.Connection, rowid: int, page_id: str) -> None:
    conn.execute(
        "UPDATE discovered_items SET notion_page_id = ? "
        "WHERE rowid = ? AND notion_page_id IS NULL",
        (page_id, rowid),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Notion HTTP client
# ---------------------------------------------------------------------------


@dataclass
class NotionClient:
    token: str
    rate_limit_ms: int = DEFAULT_RATE_LIMIT_MS
    summary_ref: RunSummary | None = None
    _sleep: Callable[[float], None] = field(default=time.sleep, repr=False)
    _opener: Callable[[urllib.request.Request, float], Any] = field(
        default=urllib.request.urlopen, repr=False
    )

    def _headers(self) -> dict[str, str]:
        # Token only in headers; never logged, never repr'd.
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
            "User-Agent": "umbral-stage4-push/1.0",
        }

    def __repr__(self) -> str:  # safety: prevent accidental token leak
        return f"NotionClient(rate_limit_ms={self.rate_limit_ms})"

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        """HTTP with 429 backoff. Path starts with '/v1/...'."""
        url = NOTION_API_BASE + path[len("/v1") :] if path.startswith("/v1/") else NOTION_API_BASE + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url=url, data=data, method=method, headers=self._headers())
        last_err: str | None = None
        for attempt, wait in enumerate((0,) + RETRY_BACKOFFS_SEC):
            if wait:
                self._sleep(wait)
            try:
                resp = self._opener(req, timeout=30)
                payload = resp.read()
                return json.loads(payload.decode("utf-8")) if payload else {}
            except urllib.error.HTTPError as e:
                body_txt = ""
                try:
                    body_txt = e.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    pass
                if e.code == 429:
                    if self.summary_ref is not None and attempt < len(RETRY_BACKOFFS_SEC):
                        self.summary_ref.retries_429 += 1
                    last_err = f"429 retry={attempt}"
                    print(f"[notion] 429 attempt={attempt} backoff_next={RETRY_BACKOFFS_SEC[attempt] if attempt < len(RETRY_BACKOFFS_SEC) else 'abort'}s",
                          file=sys.stderr)
                    continue
                # Non-429 HTTP error: do not retry.
                raise Stage4Error(f"HTTP {e.code} on {method} {path}: {body_txt}")
            except urllib.error.URLError as e:
                raise Stage4Error(f"URL error on {method} {path}: {e}")
        raise Stage4Error(f"persistent 429 on {method} {path}: {last_err}")

    def sleep_rl(self) -> None:
        self._sleep(self.rate_limit_ms / 1000.0)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def fetch_schema(client: NotionClient, data_source_id: str) -> dict[str, str]:
    """GET /v1/data_sources/{id} → {prop_name: type}."""
    payload = client.request("GET", f"/v1/data_sources/{data_source_id}")
    if payload.get("object") != "data_source":
        raise Stage4Error(f"unexpected object kind for data source: {payload.get('object')!r}")
    return {name: prop.get("type") for name, prop in (payload.get("properties") or {}).items()}


def validate_schema(observed: dict[str, str]) -> list[str]:
    """Return list of issues (empty == valid). Each issue is a human string."""
    issues: list[str] = []
    for name, expected_type in REQUIRED_PROPS.items():
        if name not in observed:
            issues.append(f"missing property: {name!r} (expected type={expected_type})")
            continue
        actual = observed[name]
        if actual != expected_type:
            issues.append(
                f"type mismatch for {name!r}: expected {expected_type}, got {actual}"
            )
    return issues


# ---------------------------------------------------------------------------
# Payload + lookup
# ---------------------------------------------------------------------------


def _normalize_publicado_en(raw: str | None) -> str | None:
    """Notion date accepts ISO-8601. Best-effort pass-through; None on failure."""
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    # ISO-8601 fast path
    try:
        iso = s.replace("Z", "+00:00") if s.endswith("Z") else s
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except ValueError:
        pass
    # RFC822 fallback
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(s)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception:
        return None


def build_payload(item: Item, data_source_id: str) -> dict:
    """Return the POST /v1/pages JSON payload for this item."""
    titulo = (item.titulo or "").strip() or "(sin título)"
    notas = f"[ref: {item.referente_nombre} | sqlite: {item.rowid}]"

    properties: dict[str, Any] = {
        "Título": {"title": [{"type": "text", "text": {"content": titulo[:2000]}}]},
        "Fuente primaria": {"url": item.url_canonica},
        "idempotency_key": {
            "rich_text": [{"type": "text", "text": {"content": item.url_canonica[:2000]}}]
        },
        "Canal": {"select": {"name": CANAL_VALUE}},
        "Notas": {"rich_text": [{"type": "text", "text": {"content": notas[:2000]}}]},
        "Estado": {"status": {"name": ESTADO_INICIAL}},
        "Creado por sistema": {"checkbox": True},
    }
    pub_iso = _normalize_publicado_en(item.publicado_en)
    if pub_iso:
        properties["Fecha publicación"] = {"date": {"start": pub_iso}}

    return {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "properties": properties,
    }


def query_existing(
    client: NotionClient, data_source_id: str, url_canonica: str
) -> tuple[str | None, str | None]:
    """Return (page_id, page_url) of an existing page matching idempotency_key,
    or (None, None) if no match.
    """
    body = {
        "filter": {
            "property": "idempotency_key",
            "rich_text": {"equals": url_canonica},
        },
        "page_size": 1,
    }
    payload = client.request(
        "POST", f"/v1/data_sources/{data_source_id}/query", body=body
    )
    results = payload.get("results") or []
    if not results:
        return None, None
    first = results[0]
    return first.get("id"), first.get("url")


def create_page(client: NotionClient, payload: dict) -> tuple[str, str]:
    """POST /v1/pages. Returns (page_id, page_url)."""
    resp = client.request("POST", "/v1/pages", body=payload)
    page_id = resp.get("id")
    if not page_id:
        raise Stage4Error(f"create_page: no id in response: {str(resp)[:200]}")
    return page_id, resp.get("url") or ""


# ---------------------------------------------------------------------------
# Run loop
# ---------------------------------------------------------------------------


def process_items(
    *,
    items: list[Item],
    client: NotionClient | None,
    conn: sqlite3.Connection,
    data_source_id: str,
    commit: bool,
    summary: RunSummary,
) -> list[ItemOutcome]:
    outcomes: list[ItemOutcome] = []
    consecutive_errors = 0
    for idx, item in enumerate(items):
        summary.considered += 1
        titulo_short = ((item.titulo or "").strip())[:60]

        if not commit:
            summary.would_create += 1
            outcomes.append(
                ItemOutcome(
                    rowid=item.rowid,
                    url_canonica=item.url_canonica,
                    titulo=titulo_short,
                    classification="would_create",
                )
            )
            continue

        # commit mode: rate-limit between every HTTP op (after the first)
        try:
            if idx > 0 or True:  # rate-limit before each item's first op too (safe)
                if idx > 0:
                    client.sleep_rl()  # type: ignore[union-attr]
            existing_id, existing_url = query_existing(
                client, data_source_id, item.url_canonica  # type: ignore[arg-type]
            )
            if existing_id:
                mark_persisted(conn, item.rowid, existing_id)
                summary.skipped_existing += 1
                outcomes.append(
                    ItemOutcome(
                        rowid=item.rowid,
                        url_canonica=item.url_canonica,
                        titulo=titulo_short,
                        classification="skipped_existing",
                        notion_page_id=existing_id,
                        notion_url=existing_url,
                    )
                )
                consecutive_errors = 0
                print(f"[stage4] sqlite_id={item.rowid} skipped_existing page_id={existing_id}")
                continue

            client.sleep_rl()  # type: ignore[union-attr]
            payload = build_payload(item, data_source_id)
            page_id, page_url = create_page(client, payload)  # type: ignore[arg-type]
            mark_persisted(conn, item.rowid, page_id)
            summary.created += 1
            outcomes.append(
                ItemOutcome(
                    rowid=item.rowid,
                    url_canonica=item.url_canonica,
                    titulo=titulo_short,
                    classification="created",
                    notion_page_id=page_id,
                    notion_url=page_url,
                )
            )
            consecutive_errors = 0
            print(f"[stage4] sqlite_id={item.rowid} created page_id={page_id}")
        except Stage4Error as e:
            summary.errored += 1
            consecutive_errors += 1
            outcomes.append(
                ItemOutcome(
                    rowid=item.rowid,
                    url_canonica=item.url_canonica,
                    titulo=titulo_short,
                    classification="errored",
                    error=str(e),
                )
            )
            print(f"[stage4] sqlite_id={item.rowid} ERRORED: {e}", file=sys.stderr)
            if consecutive_errors >= CONSECUTIVE_ERROR_ABORT:
                raise Stage4Error(
                    f"abort: {consecutive_errors} consecutive errors "
                    f"(threshold={CONSECUTIVE_ERROR_ABORT})"
                )
    return outcomes


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def build_report(
    *,
    summary: RunSummary,
    outcomes: list[ItemOutcome],
    mode: str,
    database_id: str,
    data_source_id: str,
    schema_observed: list[str],
    schema_valid: bool | None,
    schema_issues: list[str],
    pending_total: int,
    limit: int | None,
    rate_limit_ms: int,
    started_at: str,
    finished_at: str,
) -> dict:
    if mode == "dry-run":
        overall_pass = (
            summary.created == 0
            and summary.skipped_existing == 0
            and summary.errored == 0
            and summary.would_create == summary.considered
        )
    else:
        overall_pass = (
            summary.errored == 0
            and (summary.created + summary.skipped_existing) == summary.considered
            and summary.would_create == 0
        )

    def _sample(kind: str) -> list[dict]:
        out = []
        for o in outcomes:
            if o.classification != kind:
                continue
            d = {
                "sqlite_id": o.rowid,
                "url_canonica": o.url_canonica,
                "titulo": o.titulo,
            }
            if o.notion_page_id:
                d["notion_page_id"] = o.notion_page_id
            if o.notion_url:
                d["notion_url"] = o.notion_url
            if o.error:
                d["error"] = o.error
            out.append(d)
            if len(out) >= SAMPLE_LIMIT:
                break
        return out

    return {
        "overall_pass": overall_pass,
        "run_started_at": started_at,
        "run_finished_at": finished_at,
        "mode": mode,
        "database_id": database_id,
        "data_source_id": data_source_id,
        "schema_observed": sorted(schema_observed),
        "schema_valid": schema_valid,
        "schema_issues": schema_issues,
        "limit": limit,
        "rate_limit_sleep_ms": rate_limit_ms,
        "summary": {
            "pending_total": pending_total,
            "considered": summary.considered,
            "created": summary.created,
            "skipped_existing": summary.skipped_existing,
            "would_create": summary.would_create,
            "errored": summary.errored,
            "retries_429": summary.retries_429,
        },
        "samples": {
            "created": _sample("created"),
            "skipped_existing": _sample("skipped_existing"),
            "would_create": _sample("would_create"),
            "errored": _sample("errored"),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sqlite", type=Path, required=True)
    p.add_argument("--database-id", required=True,
                   help="Notion database id (parent). Used to resolve data_source_id.")
    p.add_argument("--data-source-id", default=None,
                   help="Optional: pre-resolved data_source_id (skips one GET).")
    p.add_argument("--commit", action="store_true",
                   help="Actually call Notion + UPDATE SQLite. Default: dry-run.")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--rate-limit-ms", type=int, default=DEFAULT_RATE_LIMIT_MS)
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args(argv)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_data_source_id(client: NotionClient, database_id: str) -> str:
    payload = client.request("GET", f"/v1/databases/{database_id}")
    sources = payload.get("data_sources") or []
    if not sources:
        raise Stage4Error(f"database {database_id} has no data_sources")
    return sources[0]["id"]


def run(args: argparse.Namespace) -> int:
    started = _now_utc()
    token = os.environ.get("NOTION_API_KEY", "")
    if args.commit and not token:
        print("ERROR: NOTION_API_KEY not set in environment", file=sys.stderr)
        return 2

    summary = RunSummary()
    # In dry-run we do NOT instantiate a NotionClient (0 HTTP calls).
    # In commit we always need it.
    client = (
        NotionClient(token=token, rate_limit_ms=args.rate_limit_ms, summary_ref=summary)
        if args.commit
        else None
    )

    conn = open_sqlite(args.sqlite)
    try:
        added = ensure_notion_page_id_column(conn)
        if added:
            print("[stage4] migration: added notion_page_id column")

        items = select_pending(conn, args.limit)
        # Count total pending (irrespective of limit) for reporting.
        pending_total = conn.execute(
            "SELECT COUNT(*) FROM discovered_items "
            "WHERE promovido_a_candidato_at IS NOT NULL AND notion_page_id IS NULL"
        ).fetchone()[0]

        # Schema fetch + validation runs only in commit mode.
        # Dry-run: 0 HTTP calls; --data-source-id is required.
        schema_observed: dict[str, str] = {}
        schema_issues: list[str] = []
        schema_valid: bool | None = None
        data_source_id = args.data_source_id or ""
        if args.commit:
            assert client is not None
            if not data_source_id:
                data_source_id = resolve_data_source_id(client, args.database_id)
                client.sleep_rl()
            schema_observed = fetch_schema(client, data_source_id)
            schema_issues = validate_schema(schema_observed)
            schema_valid = not schema_issues
            if not schema_valid:
                raise Stage4Error("schema validation failed: " + "; ".join(schema_issues))
        else:
            if not data_source_id:
                raise Stage4Error(
                    "dry-run requires --data-source-id (no Notion calls allowed)"
                )
            schema_valid = None
            schema_issues = ["schema fetch skipped in dry-run (0 HTTP calls)"]

        mode = "commit" if args.commit else "dry-run"
        outcomes = process_items(
            items=items,
            client=client,
            conn=conn,
            data_source_id=data_source_id,
            commit=args.commit,
            summary=summary,
        )

        finished = _now_utc()
        report = build_report(
            summary=summary,
            outcomes=outcomes,
            mode=mode,
            database_id=args.database_id,
            data_source_id=data_source_id,
            schema_observed=list(schema_observed.keys()),
            schema_valid=schema_valid,
            schema_issues=schema_issues,
            pending_total=pending_total,
            limit=args.limit,
            rate_limit_ms=args.rate_limit_ms,
            started_at=_iso(started),
            finished_at=_iso(finished),
        )
    finally:
        conn.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {args.output}")
    s = report["summary"]
    print(
        f"mode={mode} pending={s['pending_total']} considered={s['considered']} "
        f"created={s['created']} skipped_existing={s['skipped_existing']} "
        f"would_create={s['would_create']} errored={s['errored']} "
        f"retries_429={s['retries_429']} overall_pass={report['overall_pass']}"
    )
    return 0 if report["overall_pass"] else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        return run(args)
    except Stage4Error as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
