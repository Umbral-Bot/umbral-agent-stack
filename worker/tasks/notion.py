"""
Tasks: Notion integration handlers.

- notion.write_transcript: crear página en Granola Inbox DB
- notion.add_comment: agregar comentario en Control Room
- notion.poll_comments: leer comentarios recientes
- notion.create_report_page: crear página hija con reporte estructurado
- notion.enrich_bitacora_page: enriquecer una página existente con bloques
"""

from datetime import datetime, timezone
from typing import Any, Dict

from .. import notion_client
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


def _sections_to_blocks(sections: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Convert a list of simplified section dicts to Notion block dicts."""
    blocks: list[Dict[str, Any]] = []
    for section in sections:
        title = section.get("title", "")
        if title:
            blocks.append(notion_client._block_heading2(title))

        if "content" in section:
            for para in section["content"].split("\n\n"):
                para = para.strip()
                if para:
                    blocks.append(notion_client._block_paragraph(para))

        if "mermaid" in section:
            blocks.append(notion_client._block_code(section["mermaid"], "mermaid"))

        if "items" in section:
            for item in section["items"]:
                blocks.append(notion_client._block_bulleted(str(item)))

        if "table" in section:
            table_data = section["table"]
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])
            if headers and rows:
                blocks.append(notion_client._block_table(headers, rows))

        blocks.append(notion_client._block_divider())

    return blocks


def _raw_blocks_to_notion(raw_blocks: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Convert simplified block dicts to Notion API block format."""
    blocks: list[Dict[str, Any]] = []
    for b in raw_blocks:
        btype = b.get("type", "paragraph")
        text = b.get("text", "")

        if btype == "heading_1":
            blocks.append(notion_client._block_heading1(text))
        elif btype == "heading_2":
            blocks.append(notion_client._block_heading2(text))
        elif btype == "heading_3":
            blocks.append(notion_client._block_heading3(text))
        elif btype == "paragraph":
            blocks.append(notion_client._block_paragraph(text))
        elif btype == "bulleted_list_item":
            blocks.append(notion_client._block_bulleted(text))
        elif btype == "code":
            lang = b.get("language", "plain text")
            blocks.append(notion_client._block_code(text, lang))
        elif btype == "divider":
            blocks.append(notion_client._block_divider())
        elif btype == "callout":
            emoji = b.get("emoji", "💡")
            blocks.append(notion_client._block_callout(text, emoji))
        elif btype == "quote":
            blocks.append(notion_client._block_quote(text))
        elif btype == "table":
            rows = b.get("rows", [])
            if len(rows) >= 2:
                blocks.append(notion_client._block_table(rows[0], rows[1:]))
        else:
            blocks.append(notion_client._block_paragraph(text))

    return blocks


def handle_notion_enrich_bitacora_page(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriquece una página existente de Notion añadiendo bloques de contenido.

    Soporta dos formatos de input:

    Formato A (blocks):
        page_id (str, required): UUID de la página.
        blocks (list[dict]): Lista de bloques simplificados
            {"type": "heading_2", "text": "..."}, {"type": "code", "language": "mermaid", "text": "..."}

    Formato B (sections):
        page_id (str, required): UUID de la página.
        sections (list[dict]): Lista de secciones
            {"title": "Resumen", "content": "...", "mermaid": "...", "items": [...], "table": {...}}

    Returns:
        {"blocks_appended": N, "page_id": "..."}
    """
    page_id = input_data.get("page_id")
    if not page_id:
        raise ValueError("'page_id' is required in input")

    raw_blocks = input_data.get("blocks")
    sections = input_data.get("sections")

    if not raw_blocks and not sections:
        raise ValueError("Either 'blocks' or 'sections' must be provided")

    if sections:
        notion_blocks = _sections_to_blocks(sections)
    else:
        notion_blocks = _raw_blocks_to_notion(raw_blocks)

    return notion_client.append_blocks_to_page(
        page_id=page_id,
        blocks=notion_blocks,
    )
