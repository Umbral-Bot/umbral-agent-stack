#!/usr/bin/env python3
"""
Borra residuos del Kanban en Notion: bloques añadidos y subpágina duplicada.

Archiva:
1. Bloques "Tareas Umbral — Kanban" y bookmark en NOTION_DASHBOARD_PAGE_ID
2. La subpágina "Dashboard Rick — Kanban" (3145f443-fb5c-810a-bc2b-cdd4b4337ab3) si existe

Requiere: NOTION_API_KEY, NOTION_DASHBOARD_PAGE_ID en env.
"""
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

import httpx

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DASHBOARD_PAGE_ID = os.environ.get("NOTION_DASHBOARD_PAGE_ID")
NOTION_VERSION = os.environ.get("NOTION_API_VERSION", "2022-06-28")
NOTION_BASE = "https://api.notion.com/v1"
SUBPAGE_ID = "3145f443-fb5c-810a-bc2b-cdd4b4337ab3"  # subpágina "Dashboard Rick — Kanban"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def main() -> int:
    if not NOTION_API_KEY:
        print("NOTION_API_KEY requerido.", file=sys.stderr)
        return 1

    archived = 0

    # 1. Archivar subpágina creada
    try:
        r = httpx.patch(
            f"{NOTION_BASE}/pages/{SUBPAGE_ID}",
            headers=HEADERS,
            json={"archived": True},
            timeout=10,
        )
        if r.status_code == 200:
            print(f"Subpágina {SUBPAGE_ID[:8]}... archivada.")
            archived += 1
        else:
            print(f"Subpágina: {r.status_code} (puede no existir)")
    except Exception as e:
        print(f"Subpágina: {e}")

    # 2. Archivar bloques "Tareas Umbral — Kanban" en Dashboard
    if NOTION_DASHBOARD_PAGE_ID:
        try:
            next_cursor = None
            while True:
                params = {"page_size": 100}
                if next_cursor:
                    params["start_cursor"] = next_cursor
                r = httpx.get(
                    f"{NOTION_BASE}/blocks/{NOTION_DASHBOARD_PAGE_ID}/children",
                    headers=HEADERS,
                    params=params,
                    timeout=10,
                )
                if r.status_code != 200:
                    print(f"Dashboard blocks: {r.status_code}")
                    break
                data = r.json()
                for block in data.get("results", []):
                    if block.get("archived"):
                        continue
                    bid = block.get("id")
                    blk_type = block.get("type", "")
                    content = (block.get(blk_type) or {}).get("rich_text", []) if blk_type else []
                    text = "".join(t.get("plain_text", "") for t in content) if content else ""
                    if "Tareas Umbral" in text or (blk_type == "bookmark" and "notion.so" in str(block.get("bookmark", {}).get("url", ""))):
                        r2 = httpx.patch(
                            f"{NOTION_BASE}/blocks/{bid}",
                            headers=HEADERS,
                            json={"archived": True},
                            timeout=5,
                        )
                        if r2.status_code == 200:
                            print(f"Bloque {bid[:8]}... archivado ({blk_type})")
                            archived += 1
                next_cursor = data.get("next_cursor")
                if not next_cursor:
                    break
        except Exception as e:
            print(f"Dashboard blocks: {e}")

    print(f"\nListo. {archived} elemento(s) archivado(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
