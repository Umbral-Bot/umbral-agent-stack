#!/usr/bin/env python3
"""
Mantiene la shell operativa de la pagina OpenClaw.

- Dashboard Rick = dashboard tecnico
- OpenClaw = panel humano resumido

Este script no intenta construir linked views de Notion. Su responsabilidad es:
- refrescar el callout superior,
- refrescar un resumen visual corto,
- dejar tablas compactas de prioridad,
- y preservar la zona inferior de bases operativas.
"""

from __future__ import annotations

import json
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
    _block_callout,
    _block_bulleted,
    _block_column_list,
    _block_divider,
    _block_heading2,
    _block_heading3,
    _block_table,
    _block_toggle,
)

OPENCLAW_PAGE_ID = config.NOTION_CONTROL_ROOM_PAGE_ID
_RESIDUAL_CHILD_PAGE_PREFIXES = (
    "OODA Weekly Report - ",
    "[improvement] Workflow: self_improvement_cycle",
)
_ALLOWED_NAV_CHILD_PAGES = {
    "Dashboard Rick",
}


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


def _is_residual_child_page(block: dict[str, Any]) -> bool:
    if block.get("type") != "child_page":
        return False
    title = _extract_text(block).strip()
    return any(title.startswith(prefix) for prefix in _RESIDUAL_CHILD_PAGE_PREFIXES)


def _is_allowed_nav_child_page(block: dict[str, Any]) -> bool:
    return block.get("type") == "child_page" and _extract_text(block).strip() in _ALLOWED_NAV_CHILD_PAGES


def _archive_pages(page_ids: list[str]) -> None:
    if not page_ids:
        return
    with _api_client() as client:
        for page_id in page_ids:
            resp = client.patch(
                f"{notion_client.NOTION_BASE_URL}/pages/{page_id}",
                headers=_headers(),
                json={"archived": True},
            )
            notion_client._check_response(resp, "archive page")  # type: ignore[attr-defined]


def _delete_blocks(block_ids: list[str]) -> None:
    if not block_ids:
        return
    with _api_client() as client:
        for block_id in block_ids:
            resp = client.patch(
                f"{notion_client.NOTION_BASE_URL}/blocks/{block_id}",
                headers=_headers(),
                json={"in_trash": True},
            )
            if resp.status_code in {400, 404}:
                raw = (resp.text or "").lower()
                if "archived" in raw or "object_not_found" in raw:
                    continue
            notion_client._check_response(resp, "delete block")  # type: ignore[attr-defined]


def _remove_stale_blocks(blocks: list[dict[str, Any]]) -> int:
    child_pages = [block["id"] for block in blocks if block.get("type") == "child_page"]
    deletable_blocks = [
        block["id"]
        for block in blocks
        if block.get("type") not in {"child_page", "child_database"}
    ]
    if child_pages:
        _archive_pages(child_pages)
    if deletable_blocks:
        _delete_blocks(deletable_blocks)
    return len(child_pages) + len(deletable_blocks)


def _update_block_text(block: dict[str, Any], text: str, emoji: str | None = None) -> None:
    block_id = block["id"]
    block_type = block["type"]
    container = dict(block.get(block_type, {}) or {})
    payload: dict[str, Any] = {block_type: container}

    if block_type in {"heading_1", "heading_2", "heading_3", "paragraph"}:
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


def _query_db_optional(
    database_id: str | None,
    *,
    label: str,
    filter_payload: dict[str, Any] | None = None,
    page_size: int = 50,
) -> tuple[list[dict[str, Any]], bool]:
    if not database_id:
        return [], False
    try:
        return _query_db(database_id, filter_payload=filter_payload, page_size=page_size), True
    except RuntimeError as exc:
        print(f"[openclaw-panel] skipping optional database '{label}': {exc}", file=sys.stderr)
        return [], False


_BRIDGE_PRIORITY_ORDER = {"Alta": 0, "Media": 1, "Baja": 2, "": 3}


