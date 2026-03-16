#!/usr/bin/env python3
"""
Renderiza la pagina OpenClaw como panel operativo humano.

Mantiene:
- Dashboard Rick = dashboard tecnico
- OpenClaw = panel humano de lectura/decision

Uso:
  source ~/.config/openclaw/env
  .venv/bin/python scripts/openclaw_panel_vps.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from worker import config, notion_client
from worker.notion_client import (
    _block_bulleted,
    _block_callout,
    _block_divider,
    _block_heading2,
    _block_heading3,
    _block_paragraph,
)

OPENCLAW_PAGE_ID = config.NOTION_CONTROL_ROOM_PAGE_ID
DASHBOARD_PAGE_ID = config.NOTION_DASHBOARD_PAGE_ID


def _api_client() -> httpx.Client:
    return httpx.Client(timeout=30.0)


def _headers() -> dict[str, str]:
    return notion_client._headers()  # type: ignore[attr-defined]


def _list_children(page_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    next_cursor: str | None = None
    with _api_client() as client:
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if next_cursor:
                params["start_cursor"] = next_cursor
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


def _extract_text(block: dict[str, Any]) -> str:
    block_type = block.get("type", "")
    container = block.get(block_type, {})
    if not isinstance(container, dict):
        return ""
    if block_type == "child_page":
        return str(container.get("title", ""))
    if block_type == "child_database":
        return str(container.get("title", ""))
    rich = container.get("rich_text") or container.get("title") or []
    if isinstance(rich, list):
        return "".join(
            item.get("plain_text", item.get("text", {}).get("content", ""))
            for item in rich
            if isinstance(item, dict)
        )
    return ""


def _delete_blocks(block_ids: list[str]) -> None:
    if not block_ids:
        return
    with _api_client() as client:
        for block_id in block_ids:
            client.patch(
                f"{notion_client.NOTION_BASE_URL}/blocks/{block_id}",
                headers=_headers(),
                json={"in_trash": True},
            )


def _update_block_text(block: dict[str, Any], text: str, emoji: str | None = None) -> None:
    block_id = block["id"]
    block_type = block["type"]
    container = dict(block.get(block_type, {}) or {})
    payload: dict[str, Any] = {block_type: container}

    if block_type in {"heading_1", "heading_2", "heading_3", "paragraph", "bulleted_list_item"}:
        payload[block_type]["rich_text"] = [{"type": "text", "text": {"content": text[:2000]}}]
    elif block_type == "callout":
        payload[block_type]["rich_text"] = [{"type": "text", "text": {"content": text[:2000]}}]
        if emoji:
            payload[block_type]["icon"] = {"type": "emoji", "emoji": emoji}
    else:
        raise ValueError(f"Unsupported block type for text update: {block_type}")

    with _api_client() as client:
        resp = client.patch(
            f"{notion_client.NOTION_BASE_URL}/blocks/{block_id}",
            headers=_headers(),
            json=payload,
        )
        notion_client._check_response(resp, "update block text")  # type: ignore[attr-defined]


def _insert_after(parent_page_id: str, after_block_id: str, blocks: list[dict[str, Any]]) -> None:
    if not blocks:
        return
    with _api_client() as client:
        for i in range(0, len(blocks), 100):
            chunk = blocks[i:i + 100]
            body: dict[str, Any] = {"children": chunk}
            if i == 0:
                body["after"] = after_block_id
            resp = client.patch(
                f"{notion_client.NOTION_BASE_URL}/blocks/{parent_page_id}/children",
                headers=_headers(),
                json=body,
            )
            notion_client._check_response(resp, "insert blocks after")  # type: ignore[attr-defined]


def _plain(prop: dict[str, Any]) -> Any:
    if not isinstance(prop, dict):
        return None
    typ = prop.get("type")
    if typ == "title":
        return "".join(x.get("plain_text", "") for x in prop.get("title", []))
    if typ == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
    if typ == "select":
        return (prop.get("select") or {}).get("name")
    if typ == "status":
        return (prop.get("status") or {}).get("name")
    if typ == "date":
        return (prop.get("date") or {}).get("start")
    if typ == "relation":
        return [x.get("id") for x in prop.get("relation", [])]
    if typ == "number":
        return prop.get("number")
    if typ == "url":
        return prop.get("url")
    return None


def _query_db(database_id: str, filter_payload: dict[str, Any] | None = None, page_size: int = 50) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    next_cursor: str | None = None
    with _api_client() as client:
        while True:
            body: dict[str, Any] = {"page_size": page_size}
            if filter_payload:
                body["filter"] = filter_payload
            if next_cursor:
                body["start_cursor"] = next_cursor
            resp = client.post(
                f"{notion_client.NOTION_BASE_URL}/databases/{database_id}/query",
                headers=_headers(),
                json=body,
            )
            data = notion_client._check_response(resp, "query db")  # type: ignore[attr-defined]
            results.extend(data.get("results", []))
            next_cursor = data.get("next_cursor")
            if not next_cursor:
                break
    return results


def _page_url(page_id: str) -> str:
    compact = page_id.replace("-", "")
    return f"https://www.notion.so/{compact}"


def _summarize_text(text: str, limit: int = 140) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _build_operational_snapshot() -> dict[str, Any]:
    deliverables_raw = _query_db(config.NOTION_DELIVERABLES_DB_ID)
    deliverables: list[dict[str, Any]] = []
    for row in deliverables_raw:
        props = row.get("properties", {})
        review = _plain(props.get("Estado revision", {})) or ""
        if review not in {"Pendiente revision", "Aprobado con ajustes"}:
            continue
        deliverables.append(
            {
                "id": row["id"],
                "name": _plain(props.get("Nombre", {})) or "Sin nombre",
                "review": review,
                "project_ids": _plain(props.get("Proyecto", {})) or [],
                "due_date": _plain(props.get("Fecha limite sugerida", {})),
                "next_action": _plain(props.get("Siguiente accion", {})) or "",
                "date": _plain(props.get("Fecha", {})),
            }
        )

    projects_raw = _query_db(config.NOTION_PROJECTS_DB_ID)
    projects: list[dict[str, Any]] = []
    for row in projects_raw:
        props = row.get("properties", {})
        name = _plain(props.get("Nombre", {})) or "Sin nombre"
        blockers = (_plain(props.get("Bloqueos", {})) or "").strip()
        next_action = (_plain(props.get("Siguiente acción", {})) or "").strip()
        tasks_rel = _plain(props.get("Tareas", {})) or []
        open_issues = _plain(props.get("Issues abiertas", {})) or 0
        if blockers or open_issues or not tasks_rel:
            projects.append(
                {
                    "id": row["id"],
                    "name": name,
                    "blockers": blockers,
                    "next_action": next_action,
                    "open_issues": open_issues,
                    "task_count": len(tasks_rel),
                }
            )

    bridge_raw = _query_db("8496ee73-6c7d-43a3-89cf-b9c8825b5dfc")
    bridge_live: list[dict[str, Any]] = []
    for row in bridge_raw:
        props = row.get("properties", {})
        title = _plain(props.get("Ítem", {})) or "Sin titulo"
        status = _plain(props.get("Estado", {})) or ""
        notes = _plain(props.get("Notas", {})) or ""
        if status != "Resuelto":
            bridge_live.append(
                {
                    "id": row["id"],
                    "title": title,
                    "status": status,
                    "notes": notes,
                    "last_move": _plain(props.get("Último movimiento", {})),
                }
            )

    due_items = sorted(
        [d for d in deliverables if d.get("due_date")],
        key=lambda item: item.get("due_date") or "9999-99-99",
    )[:5]

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "pending_deliverables": deliverables[:6],
        "projects_attention": projects[:6],
        "bridge_live": bridge_live[:6],
        "due_items": due_items,
    }


def _build_panel_blocks(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    blocks.append(_block_heading2("Panel operativo"))
    blocks.append(
        _block_callout(
            f"Actualizado: {snapshot['generated_at']}. "
            "Usa esta seccion para decidir que revisar ahora. "
            "El estado tecnico del stack vive en Dashboard Rick.",
            emoji="🧭",
            color="blue_background",
        )
    )

    blocks.append(_block_heading3("Entregables pendientes de revision"))
    pending = snapshot["pending_deliverables"]
    if pending:
        for item in pending:
            line = f"{item['name']} — {item['review']}"
            if item.get("due_date"):
                line += f" — vence: {item['due_date']}"
            blocks.append(_block_bulleted(line))
            if item.get("next_action"):
                blocks.append(_block_paragraph(f"Siguiente accion: {_summarize_text(item['next_action'])}"))
    else:
        blocks.append(_block_bulleted("No hay entregables pendientes de revision."))

    blocks.append(_block_heading3("Proyectos con bloqueo o drift"))
    projects = snapshot["projects_attention"]
    if projects:
        for project in projects:
            summary = project["blockers"] or project["next_action"] or "Sin detalle registrado."
            blocks.append(
                _block_bulleted(
                    f"{project['name']} — issues abiertas: {project['open_issues']} — tareas ligadas: {project['task_count']}"
                )
            )
            blocks.append(_block_paragraph(_summarize_text(summary)))
    else:
        blocks.append(_block_bulleted("No hay proyectos con bloqueo o drift visibles."))

    blocks.append(_block_heading3("Bandeja viva"))
    bridge = snapshot["bridge_live"]
    if bridge:
        for item in bridge:
            blocks.append(_block_bulleted(f"{item['title']} — {item['status']}"))
            if item.get("notes"):
                blocks.append(_block_paragraph(_summarize_text(item['notes'])))
    else:
        blocks.append(_block_bulleted("No hay items vivos en Bandeja Puente."))

    blocks.append(_block_heading3("Proximos vencimientos"))
    due_items = snapshot["due_items"]
    if due_items:
        for item in due_items:
            blocks.append(_block_bulleted(f"{item['due_date']} — {item['name']}"))
    else:
        blocks.append(_block_bulleted("No hay fechas limite sugeridas proximas."))

    blocks.append(_block_divider())
    return blocks


def refresh_openclaw_panel() -> dict[str, Any]:
    if not OPENCLAW_PAGE_ID:
        raise RuntimeError("NOTION_CONTROL_ROOM_PAGE_ID not configured")

    children = _list_children(OPENCLAW_PAGE_ID)
    if not children:
        raise RuntimeError("OpenClaw page has no blocks")

    first_block = children[0]
    if first_block.get("type") != "callout":
        raise RuntimeError("Expected first OpenClaw block to be a callout")

    resources_heading_index = next(
        (
            idx
            for idx, block in enumerate(children)
            if block.get("type") == "heading_3" and _extract_text(block).strip().lower() == "recursos"
        ),
        None,
    )
    if resources_heading_index is None:
        raise RuntimeError("Could not find 'Recursos' heading in OpenClaw page")

    # Remove everything between the top callout and Recursos.
    stale_ids = [block["id"] for block in children[1:resources_heading_index]]
    _delete_blocks(stale_ids)

    panel_blocks = _build_panel_blocks(_build_operational_snapshot())
    _update_block_text(
        first_block,
        "OpenClaw es el panel operativo humano. Revisa aqui entregables, proyectos y bandeja viva. "
        "Para salud tecnica del stack, abre Dashboard Rick.",
        emoji="🧭",
    )
    _insert_after(OPENCLAW_PAGE_ID, first_block["id"], panel_blocks)

    # Clean old explanatory bullets under "Como leer este dashboard", but preserve databases.
    children = _list_children(OPENCLAW_PAGE_ID)
    for idx, block in enumerate(children):
        if block.get("type") == "heading_3" and _extract_text(block).strip().lower() == "cómo leer este dashboard":
            _update_block_text(block, "Bases operativas")
            delete_ids: list[str] = []
            for follow in children[idx + 1 :]:
                if follow.get("type") in {"child_database", "child_page", "heading_3", "heading_2", "heading_1"}:
                    break
                delete_ids.append(follow["id"])
            _delete_blocks(delete_ids)
            break

    return {"updated": True, "panel_blocks": len(panel_blocks)}


def main() -> int:
    result = refresh_openclaw_panel()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
