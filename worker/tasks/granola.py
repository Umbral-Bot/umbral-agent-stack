"""
Tasks: Granola pipeline handlers.

- granola.process_transcript: pipeline completo de transcripción → Notion
- granola.create_followup: follow-up proactivo (reminder, email_draft, proposal)
"""

import logging
import re
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .. import config, notion_client
from .notion import (
    handle_notion_upsert_deliverable,
    handle_notion_upsert_project,
    handle_notion_upsert_task,
)
from .notion_markdown import markdown_to_blocks

logger = logging.getLogger("worker.tasks.granola")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ACTION_ITEM_RE = re.compile(
    r"[-*]\s*\[[ x]?\]\s*(.+)", re.IGNORECASE
)
_RAW_CANONICAL_KIND_LABELS = {
    "task": "Tarea",
    "project": "Proyecto",
    "deliverable": "Entregable",
    "program": "Programa",
    "resource": "Recurso",
    "ignore": "Ignorar",
}
_SUPPORTED_RAW_CAPITALIZATION_KINDS = {"task", "project", "deliverable"}
_RAW_PAGE_MAX_BLOCKS = 10_000


def _build_action_item_task_id(title: str, date: str, item: Dict[str, str]) -> str:
    """Build a stable task id so repeated transcript ingests upsert instead of duplicating."""
    parts = [
        (title or "").strip().lower(),
        (date or "").strip(),
        (item.get("text") or "").strip().lower(),
        (item.get("assignee") or "").strip().lower(),
        (item.get("due") or "").strip(),
    ]
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"granola-action-item-{digest}"


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


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _today_utc() -> str:
    return _now_utc().strftime("%Y-%m-%d")


def _now_utc_iso() -> str:
    return _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def _rich_text_property(text: str) -> dict[str, Any]:
    return {"rich_text": [{"text": {"content": text[:2000]}}]}


def _date_property(value: str) -> dict[str, Any]:
    return {"date": {"start": value}}


def _select_property(value: str) -> dict[str, Any]:
    return {"select": {"name": value}}


def _canonical_kind_label(kind: str) -> str:
    return _RAW_CANONICAL_KIND_LABELS.get((kind or "").strip().lower(), "Ignorar")


def _stable_capitalization_task_id(raw_page_id: str, target_kind: str, target_name: str) -> str:
    digest = hashlib.sha1(
        f"{raw_page_id.strip()}|{target_kind.strip().lower()}|{target_name.strip().lower()}".encode("utf-8")
    ).hexdigest()[:16]
    return f"granola-capitalization-{digest}"


def _append_log(existing: Any, entry: str) -> str:
    existing_text = str(existing or "").strip()
    parts = [part for part in [existing_text, entry.strip()] if part]
    if not parts:
        return ""
    merged = "\n".join(parts)
    return merged[-2000:]


def _build_traceability_block(raw_page_id: str, target_kind: str, canonical_url: str) -> str:
    return "\n".join(
        [
            "source=granola",
            "capitalization_mode=raw_direct_v2",
            f"raw_page_id={raw_page_id}",
            f"canonical_target_type={target_kind}",
            f"canonical_target_url={canonical_url}",
            "runtime_actor=granola.capitalize_raw",
            f"processed_at={_now_utc_iso()}",
        ]
    )


def _read_raw_snapshot(raw_page_id: str) -> dict[str, Any]:
    snapshot = notion_client.get_page_snapshot(raw_page_id, max_blocks=_RAW_PAGE_MAX_BLOCKS)
    title = str(snapshot.get("title") or "").strip()
    content = str(snapshot.get("plain_text") or "").strip()
    if not title:
        raise ValueError("Raw page is missing a title")
    if not content:
        raise ValueError("Raw page is missing transcript content")
    return snapshot


