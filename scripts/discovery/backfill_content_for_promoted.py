#!/usr/bin/env python3
"""Backfill ``contenido_html`` for items already promoted to candidato.

Re-fetches each referente's RSS/YouTube/Web feed and tries to match the canonical
URL of every promoted-but-uncaptured row. Reuses Stage 2 fetch + parse code so
extraction logic stays in a single place.

NO HTTP scraping of article pages — only feed content. Items not present in the
current feed window remain ``contenido_html = NULL`` (counted under
``unmatched``).

Defaults to dry-run (no DB writes, only summary). Pass ``--commit`` to persist.

Reports JSON to ``reports/backfill-content-<ts>.json`` (always, even in dry-run).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# Reuse Stage 2 internals.
from scripts.discovery.stage2_ingest import (
    CHANNEL_RSS,
    CHANNEL_WEB_RSS,
    CHANNEL_YOUTUBE,
    DEFAULT_NOTION_API_VERSION,
    canonicalize_url,
    fetch_referentes,
    get_runtime_notion_api_key,
    is_direct_rss_candidate,
    load_registry,
    normalize_referente,
    parse_feed_xml,
    parse_youtube_channel_id,
    verify_rsshub,
)

DEFAULT_SQLITE_PATH = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_REGISTRY_PATH = Path("config") / "discovery_registry.yaml"
DEFAULT_RSSHUB_BASE = "http://127.0.0.1:1200"
DEFAULT_REPORTS_DIR = Path("reports")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def select_promoted_without_content(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT rowid, url_canonica, referente_id, canal "
        "FROM discovered_items "
        "WHERE promovido_a_candidato_at IS NOT NULL AND contenido_html IS NULL "
        "ORDER BY rowid"
    )
    return [
        {"sqlite_id": r[0], "url_canonica": r[1], "referente_id": r[2], "canal": r[3]}
        for r in cur.fetchall()
    ]


def update_content(conn: sqlite3.Connection, sqlite_id: int, html: str) -> None:
    conn.execute(
        "UPDATE discovered_items SET contenido_html = ?, contenido_extraido_at = ? "
        "WHERE rowid = ?",
        (html, _now_iso(), sqlite_id),
    )


def fetch_and_index(
    client: httpx.Client, *, url: str | None
) -> dict[str, str]:
    """Return mapping canonical_url -> contenido_html for a single feed."""
    if not url:
        return {}
    try:
        r = client.get(url, timeout=20.0)
        if r.status_code >= 400:
            return {}
        items = parse_feed_xml(r.text)
    except Exception:
        return {}
    out: dict[str, str] = {}
    for it in items:
        u = (it.get("url") or "").strip()
        html = it.get("contenido_html")
        if not u or not html:
            continue
        canon = canonicalize_url(u)
        if canon and canon not in out:
            out[canon] = html
    return out


def run_backfill(
    *,
    sqlite_path: Path,
    registry_path: Path,
    rsshub_base: str,
    commit: bool,
    reports_dir: Path,
) -> dict[str, Any]:
    started = _now_iso()
    conn = sqlite3.connect(str(sqlite_path))
    pending = select_promoted_without_content(conn)
    summary: dict[str, Any] = {
        "started": started,
        "commit": commit,
        "pending_total": len(pending),
        "matched": 0,
        "unmatched": 0,
        "feed_errors": 0,
        "by_referente": {},
    }

    if not pending:
        summary["finished"] = _now_iso()
        _write_report(reports_dir, summary)
        return summary

    # Verify RSSHub for YouTube channels.
    try:
        verify_rsshub(rsshub_base)
        rsshub_ok = True
    except Exception as exc:
        rsshub_ok = False
        summary["rsshub_warning"] = f"{exc.__class__.__name__}: {exc}"

    api_key = get_runtime_notion_api_key()
    registry = load_registry(registry_path)
    raw_rows = fetch_referentes(
        data_source_id=registry["data_source_id"],
        api_key=api_key,
        api_version=DEFAULT_NOTION_API_VERSION,
    )
    referentes = {r.id: r for r in (normalize_referente(row) for row in raw_rows)}

    pending_by_ref: dict[str, list[dict[str, Any]]] = {}
    for row in pending:
        pending_by_ref.setdefault(row["referente_id"], []).append(row)

    with httpx.Client(headers={"User-Agent": "umbral-stage2-backfill/1.0"}) as client:
        for ref_id, rows in pending_by_ref.items():
            ref = referentes.get(ref_id)
            ref_label = ref.nombre if ref else f"<missing:{ref_id}>"
            ref_summary = {"pending": len(rows), "matched": 0, "unmatched": 0}
            content_index: dict[str, str] = {}

            if ref is not None:
                # RSS direct.
                content_index.update(fetch_and_index(client, url=ref.rss_url))
                # YouTube via RSSHub.
                if rsshub_ok and ref.web_url:
                    yt = parse_youtube_channel_id(ref.web_url)
                    if yt:
                        kind, ident = yt
                        if kind == "channel_id":
                            yt_url = f"{rsshub_base}/youtube/channel/{ident}"
                        elif kind == "user":
                            yt_url = f"{rsshub_base}/youtube/user/{ident}"
                        elif kind == "custom":
                            yt_url = f"{rsshub_base}/youtube/c/{ident}"
                        else:
                            yt_url = None
                        if yt_url:
                            content_index.update(fetch_and_index(client, url=yt_url))
                # Web RSS.
                if ref.web_url and is_direct_rss_candidate(ref.web_url):
                    content_index.update(fetch_and_index(client, url=ref.web_url))

            for row in rows:
                html = content_index.get(row["url_canonica"])
                if html:
                    ref_summary["matched"] += 1
                    summary["matched"] += 1
                    if commit:
                        update_content(conn, row["sqlite_id"], html)
                else:
                    ref_summary["unmatched"] += 1
                    summary["unmatched"] += 1
            summary["by_referente"][ref_label] = ref_summary

    if commit:
        conn.commit()
    summary["finished"] = _now_iso()
    _write_report(reports_dir, summary)
    return summary


def _write_report(reports_dir: Path, summary: dict[str, Any]) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"backfill-content-{_now_ts()}.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill contenido_html for promoted items.")
    p.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE_PATH)
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    p.add_argument("--rsshub-base", default=DEFAULT_RSSHUB_BASE)
    p.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    p.add_argument("--commit", action="store_true",
                   help="Persist updates (default: dry-run, no DB writes).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    summary = run_backfill(
        sqlite_path=args.sqlite,
        registry_path=args.registry,
        rsshub_base=args.rsshub_base,
        commit=args.commit,
        reports_dir=args.reports_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