def _summarize_text(text: str, limit: int = 90) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _metric_color(label: str, count: int, *, bridge_available: bool) -> str:
    if label == "Bandeja":
        if not bridge_available:
            return "yellow_background"
        return "blue_background" if count == 0 else "yellow_background"
    if label == "Vencimientos":
        return "red_background" if count else "green_background"
    if count == 0:
        return "green_background"
    if count >= 3:
        return "red_background"
    return "yellow_background"


def _metric_card(
    label: str,
    count: int,
    hint: str,
    emoji: str,
    *,
    color: str,
    secondary: str | None = None,
) -> list[dict[str, Any]]:
    lines = [label, str(count), hint]
    if secondary:
        lines.append(secondary)
    return [
        _block_callout(
            "\n".join(lines),
            emoji=emoji,
            color=color,
        ),
    ]


def _primary_focus(snapshot: dict[str, Any]) -> dict[str, str]:
    pending = snapshot["pending_deliverables"]
    if pending:
        item = pending[0]
        due = item.get("due_date") or "sin fecha"
        review = item.get("review") or "Pendiente"
        next_action = item.get("next_action") or "Toma una decision de revision y deja la siguiente accion amarrada."
        return {
            "title": "Prioridad inmediata",
            "body": (
                f"Entregable: {item['name']}\n"
                f"Proyecto: {item.get('project_name', 'Sin proyecto')}\n"
                f"Estado: {review} · Vence: {due}\n"
                f"Siguiente paso: {_summarize_text(next_action, 150)}"
            ),
            "emoji": "🎯",
            "color": "red_background" if review == "Pendiente revision" else "yellow_background",
        }

    projects = snapshot["projects_attention"]
    if projects:
        item = projects[0]
        signal = item.get("blockers") or item.get("next_action") or "Sin detalle registrado."
        return {
            "title": "Proyecto que requiere decision",
            "body": (
                f"Proyecto: {item['name']}\n"
                f"Issues abiertas: {item.get('open_issues', 0)} · Tareas: {item.get('task_count', 0)}\n"
                f"Señal dominante: {_summarize_text(signal, 150)}"
            ),
            "emoji": "🧱",
            "color": "yellow_background",
        }

    bridge = snapshot["bridge_live"]
    if bridge:
        item = bridge[0]
        action = item.get("next_action") or item.get("notes") or "Sin siguiente acción registrada."
        return {
            "title": "Coordinacion viva",
            "body": (
                f"Item: {item['title']}\n"
                f"Estado: {item.get('status') or 'Sin estado'} · Proyecto: {item.get('project') or 'Sin proyecto'}\n"
                f"Siguiente accion: {_summarize_text(action, 120)}"
            ),
            "emoji": "📮",
            "color": "blue_background",
        }

    return {
        "title": "Panel despejado",
        "body": "No hay urgencias operativas fuertes.\nUsa este panel para revisar vencimientos y mantener el flujo limpio.",
        "emoji": "✅",
        "color": "green_background",
    }


