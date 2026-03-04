"""
Tasks: Granola pipeline handlers.

- granola.process_transcript: procesa transcript completo → Notion + action items + notificación
- granola.create_followup: follow-up proactivo (reminder, proposal, email_draft)
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

from .. import config, notion_client
from .notion_markdown import markdown_to_blocks

logger = logging.getLogger("worker.granola")

ENLACE_NOTION_USER_ID = config.ENLACE_NOTION_USER_ID if hasattr(config, "ENLACE_NOTION_USER_ID") else None


def _extract_action_items(content: str) -> list[str]:
    """Extract action items from markdown content (checkbox lines)."""
    items: list[str] = []
    lines = content.split("\n")
    action_section = False
    action_heading = re.compile(
        r"^#{1,3}\s*(action\s*items|compromisos|tareas|next\s*steps|pr[oó]ximos\s*pasos)",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()
        if action_heading.match(stripped):
            action_section = True
            continue

        checkbox = re.match(r"^-\s*\[[ x]\]\s*(.+)", stripped, re.IGNORECASE)
        if checkbox:
            items.append(checkbox.group(1).strip())
            continue

        if action_section:
            if stripped.startswith("#") or (not stripped and items):
                action_section = False
                continue
            item = re.sub(r"^[-*]\s*", "", stripped).strip()
            if item:
                items.append(item)

    return items


def handle_granola_process_transcript(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa un transcript de Granola: sube a Notion, notifica a Enlace, crea tareas.

    Input:
        title (str, required): Título de la reunión.
        content (str, required): Contenido completo en Markdown.
        date (str, optional): Fecha ISO (default: hoy).
        attendees (list[str], optional): Lista de participantes.
        action_items (list[str], optional): Action items pre-parseados.
        source (str, optional): Fuente (default: "granola").

    Returns:
        {
            "page_id": "...",
            "page_url": "...",
            "tasks_created": N,
            "comment_added": true/false
        }
    """
    title = input_data.get("title")
    content = input_data.get("content")
    if not title or not content:
        raise ValueError("'title' and 'content' are required in input")

    date = input_data.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    attendees = input_data.get("attendees", [])
    source = input_data.get("source", "granola")

    action_items = input_data.get("action_items") or _extract_action_items(content)

    # --- Step 1: Build enriched Notion page with markdown blocks ---
    header_md = f"# {title}\n\n"
    if date:
        header_md += f"**Fecha:** {date}\n\n"
    if attendees:
        header_md += "**Participantes:** " + ", ".join(attendees) + "\n\n"
    header_md += "---\n\n"

    full_md = header_md + content
    content_blocks = markdown_to_blocks(full_md)

    if action_items:
        content_blocks.append({
            "object": "block", "type": "divider", "divider": {}
        })
        content_blocks.append({
            "object": "block", "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Action Items"}}],
                "color": "default", "is_toggleable": False,
            },
        })
        for item in action_items:
            content_blocks.append({
                "object": "block", "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": item[:2000]}}],
                    "checked": False, "color": "default",
                },
            })

    # --- Step 2: Create page in Granola Inbox DB ---
    page_result = notion_client.create_transcript_page(
        title=title,
        content=content,
        source=source,
        date=date,
    )
    page_id = page_result["page_id"]
    page_url = page_result.get("url", "")

    logger.info("Transcript page created: %s (%s)", page_id, title)

    # --- Step 3: Append rich content blocks ---
    _append_blocks_to_page(page_id, content_blocks)

    # --- Step 4: Add notification comment ---
    comment_added = False
    try:
        attendees_str = ", ".join(attendees) if attendees else "sin participantes listados"
        items_str = f" | {len(action_items)} action items detectados" if action_items else ""
        comment_text = (
            f"Transcripción lista para optimizar. "
            f"Participantes: {attendees_str}{items_str}."
        )
        notion_client.add_comment(page_id=page_id, text=comment_text)
        comment_added = True
        logger.info("Notification comment added to page %s", page_id)
    except Exception as exc:
        logger.warning("Could not add comment to page %s: %s", page_id, exc)

    # --- Step 5: Create tasks for action items ---
    tasks_created = 0
    for idx, item in enumerate(action_items[:20]):
        try:
            task_id = f"granola-{page_id[:8]}-{idx}"
            notion_client.upsert_task(
                task_id=task_id,
                status="queued",
                team="granola",
                task=item[:200],
                input_summary=f"De reunión: {title}",
            )
            tasks_created += 1
        except Exception as exc:
            logger.warning("Could not create task for action item %d: %s", idx, exc)

    return {
        "page_id": page_id,
        "page_url": page_url,
        "tasks_created": tasks_created,
        "action_items_found": len(action_items),
        "comment_added": comment_added,
    }


def _append_blocks_to_page(page_id: str, blocks: list[dict]) -> None:
    """Append blocks to an existing Notion page (batches of 100)."""
    if not blocks:
        return

    import httpx

    headers = {
        "Authorization": f"Bearer {config.NOTION_API_KEY}",
        "Notion-Version": config.NOTION_API_VERSION,
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=60.0) as client:
        for i in range(0, len(blocks), 100):
            batch = blocks[i : i + 100]
            resp = client.patch(
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers=headers,
                json={"children": batch},
            )
            if resp.status_code >= 400:
                logger.warning(
                    "Failed to append blocks batch %d to %s: %s",
                    i // 100, page_id, resp.text[:300],
                )


