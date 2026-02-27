#!/usr/bin/env python3
"""
Crea la base de datos "Tareas Umbral" en Notion para el Kanban de seguimiento.

Ejecutar una vez. Requiere:
  - NOTION_API_KEY
  - NOTION_TASKS_PARENT_PAGE_ID (página donde crear la DB; puede ser NOTION_DASHBOARD_PAGE_ID o NOTION_CONTROL_ROOM_PAGE_ID)

Salida: imprime el ID de la DB. Añadirlo a ~/.config/openclaw/env como NOTION_TASKS_DB_ID.

Uso:
  cd ~/umbral-agent-stack && source .venv/bin/activate
  export NOTION_API_KEY=... NOTION_TASKS_PARENT_PAGE_ID=...
  python scripts/setup_notion_tasks_db.py
"""

import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import httpx

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_PARENT = os.environ.get("NOTION_TASKS_PARENT_PAGE_ID") or os.environ.get("NOTION_DASHBOARD_PAGE_ID") or os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID")
NOTION_VERSION = os.environ.get("NOTION_API_VERSION", "2022-06-28")
NOTION_BASE = "https://api.notion.com/v1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def main() -> int:
    if not NOTION_API_KEY:
        print("NOTION_API_KEY no definido.", file=sys.stderr)
        return 1
    if not NOTION_PARENT:
        print("NOTION_TASKS_PARENT_PAGE_ID (o NOTION_DASHBOARD_PAGE_ID) no definido.", file=sys.stderr)
        return 1

    # Si NOTION_PARENT es una DB (error 400 al crear), usar workspace
    payload = {
        "title": [{"type": "text", "text": {"content": "Tareas Umbral — Kanban"}}],
        "properties": {
            "Tarea": {"title": {}},
            "Estado": {
                "select": {
                    "options": [
                        {"name": "En cola", "color": "gray"},
                        {"name": "En curso", "color": "blue"},
                        {"name": "Hecho", "color": "green"},
                        {"name": "Bloqueado", "color": "yellow"},
                        {"name": "Fallido", "color": "red"},
                    ]
                }
            },
            "Agente": {
                "select": {
                    "options": [
                        {"name": "marketing", "color": "blue"},
                        {"name": "advisory", "color": "purple"},
                        {"name": "improvement", "color": "green"},
                        {"name": "system", "color": "gray"},
                        {"name": "lab", "color": "orange"},
                    ]
                }
            },
            "Task ID": {"rich_text": {}},
            "Actualizada": {"date": {}},
            "Creada": {"date": {}},
            "Resumen": {"rich_text": {}},
        },
    }

    def create_db(parent_obj):
        return httpx.post(
            f"{NOTION_BASE}/databases",
            headers=HEADERS,
            json={"parent": parent_obj, **payload},
            timeout=15,
        )

    try:
        r = create_db({"type": "page_id", "page_id": NOTION_PARENT})
        err = r.text or ""
        page_id = None
        if r.status_code == 400 and "parented by a database" in err:
            r_search = httpx.post(
                f"{NOTION_BASE}/search",
                headers=HEADERS,
                json={"filter": {"property": "object", "value": "page"}, "page_size": 5},
                timeout=10,
            )
            if r_search.status_code == 200:
                for item in r_search.json().get("results", []):
                    pid = item.get("id")
                    if pid and pid != NOTION_PARENT:
                        r = create_db({"type": "page_id", "page_id": pid})
                        if r.status_code < 400:
                            break
        r.raise_for_status()
        data = r.json()
        db_id = data["id"]
        url = data.get("url", "")
        print(f"Base de datos creada: {db_id}")
        print(f"URL: {url}")
        print("")
        print("Añadir a ~/.config/openclaw/env:")
        print(f"  NOTION_TASKS_DB_ID={db_id}")
        return 0
    except httpx.HTTPStatusError as e:
        print(f"Error Notion API ({e.response.status_code}): {e.response.text[:500]}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
