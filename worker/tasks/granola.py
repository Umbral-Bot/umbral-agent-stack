"""
Tasks: Granola pipeline handlers.

- granola.process_transcript: pipeline completo de transcripción → Notion
- granola.create_followup: follow-up proactivo (reminder, email_draft, proposal)
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .. import notion_client
from .notion_markdown import markdown_to_blocks

logger = logging.getLogger("worker.tasks.granola")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ACTION_ITEM_RE = re.compile(
    r"[-*]\s*\[[ x]?\]\s*(.+)", re.IGNORECASE
)


def _extract_action_items_from_content(content: str) -> List[Dict[str, str]]:
    """Best-effort extraction of action items from freeform markdown content."""
    items: List[Dict[str, str]] = []
    in_section = False
    for line in content.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("## ") and any(
            kw in stripped for kw in ("action item", "compromisos", "tareas", "to-do", "todo")
        ):
            in_section = True
            continue
        if stripped.startswith("## ") and in_section:
            break
        if in_section:
            m = _ACTION_ITEM_RE.match(line.strip())
            if m:
                item_text = m.group(1).strip()
                assignee = ""
                due = ""
                paren = re.search(r"\(([^)]+)\)\s*$", item_text)
                if paren:
                    parts = [p.strip() for p in paren.group(1).split(",")]
                    for p in parts:
                        if re.match(r"\d{4}-\d{2}-\d{2}", p):
                            due = p
                        else:
                            assignee = p
                    item_text = item_text[: paren.start()].strip()
                items.append({"text": item_text, "assignee": assignee, "due": due})
    return items


def _build_transcript_blocks(parsed: Dict[str, Any]) -> list[dict[str, Any]]:
    """Build Notion blocks from parsed transcript data."""
    blocks: list[dict[str, Any]] = []

    # Attendees callout
    attendees = parsed.get("attendees", [])
    if attendees:
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"Participantes: {', '.join(attendees)}"}}],
                "icon": {"type": "emoji", "emoji": "👥"},
                "color": "gray_background",
            },
        })

    # Content via markdown converter
    content = parsed.get("content", "")
    if content:
        content_blocks = markdown_to_blocks(content)
        blocks.extend(content_blocks)

    # Action items section
    action_items = parsed.get("action_items", [])
    if action_items:
        blocks.append({"object": "block", "type": "divider", "divider": {}})
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Action Items"}}],
                "color": "default",
            },
        })
        for item in action_items:
            text = item.get("text", "")
            assignee = item.get("assignee", "")
            due = item.get("due", "")
            suffix = ""
            if assignee:
                suffix += f" — {assignee}"
            if due:
                suffix += f" (vence: {due})"
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": f"{text}{suffix}"}}],
                    "checked": False,
                    "color": "default",
                },
            })

    return blocks


# ---------------------------------------------------------------------------
# granola.process_transcript
# ---------------------------------------------------------------------------

def handle_granola_process_transcript(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pipeline completo: transcripción de Granola → Notion.

    Input:
        title (str, required): Título de la reunión.
        content (str, required): Contenido/transcripción en markdown.
        date (str, optional): Fecha ISO (default: hoy UTC).
        attendees (list[str], optional): Lista de participantes.
        action_items (list[dict], optional): Action items pre-parseados
            [{text, assignee, due}]. Si no se proporcionan, se extraen del content.
        source (str, optional): Fuente (default: "granola").
        notify_enlace (bool, optional): Notificar a Enlace (default: true).

    Returns:
        page_id (str): ID de la página creada en Notion.
        url (str): URL de la página.
        action_items_created (int): Número de action items creados como tareas.
        notification_sent (bool): Si se notificó a Enlace.
    """
    title = input_data.get("title", "").strip()
    content = input_data.get("content", "").strip()
    if not title:
        raise ValueError("'title' is required in input")
    if not content:
        raise ValueError("'content' is required in input")

    date = input_data.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    attendees = input_data.get("attendees", [])
    source = input_data.get("source", "granola")
    notify_enlace = input_data.get("notify_enlace", True)

    # Action items: use provided or extract from content
    action_items = input_data.get("action_items")
    if not action_items:
        action_items = _extract_action_items_from_content(content)
        logger.info("Extracted %d action items from content", len(action_items))

    # Step 1: Create transcript page in Notion
    logger.info("Creating Granola transcript page: %s", title)
    page_result = notion_client.create_transcript_page(
        title=title,
        content=content,
        source=source,
        date=date,
    )
    page_id = page_result["page_id"]
    page_url = page_result.get("url", "")
    logger.info("Created page: %s (%s)", page_id, page_url)

    # Step 2: Create action items as Notion tasks
    ai_created = 0
    for item in action_items:
        try:
            task_id = str(uuid.uuid4())
            task_name = item.get("text", "Action item")[:200]
            assignee = item.get("assignee", "sin asignar")
            notion_client.upsert_task(
                task_id=task_id,
                status="queued",
                team=assignee or "sin asignar",
                task=f"[Granola] {task_name}",
                input_summary=f"De reunión: {title} ({date})",
            )
            ai_created += 1
        except Exception as e:
            logger.warning("Failed to create action item task: %s", e)

    # Step 3: Notify Enlace in Control Room (literal @Enlace per convention)
    notification_sent = False
    if notify_enlace:
        try:
            attendees_str = f" ({', '.join(attendees)})" if attendees else ""
            transcript_ref = page_url or page_id
            comment_text = (
                f"Hola @Enlace, transcripción lista para revisar: "
                f"{title}{attendees_str} — {date}. "
                f"Página: {transcript_ref}. "
                f"{len(action_items)} action items identificados."
            )
            notion_client.add_comment(page_id=None, text=comment_text)
            notification_sent = True
            logger.info("Enlace notified in Control Room for transcript %s", page_id)
        except Exception as e:
            logger.warning("Failed to notify Enlace: %s", e)

    return {
        "page_id": page_id,
        "url": page_url,
        "action_items_created": ai_created,
        "notification_sent": notification_sent,
    }


