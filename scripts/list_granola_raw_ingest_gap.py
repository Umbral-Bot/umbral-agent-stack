#!/usr/bin/env python3
"""Compare live Granola cache exportables against the live Notion raw DB.

This script covers the ingestion leg that `list_granola_promotion_candidates.py`
does not see:

    Granola cache/API -> exporter -> Notion raw DB

It is intentionally read-only. The output is designed for backlog triage before
running any raw-only batch.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts import env_loader

env_loader.load()

from scripts.vm import granola_cache_exporter
from worker import config, notion_client


SMOKE_TERMS = (
    "smoke",
    "manual-watcher",
    "manual watcher",
    "watcher-smoke",
    "test",
    "prueba",
)
NEAR_DUPLICATE_THRESHOLD = 0.84


@dataclass(frozen=True)
class ExportItem:
    document_id: str
    title: str
    meeting_date: str
    notes_source: str
    transcript_source: str
    normalized_title: str


def _normalize_title(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    ascii_text = text.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(cleaned.split())


def _is_smoke_like_title(title: str) -> bool:
    normalized = _normalize_title(title)
    return any(term in normalized for term in SMOKE_TERMS)


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(a=left, b=right).ratio()


def _parse_meeting_date(raw: str) -> date | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _load_export_items(
    *,
    cache_path: Path,
    limit: int | None = None,
    enable_private_api_hydration: bool = True,
) -> dict[str, Any]:
    granola_cache_exporter.logger.setLevel(logging.WARNING)
    with tempfile.TemporaryDirectory(prefix="granola-gap-") as tmpdir:
        base = Path(tmpdir)
        export_dir = base / "exports"
        processed_dir = base / "processed"
        manifest_path = base / "manifest.json"
        export_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        summary = granola_cache_exporter.export_cache_once(
            cache_path=cache_path,
            export_dir=export_dir,
            processed_dir=processed_dir,
            manifest_path=manifest_path,
            dry_run=True,
            force=True,
            limit=limit,
            document_ids=None,
            enable_private_api_hydration=enable_private_api_hydration,
        )
    exports: list[ExportItem] = []
    for item in summary.get("exports", []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        exports.append(
            ExportItem(
                document_id=str(item.get("document_id") or "").strip(),
                title=title,
                meeting_date=str(item.get("meeting_date") or "").strip(),
                notes_source=str(item.get("notes_source") or "none"),
                transcript_source=str(item.get("transcript_source") or "none"),
                normalized_title=_normalize_title(title),
            )
        )
    summary["exports"] = exports
    return summary


def _load_raw_items(max_items: int) -> dict[str, Any]:
    if not config.NOTION_GRANOLA_DB_ID:
        raise RuntimeError("NOTION_GRANOLA_DB_ID not configured")
    raw = notion_client.read_database(config.NOTION_GRANOLA_DB_ID, max_items=max_items)
    real_items: list[dict[str, Any]] = []
    smoke_items: list[dict[str, Any]] = []
    for item in raw.get("items", []):
        title = str(item.get("title") or "")
        entry = {
            "page_id": item.get("page_id"),
            "url": item.get("url"),
            "title": title,
            "normalized_title": _normalize_title(title),
            "properties": item.get("properties") or {},
        }
        if _is_smoke_like_title(title):
            smoke_items.append(entry)
        else:
            real_items.append(entry)
    return {
        "database_id": raw.get("database_id"),
        "url": raw.get("url"),
        "title": raw.get("title"),
        "all_items": raw.get("items", []),
        "real_items": real_items,
        "smoke_items": smoke_items,
    }


def _find_near_raw_matches(
    export_title: str,
    raw_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for raw in raw_items:
        score = _similarity(export_title, str(raw.get("normalized_title") or ""))
        if score >= NEAR_DUPLICATE_THRESHOLD:
            matches.append(
                {
                    "title": raw.get("title"),
                    "page_id": raw.get("page_id"),
                    "score": round(score, 2),
                }
            )
    matches.sort(key=lambda item: (-float(item["score"]), str(item["title"])))
    return matches


def _classify_gap(
    exports: list[ExportItem],
    raw_snapshot: dict[str, Any],
    *,
    recent_days: int,
) -> dict[str, Any]:
    raw_real_items = raw_snapshot["real_items"]
    raw_by_title: dict[str, list[dict[str, Any]]] = {}
    for item in raw_real_items:
        raw_by_title.setdefault(str(item["normalized_title"]), []).append(item)

    export_title_counts = Counter(item.normalized_title for item in exports)
    cutoff = date.today() - timedelta(days=recent_days)

    likely_present: list[dict[str, Any]] = []
    batch1_recent_unique: list[dict[str, Any]] = []
    batch1_recent_ambiguous: list[dict[str, Any]] = []
    historic_unique: list[dict[str, Any]] = []
    historic_ambiguous: list[dict[str, Any]] = []

    for item in exports:
        near_raw_matches = _find_near_raw_matches(item.normalized_title, raw_real_items)
        meeting_date = _parse_meeting_date(item.meeting_date)
        is_recent = meeting_date is not None and meeting_date >= cutoff

        payload = {
            "document_id": item.document_id,
            "title": item.title,
            "meeting_date": item.meeting_date,
            "notes_source": item.notes_source,
            "transcript_source": item.transcript_source,
            "related_raw_titles": near_raw_matches,
        }

        has_exact_raw_title = item.normalized_title in raw_by_title
        repeated_export_family = export_title_counts[item.normalized_title] > 1
        has_near_duplicate = (
            bool(near_raw_matches)
            and not (
                len(near_raw_matches) == 1
                and near_raw_matches[0]["score"] == 1.0
                and has_exact_raw_title
            )
        )

        if has_exact_raw_title and not repeated_export_family:
            likely_present.append(
                {
                    **payload,
                    "classification": "likely_present_exact_title",
                    "reason": "single export item shares exact normalized title with one raw page",
                }
            )
            continue

        if has_exact_raw_title or repeated_export_family or has_near_duplicate:
            target = batch1_recent_ambiguous if is_recent else historic_ambiguous
            reasons: list[str] = []
            if has_exact_raw_title:
                reasons.append("exact_title_already_exists_in_raw")
            if repeated_export_family:
                reasons.append("same_normalized_title_appears_multiple_times_in_cache")
            if has_near_duplicate:
                reasons.append("near_duplicate_title_detected_against_raw")
            target.append(
                {
                    **payload,
                    "classification": "ambiguous",
                    "reason": ", ".join(reasons),
                }
            )
            continue

        target = batch1_recent_unique if is_recent else historic_unique
        target.append(
            {
                **payload,
                "classification": "missing_unique",
                "reason": "not present in raw by exact or near title",
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "recent_cutoff": cutoff.isoformat(),
        "cache_summary": {
            "scanned": len(exports)
            + int(raw_snapshot.get("skipped_unusable_placeholder", 0)),
            "exportable_count": len(exports),
        },
        "raw_summary": {
            "raw_total_count": len(raw_snapshot["all_items"]),
            "raw_real_count": len(raw_real_items),
            "raw_smoke_count": len(raw_snapshot["smoke_items"]),
        },
        "gap_summary": {
            "likely_present_count": len(likely_present),
            "batch1_recent_unique_count": len(batch1_recent_unique),
            "batch1_recent_ambiguous_count": len(batch1_recent_ambiguous),
            "historic_unique_count": len(historic_unique),
            "historic_ambiguous_count": len(historic_ambiguous),
        },
        "raw_real_items": [
            {
                "page_id": item["page_id"],
                "title": item["title"],
                "date": (item["properties"].get("Fecha") or {}).get("start")
                if isinstance(item["properties"].get("Fecha"), dict)
                else item["properties"].get("Fecha"),
                "status": item["properties"].get("Estado"),
                "artifact_url": item["properties"].get("URL artefacto"),
                "url": item["url"],
            }
            for item in raw_real_items
        ],
        "likely_present": likely_present,
        "batch1_recent_unique": batch1_recent_unique,
        "batch1_recent_ambiguous": batch1_recent_ambiguous,
        "historic_unique": historic_unique,
        "historic_ambiguous": historic_ambiguous,
        "notes": [
            "Historical raw Notion pages do not reliably persist Granola document_id, so exact 1:1 reconciliation remains fuzzy for repeated titles.",
            "This report is read-only and prioritizes batch safety over aggressive matching.",
        ],
    }


def build_report(*, cache_path: Path, max_items: int, recent_days: int, enable_private_api_hydration: bool) -> dict[str, Any]:
    export_summary = _load_export_items(
        cache_path=cache_path,
        limit=None,
        enable_private_api_hydration=enable_private_api_hydration,
    )
    raw_snapshot = _load_raw_items(max_items=max_items)
    raw_snapshot["skipped_unusable_placeholder"] = export_summary.get("scanned", 0) - len(export_summary["exports"])
    report = _classify_gap(
        export_summary["exports"],
        raw_snapshot,
        recent_days=recent_days,
    )
    report["cache_summary"] = {
        "cache_path": str(cache_path),
        "scanned": export_summary.get("scanned", 0),
        "exportable_count": len(export_summary["exports"]),
        "skipped_unusable": export_summary.get("skipped_unusable", 0),
        "skipped_reason_counts": export_summary.get("skipped_reason_counts", {}),
        "private_api_hydration": enable_private_api_hydration,
    }
    report["raw_summary"] |= {
        "database_id": raw_snapshot["database_id"],
        "database_title": raw_snapshot["title"],
        "database_url": raw_snapshot["url"],
    }
    return report


def _print_human(report: dict[str, Any]) -> None:
    cache = report["cache_summary"]
    raw = report["raw_summary"]
    gap = report["gap_summary"]
    print(
        "cache_scanned={scanned} exportable={exportable_count} skipped_unusable={skipped_unusable}".format(
            **cache
        )
    )
    print(
        "raw_total={raw_total_count} raw_real={raw_real_count} raw_smoke={raw_smoke_count}".format(
            **raw
        )
    )
    print(
        "likely_present={likely_present_count} batch1_recent_unique={batch1_recent_unique_count} batch1_recent_ambiguous={batch1_recent_ambiguous_count} historic_unique={historic_unique_count} historic_ambiguous={historic_ambiguous_count}".format(
            **gap
        )
    )
    print("")
    sections = (
        ("Batch 1 — Recent Unique", report["batch1_recent_unique"]),
        ("Batch 1 — Recent Ambiguous", report["batch1_recent_ambiguous"]),
        ("Historic Unique", report["historic_unique"]),
        ("Historic Ambiguous", report["historic_ambiguous"]),
    )
    for title, items in sections:
        print(f"## {title} ({len(items)})")
        for item in items:
            print(f"- {item['meeting_date']} :: {item['title']} :: {item['document_id']}")
            if item["reason"]:
                print(f"  reason: {item['reason']}")
            for raw in item.get("related_raw_titles", [])[:3]:
                print(
                    f"  related_raw: {raw['title']} :: {raw['page_id']} :: score={raw['score']}"
                )
        print("")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Granola cache exportables against Notion raw DB")
    parser.add_argument(
        "--cache-path",
        default=str(Path(os.environ.get("APPDATA", "")) / "Granola" / "cache-v6.json"),
        help="Path to Granola cache-v6.json",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=200,
        help="Maximum number of raw rows to read from Notion",
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        default=7,
        help="Window for Batch 1 recent prioritization",
    )
    parser.add_argument(
        "--no-private-api-hydration",
        action="store_true",
        help="Disable Granola private API hydration",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON",
    )
    args = parser.parse_args()

    report = build_report(
        cache_path=Path(args.cache_path),
        max_items=max(1, min(int(args.max_items), 500)),
        recent_days=max(1, int(args.recent_days)),
        enable_private_api_hydration=not args.no_private_api_hydration,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    _print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