def _panel_status_blocks(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    summary = snapshot["summary"]
    bridge_state = "disponible" if summary["bridge_available"] else "sin acceso"
    return [
        _block_callout(
            (
                "Estado del panel\n"
                f"Actualizado: {snapshot['generated_at']}\n"
                f"Revision: {summary['pending_deliverables']} · Proyectos: {summary['projects_attention']}\n"
                f"Bandeja Puente: {bridge_state}"
            ),
            emoji="🧭",
            color="blue_background",
        )
    ]


def _usage_guide_block() -> dict[str, Any]:
    return _block_toggle(
        "Como usar este panel",
        [
            _block_bulleted("Empieza por la tarjeta principal: resume la decision con mas impacto ahora."),
            _block_bulleted("Luego revisa Entregables y Proyectos; ahi es donde se decide si algo se aprueba, ajusta o destraba."),
            _block_bulleted("Usa OpenClaw para dirigir. Usa Proyectos, Tareas y Entregables para ejecutar y dejar trazabilidad."),
        ],
    )


def _find_child_database_id(children: list[dict[str, Any]], title: str) -> str | None:
    wanted = title.strip().lower()
    for block in children:
        if block.get("type") != "child_database":
            continue
        if _extract_text(block).strip().lower() == wanted:
            return block.get("id")
    return None


def _build_operational_snapshot(bridge_db_id: str | None = None) -> dict[str, Any]:
    projects_raw = _query_db(config.NOTION_PROJECTS_DB_ID)
    project_name_by_id: dict[str, str] = {}
    for row in projects_raw:
        props = row.get("properties", {})
        project_name_by_id[row["id"]] = _plain(props.get("Nombre", {})) or "Sin nombre"

    deliverables_raw = _query_db(config.NOTION_DELIVERABLES_DB_ID)
    deliverables: list[dict[str, Any]] = []
    for row in deliverables_raw:
        props = row.get("properties", {})
        review = _plain(props.get("Estado revision", {})) or ""
        if review not in {"Pendiente revision", "Aprobado con ajustes"}:
            continue
        project_ids = _plain(props.get("Proyecto", {})) or []
        project_name = project_name_by_id.get(project_ids[0], "Sin proyecto") if project_ids else "Sin proyecto"
        deliverables.append(
            {
                "id": row["id"],
                "name": _plain(props.get("Nombre", {})) or "Sin nombre",
                "project_name": project_name,
                "review": review,
                "due_date": _plain(props.get("Fecha limite sugerida", {})),
                "next_action": _plain(props.get("Siguiente accion", {})) or "",
            }
        )
    deliverables.sort(
        key=lambda item: (
            0 if item["review"] == "Pendiente revision" else 1,
            item.get("due_date") or "9999-99-99",
            item["project_name"],
            item["name"],
        )
    )

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
    projects.sort(
        key=lambda item: (
            0 if item["blockers"] else 1,
            -item["open_issues"],
            item["task_count"],
            item["name"],
        )
    )

    bridge_raw, bridge_available = _query_db_optional(
        bridge_db_id,
        label="Bandeja Puente",
    )
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
                    "project": _plain(props.get("Proyecto", {})) or "",
                    "priority": _plain(props.get("Prioridad", {})) or "",
                    "source": _plain(props.get("Origen", {})) or "",
                    "next_action": _plain(props.get("Siguiente acción", {})) or "",
                    "link": _plain(props.get("Link", {})) or "",
                    "notes": notes,
                    "last_move": _plain(props.get("Último movimiento", {})),
                }
            )
    bridge_live.sort(
        key=lambda item: (
            _BRIDGE_PRIORITY_ORDER.get(str(item.get("priority") or ""), 3),
            -(1 if item.get("status") == "Esperando" else 0),
            item.get("last_move") or "",
        )
    )

    due_items = sorted(
        [d for d in deliverables if d.get("due_date")],
        key=lambda item: item.get("due_date") or "9999-99-99",
    )[:5]

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "summary": {
            "pending_deliverables": len(deliverables),
            "deliverables_adjustments": len([d for d in deliverables if d["review"] == "Aprobado con ajustes"]),
            "projects_attention": len(projects),
            "bridge_live": len(bridge_live),
            "bridge_available": bridge_available,
            "due_items": len(due_items),
        },
        "pending_deliverables": deliverables[:6],
        "projects_attention": projects[:6],
        "bridge_live": bridge_live[:6],
        "due_items": due_items,
    }


def _deliverables_rows(items: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [
            item["name"],
            item.get("project_name", "Sin proyecto"),
            item["review"],
            item.get("due_date") or "—",
        ]
        for item in items
    ]


