#!/usr/bin/env python3
"""Stage 4: push promoted candidatos to Notion DB '📰 Publicaciones de Referentes'.

Default: dry-run (no HTTP /pages calls). Use ``--commit`` (and optionally
``--limit``) to actually create pages. Idempotent via the
``idempotency_key`` rich_text property (= SQLite ``url_canonica``).

Replaces 013-E targeting of the old 'Publicaciones' DB. New schema (013-F):

  Título (title)              ← discovered_items.titulo (or url_canonica)
  Enlace (url)                ← discovered_items.url_canonica
  Canal (select)              ← real value from discovered_items.canal,
                                mapped to one of {youtube, linkedin, x, blog,
                                podcast, newsletter, otro}.
  Referente (relation)        ← lookup by name in Referentes data_source
                                (cache built once at startup).
  Fecha publicación (date)    ← discovered_items.publicado_en (best-effort ISO).
  Estado revisión (select)    ← "Sin revisar" (constant).
  Sqlite ID (number)          ← discovered_items.rowid.
  Creado por sistema (cb)     ← True.
  idempotency_key (rich_text) ← discovered_items.url_canonica.

Body: contenido_html → markdown → Notion blocks (paragraph/heading/list/image),
truncated to 90 blocks. On conversion failure, a single 'created_no_body'
paragraph is used.

Token only in headers; never logged.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from scripts.discovery.html_to_notion_blocks import (
    fallback_no_body_block,
    html_to_notion_blocks,
)
from scripts.discovery.stage2_ingest import get_runtime_notion_api_key

NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2025-09-03"
RATE_LIMIT_SLEEP_S = 0.35
MAX_429_RETRIES = 4
MAX_CONSECUTIVE_NON_429_ERRORS = 3
DEFAULT_SQLITE_PATH = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_REPORTS_DIR = Path("reports")

CANAL_VALID = {"youtube", "linkedin", "x", "blog", "podcast", "newsletter", "otro"}
# Map raw stage2 canal codes (rss, web_rss, youtube, linkedin, otros, ...)
# to the Notion select options for this DB.
CANAL_MAP = {
    "youtube": "youtube",
    "linkedin": "linkedin",
    "x": "x",
    "twitter": "x",
    "blog": "blog",
    "rss": "blog",
    "web_rss": "blog",
    "podcast": "podcast",
    "newsletter": "newsletter",
    "otros": "otro",
    "otro": "otro",
}


# ---------- Models ----------

@dataclass
class ItemOutcome:
    sqlite_id: int
    url_canonica: str
    status: str  # would_create | created | already_present | created_no_body | updated | error
    notion_page_id: str | None = None
    error: str | None = None
    blocks_count: int = 0
    deleted_blocks: int = 0
    appended_blocks: int = 0


@dataclass
class RunSummary:
    started: str
    finished: str | None = None
    commit: bool = False
    dry_run: bool = True
    database_id: str | None = None
    data_source_id: str | None = None
    pending_total: int = 0
    processed: int = 0
    would_create: int = 0
    created: int = 0
    already_present: int = 0
    created_no_body: int = 0
    updated: int = 0
    errors: int = 0
    items: list[ItemOutcome] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


# ---------- Notion HTTP client ----------

class NotionClient:
    def __init__(self, api_key: str, *, base_url: str = NOTION_BASE_URL,
                 api_version: str = NOTION_API_VERSION,
                 client: httpx.Client | None = None):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": api_version,
            "Content-Type": "application/json",
        }
        self._client = client or httpx.Client(timeout=30.0)

    def __repr__(self) -> str:  # noqa: D401
        return f"<NotionClient base={self._base_url!r} token=***REDACTED***>"

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self._base_url}{path}"
        # Strip any caller-provided Authorization to guarantee header-only token.
        kwargs.pop("headers", None)
        delay = 1.0
        for attempt in range(MAX_429_RETRIES + 1):
            r = self._client.request(method, url, headers=self._headers, **kwargs)
            if r.status_code != 429:
                return r
            if attempt >= MAX_429_RETRIES:
                return r
            time.sleep(delay)
            delay *= 2
        return r  # unreachable

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, json_body: Any) -> httpx.Response:
        return self._request("POST", path, json=json_body)

    def patch(self, path: str, json_body: Any) -> httpx.Response:
        return self._request("PATCH", path, json=json_body)

    def delete(self, path: str) -> httpx.Response:
        return self._request("DELETE", path)


# ---------- Schema validation ----------

EXPECTED_PROPS = {
    "Título": "title",
    "Enlace": "url",
    "Canal": "select",
    "Referente": "relation",
    "Fecha publicación": "date",
    "Estado revisión": "select",
    "Sqlite ID": "number",
    "Creado por sistema": "checkbox",
    "idempotency_key": "rich_text",
}


def fetch_data_source(client: NotionClient, data_source_id: str) -> dict[str, Any]:
    r = client.get(f"/data_sources/{data_source_id}")
    if r.status_code != 200:
        raise RuntimeError(f"data_source GET failed: HTTP {r.status_code} body={r.text[:300]}")
    return r.json()


def validate_schema(ds: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    props = ds.get("properties", {})
    for name, expected_type in EXPECTED_PROPS.items():
        prop = props.get(name)
        if prop is None:
            issues.append(f"missing_property:{name}")
            continue
        if prop.get("type") != expected_type:
            issues.append(f"wrong_type:{name}:expected={expected_type}:got={prop.get('type')}")
    return issues


# ---------- Referentes lookup ----------

def build_referentes_index(client: NotionClient, data_source_id: str) -> dict[str, str]:
    """Return mapping referente_nombre (lowercase) -> page_id."""
    index: dict[str, str] = {}
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = client.post(f"/data_sources/{data_source_id}/query", body)
        if r.status_code != 200:
            raise RuntimeError(
                f"referentes query failed: HTTP {r.status_code} body={r.text[:300]}"
            )
        time.sleep(RATE_LIMIT_SLEEP_S)
        data = r.json()
        for page in data.get("results", []):
            pid = page.get("id")
            props = page.get("properties", {})
            name = _extract_title(props)
            if pid and name:
                index[name.strip().lower()] = pid
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return index


def _extract_title(props: dict[str, Any]) -> str | None:
    for name, prop in props.items():
        if prop.get("type") == "title":
            parts = prop.get("title", [])
            return "".join(p.get("plain_text", "") for p in parts) or None
    return None


# ---------- SQLite ----------

SCHEMA_DDL_NOTION_PAGE_ID = """
CREATE INDEX IF NOT EXISTS idx_discovered_notion_page
ON discovered_items(notion_page_id);
"""


def ensure_notion_page_id_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add ``notion_page_id`` column if missing.

    Also ensures the Stage-2 content columns exist so stage4 can read pre-existing
    DBs that pre-date the 013-F schema bump.
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info(discovered_items)")}
    if "notion_page_id" not in cols:
        conn.execute("ALTER TABLE discovered_items ADD COLUMN notion_page_id TEXT")
    if "contenido_html" not in cols:
        conn.execute("ALTER TABLE discovered_items ADD COLUMN contenido_html TEXT")
    if "contenido_extraido_at" not in cols:
        conn.execute("ALTER TABLE discovered_items ADD COLUMN contenido_extraido_at TEXT")
    conn.executescript(SCHEMA_DDL_NOTION_PAGE_ID)
    conn.commit()


def select_pending(
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
    include_existing: bool = False,
) -> list[dict[str, Any]]:
    """Promoted items pending push. With ``include_existing`` (used by
    ``--update-existing``) also returns items already linked to a Notion page.
    """
    sql = (
        "SELECT rowid, url_canonica, referente_id, referente_nombre, canal, titulo, "
        "       publicado_en, contenido_html, notion_page_id "
        "FROM discovered_items "
        "WHERE promovido_a_candidato_at IS NOT NULL"
    )
    if not include_existing:
        sql += " AND notion_page_id IS NULL"
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    cur = conn.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def mark_persisted(conn: sqlite3.Connection, sqlite_id: int, notion_page_id: str) -> None:
    conn.execute(
        "UPDATE discovered_items SET notion_page_id = ? WHERE rowid = ?",
        (notion_page_id, sqlite_id),
    )
    conn.commit()


# ---------- Payload ----------

def _normalize_canal(raw: str | None) -> str:
    if not raw:
        return "otro"
    key = raw.strip().lower()
    return CANAL_MAP.get(key, "otro")


def _normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    # Try ISO first.
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except ValueError:
        pass
    # Try RFC 822 (RSS pubDate).
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(raw)
        if dt:
            return dt.date().isoformat()
    except Exception:
        return None
    return None


def build_payload(
    *,
    item: dict[str, Any],
    data_source_id: str,
    referente_page_id: str | None,
    children: list[dict[str, Any]],
) -> dict[str, Any]:
    titulo = (item.get("titulo") or item["url_canonica"]).strip()
    canal = _normalize_canal(item.get("canal"))
    fecha = _normalize_date(item.get("publicado_en"))

    properties: dict[str, Any] = {
        "Título": {"title": [{"type": "text", "text": {"content": titulo[:1900]}}]},
        "Enlace": {"url": item["url_canonica"]},
        "Canal": {"select": {"name": canal}},
        "Estado revisión": {"select": {"name": "Sin revisar"}},
        "Sqlite ID": {"number": int(item["rowid"])},
        "Creado por sistema": {"checkbox": True},
        "idempotency_key": {
            "rich_text": [{"type": "text", "text": {"content": item["url_canonica"][:1900]}}]
        },
    }
    if fecha:
        properties["Fecha publicación"] = {"date": {"start": fecha}}
    if referente_page_id:
        properties["Referente"] = {"relation": [{"id": referente_page_id}]}

    payload: dict[str, Any] = {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "properties": properties,
    }
    if children:
        payload["children"] = children
    return payload


# ---------- Idempotency ----------

def query_existing(client: NotionClient, *, data_source_id: str,
                    url_canonica: str) -> str | None:
    body = {
        "filter": {
            "property": "idempotency_key",
            "rich_text": {"equals": url_canonica},
        },
        "page_size": 1,
    }
    r = client.post(f"/data_sources/{data_source_id}/query", body)
    if r.status_code != 200:
        raise RuntimeError(
            f"idempotency query failed: HTTP {r.status_code} body={r.text[:300]}"
        )
    data = r.json()
    results = data.get("results") or []
    return results[0].get("id") if results else None


def create_page(client: NotionClient, payload: dict[str, Any]) -> dict[str, Any]:
    r = client.post("/pages", payload)
    if r.status_code >= 400:
        raise RuntimeError(f"create_page HTTP {r.status_code}: {r.text[:500]}")
    return r.json()


def update_existing_page(
    client: NotionClient,
    *,
    page_id: str,
    payload: dict[str, Any],
) -> tuple[int, int]:
    """Update title + replace body of an existing Notion page.
    Returns ``(deleted, appended)``. Sleeps RATE_LIMIT_SLEEP_S between calls.
    """
    def _check(r: httpx.Response, what: str) -> httpx.Response:
        if r.status_code >= 400:
            raise RuntimeError(f"{what} HTTP {r.status_code}: {r.text[:500]}")
        time.sleep(RATE_LIMIT_SLEEP_S)
        return r

    props = payload.get("properties") or {}
    if props:
        _check(client.patch(f"/pages/{page_id}", {"properties": props}), "patch_page")
    deleted = 0
    cursor: str | None = None
    while True:
        path = f"/blocks/{page_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        data = _check(client.get(path), "get_children").json()
        for block in data.get("results", []):
            bid = block.get("id")
            if not bid:
                continue
            _check(client.delete(f"/blocks/{bid}"), "delete_block")
            deleted += 1
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    children = payload.get("children") or [fallback_no_body_block()]
    appended = 0
    for i in range(0, len(children), 100):
        chunk = children[i:i + 100]
        _check(client.patch(f"/blocks/{page_id}/children", {"children": chunk}),
               "append_children")
        appended += len(chunk)
    return deleted, appended


# ---------- Orchestration ----------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def process_items(
    *,
    client: NotionClient,
    conn: sqlite3.Connection,
    items: list[dict[str, Any]],
    data_source_id: str,
    referentes_index: dict[str, str],
    commit: bool,
    update_existing: bool = False,
) -> RunSummary:
    summary = RunSummary(
        started=_now_iso(),
        commit=commit,
        dry_run=not commit,
        data_source_id=data_source_id,
        pending_total=len(items),
    )
    consecutive_errors = 0

    for item in items:
        outcome = ItemOutcome(
            sqlite_id=item["rowid"],
            url_canonica=item["url_canonica"],
            status="would_create",
        )
        try:
            referente_page_id = referentes_index.get(
                (item.get("referente_nombre") or "").strip().lower()
            )

            # Body conversion (always done; cheap, helps dry-run telemetry).
            try:
                children = html_to_notion_blocks(item.get("contenido_html"))
                if not children:
                    children = [fallback_no_body_block()]
                    body_status_no_body = True
                else:
                    body_status_no_body = False
            except Exception:
                children = [fallback_no_body_block()]
                body_status_no_body = True
            outcome.blocks_count = len(children)

            payload = build_payload(
                item=item,
                data_source_id=data_source_id,
                referente_page_id=referente_page_id,
                children=children,
            )

            if not commit:
                outcome.status = "would_create"
                summary.would_create += 1
            else:
                # Idempotency check.
                existing_id = query_existing(
                    client, data_source_id=data_source_id,
                    url_canonica=item["url_canonica"],
                )
                time.sleep(RATE_LIMIT_SLEEP_S)
                if existing_id:
                    if update_existing:
                        deleted, appended = update_existing_page(
                            client, page_id=existing_id, payload=payload,
                        )
                        outcome.status = "updated"
                        outcome.notion_page_id = existing_id
                        outcome.deleted_blocks = deleted
                        outcome.appended_blocks = appended
                        summary.updated += 1
                        mark_persisted(conn, item["rowid"], existing_id)
                        print(f"updated sid={item['rowid']} deleted={deleted} appended={appended}", flush=True)
                    else:
                        outcome.status = "already_present"
                        outcome.notion_page_id = existing_id
                        summary.already_present += 1
                        mark_persisted(conn, item["rowid"], existing_id)
                else:
                    page = create_page(client, payload)
                    page_id = page.get("id")
                    outcome.notion_page_id = page_id
                    if body_status_no_body:
                        outcome.status = "created_no_body"
                        summary.created_no_body += 1
                    else:
                        outcome.status = "created"
                        summary.created += 1
                    if page_id:
                        mark_persisted(conn, item["rowid"], page_id)
                    time.sleep(RATE_LIMIT_SLEEP_S)
            consecutive_errors = 0
        except Exception as exc:
            outcome.status = "error"
            outcome.error = f"{exc.__class__.__name__}: {exc}"[:500]
            summary.errors += 1
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_NON_429_ERRORS:
                summary.items.append(outcome)
                summary.processed += 1
                summary.finished = _now_iso()
                summary.errors = summary.errors  # keep for clarity
                # Append abort marker as a synthetic outcome to be visible in report.
                summary.items.append(ItemOutcome(
                    sqlite_id=-1, url_canonica="<aborted>", status="aborted",
                    error=f"aborted_after_{consecutive_errors}_consecutive_errors",
                ))
                return summary
        summary.items.append(outcome)
        summary.processed += 1

    summary.finished = _now_iso()
    return summary


def write_report(reports_dir: Path, summary: RunSummary, *, suffix: str) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"stage4-push-{_now_ts()}-{suffix}.json"
    path.write_text(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False))
    return path


# ---------- CLI ----------

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Push promoted candidatos to Notion (013-F).")
    p.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE_PATH)
    p.add_argument("--database-id", required=True,
                   help="Notion database id (sanity, not used for POST).")
    p.add_argument("--data-source-id", required=True,
                   help="Notion data_source id used as parent for new pages.")
    p.add_argument("--referentes-data-source-id", required=True,
                   help="Notion data_source id of the Referentes DB used to resolve relations.")
    p.add_argument("--commit", action="store_true",
                   help="Actually create pages (default: dry-run, no /pages calls).")
    p.add_argument("--update-existing", action="store_true",
                   help="Opt-in: when item is already_present, PATCH title + replace blocks. Default OFF.")
    p.add_argument("--limit", type=int, default=None,
                   help="Max items to process this run.")
    p.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    api_key = get_runtime_notion_api_key()

    conn = sqlite3.connect(str(args.sqlite))
    ensure_notion_page_id_column(conn)
    items = select_pending(conn, limit=args.limit,
                           include_existing=args.update_existing)

    client = NotionClient(api_key)
    try:
        ds = fetch_data_source(client, args.data_source_id)
        issues = validate_schema(ds)
        if issues:
            err = {
                "status": "schema_mismatch",
                "data_source_id": args.data_source_id,
                "issues": issues,
            }
            print(json.dumps(err, indent=2))
            return 2
        referentes_index = build_referentes_index(client, args.referentes_data_source_id)
        summary = process_items(
            client=client, conn=conn, items=items,
            data_source_id=args.data_source_id,
            referentes_index=referentes_index,
            commit=args.commit,
            update_existing=args.update_existing,
        )
        summary.database_id = args.database_id
    finally:
        client.close()

    suffix = "commit" if args.commit else "dryrun"
    if args.commit and args.limit:
        suffix = f"commit{args.limit}"
    report_path = write_report(args.reports_dir, summary, suffix=suffix)
    print(json.dumps({"report": str(report_path), **summary.to_dict()}, indent=2,
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
