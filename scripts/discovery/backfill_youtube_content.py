#!/usr/bin/env python3
"""Backfill ``contenido_html`` for promoted ``canal=youtube`` items via Data API v3.

Companion to ``backfill_content_for_promoted.py``: that script handles RSS /
web feeds. This script handles the YouTube case, which Stage 2's RSSHub feed
cannot enrich (RSSHub returns thumbnail + title only, leaving
``contenido_html = NULL`` and forcing Stage 4 into ``created_no_body``).

Decision context (spike 013-K, PR #342):
  * VIA A (residential VM browser) invalidated — 100% reCAPTCHA wall.
  * VIA B (this) — 8/8 individual coverage with retry-once on transient
    HTTP 400 "API key expired" Google-side flake.

Default: dry-run (no DB writes). Pass ``--commit`` to persist
``contenido_html`` and stamp ``contenido_extraido_at``.

Read-only over Notion. Reads ``YOUTUBE_DATA_API_KEY`` from env (loaded by
the dispatcher's systemd ``EnvironmentFile=/home/rick/.config/openclaw/env``).
"""

from __future__ import annotations

import argparse
import asyncio
import html as _html
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from dispatcher.extractors.youtube_data_api import (
    YoutubeApiKeyMissing,
    YoutubeExtractionError,
    YoutubeExtractionResult,
    YoutubeVideoNotFound,
    extract_youtube_video,
)

