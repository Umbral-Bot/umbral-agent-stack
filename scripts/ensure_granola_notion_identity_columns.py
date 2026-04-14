#!/usr/bin/env python3
"""
Ensure visible Notion identity columns exist for the Granola pipeline surfaces.

Adds, when missing:
- "ID interno Notion" as rich_text
- "Creado en Notion" as created_time

Then backfills "ID interno Notion" with the actual Notion page UUID for
existing rows.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import env_loader

env_loader.load()

from worker import config, notion_client


IDENTITY_ID_FIELD = "ID interno Notion"
IDENTITY_CREATED_FIELD = "Creado en Notion"


def _plain_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        if value.get("type") == "rich_text":
            parts: list[str] = []
            for item in value.get("rich_text") or []:
                if isinstance(item, dict):
                    parts.append(
                        item.get("plain_text", item.get("text", {}).get("content", ""))
                    )
            return "".join(parts).strip()
        if value.get("type") == "title":
            parts: list[str] = []
            for item in value.get("title") or []:
                if isinstance(item, dict):
                    parts.append(
                        item.get("plain_text", item.get("text", {}).get("content", ""))
                    )
            return "".join(parts).strip()
    return ""


def _target_databases() -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    if config.NOTION_GRANOLA_DB_ID:
        targets.append(("granola_raw", config.NOTION_GRANOLA_DB_ID))
    curated_db_id = config.get_notion_session_capitalizable_db_id()
    if curated_db_id:
        targets.append(("curated_sessions", curated_db_id))
    if config.NOTION_HUMAN_TASKS_DB_ID:
        targets.append(("human_tasks", config.NOTION_HUMAN_TASKS_DB_ID))
    return targets


def ensure_columns(database_id: str) -> dict[str, str]:
    snapshot = notion_client.read_database(database_id, max_items=1)
    schema = snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError(f"Could not read schema for database {database_id}")

    missing: dict[str, Any] = {}
    if IDENTITY_ID_FIELD not in schema:
        missing[IDENTITY_ID_FIELD] = {"rich_text": {}}
    if IDENTITY_CREATED_FIELD not in schema:
        missing[IDENTITY_CREATED_FIELD] = {"created_time": {}}

    if missing:
        notion_client.update_database_properties(database_id, missing)
        snapshot = notion_client.read_database(database_id, max_items=1)
        schema = snapshot.get("schema") or {}
        if not isinstance(schema, dict):
            raise RuntimeError(f"Could not re-read schema for database {database_id}")

    return schema


def backfill_page_ids(database_id: str, schema: dict[str, str]) -> dict[str, Any]:
    field_type = str(schema.get(IDENTITY_ID_FIELD) or "").strip()
    if field_type != "rich_text":
        return {"updated": 0, "scanned": 0, "skipped": True}

    updated = 0
    scanned = 0
    for row in notion_client.query_database(database_id):
        scanned += 1
        page_id = str(row.get("id") or "").strip()
        if not page_id:
            continue
        current = _plain_text((row.get("properties") or {}).get(IDENTITY_ID_FIELD))
        if current == page_id:
            continue
        notion_client.update_page_properties(
            page_id,
            properties={
                IDENTITY_ID_FIELD: {
                    "rich_text": [{"text": {"content": page_id}}]
                }
            },
        )
        updated += 1
    return {"updated": updated, "scanned": scanned, "skipped": False}


def main() -> int:
    results: list[dict[str, Any]] = []
    for label, database_id in _target_databases():
        schema = ensure_columns(database_id)
        backfill = backfill_page_ids(database_id, schema)
        results.append(
            {
                "label": label,
                "database_id": database_id,
                "has_id_field": IDENTITY_ID_FIELD in schema,
                "has_created_field": IDENTITY_CREATED_FIELD in schema,
                **backfill,
            }
        )

    for item in results:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
