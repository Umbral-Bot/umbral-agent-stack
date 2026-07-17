"""
granola.capitalize_task_from_raw — deterministic raw -> Tarea capitalization (P1).

Implements the B path of the hybrid capitalization plan
(``docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md``): the Worker as
a deterministic execution engine over a raw row of ``Transcripciones Granola``
whose ``Destino canonico`` is already ``Tarea`` and whose human gate
(``Procesar con agente``) is already ticked.

Hard properties of this handler:

- **0 LLM calls.** Everything is property comparison over data already present.
- **dry_run=True by default.** A dry run performs reads only and reports the
  exact action it *would* take (create/update/review/error), the exact
  properties it would write, and why — it never claims a capitalization
  happened.
- **Human tasks binding only.** Writes go exclusively to
  ``config.NOTION_HUMAN_TASKS_DB_ID`` (Registro de Tareas y Proximas Acciones).
  ``NOTION_TASKS_DB_ID`` (a different, stack-operational DB) is never read here.
- **Fail closed.** Missing binding, missing raw, wrong source DB, wrong
  ``Destino canonico``, unticked gate, thin evidence, invalid Trazabilidad or
  ambiguous dedup all stop the run before any write.
- **Safe dedup.** 0 exact title matches -> create; 1 match -> update only when
  the caller passes ``expected_task_page_id`` matching that page; 2+ matches
  -> review. No semantic matching, ever.
- **Anti-Comgrap guard.** If the raw carries structured commercial signals
  (Cliente/Partner relation + Reunión/Llamada + project signal), converting it
  into a loose task requires the explicit input ``human_confirmed_task=true``;
  otherwise the row is routed to review (Duda de clasificación).
- **Verify-after-write is blocking.** Success is only declared when a re-read
  of both the raw and the task passes ``verify_task_capitalization`` (P0).
  A write response is never treated as evidence.
- Pre-write review outcomes perform **no writes at all** (not even the review
  close — it is returned as a plan for the orchestrator/human). The only
  mutation on a failure path is the post-write technical close when
  verification fails after real writes.

No transcript content, PII or secrets are ever included in results or logs —
only lengths and property names.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from .. import config, notion_client
from .granola import (
    _extract_named_date_property,
    _extract_page_text_property,
    _extract_relation_values,
    _extract_select_value,
    _extract_title_from_page,
    _page_schema_from_page,
    _relation_ids,
    _schema_property_name,
    _set_schema_property,
)
from .granola_capitalization import (
    ExpectedCapitalization,
    RelationExpectation,
    append_capitalization_traceability,
    verify_task_capitalization,
)
from .granola_finality import DEFAULT_MIN_STABLE_CHARS

logger = logging.getLogger("worker.tasks.granola_task_capitalize")

CAPITALIZATION_MODE = "worker_task_from_raw_v1"
_ANTI_COMGRAP_SESSION_TYPES = {"Reunión", "Llamada", "Reunion"}
_NOTION_RICH_TEXT_CHUNK = 2000


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off", ""}:
            return False
    return default


def _normalize_notion_id(value: str | None) -> str:
    return (value or "").replace("-", "").strip().lower()


def _checkbox_is_true(page_data: Dict[str, Any], *names: str) -> bool:
    properties = page_data.get("properties") or {}
    for name in names:
        prop = properties.get(name)
        if isinstance(prop, dict) and prop.get("type") == "checkbox":
            return bool(prop.get("checkbox"))
    return False


def _chunked_rich_text_payload(text: str) -> Dict[str, Any]:
    """Build a rich_text property payload without truncating.

    ``_set_schema_property`` truncates rich_text at 2000 chars, which would
    silently drop ingest Trazabilidad lines. Chunk instead (Notion accepts
    multiple text objects of <=2000 chars each).
    """
    chunks = [text[i : i + _NOTION_RICH_TEXT_CHUNK] for i in range(0, len(text), _NOTION_RICH_TEXT_CHUNK)] or [""]
    return {"rich_text": [{"text": {"content": chunk}} for chunk in chunks]}


def _result(
    *,
    ok: bool,
    action: str,
    dry_run: bool,
    reason: str,
    transcript_page_id: str,
    **extra: Any,
) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "ok": ok,
        "action": action,
        "capitalized": bool(extra.pop("capitalized", False)),
        "dry_run": dry_run,
        "reason": reason,
        "transcript_page_id": transcript_page_id,
    }
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
# Phase 1 — preflight (reads only)
# ---------------------------------------------------------------------------


def _run_preflight(
    *,
    transcript_page_id: str,
    human_confirmed_task: bool,
    min_evidence_chars: int,
) -> Dict[str, Any]:
    """Run every pre-write gate. Returns a dict with ``passed`` plus either the
    loaded raw context (on pass) or a structured refusal (on fail)."""
    checks: Dict[str, Any] = {}

    if not config.NOTION_HUMAN_TASKS_DB_ID:
        raise RuntimeError(
            "NOTION_HUMAN_TASKS_DB_ID not configured — fail closed. "
            "granola.capitalize_task_from_raw writes only to the human tasks DB "
            "and never falls back to NOTION_TASKS_DB_ID."
        )
    checks["human_tasks_binding"] = "ok"

    if not config.NOTION_GRANOLA_DB_ID:
        raise RuntimeError("NOTION_GRANOLA_DB_ID not configured — cannot validate raw source DB.")
    checks["granola_binding"] = "ok"

    try:
        page_data = notion_client.get_page(transcript_page_id)
    except Exception as exc:  # noqa: BLE001 — structured refusal, no write happened
        return {
            "passed": False,
            "action": "error",
            "reason": "raw_page_not_accessible",
            "detail": f"{type(exc).__name__}: {str(exc)[:200]}",
            "checks": checks,
        }
    checks["raw_page"] = "ok"

    parent = page_data.get("parent") or {}
    parent_db = _normalize_notion_id(str(parent.get("database_id") or ""))
    if parent_db != _normalize_notion_id(config.NOTION_GRANOLA_DB_ID):
        return {
            "passed": False,
            "action": "error",
            "reason": "raw_not_in_transcripciones_granola",
            "detail": "The page does not belong to the Transcripciones Granola database.",
            "checks": checks,
        }
    checks["raw_source_db"] = "ok"

    destino = _extract_select_value(page_data, "Destino canonico", "Destino canónico")
    if destino != "Tarea":
        return {
            "passed": False,
            "action": "error",
            "reason": "destino_canonico_not_tarea",
            "detail": f"Destino canonico={destino or '(vacio)'} — this task only handles Tarea. "
            "Proyecto/Entregable/Programa/Recurso stay in Revision requerida per contract.",
            "checks": checks,
        }
    checks["destino_canonico"] = "ok"

    if not _checkbox_is_true(page_data, "Procesar con agente"):
        return {
            "passed": False,
            "action": "error",
            "reason": "procesar_con_agente_not_set",
            "detail": "Human gate unticked — the row is not authorized for processing.",
            "checks": checks,
        }
    checks["procesar_con_agente"] = "ok"

    try:
        page_snapshot = notion_client.read_page(transcript_page_id, max_blocks=30)
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "action": "error",
            "reason": "raw_content_not_readable",
            "detail": f"{type(exc).__name__}: {str(exc)[:200]}",
            "checks": checks,
        }
    evidence_chars = len((page_snapshot.get("plain_text") or "").strip())
    if evidence_chars < min_evidence_chars:
        return {
            "passed": False,
            "action": "review",
            "reason": "insufficient_evidence",
            "motivo_revision": "Falta evidencia",
            "detail": f"Raw body has {evidence_chars} chars (< {min_evidence_chars}).",
            "checks": checks,
            "page_data": page_data,
        }
    checks["evidence"] = f"ok ({evidence_chars} chars)"

    existing_traceability = _extract_page_text_property(page_data, "Trazabilidad", "Traceability")
    trace_probe = append_capitalization_traceability(
        existing_traceability,
        source="probe",
        capitalization_mode="probe",
        canonical_target_type="probe",
        canonical_target_name="probe",
        processed_at="probe",
    )
    if not trace_probe.ok:
        return {
            "passed": False,
            "action": "review",
            "reason": "invalid_traceability",
            "motivo_revision": "Bloqueo técnico",
            "detail": trace_probe.error.as_dict() if trace_probe.error else {},
            "checks": checks,
            "page_data": page_data,
        }
    checks["traceability_format"] = "ok"

    cliente_rel = _extract_relation_values(page_data, "Cliente/Partner relacionado")
    tipo = _extract_select_value(page_data, "Tipo propuesto")
    proyecto_text = _extract_page_text_property(page_data, "Proyecto").strip()
    proyecto_rel = _extract_relation_values(page_data, "Proyecto relacionado")
    commercial_signals = bool(cliente_rel) and tipo in _ANTI_COMGRAP_SESSION_TYPES and bool(
        proyecto_text or proyecto_rel
    )
    checks["anti_comgrap_signals"] = {
        "cliente_partner_relacionado": bool(cliente_rel),
        "tipo_propuesto": tipo,
        "proyecto_signal": bool(proyecto_text or proyecto_rel),
        "triggered": commercial_signals,
    }
    if commercial_signals and not human_confirmed_task:
        return {
            "passed": False,
            "action": "review",
            "reason": "anti_comgrap_requires_confirmation",
            "motivo_revision": "Duda de clasificación",
            "detail": (
                "Structured commercial signals present (client relation + "
                f"{tipo} + project signal). Converting this meeting into a loose "
                "task requires human_confirmed_task=true (G2/G7 project-first guardrail)."
            ),
            "checks": checks,
            "page_data": page_data,
        }
    checks["anti_comgrap"] = "ok" + (" (human_confirmed_task)" if commercial_signals else "")

    return {
        "passed": True,
        "checks": checks,
        "page_data": page_data,
        "evidence_chars": evidence_chars,
        "existing_traceability": existing_traceability,
        "raw_relations": {
            "Proyecto relacionado": proyecto_rel,
            "Cliente/Partner relacionado": cliente_rel,
        },
    }


# ---------------------------------------------------------------------------
# Phase 2 — plan (reads only)
# ---------------------------------------------------------------------------


def _load_tasks_db_schema() -> Dict[str, str]:
    db_snapshot = notion_client.read_database(config.NOTION_HUMAN_TASKS_DB_ID, max_items=1)
    schema = db_snapshot.get("schema") or {}
    if not isinstance(schema, dict) or not schema:
        raise RuntimeError("Could not read human tasks DB schema")
    return schema


def _dedup_by_exact_title(
    *,
    schema: Dict[str, str],
    task_name: str,
    expected_task_page_id: str,
) -> Dict[str, Any]:
    title_prop = _schema_property_name(schema, ["Nombre", "Name", "Title"], {"title"})
    if not title_prop:
        raise RuntimeError("Human tasks DB does not expose a title property")

    matches = notion_client.query_database(
        database_id=config.NOTION_HUMAN_TASKS_DB_ID,
        filter={"property": title_prop, "title": {"equals": task_name}},
    )
    match_ids = [str(m.get("id") or "") for m in matches]
    expected_norm = _normalize_notion_id(expected_task_page_id)

    if len(matches) == 0:
        if expected_norm:
            return {
                "action": "review",
                "reason": "expected_task_not_found_by_title",
                "motivo_revision": "Ambigüedad de match",
                "matches": match_ids,
                "title_prop": title_prop,
            }
        return {"action": "create", "matches": match_ids, "title_prop": title_prop}

    if len(matches) == 1:
        match_id = match_ids[0]
        if not expected_norm:
            return {
                "action": "review",
                "reason": "single_match_requires_expected_task_page_id",
                "motivo_revision": "Ambigüedad de match",
                "matches": match_ids,
                "title_prop": title_prop,
                "detail": (
                    "One exact-title match exists. Updating by inference is "
                    "forbidden in P1 — pass expected_task_page_id equal to the "
                    "match to authorize the update."
                ),
            }
        if _normalize_notion_id(match_id) != expected_norm:
            return {
                "action": "review",
                "reason": "expected_task_page_id_mismatch",
                "motivo_revision": "Ambigüedad de match",
                "matches": match_ids,
                "title_prop": title_prop,
            }
        return {
            "action": "update",
            "matches": match_ids,
            "target_task_page_id": match_id,
            "title_prop": title_prop,
        }

    return {
        "action": "review",
        "reason": "multiple_exact_title_matches",
        "motivo_revision": "Ambigüedad de match",
        "matches": match_ids,
        "title_prop": title_prop,
    }


def _build_task_properties(
    *,
    schema: Dict[str, str],
    page_data: Dict[str, Any],
    input_data: Dict[str, Any],
    task_name: str,
    raw_url: str,
    raw_title: str,
    raw_date: str,
) -> tuple[Dict[str, Any], list[str], list[str]]:
    """Schema-driven task properties. Relations are only ever propagated from
    the raw or taken from explicit input IDs — never inferred."""
    properties: Dict[str, Any] = {}
    used_fields: list[str] = []

    _set_schema_property(properties, schema, ["Nombre", "Name", "Title"], task_name, expected_types={"title"}, used_fields=used_fields)
    _set_schema_property(
        properties, schema, ["Dominio", "Domain"],
        _extract_select_value(page_data, "Dominio propuesto"),
        expected_types={"select", "status", "rich_text"}, used_fields=used_fields,
    )
    _set_schema_property(
        properties, schema, ["Estado", "Status"],
        input_data.get("estado") or input_data.get("status") or "Pendiente",
        expected_types={"select", "status", "rich_text"}, used_fields=used_fields,
    )
    _set_schema_property(
        properties, schema, ["Prioridad", "Priority"],
        input_data.get("priority") or input_data.get("prioridad"),
        expected_types={"select", "status", "rich_text"}, used_fields=used_fields,
    )
    _set_schema_property(
        properties, schema, ["Fecha objetivo", "Due date", "Target date"],
        input_data.get("due_date")
        or _extract_named_date_property(page_data, "Fecha de acción derivada", "Fecha de accion derivada"),
        expected_types={"date"}, used_fields=used_fields,
    )
    _set_schema_property(
        properties, schema, ["Origen", "Source"],
        input_data.get("origin") or "Sesión",
        expected_types={"select", "status", "rich_text"}, used_fields=used_fields,
    )
    _set_schema_property(
        properties, schema, ["URL fuente", "Source URL", "URL", "Link"],
        raw_url, expected_types={"url", "rich_text"}, used_fields=used_fields,
    )
    _set_schema_property(
        properties, schema, ["Notas", "Notes"],
        f"Derivada de raw Granola: {raw_title} ({raw_date}) - {raw_url}",
        expected_types={"rich_text"}, used_fields=used_fields,
    )

    project_ids = _relation_ids(input_data.get("project_page_id")) or _extract_relation_values(
        page_data, "Proyecto relacionado"
    )
    if project_ids:
        _set_schema_property(
            properties, schema, ["Proyecto", "Project"],
            project_ids, expected_types={"relation"}, used_fields=used_fields,
        )

    return properties, used_fields, project_ids


def _build_raw_close_properties(
    *,
    raw_schema: Dict[str, str],
    task_url: str,
    traceability_text: str,
    today: str,
) -> tuple[Dict[str, Any], str | None]:
    """Success close of the raw row per docs/databases/02 step 7a."""
    properties: Dict[str, Any] = {}
    used: list[str] = []
    _set_schema_property(properties, raw_schema, ["URL artefacto"], task_url, expected_types={"url"}, used_fields=used)
    _set_schema_property(properties, raw_schema, ["Estado"], "Procesada", expected_types={"select", "status"}, used_fields=used)
    _set_schema_property(properties, raw_schema, ["Estado agente"], "Procesada", expected_types={"select", "status"}, used_fields=used)
    _set_schema_property(properties, raw_schema, ["Accion agente", "Acción agente"], "Capitalizado", expected_types={"select", "status"}, used_fields=used)
    _set_schema_property(properties, raw_schema, ["Estado revisión", "Estado revision"], "No aplica", expected_types={"select", "status"}, used_fields=used)
    _set_schema_property(properties, raw_schema, ["Fecha que el agente procesó", "Fecha que el agente proceso"], today, expected_types={"date"}, used_fields=used)
    procesar_prop = _schema_property_name(raw_schema, ["Procesar con agente"], {"checkbox"})
    if procesar_prop:
        properties[procesar_prop] = {"checkbox": False}
    trazabilidad_prop = _schema_property_name(raw_schema, ["Trazabilidad", "Traceability"], {"rich_text"})
    if trazabilidad_prop:
        properties[trazabilidad_prop] = _chunked_rich_text_payload(traceability_text)
    return properties, trazabilidad_prop


def _build_review_close_plan(*, motivo: str, reason: str, detail: Any) -> Dict[str, Any]:
    """Review close per docs/databases/02 step 7c — returned as a PLAN only.

    P1 never writes this pre-write review close itself (conservative reading of
    the dedup contract: refusal paths perform zero writes). The orchestrator or
    a human applies it.
    """
    return {
        "Estado": "Pendiente",
        "Estado agente": "Revision requerida",
        "Accion agente": "Bloqueado por ambiguedad",
        "Estado revisión": "Pendiente",
        "Motivo revisión": motivo,
        "Pregunta de revisión": f"Resolver bloqueo determinista: {reason}",
        "Recomendación agente": "Revisar el detalle estructurado del worker y decidir la ruta.",
        "Procesar con agente": False,
        "_detail": detail,
        "_not_written_by_p1": True,
    }


# ---------------------------------------------------------------------------
# Phase 3 — execute (writes; only reached with dry_run=false)
# ---------------------------------------------------------------------------


def _apply_technical_review_close(transcript_page_id: str, raw_schema: Dict[str, str], detail: str) -> bool:
    """Post-write failure close: Revision requerida + Bloqueo técnico. Best effort."""
    try:
        properties: Dict[str, Any] = {}
        used: list[str] = []
        _set_schema_property(properties, raw_schema, ["Estado"], "Pendiente", expected_types={"select", "status"}, used_fields=used)
        _set_schema_property(properties, raw_schema, ["Estado agente"], "Revision requerida", expected_types={"select", "status"}, used_fields=used)
        _set_schema_property(properties, raw_schema, ["Motivo revisión", "Motivo revision"], "Bloqueo técnico", expected_types={"select", "status"}, used_fields=used)
        _set_schema_property(properties, raw_schema, ["Estado revisión", "Estado revision"], "Pendiente", expected_types={"select", "status"}, used_fields=used)
        _set_schema_property(properties, raw_schema, ["Pregunta de revisión", "Pregunta de revision"], detail[:1800], expected_types={"rich_text"}, used_fields=used)
        procesar_prop = _schema_property_name(raw_schema, ["Procesar con agente"], {"checkbox"})
        if procesar_prop:
            properties[procesar_prop] = {"checkbox": False}
        if properties:
            notion_client.update_page_properties(transcript_page_id, properties=properties)
        return True
    except Exception:  # noqa: BLE001 — never mask the original verification failure
        logger.exception("Technical review close failed for %s", transcript_page_id[:8])
        return False


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def handle_granola_capitalize_task_from_raw(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic raw -> Tarea capitalization with blocking verify-after-write.

    Input:
        transcript_page_id (str, required): raw page in Transcripciones Granola.
        dry_run (bool, default TRUE): reads only; report the exact plan.
        human_confirmed_task (bool, default false): required when the raw carries
            structured commercial signals (anti-Comgrap guard).
        expected_task_page_id (str, optional): required to authorize an update
            when exactly one exact-title match exists.
        task_name (str, optional): task title; defaults to the raw title.
        estado / priority / due_date / origin / project_page_id (optional):
            explicit task fields; nothing else is inferred.
        min_evidence_chars (int, optional): evidence threshold override.
        processed_at (str, optional): ISO override for Trazabilidad (tests).

    Returns a structured decision. ``capitalized=True`` only ever appears on a
    non-dry-run whose post-write re-read passed verification.
    """
    transcript_page_id = str(
        input_data.get("transcript_page_id")
        or input_data.get("page_id")
        or input_data.get("page_id_or_url")
        or ""
    ).strip()
    if not transcript_page_id:
        raise ValueError("'transcript_page_id' is required in input")

    dry_run = _as_bool(input_data.get("dry_run"), True)
    human_confirmed_task = _as_bool(input_data.get("human_confirmed_task"), False)
    expected_task_page_id = str(input_data.get("expected_task_page_id") or "").strip()
    min_evidence_chars = int(input_data.get("min_evidence_chars") or DEFAULT_MIN_STABLE_CHARS)

    # ---- Phase 1: preflight -------------------------------------------------
    preflight = _run_preflight(
        transcript_page_id=transcript_page_id,
        human_confirmed_task=human_confirmed_task,
        min_evidence_chars=min_evidence_chars,
    )
    if not preflight["passed"]:
        extra: Dict[str, Any] = {
            "preflight": preflight["checks"],
            "detail": preflight.get("detail"),
        }
        if preflight["action"] == "review":
            extra["motivo_revision"] = preflight.get("motivo_revision", "")
            extra["planned_raw_close"] = _build_review_close_plan(
                motivo=preflight.get("motivo_revision", "Otro"),
                reason=preflight["reason"],
                detail=preflight.get("detail"),
            )
        return _result(
            ok=False,
            action=preflight["action"],
            dry_run=dry_run,
            reason=preflight["reason"],
            transcript_page_id=transcript_page_id,
            **extra,
        )

    page_data = preflight["page_data"]
    raw_title = _extract_title_from_page(page_data) or "Reunión"
    raw_url = str(page_data.get("url") or "").strip()
    raw_date = (
        _extract_named_date_property(page_data, "Fecha", "Date")
        or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    task_name = str(input_data.get("task_name") or "").strip() or raw_title

    # ---- Phase 2: plan (dedup + payloads, reads only) ------------------------
    schema = _load_tasks_db_schema()
    dedup = _dedup_by_exact_title(
        schema=schema, task_name=task_name, expected_task_page_id=expected_task_page_id
    )
    if dedup["action"] == "review":
        return _result(
            ok=False,
            action="review",
            dry_run=dry_run,
            reason=dedup["reason"],
            transcript_page_id=transcript_page_id,
            preflight=preflight["checks"],
            motivo_revision=dedup["motivo_revision"],
            dedup={"matches": dedup["matches"], "detail": dedup.get("detail", "")},
            planned_raw_close=_build_review_close_plan(
                motivo=dedup["motivo_revision"], reason=dedup["reason"], detail=dedup.get("detail", "")
            ),
        )

    task_properties, task_fields_used, project_ids = _build_task_properties(
        schema=schema,
        page_data=page_data,
        input_data=input_data,
        task_name=task_name,
        raw_url=raw_url,
        raw_title=raw_title,
        raw_date=raw_date,
    )

    processed_at = str(input_data.get("processed_at") or "").strip() or (
        datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    source_value = _extract_select_value(page_data, "Fuente", "Source") or "granola"
    trace = append_capitalization_traceability(
        preflight["existing_traceability"],
        source=source_value,
        capitalization_mode=CAPITALIZATION_MODE,
        canonical_target_type="task",
        canonical_target_name=task_name,
        processed_at=processed_at,
    )
    if not trace.ok:
        # Preflight probed format already; this only fires on forbidden new values.
        return _result(
            ok=False,
            action="review",
            dry_run=dry_run,
            reason="traceability_append_rejected",
            transcript_page_id=transcript_page_id,
            preflight=preflight["checks"],
            motivo_revision="Bloqueo técnico",
            detail=trace.error.as_dict() if trace.error else {},
            planned_raw_close=_build_review_close_plan(
                motivo="Bloqueo técnico",
                reason="traceability_append_rejected",
                detail=trace.error.as_dict() if trace.error else {},
            ),
        )

    raw_schema = _page_schema_from_page(page_data)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if dry_run:
        planned_close, _ = _build_raw_close_properties(
            raw_schema=raw_schema,
            task_url="<url real de la tarea tras relectura>",
            traceability_text=trace.text,
            today=today,
        )
        return _result(
            ok=True,
            action=dedup["action"],
            dry_run=True,
            reason="dry_run_plan_only",
            transcript_page_id=transcript_page_id,
            capitalized=False,
            preflight=preflight["checks"],
            dedup={"matches": dedup["matches"], "target_task_page_id": dedup.get("target_task_page_id", "")},
            task_name=task_name,
            planned_task_properties=task_properties,
            planned_task_fields=task_fields_used,
            planned_raw_close=planned_close,
            planned_traceability_preview={
                "preserved_ingest_lines": len(trace.preserved_lines),
                "appended_keys": list(trace.appended_keys),
                "updated_keys": list(trace.updated_keys),
            },
            note="dry_run: no se realizó ninguna escritura; esto es el plan exacto.",
        )

    # ---- Phase 3: execute ----------------------------------------------------
    try:
        if dedup["action"] == "create":
            write_result = notion_client.create_database_page(
                config.NOTION_HUMAN_TASKS_DB_ID, properties=task_properties
            )
            task_page_id = str(write_result.get("page_id") or "")
        else:
            task_page_id = dedup["target_task_page_id"]
            notion_client.update_page_properties(task_page_id, properties=task_properties)
    except Exception as exc:  # noqa: BLE001 — task write failed; raw untouched
        return _result(
            ok=False,
            action="error",
            dry_run=False,
            reason="task_write_failed",
            transcript_page_id=transcript_page_id,
            preflight=preflight["checks"],
            detail=f"{type(exc).__name__}: {str(exc)[:300]}",
            note="El raw no fue modificado; la fila sigue gateada y puede reintentarse.",
        )

    try:
        # Re-read the task: its REAL url is the only valid value for URL artefacto.
        task_page = notion_client.get_page(task_page_id)
        real_task_url = str(task_page.get("url") or "").strip()

        raw_close, _ = _build_raw_close_properties(
            raw_schema=raw_schema,
            task_url=real_task_url,
            traceability_text=trace.text,
            today=today,
        )
        notion_client.update_page_properties(transcript_page_id, properties=raw_close)

        # ---- Phase 4: verify (blocking; re-reads only) ------------------------
        raw_reread = notion_client.get_page(transcript_page_id)
        task_reread = notion_client.get_page(task_page_id)
    except Exception as exc:  # noqa: BLE001 — partial state: task may exist but close unverified
        detail = f"{type(exc).__name__}: {str(exc)[:300]}"
        review_close_applied = _apply_technical_review_close(
            transcript_page_id,
            raw_schema,
            f"Error parcial post-escritura de tarea ({task_page_id}): {detail}",
        )
        return _result(
            ok=False,
            action="error",
            dry_run=False,
            reason="partial_execution_failure",
            transcript_page_id=transcript_page_id,
            capitalized=False,
            preflight=preflight["checks"],
            task={"page_id": task_page_id},
            technical_review_close_applied=review_close_applied,
            detail=detail,
        )

    expected_relations: list[RelationExpectation] = []
    if project_ids:
        task_project_prop = _schema_property_name(schema, ["Proyecto", "Project"], {"relation"})
        if task_project_prop:
            expected_relations.append(
                RelationExpectation(
                    page="task",
                    property_name=task_project_prop,
                    expected_ids=tuple(project_ids),
                )
            )

    expected = ExpectedCapitalization(
        task_title=task_name,
        ingest_lines_before=trace.preserved_lines,
        capitalization_mode=CAPITALIZATION_MODE,
        canonical_target_type="task",
        canonical_target_name=task_name,
        processed_at=processed_at,
        expected_relations=tuple(expected_relations),
    )
    verification = verify_task_capitalization(expected, raw_page=raw_reread, task_page=task_reread)

    if verification.ok:
        return _result(
            ok=True,
            action=dedup["action"],
            dry_run=False,
            reason="verified_by_reread",
            transcript_page_id=transcript_page_id,
            capitalized=True,
            preflight=preflight["checks"],
            dedup={"matches": dedup["matches"]},
            task={"page_id": task_page_id, "url": real_task_url, "title": task_name},
            verification=verification.as_dict(),
        )

    mismatch_summary = "; ".join(
        f"{m.field}: esperado={m.expected!r} observado={m.observed!r}" for m in verification.mismatches
    )[:1500]
    review_close_applied = _apply_technical_review_close(
        transcript_page_id,
        raw_schema,
        f"Verificación post-escritura falló: {mismatch_summary}",
    )
    return _result(
        ok=False,
        action="error",
        dry_run=False,
        reason="verification_failed",
        transcript_page_id=transcript_page_id,
        capitalized=False,
        preflight=preflight["checks"],
        task={"page_id": task_page_id, "url": real_task_url, "title": task_name},
        verification=verification.as_dict(),
        technical_review_close_applied=review_close_applied,
        detail="La relectura no confirmó el estado esperado; no se declara éxito (regla anti 'log miente').",
    )


__all__ = ["handle_granola_capitalize_task_from_raw", "CAPITALIZATION_MODE"]
