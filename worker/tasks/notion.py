"""
Tasks: Notion integration handlers.

- notion.write_transcript: crear página en Granola Inbox DB
- notion.add_comment: agregar comentario en Control Room
- notion.poll_comments: leer comentarios recientes
- notion.read_page: leer metadata y snapshot de una página
- notion.create_report_page: crear página hija con reporte estructurado
- notion.enrich_bitacora_page: enriquecer página de Bitácora con secciones o bloques
- notion.create_database_page: crear página en una base de datos usando propiedades raw
- notion.update_page_properties: actualizar propiedades de una página existente
- notion.upsert_project: crear o actualizar proyecto en DB 📁 Proyectos — Umbral
"""

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from .. import config, notion_client

_poll_redis_client: Any | None = None
_poll_redis_disabled = False
_poll_logger = logging.getLogger("worker.notion.poll")


def _get_poll_redis_client() -> Any | None:
    """Lazily build a Redis client for poll_comments cursor checkpoint (ADR-010).

    Returns None silently if `redis` isn't installed or REDIS_URL is unset/unreachable.
    """
    global _poll_redis_client, _poll_redis_disabled
    if _poll_redis_client is not None:
        return _poll_redis_client
    if _poll_redis_disabled:
        return None
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        _poll_redis_disabled = True
        return None
    try:
        import redis  # type: ignore

        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        _poll_redis_client = client
        return client
    except Exception as exc:
        _poll_logger.warning("poll_comments cursor disabled (redis unavailable): %s", exc)
        _poll_redis_disabled = True
        return None
from ..notion_client import (
    _block_heading1,
    _block_heading2,
    _block_heading3,
    _block_paragraph,
    _block_bulleted,
    _block_callout,
    _block_code,
    _block_divider,
    _block_quote,
    _block_table,
)
from .notion_markdown import markdown_to_blocks


def _maybe_trigger_openclaw_panel_refresh(reason: str, *, source: str) -> Dict[str, Any]:
    try:
        from scripts.openclaw_panel_vps import trigger_openclaw_panel_refresh

        return trigger_openclaw_panel_refresh(reason, source=source)
    except Exception as exc:
        return {
            "triggered": False,
            "reason": "openclaw_refresh_failed",
            "error": str(exc)[:200],
        }


