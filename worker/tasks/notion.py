"""
Tasks: Notion integration handlers.

- notion.write_transcript: crear página en Granola Inbox DB
- notion.add_comment: agregar comentario en Control Room
- notion.poll_comments: leer comentarios recientes
"""

from typing import Any, Dict

from .. import notion_client


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