def _build_raw_update_properties(
    *,
    estado_agente: str,
    accion_agente: str,
    estado: str | None = None,
    resumen_agente: str | None = None,
    log_agente: str | None = None,
    trazabilidad: str | None = None,
    destino_canonico: str | None = None,
    url_artefacto: str | None = None,
    processed_date: str | None = None,
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "Estado agente": _select_property(estado_agente),
        "Accion agente": _select_property(accion_agente),
    }
    if estado:
        properties["Estado"] = _select_property(estado)
    if resumen_agente is not None:
        properties["Resumen agente"] = _rich_text_property(resumen_agente)
    if log_agente is not None:
        properties["Log del agente"] = _rich_text_property(log_agente)
    if trazabilidad is not None:
        properties["Trazabilidad"] = _rich_text_property(trazabilidad)
    if destino_canonico is not None:
        properties["Destino canonico"] = _select_property(destino_canonico)
    if url_artefacto is not None:
        properties["URL artefacto"] = {"url": url_artefacto}
    if processed_date:
        properties["Fecha que el agente procesó"] = _date_property(processed_date)
    return properties


def _mark_raw_review_required(
    raw_snapshot: dict[str, Any],
    *,
    reason: str,
    destino_canonico: str | None = None,
    clear_artifact_url: bool = False,
) -> dict[str, Any]:
    properties = raw_snapshot.get("properties") or {}
    log_value = _append_log(
        properties.get("Log del agente"),
        f"{_today_utc()} granola.capitalize_raw bloqueado: {reason}",
    )
    summary = f"Bloqueo por ambiguedad: {reason}"
    update_properties = _build_raw_update_properties(
        estado_agente="Revision requerida",
        accion_agente="Bloqueado por ambiguedad",
        estado="Pendiente",
        resumen_agente=summary,
        log_agente=log_value,
        destino_canonico=destino_canonico,
        url_artefacto="" if clear_artifact_url else None,
        processed_date=_today_utc(),
    )
    notion_client.update_page_properties(
        page_id_or_url=str(raw_snapshot.get("page_id") or ""),
        properties=update_properties,
    )
    return {
        "ok": False,
        "raw_page_id": raw_snapshot.get("page_id"),
        "blocked": True,
        "reason": reason,
    }


def _build_task_capitalization_payload(
    *,
    raw_snapshot: dict[str, Any],
    target_name: str,
    project_name: str,
    project_page_id: str,
    summary: str,
    notes: str,
    next_action: str,
) -> dict[str, Any]:
    raw_page_id = str(raw_snapshot.get("page_id") or "")
    raw_url = str(raw_snapshot.get("url") or "")
    raw_title = str(raw_snapshot.get("title") or "")
    raw_date = str((raw_snapshot.get("properties") or {}).get("Fecha") or _today_utc())
    details = " ".join(part for part in [summary, notes, next_action] if part).strip()
    if not details:
        details = f"Revisar transcripcion raw: {raw_title} ({raw_date}). Ref: {raw_url or raw_page_id}"

    payload: dict[str, Any] = {
        "task_id": _stable_capitalization_task_id(raw_page_id, "task", target_name),
        "status": "queued",
        "team": "david",
        "task": "granola.capitalize_raw",
        "task_name": target_name,
        "input_summary": details[:2000],
        "source": "granola.capitalize_raw",
        "source_kind": "task",
    }
    if project_name:
        payload["project_name"] = project_name
    if project_page_id:
        payload["project_page_id"] = project_page_id
    return payload


def _build_project_capitalization_payload(
    *,
    raw_snapshot: dict[str, Any],
    target_name: str,
    summary: str,
    notes: str,
    next_action: str,
) -> dict[str, Any]:
    raw_title = str(raw_snapshot.get("title") or "")
    raw_date = str((raw_snapshot.get("properties") or {}).get("Fecha") or _today_utc())
    bloqueos = notes or ""
    if not bloqueos:
        bloqueos = f"Sin bloqueos confirmados; revisar reunion raw {raw_title} ({raw_date})."

    payload: dict[str, Any] = {
        "name": target_name,
        "estado": "Activo",
        "responsable": "David Moreira",
        "agentes": ["Rick"],
        "bloqueos": bloqueos,
        "next_action": next_action or summary or f"Revisar reunion raw {raw_title}.",
        "last_update_date": _today_utc(),
    }
    return payload


