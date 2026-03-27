#!/usr/bin/env python3
"""List actionable Granola raw pages for promotion planning.

This script inspects the raw Granola DB and the curated sessions DB and classifies
raw pages into:

- candidate
- promoted
- duplicate_of_promoted
- smoke_or_test

It is read-only and intended to support explicit batch planning.
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts import env_loader

env_loader.load()

from worker import config, notion_client


SMOKE_TERMS = (
    "smoke",
    "manual-watcher",
    "manual watcher",
    "watcher-smoke",
    "test",
    "prueba",
)


def _normalize_title(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    ascii_text = text.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(cleaned.split())


def _extract_date_start(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("start") or "").strip()
    return ""


def _extract_raw_key(item: dict[str, Any]) -> tuple[str, str]:
    title = str(item.get("title") or "")
    properties = item.get("properties") or {}
    date = _extract_date_start(properties.get("Fecha"))
    return (_normalize_title(title), date)


def _is_smoke_like_title(title: str) -> bool:
    normalized = _normalize_title(title)
    return any(term in normalized for term in SMOKE_TERMS)


def _classify_raw_items(
    raw_items: list[dict[str, Any]],
    curated_items: list[dict[str, Any]],
) -> dict[str, Any]:
    curated_source_urls = {
        str((item.get("properties") or {}).get("URL fuente") or "").strip()
        for item in curated_items
    }

    raw_group_counts = Counter(_extract_raw_key(item) for item in raw_items)
    promoted_raw_keys = {
        _extract_raw_key(item)
        for item in raw_items
        if str(item.get("url") or "").strip() in curated_source_urls
    }

    results: list[dict[str, Any]] = []
    for item in raw_items:
        title = str(item.get("title") or "")
        url = str(item.get("url") or "").strip()
        properties = item.get("properties") or {}
        date = properties.get("Fecha")
        key = _extract_raw_key(item)

        classification = "candidate"
        reason = ""
        if _is_smoke_like_title(title):
            classification = "smoke_or_test"
            reason = "title_matches_smoke_or_test_pattern"
        elif url in curated_source_urls:
            classification = "promoted"
            reason = "raw_url_present_in_curated_source"
        elif raw_group_counts[key] > 1 and key in promoted_raw_keys:
            classification = "duplicate_of_promoted"
            reason = "duplicate_title_date_group_with_promoted_raw"

        results.append(
            {
                "page_id": item.get("page_id"),
                "title": title,
                "date": date,
                "source": properties.get("Fuente"),
                "status": properties.get("Estado"),
                "url": url,
                "classification": classification,
                "reason": reason,
            }
        )

    counts = Counter(item["classification"] for item in results)
    return {
        "summary": {
            "raw_count": len(raw_items),
            "curated_count": len(curated_items),
            "candidate_count": counts.get("candidate", 0),
            "promoted_count": counts.get("promoted", 0),
            "duplicate_of_promoted_count": counts.get("duplicate_of_promoted", 0),
            "smoke_or_test_count": counts.get("smoke_or_test", 0),
        },
        "items": results,
    }


def run() -> dict[str, Any]:
    if not config.NOTION_GRANOLA_DB_ID:
        raise RuntimeError("NOTION_GRANOLA_DB_ID not configured")
    if not config.NOTION_CURATED_SESSIONS_DB_ID:
        raise RuntimeError("NOTION_CURATED_SESSIONS_DB_ID not configured")

    raw_items = notion_client.read_database(config.NOTION_GRANOLA_DB_ID, max_items=200).get("items", [])
    curated_items = notion_client.read_database(config.NOTION_CURATED_SESSIONS_DB_ID, max_items=200).get("items", [])
    return _classify_raw_items(raw_items, curated_items)


def main() -> int:
    parser = argparse.ArgumentParser(description="List Granola raw promotion candidates")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    result = run()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    summary = result["summary"]
    print(
        "raw={raw_count} curated={curated_count} candidates={candidate_count} promoted={promoted_count} duplicates={duplicate_of_promoted_count} smoke={smoke_or_test_count}".format(
            **summary
        )
    )
    for item in result["items"]:
        print(
            f"- [{item['classification']}] {item['title']} :: {item['page_id']} :: {json.dumps(item['date'], ensure_ascii=False)}"
        )
        if item["reason"]:
            print(f"  reason: {item['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
