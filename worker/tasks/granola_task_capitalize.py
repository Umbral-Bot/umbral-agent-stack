"""
granola.capitalize_task_from_raw — deterministic raw -> Tarea capitalization (P1 + P1.1).

Implements the B path of the hybrid capitalization plan
(``docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md``): the Worker as
a deterministic execution engine over a raw row of ``Transcripciones Granola``
whose ``Destino canonico`` is already ``Tarea`` and whose human gate
(``Procesar con agente``) is already ticked.

Hard properties of this handler:

- **0 LLM calls.** Everything is property comparison over data already present.
- **dry_run=True by default.** A dry run performs reads only and reports the
  exact action it *would* take, the exact properties it would write, and why —
  it never claims a capitalization happened.
- **Human tasks binding only.** Writes go exclusively to
  ``config.NOTION_HUMAN_TASKS_DB_ID`` (Registro de Tareas y Proximas Acciones).
  ``NOTION_TASKS_DB_ID`` (a different, stack-operational DB) is never read here.
- **Fail closed.** Missing binding, missing raw, wrong source DB, wrong
  ``Destino canonico``, unticked gate, thin evidence, invalid Trazabilidad or
  ambiguous dedup all stop the run before any write.
- **Canonical identity by ``URL artefacto`` (P1.1).** When the raw already
  points to a canonical task via ``URL artefacto``, that identity has absolute
  priority over title dedup: planning a ``create`` is structurally impossible,
  and the update still requires ``expected_task_page_id`` matching the observed
  task (fail closed with the observed candidate otherwise). Title dedup never
  overrides an explicit identity.
- **Safe, idempotent update (P1.1).** On an existing task, human-editable
  fields (Nombre, Estado, Prioridad, Fecha objetivo, Notas, Origen, Dominio,
  relations) are NEVER overwritten by defaults. Only fields explicitly
  allowlisted via ``update_fields`` (with explicit input values) are patched,
  plus safe technical fills of empty fields (``URL fuente``). With
  ``update_fields=[]`` the update degrades to a verified no-op: the task is not
  touched and only the raw is reconciled/closed against the observed task.
- **Safe dedup (create path only).** 0 exact title matches -> create; 1 match
  -> update only with matching ``expected_task_page_id``; 2+ matches -> review.
  No semantic matching, ever.
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
import re
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import urlparse

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
    _property_nonempty,
    append_capitalization_traceability,
    verify_task_capitalization,
)
from .granola_finality import DEFAULT_MIN_STABLE_CHARS

logger = logging.getLogger("worker.tasks.granola_task_capitalize")

CAPITALIZATION_MODE = "worker_task_from_raw_v1"
_ANTI_COMGRAP_SESSION_TYPES = {"Reunión", "Llamada", "Reunion"}
_NOTION_RICH_TEXT_CHUNK = 2000
_NOTION_URL_HOST_MARKERS = ("notion.so", "notion.site", "notion.com")

# P1.1 — human-editable fields on an EXISTING task. None of these is ever
# written on an update unless the caller allowlists the field in
# ``update_fields`` AND provides an explicit input value for it. Defaults
# (e.g. Estado="Pendiente") only ever apply to a brand-new task (create path).
_UPDATE_FIELD_SPECS: Dict[str, Dict[str, Any]] = {
    "Nombre": {
        "input_keys": ("task_name",),
        "candidates": ["Nombre", "Name", "Title"],
        "types": {"title"},
    },
    "Estado": {
        "input_keys": ("estado", "status"),
        "candidates": ["Estado", "Status"],
        "types": {"select", "status", "rich_text"},
    },
    "Prioridad": {
        "input_keys": ("priority", "prioridad"),
        "candidates": ["Prioridad", "Priority"],
        "types": {"select", "status", "rich_text"},
    },
    "Fecha objetivo": {
        "input_keys": ("due_date", "target_date"),
        "candidates": ["Fecha objetivo", "Due date", "Target date"],
        "types": {"date"},
    },
    "Notas": {
        "input_keys": ("notes", "notas"),
        "candidates": ["Notas", "Notes"],
        "types": {"rich_text"},
    },
    "Origen": {
        "input_keys": ("origin", "origen"),
        "candidates": ["Origen", "Source"],
        "types": {"select", "status", "rich_text"},
    },
    "Dominio": {
        "input_keys": ("dominio", "domain"),
        "candidates": ["Dominio", "Domain"],
        "types": {"select", "status", "rich_text"},
    },
    "Proyecto": {
        "input_keys": ("project_page_id",),
        "candidates": ["Proyecto", "Project"],
        "types": {"relation"},
    },
}


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


def _hex_to_uuid(hex32: str) -> str:
    h = hex32.lower()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def _extract_page_id_from_notion_url(url: str) -> str:
    """Extract and normalize a Notion page id from a Notion URL.

    Returns "" when the URL is not a well-formed Notion page URL — the caller
    must treat that as an invalid canonical pointer, never fall through to a
    create.
    """
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        return ""
    host = (parsed.netloc or "").lower()
    if not any(marker in host for marker in _NOTION_URL_HOST_MARKERS):
        return ""
    segments = [segment for segment in (parsed.path or "").split("/") if segment]
    if not segments:
        return ""
    tail = segments[-1].replace("-", "").lower()
    match = re.search(r"([0-9a-f]{32})$", tail)
    if not match:
        return ""
    return _hex_to_uuid(match.group(1))


def _checkbox_is_true(page_data: Dict[str, Any], *names: str) -> bool:
    properties = page_data.get("properties") or {}
    for name in names:
        prop = properties.get(name)
        if isinstance(prop, dict) and prop.get("type") == "checkbox":
            return bool(prop.get("checkbox"))
    return False


def _url_property_value(page_data: Dict[str, Any], *names: str) -> str:
    properties = page_data.get("properties") or {}
    for name in names:
        prop = properties.get(name)
        if isinstance(prop, dict) and prop.get("type") == "url":
            return str(prop.get("url") or "").strip()
    return ""


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
# Phase 2a — canonical identity by URL artefacto (P1.1; reads only)
# ---------------------------------------------------------------------------


def _resolve_canonical_identity(
    *,
    page_data: Dict[str, Any],
    expected_task_page_id: str,
) -> Dict[str, Any]:
    """Resolve the canonical task identity declared by the raw's ``URL artefacto``.

    Contract (P1.1):

    - Empty ``URL artefacto`` -> ``{"source": "none"}`` (create path via dedup).
    - Non-empty ``URL artefacto`` NEVER falls through to create. It resolves to
      either an authorized ``update`` (expected_task_page_id matches the
      observed task in the human tasks DB) or a fail-closed ``review`` that
      returns the observed candidate without writing anything.
    - Titles never replace an explicit identity.
    """
    url_artefacto = _url_property_value(page_data, "URL artefacto", "URL artifact")
    if not url_artefacto:
        return {"source": "none"}

    identity: Dict[str, Any] = {"source": "url_artefacto", "url_artefacto": url_artefacto}

    extracted_id = _extract_page_id_from_notion_url(url_artefacto)
    if not extracted_id:
        return {
            **identity,
            "action": "review",
            "reason": "canonical_identity_invalid_url",
            "motivo_revision": "Bloqueo técnico",
            "detail": (
                "URL artefacto is set but is not a parseable Notion page URL. "
                "A raw with a canonical pointer can never plan a create; fix the "
                "pointer or clear it deliberately after human review."
            ),
        }
    identity["extracted_page_id"] = extracted_id

    try:
        task_page = notion_client.get_page(extracted_id)
    except Exception as exc:  # noqa: BLE001 — refusal, no write happened
        return {
            **identity,
            "action": "review",
            "reason": "canonical_identity_inaccessible",
            "motivo_revision": "Bloqueo técnico",
            "detail": (
                f"URL artefacto points to a page that could not be re-read "
                f"({type(exc).__name__}: {str(exc)[:160]}). Possible legacy residue "
                "or sharing gap — requires human review, never a create."
            ),
        }

    parent = task_page.get("parent") or {}
    parent_db = _normalize_notion_id(str(parent.get("database_id") or ""))
    if parent_db != _normalize_notion_id(config.NOTION_HUMAN_TASKS_DB_ID):
        return {
            **identity,
            "action": "review",
            "reason": "canonical_identity_wrong_database",
            "motivo_revision": "Bloqueo técnico",
            "detail": (
                "URL artefacto points outside Registro de Tareas y Proximas "
                "Acciones (possibly a legacy artifact or another surface). "
                "This flow only updates human tasks — requires human review."
            ),
        }

    observed = {
        "task_page_id": str(task_page.get("id") or extracted_id),
        "task_title": _extract_title_from_page(task_page),
        "task_url": str(task_page.get("url") or "").strip(),
    }
    identity["observed_candidate"] = observed

    expected_norm = _normalize_notion_id(expected_task_page_id)
    if not expected_norm:
        return {
            **identity,
            "action": "review",
            "reason": "canonical_identity_requires_confirmation",
            "motivo_revision": "Ambigüedad de match",
            "detail": (
                "URL artefacto identifies an existing canonical task. Updating it "
                "requires a second call with expected_task_page_id set to the "
                "observed candidate — implicit confirmation is forbidden."
            ),
        }
    if expected_norm != _normalize_notion_id(observed["task_page_id"]):
        return {
            **identity,
            "action": "review",
            "reason": "canonical_identity_mismatch",
            "motivo_revision": "Ambigüedad de match",
            "detail": (
                "expected_task_page_id does not match the task identified by "
                "URL artefacto. Resolve the contradiction by hand; nothing was written."
            ),
        }

    return {**identity, "action": "update", "task_page": task_page, **observed}


# ---------------------------------------------------------------------------
# Phase 2b — plan (reads only)
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
    """Schema-driven task properties for a BRAND-NEW task (create path only —
    defaults like Estado=Pendiente never apply to an existing task). Relations
    are only ever propagated from the raw or taken from explicit input IDs —
    never inferred."""
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


def _plan_safe_update(
    *,
    schema: Dict[str, str],
    task_page: Dict[str, Any],
    input_data: Dict[str, Any],
    update_fields: list[str],
    raw_url: str,
) -> Dict[str, Any]:
    """Plan a conservative, idempotent patch for an EXISTING task (P1.1).

    Rules:

    - Human-editable fields are written ONLY when allowlisted in
      ``update_fields`` AND an explicit input value exists. Defaults never
      overwrite; an existing Estado is never degraded implicitly.
    - Safe technical fill: ``URL fuente`` is patched only when observed empty.
    - Empty patch -> ``update_noop_verified`` (task untouched; the raw is
      reconciled/closed against the observed task).
    """
    unknown = [field for field in update_fields if field not in _UPDATE_FIELD_SPECS]
    if unknown:
        return {
            "action": "error",
            "reason": "invalid_update_fields",
            "detail": (
                f"Unknown update_fields entries: {unknown}. "
                f"Allowed: {sorted(_UPDATE_FIELD_SPECS)}."
            ),
        }

    patch: Dict[str, Any] = {}
    patch_reasons: Dict[str, str] = {}
    used_fields: list[str] = []
    explicit_new_title: str | None = None
    explicit_project_ids: list[str] = []

    for field in update_fields:
        spec = _UPDATE_FIELD_SPECS[field]
        value: Any = None
        for key in spec["input_keys"]:
            candidate = input_data.get(key)
            if candidate not in (None, "", []):
                value = candidate
                break
        if value in (None, "", []):
            return {
                "action": "error",
                "reason": "update_field_without_explicit_value",
                "detail": (
                    f"'{field}' is allowlisted in update_fields but no explicit "
                    f"input value was provided ({'/'.join(spec['input_keys'])}). "
                    "Defaults never overwrite an existing task."
                ),
            }
        prop_name = _set_schema_property(
            patch, schema, list(spec["candidates"]), value,
            expected_types=set(spec["types"]), used_fields=used_fields,
        )
        if prop_name:
            patch_reasons[prop_name] = "explicit_update_fields_allowlist"
            if field == "Nombre":
                explicit_new_title = str(value)
            if field == "Proyecto":
                explicit_project_ids = _relation_ids(value)

    # Safe technical fill: URL fuente only when observed empty on the task.
    url_prop = _schema_property_name(schema, ["URL fuente", "Source URL", "URL", "Link"], {"url", "rich_text"})
    if url_prop and url_prop not in patch and raw_url:
        if not _property_nonempty(task_page, url_prop):
            _set_schema_property(
                patch, schema, [url_prop], raw_url,
                expected_types={"url", "rich_text"}, used_fields=used_fields,
            )
            if url_prop in patch:
                patch_reasons[url_prop] = "safe_fill_empty_technical_field"

    preserved: list[str] = []
    for spec in _UPDATE_FIELD_SPECS.values():
        prop_name = _schema_property_name(schema, list(spec["candidates"]), set(spec["types"]))
        if prop_name and prop_name not in patch and _property_nonempty(task_page, prop_name):
            preserved.append(prop_name)
    if url_prop and url_prop not in patch and _property_nonempty(task_page, url_prop):
        preserved.append(url_prop)

    return {
        "action": "update_safe_patch" if patch else "update_noop_verified",
        "patch": patch,
        "patch_reasons": patch_reasons,
        "preserved_fields": sorted(set(preserved)),
        "fields_used": used_fields,
        "explicit_new_title": explicit_new_title,
        "explicit_project_ids": explicit_project_ids,
    }


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
        expected_task_page_id (str, optional): required to authorize an update —
            both when ``URL artefacto`` identifies the canonical task (P1.1) and
            when exactly one exact-title match exists (create path dedup).
        update_fields (list[str], default []): explicit allowlist of
            human-editable fields to patch on an EXISTING task. Allowed names:
            Nombre, Estado, Prioridad, Fecha objetivo, Notas, Origen, Dominio,
            Proyecto. Each allowlisted field requires its explicit input value
            (task_name / estado / priority / due_date / notes / origin /
            dominio / project_page_id). With [] the update is a verified no-op
            on the task plus a safe reconciliation of the raw.
        task_name (str, optional): task title. Create path: defaults to the raw
            title. Update path: only written when "Nombre" is allowlisted.
        estado / priority / due_date / notes / origin / dominio /
        project_page_id (optional): explicit values. On create they seed the
            new task; on update they are ignored unless allowlisted.
        min_evidence_chars (int, optional): evidence threshold override.
        processed_at (str, optional): ISO override for Trazabilidad (tests).

    Returns a structured decision with ``action`` in {create, update_noop_verified,
    update_safe_patch, review, error} and ``canonical_identity_source`` in
    {url_artefacto, title_dedup, new}. ``capitalized=True`` only ever appears on
    a non-dry-run whose post-write re-read passed verification.
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

    update_fields_raw = input_data.get("update_fields")
    if update_fields_raw is None:
        update_fields: list[str] = []
    elif isinstance(update_fields_raw, list):
        update_fields = [str(field).strip() for field in update_fields_raw if str(field).strip()]
    else:
        raise ValueError("'update_fields' must be a list of field names")

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

    # ---- Phase 2a: canonical identity (URL artefacto wins over titles) -------
    identity = _resolve_canonical_identity(
        page_data=page_data, expected_task_page_id=expected_task_page_id
    )
    schema = _load_tasks_db_schema()

    canonical_identity_source = "new"
    target_task_page: Dict[str, Any] | None = None
    target_task_page_id = ""
    dedup_report: Dict[str, Any]

    if identity["source"] == "url_artefacto":
        canonical_info = {
            "url_artefacto": identity.get("url_artefacto", ""),
            "extracted_page_id": identity.get("extracted_page_id", ""),
            "observed_candidate": identity.get("observed_candidate"),
        }
        if identity["action"] == "review":
            return _result(
                ok=False,
                action="review",
                dry_run=dry_run,
                reason=identity["reason"],
                transcript_page_id=transcript_page_id,
                preflight=preflight["checks"],
                motivo_revision=identity["motivo_revision"],
                canonical_identity_source="url_artefacto",
                canonical_identity=canonical_info,
                detail=identity.get("detail"),
                planned_raw_close=_build_review_close_plan(
                    motivo=identity["motivo_revision"],
                    reason=identity["reason"],
                    detail=identity.get("detail"),
                ),
            )
        canonical_identity_source = "url_artefacto"
        target_task_page = identity["task_page"]
        target_task_page_id = identity["task_page_id"]
        dedup_report = {
            "skipped": True,
            "reason": "canonical_identity_from_url_artefacto_has_priority_over_title_dedup",
            "target_task_page_id": target_task_page_id,
        }
    else:
        # ---- Phase 2b: title dedup (create path only) -------------------------
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
                canonical_identity_source="title_dedup",
                dedup={"matches": dedup["matches"], "detail": dedup.get("detail", "")},
                planned_raw_close=_build_review_close_plan(
                    motivo=dedup["motivo_revision"], reason=dedup["reason"], detail=dedup.get("detail", "")
                ),
            )
        if dedup["action"] == "create":
            canonical_identity_source = "new"
            dedup_report = {"matches": dedup["matches"], "target_task_page_id": ""}
        else:
            canonical_identity_source = "title_dedup"
            target_task_page_id = dedup["target_task_page_id"]
            try:
                target_task_page = notion_client.get_page(target_task_page_id)
            except Exception as exc:  # noqa: BLE001 — refusal, no write happened
                return _result(
                    ok=False,
                    action="review",
                    dry_run=dry_run,
                    reason="target_task_not_accessible",
                    transcript_page_id=transcript_page_id,
                    preflight=preflight["checks"],
                    motivo_revision="Bloqueo técnico",
                    canonical_identity_source="title_dedup",
                    detail=f"{type(exc).__name__}: {str(exc)[:200]}",
                    planned_raw_close=_build_review_close_plan(
                        motivo="Bloqueo técnico",
                        reason="target_task_not_accessible",
                        detail=str(exc)[:200],
                    ),
                )
            dedup_report = {"matches": dedup["matches"], "target_task_page_id": target_task_page_id}

    is_update = target_task_page is not None
    raw_schema = _page_schema_from_page(page_data)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    processed_at = str(input_data.get("processed_at") or "").strip() or (
        datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    source_value = _extract_select_value(page_data, "Fuente", "Source") or "granola"

    # ---- Phase 2c: build the concrete plan -----------------------------------
    if is_update:
        update_plan = _plan_safe_update(
            schema=schema,
            task_page=target_task_page,
            input_data=input_data,
            update_fields=update_fields,
            raw_url=raw_url,
        )
        if update_plan["action"] == "error":
            return _result(
                ok=False,
                action="error",
                dry_run=dry_run,
                reason=update_plan["reason"],
                transcript_page_id=transcript_page_id,
                preflight=preflight["checks"],
                canonical_identity_source=canonical_identity_source,
                detail=update_plan["detail"],
            )
        action_label = update_plan["action"]
        task_patch: Dict[str, Any] = update_plan["patch"]
        observed_task_title = _extract_title_from_page(target_task_page) or task_name
        expected_task_title = update_plan["explicit_new_title"] or observed_task_title
        canonical_target_name = expected_task_title
        task_properties: Dict[str, Any] = task_patch
        task_fields_used: list[str] = update_plan["fields_used"]
        expected_project_ids: list[str] = update_plan["explicit_project_ids"]
        update_plan_report = {
            "preserved_fields": update_plan["preserved_fields"],
            "patch_fields": sorted(task_patch.keys()),
            "patch_reasons": update_plan["patch_reasons"],
        }
        canonical_identity_report = {
            "task_page_id": target_task_page_id,
            "task_title": observed_task_title,
            "task_url": str(target_task_page.get("url") or "").strip(),
        }
    else:
        action_label = "create"
        task_properties, task_fields_used, expected_project_ids = _build_task_properties(
            schema=schema,
            page_data=page_data,
            input_data=input_data,
            task_name=task_name,
            raw_url=raw_url,
            raw_title=raw_title,
            raw_date=raw_date,
        )
        expected_task_title = task_name
        canonical_target_name = task_name
        update_plan_report = None
        canonical_identity_report = None

    trace = append_capitalization_traceability(
        preflight["existing_traceability"],
        source=source_value,
        capitalization_mode=CAPITALIZATION_MODE,
        canonical_target_type="task",
        canonical_target_name=canonical_target_name,
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
            canonical_identity_source=canonical_identity_source,
            detail=trace.error.as_dict() if trace.error else {},
            planned_raw_close=_build_review_close_plan(
                motivo="Bloqueo técnico",
                reason="traceability_append_rejected",
                detail=trace.error.as_dict() if trace.error else {},
            ),
        )

    if dry_run:
        planned_close, _ = _build_raw_close_properties(
            raw_schema=raw_schema,
            task_url="<url real de la tarea tras relectura>",
            traceability_text=trace.text,
            today=today,
        )
        return _result(
            ok=True,
            action=action_label,
            dry_run=True,
            reason="dry_run_plan_only",
            transcript_page_id=transcript_page_id,
            capitalized=False,
            preflight=preflight["checks"],
            canonical_identity_source=canonical_identity_source,
            canonical_identity=canonical_identity_report,
            dedup=dedup_report,
            task_name=expected_task_title,
            update_plan=update_plan_report,
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
        if action_label == "create":
            write_result = notion_client.create_database_page(
                config.NOTION_HUMAN_TASKS_DB_ID, properties=task_properties
            )
            task_page_id = str(write_result.get("page_id") or "")
        elif task_properties:  # update_safe_patch
            task_page_id = target_task_page_id
            notion_client.update_page_properties(task_page_id, properties=task_properties)
        else:  # update_noop_verified — the task is deliberately untouched
            task_page_id = target_task_page_id
    except Exception as exc:  # noqa: BLE001 — task write failed; raw untouched
        return _result(
            ok=False,
            action="error",
            dry_run=False,
            reason="task_write_failed",
            transcript_page_id=transcript_page_id,
            preflight=preflight["checks"],
            canonical_identity_source=canonical_identity_source,
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
            canonical_identity_source=canonical_identity_source,
            task={"page_id": task_page_id},
            technical_review_close_applied=review_close_applied,
            detail=detail,
        )

    expected_relations: list[RelationExpectation] = []
    if expected_project_ids:
        task_project_prop = _schema_property_name(schema, ["Proyecto", "Project"], {"relation"})
        if task_project_prop:
            expected_relations.append(
                RelationExpectation(
                    page="task",
                    property_name=task_project_prop,
                    expected_ids=tuple(expected_project_ids),
                )
            )

    expected = ExpectedCapitalization(
        task_title=expected_task_title,
        ingest_lines_before=trace.preserved_lines,
        capitalization_mode=CAPITALIZATION_MODE,
        canonical_target_type="task",
        canonical_target_name=canonical_target_name,
        processed_at=processed_at,
        expected_relations=tuple(expected_relations),
    )
    verification = verify_task_capitalization(expected, raw_page=raw_reread, task_page=task_reread)

    if verification.ok:
        return _result(
            ok=True,
            action=action_label,
            dry_run=False,
            reason="verified_by_reread",
            transcript_page_id=transcript_page_id,
            capitalized=True,
            preflight=preflight["checks"],
            canonical_identity_source=canonical_identity_source,
            canonical_identity=canonical_identity_report,
            dedup=dedup_report,
            update_plan=update_plan_report,
            task={"page_id": task_page_id, "url": real_task_url, "title": expected_task_title},
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
        canonical_identity_source=canonical_identity_source,
        task={"page_id": task_page_id, "url": real_task_url, "title": expected_task_title},
        verification=verification.as_dict(),
        technical_review_close_applied=review_close_applied,
        detail="La relectura no confirmó el estado esperado; no se declara éxito (regla anti 'log miente').",
    )


__all__ = ["handle_granola_capitalize_task_from_raw", "CAPITALIZATION_MODE"]