def _build_deliverable_capitalization_payload(
    *,
    raw_snapshot: dict[str, Any],
    target_name: str,
    project_name: str,
    project_page_id: str,
    summary: str,
    notes: str,
    next_action: str,
) -> dict[str, Any]:
    raw_page_id = str(raw_snapshot.get("page_id") or "")
    raw_url = str(raw_snapshot.get("url") or "")
    raw_date = str((raw_snapshot.get("properties") or {}).get("Fecha") or _today_utc())
    payload: dict[str, Any] = {
        "name": target_name,
        "date": raw_date,
        "agent": "Rick",
        "summary": summary or f"Capitalizado desde raw {raw_snapshot.get('title') or raw_page_id}",
        "notes": notes or f"Fuente raw: {raw_url or raw_page_id}",
        "next_action": next_action or "Revisar y decidir siguiente accion.",
        "artifact_url": raw_url,
        "source_task_id": raw_page_id,
    }
    if project_name:
        payload["project_name"] = project_name
    if project_page_id:
        payload["project_page_id"] = project_page_id
    return payload


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
        action_items_detected (int): Número de action items detectados en el raw.
        action_items_created (int): Siempre 0 en V2; la capitalización ocurre después.
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

    # Step 2: Notify Enlace in Control Room (literal @Enlace per convention)
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
        "action_items_detected": len(action_items),
        "action_items_created": 0,
        "notification_sent": notification_sent,
    }


