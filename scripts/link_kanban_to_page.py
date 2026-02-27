#!/usr/bin/env python3
"""
Añade un enlace al Kanban de Tareas Umbral en una página de Notion.

Ejecutar una vez. Requiere:
  - NOTION_API_KEY
  - NOTION_TASKS_DB_ID (Kanban)
  - TARGET_PAGE_ID (página donde añadir el enlace; default: NOTION_DASHBOARD_PAGE_ID)

El script añade un bloque con enlace directo al Kanban.

Uso:
  export NOTION_API_KEY=... NOTION_TASKS_DB_ID=...
  export TARGET_PAGE_ID=3145f443fb5c80e189b1da79122feeb0   # opcional
  python scripts/link_kanban_to_page.py
"""
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

import httpx

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_TASKS_DB_ID = os.environ.get("NOTION_TASKS_DB_ID")
TARGET_PAGE_ID = os.environ.get("TARGET_PAGE_ID") or os.environ.get("NOTION_DASHBOARD_PAGE_ID")
NOTION_VERSION = os.environ.get("NOTION_API_VERSION", "2022-06-28")
NOTION_BASE = "https://api.notion.com/v1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def main() -> int:
    if not NOTION_API_KEY or not NOTION_TASKS_DB_ID or not TARGET_PAGE_ID:
        print("NOTION_API_KEY, NOTION_TASKS_DB_ID y TARGET_PAGE_ID (o NOTION_DASHBOARD_PAGE_ID) requeridos.", file=sys.stderr)
        return 1

    kanban_url = f"https://www.notion.so/{NOTION_TASKS_DB_ID.replace('-', '')}"

    blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Tareas Umbral — Kanban"}}]},
        },
        {
            "object": "block",
            "type": "bookmark",
            "bookmark": {"url": kanban_url},
        },
    ]

    try:
        r = httpx.patch(
            f"{NOTION_BASE}/blocks/{TARGET_PAGE_ID}/children",
            headers=HEADERS,
            json={"children": blocks},
            timeout=15,
        )
        r.raise_for_status()
        print(f"Enlace añadido a la página {TARGET_PAGE_ID[:8]}...")
        print(f"Kanban: {kanban_url}")
        return 0
    except httpx.HTTPStatusError as e:
        print(f"Error Notion API ({e.response.status_code}): {e.response.text[:400]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