# ---------------------------------------------------------------------------
# granola.create_followup
# ---------------------------------------------------------------------------

FOLLOWUP_TYPES = {"reminder", "email_draft", "proposal", "calendar_event"}

PROPOSAL_TEMPLATE = """# Propuesta de Seguimiento

## Reunión: {title}
**Fecha:** {date}
**Participantes:** {attendees}

## Resumen de Compromisos

{action_items_text}

## Próximos Pasos Sugeridos

{next_steps}

---
*Generado automáticamente por Rick a partir de la transcripción de Granola.*
"""

EMAIL_TEMPLATE = """Asunto: Seguimiento — {title} ({date})

Estimado/a equipo,

Gracias por la reunión del {date}. A continuación los puntos clave y compromisos acordados:

{action_items_text}

Quedo atento a sus comentarios.

Saludos cordiales,
David

---
*Borrador generado por Rick a partir de la transcripción de Granola.*
"""


def handle_granola_create_followup(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Follow-up proactivo sobre una transcripción de Granola.

    Input:
        transcript_page_id (str, required): ID de la página de la transcripción en Notion.
        followup_type (str, required): "reminder" | "email_draft" | "proposal".
        title (str, optional): Título de la reunión (para templates).
        date (str, optional): Fecha de la reunión.
        attendees (list[str], optional): Participantes.
        action_items (list[dict], optional): [{text, assignee, due}].
        due_date (str, optional): Fecha límite para reminders (default: +7 días).
        notes (str, optional): Notas adicionales para el follow-up.

    Returns:
        followup_type (str): Tipo de follow-up creado.
        result (dict): Resultado dependiente del tipo.
    """
    transcript_page_id = input_data.get("transcript_page_id", "").strip()
    followup_type = input_data.get("followup_type", "").strip().lower()

    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")
    if followup_type not in FOLLOWUP_TYPES:
        raise ValueError(
            f"'followup_type' must be one of: {', '.join(sorted(FOLLOWUP_TYPES))}"
        )

    title = input_data.get("title", "Reunión")
    date = input_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    attendees = input_data.get("attendees", [])
    action_items = input_data.get("action_items", [])
    notes = input_data.get("notes", "")

    attendees_str = ", ".join(attendees) if attendees else "No especificados"
    action_items_text = "\n".join(
        f"- {item.get('text', '?')} ({item.get('assignee', '?')}, {item.get('due', 'sin fecha')})"
        for item in action_items
    ) if action_items else "- Sin compromisos registrados"

    if followup_type == "reminder":
        return _create_reminder(input_data, title, date, attendees_str, action_items_text, transcript_page_id)
    elif followup_type == "email_draft":
        return _create_email_draft(title, date, action_items_text, notes, transcript_page_id, attendees)
    elif followup_type == "proposal":
        return _create_proposal(title, date, attendees_str, action_items_text, notes, transcript_page_id)
    elif followup_type == "calendar_event":
        return _create_calendar_event(input_data, title, date, attendees, transcript_page_id)

    raise ValueError(f"Unhandled followup_type: {followup_type}")


def _create_reminder(
    input_data: Dict[str, Any],
    title: str,
    date: str,
    attendees_str: str,
    action_items_text: str,
    transcript_page_id: str,
) -> Dict[str, Any]:
    """Create a Notion task as a reminder."""
    due_date = input_data.get("due_date", "")
    if not due_date:
        from datetime import timedelta
        due_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

    task_id = str(uuid.uuid4())
    try:
        result = notion_client.upsert_task(
            task_id=task_id,
            status="queued",
            team="david",
            task=f"[Follow-up] {title} — revisar compromisos",
            input_summary=(
                f"Reunión: {title} ({date}). "
                f"Participantes: {attendees_str}. "
                f"Vence: {due_date}. "
                f"Ref: {transcript_page_id}"
            ),
        )
    except Exception as e:
        logger.error("Failed to create reminder task: %s", e)
        result = {"error": str(e)}

    return {
        "followup_type": "reminder",
        "result": {
            "task_id": task_id,
            "due_date": due_date,
            "notion_result": result,
        },
    }


def _create_email_draft(
    title: str,
    date: str,
    action_items_text: str,
    notes: str,
    transcript_page_id: str,
    attendees: List[str] | None = None,
) -> Dict[str, Any]:
    """Generate an email draft from the meeting transcript.

    If GOOGLE_GMAIL_TOKEN is configured and attendees are provided,
    a real Gmail draft is also created via the gmail.create_draft handler.
    """
    draft = EMAIL_TEMPLATE.format(
        title=title,
        date=date,
        action_items_text=action_items_text,
    )
    if notes:
        draft += f"\nNotas adicionales:\n{notes}\n"

    # Save draft as comment on the transcript page
    try:
        notion_client.add_comment(
            page_id=transcript_page_id,
            text=f"📧 Borrador de email generado:\n\n{draft[:1800]}",
        )
        posted = True
    except Exception as e:
        logger.warning("Failed to post email draft to Notion: %s", e)
        posted = False

    email_draft_result = None
    if attendees:
        try:
            from .gmail import handle_gmail_create_draft

            to_addr = attendees[0] if "@" in attendees[0] else ""
            cc_addrs = [a for a in attendees[1:] if "@" in a]
            if to_addr:
                email_draft_result = handle_gmail_create_draft({
                    "to": to_addr,
                    "subject": f"Seguimiento — {title} ({date})",
                    "body": draft,
                    "body_type": "plain",
                    "cc": cc_addrs,
                })
                logger.info("Gmail draft created: %s", email_draft_result)
        except Exception as e:
            logger.warning("Failed to create Gmail draft: %s", e)
            email_draft_result = {"ok": False, "error": str(e)}

    return {
        "followup_type": "email_draft",
        "result": {
            "draft": draft,
            "posted_to_notion": posted,
            "transcript_page_id": transcript_page_id,
            "email_draft": email_draft_result,
        },
    }


def _create_calendar_event(
    input_data: Dict[str, Any],
    title: str,
    date: str,
    attendees: List[str],
    transcript_page_id: str,
) -> Dict[str, Any]:
    """Create a Google Calendar event from the meeting follow-up."""
    from .google_calendar import handle_google_calendar_create_event

    start = input_data.get("start", f"{date}T10:00:00")
    end = input_data.get("end", "")
    tz = input_data.get("timezone", "America/Santiago")
    description = input_data.get("notes", f"Follow-up de reunión: {title}")

    attendee_emails = [a for a in attendees if "@" in a]

    try:
        cal_result = handle_google_calendar_create_event({
            "title": f"Follow-up: {title}",
            "description": description,
            "start": start,
            "end": end,
            "timezone": tz,
            "attendees": attendee_emails,
        })
        logger.info("Calendar event created: %s", cal_result)
    except Exception as e:
        logger.warning("Failed to create calendar event: %s", e)
        cal_result = {"ok": False, "error": str(e)}

    return {
        "followup_type": "calendar_event",
        "result": {
            "calendar_event": cal_result,
            "transcript_page_id": transcript_page_id,
        },
    }


def _create_proposal(
    title: str,
    date: str,
    attendees_str: str,
    action_items_text: str,
    notes: str,
    transcript_page_id: str,
) -> Dict[str, Any]:
    """Generate a proposal document from the meeting transcript."""
    next_steps = notes if notes else (
        "1. Revisar y validar los compromisos con el equipo.\n"
        "2. Agendar reunión de seguimiento.\n"
        "3. Preparar entregables pendientes."
    )

    proposal = PROPOSAL_TEMPLATE.format(
        title=title,
        date=date,
        attendees=attendees_str,
        action_items_text=action_items_text,
        next_steps=next_steps,
    )

    # Create as report page in Notion
    try:
        content_blocks = markdown_to_blocks(proposal)
        result = notion_client.create_report_page(
            parent_page_id=transcript_page_id,
            title=f"Propuesta: {title}",
            content_blocks=content_blocks,
            metadata={
                "type": "proposal",
                "meeting_date": date,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        return {
            "followup_type": "proposal",
            "result": result,
        }
    except Exception as e:
        logger.error("Failed to create proposal page: %s", e)
        return {
            "followup_type": "proposal",
            "result": {
                "proposal_text": proposal,
                "error": str(e),
                "transcript_page_id": transcript_page_id,
            },
        }
