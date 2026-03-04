"""
Tasks: Granola → Notion pipeline handlers.

- granola.process_transcript: recibe transcripción parseada, crea página en
  Notion, extrae action items, notifica a Enlace.
- granola.create_followup: genera follow-up proactivo (reminder, email draft,
  proposal) a partir de una transcripción ya subida.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from .. import config, notion_client
from .notion_markdown import markdown_to_blocks

logger = logging.getLogger("worker.tasks.granola")

FOLLOWUP_TYPES = ("reminder", "email_draft", "proposal")


def _extract_action_items(content: str) -> list[str]:
    """Best-effort extraction of action items from markdown content.

    Looks for:
    - Checkbox items: ``- [ ] text`` / ``- [x] text``
    - Bullet items under headings containing keywords like "action",
      "tareas", "compromisos", "pendientes", "to-do".
    """
    lines = content.split("\n")
    items: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        if re.match(r"^#{1,3}\s+.*(?:action|tareas|compromisos|pendientes|to.?do)", stripped, re.IGNORECASE):
            in_section = True
            continue

        if in_section and re.match(r"^#{1,3}\s+", stripped):
            in_section = False

        if in_section and re.match(r"^[-*]\s+", stripped):
            item = re.sub(r"^[-*]\s+", "", stripped).strip()
            if item:
                items.append(item)
            continue

        checkbox = re.match(r"^[-*]\s+\[.\]\s+(.+)", stripped)
        if checkbox:
            items.append(checkbox.group(1).strip())

    return items


def handle_granola_process_transcript(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa una transcripción de Granola y la sube a Notion.

    Input:
        title (str, required): Título de la reunión.
        content (str, required): Transcripción completa en markdown.
        date (str, optional): Fecha ISO de la reunión (default: hoy UTC).
        attendees (list[str], optional): Lista de participantes.
        action_items (list[str], optional): Action items ya parseados por el
            watcher.  Si no se proveen, se extraen del contenido.

    Returns:
        {
            "page_id": "...",
            "url": "...",
            "action_items_created": N,
            "comment_id": "..."
        }
    """
    title = input_data.get("title")
    content = input_data.get("content")
    if not title or not content:
        raise ValueError("'title' and 'content' are required in input")

    date = input_data.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    attendees: list[str] = input_data.get("attendees") or []
    action_items: list[str] = input_data.get("action_items") or _extract_action_items(content)

    enriched_content = content
    if attendees:
        attendee_line = f"\n\n**Participantes:** {', '.join(attendees)}"
        enriched_content = attendee_line + "\n\n" + content

    page_result = notion_client.create_transcript_page(
        title=title,
        content=enriched_content,
        source="granola",
        date=date,
    )
    page_id = page_result["page_id"]
    page_url = page_result.get("url", "")

    logger.info("Transcripción '%s' subida a Notion: %s", title, page_id)

    comment_id = None
    try:
        comment_result = notion_client.add_comment(
            page_id=page_id,
            text="Transcripción lista para optimizar — procesada automáticamente por Granola Pipeline.",
        )
        comment_id = comment_result.get("comment_id")
    except Exception as exc:
        logger.warning("No se pudo agregar comentario en la página: %s", exc)

    items_created = 0
    for item in action_items:
        try:
            task_id = str(uuid.uuid4())
            notion_client.upsert_task(
                task_id=task_id,
                status="queued",
                team="granola-followup",
                task=item[:200],
                input_summary=f"Reunión: {title} ({date})",
            )
            items_created += 1
        except Exception as exc:
            logger.warning("No se pudo crear tarea para action item '%s': %s", item[:60], exc)

    logger.info(
        "Pipeline completo: page=%s, action_items=%d/%d",
        page_id, items_created, len(action_items),
    )

    return {
        "page_id": page_id,
        "url": page_url,
        "action_items_created": items_created,
        "action_items_total": len(action_items),
        "comment_id": comment_id,
    }


def handle_granola_create_followup(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un follow-up proactivo basado en una transcripción.

    Input:
        transcript_page_id (str, required): ID de la página Notion de la
            transcripción.
        followup_type (str, required): Tipo de follow-up.
            - "reminder": crea tarea en Notion con fecha límite.
            - "email_draft": genera borrador de email como página hija.
            - "proposal": genera borrador de propuesta como página hija.
        title (str, required): Título o asunto del follow-up.
        due_date (str, optional): Fecha límite ISO (para reminder).
        body (str, optional): Contenido del follow-up (para email_draft
            y proposal).  Se puede enviar en markdown.
        assignee (str, optional): A quién va dirigido.

    Returns:
        {"ok": True, "followup_type": "...", "result": {...}}
    """
    transcript_page_id = input_data.get("transcript_page_id")
    followup_type = input_data.get("followup_type")
    title = input_data.get("title")

    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")
    if not followup_type or followup_type not in FOLLOWUP_TYPES:
        raise ValueError(f"'followup_type' must be one of {FOLLOWUP_TYPES}")
    if not title:
        raise ValueError("'title' is required in input")

    due_date = input_data.get("due_date")
    body = input_data.get("body", "")
    assignee = input_data.get("assignee", "")

    if followup_type == "reminder":
        task_id = str(uuid.uuid4())
        result = notion_client.upsert_task(
            task_id=task_id,
            status="queued",
            team="granola-followup",
            task=title,
            input_summary=f"Reminder de transcripción {transcript_page_id[:8]}. "
                          f"Asignado: {assignee or 'N/A'}. "
                          f"Fecha límite: {due_date or 'sin fecha'}.",
        )
        return {"ok": True, "followup_type": "reminder", "result": result}

    if followup_type == "email_draft":
        email_md = f"# Borrador de Email: {title}\n\n"
        if assignee:
            email_md += f"**Para:** {assignee}\n\n"
        email_md += body or "_Sin contenido proporcionado._"
        email_md += f"\n\n---\n_Generado desde transcripción {transcript_page_id[:8]}_"

        content_blocks = markdown_to_blocks(email_md)
        result = notion_client.create_report_page(
            parent_page_id=transcript_page_id,
            title=f"Email Draft: {title}",
            content_blocks=content_blocks,
            metadata={
                "type": "email_draft",
                "assignee": assignee,
                "source_transcript": transcript_page_id,
            },
        )
        return {"ok": True, "followup_type": "email_draft", "result": result}

    if followup_type == "proposal":
        proposal_md = f"# Propuesta: {title}\n\n"
        proposal_md += body or "_Sin contenido proporcionado. Rick debe completar._"
        proposal_md += f"\n\n---\n_Generado desde transcripción {transcript_page_id[:8]}_"

        content_blocks = markdown_to_blocks(proposal_md)
        result = notion_client.create_report_page(
            parent_page_id=transcript_page_id,
            title=f"Propuesta: {title}",
            content_blocks=content_blocks,
            metadata={
                "type": "proposal",
                "assignee": assignee,
                "source_transcript": transcript_page_id,
            },
        )
        return {"ok": True, "followup_type": "proposal", "result": result}

    raise ValueError(f"followup_type '{followup_type}' not implemented")
