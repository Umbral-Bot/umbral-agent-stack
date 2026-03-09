"""
Tasks: Notion integration handlers.

- notion.write_transcript: crear página en Granola Inbox DB
- notion.add_comment: agregar comentario en Control Room
- notion.poll_comments: leer comentarios recientes
- notion.read_page: leer metadata y snapshot de una página
- notion.create_report_page: crear página hija con reporte estructurado
- notion.enrich_bitacora_page: enriquecer página de Bitácora con secciones o bloques
"""

from datetime import datetime, timezone
from typing import Any, Dict

from .. import notion_client
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


def handle_notion_upsert_task(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea o actualiza una tarea en la DB Kanban (Tareas Umbral).

    Input:
        task_id (str, required): ID de la tarea.
        status (str, required): queued|running|done|failed|blocked.
        team (str, required): equipo/agente.
        task (str, required): nombre de la tarea.
        input_summary (str, optional): resumen del input.
        error (str, optional): mensaje de error si status=failed.
        result_summary (str, optional): resumen del resultado.

    Returns:
        {"page_id": "...", "updated": True} o {"skipped": True, "reason": "..."}
    """
    task_id = input_data.get("task_id")
    status = input_data.get("status")
    team = input_data.get("team")
    task = input_data.get("task")
    if not all([task_id, status, team, task]):
        raise ValueError("'task_id', 'status', 'team' and 'task' are required in input")

    return notion_client.upsert_task(
        task_id=task_id,
        status=status,
        team=team,
        task=task,
        input_summary=input_data.get("input_summary"),
        error=input_data.get("error"),
        result_summary=input_data.get("result_summary"),
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
    )


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
