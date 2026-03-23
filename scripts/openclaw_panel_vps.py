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

import argparse
import contextvars
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from infra.ops_logger import ops_log
from worker import config, notion_client
from worker.notion_client import (
    _block_callout,
    _block_bulleted,
    _block_divider,
    _block_heading2,
    _block_heading3,
    _block_table,
    _block_toggle,
)

OPENCLAW_PAGE_ID = config.NOTION_CONTROL_ROOM_PAGE_ID
SUPERVISOR_ALERT_PAGE_ID = (os.environ.get("NOTION_SUPERVISOR_ALERT_PAGE_ID") or "").strip() or None
_RESIDUAL_CHILD_PAGE_PREFIXES = (
    "OODA Weekly Report - ",
    "[improvement] Workflow: self_improvement_cycle",
)
SUMMARY_HEADING = "Resumen ejecutivo"
SUMMARY_TABLE_HEADING = "Lectura rápida"
NAVIGATION_HEADING = "Bases operativas y paneles"
TECHNICAL_DASHBOARD_TITLE = "Dashboard Rick"
SUPERVISOR_ALERTS_TITLE = "Alertas del Supervisor"
_ALLOWED_NAV_CHILD_PAGES = {
    TECHNICAL_DASHBOARD_TITLE,
    SUPERVISOR_ALERTS_TITLE,
}
_DISPLAY_REVIEW = {
    "Pendiente revision": "Pendiente revisión",
    "Pendiente revisión": "Pendiente revisión",
    "Aprobado con ajustes": "Aprobado con ajustes",
}
CALLER_ID = "script.openclaw_panel_vps"
_FINGERPRINT_PATH = Path.home() / ".config" / "umbral" / "openclaw_panel_fingerprint"
_DIRTY_FLAG_PATH = Path.home() / ".config" / "umbral" / "openclaw_panel_dirty.json"


@dataclass
class PanelRunStats:
    trigger: str
    notion_reads: int = 0
    notion_writes: int = 0
    db_queries: int = 0
    db_rows_read: int = 0
    child_list_calls: int = 0
    blocks_deleted: int = 0
    pages_archived: int = 0
    pages_renamed: int = 0


_RUN_STATS: contextvars.ContextVar[PanelRunStats | None] = contextvars.ContextVar(
    "openclaw_panel_run_stats",
    default=None,
)


def _record_stats(
    *,
    notion_reads: int = 0,
    notion_writes: int = 0,
    db_queries: int = 0,
    db_rows_read: int = 0,
    child_list_calls: int = 0,
    blocks_deleted: int = 0,
    pages_archived: int = 0,
    pages_renamed: int = 0,
) -> None:
    stats = _RUN_STATS.get()
    if stats is None:
        return
    stats.notion_reads += notion_reads
    stats.notion_writes += notion_writes
    stats.db_queries += db_queries
    stats.db_rows_read += db_rows_read
    stats.child_list_calls += child_list_calls
    stats.blocks_deleted += blocks_deleted
    stats.pages_archived += pages_archived
    stats.pages_renamed += pages_renamed


def _write_fingerprint(fingerprint: str) -> None:
    _FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FINGERPRINT_PATH.write_text(fingerprint, encoding="utf-8")


def _read_fingerprint() -> str | None:
    try:
        return _FINGERPRINT_PATH.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None


def _snapshot_fingerprint(snapshot: dict[str, Any]) -> str:
    stable = {k: v for k, v in snapshot.items() if k != "generated_at"}
    raw = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def mark_openclaw_dirty(reason: str, *, source: str | None = None) -> dict[str, Any]:
    payload = {
        "reason": reason[:200],
        "source": (source or "")[:200],
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    _DIRTY_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DIRTY_FLAG_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def _read_dirty_flag() -> dict[str, Any] | None:
    try:
        raw = _DIRTY_FLAG_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"reason": "dirty_flag_corrupt"}
    return data if isinstance(data, dict) else {"reason": "dirty_flag_invalid"}


def _clear_dirty_flag() -> None:
    try:
        _DIRTY_FLAG_PATH.unlink()
    except FileNotFoundError:
        return


