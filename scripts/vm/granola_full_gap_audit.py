#!/usr/bin/env python3
"""Granola Full Gap Audit — Windows VM standalone script.

Compares the Granola desktop cache (cache-v6.json) against the Notion raw DB
to detect meetings that exist locally but were never ingested.

This script is self-contained: it reads the cache file directly and queries
Notion via REST API. No repo clone or virtualenv required — only `requests`.

Prerequisites:
    - Python 3.10+ with `requests` installed (pip install requests)
    - Granola desktop app installed (%APPDATA%\\Granola\\cache-v6.json)
    - NOTION_TOKEN env var set (integration token)
    - NOTION_GRANOLA_DB_ID env var set (raw DB id)

Usage:
    python granola_full_gap_audit.py
    python granola_full_gap_audit.py --fail-on-recent-gaps
    python granola_full_gap_audit.py --cache-path "C:\\custom\\cache-v6.json"
    python granola_full_gap_audit.py --manual-dir "G:\\Mi unidad\\...\\Granola"

Exit codes:
    0 = no gaps
    2 = recent gaps found (with --fail-on-recent-gaps)
    1 = script error
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SMOKE_TERMS = (
    "smoke", "manual-watcher", "manual watcher", "watcher-smoke",
    "test", "prueba",
)
NEAR_DUPLICATE_THRESHOLD = 0.84
RECENT_DAYS = 14
NOTION_API_VERSION = "2022-06-28"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_title(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    ascii_text = text.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(cleaned.split())


def _is_smoke_like(title: str) -> bool:
    norm = _normalize_title(title)
    return any(term in norm for term in SMOKE_TERMS)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(a=a, b=b).ratio()


def _parse_date(raw: str) -> date | None:
    v = (raw or "").strip()[:10]
    if not v:
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Cache reader
# ---------------------------------------------------------------------------

def load_cache_documents(cache_path: Path) -> list[dict[str, Any]]:
    """Read cache-v6.json and return exportable meeting documents."""
    raw = json.loads(cache_path.read_bytes())
    docs_map = (
        raw.get("cache", {}).get("state", {}).get("documents", {})
    )
    if isinstance(docs_map, list):
        docs = docs_map
    elif isinstance(docs_map, dict):
        docs = list(docs_map.values())
    else:
        return []

    results = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if doc.get("deleted_at"):
            continue
        doc_type = doc.get("type", "")
        if doc_type not in ("meeting", ""):
            continue

        title = (doc.get("title") or "").strip()
        if not title:
            continue

        # Determine if document has meaningful content
        has_notes = bool((doc.get("notes_plain") or "").strip())
        has_markdown = bool((doc.get("notes_markdown") or "").strip())
        has_transcript = doc.get("transcribe", False)
        has_content = has_notes or has_markdown or has_transcript

        # Extract meeting date from created_at
        created = doc.get("created_at", "")
        meeting_date = created[:10] if created else ""

        results.append({
            "document_id": doc.get("id", ""),
            "title": title,
            "normalized_title": _normalize_title(title),
            "meeting_date": meeting_date,
            "has_content": has_content,
            "has_notes": has_notes,
            "has_markdown": has_markdown,
            "has_transcript": has_transcript,
            "is_smoke": _is_smoke_like(title),
        })

    return results


# ---------------------------------------------------------------------------
# Notion reader (standalone, no SDK)
# ---------------------------------------------------------------------------

def _notion_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def _extract_title(page: dict) -> str:
    props = page.get("properties", {})
    for name in ("Nombre", "Name", "Title", "Título"):
        prop = props.get(name)
        if not prop:
            continue
        if prop.get("type") == "title":
            return "".join(
                t.get("plain_text", "") for t in (prop.get("title") or [])
            )
    return ""


def _extract_traceability(page: dict) -> str:
    props = page.get("properties", {})
    for name in ("Trazabilidad", "Traceability"):
        prop = props.get(name)
        if not prop:
            continue
        if prop.get("type") == "rich_text":
            return "".join(
                t.get("plain_text", "") for t in (prop.get("rich_text") or [])
            )
    return ""


def _extract_document_id_from_traceability(traz: str) -> str:
    for line in traz.splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "granola_document_id":
            return value.strip()
    return ""


def _extract_date_prop(page: dict) -> str:
    props = page.get("properties", {})
    for name in ("Fecha", "Date"):
        prop = props.get(name)
        if isinstance(prop, dict) and prop.get("type") == "date":
            return ((prop.get("date") or {}).get("start") or "")
    return ""


def load_notion_raw_pages(token: str, db_id: str, max_pages: int = 300) -> list[dict[str, Any]]:
    """Query Notion raw DB and return structured page entries."""
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = _notion_headers(token)
    pages: list[dict] = []
    payload: dict[str, Any] = {"page_size": 100}

    while True:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more") or len(pages) >= max_pages:
            break
        payload["start_cursor"] = data["next_cursor"]

    results = []
    for page in pages:
        title = _extract_title(page)
        traz = _extract_traceability(page)
        results.append({
            "page_id": page.get("id", ""),
            "url": page.get("url", ""),
            "title": title,
            "normalized_title": _normalize_title(title),
            "date": _extract_date_prop(page),
            "granola_document_id": _extract_document_id_from_traceability(traz),
            "has_traceability": bool(traz.strip()),
            "is_smoke": _is_smoke_like(title),
        })

    return results


# ---------------------------------------------------------------------------
# Gap classification
# ---------------------------------------------------------------------------

def classify_gaps(
    cache_docs: list[dict[str, Any]],
    notion_pages: list[dict[str, Any]],
    recent_days: int = RECENT_DAYS,
) -> dict[str, Any]:
    """Compare cache documents against Notion pages, classify gaps."""
    # Index Notion pages
    notion_by_doc_id: dict[str, dict] = {}
    notion_by_title: dict[str, list[dict]] = {}
    notion_real = [p for p in notion_pages if not p["is_smoke"]]

    for p in notion_real:
        notion_by_title.setdefault(p["normalized_title"], []).append(p)
        if p["granola_document_id"]:
            notion_by_doc_id[p["granola_document_id"]] = p

    # Filter cache docs
    real_cache = [d for d in cache_docs if not d["is_smoke"]]
    title_counts = Counter(d["normalized_title"] for d in real_cache)
    cutoff = date.today() - timedelta(days=recent_days)

    present = []
    recent_gaps = []
    historic_gaps = []
    non_recordings = []

    for doc in real_cache:
        meeting_date = _parse_date(doc["meeting_date"])
        is_recent = meeting_date is not None and meeting_date >= cutoff

        entry = {
            "document_id": doc["document_id"],
            "title": doc["title"],
            "meeting_date": doc["meeting_date"],
            "has_content": doc["has_content"],
        }

        # Skip non-recordings (no content at all)
        if not doc["has_content"]:
            non_recordings.append({**entry, "reason": "no_content_in_granola"})
            continue

        # Match by document_id
        if doc["document_id"] in notion_by_doc_id:
            present.append({
                **entry,
                "match": "document_id",
                "page_id": notion_by_doc_id[doc["document_id"]]["page_id"],
            })
            continue

        # Match by exact title (unique)
        if (doc["normalized_title"] in notion_by_title
                and title_counts[doc["normalized_title"]] == 1
                and len(notion_by_title[doc["normalized_title"]]) == 1):
            present.append({
                **entry,
                "match": "exact_title",
                "page_id": notion_by_title[doc["normalized_title"]][0]["page_id"],
            })
            continue

        # Find near-matches
        near = []
        for np in notion_real:
            score = _similarity(doc["normalized_title"], np["normalized_title"])
            if score >= NEAR_DUPLICATE_THRESHOLD:
                near.append({"title": np["title"], "page_id": np["page_id"], "score": round(score, 2)})
        near.sort(key=lambda x: -x["score"])

        gap_entry = {**entry, "near_matches": near}

        if is_recent:
            recent_gaps.append(gap_entry)
        else:
            historic_gaps.append(gap_entry)

    return {
        "timestamp": datetime.now().isoformat(),
        "cache_total": len(cache_docs),
        "cache_real": len(real_cache),
        "cache_smoke": len(cache_docs) - len(real_cache),
        "notion_total": len(notion_pages),
        "notion_real": len(notion_real),
        "present_count": len(present),
        "non_recording_count": len(non_recordings),
        "recent_gap_count": len(recent_gaps),
        "historic_gap_count": len(historic_gaps),
        "recent_gaps": recent_gaps,
        "historic_gaps": historic_gaps,
        "non_recordings": non_recordings,
        "present": present,
    }


# ---------------------------------------------------------------------------
# Manual folder audit
# ---------------------------------------------------------------------------

def audit_manual_folder(manual_dir: Path) -> dict[str, Any]:
    """Audit .md files in the manual exports folder."""
    if not manual_dir.is_dir():
        return {"error": "directory_not_found", "path": str(manual_dir)}

    files = sorted(manual_dir.glob("*.md"))
    results = []
    for f in files:
        size = f.stat().st_size
        preview = ""
        has_content = False
        try:
            text = f.read_text(encoding="utf-8")
            has_content = len(text.strip()) > 50
            preview = text[:150].replace("\n", " ").strip()
        except Exception as e:
            preview = f"READ_ERROR: {e}"
        results.append({
            "filename": f.name,
            "size_bytes": size,
            "has_useful_content": has_content,
            "empty_or_corrupt": size == 0 or not has_content,
            "content_preview": preview,
        })

    return {
        "directory": str(manual_dir),
        "total_files": len(results),
        "valid_count": sum(1 for r in results if r["has_useful_content"]),
        "empty_or_corrupt_count": sum(1 for r in results if r["empty_or_corrupt"]),
        "files": results,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Granola Full Gap Audit (Windows VM standalone)"
    )
    parser.add_argument(
        "--cache-path",
        default=os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "Granola", "cache-v6.json",
        ),
        help="Path to Granola cache-v6.json",
    )
    parser.add_argument(
        "--manual-dir",
        default=None,
        help="Path to manual Granola exports folder (G: drive)",
    )
    parser.add_argument(
        "--fail-on-recent-gaps",
        action="store_true",
        help="Exit 2 if recent gaps are detected",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of summary",
    )
    args = parser.parse_args()

    # Validate env — accept multiple token var names.
    # NOTION_API_KEY is preferred (matches VPS env); NOTION_TOKEN may be stale on VM.
    notion_token = (
        os.environ.get("NOTION_API_KEY")
        or os.environ.get("NOTION_TOKEN")
        or os.environ.get("NOTION_SUPERVISOR_API_KEY")
        or ""
    ).strip()
    db_id = os.environ.get("NOTION_GRANOLA_DB_ID", "").strip()
    if not notion_token:
        print("ERROR: NOTION_TOKEN not set", file=sys.stderr)
        return 1
    if not db_id:
        print("ERROR: NOTION_GRANOLA_DB_ID not set", file=sys.stderr)
        return 1

    cache_path = Path(args.cache_path)
    if not cache_path.is_file():
        print(f"ERROR: cache not found at {cache_path}", file=sys.stderr)
        return 1

    # --- Part 1: Gap audit ---
    print(f"Loading cache: {cache_path}")
    cache_docs = load_cache_documents(cache_path)
    print(f"  Cache documents: {len(cache_docs)}")

    print(f"Querying Notion raw DB: {db_id[:8]}...")
    notion_pages = load_notion_raw_pages(notion_token, db_id)
    print(f"  Notion pages: {len(notion_pages)}")

    report = classify_gaps(cache_docs, notion_pages)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== Gap Audit Results ===")
        print(f"  Cache: {report['cache_real']} real + {report['cache_smoke']} smoke")
        print(f"  Notion: {report['notion_real']} real")
        print(f"  Matched: {report['present_count']}")
        print(f"  Non-recordings: {report['non_recording_count']}")
        print(f"  Recent gaps: {report['recent_gap_count']}")
        print(f"  Historic gaps: {report['historic_gap_count']}")

        if report["recent_gaps"]:
            print(f"\n--- Recent Gaps (last {RECENT_DAYS} days) ---")
            for g in report["recent_gaps"]:
                print(f"  [{g['meeting_date']}] {g['title']} (id={g['document_id'][:12]}...)")
                for m in g.get("near_matches", []):
                    print(f"    ~ {m['title']} (score={m['score']})")

        if report["non_recordings"]:
            print(f"\n--- Non-recordings (no content in Granola) ---")
            for nr in report["non_recordings"]:
                print(f"  [{nr['meeting_date']}] {nr['title']}")

    # --- Part 2: Manual folder audit ---
    manual_dir = args.manual_dir or os.environ.get("GOOGLE_DRIVE_MANUAL_DIR")
    if manual_dir:
        manual_path = Path(manual_dir)
        print(f"\n=== Manual Folder Audit: {manual_path} ===")
        manual_report = audit_manual_folder(manual_path)
        if "error" in manual_report:
            print(f"  SKIP: {manual_report['error']}")
        else:
            print(f"  Total files: {manual_report['total_files']}")
            print(f"  Valid: {manual_report['valid_count']}")
            print(f"  Empty/corrupt: {manual_report['empty_or_corrupt_count']}")
            if manual_report["empty_or_corrupt_count"] > 0:
                for f in manual_report["files"]:
                    if f["empty_or_corrupt"]:
                        print(f"    ! {f['filename']} ({f['size_bytes']}B)")

    # Exit code
    if args.fail_on_recent_gaps and report["recent_gap_count"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
