#!/usr/bin/env python3
"""Re-render selected discovered_items as new Notion pages.

Workflow per ``--sqlite-ids``:
1. Read ``notion_page_id`` for the row.
2. PATCH ``/pages/{id}`` with ``{"archived": true}`` (rate-limited 350ms,
   429 backoff 1/2/4/8s, max 4 retries — same as stage4).
3. On success, ``UPDATE discovered_items SET notion_page_id = NULL`` so a
   subsequent stage4 run will re-create the page from scratch with the
   current rendering pipeline (013-G inline annotations).

Default dry-run (no Notion mutations, no SQLite writes). Pass ``--commit`` to
persist. Token is only ever sent in ``Authorization`` headers via the
existing ``NotionClient`` from stage4 — never logged or written to reports.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from scripts.discovery.stage2_ingest import get_runtime_notion_api_key
from scripts.discovery.stage4_push_notion import (
    NOTION_API_VERSION,
    NOTION_BASE_URL,
    RATE_LIMIT_SLEEP_S,
    MAX_429_RETRIES,
    NotionClient,
)

DEFAULT_SQLITE_PATH = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_REPORTS_DIR = Path("reports")
MAX_CONSECUTIVE_NON429_ERRORS = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _patch(client: NotionClient, path: str, body: dict[str, Any]) -> httpx.Response:
    """PATCH wrapper using the shared client's retry/backoff loop."""
    return client._request("PATCH", path, json=body)  # noqa: SLF001 (intentional reuse)


def select_rows(conn: sqlite3.Connection, ids: list[int]) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in ids)
    cur = conn.execute(
        f"SELECT rowid, referente_nombre, canal, notion_page_id, "
        f" contenido_html IS NOT NULL AS has_content "
        f"FROM discovered_items WHERE rowid IN ({placeholders}) ORDER BY rowid",
        ids,
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def archive_and_unlink(
    *,
    sqlite_path: Path,
    ids: list[int],
    commit: bool,
    reports_dir: Path,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "started": _now_iso(),
        "commit": commit,
        "requested_ids": ids,
        "results": [],
        "archived_ok": 0,
        "skipped_no_page_id": 0,
        "errors": 0,
    }
    conn = sqlite3.connect(str(sqlite_path))
    rows = select_rows(conn, ids)
    found_ids = {r["rowid"] for r in rows}
    missing = [i for i in ids if i not in found_ids]
    if missing:
        summary["missing_ids"] = missing

    if not commit:
        for r in rows:
            summary["results"].append({
                "sqlite_id": r["rowid"],
                "referente": r["referente_nombre"],
                "canal": r["canal"],
                "notion_page_id": r["notion_page_id"],
                "has_content": bool(r["has_content"]),
                "action": "dry-run-would-archive" if r["notion_page_id"] else "no-page-id",
            })
        return _persist(summary, reports_dir)

    api_key = get_runtime_notion_api_key()
    consecutive_errors = 0
    with httpx.Client(timeout=30.0) as http:
        client = NotionClient(api_key, base_url=NOTION_BASE_URL,
                              api_version=NOTION_API_VERSION, client=http)
        try:
            for r in rows:
                page_id = r["notion_page_id"]
                if not page_id:
                    summary["skipped_no_page_id"] += 1
                    summary["results"].append({
                        "sqlite_id": r["rowid"],
                        "referente": r["referente_nombre"],
                        "action": "skipped",
                        "reason": "no_notion_page_id",
                    })
                    continue
                resp = _patch(client, f"/pages/{page_id}", {"archived": True})
                time.sleep(RATE_LIMIT_SLEEP_S)
                if resp.status_code == 200:
                    body = resp.json()
                    archived_now = bool(body.get("archived") or body.get("in_trash"))
                    conn.execute(
                        "UPDATE discovered_items SET notion_page_id = NULL WHERE rowid = ?",
                        (r["rowid"],),
                    )
                    conn.commit()
                    summary["archived_ok"] += 1
                    consecutive_errors = 0
                    summary["results"].append({
                        "sqlite_id": r["rowid"],
                        "referente": r["referente_nombre"],
                        "notion_page_id": page_id,
                        "action": "archived",
                        "archived_confirmed": archived_now,
                    })
                else:
                    summary["errors"] += 1
                    consecutive_errors += 1
                    summary["results"].append({
                        "sqlite_id": r["rowid"],
                        "referente": r["referente_nombre"],
                        "notion_page_id": page_id,
                        "action": "error",
                        "http_status": resp.status_code,
                        "body_snippet": resp.text[:200],
                    })
                    if consecutive_errors >= MAX_CONSECUTIVE_NON429_ERRORS:
                        summary["aborted"] = (
                            f"abort_after_{consecutive_errors}_consecutive_non429_errors"
                        )
                        break
        finally:
            client.close()

    summary["finished"] = _now_iso()
    return _persist(summary, reports_dir)


def _persist(summary: dict[str, Any], reports_dir: Path) -> dict[str, Any]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = "commit" if summary.get("commit") else "dryrun"
    path = reports_dir / f"rerender-pages-{_now_ts()}-{suffix}.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    summary["_report_path"] = str(path)
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Archive Notion pages + null notion_page_id for re-render.")
    p.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE_PATH)
    p.add_argument("--sqlite-ids", required=True,
                   help="Comma-separated SQLite rowids to re-render (e.g. '1,31,32,33,51').")
    p.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    p.add_argument("--commit", action="store_true",
                   help="Persist (default: dry-run).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        ids = [int(x.strip()) for x in args.sqlite_ids.split(",") if x.strip()]
    except ValueError:
        print("error: --sqlite-ids must be comma-separated integers", file=sys.stderr)
        return 2
    if not ids:
        print("error: at least one id required", file=sys.stderr)
        return 2
    summary = archive_and_unlink(
        sqlite_path=args.sqlite,
        ids=ids,
        commit=args.commit,
        reports_dir=args.reports_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary.get("errors", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