def _openclaw_panel_ready() -> bool:
    required = [
        config.NOTION_CONTROL_ROOM_PAGE_ID,
        config.NOTION_API_KEY,
        config.NOTION_PROJECTS_DB_ID,
        config.NOTION_DELIVERABLES_DB_ID,
    ]
    return all(isinstance(value, str) and value.strip() for value in required)


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
            _record_stats(notion_reads=1, child_list_calls=1)
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


def _normalize_page_id(page_id: str | None) -> str:
    return (page_id or "").replace("-", "").strip().lower()


def _canonical_nav_page_title(page_id: str, current_title: str) -> str | None:
    if _normalize_page_id(config.NOTION_DASHBOARD_PAGE_ID) and _normalize_page_id(page_id) == _normalize_page_id(config.NOTION_DASHBOARD_PAGE_ID):
        return TECHNICAL_DASHBOARD_TITLE
    if _normalize_page_id(SUPERVISOR_ALERT_PAGE_ID) and _normalize_page_id(page_id) == _normalize_page_id(SUPERVISOR_ALERT_PAGE_ID):
        return SUPERVISOR_ALERTS_TITLE
    if current_title in _ALLOWED_NAV_CHILD_PAGES:
        return current_title
    return None


def _normalize_review(review: str | None) -> str:
    return _DISPLAY_REVIEW.get((review or "").strip(), (review or "").strip())


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
            _record_stats(notion_writes=1, pages_archived=1)
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
            _record_stats(notion_writes=1, blocks_deleted=1)
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
        _record_stats(notion_writes=1)
        notion_client._check_response(resp, "update block text")  # type: ignore[attr-defined]


def _update_page_title(page_id: str, title: str) -> None:
    with _api_client() as client:
        resp = client.get(
            f"{notion_client.NOTION_BASE_URL}/pages/{page_id}",
            headers=_headers(),
        )
        _record_stats(notion_reads=1)
        page = notion_client._check_response(resp, "get page")  # type: ignore[attr-defined]

        properties = page.get("properties", {}) or {}
        title_property = next(
            (name for name, prop in properties.items() if isinstance(prop, dict) and prop.get("type") == "title"),
            None,
        )
        if not title_property:
            raise RuntimeError(f"Could not find title property for page {page_id}")

        resp = client.patch(
            f"{notion_client.NOTION_BASE_URL}/pages/{page_id}",
            headers=_headers(),
            json={
                "properties": {
                    title_property: {
                        "title": [{"type": "text", "text": {"content": title[:2000]}}],
                    }
                }
            },
        )
        _record_stats(notion_writes=1)
        notion_client._check_response(resp, "update page title")  # type: ignore[attr-defined]


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
            _record_stats(notion_writes=1)
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
    _record_stats(db_queries=1)
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
            _record_stats(notion_reads=1)
            data = notion_client._check_response(resp, "query db")  # type: ignore[attr-defined]
            results.extend(data.get("results", []))
            next_cursor = data.get("next_cursor")
            if not next_cursor:
                break
    _record_stats(db_rows_read=len(results))
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


