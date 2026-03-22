#!/usr/bin/env python3
"""
Provisiona y mantiene la base `Bandeja Puente` bajo OpenClaw.

- Reutiliza una DB existente si ya cuelga de OpenClaw con ese título.
- Si existe, actualiza su schema mínimo operativo.
- Si no existe, crea una nueva con el schema esperado por OpenClaw.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from worker import config, notion_client


def _headers() -> dict[str, str]:
    return notion_client._headers()  # type: ignore[attr-defined]


def _api(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.request(
            method,
            f"{notion_client.NOTION_BASE_URL}{path}",
            headers=_headers(),
            json=payload,
        )
    return notion_client._check_response(resp, path)  # type: ignore[attr-defined]


def _list_children(page_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    next_cursor: str | None = None
    while True:
        params: dict[str, Any] = {"page_size": 100}
        if next_cursor:
            params["start_cursor"] = next_cursor
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{notion_client.NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=_headers(),
                params=params,
            )
        data = notion_client._check_response(resp, "list children")  # type: ignore[attr-defined]
        results.extend(data.get("results", []))
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
    return results


def _find_child_database_id(page_id: str, title: str) -> str | None:
    wanted = title.strip().lower()
    for block in _list_children(page_id):
        if block.get("type") != "child_database":
            continue
        current = ((block.get("child_database") or {}).get("title") or "").strip().lower()
        if current == wanted:
            return block.get("id")
    return None


def _bridge_properties() -> dict[str, Any]:
    return {
        "Ítem": {"title": {}},
        "Estado": {
            "status": {
                "options": [
                    {"name": "Nuevo", "color": "blue"},
                    {"name": "En curso", "color": "yellow"},
                    {"name": "Esperando", "color": "orange"},
                    {"name": "Resuelto", "color": "green"},
                ]
            }
        },
        "Último movimiento": {"date": {}},
        "Notas": {"rich_text": {}},
        "Proyecto": {"rich_text": {}},
        "Prioridad": {
            "select": {
                "options": [
                    {"name": "Alta", "color": "red"},
                    {"name": "Media", "color": "yellow"},
                    {"name": "Baja", "color": "gray"},
                ]
            }
        },
        "Origen": {
            "select": {
                "options": [
                    {"name": "Rick", "color": "blue"},
                    {"name": "David", "color": "purple"},
                    {"name": "Sistema", "color": "pink"},
                    {"name": "Control Room", "color": "brown"},
                    {"name": "Proyecto", "color": "green"},
                    {"name": "Entregable", "color": "orange"},
                    {"name": "Manual", "color": "gray"},
                ]
            }
        },
        "Siguiente acción": {"rich_text": {}},
        "Link": {"url": {}},
    }


def _ensure_bridge_schema(database_id: str) -> None:
    _api(
        "PATCH",
        f"/databases/{database_id}",
        {
            "properties": _bridge_properties(),
        },
    )


def provision_bridge_db() -> dict[str, Any]:
    parent_page_id = config.NOTION_CONTROL_ROOM_PAGE_ID
    if not parent_page_id:
        raise RuntimeError("NOTION_CONTROL_ROOM_PAGE_ID not configured")

    existing_id = _find_child_database_id(parent_page_id, "Bandeja Puente")
    if existing_id:
        _ensure_bridge_schema(existing_id)
        return {"created": False, "database_id": existing_id, "title": "Bandeja Puente", "schema_updated": True}

    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "Bandeja Puente"}}],
        "properties": _bridge_properties(),
    }
    db = _api("POST", "/databases", payload)
    return {
        "created": True,
        "database_id": db.get("id"),
        "url": db.get("url", ""),
        "title": "Bandeja Puente",
        "schema_updated": True,
    }


def main() -> int:
    result = provision_bridge_db()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
