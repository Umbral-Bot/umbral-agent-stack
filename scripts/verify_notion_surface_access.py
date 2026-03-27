"""
Verify visibility of configured Notion database surfaces for the Worker token.

This script performs read-only `retrieve database` checks against the IDs
configured in the environment and reports whether each surface is:

- configured and reachable
- not configured
- configured but not accessible to the current integration

Usage:
    python scripts/verify_notion_surface_access.py
    python scripts/verify_notion_surface_access.py --json
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import httpx

from worker import config

NOTION_BASE_URL = "https://api.notion.com/v1"
TIMEOUT = 30.0


def _headers() -> dict[str, str]:
    api_key, _ = config.require_notion_core()
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": config.NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def _title_from_database(payload: dict[str, Any]) -> str:
    return "".join(rt.get("plain_text", "") for rt in payload.get("title", []))


def _probe_database(client: httpx.Client, db_id: str) -> dict[str, Any]:
    resp = client.get(f"{NOTION_BASE_URL}/databases/{db_id}", headers=_headers())
    if resp.status_code == 404:
        return {
            "ok": False,
            "status": "not_shared_or_not_found",
            "db_id": db_id,
            "message": resp.json().get("message", resp.text[:300]),
        }
    if resp.status_code >= 400:
        return {
            "ok": False,
            "status": "error",
            "db_id": db_id,
            "message": resp.text[:300],
        }
    data = resp.json()
    props = data.get("properties") or {}
    return {
        "ok": True,
        "status": "reachable",
        "db_id": data.get("id", db_id),
        "title": _title_from_database(data),
        "property_count": len(props),
        "properties": list(props.keys()),
    }


def build_surface_map() -> dict[str, str | None]:
    return {
        "granola_raw": config.NOTION_GRANOLA_DB_ID,
        "technical_tasks": config.NOTION_TASKS_DB_ID,
        "technical_projects": config.NOTION_PROJECTS_DB_ID,
        "bridge": config.NOTION_BRIDGE_DB_ID,
        "deliverables": config.NOTION_DELIVERABLES_DB_ID,
        "curated_sessions": config.NOTION_CURATED_SESSIONS_DB_ID,
        "human_tasks": config.NOTION_HUMAN_TASKS_DB_ID,
        "commercial_projects": config.NOTION_COMMERCIAL_PROJECTS_DB_ID,
    }


def run() -> dict[str, Any]:
    surfaces = build_surface_map()
    results: dict[str, Any] = {}
    with httpx.Client(timeout=TIMEOUT) as client:
        for name, db_id in surfaces.items():
            if not db_id:
                results[name] = {"ok": False, "status": "not_configured"}
                continue
            results[name] = _probe_database(client, db_id)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print JSON output")
    args = parser.parse_args()

    results = run()
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    for name, result in results.items():
        status = result.get("status")
        print(f"[{name}] {status}")
        if result.get("db_id"):
            print(f"  db_id: {result['db_id']}")
        if result.get("title"):
            print(f"  title: {result['title']}")
        if result.get("property_count") is not None:
            print(f"  property_count: {result['property_count']}")
        if result.get("message"):
            print(f"  message: {result['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