def _primary_focus(snapshot: dict[str, Any]) -> dict[str, str]:
    pending = snapshot["pending_deliverables"]
    if pending:
        item = pending[0]
        due = item.get("due_date") or "sin fecha"
        review = item.get("review") or "Pendiente"
        next_action = item.get("next_action") or "Toma una decisión de revisión y deja la siguiente acción amarrada."
        return {
            "title": "Prioridad inmediata",
            "body": (
                f"Entregable: {item['name']}\n"
                f"Proyecto: {item.get('project_name', 'Sin proyecto')}\n"
                f"Estado: {review} · Vence: {due}\n"
                f"Siguiente paso: {_summarize_text(next_action, 150)}"
            ),
            "emoji": "🎯",
            "color": "red_background" if review == "Pendiente revisión" else "yellow_background",
        }

    projects = snapshot["projects_attention"]
    if projects:
        item = projects[0]
        signal = item.get("blockers") or item.get("next_action") or "Sin detalle registrado."
        return {
            "title": "Proyecto que requiere decisión",
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
            "title": "Coordinación viva",
            "body": (
                f"Item: {item['title']}\n"
                f"Estado: {item.get('status') or 'Sin estado'} · Proyecto: {item.get('project') or 'Sin proyecto'}\n"
                f"Siguiente acción: {_summarize_text(action, 120)}"
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


def _summary_rows(snapshot: dict[str, Any]) -> list[list[str]]:
    summary = snapshot["summary"]
    bridge_state = "Disponible" if summary["bridge_available"] else "Sin acceso"
    next_due = snapshot["due_items"][0]["due_date"] if snapshot["due_items"] else "Sin fechas próximas"
    return [
        [
            "📬 Entregables",
            f"{summary['pending_deliverables']} por revisar · {summary['deliverables_adjustments']} con ajustes",
            "Esperan una decisión humana o el cierre de ajustes ya pedidos.",
        ],
        [
            "📁 Proyectos",
            f"{summary['projects_attention']} con atención",
            "Concentran bloqueo, drift operativo o falta de tracción.",
        ],
        [
            "📮 Bandeja puente",
            f"{summary['bridge_live']} items vivos · {bridge_state}",
            "Muestra coordinación cruzada pendiente entre frentes y agentes.",
        ],
        [
            "⏰ Vencimientos",
            f"{summary['due_items']} próximos · primero {next_due}",
            "Da la siguiente fecha que conviene revisar antes de destrabar.",
        ],
    ]


def _panel_status_blocks(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    summary = snapshot["summary"]
    bridge_state = "disponible" if summary["bridge_available"] else "sin acceso"
    return [
        _block_callout(
            (
                "Estado del panel\n"
                f"Actualizado: {snapshot['generated_at']}\n"
                f"Revisión: {summary['pending_deliverables']} · Proyectos: {summary['projects_attention']}\n"
                f"Bandeja Puente: {bridge_state}"
            ),
            emoji="🧭",
            color="blue_background",
        )
    ]


def _usage_guide_block() -> dict[str, Any]:
    return _block_toggle(
        "Cómo usar este panel",
        [
            _block_bulleted("Empieza por la prioridad inmediata: resume la decisión con más impacto ahora."),
            _block_bulleted("Luego baja a Entregables y Proyectos; ahí se decide qué se aprueba, ajusta o destraba."),
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


def _rename_navigation_pages(children: list[dict[str, Any]]) -> int:
    renamed = 0
    for block in children:
        if block.get("type") != "child_page":
            continue
        page_id = block.get("id")
        current_title = _extract_text(block).strip()
        if not page_id:
            continue
        target_title = _canonical_nav_page_title(page_id, current_title)
        if target_title and current_title != target_title:
            _update_page_title(page_id, target_title)
            _record_stats(pages_renamed=1)
            renamed += 1
    return renamed


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
        review = _normalize_review(_plain(props.get("Estado revision", {})) or "")
        if review not in {"Pendiente revisión", "Aprobado con ajustes"}:
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
            0 if item["review"] == "Pendiente revisión" else 1,
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
        title = _plain(props.get("Ítem", {})) or "Sin título"
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
    blocks: list[dict[str, Any]] = [
        _block_heading2(SUMMARY_HEADING),
        _block_callout(
            f"{focus['title']}\n{focus['body']}",
            emoji=focus["emoji"],
            color=focus["color"],
        ),
        _block_heading3(SUMMARY_TABLE_HEADING),
        _block_table(
            ["Frente", "Estado actual", "Qué significa"],
            _summary_rows(snapshot),
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
            _block_heading3("Proyectos que requieren atención"),
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

    blocks.append(_block_heading3("Próximos vencimientos"))
    due_items = snapshot["due_items"]
    if due_items:
        blocks.append(_block_table(["Vence", "Entregable", "Proyecto", "Estado"], _due_rows(due_items)))
    else:
        blocks.append(_block_table(["Vence", "Entregable", "Proyecto", "Estado"], [["Sin fechas próximas.", "—", "—", "—"]]))

    blocks.append(_block_divider())
    return blocks


def _find_bases_anchor(children: list[dict[str, Any]]) -> int | None:
    for idx, block in enumerate(children):
        if block.get("type") == "heading_3" and _extract_text(block).strip().lower() in {
            "recursos",
            "bases operativas",
            "bases operativas y paneles",
        }:
            return idx
    return None


def _tidy_navigation_sections(page_id: str, children: list[dict[str, Any]]) -> None:
    divider_idx = next((idx for idx, block in enumerate(children) if block.get("type") == "divider"), None)
    if divider_idx is not None:
        tail = children[divider_idx + 1 :]
        if tail and tail[0].get("type") in {"child_page", "child_database"}:
            _insert_after(page_id, children[divider_idx]["id"], [_block_heading3(NAVIGATION_HEADING)])
            children = _list_children(page_id)
    base_heading_indexes = [
        idx
        for idx, block in enumerate(children)
        if block.get("type") == "heading_3"
        and _extract_text(block).strip().lower() in {
            "accesos rapidos",
            "bases operativas",
            "bases operativas y paneles",
            "recursos",
        }
    ]
    if base_heading_indexes:
        _update_block_text(children[base_heading_indexes[0]], NAVIGATION_HEADING)
        if len(base_heading_indexes) > 1:
            _delete_blocks([children[idx]["id"] for idx in base_heading_indexes[1:]])


def _cleanup_openclaw_residuals(children: list[dict[str, Any]]) -> int:
    residual_pages = [block["id"] for block in children if _is_residual_child_page(block)]
    if residual_pages:
        _archive_pages(residual_pages)

    empty_paragraphs = [
        block["id"]
        for block in children
        if block.get("type") == "paragraph" and not _extract_text(block).strip()
    ]
    if empty_paragraphs:
        _delete_blocks(empty_paragraphs)

    return len(residual_pages) + len(empty_paragraphs)


def _synchronize_summary_callout(children: list[dict[str, Any]], snapshot: dict[str, Any]) -> None:
    focus = _primary_focus(snapshot)
    summary_idx = next(
        (
            idx
            for idx, block in enumerate(children)
            if block.get("type") == "heading_2" and _extract_text(block).strip() == SUMMARY_HEADING
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
        SUMMARY_HEADING,
        SUMMARY_TABLE_HEADING,
        "Entregables por revisar",
        "Proyectos que requieren atención",
        "Bandeja viva",
        "Próximos vencimientos",
        NAVIGATION_HEADING,
    }
    quick_access_present = any(_is_allowed_nav_child_page(block) for block in children)
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


def _refresh_openclaw_panel_impl() -> dict[str, Any]:
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
        raise RuntimeError("Could not find the navigation heading in OpenClaw page")

    bridge_db_id = getattr(config, "NOTION_BRIDGE_DB_ID", None) or _find_child_database_id(children, "Bandeja Puente")

    snapshot = _build_operational_snapshot(bridge_db_id=bridge_db_id)
    panel_blocks = _build_panel_blocks(snapshot)
    stale_blocks = children[1:anchor_idx]
    _remove_stale_blocks(stale_blocks)
    _update_block_text(
        first_block,
        "OpenClaw es el panel operativo humano. Aquí revisas qué atender, aprobar o destrabar. "
        "Para salud técnica del stack, abre Dashboard Rick. "
        "Las alertas automáticas viven en Alertas del Supervisor.",
        emoji="🧭",
    )
    _insert_after(OPENCLAW_PAGE_ID, first_block["id"], panel_blocks)

    children = _list_children(OPENCLAW_PAGE_ID)
    for idx, block in enumerate(children):
        if block.get("type") == "heading_3" and _extract_text(block).strip().lower() in {"cómo leer este dashboard", "recursos"}:
            _update_block_text(block, NAVIGATION_HEADING)
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
    renamed_pages = _rename_navigation_pages(children)
    children = _list_children(OPENCLAW_PAGE_ID)
    cleaned = _cleanup_openclaw_residuals(children)
    validation = validate_openclaw_shell(_list_children(OPENCLAW_PAGE_ID))
    return {
        "updated": True,
        "panel_blocks": len(panel_blocks),
        "cleaned_blocks": cleaned,
        "renamed_pages": renamed_pages,
        "validation": validation,
    }


def _log_openclaw_activity(
    *,
    status: str,
    duration_ms: float,
    trigger: str,
    fingerprint: str | None,
    stats: PanelRunStats,
    details: str | None = None,
) -> None:
    ops_log.system_activity(
        "openclaw_panel",
        "refresh",
        status,
        duration_ms,
        trigger=trigger,
        fingerprint=fingerprint,
        notion_reads=stats.notion_reads,
        notion_writes=stats.notion_writes,
        db_rows_read=stats.db_rows_read,
        details=details,
    )


def refresh_openclaw_panel(*, force: bool = False, trigger: str = "manual") -> dict[str, Any]:
    if not OPENCLAW_PAGE_ID:
        raise RuntimeError("NOTION_CONTROL_ROOM_PAGE_ID not configured")

    started_at = time.perf_counter()
    stats = PanelRunStats(trigger=trigger)
    token = _RUN_STATS.set(stats)
    fingerprint: str | None = None
    try:
        children = _list_children(OPENCLAW_PAGE_ID)
        if not children:
            raise RuntimeError("OpenClaw page has no blocks")

        bridge_db_id = getattr(config, "NOTION_BRIDGE_DB_ID", None) or _find_child_database_id(children, "Bandeja Puente")
        snapshot = _build_operational_snapshot(bridge_db_id=bridge_db_id)
        fingerprint = _snapshot_fingerprint(snapshot)
        dirty_flag = _read_dirty_flag()
        validation_before = validate_openclaw_shell(children)

        if not force and validation_before["ok"] and fingerprint == _read_fingerprint() and not dirty_flag:
            duration_ms = (time.perf_counter() - started_at) * 1000
            _log_openclaw_activity(
                status="skipped",
                duration_ms=duration_ms,
                trigger=trigger,
                fingerprint=fingerprint,
                stats=stats,
                details="fingerprint_unchanged",
            )
            return {
                "updated": False,
                "skipped": True,
                "reason": "fingerprint_unchanged",
                "fingerprint": fingerprint,
                "dirty_flag": dirty_flag,
                "validation": validation_before,
            }

        result = _refresh_openclaw_panel_impl()
        _write_fingerprint(fingerprint)
        _clear_dirty_flag()
        duration_ms = (time.perf_counter() - started_at) * 1000
        _log_openclaw_activity(
            status="updated",
            duration_ms=duration_ms,
            trigger=trigger,
            fingerprint=fingerprint,
            stats=stats,
            details=(
                f"panel_blocks={result.get('panel_blocks', 0)}; "
                f"cleaned={result.get('cleaned_blocks', 0)}; "
                f"renamed={result.get('renamed_pages', 0)}"
            ),
        )
        return {
            **result,
            "fingerprint": fingerprint,
            "dirty_flag": dirty_flag,
        }
    except Exception as exc:
        duration_ms = (time.perf_counter() - started_at) * 1000
        _log_openclaw_activity(
            status="failed",
            duration_ms=duration_ms,
            trigger=trigger,
            fingerprint=fingerprint,
            stats=stats,
            details=str(exc),
        )
        raise
    finally:
        _RUN_STATS.reset(token)


def trigger_openclaw_panel_refresh(reason: str, *, source: str | None = None, force: bool = False) -> dict[str, Any]:
    if not _openclaw_panel_ready():
        return {
            "triggered": False,
            "reason": "openclaw_panel_not_ready",
        }

    dirty_flag = mark_openclaw_dirty(reason, source=source)
    result = refresh_openclaw_panel(
        force=force,
        trigger=source or reason or "event",
    )
    return {
        "triggered": True,
        "dirty_flag": dirty_flag,
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh OpenClaw human panel")
    parser.add_argument("--force", action="store_true", help="Refresh even if fingerprint did not change")
    parser.add_argument("--trigger", default="manual", help="Trigger label for ops_log tracking")
    args = parser.parse_args()

    result = refresh_openclaw_panel(force=args.force, trigger=args.trigger)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
