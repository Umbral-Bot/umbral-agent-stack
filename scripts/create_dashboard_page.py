#!/usr/bin/env python3
"""
Crea una página "Dashboard Rick" con el enlace al Kanban, y la añade como subpágina
de la base de datos indicada. La nueva página será visible como subpágina/fila.

Requiere: NOTION_API_KEY, NOTION_TASKS_DB_ID (Kanban), y una de:
  - NOTION_MAIN_DB_ID (base de datos donde crear la página)
  - O NOTION_DASHBOARD_PARENT_PAGE_ID (página padre)

Salida: imprime el ID de la nueva página. Añadir a env como NOTION_DASHBOARD_PAGE_ID.
"""
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

import httpx

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_TASKS_DB_ID = os.environ.get("NOTION_TASKS_DB_ID")
NOTION_MAIN_DB_ID = os.environ.get("NOTION_MAIN_DB_ID", "3145f443fb5c80e189b1da79122feeb0")
NOTION_VERSION = os.environ.get("NOTION_API_VERSION", "2022-06-28")
NOTION_BASE = "https://api.notion.com/v1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def main() -> int:
    if not NOTION_API_KEY or not NOTION_TASKS_DB_ID:
        print("NOTION_API_KEY y NOTION_TASKS_DB_ID requeridos.", file=sys.stderr)
        return 1

    kanban_url = f"https://www.notion.so/{NOTION_TASKS_DB_ID.replace('-', '')}"

    # 1. Obtener schema de la base de datos
    r_db = httpx.get(
        f"{NOTION_BASE}/databases/{NOTION_MAIN_DB_ID}",
        headers=HEADERS,
        timeout=10,
    )
    if r_db.status_code != 200:
        print(f"Error al obtener DB: {r_db.status_code} {r_db.text[:300]}", file=sys.stderr)
        return 2

    props = r_db.json().get("properties", {})
    title_prop = None
    for name, p in props.items():
        if p.get("type") == "title":
            title_prop = name
            break
    if not title_prop:
        print("La base de datos no tiene propiedad title.", file=sys.stderr)
        return 2

    # 2. Crear nueva página (fila) en la base de datos
    page_props = {title_prop: {"title": [{"text": {"content": "Dashboard Rick — Kanban"}}]}}
    r_page = httpx.post(
        f"{NOTION_BASE}/pages",
        headers=HEADERS,
        json={
            "parent": {"type": "database_id", "database_id": NOTION_MAIN_DB_ID},
            "properties": page_props,
        },
        timeout=15,
    )
    if r_page.status_code != 200:
        print(f"Error al crear página: {r_page.status_code} {r_page.text[:400]}", file=sys.stderr)
        return 2

    new_page_id = r_page.json()["id"]
    new_url = r_page.json().get("url", "")

    # 3. Añadir bloques (heading + bookmark) a la nueva página
    blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Tareas Umbral — Kanban"}}]},
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "Enlace directo: ", "link": None},
                    },
                    {
                        "type": "text",
                        "text": {"content": "Abrir Kanban", "link": {"url": kanban_url}},
                    },
                ]
            },
        },
        {
            "object": "block",
            "type": "bookmark",
            "bookmark": {"url": kanban_url},
        },
    ]
    r_blocks = httpx.patch(
        f"{NOTION_BASE}/blocks/{new_page_id}/children",
        headers=HEADERS,
        json={"children": blocks},
        timeout=15,
    )
    if r_blocks.status_code != 200:
        print(f"Página creada pero error al añadir bloques: {r_blocks.status_code}", file=sys.stderr)

    print(f"Página creada: {new_page_id}")
    print(f"URL: {new_url}")
    print("")
    print("Añadir a ~/.config/openclaw/env:")
    print(f"  NOTION_DASHBOARD_PAGE_ID={new_page_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