def handle_granola_create_followup(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea follow-up proactivo a partir de un transcript.

    Input:
        transcript_page_id (str, required): ID de la página de transcript en Notion.
        followup_type (str, required): "reminder" | "proposal" | "email_draft"
        title (str, optional): Título del follow-up.
        due_date (str, optional): Fecha límite ISO (para reminder).
        assignee (str, optional): Persona asignada.
        notes (str, optional): Notas adicionales para el follow-up.

    Returns:
        {"followup_type": "...", "result": {...}}
    """
    transcript_page_id = input_data.get("transcript_page_id")
    followup_type = input_data.get("followup_type")

    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")
    if followup_type not in ("reminder", "proposal", "email_draft"):
        raise ValueError("'followup_type' must be one of: reminder, proposal, email_draft")

    title = input_data.get("title", "Follow-up de reunión")
    due_date = input_data.get("due_date")
    assignee = input_data.get("assignee", "")
    notes = input_data.get("notes", "")

    if followup_type == "reminder":
        return _create_reminder(transcript_page_id, title, due_date, assignee, notes)
    elif followup_type == "proposal":
        return _create_proposal(transcript_page_id, title, notes)
    else:
        return _create_email_draft(transcript_page_id, title, assignee, notes)


def _create_reminder(
    transcript_page_id: str,
    title: str,
    due_date: str | None,
    assignee: str,
    notes: str,
) -> Dict[str, Any]:
    """Create a Notion task as reminder with optional due date."""
    if not due_date:
        due_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    task_id = f"followup-{transcript_page_id[:8]}-{int(datetime.now(timezone.utc).timestamp())}"
    input_summary = f"Reminder: {title}"
    if assignee:
        input_summary += f" (asignado a {assignee})"
    if notes:
        input_summary += f" — {notes[:100]}"

    result = notion_client.upsert_task(
        task_id=task_id,
        status="queued",
        team="granola",
        task=title[:200],
        input_summary=input_summary[:200],
    )

    try:
        notion_client.add_comment(
            page_id=transcript_page_id,
            text=f"Reminder creado: {title} (fecha: {due_date})",
        )
    except Exception as exc:
        logger.warning("Could not add reminder comment: %s", exc)

    return {
        "followup_type": "reminder",
        "result": result,
        "task_id": task_id,
        "due_date": due_date,
    }


def _create_proposal(
    transcript_page_id: str,
    title: str,
    notes: str,
) -> Dict[str, Any]:
    """Create a structured proposal page in Notion as child of transcript."""
    proposal_md = f"# Propuesta: {title}\n\n"
    proposal_md += f"**Generado desde:** transcript {transcript_page_id[:8]}\n\n"
    proposal_md += "---\n\n"
    proposal_md += "## Contexto\n\n"
    proposal_md += (notes or "Basado en la reunión registrada.") + "\n\n"
    proposal_md += "## Propuesta\n\n"
    proposal_md += "_[Rick completará con análisis del transcript]_\n\n"
    proposal_md += "## Próximos pasos\n\n"
    proposal_md += "- [ ] Revisar propuesta\n"
    proposal_md += "- [ ] Enviar al cliente\n"

    content_blocks = markdown_to_blocks(proposal_md)

    result = notion_client.create_report_page(
        parent_page_id=transcript_page_id,
        title=f"Propuesta: {title}",
        content_blocks=content_blocks,
        metadata={
            "type": "proposal",
            "source_transcript": transcript_page_id,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )

    try:
        notion_client.add_comment(
            page_id=transcript_page_id,
            text=f"Propuesta creada: {result.get('page_url', result.get('page_id', '?'))}",
        )
    except Exception as exc:
        logger.warning("Could not add proposal comment: %s", exc)

    return {
        "followup_type": "proposal",
        "result": result,
    }


def _create_email_draft(
    transcript_page_id: str,
    title: str,
    assignee: str,
    notes: str,
) -> Dict[str, Any]:
    """Create an email draft as a Notion page under the transcript."""
    recipient = assignee or "[destinatario]"

    draft_md = f"# Borrador de email: {title}\n\n"
    draft_md += f"**Para:** {recipient}\n\n"
    draft_md += f"**Asunto:** {title}\n\n"
    draft_md += "---\n\n"
    draft_md += f"Estimado/a {recipient},\n\n"
    draft_md += "En seguimiento a nuestra reunión, "
    draft_md += (notes or "quiero confirmar los puntos acordados.") + "\n\n"
    draft_md += "Quedo atento a sus comentarios.\n\n"
    draft_md += "Saludos cordiales,\nDavid\n"

    content_blocks = markdown_to_blocks(draft_md)

    result = notion_client.create_report_page(
        parent_page_id=transcript_page_id,
        title=f"Email draft: {title}",
        content_blocks=content_blocks,
        metadata={
            "type": "email_draft",
            "recipient": recipient,
            "source_transcript": transcript_page_id,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )

    try:
        notion_client.add_comment(
            page_id=transcript_page_id,
            text=f"Borrador de email creado: {result.get('page_url', result.get('page_id', '?'))}",
        )
    except Exception as exc:
        logger.warning("Could not add email draft comment: %s", exc)

    return {
        "followup_type": "email_draft",
        "result": result,
    }
