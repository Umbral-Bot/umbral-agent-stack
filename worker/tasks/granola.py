"""
Tasks: Granola pipeline handlers.

- granola.process_transcript: pipeline completo de transcripción → Notion
- granola.create_followup: follow-up proactivo (reminder, email_draft, proposal)
"""

import logging
import re
import hashlib
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .. import config, notion_client
from .notion import (
    handle_notion_upsert_bridge_item,
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


def _extract_title_from_page(page_data: Dict[str, Any]) -> str:
    properties = page_data.get("properties") or {}
    for prop in properties.values():
        if isinstance(prop, dict) and prop.get("type") == "title":
            parts: list[str] = []
            for item in prop.get("title") or []:
                if isinstance(item, dict):
                    parts.append(item.get("plain_text", item.get("text", {}).get("content", "")))
            return "".join(parts).strip()
    return ""


def _extract_date_from_page(page_data: Dict[str, Any]) -> str:
    properties = page_data.get("properties") or {}
    for candidate in ("Fecha", "Date", "Fecha de transcripcion", "Meeting Date"):
        prop = properties.get(candidate)
        if isinstance(prop, dict) and prop.get("type") == "date":
            return ((prop.get("date") or {}).get("start") or "").strip()
    return ""


def _extract_select_value(page_data: Dict[str, Any], *names: str) -> str:
    properties = page_data.get("properties") or {}
    for candidate in names:
        prop = properties.get(candidate)
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        if prop_type == "select":
            return ((prop.get("select") or {}).get("name") or "").strip()
        if prop_type == "status":
            return ((prop.get("status") or {}).get("name") or "").strip()
        if prop_type == "rich_text":
            parts: list[str] = []
            for item in prop.get("rich_text") or []:
                if isinstance(item, dict):
                    parts.append(item.get("plain_text", item.get("text", {}).get("content", "")))
            return "".join(parts).strip()
    return ""


def _extract_relation_values(page_data: Dict[str, Any], *names: str) -> list[str]:
    properties = page_data.get("properties") or {}
    for candidate in names:
        prop = properties.get(candidate)
        if not isinstance(prop, dict) or prop.get("type") != "relation":
            continue
        resolved: list[str] = []
        for item in prop.get("relation") or []:
            if isinstance(item, dict):
                item_id = str(item.get("id") or "").strip()
                if item_id:
                    resolved.append(item_id)
        if resolved:
            return resolved
    return []


def _compact_excerpt(text: str, limit: int = 280) -> str:
    value = " ".join((text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _normalize_lookup_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    ascii_text = text.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else " " for ch in ascii_text.lower())
    return " ".join(cleaned.split())


def _extract_date_start(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("start") or "").strip()
    return str(value or "").strip()


def _extract_page_text_property(page_data: Dict[str, Any], *names: str) -> str:
    properties = page_data.get("properties") or {}
    for candidate in names:
        prop = properties.get(candidate)
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        if prop_type == "url":
            return str(prop.get("url") or "").strip()
        if prop_type in {"title", "rich_text"}:
            key = "title" if prop_type == "title" else "rich_text"
            parts: list[str] = []
            for item in prop.get(key) or []:
                if isinstance(item, dict):
                    parts.append(item.get("plain_text", item.get("text", {}).get("content", "")))
            return "".join(parts).strip()
    return ""


def _append_context(existing: str, extra: str) -> str:
    base = (existing or "").strip()
    addon = (extra or "").strip()
    if not addon:
        return base
    if not base:
        return addon
    return f"{base}\n\n{addon}"


def _comment_safe(page_id: str | None, text: str) -> bool:
    if not page_id or not text.strip():
        return False
    try:
        notion_client.add_comment(page_id=page_id, text=text)
        return True
    except Exception as exc:
        logger.warning("Failed to add traceability comment to %s: %s", page_id, exc)
        return False


def _leave_review_comment(
    page_id: str | None,
    *,
    source_evidence: str,
    intended_target: str,
    blocking_ambiguity: str,
    next_review: str,
) -> bool:
    comment = (
        "Revision requerida en raw por el contrato V2 vigente.\n"
        f"1. Evidencia fuente: {source_evidence}\n"
        f"2. Destino intencionado: {intended_target}\n"
        f"3. Bloqueo: {blocking_ambiguity}\n"
        f"4. Siguiente revision necesaria: {next_review}"
    )
    return _comment_safe(page_id, comment)


def _result_page_id(result: Dict[str, Any] | None) -> str:
    if not isinstance(result, dict):
        return ""
    direct = str(result.get("page_id") or "").strip()
    if direct:
        return direct
    nested = result.get("result")
    if isinstance(nested, dict):
        inner_page_id = str(nested.get("page_id") or "").strip()
        if inner_page_id:
            return inner_page_id
        notion_result = nested.get("notion_result")
        if isinstance(notion_result, dict):
            return str(notion_result.get("page_id") or "").strip()
    return ""


def _today_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _page_schema_from_page(page_data: Dict[str, Any]) -> Dict[str, str]:
    properties = page_data.get("properties") or {}
    schema: Dict[str, str] = {}
    for name, meta in properties.items():
        if not isinstance(meta, dict):
            continue
        prop_type = str(meta.get("type") or "").strip()
        if prop_type:
            schema[name] = prop_type
    return schema


def _schema_property_name(
    schema: Dict[str, str],
    candidates: list[str],
    expected_types: set[str] | None = None,
) -> str | None:
    for candidate in candidates:
        prop_type = str(schema.get(candidate) or "").strip()
        if not prop_type:
            continue
        if expected_types and prop_type not in expected_types:
            continue
        return candidate
    return None


def _pick_best_existing_curated_session(
    candidates: list[Dict[str, Any]],
    *,
    session_name: str,
    transcript_date: str,
    transcript_url: str,
    source_prop: str | None,
) -> tuple[Dict[str, Any] | None, str]:
    normalized_target = _normalize_lookup_text(session_name)
    ranked: list[tuple[tuple[int, int, int], Dict[str, Any], str]] = []

    for candidate in candidates:
        candidate_title = _extract_title_from_page(candidate)
        candidate_date = _extract_date_from_page(candidate)
        candidate_source = (
            _extract_page_text_property(candidate, source_prop) if source_prop else ""
        )

        same_source = bool(transcript_url and candidate_source == transcript_url)
        exact_title = bool(session_name and candidate_title == session_name)
        normalized_title = bool(
            normalized_target
            and candidate_title
            and _normalize_lookup_text(candidate_title) == normalized_target
        )
        same_date = bool(transcript_date and candidate_date == transcript_date)

        match_strategy = ""
        if same_source:
            match_strategy = "source_url"
            primary_rank = 0
        elif exact_title:
            match_strategy = "exact_title"
            primary_rank = 1
        elif normalized_title and same_date:
            match_strategy = "normalized_title_date"
            primary_rank = 2
        else:
            continue

        mangled_penalty = 1 if "?" in candidate_title else 0
        date_penalty = 0 if same_date or not transcript_date else 1
        ranked.append(
            ((primary_rank, mangled_penalty, date_penalty), candidate, match_strategy)
        )

    if not ranked:
        return None, ""

    ranked.sort(key=lambda item: item[0])
    return ranked[0][1], ranked[0][2]


def _relation_ids(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        clean = value.strip()
        return [clean] if clean else []
    if isinstance(value, dict):
        return _relation_ids(value.get("id") or value.get("page_id"))
    if isinstance(value, list):
        resolved: list[str] = []
        for item in value:
            resolved.extend(_relation_ids(item))
        seen: set[str] = set()
        unique: list[str] = []
        for item in resolved:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique
    return []


def _set_schema_property(
    payload: Dict[str, Any],
    schema: Dict[str, str],
    candidates: list[str],
    value: Any,
    *,
    expected_types: set[str] | None = None,
    used_fields: list[str] | None = None,
) -> str | None:
    if value is None or value == "" or value == []:
        return None

    prop_name = _schema_property_name(schema, candidates, expected_types)
    if not prop_name:
        return None

    prop_type = schema[prop_name]
    if prop_type == "title":
        payload[prop_name] = {"title": [{"text": {"content": str(value)[:2000]}}]}
    elif prop_type == "rich_text":
        payload[prop_name] = {"rich_text": [{"text": {"content": str(value)[:2000]}}]}
    elif prop_type == "date":
        payload[prop_name] = {"date": {"start": str(value)}}
    elif prop_type == "select":
        payload[prop_name] = {"select": {"name": str(value)}}
    elif prop_type == "status":
        payload[prop_name] = {"status": {"name": str(value)}}
    elif prop_type == "url":
        payload[prop_name] = {"url": str(value)}
    elif prop_type == "relation":
        ids = _relation_ids(value)
        if not ids:
            return None
        payload[prop_name] = {"relation": [{"id": item} for item in ids]}
    elif prop_type == "checkbox":
        payload[prop_name] = {"checkbox": bool(value)}
    elif prop_type == "number":
        try:
            payload[prop_name] = {"number": float(value)}
        except (TypeError, ValueError):
            return None
    else:
        return None

    if used_fields is not None:
        used_fields.append(prop_name)
    return prop_name


def _clear_schema_property(
    payload: Dict[str, Any],
    schema: Dict[str, str],
    candidates: list[str],
    *,
    expected_types: set[str] | None = None,
    used_fields: list[str] | None = None,
) -> str | None:
    prop_name = _schema_property_name(schema, candidates, expected_types)
    if not prop_name:
        return None

    prop_type = schema[prop_name]
    if prop_type == "title":
        payload[prop_name] = {"title": []}
    elif prop_type == "rich_text":
        payload[prop_name] = {"rich_text": []}
    elif prop_type == "date":
        payload[prop_name] = {"date": None}
    elif prop_type == "select":
        payload[prop_name] = {"select": None}
    elif prop_type == "status":
        payload[prop_name] = {"status": None}
    elif prop_type == "url":
        payload[prop_name] = {"url": None}
    elif prop_type == "relation":
        payload[prop_name] = {"relation": []}
    elif prop_type == "checkbox":
        payload[prop_name] = {"checkbox": False}
    elif prop_type == "number":
        payload[prop_name] = {"number": None}
    else:
        return None

    if used_fields is not None:
        used_fields.append(prop_name)
    return prop_name


def _traceability_block(
    *,
    canonical_target_type: str,
    canonical_target_name: str,
    processed_at: str,
) -> str:
    return "\n".join(
        [
            "source=granola",
            "capitalization_mode=notion_ai_raw_direct_v2",
            f"canonical_target_type={canonical_target_type or 'ignorar'}",
            f"canonical_target_name={canonical_target_name or 'pending_review'}",
            f"processed_at={processed_at}",
        ]
    )


def _sync_raw_v2_state(
    raw_page_id: str,
    raw_page_data: Dict[str, Any],
    *,
    status: str,
    agent_status: str,
    agent_action: str,
    proposed_domain: str,
    proposed_type: str,
    canonical_target_type: str,
    canonical_target_name: str,
    summary: str,
    agent_log: str,
    artifact_url: str = "",
    review_status: str = "No aplica",
    review_reason: str = "",
    review_question: str = "",
    agent_recommendation: str = "",
    review_response: str = "",
    review_decision: str = "",
    reprocess_after_review: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    raw_schema = _page_schema_from_page(raw_page_data)
    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    _set_schema_property(
        properties,
        raw_schema,
        ["Estado", "Status"],
        status,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Estado agente", "Estado Agente", "Agent Status"],
        agent_status,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Accion agente", "Acción agente", "Agent Action"],
        agent_action,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Dominio propuesto", "Proposed Domain"],
        proposed_domain,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Tipo propuesto", "Proposed Type"],
        proposed_type,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Destino canonico", "Destino canónico", "Canonical Target"],
        canonical_target_type,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Resumen agente", "Agent Summary"],
        summary,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Log del agente", "Agent Log"],
        agent_log,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Trazabilidad", "Traceability"],
        _traceability_block(
            canonical_target_type=canonical_target_type,
            canonical_target_name=canonical_target_name,
            processed_at=processed_at,
        ),
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Fecha que el agente procesó", "Fecha que el agente proceso", "Processed At"],
        _today_date(),
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Estado revisión", "Estado revisiÃ³n", "Estado revision", "Review Status"],
        review_status,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Motivo revisión", "Motivo revisiÃ³n", "Motivo revision", "Review Reason"],
        review_reason,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Pregunta de revisión", "Pregunta de revisiÃ³n", "Pregunta de revision", "Review Question"],
        review_question,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Recomendación agente", "RecomendaciÃ³n agente", "Recomendacion agente", "Agent Recommendation"],
        agent_recommendation,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Respuesta revisión", "Respuesta revisiÃ³n", "Respuesta revision", "Review Response"],
        review_response,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Decisión revisión", "DecisiÃ³n revisiÃ³n", "Decision revision", "Review Decision"],
        review_decision,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        raw_schema,
        ["Reprocesar tras revisión", "Reprocesar tras revisiÃ³n", "Reprocesar tras revision", "Reprocess After Review"],
        reprocess_after_review,
        expected_types={"checkbox"},
        used_fields=used_fields,
    )
    if artifact_url:
        _set_schema_property(
            properties,
            raw_schema,
            ["URL artefacto", "Artifact URL", "Artifact Link"],
            artifact_url,
            expected_types={"url", "rich_text"},
            used_fields=used_fields,
        )
    else:
        _clear_schema_property(
            properties,
            raw_schema,
            ["URL artefacto", "Artifact URL", "Artifact Link"],
            expected_types={"url", "rich_text"},
            used_fields=used_fields,
        )

    if review_status == "No aplica":
        _clear_schema_property(
            properties,
            raw_schema,
            ["Motivo revisión", "Motivo revisiÃ³n", "Motivo revision", "Review Reason"],
            expected_types={"rich_text"},
            used_fields=used_fields,
        )
        _clear_schema_property(
            properties,
            raw_schema,
            ["Pregunta de revisión", "Pregunta de revisiÃ³n", "Pregunta de revision", "Review Question"],
            expected_types={"rich_text"},
            used_fields=used_fields,
        )
        _clear_schema_property(
            properties,
            raw_schema,
            ["Recomendación agente", "RecomendaciÃ³n agente", "Recomendacion agente", "Agent Recommendation"],
            expected_types={"rich_text"},
            used_fields=used_fields,
        )
        _clear_schema_property(
            properties,
            raw_schema,
            ["Respuesta revisión", "Respuesta revisiÃ³n", "Respuesta revision", "Review Response"],
            expected_types={"rich_text"},
            used_fields=used_fields,
        )
        _clear_schema_property(
            properties,
            raw_schema,
            ["Decisión revisión", "DecisiÃ³n revisiÃ³n", "Decision revision", "Review Decision"],
            expected_types={"rich_text"},
            used_fields=used_fields,
        )

    if dry_run:
        return {
            "ok": True,
            "page_id": raw_page_id,
            "updated": bool(properties),
            "dry_run": True,
            "properties": properties,
            "schema_fields_used": used_fields,
            "processed_at": processed_at,
        }

    if not properties:
        return {
            "ok": True,
            "page_id": raw_page_id,
            "updated": False,
            "dry_run": False,
            "properties": {},
            "schema_fields_used": used_fields,
            "processed_at": processed_at,
        }

    result = notion_client.update_page_properties(raw_page_id, properties=properties)
    result["ok"] = True
    result["dry_run"] = False
    result["schema_fields_used"] = used_fields
    result["processed_at"] = processed_at
    return result


def _build_default_raw_summary(*, target_type: str, target_name: str, transcript_title: str) -> str:
    if not target_name:
        return f"Revision requerida desde raw para '{transcript_title}'."
    return f"Capitalizacion directa desde raw hacia {target_type.lower()}: {target_name}."


def _upsert_human_task_from_raw(
    *,
    raw_page_id: str,
    transcript_title: str,
    transcript_url: str,
    transcript_date: str,
    context_excerpt: str,
    input_data: Dict[str, Any],
    project_relation_ids: list[str] | None = None,
) -> Dict[str, Any]:
    task_name = (
        (input_data.get("task_name") or "").strip()
        or (input_data.get("human_task_name") or "").strip()
        or (input_data.get("title") or "").strip()
    )
    if not task_name:
        raise ValueError("'task_name' is required for direct raw task capitalization")

    human_tasks_db_id = config.NOTION_HUMAN_TASKS_DB_ID or config.NOTION_TASKS_DB_ID
    if not human_tasks_db_id:
        raise RuntimeError("NOTION_HUMAN_TASKS_DB_ID not configured")

    db_snapshot = notion_client.read_database(
        human_tasks_db_id,
        max_items=1,
    )
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError("Could not read human tasks DB schema")

    title_prop = _schema_property_name(schema, ["Nombre", "Name", "Title"], {"title"})
    if not title_prop:
        raise RuntimeError("Human tasks DB does not expose a title property")

    task_notes = (
        (input_data.get("notes") or "").strip()
        or (input_data.get("task_notes") or "").strip()
    )
    if not task_notes:
        task_notes = (
            f"Derivada de raw Granola: {transcript_title} ({transcript_date}) - "
            f"{transcript_url or raw_page_id}"
        )
        if context_excerpt:
            task_notes = _append_context(task_notes, f"Contexto observado: {context_excerpt}")

    resolved_project_relation_ids = list(project_relation_ids or _relation_ids(input_data.get("project_page_id")))
    if not resolved_project_relation_ids:
        project_lookup_name = (
            (input_data.get("task_project_name") or "").strip()
            or (input_data.get("project_name") or "").strip()
        )
        project_lookup_db_id = config.NOTION_COMMERCIAL_PROJECTS_DB_ID or config.NOTION_PROJECTS_DB_ID
        if project_lookup_name and project_lookup_db_id:
            project_matches = notion_client.query_database(
                database_id=project_lookup_db_id,
                filter={"property": "Nombre", "title": {"equals": project_lookup_name}},
            )
            if project_matches:
                resolved_project_relation_ids = [project_matches[0]["id"]]

    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    _set_schema_property(
        properties,
        schema,
        [title_prop],
        task_name,
        expected_types={"title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Dominio", "Domain"],
        input_data.get("domain") or input_data.get("task_domain") or "Mixto",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Proyecto", "Project"],
        resolved_project_relation_ids,
        expected_types={"relation"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Tipo", "Type"],
        input_data.get("task_type") or input_data.get("type") or "Follow-up",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Estado", "Status"],
        input_data.get("estado") or input_data.get("status") or "Pendiente",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Prioridad", "Priority"],
        input_data.get("priority") or input_data.get("prioridad"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Fecha objetivo", "Due date", "Target date"],
        input_data.get("due_date") or input_data.get("target_date"),
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Origen", "Source"],
        input_data.get("origin") or input_data.get("task_origin") or "Sesion",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["URL fuente", "Source URL", "URL", "Link"],
        input_data.get("source_url") or transcript_url or raw_page_id,
        expected_types={"url", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Notas", "Notes"],
        task_notes,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )

    existing = notion_client.query_database(
        database_id=human_tasks_db_id,
        filter={"property": title_prop, "title": {"equals": task_name}},
    )
    matched_existing = bool(existing)
    dry_run = bool(input_data.get("dry_run"))
    if dry_run:
        notion_result = {
            "page_id": existing[0]["id"] if matched_existing else "",
            "url": existing[0].get("url", "") if matched_existing else "",
            "created": not matched_existing,
            "updated": matched_existing,
            "dry_run": True,
            "properties": properties,
        }
    elif matched_existing:
        notion_result = notion_client.update_page_properties(
            existing[0]["id"],
            properties=properties,
        )
        notion_result["created"] = False
    else:
        notion_result = notion_client.create_database_page(
            human_tasks_db_id,
            properties=properties,
        )
        notion_result["created"] = True

    notion_result["ok"] = True
    notion_result["schema_fields_used"] = used_fields
    notion_result["matched_existing"] = matched_existing
    notion_result["target_name"] = task_name
    return notion_result


def _upsert_commercial_project_from_raw(
    *,
    raw_page_id: str,
    transcript_title: str,
    transcript_url: str,
    transcript_date: str,
    context_excerpt: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    project_name = (
        (input_data.get("project_name") or "").strip()
        or (input_data.get("title") or "").strip()
    )
    if not project_name:
        raise ValueError("'project_name' is required for direct raw project capitalization")

    commercial_db_id = config.NOTION_COMMERCIAL_PROJECTS_DB_ID or config.NOTION_PROJECTS_DB_ID
    if not commercial_db_id:
        raise RuntimeError("NOTION_COMMERCIAL_PROJECTS_DB_ID not configured")

    db_snapshot = notion_client.read_database(
        commercial_db_id,
        max_items=1,
    )
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError("Could not read commercial projects DB schema")

    title_prop = _schema_property_name(schema, ["Nombre", "Name", "Title"], {"title"})
    if not title_prop:
        raise RuntimeError("Commercial projects DB does not expose a title property")

    project_notes = (
        (input_data.get("notes") or "").strip()
        or (input_data.get("project_notes") or "").strip()
    )
    if not project_notes:
        project_notes = (
            f"Actualizacion desde raw Granola: {transcript_title} ({transcript_date}) - "
            f"{transcript_url or raw_page_id}"
        )
        if context_excerpt:
            project_notes = _append_context(project_notes, f"Contexto observado: {context_excerpt}")

    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    _set_schema_property(
        properties,
        schema,
        [title_prop],
        project_name,
        expected_types={"title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Estado", "Status"],
        input_data.get("project_estado") or input_data.get("estado"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Acción Requerida", "AcciÃ³n Requerida", "Accion Requerida", "Next Action"],
        input_data.get("project_next_action") or input_data.get("accion_requerida"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Fecha", "Date"],
        input_data.get("project_date") or input_data.get("fecha") or transcript_date,
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Plazo", "Deadline"],
        input_data.get("project_deadline") or input_data.get("plazo"),
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Monto", "Amount"],
        input_data.get("project_amount") or input_data.get("monto"),
        expected_types={"number"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Tipo", "Type"],
        input_data.get("project_type") or input_data.get("tipo"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Cliente", "Client"],
        input_data.get("project_client") or input_data.get("cliente"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["URL fuente", "Source URL", "URL", "Link"],
        input_data.get("source_url") or transcript_url or raw_page_id,
        expected_types={"url", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Notas", "Notes"],
        project_notes,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )

    existing = notion_client.query_database(
        database_id=commercial_db_id,
        filter={"property": title_prop, "title": {"equals": project_name}},
    )
    matched_existing = bool(existing)
    dry_run = bool(input_data.get("dry_run"))
    if dry_run:
        notion_result = {
            "page_id": existing[0]["id"] if matched_existing else "",
            "url": existing[0].get("url", "") if matched_existing else "",
            "created": not matched_existing,
            "updated": matched_existing,
            "dry_run": True,
            "properties": properties,
        }
    elif matched_existing:
        notion_result = notion_client.update_page_properties(
            existing[0]["id"],
            properties=properties,
        )
        notion_result["created"] = False
    else:
        notion_result = notion_client.create_database_page(
            commercial_db_id,
            properties=properties,
        )
        notion_result["created"] = True

    notion_result["ok"] = True
    notion_result["schema_fields_used"] = used_fields
    notion_result["matched_existing"] = matched_existing
    notion_result["target_name"] = project_name
    return notion_result


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
    allow_legacy_raw_task_writes = bool(input_data.get("allow_legacy_raw_task_writes"))

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

    action_items_for_tasks = action_items if allow_legacy_raw_task_writes else []
    if action_items and not allow_legacy_raw_task_writes:
        logger.info(
            "Skipping %d raw action items for transcript %s due to V1 guardrail",
            len(action_items),
            page_id,
        )

    # Step 2: Create action items as Notion tasks
    ai_created = 0
    for item in action_items_for_tasks:
        try:
            task_name = (item.get("text", "Action item") or "Action item").strip()[:200] or "Action item"
            assignee = (item.get("assignee", "sin asignar") or "sin asignar").strip() or "sin asignar"
            due = (item.get("due") or "").strip()
            summary = (
                f"De reunión: {title} ({date}). "
                f"Responsable sugerido: {assignee}. "
                f"Ref: {page_url or page_id}"
            )
            if due:
                summary += f". Vence: {due}"
            handle_notion_upsert_task(
                {
                    "task_id": _build_action_item_task_id(title, date, item),
                    "status": "queued",
                    "team": assignee,
                    "task": "granola.action_item",
                    "task_name": f"[Granola] {task_name}",
                    "project_name": "Proyecto Granola",
                    "input_summary": summary,
                    "source": "granola_process_transcript",
                    "source_kind": "action_item",
                }
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
        "action_items_detected": len(action_items),
        "action_items_created": ai_created,
        "legacy_raw_task_writes_enabled": allow_legacy_raw_task_writes,
        "notification_sent": notification_sent,
    }


def handle_granola_capitalize_raw(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Capitalize an existing raw Granola page directly into the supported V2 canonical targets.
    """
    transcript_page_id = (
        input_data.get("transcript_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")

    page_snapshot = notion_client.read_page(transcript_page_id, max_blocks=80)
    page_data = notion_client.get_page(transcript_page_id)

    transcript_title = (
        (page_snapshot.get("title") or "").strip()
        or _extract_title_from_page(page_data)
        or "Reunion"
    )
    transcript_url = (page_snapshot.get("url") or page_data.get("url") or "").strip()
    transcript_date = (
        (input_data.get("date") or "").strip()
        or _extract_date_from_page(page_data)
        or _today_date()
    )
    transcript_source = (
        (input_data.get("source") or "").strip()
        or _extract_select_value(page_data, "Fuente", "Source")
        or "granola"
    )
    context_excerpt = _compact_excerpt(page_snapshot.get("plain_text") or "")
    add_trace_comments = input_data.get("add_trace_comments", True)
    trace_comments_added = 0
    results: Dict[str, Any] = {}

    proposed_domain = (
        (input_data.get("domain") or "").strip()
        or _extract_select_value(page_data, "Dominio propuesto", "Dominio", "Domain")
        or "Mixto"
    )
    proposed_type = (
        (input_data.get("session_type") or "").strip()
        or (input_data.get("type") or "").strip()
        or _extract_select_value(page_data, "Tipo propuesto", "Tipo", "Type")
        or "Reunión"
    )

    canonical_target_raw = (input_data.get("canonical_target_type") or "").strip()
    canonical_target_key = (
        unicodedata.normalize("NFKD", canonical_target_raw).encode("ascii", "ignore").decode("ascii").lower()
    )
    target_requests = {
        "task": (input_data.get("task_name") or input_data.get("human_task_name") or "").strip(),
        "project": (input_data.get("project_name") or "").strip(),
        "deliverable": (input_data.get("deliverable_name") or "").strip(),
    }
    requested_targets = {key: value for key, value in target_requests.items() if value}
    read_only_target = ""
    read_only_target_name = ""
    if canonical_target_key in {"programa", "program", "programas"}:
        read_only_target = "Programa"
        read_only_target_name = (input_data.get("program_name") or input_data.get("canonical_target_name") or "").strip()
    elif canonical_target_key in {"recurso", "resource", "resources"}:
        read_only_target = "Recurso"
        read_only_target_name = (input_data.get("resource_name") or input_data.get("canonical_target_name") or "").strip()

    if not read_only_target:
        program_name = (input_data.get("program_name") or "").strip()
        resource_name = (input_data.get("resource_name") or "").strip()
        if program_name:
            read_only_target = "Programa"
            read_only_target_name = program_name
        elif resource_name:
            read_only_target = "Recurso"
            read_only_target_name = resource_name

    wants_bridge = bool((input_data.get("bridge_item_name") or "").strip())
    wants_followup = bool((input_data.get("followup_type") or "").strip())

    selected_target_key = ""
    contextual_project_name = ""
    if canonical_target_key in requested_targets:
        selected_target_key = canonical_target_key
        remaining_targets = {key: value for key, value in requested_targets.items() if key != selected_target_key}
        if remaining_targets == {"project": requested_targets["project"]} and selected_target_key in {"task", "deliverable"}:
            contextual_project_name = requested_targets["project"]
        elif remaining_targets:
            selected_target_key = ""
    elif len(requested_targets) == 1:
        selected_target_key = next(iter(requested_targets))

    review_required = False
    review_reason = ""
    review_question = ""
    agent_recommendation = ""
    intended_target = "Por definir en raw"
    canonical_target_type = "Ignorar"
    canonical_target_name = ""

    if read_only_target:
        review_required = True
        canonical_target_type = read_only_target
        canonical_target_name = read_only_target_name or (input_data.get("canonical_target_name") or "").strip()
        intended_target = f"{read_only_target}: {canonical_target_name or 'sin nombre'}"
        review_reason = (
            f"{read_only_target} es un target de clasificacion/lectura en el flujo V2 directo y no admite capitalizacion exitosa desde raw."
        )
        review_question = f"Confirmar si la reunion debe quedar clasificada como {read_only_target.lower()} y qué hacer manualmente con ella."
        agent_recommendation = "Mantener la fila en raw, completar la revision humana y no escribir un artefacto final."
    elif wants_bridge or wants_followup:
        review_required = True
        canonical_target_type = canonical_target_raw or "Ignorar"
        intended_target = ", ".join(
            [part for part in [
                f"Puente: {(input_data.get('bridge_item_name') or '').strip()}" if wants_bridge else "",
                f"Follow-up: {(input_data.get('followup_type') or '').strip()}" if wants_followup else "",
            ] if part]
        ) or "Residuo V1"
        review_reason = "Bridge items y follow-ups siguen siendo residuos de V1 y no son targets canonicos del flujo raw directo V2."
        review_question = "Definir si esto realmente corresponde a tarea, proyecto o entregable, o si solo requiere comentario/revision."
        agent_recommendation = "No crear artefactos V1 desde raw; reclasificar el destino canonico en la misma fila raw."
    elif not selected_target_key:
        review_required = True
        intended_target = ", ".join(
            f"{key}: {value}"
            for key, value in (
                ("Tarea", requested_targets.get("task", "")),
                ("Proyecto", requested_targets.get("project", "")),
                ("Entregable", requested_targets.get("deliverable", "")),
            )
            if value
        ) or "Sin destino explicito"
        review_reason = (
            "El flujo V2 directo requiere exactamente un target canonico soportado por corrida."
            if requested_targets
            else "No se proporciono un target canonico soportado para capitalizar desde raw."
        )
        review_question = "Elegir un unico target canonico soportado: Tarea, Proyecto o Entregable."
        agent_recommendation = "Completar la clasificacion en raw y reintentar con un solo destino canonico."

    if review_required:
        summary = (
            (input_data.get("summary") or "").strip()
            or _build_default_raw_summary(
                target_type=canonical_target_type or "Ignorar",
                target_name=canonical_target_name,
                transcript_title=transcript_title,
            )
        )
        agent_log = (
            (input_data.get("agent_log") or "").strip()
            or f"Capitalizacion detenida en raw. Motivo: {review_reason}"
        )
        raw_status_update = _sync_raw_v2_state(
            page_snapshot.get("page_id") or transcript_page_id,
            page_data,
            status="Pendiente",
            agent_status="Revision requerida",
            agent_action="Bloqueado por ambiguedad",
            proposed_domain=proposed_domain,
            proposed_type=proposed_type,
            canonical_target_type=canonical_target_type or "Ignorar",
            canonical_target_name=canonical_target_name,
            summary=summary,
            agent_log=agent_log,
            review_status="Pendiente",
            review_reason=review_reason,
            review_question=review_question,
            agent_recommendation=agent_recommendation,
            reprocess_after_review=True,
            dry_run=bool(input_data.get("dry_run")),
        )

        review_comment_added = False
        if add_trace_comments and not bool(input_data.get("dry_run")):
            review_comment_added = _leave_review_comment(
                page_snapshot.get("page_id") or transcript_page_id,
                source_evidence=f"{transcript_title} ({transcript_date}) - {transcript_url or transcript_page_id}",
                intended_target=intended_target,
                blocking_ambiguity=review_reason,
                next_review=review_question,
            )
            trace_comments_added += 1 if review_comment_added else 0

        return {
            "ok": False,
            "review_required": True,
            "review_comment_added": review_comment_added,
            "raw_status_update": raw_status_update,
            "transcript_page_id": page_snapshot.get("page_id") or transcript_page_id,
            "transcript_url": transcript_url,
            "title": transcript_title,
            "date": transcript_date,
            "source": transcript_source,
            "results": {},
            "trace_comments_added": trace_comments_added,
            "canonical_target_type": canonical_target_type or "Ignorar",
            "canonical_target_name": canonical_target_name,
        }

    canonical_map = {
        "task": "Tarea",
        "project": "Proyecto",
        "deliverable": "Entregable",
    }
    canonical_target_type = canonical_map[selected_target_key]
    canonical_target_name = requested_targets[selected_target_key]
    dry_run = bool(input_data.get("dry_run"))

    if selected_target_key == "task":
        results["task"] = _upsert_human_task_from_raw(
            raw_page_id=page_snapshot.get("page_id") or transcript_page_id,
            transcript_title=transcript_title,
            transcript_url=transcript_url,
            transcript_date=transcript_date,
            context_excerpt=context_excerpt,
            input_data=input_data,
            project_relation_ids=_relation_ids(input_data.get("project_page_id")),
        )
        final_result = results["task"]
    elif selected_target_key == "project":
        results["project"] = _upsert_commercial_project_from_raw(
            raw_page_id=page_snapshot.get("page_id") or transcript_page_id,
            transcript_title=transcript_title,
            transcript_url=transcript_url,
            transcript_date=transcript_date,
            context_excerpt=context_excerpt,
            input_data=input_data,
        )
        final_result = results["project"]
    else:
        deliverable_notes = _append_context(
            str(input_data.get("deliverable_notes") or ""),
            f"Origen raw: {transcript_title} ({transcript_date}) - {transcript_url or transcript_page_id}",
        )
        if context_excerpt:
            deliverable_notes = _append_context(
                deliverable_notes,
                f"Contexto observado: {context_excerpt}",
            )
        deliverable_payload = {
            "name": canonical_target_name,
            "project_name": (input_data.get("deliverable_project_name") or "").strip() or contextual_project_name or None,
            "deliverable_type": input_data.get("deliverable_type"),
            "review_status": input_data.get("deliverable_review_status"),
            "summary": input_data.get("deliverable_summary") or f"Derivado de reunion raw: {transcript_title}",
            "notes": deliverable_notes,
            "next_action": input_data.get("deliverable_next_action"),
            "date": input_data.get("deliverable_date") or transcript_date,
            "source_task_id": input_data.get("source_task_id"),
            "last_update_date": input_data.get("deliverable_last_update_date") or transcript_date,
        }
        results["deliverable"] = handle_notion_upsert_deliverable(
            {k: v for k, v in deliverable_payload.items() if v not in (None, "", [])}
        )
        final_result = results["deliverable"]

    summary = (
        (input_data.get("summary") or "").strip()
        or _build_default_raw_summary(
            target_type=canonical_target_type,
            target_name=canonical_target_name,
            transcript_title=transcript_title,
        )
    )
    agent_log = (
        (input_data.get("agent_log") or "").strip()
        or f"Capitalizacion directa completada en raw hacia {canonical_target_type.lower()}: {canonical_target_name}."
    )
    raw_status_update = _sync_raw_v2_state(
        page_snapshot.get("page_id") or transcript_page_id,
        page_data,
        status="Procesada",
        agent_status="Procesada",
        agent_action="Capitalizado",
        proposed_domain=proposed_domain,
        proposed_type=proposed_type,
        canonical_target_type=canonical_target_type,
        canonical_target_name=canonical_target_name,
        summary=summary,
        agent_log=agent_log,
        artifact_url=str(final_result.get("url") or "").strip(),
        dry_run=dry_run,
    )

    if add_trace_comments and not dry_run:
        raw_comment = (
            f"Capitalizacion directa registrada para '{transcript_title}' ({transcript_date}). "
            f"Destino: {canonical_target_type}: {canonical_target_name}."
        )
        if _comment_safe(page_snapshot.get("page_id"), raw_comment):
            trace_comments_added += 1

        target_comment = (
            f"Origen raw Granola: '{transcript_title}' ({transcript_date}). "
            f"Ref: {transcript_url or transcript_page_id}"
        )
        target_page_id = _result_page_id(final_result)
        if _comment_safe(target_page_id, target_comment):
            trace_comments_added += 1

    return {
        "ok": True,
        "transcript_page_id": page_snapshot.get("page_id") or transcript_page_id,
        "transcript_url": transcript_url,
        "title": transcript_title,
        "date": transcript_date,
        "source": transcript_source,
        "results": results,
        "raw_status_update": raw_status_update,
        "trace_comments_added": trace_comments_added,
        "canonical_target_type": canonical_target_type,
        "canonical_target_name": canonical_target_name,
    }


def handle_granola_promote_curated_session(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy V1 helper: promote an existing raw Granola page into the retired curated sessions DB.

    This handler stays conservative by:
    - requiring NOTION_CURATED_SESSIONS_DB_ID
    - reading the raw page as evidence first
    - only populating fields supported by the live curated DB schema
    - only setting relations passed explicitly in the payload
    """
    transcript_page_id = (
        input_data.get("transcript_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")
    session_capitalizable_db_id = config.require_notion_session_capitalizable_db_id()

    page_snapshot = notion_client.read_page(transcript_page_id, max_blocks=80)
    page_data = notion_client.get_page(transcript_page_id)

    transcript_title = (
        (page_snapshot.get("title") or "").strip()
        or _extract_title_from_page(page_data)
        or "Sesion"
    )
    transcript_url = (page_snapshot.get("url") or page_data.get("url") or "").strip()
    transcript_date = (
        (input_data.get("date") or "").strip()
        or _extract_date_from_page(page_data)
        or _today_date()
    )
    transcript_source = (
        (input_data.get("source") or "").strip()
        or _extract_select_value(page_data, "Fuente", "Source")
        or "granola"
    )
    context_excerpt = _compact_excerpt(page_snapshot.get("plain_text") or "")

    session_name = (
        (input_data.get("session_name") or "").strip()
        or (input_data.get("title") or "").strip()
        or transcript_title
    )
    session_summary = (
        (input_data.get("summary") or "").strip()
        or (input_data.get("session_summary") or "").strip()
    )
    session_notes = (
        (input_data.get("notes") or "").strip()
        or (input_data.get("session_notes") or "").strip()
    )
    if not session_notes:
        session_notes = f"Origen raw: {transcript_title} ({transcript_date}) - {transcript_url or transcript_page_id}"
        if context_excerpt:
            session_notes = _append_context(
                session_notes,
                f"Contexto observado: {context_excerpt}",
            )

    db_snapshot = notion_client.read_database(
        session_capitalizable_db_id,
        max_items=100,
    )
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError("Could not read curated sessions DB schema")

    title_prop = _schema_property_name(schema, ["Nombre", "Name", "Title"], {"title"})
    if not title_prop:
        raise RuntimeError("Curated sessions DB does not expose a title property")

    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    _set_schema_property(
        properties,
        schema,
        [title_prop],
        session_name,
        expected_types={"title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Fecha", "Date", "Meeting Date"],
        transcript_date,
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Dominio", "Domain"],
        input_data.get("domain") or input_data.get("session_domain"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Tipo", "Type"],
        input_data.get("session_type") or input_data.get("type"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Estado", "Status"],
        input_data.get("estado") or input_data.get("status"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Origen", "Fuente", "Source"],
        input_data.get("origin") or input_data.get("session_origin") or transcript_source,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["URL fuente", "Source URL", "URL", "Link"],
        input_data.get("source_url") or transcript_url or transcript_page_id,
        expected_types={"url", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Resumen", "Summary"],
        session_summary,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Notas", "Notes"],
        session_notes,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Transcripción disponible", "Transcripcion disponible", "Transcript available"],
        input_data.get("transcript_available", True),
        expected_types={"checkbox"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Proyecto", "Project"],
        input_data.get("project_page_id"),
        expected_types={"relation"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Programa", "Program"],
        input_data.get("program_page_id"),
        expected_types={"relation"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Recurso relacionado", "Recurso", "Resource related", "Resource"],
        input_data.get("resource_page_id") or input_data.get("resource_page_ids"),
        expected_types={"relation"},
        used_fields=used_fields,
    )

    source_prop = _schema_property_name(
        schema,
        ["URL fuente", "Source URL", "URL", "Link"],
        {"url", "rich_text"},
    )
    existing_candidates: list[Dict[str, Any]] = []
    match_strategy = ""

    if source_prop and transcript_url:
        source_prop_type = schema.get(source_prop)
        source_filter: Dict[str, Any] | None = None
        if source_prop_type == "url":
            source_filter = {"property": source_prop, "url": {"equals": transcript_url}}
        elif source_prop_type == "rich_text":
            source_filter = {"property": source_prop, "rich_text": {"equals": transcript_url}}
        if source_filter:
            existing_candidates = notion_client.query_database(
                database_id=session_capitalizable_db_id,
                filter=source_filter,
            )

    existing_match, match_strategy = _pick_best_existing_curated_session(
        existing_candidates,
        session_name=session_name,
        transcript_date=transcript_date,
        transcript_url=transcript_url,
        source_prop=source_prop,
    )

    if not existing_match:
        exact_title_candidates = notion_client.query_database(
            database_id=session_capitalizable_db_id,
            filter={"property": title_prop, "title": {"equals": session_name}},
        )
        existing_match, match_strategy = _pick_best_existing_curated_session(
            exact_title_candidates,
            session_name=session_name,
            transcript_date=transcript_date,
            transcript_url=transcript_url,
            source_prop=source_prop,
        )

    if not existing_match:
        snapshot_candidates: list[Dict[str, Any]] = []
        for item in db_snapshot.get("items") or []:
            title_value = str(item.get("title") or "").strip()
            date_value = _extract_date_start((item.get("properties") or {}).get("Fecha"))
            source_value = (
                str((item.get("properties") or {}).get(source_prop) or "").strip()
                if source_prop
                else ""
            )

            snapshot_properties: Dict[str, Any] = {
                title_prop: {"type": "title", "title": [{"plain_text": title_value}]},
            }
            if date_value:
                snapshot_properties["Fecha"] = {"type": "date", "date": {"start": date_value}}
            if source_prop and source_value:
                source_prop_type = schema.get(source_prop)
                if source_prop_type == "url":
                    snapshot_properties[source_prop] = {"type": "url", "url": source_value}
                elif source_prop_type == "rich_text":
                    snapshot_properties[source_prop] = {
                        "type": "rich_text",
                        "rich_text": [{"plain_text": source_value}],
                    }

            snapshot_candidates.append(
                {
                    "id": item.get("page_id"),
                    "url": item.get("url"),
                    "properties": snapshot_properties,
                }
            )

        existing_match, match_strategy = _pick_best_existing_curated_session(
            snapshot_candidates,
            session_name=session_name,
            transcript_date=transcript_date,
            transcript_url=transcript_url,
            source_prop=source_prop,
        )

    matched_existing = bool(existing_match)
    resolved_session_name = session_name
    if matched_existing:
        existing_title = _extract_title_from_page(existing_match)
        same_normalized_title = bool(
            existing_title
            and _normalize_lookup_text(existing_title) == _normalize_lookup_text(session_name)
        )
        if (
            existing_title
            and existing_title != session_name
            and (
                ("?" in session_name and match_strategy == "source_url")
                or (
                    same_normalized_title
                    and ("?" in session_name or match_strategy in {"source_url", "normalized_title_date"})
                )
            )
        ):
            resolved_session_name = existing_title
            properties[title_prop] = {
                "title": [{"text": {"content": resolved_session_name[:2000]}}]
            }

    dry_run = bool(input_data.get("dry_run"))
    if dry_run:
        notion_result = {
            "page_id": existing_match["id"] if matched_existing else "",
            "url": existing_match.get("url", "") if matched_existing else "",
            "created": not matched_existing,
            "updated": matched_existing,
            "dry_run": True,
            "properties": properties,
        }
    elif matched_existing:
        notion_result = notion_client.update_page_properties(
            existing_match["id"],
            properties=properties,
        )
        notion_result["created"] = False
    else:
        notion_result = notion_client.create_database_page(
            session_capitalizable_db_id,
            properties=properties,
        )

    raw_status_update: Dict[str, Any]
    try:
        raw_status_update = _sync_raw_v2_state(
            page_snapshot.get("page_id") or transcript_page_id,
            page_data,
            status="Pendiente",
            agent_status="Revision requerida",
            agent_action="Bloqueado por ambiguedad",
            proposed_domain=(input_data.get("domain") or "").strip()
            or _extract_select_value(page_data, "Dominio propuesto", "Dominio", "Domain")
            or "Mixto",
            proposed_type=(input_data.get("session_type") or "").strip()
            or (input_data.get("type") or "").strip()
            or _extract_select_value(page_data, "Tipo propuesto", "Tipo", "Type")
            or "Reunión",
            canonical_target_type="Ignorar",
            canonical_target_name=resolved_session_name,
            summary=(
                (input_data.get("summary") or "").strip()
                or f"Residuo legacy V1 detectado para '{resolved_session_name}'."
            ),
            agent_log=(
                (input_data.get("agent_log") or "").strip()
                or "Se actualizo la superficie legacy `Registro de Sesiones y Transcripciones`; el target canonico final sigue pendiente en raw."
            ),
            review_status="Pendiente",
            review_reason=(
                "`Registro de Sesiones y Transcripciones` es una superficie legacy V1 y ya no es un artefacto final valido del flujo actual."
            ),
            review_question="Confirmar el target canonico final en raw y reemplazar la referencia legacy si corresponde.",
            agent_recommendation="Usar capitalizacion directa desde raw hacia Tarea, Proyecto o Entregable.",
            artifact_url="",
            reprocess_after_review=True,
            dry_run=dry_run,
        )
    except Exception as exc:
        logger.warning(
            "Failed to sync raw Granola state for %s after curated promotion: %s",
            transcript_page_id,
            exc,
        )
        raw_status_update = {
            "ok": False,
            "page_id": page_snapshot.get("page_id") or transcript_page_id,
            "dry_run": dry_run,
            "error": str(exc),
        }

    trace_comments_added = 0
    add_trace_comments = input_data.get("add_trace_comments", True)
    curated_page_id = _result_page_id(notion_result) or notion_result.get("page_id", "")
    if add_trace_comments and not dry_run:
        raw_comment = (
            f"Referencia legacy V1 registrada para '{resolved_session_name}' ({transcript_date}). "
            f"Sesion legacy: {curated_page_id or 'creada/actualizada'}. Revisar target canonico final en raw."
        )
        if _comment_safe(page_snapshot.get("page_id"), raw_comment):
            trace_comments_added += 1

        curated_comment = (
            f"Origen raw Granola legado: '{transcript_title}' ({transcript_date}). "
            f"Ref: {transcript_url or transcript_page_id}"
        )
        if _comment_safe(curated_page_id, curated_comment):
            trace_comments_added += 1

    return {
        "transcript_page_id": page_snapshot.get("page_id") or transcript_page_id,
        "transcript_url": transcript_url,
        "title": transcript_title,
        "session_name": resolved_session_name,
        "date": transcript_date,
        "source": transcript_source,
        "curated_session": notion_result,
        "raw_status_update": raw_status_update,
        "matched_existing": matched_existing,
        "match_strategy": match_strategy if matched_existing else "",
        "dry_run": dry_run,
        "trace_comments_added": trace_comments_added,
        "schema_fields_used": used_fields,
    }


# ---------------------------------------------------------------------------
# granola.create_human_task_from_curated_session
# ---------------------------------------------------------------------------

def handle_granola_create_human_task_from_curated_session(
    input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Legacy V1 helper: create or update a human task from a curated session page.

    This slice remains conservative:
    - requires NOTION_HUMAN_TASKS_DB_ID
    - reads the curated session page as evidence first
    - requires an explicit task_name/title
    - only populates fields supported by the live human tasks schema
    - only sets explicit or directly inherited relations
    """
    curated_session_page_id = (
        input_data.get("curated_session_page_id")
        or input_data.get("session_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not curated_session_page_id:
        raise ValueError("'curated_session_page_id' is required in input")
    if not config.NOTION_HUMAN_TASKS_DB_ID:
        raise RuntimeError("NOTION_HUMAN_TASKS_DB_ID not configured")

    task_name = (
        (input_data.get("task_name") or "").strip()
        or (input_data.get("title") or "").strip()
    )
    if not task_name:
        raise ValueError("'task_name' is required in input")

    session_snapshot = notion_client.read_page(curated_session_page_id, max_blocks=80)
    session_page = notion_client.get_page(curated_session_page_id)

    session_title = (
        (session_snapshot.get("title") or "").strip()
        or _extract_title_from_page(session_page)
        or "Sesion curada"
    )
    session_url = (session_snapshot.get("url") or session_page.get("url") or "").strip()
    session_date = (
        (input_data.get("session_date") or "").strip()
        or _extract_date_from_page(session_page)
        or _today_date()
    )
    session_domain = (
        (input_data.get("domain") or "").strip()
        or (input_data.get("task_domain") or "").strip()
        or _extract_select_value(session_page, "Dominio", "Domain")
    )
    session_excerpt = _compact_excerpt(session_snapshot.get("plain_text") or "")

    project_relation_ids = _relation_ids(input_data.get("project_page_id"))
    if not project_relation_ids:
        project_relation_ids = _extract_relation_values(session_page, "Proyecto", "Project")

    task_notes = (
        (input_data.get("notes") or "").strip()
        or (input_data.get("task_notes") or "").strip()
    )
    if not task_notes:
        task_notes = (
            f"Derivada de sesion curada: {session_title} ({session_date}) - "
            f"{session_url or curated_session_page_id}"
        )
        if session_excerpt:
            task_notes = _append_context(
                task_notes,
                f"Contexto observado: {session_excerpt}",
            )

    db_snapshot = notion_client.read_database(
        config.NOTION_HUMAN_TASKS_DB_ID,
        max_items=1,
    )
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError("Could not read human tasks DB schema")

    title_prop = _schema_property_name(schema, ["Nombre", "Name", "Title"], {"title"})
    if not title_prop:
        raise RuntimeError("Human tasks DB does not expose a title property")

    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    _set_schema_property(
        properties,
        schema,
        [title_prop],
        task_name,
        expected_types={"title"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Dominio", "Domain"],
        session_domain,
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Proyecto", "Project"],
        project_relation_ids,
        expected_types={"relation"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Sesion relacionada", "Sesión relacionada", "Session related", "Related session"],
        curated_session_page_id,
        expected_types={"relation"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Tipo", "Type"],
        input_data.get("task_type") or input_data.get("type") or "Follow-up",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Estado", "Status"],
        input_data.get("estado") or input_data.get("status") or "Pendiente",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Prioridad", "Priority"],
        input_data.get("priority") or input_data.get("prioridad"),
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Fecha objetivo", "Due date", "Target date"],
        input_data.get("due_date") or input_data.get("target_date"),
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Origen", "Source"],
        input_data.get("origin") or input_data.get("task_origin") or "Sesion",
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["URL fuente", "Source URL", "URL", "Link"],
        input_data.get("source_url") or session_url or curated_session_page_id,
        expected_types={"url", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Notas", "Notes"],
        task_notes,
        expected_types={"rich_text"},
        used_fields=used_fields,
    )

    existing = notion_client.query_database(
        database_id=config.NOTION_HUMAN_TASKS_DB_ID,
        filter={"property": title_prop, "title": {"equals": task_name}},
    )
    matched_existing = bool(existing)
    dry_run = bool(input_data.get("dry_run"))
    if dry_run:
        notion_result = {
            "page_id": existing[0]["id"] if matched_existing else "",
            "url": existing[0].get("url", "") if matched_existing else "",
            "created": not matched_existing,
            "updated": matched_existing,
            "dry_run": True,
            "properties": properties,
        }
    elif matched_existing:
        notion_result = notion_client.update_page_properties(
            existing[0]["id"],
            properties=properties,
        )
        notion_result["created"] = False
    else:
        notion_result = notion_client.create_database_page(
            config.NOTION_HUMAN_TASKS_DB_ID,
            properties=properties,
        )

    trace_comments_added = 0
    add_trace_comments = input_data.get("add_trace_comments", True)
    human_task_page_id = _result_page_id(notion_result) or notion_result.get("page_id", "")
    if add_trace_comments and not dry_run:
        session_comment = (
            f"Tarea humana registrada desde sesion curada: '{task_name}'. "
            f"Tarea: {human_task_page_id or 'creada/actualizada'}."
        )
        if _comment_safe(session_snapshot.get("page_id"), session_comment):
            trace_comments_added += 1

        task_comment = (
            f"Origen sesion curada: '{session_title}' ({session_date}). "
            f"Ref: {session_url or curated_session_page_id}"
        )
        if _comment_safe(human_task_page_id, task_comment):
            trace_comments_added += 1

    return {
        "curated_session_page_id": session_snapshot.get("page_id") or curated_session_page_id,
        "curated_session_url": session_url,
        "session_title": session_title,
        "task_name": task_name,
        "date": session_date,
        "human_task": notion_result,
        "matched_existing": matched_existing,
        "dry_run": dry_run,
        "trace_comments_added": trace_comments_added,
        "schema_fields_used": used_fields,
    }


# ---------------------------------------------------------------------------
# granola.update_commercial_project_from_curated_session
# ---------------------------------------------------------------------------

def handle_granola_update_commercial_project_from_curated_session(
    input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Legacy V1 helper: update the human commercial projects DB from a curated session.

    This slice stays narrow:
    - requires NOTION_COMMERCIAL_PROJECTS_DB_ID
    - reads the curated session as evidence first
    - requires an explicit project target or a project relation on the session
    - only updates supported commercial fields present in the live schema
    - leaves traceability through comments rather than freeform page content
    """
    curated_session_page_id = (
        input_data.get("curated_session_page_id")
        or input_data.get("session_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not curated_session_page_id:
        raise ValueError("'curated_session_page_id' is required in input")
    if not config.NOTION_COMMERCIAL_PROJECTS_DB_ID:
        raise RuntimeError("NOTION_COMMERCIAL_PROJECTS_DB_ID not configured")

    session_snapshot = notion_client.read_page(curated_session_page_id, max_blocks=80)
    session_page = notion_client.get_page(curated_session_page_id)

    session_title = (
        (session_snapshot.get("title") or "").strip()
        or _extract_title_from_page(session_page)
        or "Sesion curada"
    )
    session_url = (session_snapshot.get("url") or session_page.get("url") or "").strip()
    session_date = (
        (input_data.get("session_date") or "").strip()
        or _extract_date_from_page(session_page)
        or _today_date()
    )
    session_excerpt = _compact_excerpt(session_snapshot.get("plain_text") or "")

    project_page_id = (
        (input_data.get("project_page_id") or "").strip()
        or (_extract_relation_values(session_page, "Proyecto", "Project") or [""])[0]
    )
    if not project_page_id:
        review_comment_added = _leave_review_comment(
            session_snapshot.get("page_id") or curated_session_page_id,
            source_evidence=f"{session_title} ({session_date}) - {session_url or curated_session_page_id}",
            intended_target="Proyecto comercial canonico",
            blocking_ambiguity="No project target verified on the capitalizable session.",
            next_review="Relacionar la sesion con el proyecto correcto o pasar project_page_id verificado.",
        )
        return {
            "ok": False,
            "blocked_by_ambiguity": True,
            "review_comment_added": review_comment_added,
            "curated_session_page_id": session_snapshot.get("page_id") or curated_session_page_id,
            "curated_session_url": session_url,
            "session_title": session_title,
            "date": session_date,
            "trace_comments_added": 1 if review_comment_added else 0,
        }

    update_fields = {
        "Estado": input_data.get("estado") or input_data.get("project_estado"),
        "Acción Requerida": input_data.get("accion_requerida") or input_data.get("project_next_action"),
        "Fecha": input_data.get("fecha") or input_data.get("project_date"),
        "Plazo": input_data.get("plazo") or input_data.get("project_deadline"),
        "Monto": input_data.get("monto") or input_data.get("project_amount"),
        "Tipo": input_data.get("tipo") or input_data.get("project_type"),
        "Cliente": input_data.get("cliente") or input_data.get("project_client"),
    }
    if all(value in (None, "", []) for value in update_fields.values()):
        raise ValueError(
            "At least one explicit commercial field is required: estado, accion_requerida, fecha, plazo, monto, tipo or cliente"
        )

    db_snapshot = notion_client.read_database(
        config.NOTION_COMMERCIAL_PROJECTS_DB_ID,
        max_items=1,
    )
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict):
        raise RuntimeError("Could not read commercial projects DB schema")

    project_page = notion_client.get_page(project_page_id)
    project_title = _extract_title_from_page(project_page) or "Proyecto comercial"

    properties: Dict[str, Any] = {}
    used_fields: list[str] = []
    _set_schema_property(
        properties,
        schema,
        ["Estado", "Status"],
        update_fields["Estado"],
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Acción Requerida", "Accion Requerida", "Next Action"],
        update_fields["Acción Requerida"],
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Fecha", "Date"],
        update_fields["Fecha"],
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Plazo", "Deadline"],
        update_fields["Plazo"],
        expected_types={"date"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Monto", "Amount"],
        update_fields["Monto"],
        expected_types={"number"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Tipo", "Type"],
        update_fields["Tipo"],
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )
    _set_schema_property(
        properties,
        schema,
        ["Cliente", "Client"],
        update_fields["Cliente"],
        expected_types={"select", "status", "rich_text"},
        used_fields=used_fields,
    )

    if not properties:
        raise RuntimeError("No supported commercial project fields were available to update")

    dry_run = bool(input_data.get("dry_run"))
    if dry_run:
        notion_result = {
            "page_id": project_page_id,
            "url": project_page.get("url", ""),
            "updated": True,
            "dry_run": True,
            "properties": properties,
        }
    else:
        notion_result = notion_client.update_page_properties(
            project_page_id,
            properties=properties,
        )

    trace_comments_added = 0
    add_trace_comments = input_data.get("add_trace_comments", True)
    if add_trace_comments and not dry_run:
        project_comment_parts = [
            f"Actualizacion comercial desde sesion curada: '{session_title}' ({session_date}).",
        ]
        if update_fields["Estado"]:
            project_comment_parts.append(f"Estado -> {update_fields['Estado']}.")
        if update_fields["Acción Requerida"]:
            project_comment_parts.append(f"Accion requerida -> {update_fields['Acción Requerida']}.")
        if session_excerpt:
            project_comment_parts.append(f"Contexto: {session_excerpt}")
        if _comment_safe(project_page_id, " ".join(project_comment_parts)):
            trace_comments_added += 1

        session_comment = (
            f"Proyecto comercial actualizado: '{project_title}'. "
            f"Ref: {project_page.get('url') or project_page_id}"
        )
        if _comment_safe(session_snapshot.get("page_id"), session_comment):
            trace_comments_added += 1

    return {
        "curated_session_page_id": session_snapshot.get("page_id") or curated_session_page_id,
        "curated_session_url": session_url,
        "session_title": session_title,
        "project_page_id": project_page_id,
        "project_title": project_title,
        "commercial_project": notion_result,
        "dry_run": dry_run,
        "trace_comments_added": trace_comments_added,
        "schema_fields_used": used_fields,
    }


# ---------------------------------------------------------------------------
# granola.promote_operational_slice
# ---------------------------------------------------------------------------

def handle_granola_promote_operational_slice(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy V1 orchestrator for explicit `raw -> curated -> destination` slices.

    This orchestrator does not invent classification. It only chains the already
    conservative handlers when the caller supplies explicit sub-payloads.
    """
    transcript_page_id = (
        input_data.get("transcript_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")

    curated_payload = dict(input_data.get("curated_payload") or {})
    human_task_payload = dict(input_data.get("human_task_payload") or {})
    commercial_project_payload = dict(input_data.get("commercial_project_payload") or {})
    dry_run = bool(input_data.get("dry_run"))

    if not curated_payload:
        raise ValueError("'curated_payload' is required")
    if not human_task_payload and not commercial_project_payload:
        raise ValueError("At least one destination payload is required: human_task_payload or commercial_project_payload")

    curated_payload["transcript_page_id"] = transcript_page_id
    if dry_run and "dry_run" not in curated_payload:
        curated_payload["dry_run"] = True
    curated_result = handle_granola_promote_curated_session(curated_payload)
    curated_page_id = _result_page_id(curated_result.get("curated_session")) or ""
    if not curated_page_id and dry_run:
        curated_page_id = (curated_payload.get("curated_session_page_id") or "").strip()
    results: Dict[str, Any] = {"curated": curated_result}
    if not curated_page_id and dry_run:
        skip_reason = "curated_session_page_id_unavailable_in_dry_run_for_new_session"
        if human_task_payload:
            results["human_task"] = {
                "dry_run": True,
                "skipped": True,
                "reason": skip_reason,
            }
        if commercial_project_payload:
            results["commercial_project"] = {
                "dry_run": True,
                "skipped": True,
                "reason": skip_reason,
            }
        return {
            "transcript_page_id": transcript_page_id,
            "curated_session_page_id": "",
            "dry_run": True,
            "results": results,
        }
    if not curated_page_id:
        raise RuntimeError("Could not resolve curated session page id from promote_curated_session result")
    if human_task_payload:
        human_task_payload["curated_session_page_id"] = curated_page_id
        if dry_run and "dry_run" not in human_task_payload:
            human_task_payload["dry_run"] = True
        results["human_task"] = handle_granola_create_human_task_from_curated_session(human_task_payload)
    if commercial_project_payload:
        commercial_project_payload["curated_session_page_id"] = curated_page_id
        if dry_run and "dry_run" not in commercial_project_payload:
            commercial_project_payload["dry_run"] = True
        results["commercial_project"] = handle_granola_update_commercial_project_from_curated_session(commercial_project_payload)

    return {
        "transcript_page_id": transcript_page_id,
        "curated_session_page_id": curated_page_id,
        "dry_run": dry_run,
        "results": results,
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