DEFAULT_SQLITE_PATH = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_REPORTS_DIR = Path("reports")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def extract_video_id_from_url(url: str) -> str | None:
    """Best-effort extraction of YouTube ``video_id`` from a canonical URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = (parsed.netloc or "").lower()
    if "youtube.com" in host:
        qs = parse_qs(parsed.query)
        v = qs.get("v")
        if v and v[0]:
            return v[0]
        # ``/shorts/<id>`` or ``/embed/<id>``.
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
            return parts[1]
    if "youtu.be" in host:
        parts = [p for p in parsed.path.split("/") if p]
        if parts:
            return parts[0]
    return None


def select_promoted_youtube_without_content(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT rowid, url_canonica, referente_id, referente_nombre, canal "
        "FROM discovered_items "
        "WHERE promovido_a_candidato_at IS NOT NULL "
        "  AND contenido_html IS NULL "
        "  AND canal = 'youtube' "
        "ORDER BY rowid"
    )
    return [
        {
            "sqlite_id": r[0],
            "url_canonica": r[1],
            "referente_id": r[2],
            "referente_nombre": r[3],
            "canal": r[4],
        }
        for r in cur.fetchall()
    ]


def update_content(
    conn: sqlite3.Connection,
    sqlite_id: int,
    html: str,
    *,
    cleaned: bool = False,
    removals_count: int | None = None,
) -> None:
    if cleaned:
        conn.execute(
            "UPDATE discovered_items SET contenido_html = ?, contenido_extraido_at = ?, "
            "description_cleaned_at = ?, description_removals_count = ? "
            "WHERE rowid = ?",
            (html, _now_iso(), _now_iso(), removals_count, sqlite_id),
        )
    else:
        conn.execute(
            "UPDATE discovered_items SET contenido_html = ?, contenido_extraido_at = ? "
            "WHERE rowid = ?",
            (html, _now_iso(), sqlite_id),
        )


def ensure_cleaner_columns(conn: sqlite3.Connection) -> None:
    """Idempotently add the description-cleaner tracking columns.

    Adds ``description_cleaned_at TEXT`` and ``description_removals_count INTEGER``
    to ``discovered_items`` if they do not already exist. Safe to call on every
    invocation — a no-op when the columns are present.
    """
    existing = {r[1] for r in conn.execute("PRAGMA table_info(discovered_items)")}
    if "description_cleaned_at" not in existing:
        conn.execute("ALTER TABLE discovered_items ADD COLUMN description_cleaned_at TEXT")
    if "description_removals_count" not in existing:
        conn.execute(
            "ALTER TABLE discovered_items ADD COLUMN description_removals_count INTEGER"
        )


def render_video_to_html(result: YoutubeExtractionResult) -> str:
    """Render the extraction result into HTML for ``html_to_notion_blocks``.

    Layout (designed to flow well through the existing markdownify → Notion
    blocks pipeline):
      1. ``<p>`` with metadata (canal, duration, publishedAt, view/like counts).
      2. ``<h2>Descripción</h2>`` + ``<p>`` paragraphs from description
         (split on blank lines, escaped).
      3. ``<h2>Capítulos</h2>`` (only if chapters parsed) as a ``<ul>``.

    Plain HTML, no scripts, no external assets — every URL referenced inside
    the description is preserved as text and Stage 4's converter handles it.
    """
    parts: list[str] = []

    meta_bits: list[str] = []
    if result.duration_seconds:
        h, rem = divmod(result.duration_seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            meta_bits.append(f"Duración: {h}h{m:02d}m{s:02d}s")
        else:
            meta_bits.append(f"Duración: {m}m{s:02d}s")
    if result.published_at:
        meta_bits.append(f"Publicado: {result.published_at.date().isoformat()}")
    if result.channel_title:
        meta_bits.append(f"Canal: {_html.escape(result.channel_title)}")
    if result.view_count is not None:
        meta_bits.append(f"Vistas: {result.view_count:,}")
    if result.like_count is not None:
        meta_bits.append(f"Likes: {result.like_count:,}")
    if meta_bits:
        parts.append("<p><em>" + " · ".join(meta_bits) + "</em></p>")

    if result.description:
        parts.append("<h2>Descripción</h2>")
        for paragraph in result.description.split("\n\n"):
            text = paragraph.strip()
            if not text:
                continue
            parts.append("<p>" + _html.escape(text).replace("\n", "<br/>") + "</p>")

    if result.chapters:
        parts.append("<h2>Capítulos</h2>")
        parts.append("<ul>")
        for ch in result.chapters:
            parts.append(
                f"<li>{ch['start_seconds']}s — {_html.escape(ch['title'])}</li>"
            )
        parts.append("</ul>")

    return "\n".join(parts)


async def _enrich_one(
    client: httpx.AsyncClient,
    row: dict[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "sqlite_id": row["sqlite_id"],
        "url_canonica": row["url_canonica"],
        "video_id": None,
        "status": "pending",
        "error": None,
        "description_length": 0,
        "duration_seconds": None,
    }
    video_id = extract_video_id_from_url(row["url_canonica"])
    out["video_id"] = video_id
    if not video_id:
        out["status"] = "skipped_no_video_id"
        return out
    try:
        result = await extract_youtube_video(video_id, http=client)
    except YoutubeVideoNotFound as exc:
        out["status"] = "not_found"
        out["error"] = str(exc)[:300]
        return out
    except YoutubeExtractionError as exc:
        out["status"] = "extraction_error"
        out["error"] = str(exc)[:300]
        return out
    out["html"] = render_video_to_html(result)
    out["description_length"] = len(result.description or "")
    out["duration_seconds"] = result.duration_seconds
    out["status"] = "ok"
    return out


async def run_backfill_async(
    *,
    sqlite_path: Path,
    commit: bool,
    reports_dir: Path,
    limit: int | None,
    clean_description: bool = False,
) -> dict[str, Any]:
    started = _now_iso()
    conn = sqlite3.connect(str(sqlite_path))
    if clean_description and commit:
        ensure_cleaner_columns(conn)
    pending = select_promoted_youtube_without_content(conn)
    if limit is not None:
        pending = pending[:limit]
    summary: dict[str, Any] = {
        "started": started,
        "commit": commit,
        "clean_description": clean_description,
        "pending_total": len(pending),
        "ok": 0,
        "not_found": 0,
        "extraction_error": 0,
        "skipped_no_video_id": 0,
        "items": [],
    }

    if not pending:
        summary["finished"] = _now_iso()
        _write_report(reports_dir, summary)
        return summary

    async with httpx.AsyncClient(
        headers={"User-Agent": "umbral-stage2-youtube-backfill/1.0"}
    ) as client:
        for row in pending:
            res = await _enrich_one(client, row)
            status = res["status"]
            summary[status] = summary.get(status, 0) + 1
            if status == "ok":
                final_html = res["html"]
                removals_count: int | None = None
                if clean_description:
                    # Local import keeps the stripper optional at module level.
                    from dispatcher.extractors.youtube_description_cleaner import (
                        clean_html as _clean_html,
                    )

                    final_html, removals = _clean_html(res["html"])
                    removals_count = len(removals)
                    res["removals_count"] = removals_count
                    res["removals_reasons"] = sorted({r.reason for r in removals})
                    print(
                        f"  cleaned sid={row['sqlite_id']} "
                        f"removals={removals_count} reasons={res['removals_reasons']}",
                        flush=True,
                    )
                if commit:
                    update_content(
                        conn,
                        row["sqlite_id"],
                        final_html,
                        cleaned=clean_description,
                        removals_count=removals_count,
                    )
            # Strip ``html`` from the report payload (can be large).
            res_for_report = {k: v for k, v in res.items() if k != "html"}
            summary["items"].append(res_for_report)

    if commit:
        conn.commit()
    summary["finished"] = _now_iso()
    _write_report(reports_dir, summary)
    return summary


def _write_report(reports_dir: Path, summary: dict[str, Any]) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"backfill-youtube-content-{_now_ts()}.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Backfill contenido_html for promoted YouTube items via Data API v3.",
    )
    p.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE_PATH)
    p.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    p.add_argument(
        "--commit", action="store_true",
        help="Persist updates (default: dry-run, no DB writes).",
    )
    p.add_argument(
        "--limit", type=int, default=None,
        help="Optional cap on number of pending rows to process.",
    )
    p.add_argument(
        "--clean-description", action="store_true",
        help=(
            "Pass extracted contenido_html through "
            "dispatcher.extractors.youtube_description_cleaner before writing. "
            "OPT-IN. Stamps description_cleaned_at + description_removals_count "
            "(columns auto-created if missing)."
        ),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        summary = asyncio.run(
            run_backfill_async(
                sqlite_path=args.sqlite,
                commit=args.commit,
                reports_dir=args.reports_dir,
                limit=args.limit,
                clean_description=args.clean_description,
            )
        )
    except YoutubeApiKeyMissing as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        f"pending={summary['pending_total']} ok={summary['ok']} "
        f"not_found={summary['not_found']} extraction_error={summary['extraction_error']} "
        f"skipped_no_video_id={summary['skipped_no_video_id']} "
        f"commit={summary['commit']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
