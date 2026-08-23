"""
Notion-side snapshot for the Drive->Notion Granola gap-check.

``scripts/list_granola_drive_ingest_gap.py`` needs one JSON record per page
already living in the canonical "Transcripciones Granola" DB. P1.1b built that
snapshot by hand, per batch — fine for a one-shot catch-up, useless for a
feeder that has to run unattended every day. This module is the missing piece:
it pages the whole DB and emits exactly the shape the gap-check consumes.

The per-page parsing is NOT reimplemented here. It delegates to
``worker/tasks/granola.py::_build_existing_raw_candidate`` — the same function
the worker itself uses at execute time to decide what an existing page is — so
the feeder's pre-classification cannot silently disagree with the authority.
Only two display-level fields the worker does not expose are read directly off
the page properties: ``Fuente`` and ``Longitud Notion``.

Pagination is mandatory: the DB crossed 100 pages during P1.1b, and a
single un-paged query would silently under-report existing pages and make the
gap-check propose duplicates. If the walk cannot finish, this raises instead
of writing a partial snapshot.

SAFETY: read-only. This module never writes to Notion.

Examples::

    python scripts/vm/granola_notion_raw_snapshot.py --output notion_pages.json
    python scripts/vm/granola_notion_raw_snapshot.py \\
        --database-id 3265f443-... --output notion_pages.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from worker.tasks.granola import _build_existing_raw_candidate  # noqa: E402

NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"
TIMEOUT = 60.0
PAGE_SIZE = 100
# The DB held 134 pages on 2026-08-23 and grows by a handful a week. This is a
# runaway-loop backstop, not an expected ceiling -- exceeding it raises.
MAX_PAGES = 100


def resolve_notion_config(
    api_key: str | None = None,
    database_id: str | None = None,
) -> tuple[str, str]:
    key = (api_key or os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN") or "").strip()
    if not key:
        raise RuntimeError(
            "NOTION_API_KEY not set. Pass --api-key or set the NOTION_API_KEY env var."
        )
    db = (database_id or os.environ.get("NOTION_GRANOLA_DB_ID") or "").strip()
    if not db:
        raise RuntimeError(
            "NOTION_GRANOLA_DB_ID not set. Pass --database-id or set the "
            "NOTION_GRANOLA_DB_ID env var."
        )
    return key, db


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def _select_name(properties: dict[str, Any], name: str) -> str:
    prop = properties.get(name) or {}
    select = prop.get("select") or {}
    return str(select.get("name") or "")


def _number(properties: dict[str, Any], name: str) -> int:
    prop = properties.get(name) or {}
    value = prop.get("number")
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def build_record(page: dict[str, Any]) -> dict[str, Any]:
    """Map one raw Notion page object onto a gap-check ``notion_records`` item."""
    record = _build_existing_raw_candidate(page)
    properties = page.get("properties") or {}
    record["fuente"] = _select_name(properties, "Fuente") or _select_name(properties, "Source")
    record["longitud_notion"] = _number(properties, "Longitud Notion")
    return record


def fetch_pages(
    api_key: str,
    database_id: str,
    *,
    page_size: int = PAGE_SIZE,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Page the whole DB and return every raw page object.

    Raises if Notion errors out or if the cursor walk exceeds ``MAX_PAGES``
    requests -- a partial snapshot is worse than none, because the gap-check
    would read the missing pages as "not in Notion" and propose duplicates.
    """
    owns_client = client is None
    client = client or httpx.Client(timeout=TIMEOUT)
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    requests_made = 0

    try:
        while True:
            if requests_made >= MAX_PAGES:
                raise RuntimeError(
                    f"Notion pagination exceeded {MAX_PAGES} requests -- refusing to "
                    "write a possibly truncated snapshot."
                )
            body: dict[str, Any] = {"page_size": page_size}
            if cursor:
                body["start_cursor"] = cursor
            resp = client.post(
                f"{NOTION_BASE_URL}/databases/{database_id}/query",
                headers=_headers(api_key),
                json=body,
            )
            requests_made += 1
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Notion API error ({resp.status_code}) during granola raw snapshot: "
                    f"{resp.text[:300]}"
                )
            data = resp.json()
            pages.extend(item for item in data.get("results", []) if isinstance(item, dict))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
    finally:
        if owns_client:
            client.close()

    return pages


def build_snapshot(pages: list[dict[str, Any]]) -> dict[str, Any]:
    records = [build_record(page) for page in pages]
    return {"count": len(records), "records": records}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Snapshot the canonical Granola raw Notion DB for the gap-check (read-only)."
    )
    parser.add_argument("--output", required=True, help="Path to write the snapshot JSON (UTF-8)")
    parser.add_argument("--database-id", dest="database_id", default=None)
    parser.add_argument("--api-key", dest="api_key", default=None)
    parser.add_argument("--page-size", dest="page_size", type=int, default=PAGE_SIZE)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    api_key, database_id = resolve_notion_config(args.api_key, args.database_id)
    pages = fetch_pages(api_key, database_id, page_size=args.page_size)
    snapshot = build_snapshot(pages)
    Path(args.output).write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"count": snapshot["count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