def handle_notion_write_transcript(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una página en la DB de transcripciones (Granola Inbox).

    Input:
        title (str, required): Título de la transcripción.
        content (str, required): Texto de la transcripción.
        source (str, optional): Fuente (default: "granola").
        date (str, optional): Fecha ISO (default: hoy UTC).

    Returns:
        {"page_id": "...", "url": "..."}
    """
    title = input_data.get("title")
    content = input_data.get("content")
    if not title or not content:
        raise ValueError("'title' and 'content' are required in input")

    return notion_client.create_transcript_page(
        title=title,
        content=content,
        source=input_data.get("source", "granola"),
        date=input_data.get("date"),
    )


def handle_notion_add_comment(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agrega un comentario en una página de Notion (default: Control Room).

    Input:
        text (str, required): Texto del comentario.
        page_id (str, optional): ID de la página. Default: NOTION_CONTROL_ROOM_PAGE_ID.

    Returns:
        {"comment_id": "..."}
    """
    text = input_data.get("text")
    if not text:
        raise ValueError("'text' is required in input")

    return notion_client.add_comment(
        page_id=input_data.get("page_id"),
        text=text,
    )


def handle_notion_poll_comments(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lee comentarios recientes de una página de Notion.

    Input:
        page_id (str, optional): ID de la página. Default: NOTION_CONTROL_ROOM_PAGE_ID.
        since (str, optional): ISO datetime — solo comentarios después de esta fecha.
        limit (int, optional): Máximo de comentarios (default: 20).

    Returns:
        {"comments": [...], "count": N}
    """
    return notion_client.poll_comments(
        page_id=input_data.get("page_id"),
        since=input_data.get("since"),
        limit=input_data.get("limit", 20),
        redis_client=_get_poll_redis_client(),
    )


def handle_notion_read_page(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lee metadata y un snapshot de bloques de una página de Notion.

    Input:
        page_id_or_url (str, required): UUID o URL completa de Notion.
        max_blocks (int, optional): Máximo de bloques top-level a devolver (default: 50).

    Returns:
        {"page_id": "...", "title": "...", "blocks": [...], "plain_text": "..."}
    """
    page_id_or_url = input_data.get("page_id_or_url") or input_data.get("page_id") or input_data.get("url")
    if not page_id_or_url:
        raise ValueError("'page_id_or_url' is required in input")

    return notion_client.read_page(
        page_id_or_url=str(page_id_or_url),
        max_blocks=input_data.get("max_blocks", 50),
    )


def handle_notion_read_database(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lee metadata y un snapshot plano de una base de datos de Notion.

    Input:
        database_id_or_url (str, required): UUID o URL completa de Notion.
        max_items (int, optional): Máximo de filas a devolver (default: 50).
        filter (dict, optional): Filtro Notion para query.

    Returns:
        {"database_id": "...", "title": "...", "schema": {...}, "items": [...]}
    """
    database_id_or_url = (
        input_data.get("database_id_or_url")
        or input_data.get("database_id")
        or input_data.get("url")
    )
    if not database_id_or_url:
        raise ValueError("'database_id_or_url' is required in input")

    return notion_client.read_database(
        database_id_or_url=str(database_id_or_url),
        max_items=input_data.get("max_items", 50),
        filter=input_data.get("filter"),
    )


def handle_notion_search_databases(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Busca bases de datos de Notion por título.

    Input:
        query (str, required): Texto a buscar.
        max_results (int, optional): Máximo de bases a devolver (default: 10).

    Returns:
        {"query": "...", "results": [...], "count": N}
    """
    query = input_data.get("query")
    if not query:
        raise ValueError("'query' is required in input")

    return notion_client.search_databases(
        query=str(query),
        max_results=input_data.get("max_results", 10),
    )


def handle_notion_create_database_page(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una página dentro de una base de datos de Notion usando propiedades raw.

    Input:
        database_id_or_url (str, required): UUID o URL de la base.
        properties (dict, required): payload raw de propiedades Notion.
        children (list[dict], optional): bloques hijos opcionales.
        icon (str, optional): emoji o URL externa para el icono de la pagina.

    Returns:
        {"page_id": "...", "url": "...", "created": True}
    """
    database_id_or_url = (
        input_data.get("database_id_or_url")
        or input_data.get("database_id")
        or input_data.get("url")
    )
    if not database_id_or_url:
        raise ValueError("'database_id_or_url' is required in input")

    properties = input_data.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise ValueError("'properties' must be a non-empty object")

    children = input_data.get("children")
    if children is not None and not isinstance(children, list):
        raise ValueError("'children' must be a list when provided")

    return notion_client.create_database_page(
        database_id_or_url=str(database_id_or_url),
        properties=properties,
        children=children,
        icon=input_data.get("icon"),
    )


def handle_notion_update_page_properties(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza propiedades raw de una página existente de Notion.

    Input:
        page_id_or_url (str, required): UUID o URL de la página.
        properties (dict, optional): payload raw de propiedades Notion.
        icon (str, optional): emoji o URL externa para el icono de la pagina.
        archived (bool, optional): archiva o desarchiva la pagina.

    Returns:
        {"page_id": "...", "url": "...", "updated": True}
    """
    page_id_or_url = input_data.get("page_id_or_url") or input_data.get("page_id") or input_data.get("url")
    if not page_id_or_url:
        raise ValueError("'page_id_or_url' is required in input")

    properties = input_data.get("properties", {})
    if not isinstance(properties, dict):
        raise ValueError("'properties' must be an object when provided")
    if not properties and not input_data.get("icon") and input_data.get("archived") is None:
        raise ValueError("'properties', 'icon' or 'archived' must be provided")

    return notion_client.update_page_properties(
        page_id_or_url=str(page_id_or_url),
        properties=properties,
        icon=input_data.get("icon"),
        archived=input_data.get("archived"),
    )


def handle_notion_upsert_task(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea o actualiza una tarea en la DB Kanban (Tareas Umbral).

    Input:
        task_id (str, required): ID de la tarea.
        status (str, required): queued|running|done|failed|blocked.
        team (str, required): equipo/agente.
        task (str, required): nombre técnico de la tarea/handler.
        task_name (str, optional): nombre humano de la tarea para mostrar en Notion.
        input_summary (str, optional): resumen del input.
        error (str, optional): mensaje de error si status=failed.
        result_summary (str, optional): resumen del resultado.
        project_name (str, optional): nombre exacto del proyecto en el registry.
        project_page_id (str, optional): page id del proyecto si ya se conoce.
        deliverable_name (str, optional): nombre exacto del entregable asociado.
        deliverable_page_id (str, optional): page id del entregable si ya se conoce.
        source (str, optional): origen declarado de la tarea.
        source_kind (str, optional): subtipo/canal del origen.
        trace_id (str, optional): id de traza end-to-end.
        selected_model (str, optional): modelo finalmente elegido por el dispatcher.

    Returns:
        {"page_id": "...", "updated": True} o {"skipped": True, "reason": "..."}
    """
    task_id = input_data.get("task_id")
    status = input_data.get("status")
    team = input_data.get("team")
    task = input_data.get("task")
    if not all([task_id, status, team, task]):
        raise ValueError("'task_id', 'status', 'team' and 'task' are required in input")
    human_task_name = _normalize_spaces(str(input_data.get("task_name") or "")) or task

    existing_task_page: Dict[str, Any] | None = None
    if config.NOTION_TASKS_DB_ID:
        try:
            existing_matches = notion_client.query_database(
                database_id=config.NOTION_TASKS_DB_ID,
                filter={
                    "property": "Task ID",
                    "rich_text": {"equals": str(task_id)},
                },
            )
            if existing_matches:
                existing_task_page = existing_matches[0]
        except Exception:
            existing_task_page = None

    project_page_id = (input_data.get("project_page_id") or "").strip()
    project_name = (input_data.get("project_name") or "").strip()
    if not project_page_id and existing_task_page:
        existing_project = _plain_property_value((existing_task_page.get("properties") or {}).get("Proyecto")) or []
        if existing_project:
            project_page_id = str(existing_project[0])
    project_context = _resolve_project_context(
        project_name=project_name or None,
        project_page_id=project_page_id or None,
    )
    if project_context.get("page_id"):
        project_page_id = project_context["page_id"]

    deliverable_page_id = (input_data.get("deliverable_page_id") or "").strip()
    deliverable_name = (input_data.get("deliverable_name") or "").strip()
    deliverable_page = None
    if not deliverable_page_id and existing_task_page:
        existing_deliverable = _plain_property_value((existing_task_page.get("properties") or {}).get("Entregable")) or []
        if existing_deliverable:
            deliverable_page_id = str(existing_deliverable[0])
    normalized_deliverable_name = _normalize_deliverable_name({"name": deliverable_name}) if deliverable_name else ""
    if not deliverable_page_id and normalized_deliverable_name and config.NOTION_DELIVERABLES_DB_ID:
        matches = notion_client.query_database(
            database_id=config.NOTION_DELIVERABLES_DB_ID,
            filter={
                "property": "Nombre",
                "title": {"equals": normalized_deliverable_name},
            },
        )
        if not matches and deliverable_name != normalized_deliverable_name:
            matches = notion_client.query_database(
                database_id=config.NOTION_DELIVERABLES_DB_ID,
                filter={
                    "property": "Nombre",
                    "title": {"equals": deliverable_name},
                },
            )
        if matches:
            deliverable_page_id = matches[0]["id"]
            deliverable_name = normalized_deliverable_name or deliverable_name
    if deliverable_page_id:
        try:
            deliverable_page = notion_client.get_page(deliverable_page_id)
        except Exception:
            deliverable_page = None
        if not project_page_id and deliverable_page:
            deliverable_project = _plain_property_value((deliverable_page.get("properties") or {}).get("Proyecto")) or []
            if deliverable_project:
                project_page_id = str(deliverable_project[0])
                project_context = _resolve_project_context(project_page_id=project_page_id or None)
        if not deliverable_name and deliverable_page:
            deliverable_name = _extract_page_title_from_properties(deliverable_page)

    existing_props = (existing_task_page or {}).get("properties") or {}
    merged_input = dict(input_data)
    if existing_props:
        if not merged_input.get("source"):
            merged_input["source"] = _plain_property_value(existing_props.get("Source")) or merged_input.get("source")
        if not merged_input.get("source_kind"):
            merged_input["source_kind"] = _plain_property_value(existing_props.get("Source Kind")) or merged_input.get("source_kind")
        if not merged_input.get("trace_id"):
            merged_input["trace_id"] = _plain_property_value(existing_props.get("Trace ID")) or merged_input.get("trace_id")
        if not merged_input.get("selected_model"):
            merged_input["selected_model"] = _plain_property_value(existing_props.get("Model")) or merged_input.get("selected_model")

    resolved_icon = input_data.get("icon") or project_context.get("icon")
    if not resolved_icon:
        resolved_icon = _infer_icon_from_text(
            task,
            project_name,
            deliverable_name,
            input_data.get("input_summary"),
            input_data.get("result_summary"),
            fallback="🗂️",
        )

    page_blocks = _build_task_page_blocks(
        merged_input,
        project_context=project_context,
        deliverable_name=deliverable_name or None,
    )

    return notion_client.upsert_task(
        task_id=task_id,
        status=status,
        team=team,
        task=task,
        task_name=human_task_name,
        input_summary=input_data.get("input_summary"),
        error=input_data.get("error"),
        result_summary=input_data.get("result_summary"),
        source=merged_input.get("source"),
        source_kind=merged_input.get("source_kind"),
        trace_id=merged_input.get("trace_id"),
        selected_model=merged_input.get("selected_model"),
        project_page_id=project_page_id or None,
        deliverable_page_id=deliverable_page_id or None,
        icon=resolved_icon,
        children=page_blocks,
    )


def handle_notion_update_dashboard(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza la página Dashboard en Notion con métricas (doc 22).

    Input:
        metrics (dict, required): { "Nombre métrica": "valor", ... }.
        page_id (str, optional): ID de la página. Default: NOTION_DASHBOARD_PAGE_ID.

    Returns:
        {"updated": True, "blocks_appended": N}
    """
    metrics = input_data.get("metrics")
    if not metrics or not isinstance(metrics, dict):
        raise ValueError("'metrics' (dict) is required in input")
    return notion_client.update_dashboard_page(
        page_id=input_data.get("page_id"),
        metrics=metrics,
    )


def handle_notion_create_report_page(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una página hija en la Control Room con un reporte completo.

    Input:
        parent_page_id (str, optional): ID de la página padre. Default: Control Room.
        title (str, required): Título del reporte.
        content (str, required): Contenido en markdown.
        sources (list[dict], optional): Fuentes utilizadas (url, title).
        metadata (dict, optional): Fecha, topic, team, etc.
        icon (str, optional): emoji o URL externa para el icono de la pagina.

    Returns:
        {"page_id": "...", "page_url": "...", "ok": True}
    """
    title = input_data.get("title", "").strip()
    content = input_data.get("content", "").strip()
    if not title:
        raise ValueError("'title' is required in input")
    if not content:
        raise ValueError("'content' is required in input")

    # Convert markdown content to Notion blocks
    content_blocks = markdown_to_blocks(content)

    sources = input_data.get("sources")
    metadata = input_data.get("metadata", {})
    queries = input_data.get("queries")

    # Add generation timestamp to metadata
    metadata.setdefault("generated_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    return notion_client.create_report_page(
        parent_page_id=input_data.get("parent_page_id"),
        title=title,
        content_blocks=content_blocks,
        sources=sources,
        queries=queries,
        metadata=metadata,
        icon=input_data.get("icon") or _infer_report_icon(input_data),
    )


# ---------------------------------------------------------------------------
# Project registry (📁 Proyectos — Umbral)
# ---------------------------------------------------------------------------

_AGENTES_VALID = {"Rick", "Claude", "Codex", "Cursor", "Antigravity"}
_ESTADO_VALID = {"Activo", "En pausa", "Completado", "Archivado"}
_TIPO_ENTREGABLE_VALID = {
    "Benchmark",
    "Reporte",
    "Borrador",
    "Pieza editorial",
    "Criterio / base de conocimiento",
    "Plan",
    "Auditoria",
}
_ESTADO_REVISION_VALID = {
    "Pendiente revision",
    "Aprobado",
    "Aprobado con ajustes",
    "Rechazado",
    "Archivado",
}
_PROCEDENCIA_ENTREGABLE_VALID = {
    "Tarea",
    "Historico",
    "Smoke",
    "Manual",
}
_BRIDGE_STATUS_VALID = {"Nuevo", "En curso", "Esperando", "Resuelto"}
_BRIDGE_PRIORITY_VALID = {"Alta", "Media", "Baja"}
_BRIDGE_SOURCE_VALID = {"Rick", "David", "Sistema", "Control Room", "Proyecto", "Entregable", "Manual"}

_DATE_IN_NAME_RE = re.compile(
    r"(?:\s*[-_/]?\s*)(20\d{2}[-_/](?:0[1-9]|1[0-2])[-_/](?:0[1-9]|[12]\d|3[01]))(?:\b|$)"
)

_SLUG_TOKEN_MAP = {
    "ia": "IA",
    "ai": "IA",
    "bim": "BIM",
    "gui": "GUI",
    "rpa": "RPA",
    "vm": "VM",
    "linkedin": "LinkedIn",
    "youtube": "YouTube",
    "notion": "Notion",
    "rick": "Rick",
    "david": "David",
    "umbral": "Umbral",
    "freepik": "Freepik",
    "figma": "Figma",
}

_PROJECT_ICON_RULES: list[tuple[str, str]] = [
    ("embudo", "🎯"),
    ("linkedin", "🎯"),
    ("youtube", "🎯"),
    ("marketing", "🎯"),
    ("laboral", "💼"),
    ("postul", "💼"),
    ("trabajo", "💼"),
    ("mejora continua", "🔄"),
    ("improvement", "🔄"),
    ("auditor", "🔄"),
    ("editorial", "✍️"),
    ("contenido", "✍️"),
    ("newsletter", "✍️"),
    ("blog", "✍️"),
    ("advisory", "🧠"),
    ("granola", "🎙️"),
    ("transcrip", "🎙️"),
    ("browser", "🌐"),
    ("navegador", "🌐"),
    ("gui", "🖱️"),
    ("rpa", "🖱️"),
    ("ops", "🛠️"),
    ("vm", "🖥️"),
    ("system", "⚙️"),
    ("lab", "🧪"),
    ("freepik", "🎨"),
    ("figma", "🎨"),
    ("docencia", "🎓"),
    ("docente", "🎓"),
    ("clase", "🎓"),
]

_DELIVERABLE_TYPE_ICONS = {
    "Benchmark": "🔎",
    "Reporte": "📝",
    "Borrador": "📝",
    "Pieza editorial": "✍️",
    "Criterio / base de conocimiento": "🧠",
    "Plan": "🗺️",
    "Auditoria": "🔄",
}


_SMOKE_DELIVERABLE_HINTS = (
    "prueba",
    "smoke",
    "guardrail",
    "icono",
    "iconos",
    "reintento",
    "enrutamiento",
)


def _normalize_icon_value(icon_payload: Any) -> str | None:
    """Extract a plain icon string from a Notion icon payload."""
    if isinstance(icon_payload, dict):
        if icon_payload.get("type") == "emoji":
            value = icon_payload.get("emoji")
            return str(value).strip() if value else None
        if icon_payload.get("type") == "external":
            url = (icon_payload.get("external") or {}).get("url")
            return str(url).strip() if url else None
    if isinstance(icon_payload, str):
        return icon_payload.strip() or None
    return None


def _infer_icon_from_text(*values: str | None, fallback: str | None = None) -> str | None:
    haystack = " ".join((value or "").lower() for value in values if value).strip()
    for needle, icon in _PROJECT_ICON_RULES:
        if needle in haystack:
            return icon
    return fallback


def _extract_page_title_from_properties(page: Dict[str, Any]) -> str:
    properties = page.get("properties") or {}
    if not isinstance(properties, dict):
        return ""
    for meta in properties.values():
        if isinstance(meta, dict) and meta.get("type") == "title":
            return notion_client._plain_text_from_rich_text(meta.get("title"))  # type: ignore[attr-defined]
    return ""


def _plain_property_value(prop: Dict[str, Any] | None) -> Any:
    if not isinstance(prop, dict):
        return None
    prop_type = prop.get("type")
    if prop_type == "title":
        return "".join(item.get("plain_text", "") for item in prop.get("title", []))
    if prop_type == "rich_text":
        return "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))
    if prop_type == "status":
        return (prop.get("status") or {}).get("name")
    if prop_type == "select":
        return (prop.get("select") or {}).get("name")
    if prop_type == "relation":
        return [x.get("id") for x in prop.get("relation", []) if x.get("id")]
    return None


def _resolve_project_context(project_name: str | None = None, project_page_id: str | None = None) -> Dict[str, str]:
    """
    Resolve project page id, title and best icon candidate from Projects registry.
    Returns an empty dict when the project cannot be resolved.
    """
    context: Dict[str, str] = {}
    page: Dict[str, Any] | None = None

    if project_page_id:
        try:
            page = notion_client.get_page(project_page_id)
        except Exception:
            page = None
    elif project_name:
        db_id = config.NOTION_PROJECTS_DB_ID
        if db_id:
            matches = notion_client.query_database(
                database_id=db_id,
                filter={
                    "property": "Nombre",
                    "title": {"equals": project_name},
                },
            )
            if matches:
                page = matches[0]

    if page:
        context["page_id"] = str(page.get("id", "")).strip()
        title = _extract_page_title_from_properties(page) or (project_name or "").strip()
        if title:
            context["name"] = title
        icon = _normalize_icon_value(page.get("icon"))
        if icon:
            context["icon"] = icon

    if "icon" not in context and (context.get("name") or project_name):
        inferred = _infer_icon_from_text(context.get("name"), project_name, fallback="📁")
        if inferred:
            context["icon"] = inferred

    return context


def _infer_report_icon(input_data: Dict[str, Any]) -> str:
    metadata = input_data.get("metadata") or {}
    title = str(input_data.get("title") or "")
    project_name = str(metadata.get("project_name") or metadata.get("project") or "")
    project_context = _resolve_project_context(project_name=project_name) if project_name else {}
    if project_context.get("icon"):
        return project_context["icon"]
    return _infer_icon_from_text(title, str(metadata), fallback="📝") or "📝"


def _today_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _strip_date_from_name(text: str) -> str:
    if not text:
        return ""
    value = _DATE_IN_NAME_RE.sub("", text)
    value = value.replace("—", "-")
    value = re.sub(r"\s*-\s*$", "", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip(" -_/")


def _humanize_slug(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    normalized = raw.replace("_", " ").replace("-", " ")
    parts = [part for part in normalized.split() if part]
    if not parts:
        return raw

    human_parts: list[str] = []
    for token in parts:
        lower = token.lower()
        if lower in _SLUG_TOKEN_MAP:
            human_parts.append(_SLUG_TOKEN_MAP[lower])
        elif token.isupper() and len(token) <= 5:
            human_parts.append(token)
        else:
            human_parts.append(token.capitalize())
    return " ".join(human_parts).strip()


def _normalize_deliverable_name(input_data: Dict[str, Any]) -> str:
    raw_name = _normalize_spaces(str(input_data.get("name") or ""))
    if not raw_name:
        return ""

    without_date = _strip_date_from_name(raw_name)
    if without_date and " " not in without_date and ("-" in raw_name or "_" in raw_name):
        without_date = _humanize_slug(without_date)
    elif without_date and ("-" in without_date or "_" in without_date) and without_date.lower() == without_date:
        without_date = _humanize_slug(without_date)

    normalized = _normalize_spaces(without_date or raw_name)
    if normalized:
        return normalized
    return raw_name


def _infer_deliverable_procedencia(input_data: Dict[str, Any]) -> str:
    explicit = _normalize_spaces(
        str(
            input_data.get("procedencia")
            or input_data.get("provenance")
            or input_data.get("traceability_origin")
            or ""
        )
    )
    if explicit:
        canonical = explicit.replace("ó", "o").replace("í", "i").strip().title()
        if canonical in _PROCEDENCIA_ENTREGABLE_VALID:
            return canonical

    if input_data.get("source_task_id"):
        return "Tarea"

    haystack = " ".join(
        str(input_data.get(key) or "")
        for key in ("name", "summary", "notes", "next_action")
    ).lower()
    if any(hint in haystack for hint in _SMOKE_DELIVERABLE_HINTS):
        return "Smoke"

    review_status = str(input_data.get("review_status") or "").strip()
    if review_status in {"Archivado", "Aprobado"}:
        return "Historico"

    return "Manual"


def _parse_date(value: str | None) -> datetime:
    raw = (value or "").strip()
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _suggest_due_date(input_data: Dict[str, Any]) -> str | None:
    explicit = (input_data.get("suggested_due_date") or "").strip()
    if explicit:
        return explicit

    review_status = str(input_data.get("review_status") or "").strip()
    if review_status in {"Aprobado", "Archivado"}:
        return None

    deliverable_type = str(input_data.get("deliverable_type") or "").strip()
    base_date = _parse_date(str(input_data.get("date") or "")).date()
    days_by_type = {
        "Benchmark": 3,
        "Reporte": 3,
        "Auditoria": 4,
        "Borrador": 2,
        "Pieza editorial": 2,
        "Criterio / base de conocimiento": 5,
        "Plan": 5,
    }
    delta_days = days_by_type.get(deliverable_type, 3)
    return (base_date + timedelta(days=delta_days)).strftime("%Y-%m-%d")


def _build_project_page_blocks(input_data: Dict[str, Any]) -> list[Dict[str, Any]]:
    name = str(input_data.get("name") or "Proyecto sin nombre").strip()
    estado = str(input_data.get("estado") or "Activo").strip() or "Activo"
    responsable = str(input_data.get("responsable") or "David Moreira").strip() or "David Moreira"
    agentes = input_data.get("agentes") or []
    if isinstance(agentes, str):
        agentes = [item.strip() for item in agentes.split(",") if item.strip()]
    agentes_text = ", ".join(agentes) if agentes else "Sin agentes definidos"
    sprint = str(input_data.get("sprint") or "Sin sprint").strip() or "Sin sprint"
    linear_url = str(input_data.get("linear_project_url") or "").strip()
    shared_path = str(input_data.get("shared_path") or "").strip()
    open_issues = input_data.get("open_issues")
    open_issues_text = str(open_issues) if open_issues is not None else "Sin dato"
    bloqueos = _normalize_spaces(str(input_data.get("bloqueos") or "")) or "Sin bloqueos registrados."
    next_action = _normalize_spaces(str(input_data.get("next_action") or "")) or "Definir siguiente accion."
    last_update = str(input_data.get("last_update_date") or "").strip() or _today_date()

    blocks: list[Dict[str, Any]] = [
        _block_callout(f"{name} — estado {estado}. Esta pagina resume el estado operativo oficial del proyecto.", emoji="📁"),
        _block_heading2("Resumen operativo"),
        _block_bulleted(f"Responsable: {responsable}"),
        _block_bulleted(f"Agentes: {agentes_text}"),
        _block_bulleted(f"Sprint: {sprint}"),
        _block_bulleted(f"Issues abiertas: {open_issues_text}"),
        _block_bulleted(f"Ultimo update: {last_update}"),
    ]
    if linear_url:
        blocks.append(_block_bulleted(f"Linear: {linear_url}"))
    if shared_path:
        blocks.append(_block_bulleted(f"Ruta compartida: {shared_path}"))

    blocks.extend(
        [
            _block_heading2("Bloqueos actuales"),
            _block_paragraph(bloqueos),
            _block_heading2("Siguiente accion"),
            _block_paragraph(next_action),
            _block_heading2("Uso de esta pagina"),
            _block_bulleted("Mantener aqui un resumen legible del estado real del proyecto."),
            _block_bulleted("Usar la base de tareas para ejecucion y la base de entregables para revision."),
        ]
    )
    return blocks


def _build_deliverable_page_blocks(input_data: Dict[str, Any], project_context: Dict[str, str] | None = None) -> list[Dict[str, Any]]:
    project_context = project_context or {}
    name = _normalize_deliverable_name(input_data)
    project_name = project_context.get("name") or str(input_data.get("project_name") or "").strip() or "Sin proyecto"
    deliverable_type = str(input_data.get("deliverable_type") or "Entregable").strip() or "Entregable"
    review_status = str(input_data.get("review_status") or "Pendiente revision").strip() or "Pendiente revision"
    summary = _normalize_spaces(str(input_data.get("summary") or "")) or "Sin resumen registrado."
    notes = _normalize_spaces(str(input_data.get("notes") or "")) or "Sin observaciones registradas."
    next_action = _normalize_spaces(str(input_data.get("next_action") or "")) or "Definir siguiente accion."
    artifact_url = str(input_data.get("artifact_url") or "").strip()
    artifact_path = str(input_data.get("artifact_path") or "").strip()
    linear_issue = str(input_data.get("linear_issue_url") or "").strip()
    date_value = str(input_data.get("date") or "").strip() or _today_date()
    suggested_due_date = _suggest_due_date(input_data) or "Sin sugerencia"
    agent = str(input_data.get("agent") or "Rick").strip() or "Rick"
    procedencia = _infer_deliverable_procedencia(input_data)
    source_task_id = str(input_data.get("source_task_id") or "").strip()

    blocks: list[Dict[str, Any]] = [
        _block_callout(f"{deliverable_type} para {project_name} — estado de revision: {review_status}.", emoji="📬"),
        _block_heading2("Resumen"),
        _block_paragraph(summary),
        _block_heading2("Ficha rapida"),
        _block_bulleted(f"Proyecto: {project_name}"),
        _block_bulleted(f"Tipo: {deliverable_type}"),
        _block_bulleted(f"Agente: {agent}"),
        _block_bulleted(f"Procedencia: {procedencia}"),
        _block_bulleted(f"Fecha del entregable: {date_value}"),
        _block_bulleted(f"Fecha limite sugerida: {suggested_due_date}"),
    ]
    if source_task_id:
        blocks.append(_block_bulleted(f"Task ID origen: {source_task_id}"))
    if artifact_path:
        blocks.append(_block_bulleted(f"Ruta artefacto: {artifact_path}"))
    if artifact_url:
        blocks.append(_block_bulleted(f"URL artefacto: {artifact_url}"))
    if linear_issue:
        blocks.append(_block_bulleted(f"Linear Issue: {linear_issue}"))

    blocks.extend(
        [
            _block_heading2("Observaciones"),
            _block_paragraph(notes),
            _block_heading2("Siguiente accion"),
            _block_paragraph(next_action),
        ]
    )
    return blocks


def _build_bridge_properties(input_data: Dict[str, Any]) -> Dict[str, Any]:
    props: Dict[str, Any] = {}

    name = _normalize_spaces(str(input_data.get("name") or "")) or _normalize_spaces(str(input_data.get("item") or ""))
    if name:
        props["Ítem"] = {"title": [{"text": {"content": name[:2000]}}]}

    status = _normalize_spaces(str(input_data.get("status") or "")) or "Nuevo"
    if status not in _BRIDGE_STATUS_VALID:
        status = "Nuevo"
    props["Estado"] = {"status": {"name": status}}

    last_move = _normalize_spaces(str(input_data.get("last_move_date") or "")) or _today_date()
    props["Último movimiento"] = {"date": {"start": last_move}}

    notes = _normalize_spaces(str(input_data.get("notes") or ""))
    if notes:
        props["Notas"] = {"rich_text": [{"text": {"content": notes[:2000]}}]}

    project_name = _normalize_spaces(str(input_data.get("project_name") or ""))
    if project_name:
        props["Proyecto"] = {"rich_text": [{"text": {"content": project_name[:2000]}}]}

    priority = _normalize_spaces(str(input_data.get("priority") or "")) or "Media"
    if priority not in _BRIDGE_PRIORITY_VALID:
        priority = "Media"
    props["Prioridad"] = {"select": {"name": priority}}

    source = _normalize_spaces(str(input_data.get("source") or "")) or "Manual"
    if source not in _BRIDGE_SOURCE_VALID:
        source = "Manual"
    props["Origen"] = {"select": {"name": source}}

    next_action = _normalize_spaces(str(input_data.get("next_action") or ""))
    if next_action:
        props["Siguiente acción"] = {"rich_text": [{"text": {"content": next_action[:2000]}}]}

    link = str(input_data.get("link") or "").strip()
    if link:
        props["Link"] = {"url": link}

    return props


def _build_bridge_page_blocks(input_data: Dict[str, Any]) -> list[Dict[str, Any]]:
    name = _normalize_spaces(str(input_data.get("name") or "")) or _normalize_spaces(str(input_data.get("item") or "")) or "Ítem puente"
    status = _normalize_spaces(str(input_data.get("status") or "")) or "Nuevo"
    project_name = _normalize_spaces(str(input_data.get("project_name") or "")) or "Sin proyecto"
    priority = _normalize_spaces(str(input_data.get("priority") or "")) or "Media"
    source = _normalize_spaces(str(input_data.get("source") or "")) or "Manual"
    next_action = _normalize_spaces(str(input_data.get("next_action") or "")) or "Definir siguiente acción."
    notes = _normalize_spaces(str(input_data.get("notes") or "")) or "Sin notas registradas."
    link = str(input_data.get("link") or "").strip()

    blocks: list[Dict[str, Any]] = [
        _block_callout(f"Ítem puente {status.lower()} para coordinación operativa.", emoji="📮"),
        _block_heading2("Resumen"),
        _block_paragraph(name),
        _block_heading2("Ficha rápida"),
        _block_bulleted(f"Proyecto: {project_name}"),
        _block_bulleted(f"Prioridad: {priority}"),
        _block_bulleted(f"Origen: {source}"),
        _block_bulleted(f"Último movimiento: {_normalize_spaces(str(input_data.get('last_move_date') or '')) or _today_date()}"),
        _block_heading2("Siguiente acción"),
        _block_paragraph(next_action),
        _block_heading2("Notas"),
        _block_paragraph(notes),
    ]
    if link:
        blocks.insert(8, _block_bulleted(f"Link: {link}"))
    return blocks


def _build_task_page_blocks(input_data: Dict[str, Any], project_context: Dict[str, str] | None = None, deliverable_name: str | None = None) -> list[Dict[str, Any]]:
    project_context = project_context or {}
    task = str(input_data.get("task") or "Tarea").strip() or "Tarea"
    human_task_name = _normalize_spaces(str(input_data.get("task_name") or "")) or task
    status = str(input_data.get("status") or "queued").strip() or "queued"
    team = str(input_data.get("team") or "system").strip() or "system"
    task_id = str(input_data.get("task_id") or "").strip()
    project_name = project_context.get("name") or str(input_data.get("project_name") or "").strip() or "Sin proyecto"
    linked_deliverable = deliverable_name or str(input_data.get("deliverable_name") or "").strip()
    input_summary = _normalize_spaces(str(input_data.get("input_summary") or "")) or "Sin input resumido."
    result_summary = _normalize_spaces(str(input_data.get("result_summary") or "")) or "Sin resultado resumido todavia."
    error = _normalize_spaces(str(input_data.get("error") or ""))
    source = _normalize_spaces(str(input_data.get("source") or "")) or "Sin origen declarado"
    source_kind = _normalize_spaces(str(input_data.get("source_kind") or "")) or "Sin tipo de origen"
    trace_id = _normalize_spaces(str(input_data.get("trace_id") or "")) or "Sin trace id"
    selected_model = _normalize_spaces(str(input_data.get("selected_model") or "")) or "Sin modelo registrado"

    blocks: list[Dict[str, Any]] = [
        _block_callout(f"Tarea {status} del equipo {team}.", emoji="🗂️"),
        _block_heading2("Que hace esta tarea"),
        _block_paragraph(human_task_name),
        _block_heading2("Contexto"),
        _block_bulleted(f"Proyecto: {project_name}"),
        _block_bulleted(f"Entregable: {linked_deliverable or 'Sin entregable asociado'}"),
        _block_heading2("Input resumido"),
        _block_paragraph(input_summary),
        _block_heading2("Resultado resumido"),
        _block_paragraph(result_summary),
    ]
    if error:
        blocks.extend(
            [
                _block_heading2("Error o bloqueo"),
                _block_paragraph(error),
            ]
        )
    return blocks


def _ensure_page_blocks(page_id: str, blocks: list[Dict[str, Any]], *, force_replace: bool = False) -> None:
    if not page_id or not blocks:
        return
    if force_replace:
        notion_client.replace_blocks_in_page(page_id=page_id, blocks=blocks)
        return
    try:
        snapshot = notion_client.read_page(page_id_or_url=page_id, max_blocks=10)
    except Exception:
        snapshot = None
    if snapshot and str(snapshot.get("plain_text") or "").strip():
        return
    notion_client.append_blocks_to_page(page_id=page_id, blocks=blocks)


def _build_project_properties(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build raw Notion properties for 📁 Proyectos — Umbral from handler input."""
    props: Dict[str, Any] = {}

    name = (input_data.get("name") or "").strip()
    if name:
        props["Nombre"] = {"title": [{"text": {"content": name}}]}

    estado = input_data.get("estado")
    if estado and estado in _ESTADO_VALID:
        props["Estado"] = {"select": {"name": estado}}

    linear_url = input_data.get("linear_project_url")
    if linear_url:
        props["Linear Project"] = {"url": linear_url}

    shared_path = input_data.get("shared_path")
    if shared_path:
        props["Ruta compartida"] = {"rich_text": [{"text": {"content": shared_path}}]}

    responsable = input_data.get("responsable")
    if responsable:
        props["Responsable"] = {"rich_text": [{"text": {"content": responsable}}]}

    agentes = input_data.get("agentes")
    if agentes:
        if isinstance(agentes, str):
            agentes = [a.strip() for a in agentes.split(",") if a.strip()]
        valid_agentes = [a for a in agentes if a in _AGENTES_VALID]
        if valid_agentes:
            props["Agentes"] = {"multi_select": [{"name": a} for a in valid_agentes]}

    sprint = input_data.get("sprint")
    if sprint:
        props["Sprint"] = {"rich_text": [{"text": {"content": str(sprint)}}]}

    start_date = input_data.get("start_date")
    if start_date:
        props["Inicio"] = {"date": {"start": start_date}}

    target_date = input_data.get("target_date")
    if target_date:
        props["Objetivo"] = {"date": {"start": target_date}}

    open_issues = input_data.get("open_issues")
    if open_issues is not None:
        props["Issues abiertas"] = {"number": int(open_issues)}

    bloqueos = input_data.get("bloqueos")
    if bloqueos:
        props["Bloqueos"] = {"rich_text": [{"text": {"content": bloqueos}}]}

    next_action = input_data.get("next_action")
    if next_action:
        props["Siguiente acción"] = {"rich_text": [{"text": {"content": next_action}}]}

    last_update = input_data.get("last_update_date")
    if last_update:
        props["Último update"] = {"date": {"start": last_update}}

    return props


def _lookup_project_page_id(project_name: str) -> str | None:
    """Resolve a project page id in the projects registry by exact Nombre."""
    db_id = config.NOTION_PROJECTS_DB_ID
    if not db_id or not project_name:
        return None

    matches = notion_client.query_database(
        database_id=db_id,
        filter={
            "property": "Nombre",
            "title": {"equals": project_name},
        },
    )
    if not matches:
        return None
    return matches[0]["id"]


def _build_deliverable_properties(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build raw Notion properties for the deliverables review registry."""
    props: Dict[str, Any] = {}

    name = _normalize_deliverable_name(input_data)
    if name:
        props["Nombre"] = {"title": [{"text": {"content": name}}]}

    project_page_id = (input_data.get("project_page_id") or "").strip()
    project_name = (input_data.get("project_name") or "").strip()
    if not project_page_id and project_name:
        project_page_id = _lookup_project_page_id(project_name) or ""
    if project_page_id:
        props["Proyecto"] = {"relation": [{"id": project_page_id}]}

    deliverable_type = input_data.get("deliverable_type")
    if deliverable_type and deliverable_type in _TIPO_ENTREGABLE_VALID:
        props["Tipo"] = {"select": {"name": deliverable_type}}

    review_status = input_data.get("review_status")
    if review_status and review_status in _ESTADO_REVISION_VALID:
        props["Estado revision"] = {"select": {"name": review_status}}

    procedencia = _infer_deliverable_procedencia(input_data)
    if procedencia in _PROCEDENCIA_ENTREGABLE_VALID:
        props["Procedencia"] = {"select": {"name": procedencia}}

    date_value = input_data.get("date")
    if date_value:
        props["Fecha"] = {"date": {"start": date_value}}

    suggested_due_date = _suggest_due_date(input_data)
    if suggested_due_date:
        props["Fecha limite sugerida"] = {"date": {"start": suggested_due_date}}

    agent = input_data.get("agent")
    if agent and agent in _AGENTES_VALID:
        props["Agente"] = {"select": {"name": agent}}

    summary = input_data.get("summary")
    if summary:
        props["Resumen"] = {"rich_text": [{"text": {"content": str(summary)}}]}

    artifact_url = input_data.get("artifact_url")
    if artifact_url:
        props["URL artefacto"] = {"url": str(artifact_url)}

    artifact_path = input_data.get("artifact_path")
    if artifact_path:
        props["Ruta artefacto"] = {"rich_text": [{"text": {"content": str(artifact_path)}}]}

    notes = input_data.get("notes")
    if notes:
        props["Observaciones"] = {"rich_text": [{"text": {"content": str(notes)}}]}

    next_action = input_data.get("next_action")
    if next_action:
        props["Siguiente accion"] = {"rich_text": [{"text": {"content": str(next_action)}}]}

    linear_issue_url = input_data.get("linear_issue_url")
    if linear_issue_url:
        props["Linear Issue"] = {"url": str(linear_issue_url)}

    source_task_id = input_data.get("source_task_id")
    if source_task_id:
        props["Task ID origen"] = {"rich_text": [{"text": {"content": str(source_task_id)}}]}

    last_update = input_data.get("last_update_date")
    if last_update:
        props["Ultima actualizacion"] = {"date": {"start": last_update}}

    return props


def handle_notion_upsert_project(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea o actualiza un proyecto en la DB 📁 Proyectos — Umbral.

    Input:
        name (str, required): nombre del proyecto (clave de búsqueda).
        estado (str, optional): Activo|En pausa|Completado|Archivado.
        linear_project_url (str, optional): URL del proyecto en Linear.
        shared_path (str, optional): ruta compartida (ej. G:\\Mi unidad\\...).
        responsable (str, optional): nombre del responsable humano.
        agentes (str|list, optional): Rick, Claude, Codex, Cursor, Antigravity.
        sprint (str, optional): sprint actual (ej. R21).
        start_date (str, optional): YYYY-MM-DD.
        target_date (str, optional): YYYY-MM-DD.
        open_issues (int, optional): número de issues abiertas en Linear.
        bloqueos (str, optional): bloqueos actuales.
        next_action (str, optional): siguiente acción concreta.
        last_update_date (str, optional): YYYY-MM-DD del último update.
        icon (str, optional): emoji o URL externa para el icono de la fila/pagina.

    Returns:
        {"ok": True, "page_id": "...", "url": "...", "created": bool}
    """
    name = (input_data.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "'name' is required"}

    db_id = config.NOTION_PROJECTS_DB_ID
    if not db_id:
        return {"ok": False, "error": "NOTION_PROJECTS_DB_ID not configured on server"}

    try:
        existing = notion_client.query_database(
            database_id=db_id,
            filter={
                "property": "Nombre",
                "title": {"equals": name},
            },
        )
    except Exception as e:
        return {"ok": False, "error": f"Failed to query projects DB: {e}"}

    props = _build_project_properties(input_data)
    page_blocks = _build_project_page_blocks(input_data)

    resolved_icon = input_data.get("icon")
    if not resolved_icon:
        resolved_icon = _infer_icon_from_text(name, fallback="📁")

    try:
        if existing:
            page_id = existing[0]["id"]
            result = notion_client.update_page_properties(
                page_id_or_url=page_id,
                properties=props,
                icon=resolved_icon,
            )
            _ensure_page_blocks(page_id=result["page_id"], blocks=page_blocks, force_replace=True)
            _maybe_trigger_openclaw_panel_refresh(
                "project_upsert",
                source="notion.upsert_project",
            )
            return {"ok": True, "page_id": result["page_id"], "url": result["url"], "created": False}
        else:
            result = notion_client.create_database_page(
                database_id_or_url=db_id,
                properties=props,
                children=page_blocks,
                icon=resolved_icon,
            )
            _maybe_trigger_openclaw_panel_refresh(
                "project_upsert",
                source="notion.upsert_project",
            )
            return {"ok": True, "page_id": result["page_id"], "url": result["url"], "created": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_notion_upsert_deliverable(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create or update a reviewable deliverable in the deliverables registry.

    Input:
        name (str, required): deliverable title and lookup key.
        project_name (str, optional): exact project name in Projects registry.
        project_page_id (str, optional): project page id if already known.
        deliverable_type (str, optional): Benchmark|Reporte|Borrador|Pieza editorial|Criterio / base de conocimiento|Plan|Auditoria.
        review_status (str, optional): Pendiente revision|Aprobado|Aprobado con ajustes|Rechazado|Archivado.
        date (str, optional): YYYY-MM-DD.
        agent (str, optional): Rick|Claude|Codex|Cursor|Antigravity.
        summary (str, optional): short summary.
        artifact_url (str, optional): canonical URL to the artifact.
        artifact_path (str, optional): canonical shared path.
        notes (str, optional): review notes or context.
        next_action (str, optional): next concrete action.
        linear_issue_url (str, optional): related Linear issue.
        source_task_id (str, optional): runtime task id if any.
        last_update_date (str, optional): YYYY-MM-DD.
        icon (str, optional): emoji o URL externa para el icono de la fila/pagina.

    Returns:
        {"ok": True, "page_id": "...", "url": "...", "created": bool}
    """
    original_name = (input_data.get("name") or "").strip()
    name = _normalize_deliverable_name(input_data)
    if not name:
        return {"ok": False, "error": "'name' is required"}
    input_data = {**input_data, "name": name}

    db_id = config.NOTION_DELIVERABLES_DB_ID
    if not db_id:
        return {"ok": False, "error": "NOTION_DELIVERABLES_DB_ID not configured on server"}

    raw_name = original_name

    try:
        existing = notion_client.query_database(
            database_id=db_id,
            filter={
                "property": "Nombre",
                "title": {"equals": name},
            },
        )
        if not existing and raw_name and raw_name != name:
            existing = notion_client.query_database(
                database_id=db_id,
                filter={
                    "property": "Nombre",
                    "title": {"equals": raw_name},
                },
            )
    except Exception as e:
        return {"ok": False, "error": f"Failed to query deliverables DB: {e}"}

    project_context = _resolve_project_context(
        project_name=(input_data.get("project_name") or "").strip() or None,
        project_page_id=(input_data.get("project_page_id") or "").strip() or None,
    )
    if project_context.get("page_id") and not input_data.get("project_page_id"):
        input_data = {**input_data, "project_page_id": project_context["page_id"]}

    try:
        props = _build_deliverable_properties(input_data)
    except Exception as e:
        return {"ok": False, "error": f"Failed to build deliverable properties: {e}"}
    page_blocks = _build_deliverable_page_blocks(input_data, project_context=project_context)

    resolved_icon = input_data.get("icon") or project_context.get("icon")
    if not resolved_icon:
        resolved_icon = _DELIVERABLE_TYPE_ICONS.get(str(input_data.get("deliverable_type") or "").strip())
    if not resolved_icon:
        resolved_icon = _infer_icon_from_text(
            str(input_data.get("name") or ""),
            str(input_data.get("summary") or ""),
            fallback="📝",
        )

    try:
        if existing:
            page_id = existing[0]["id"]
            result = notion_client.update_page_properties(
                page_id_or_url=page_id,
                properties=props,
                icon=resolved_icon,
            )
            _ensure_page_blocks(page_id=result["page_id"], blocks=page_blocks, force_replace=True)
            _maybe_trigger_openclaw_panel_refresh(
                "deliverable_upsert",
                source="notion.upsert_deliverable",
            )
            return {"ok": True, "page_id": result["page_id"], "url": result["url"], "created": False}

        result = notion_client.create_database_page(
            database_id_or_url=db_id,
            properties=props,
            children=page_blocks,
            icon=resolved_icon,
        )
        _maybe_trigger_openclaw_panel_refresh(
            "deliverable_upsert",
            source="notion.upsert_deliverable",
        )
        return {"ok": True, "page_id": result["page_id"], "url": result["url"], "created": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_notion_upsert_bridge_item(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create or update an operational inbox item in `Bandeja Puente`.

    Input:
        name (str, required): title of the bridge item.
        status (str, optional): Nuevo|En curso|Esperando|Resuelto.
        project_name (str, optional): human-readable project name.
        priority (str, optional): Alta|Media|Baja.
        source (str, optional): Rick|David|Sistema|Control Room|Proyecto|Entregable|Manual.
        notes (str, optional): context or coordination notes.
        next_action (str, optional): next concrete action.
        last_move_date (str, optional): YYYY-MM-DD.
        link (str, optional): canonical URL if any.
        page_id (str, optional): explicit Notion page id to update in-place.
        icon (str, optional): emoji or external icon URL.

    Returns:
        {"ok": True, "page_id": "...", "url": "...", "created": bool}
    """
    name = _normalize_spaces(str(input_data.get("name") or "")) or _normalize_spaces(str(input_data.get("item") or ""))
    if not name:
        return {"ok": False, "error": "'name' is required"}

    db_id = config.NOTION_BRIDGE_DB_ID
    if not db_id:
        return {"ok": False, "error": "NOTION_BRIDGE_DB_ID not configured on server"}

    page_id = _normalize_spaces(str(input_data.get("page_id") or input_data.get("page_id_or_url") or ""))

    try:
        existing = []
        if page_id:
            existing = [{"id": page_id}]
        else:
            existing = notion_client.query_database(
                database_id=db_id,
                filter={
                    "property": "Ítem",
                    "title": {"equals": name},
                },
            )
            if not existing:
                for row in notion_client.query_database(database_id=db_id):
                    if _extract_page_title_from_properties(row) == name:
                        existing = [row]
                        break
    except Exception as e:
        return {"ok": False, "error": f"Failed to query bridge DB: {e}"}

    props = _build_bridge_properties({**input_data, "name": name})
    page_blocks = _build_bridge_page_blocks({**input_data, "name": name})

    resolved_icon = input_data.get("icon")
    if not resolved_icon:
        resolved_icon = _infer_icon_from_text(
            name,
            input_data.get("project_name"),
            input_data.get("priority"),
            input_data.get("status"),
            fallback="📮",
        )

    try:
        if existing:
            page_id = existing[0]["id"]
            result = notion_client.update_page_properties(
                page_id_or_url=page_id,
                properties=props,
                icon=resolved_icon,
            )
            _ensure_page_blocks(page_id=result["page_id"], blocks=page_blocks, force_replace=True)
            _maybe_trigger_openclaw_panel_refresh(
                "bridge_item_upsert",
                source="notion.upsert_bridge_item",
            )
            return {"ok": True, "page_id": result["page_id"], "url": result["url"], "created": False}

        result = notion_client.create_database_page(
            database_id_or_url=db_id,
            properties=props,
            children=page_blocks,
            icon=resolved_icon,
        )
        _maybe_trigger_openclaw_panel_refresh(
            "bridge_item_upsert",
            source="notion.upsert_bridge_item",
        )
        return {"ok": True, "page_id": result["page_id"], "url": result["url"], "created": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Bitácora enrichment
# ---------------------------------------------------------------------------


def _sections_to_blocks(sections: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """
    Convert high-level section dicts to Notion API block arrays.

    Each section may contain:
        - title (str): heading_2
        - content (str): paragraphs split on double newlines
        - mermaid (str): code block with language="mermaid"
        - items (list[str]): bulleted list items
        - table (dict): {"headers": [...], "rows": [[...]]}
    A divider is appended after each section.
    """
    blocks: list[Dict[str, Any]] = []

    for section in sections:
        title = section.get("title")
        if title:
            blocks.append(_block_heading2(title))

        content = section.get("content")
        if content:
            for paragraph in content.split("\n\n"):
                paragraph = paragraph.strip()
                if paragraph:
                    blocks.append(_block_paragraph(paragraph))

        mermaid = section.get("mermaid")
        if mermaid:
            blocks.append(_block_code(mermaid, "mermaid"))

        items = section.get("items")
        if items:
            for item in items:
                blocks.append(_block_bulleted(item))

        table = section.get("table")
        if table:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            blocks.append(_block_table(headers, rows))

        blocks.append(_block_divider())

    return blocks


def _raw_blocks_to_notion(raw_blocks: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """
    Convert simplified raw block dicts to full Notion API block format.

    Supported raw formats:
        {"type": "heading_1", "text": "..."}
        {"type": "heading_2", "text": "..."}
        {"type": "heading_3", "text": "..."}
        {"type": "paragraph", "text": "..."}
        {"type": "code", "language": "mermaid", "text": "..."}
        {"type": "bulleted_list_item", "text": "..."}
        {"type": "divider"}
        {"type": "callout", "text": "...", "emoji": "⚠️"}
        {"type": "quote", "text": "..."}
        {"type": "table", "rows": [["H1","H2"], ["a","b"]]}

    Unknown types default to paragraph.
    """
    _BLOCK_MAP = {
        "heading_1": lambda b: _block_heading1(b.get("text", "")),
        "heading_2": lambda b: _block_heading2(b.get("text", "")),
        "heading_3": lambda b: _block_heading3(b.get("text", "")),
        "paragraph": lambda b: _block_paragraph(b.get("text", "")),
        "code": lambda b: _block_code(b.get("text", ""), b.get("language", "plain text")),
        "bulleted_list_item": lambda b: _block_bulleted(b.get("text", "")),
        "divider": lambda b: _block_divider(),
        "callout": lambda b: _block_callout(b.get("text", ""), b.get("emoji", "💡")),
        "quote": lambda b: _block_quote(b.get("text", "")),
        "table": lambda b: _block_table(
            b.get("rows", [[]])[0] if b.get("rows") else [],
            b.get("rows", [[]])[1:] if b.get("rows") else [],
        ),
    }

    blocks: list[Dict[str, Any]] = []
    for raw in raw_blocks:
        block_type = raw.get("type", "paragraph")
        builder = _BLOCK_MAP.get(block_type, _BLOCK_MAP["paragraph"])
        blocks.append(builder(raw))
    return blocks


def handle_notion_enrich_bitacora_page(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich a Bitácora page by appending structured content blocks.

    Input:
        page_id (str, required): Notion page ID.
        sections (list[dict], optional): High-level section dicts.
        blocks (list[dict], optional): Raw block dicts.

    At least one of 'sections' or 'blocks' must be provided.

    Returns:
        {"blocks_appended": N, "page_id": "..."}
    """
    page_id = input_data.get("page_id")
    if not page_id:
        raise ValueError("'page_id' is required in input")

    sections = input_data.get("sections")
    raw_blocks = input_data.get("blocks")

    if sections is None and raw_blocks is None:
        raise ValueError("Either 'blocks' or 'sections' must be provided in input")

    if sections is not None:
        notion_blocks = _sections_to_blocks(sections)
    else:
        notion_blocks = _raw_blocks_to_notion(raw_blocks)

    return notion_client.append_blocks_to_page(page_id, notion_blocks)