def handle_granola_capitalize_raw(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Capitalize a Granola raw page directly into a canonical target.

    Input:
        raw_page_id (str, required): raw page id in Transcripciones Granola.
        target_kind (str, required): task | project | deliverable.
        target_name (str, required): canonical target name.
        project_name (str, optional): exact project name.
        project_page_id (str, optional): exact project relation target.
        summary (str, optional): short summary for the canonical target.
        notes (str, optional): supporting notes or context.
        next_action (str, optional): next action.
        dry_run (bool, optional): when true, returns the planned write without mutating.
    """
    raw_page_id = str(input_data.get("raw_page_id") or "").strip()
    target_kind = str(input_data.get("target_kind") or "").strip().lower()
    target_name = str(input_data.get("target_name") or "").strip()
    project_name = str(input_data.get("project_name") or "").strip()
    project_page_id = str(input_data.get("project_page_id") or "").strip()
    summary = str(input_data.get("summary") or "").strip()
    notes = str(input_data.get("notes") or "").strip()
    next_action = str(input_data.get("next_action") or "").strip()
    dry_run = bool(input_data.get("dry_run", False))

    if not raw_page_id:
        raise ValueError("'raw_page_id' is required in input")
    if not target_kind:
        raise ValueError("'target_kind' is required in input")
    if not target_name:
        raise ValueError("'target_name' is required in input")

    raw_snapshot = _read_raw_snapshot(raw_page_id)
    destino_canonico = _canonical_kind_label(target_kind)

    if not dry_run and config.GRANOLA_CAPITALIZATION_MODE != config.GRANOLA_CAPITALIZATION_MODE_RAW_DIRECT_V2:
        return {
            "ok": False,
            "skipped": True,
            "raw_page_id": raw_page_id,
            "reason": (
                "GRANOLA_CAPITALIZATION_MODE must be "
                f"'{config.GRANOLA_CAPITALIZATION_MODE_RAW_DIRECT_V2}' to write canonical targets"
            ),
        }

    if target_kind not in _SUPPORTED_RAW_CAPITALIZATION_KINDS:
        reason = (
            f"target_kind '{target_kind}' no está soportado en raw_direct_v2; "
            "solo task, project y deliverable tienen write determinístico en este corte."
        )
        if dry_run:
            return {
                "ok": False,
                "dry_run": True,
                "blocked": True,
                "raw_page_id": raw_page_id,
                "target_kind": target_kind,
                "target_name": target_name,
                "reason": reason,
            }
        return _mark_raw_review_required(
            raw_snapshot,
            reason=reason,
            destino_canonico=destino_canonico,
        )

    if target_kind == "task":
        handler_payload = _build_task_capitalization_payload(
            raw_snapshot=raw_snapshot,
            target_name=target_name,
            project_name=project_name,
            project_page_id=project_page_id,
            summary=summary,
            notes=notes,
            next_action=next_action,
        )
        handler_name = "notion.upsert_task"
    elif target_kind == "project":
        handler_payload = _build_project_capitalization_payload(
            raw_snapshot=raw_snapshot,
            target_name=target_name,
            summary=summary,
            notes=notes,
            next_action=next_action,
        )
        handler_name = "notion.upsert_project"
    else:
        handler_payload = _build_deliverable_capitalization_payload(
            raw_snapshot=raw_snapshot,
            target_name=target_name,
            project_name=project_name,
            project_page_id=project_page_id,
            summary=summary,
            notes=notes,
            next_action=next_action,
        )
        handler_name = "notion.upsert_deliverable"

    if dry_run:
        traceability = _build_traceability_block(raw_page_id, target_kind, "<pending>")
        return {
            "ok": True,
            "dry_run": True,
            "raw_page_id": raw_page_id,
            "target_kind": target_kind,
            "target_name": target_name,
            "handler": handler_name,
            "handler_payload": handler_payload,
            "traceability": traceability,
        }

    pre_log = _append_log(
        (raw_snapshot.get("properties") or {}).get("Log del agente"),
        f"{_today_utc()} granola.capitalize_raw preparando write hacia {target_kind}:{target_name}",
    )
    notion_client.update_page_properties(
        page_id_or_url=raw_page_id,
        properties=_build_raw_update_properties(
            estado_agente="Procesando",
            accion_agente="Listo para promocion",
            estado="Pendiente",
            resumen_agente=summary or f"Preparando capitalizacion hacia {target_kind}:{target_name}",
            log_agente=pre_log,
            destino_canonico=destino_canonico,
            processed_date=_today_utc(),
        ),
    )

    if target_kind == "task":
        result = handle_notion_upsert_task(handler_payload)
    elif target_kind == "project":
        result = handle_notion_upsert_project(handler_payload)
    else:
        result = handle_notion_upsert_deliverable(handler_payload)

    if not result.get("ok", True) and not result.get("page_id"):
        reason = str(result.get("error") or f"Canonical write failed for {target_kind}:{target_name}")
        return _mark_raw_review_required(
            raw_snapshot,
            reason=reason,
            destino_canonico=destino_canonico,
        )

    canonical_url = str(result.get("url") or "").strip()
    if not canonical_url:
        reason = f"Canonical write for {target_kind}:{target_name} returned no canonical URL"
        return _mark_raw_review_required(
            raw_snapshot,
            reason=reason,
            destino_canonico=destino_canonico,
        )

    traceability = _build_traceability_block(raw_page_id, target_kind, canonical_url)
    success_log = _append_log(
        pre_log,
        f"{_today_utc()} granola.capitalize_raw wrote {target_kind}:{target_name} -> {canonical_url}",
    )
    notion_client.update_page_properties(
        page_id_or_url=raw_page_id,
        properties=_build_raw_update_properties(
            estado_agente="Procesada",
            accion_agente="Listo para promocion",
            estado="Procesada",
            resumen_agente=summary or f"Capitalizado como {destino_canonico.lower()}",
            log_agente=success_log,
            trazabilidad=traceability,
            destino_canonico=destino_canonico,
            url_artefacto=canonical_url,
            processed_date=_today_utc(),
        ),
    )

    return {
        "ok": True,
        "raw_page_id": raw_page_id,
        "target_kind": target_kind,
        "target_name": target_name,
        "page_id": result.get("page_id"),
        "url": canonical_url,
        "created": result.get("created"),
        "traceability": traceability,
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