def _projects_rows(items: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in items:
        signal = item["blockers"] or item["next_action"] or "Sin detalle registrado."
        rows.append(
            [
                item["name"],
                str(item["open_issues"]),
                str(item["task_count"]),
                _summarize_text(signal, 90),
            ]
        )
    return rows


def _bridge_rows(items: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in items:
        rows.append(
            [
                item["title"],
                item["status"],
                item.get("project") or "—",
                item.get("priority") or "—",
                _summarize_text(item.get("next_action") or item.get("notes") or "Sin siguiente acción.", 90),
            ]
        )
    return rows


def _due_rows(items: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [
            item.get("due_date") or "—",
            item["name"],
            item.get("project_name", "Sin proyecto"),
            item["review"],
        ]
        for item in items
    ]


def _build_panel_blocks(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    summary = snapshot["summary"]
    focus = _primary_focus(snapshot)
    bridge_hint = "Disponible" if summary["bridge_available"] else "Sin acceso"
    next_due = snapshot["due_items"][0]["due_date"] if snapshot["due_items"] else "Sin fechas"
    blocks: list[dict[str, Any]] = [
        _block_heading2("Resumen operativo"),
        _block_callout(
            f"{focus['title']}\n{focus['body']}",
            emoji=focus["emoji"],
            color=focus["color"],
        ),
        _block_column_list(
            [
                [
                    *_metric_card(
                        "Revision",
                        summary["pending_deliverables"],
                        "por revisar",
                        "📬",
                        color=_metric_color("Entregables", summary["pending_deliverables"], bridge_available=summary["bridge_available"]),
                        secondary=f"Ajustes: {summary['deliverables_adjustments']}",
                    ),
                    *_metric_card(
                        "Proyectos",
                        summary["projects_attention"],
                        "con atencion",
                        "📁",
                        color=_metric_color("Proyectos", summary["projects_attention"], bridge_available=summary["bridge_available"]),
                        secondary="bloqueo o drift",
                    ),
                ],
                [
                    *_metric_card(
                        "Bandeja",
                        summary["bridge_live"],
                        "items vivos",
                        "📮",
                        color=_metric_color("Bandeja", summary["bridge_live"], bridge_available=summary["bridge_available"]),
                        secondary=bridge_hint,
                    ),
                    *_metric_card(
                        "Vencimientos",
                        summary["due_items"],
                        "proximos",
                        "⏰",
                        color=_metric_color("Vencimientos", summary["due_items"], bridge_available=summary["bridge_available"]),
                        secondary=f"Primero: {next_due}",
                    ),
                ],
            ]
        ),
        *_panel_status_blocks(snapshot),
        _usage_guide_block(),
        _block_heading3("Entregables por revisar"),
    ]

    pending = snapshot["pending_deliverables"]
    if pending:
        blocks.append(_block_table(["Entregable", "Proyecto", "Estado", "Vence"], _deliverables_rows(pending)))
    else:
        blocks.append(_block_table(["Entregable", "Proyecto", "Estado", "Vence"], [["No hay entregables pendientes.", "—", "—", "—"]]))

    blocks.extend(
        [
            _block_heading3("Proyectos que requieren atencion"),
        ]
    )
    projects = snapshot["projects_attention"]
    if projects:
        blocks.append(_block_table(["Proyecto", "Issues", "Tareas", "Señal"], _projects_rows(projects)))
    else:
        blocks.append(_block_table(["Proyecto", "Issues", "Tareas", "Señal"], [["Sin proyectos con drift visible.", "0", "0", "—"]]))

    blocks.append(_block_heading3("Bandeja viva"))
    bridge = snapshot["bridge_live"]
    if bridge:
        blocks.append(_block_table(["Item", "Estado", "Proyecto", "Prioridad", "Siguiente acción"], _bridge_rows(bridge)))
    else:
        empty_note = "Sin acceso actual a Bandeja Puente." if not summary["bridge_available"] else "Sin items vivos."
        blocks.append(_block_table(["Item", "Estado", "Proyecto", "Prioridad", "Siguiente acción"], [[empty_note, "-", "-", "-", empty_note]]))

    blocks.append(_block_heading3("Proximos vencimientos"))
    due_items = snapshot["due_items"]
    if due_items:
        blocks.append(_block_table(["Vence", "Entregable", "Proyecto", "Estado"], _due_rows(due_items)))
    else:
        blocks.append(_block_table(["Vence", "Entregable", "Proyecto", "Estado"], [["Sin fechas proximas.", "—", "—", "—"]]))

    blocks.append(_block_divider())
    return blocks


def _find_bases_anchor(children: list[dict[str, Any]]) -> int | None:
    for idx, block in enumerate(children):
        if block.get("type") == "heading_3" and _extract_text(block).strip().lower() in {"recursos", "bases operativas"}:
            return idx
    return None


def _tidy_navigation_sections(page_id: str, children: list[dict[str, Any]]) -> None:
    divider_idx = next((idx for idx, block in enumerate(children) if block.get("type") == "divider"), None)
    if divider_idx is not None:
        tail = children[divider_idx + 1 :]
        if tail and tail[0].get("type") in {"child_page", "child_database"}:
            _insert_after(page_id, children[divider_idx]["id"], [_block_heading3("Accesos rapidos")])
            children = _list_children(page_id)
            divider_idx = next((idx for idx, block in enumerate(children) if block.get("type") == "divider"), None)

        nav_heading_indexes = [
            idx
            for idx, block in enumerate(children[divider_idx + 1 :], start=divider_idx + 1)
            if block.get("type") == "heading_3"
        ]
        if len(nav_heading_indexes) >= 2:
            _update_block_text(children[nav_heading_indexes[0]], "Accesos rapidos")
            _update_block_text(children[nav_heading_indexes[1]], "Bases operativas")
            return

    base_heading_indexes = [
        idx
        for idx, block in enumerate(children)
        if block.get("type") == "heading_3" and _extract_text(block).strip().lower() == "bases operativas"
    ]
    if len(base_heading_indexes) >= 2:
        _update_block_text(children[base_heading_indexes[0]], "Accesos rapidos")
        _update_block_text(children[base_heading_indexes[1]], "Bases operativas")

    for idx, block in enumerate(children[:-1]):
        if block.get("type") != "paragraph":
            continue
        if _extract_text(block).strip():
            continue
        next_block = children[idx + 1]
        if next_block.get("type") == "child_page" and _extract_text(next_block).strip().lower().startswith("ooda weekly report"):
            _update_block_text(block, "Historico reciente")
            break


def _cleanup_openclaw_residuals(children: list[dict[str, Any]]) -> int:
    residual_pages = [block["id"] for block in children if _is_residual_child_page(block)]
    if residual_pages:
        _archive_pages(residual_pages)

    trailing_empty_blocks: list[str] = []
    for block in reversed(children):
        if block.get("type") != "paragraph":
            break
        if _extract_text(block).strip():
            break
        trailing_empty_blocks.append(block["id"])
    if trailing_empty_blocks:
        _delete_blocks(list(reversed(trailing_empty_blocks)))

    return len(residual_pages) + len(trailing_empty_blocks)


def _synchronize_summary_callout(children: list[dict[str, Any]], snapshot: dict[str, Any]) -> None:
    focus = _primary_focus(snapshot)
    summary_idx = next(
        (
            idx
            for idx, block in enumerate(children)
            if block.get("type") == "heading_2" and _extract_text(block).strip() == "Resumen operativo"
        ),
        None,
    )
    if summary_idx is None:
        return

    for block in children[summary_idx + 1 :]:
        block_type = block.get("type")
        if block_type == "callout":
            _update_block_text(
                block,
                f"{focus['title']}\n{focus['body']}",
                emoji=focus["emoji"],
            )
            return
        if block_type in {"heading_2", "heading_3", "divider", "child_database", "child_page"}:
            return


def validate_openclaw_shell(children: list[dict[str, Any]]) -> dict[str, Any]:
    first_ok = bool(children) and children[0].get("type") == "callout"
    anchor_idx = _find_bases_anchor(children)
    child_db_count = 0
    found_headings = {
        _extract_text(block).strip()
        for block in children
        if block.get("type") in {"heading_2", "heading_3"}
    }
    required_headings = {
        "Resumen operativo",
        "Entregables por revisar",
        "Proyectos que requieren atencion",
        "Bandeja viva",
        "Proximos vencimientos",
        "Bases operativas",
    }
    quick_access_present = "Accesos rapidos" in found_headings or any(_is_allowed_nav_child_page(block) for block in children)
    residual_child_pages = [
        block["id"]
        for block in children
        if block.get("type") == "child_page" and not _is_allowed_nav_child_page(block)
    ]
    if anchor_idx is not None:
        for block in children[anchor_idx + 1 :]:
            if block.get("type") == "child_database":
                child_db_count += 1
    return {
        "ok": (
            first_ok
            and anchor_idx is not None
            and child_db_count >= 3
            and required_headings.issubset(found_headings)
            and not residual_child_pages
        ),
        "first_callout": first_ok,
        "bases_anchor": anchor_idx is not None,
        "child_databases_after_anchor": child_db_count,
        "required_headings_present": required_headings.issubset(found_headings),
        "quick_access_present": quick_access_present,
        "residual_child_pages": len(residual_child_pages),
    }


def refresh_openclaw_panel() -> dict[str, Any]:
    if not OPENCLAW_PAGE_ID:
        raise RuntimeError("NOTION_CONTROL_ROOM_PAGE_ID not configured")

    children = _list_children(OPENCLAW_PAGE_ID)
    if not children:
        raise RuntimeError("OpenClaw page has no blocks")

    first_block = children[0]
    if first_block.get("type") != "callout":
        raise RuntimeError("Expected first OpenClaw block to be a callout")

    anchor_idx = _find_bases_anchor(children)
    if anchor_idx is None:
        raise RuntimeError("Could not find 'Bases operativas' or 'Recursos' heading in OpenClaw page")

    bridge_db_id = getattr(config, "NOTION_BRIDGE_DB_ID", None) or _find_child_database_id(children, "Bandeja Puente")

    snapshot = _build_operational_snapshot(bridge_db_id=bridge_db_id)
    panel_blocks = _build_panel_blocks(snapshot)
    stale_blocks = children[1:anchor_idx]
    _remove_stale_blocks(stale_blocks)
    _update_block_text(
        first_block,
        "OpenClaw es el panel operativo humano. Aqui revisas que atender, aprobar o destrabar. "
        "Para salud tecnica del stack, abre Dashboard Rick.",
        emoji="🧭",
    )
    _insert_after(OPENCLAW_PAGE_ID, first_block["id"], panel_blocks)

    children = _list_children(OPENCLAW_PAGE_ID)
    for idx, block in enumerate(children):
        if block.get("type") == "heading_3" and _extract_text(block).strip().lower() in {"cómo leer este dashboard", "recursos"}:
            _update_block_text(block, "Bases operativas")
            delete_ids: list[str] = []
            for follow in children[idx + 1 :]:
                if follow.get("type") in {"child_database", "child_page", "heading_3", "heading_2", "heading_1"}:
                    break
                delete_ids.append(follow["id"])
            _delete_blocks(delete_ids)
            break

    children = _list_children(OPENCLAW_PAGE_ID)
    latest_snapshot = _build_operational_snapshot(bridge_db_id=bridge_db_id)
    _synchronize_summary_callout(children, latest_snapshot)
    children = _list_children(OPENCLAW_PAGE_ID)
    _tidy_navigation_sections(OPENCLAW_PAGE_ID, children)
    children = _list_children(OPENCLAW_PAGE_ID)
    cleaned = _cleanup_openclaw_residuals(children)
    validation = validate_openclaw_shell(_list_children(OPENCLAW_PAGE_ID))
    return {"updated": True, "panel_blocks": len(panel_blocks), "cleaned_blocks": cleaned, "validation": validation}


def main() -> int:
    result = refresh_openclaw_panel()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
