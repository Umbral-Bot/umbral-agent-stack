"""
Granola raw -> Tarea capitalization: deterministic Trazabilidad + verify helpers (P0).

These helpers are pure utilities used by a future ``granola.capitalize_task_from_raw``
task (P1, not implemented here). They never call Notion and never use an LLM —
everything is string/dict comparison over data the caller already fetched.

Scope (see ``docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md``, P0):

- ``append_capitalization_traceability``: build the next ``Trazabilidad`` text for
  a raw page, preserving every pre-existing ingest line byte-for-byte and in
  order, and reconciling (not duplicating) the capitalization block on retries.
- ``verify_task_capitalization``: compare an *expected* capitalization outcome
  against real re-reads of the raw page and the task page. Never declares
  success from what a write call claims to have done — only from what a
  subsequent read shows.

Both are deliberately dumb: they do not decide *whether* to capitalize, they do
not classify, and they never invent a ``canonical_target_url`` — the V2.1.1
prompt amendment (``notion-governance/prompts/agents/review-capitalizacion-v2.1.md``)
prohibits any URL inside ``Trazabilidad``; the canonical URL lives only in the
raw's ``URL artefacto`` property.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

# Documented order of the Drive-ingest Trazabilidad block (V2.1.1 Enmienda,
# `granola_drive_md_ingest.py`). This module does not enforce this exact list
# as a closed whitelist for "preserved" lines — ANY line whose key is not one
# of CAPITALIZATION_TRACEABILITY_KEYS is treated as foreign/ingest content and
# preserved untouched. This keeps the helper robust to the other ingest
# pipeline (`granola.process_transcript` / `_build_raw_traceability_text`),
# which uses a different key set (granola_document_id, source_updated_at,
# source_url, export_signature, reconciled_at, ...). The tuple below exists
# for documentation and for the compacted-line heuristic below.
INGEST_TRACEABILITY_KEYS: tuple[str, ...] = (
    "shared_folder_path",
    "sha1",
    "ingest_path",
    "content_hash",
    "char_count",
    "segment_count",
    "ingested_at",
    "truncation_detected",
    "truncation_reason",
)

# The only keys this module ever writes. `canonical_target_url` is
# deliberately absent — see module docstring.
CAPITALIZATION_TRACEABILITY_KEYS: tuple[str, ...] = (
    "source",
    "capitalization_mode",
    "canonical_target_type",
    "canonical_target_name",
    "processed_at",
)

# Error codes returned by append_capitalization_traceability.
ERR_INVALID_FORMAT = "invalid_format"
ERR_COMPACTED_LINE = "compacted_line"
ERR_LEGACY_AMBIGUOUS_CONTENT = "legacy_ambiguous_content"
ERR_DUPLICATE_KEY = "duplicate_key"
ERR_FORBIDDEN_NEW_VALUE = "forbidden_new_value"

_LINE_KEY_RE = re.compile(r"^([A-Za-z0-9_]+)=(.*)$")
_MARKDOWN_LINE_PREFIXES = ("#", "- ", "* ", "> ", "```", "|")
# Substrings that must never appear inside a Trazabilidad value: Notion mention
# placeholders, raw URLs, and markdown link syntax all break the strict
# `clave=valor` contract (V2.1.1 prompt, "PROHIBICIÓN ABSOLUTA — canonical_target_url").
_FORBIDDEN_VALUE_MARKERS = ("<mention-page", "http://", "https://", "](", "<http")

_ALL_KNOWN_KEYS_FOR_COMPACT_DETECTION: tuple[str, ...] = tuple(
    sorted(
        set(INGEST_TRACEABILITY_KEYS) | set(CAPITALIZATION_TRACEABILITY_KEYS),
        key=len,
        reverse=True,
    )
)


def _line_has_markdown_prefix(line: str) -> bool:
    return line.lstrip().startswith(_MARKDOWN_LINE_PREFIXES)


def _value_has_forbidden_markers(value: str) -> bool:
    lowered = (value or "").lower()
    return any(marker in lowered for marker in _FORBIDDEN_VALUE_MARKERS)


def _line_looks_compacted(value: str) -> str | None:
    """Return the embedded key name if ``value`` looks like it swallowed a
    second ``key=value`` pair (e.g. ``"x capitalization_mode=y"``)."""
    for key in _ALL_KNOWN_KEYS_FOR_COMPACT_DETECTION:
        if re.search(rf"(?:^|\s){re.escape(key)}=", value):
            return key
    return None


# ---------------------------------------------------------------------------
# Line parsing (shared by append + verify)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ParsedLine:
    raw: str
    key: str
    value: str


@dataclass(frozen=True)
class TraceabilityError:
    code: str
    message: str
    line: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "line": self.line}


def _parse_traceability_lines(
    text: str,
) -> tuple[list[_ParsedLine], TraceabilityError | None]:
    """Strictly parse a Trazabilidad block into ordered ``clave=valor`` lines.

    Returns ``([], error)`` on the first structural problem found — this
    module never partially repairs ambiguous legacy content; the caller must
    route the row to human review instead.
    """
    parsed: list[_ParsedLine] = []
    seen_keys: set[str] = set()
    for raw_line in (text or "").splitlines():
        if not raw_line.strip():
            continue
        if _line_has_markdown_prefix(raw_line):
            return [], TraceabilityError(
                code=ERR_INVALID_FORMAT,
                message="Line looks like markdown/legacy narrative content, not clave=valor.",
                line=raw_line,
            )
        match = _LINE_KEY_RE.match(raw_line)
        if not match:
            return [], TraceabilityError(
                code=ERR_INVALID_FORMAT,
                message="Line does not match the strict clave=valor format.",
                line=raw_line,
            )
        key, value = match.group(1), match.group(2)
        if _value_has_forbidden_markers(value):
            return [], TraceabilityError(
                code=ERR_LEGACY_AMBIGUOUS_CONTENT,
                message=(
                    "Value contains a URL, Notion mention, or markdown link — "
                    "not allowed in Trazabilidad (canonical_target_url lives only "
                    "in 'URL artefacto')."
                ),
                line=raw_line,
            )
        compacted_key = _line_looks_compacted(value)
        if compacted_key:
            return [], TraceabilityError(
                code=ERR_COMPACTED_LINE,
                message=(
                    f"Line appears to compact multiple keys onto one line "
                    f"(found embedded key '{compacted_key}=')."
                ),
                line=raw_line,
            )
        if key in seen_keys:
            return [], TraceabilityError(
                code=ERR_DUPLICATE_KEY,
                message=f"Key '{key}' appears more than once in existing Trazabilidad.",
                line=raw_line,
            )
        seen_keys.add(key)
        parsed.append(_ParsedLine(raw=raw_line, key=key, value=value))
    return parsed, None


# ---------------------------------------------------------------------------
# append_capitalization_traceability
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceabilityResult:
    ok: bool
    text: str | None
    preserved_lines: tuple[str, ...] = ()
    appended_keys: tuple[str, ...] = ()
    updated_keys: tuple[str, ...] = ()
    error: TraceabilityError | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "text": self.text,
            "preserved_lines": list(self.preserved_lines),
            "appended_keys": list(self.appended_keys),
            "updated_keys": list(self.updated_keys),
            "error": self.error.as_dict() if self.error else None,
        }


def append_capitalization_traceability(
    existing_text: str | None,
    *,
    source: str,
    capitalization_mode: str,
    canonical_target_type: str,
    canonical_target_name: str,
    processed_at: str,
) -> TraceabilityResult:
    """Build the next Trazabilidad text for a raw page.

    Preserves every pre-existing non-capitalization line exactly, in its
    original order (this covers both the Drive-ingest key set and the
    ``process_transcript`` key set — anything that isn't one of
    ``CAPITALIZATION_TRACEABILITY_KEYS`` is foreign/ingest content and is
    never touched). Reconciles the capitalization block idempotently: on a
    retry, existing capitalization keys are updated in place (same line
    position) instead of being duplicated at the end.

    Never mutates ``existing_text`` (strings are immutable in Python; no
    other mutable input is accepted). Never accepts or emits
    ``canonical_target_url`` — the 5 keys this function writes are exactly
    ``CAPITALIZATION_TRACEABILITY_KEYS``.

    Returns ``TraceabilityResult(ok=False, ...)`` — with no text written —
    when the existing block is malformed (legacy narrative text, markdown,
    Notion mentions, HTML, compacted lines, or duplicate keys). The caller
    must treat that as "requires human review", not as something to silently
    repair.
    """
    new_values = {
        "source": source or "",
        "capitalization_mode": capitalization_mode or "",
        "canonical_target_type": canonical_target_type or "",
        "canonical_target_name": canonical_target_name or "",
        "processed_at": processed_at or "",
    }
    for key, value in new_values.items():
        if _value_has_forbidden_markers(value):
            return TraceabilityResult(
                ok=False,
                text=None,
                error=TraceabilityError(
                    code=ERR_FORBIDDEN_NEW_VALUE,
                    message=(
                        f"New value for '{key}' contains a URL/mention/markdown-link. "
                        "canonical_target_url does not belong in Trazabilidad — only "
                        "'URL artefacto' carries the URL."
                    ),
                    line=f"{key}={value}",
                ),
            )

    parsed_lines, parse_error = _parse_traceability_lines(existing_text or "")
    if parse_error is not None:
        return TraceabilityResult(ok=False, text=None, error=parse_error)

    preserved = tuple(
        p.raw for p in parsed_lines if p.key not in CAPITALIZATION_TRACEABILITY_KEYS
    )

    final_lines: list[str] = []
    appended_keys: list[str] = []
    updated_keys: list[str] = []
    seen_capitalization_keys: set[str] = set()

    for p in parsed_lines:
        if p.key in CAPITALIZATION_TRACEABILITY_KEYS:
            new_value = new_values[p.key]
            final_lines.append(f"{p.key}={new_value}")
            seen_capitalization_keys.add(p.key)
            if new_value != p.value:
                updated_keys.append(p.key)
        else:
            final_lines.append(p.raw)

    for key in CAPITALIZATION_TRACEABILITY_KEYS:
        if key not in seen_capitalization_keys:
            final_lines.append(f"{key}={new_values[key]}")
            appended_keys.append(key)

    return TraceabilityResult(
        ok=True,
        text="\n".join(final_lines),
        preserved_lines=preserved,
        appended_keys=tuple(appended_keys),
        updated_keys=tuple(updated_keys),
    )


# ---------------------------------------------------------------------------
# verify_task_capitalization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelationExpectation:
    """One relation the caller claims to have written, to be checked against
    a real re-read. ``page`` is ``"raw"`` or ``"task"``."""

    page: str
    property_name: str
    expected_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExpectedCapitalization:
    """What a ``granola.capitalize_task_from_raw`` call (P1) intended to leave
    behind. Supplied entirely by the caller — this module never invents
    intent, it only checks whether re-read reality matches it."""

    task_title: str
    destino_canonico: str = "Tarea"
    estado: str = "Procesada"
    estado_agente: str = "Procesada"
    accion_agente: str = "Capitalizado"
    procesar_con_agente: bool = False
    required_v2_fields: tuple[str, ...] = (
        "Dominio propuesto",
        "Tipo propuesto",
        "Resumen agente",
    )
    ingest_lines_before: tuple[str, ...] = ()
    capitalization_mode: str = ""
    canonical_target_type: str = "Tarea"
    canonical_target_name: str = ""
    processed_at: str | None = None
    expected_relations: tuple[RelationExpectation, ...] = ()


@dataclass(frozen=True)
class Mismatch:
    field: str
    expected: Any
    observed: Any
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "expected": self.expected,
            "observed": self.observed,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    mismatches: tuple[Mismatch, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "mismatches": [m.as_dict() for m in self.mismatches]}


def _prop(page: dict[str, Any], *names: str) -> dict[str, Any] | None:
    properties = page.get("properties") or {}
    for name in names:
        candidate = properties.get(name)
        if isinstance(candidate, dict):
            return candidate
    return None


def _select_text(page: dict[str, Any], *names: str) -> str:
    prop = _prop(page, *names)
    if not prop:
        return ""
    ptype = prop.get("type")
    if ptype == "select":
        return ((prop.get("select") or {}).get("name") or "").strip()
    if ptype == "status":
        return ((prop.get("status") or {}).get("name") or "").strip()
    return ""


def _rich_text_value(page: dict[str, Any], *names: str) -> str:
    prop = _prop(page, *names)
    if not prop or prop.get("type") != "rich_text":
        return ""
    parts: list[str] = []
    for item in prop.get("rich_text") or []:
        if isinstance(item, dict):
            parts.append(item.get("plain_text") or (item.get("text") or {}).get("content", ""))
    return "".join(parts)


def _title_value(page: dict[str, Any]) -> str:
    properties = page.get("properties") or {}
    for prop in properties.values():
        if isinstance(prop, dict) and prop.get("type") == "title":
            parts: list[str] = []
            for item in prop.get("title") or []:
                if isinstance(item, dict):
                    parts.append(item.get("plain_text") or (item.get("text") or {}).get("content", ""))
            return "".join(parts).strip()
    return ""


def _checkbox_value(page: dict[str, Any], *names: str) -> bool | None:
    prop = _prop(page, *names)
    if not prop or prop.get("type") != "checkbox":
        return None
    return bool(prop.get("checkbox"))


def _url_value(page: dict[str, Any], *names: str) -> str:
    prop = _prop(page, *names)
    if not prop or prop.get("type") != "url":
        return ""
    return str(prop.get("url") or "").strip()


def _relation_id_tuple(page: dict[str, Any], name: str) -> tuple[str, ...] | None:
    prop = _prop(page, name)
    if not prop or prop.get("type") != "relation":
        return None
    ids: list[str] = []
    for item in prop.get("relation") or []:
        if isinstance(item, dict):
            item_id = str(item.get("id") or "").strip()
            if item_id:
                ids.append(item_id)
    return tuple(ids)


def _property_nonempty(page: dict[str, Any], name: str) -> bool:
    prop = _prop(page, name)
    if not prop:
        return False
    ptype = prop.get("type")
    if ptype == "select":
        return bool((prop.get("select") or {}).get("name"))
    if ptype == "status":
        return bool((prop.get("status") or {}).get("name"))
    if ptype == "rich_text":
        return bool(_rich_text_value(page, name).strip())
    if ptype == "title":
        return bool(_title_value(page))
    if ptype == "url":
        return bool(prop.get("url"))
    if ptype == "date":
        return bool((prop.get("date") or {}).get("start"))
    if ptype == "checkbox":
        return True
    return False


def verify_task_capitalization(
    expected: ExpectedCapitalization,
    *,
    raw_page: dict[str, Any] | None,
    task_page: dict[str, Any] | None,
) -> VerificationResult:
    """Compare an expected capitalization outcome against real re-reads.

    ``raw_page`` and ``task_page`` must be the raw Notion page objects
    (``notion_client.get_page()`` shape: ``{"id", "url", "properties": {...}}``)
    obtained AFTER the write. This function makes no Notion calls itself and
    never declares success from what a write response claimed — only from
    what these re-reads actually show.

    Returns ``ok=True`` only when every check below passes; otherwise returns
    every mismatch found (not just the first one), so the caller can decide
    between a targeted repair-and-reread and a hard Error/Revisión requerida.
    """
    mismatches: list[Mismatch] = []

    if raw_page is None:
        mismatches.append(Mismatch("raw_page", "accessible", "missing", "Raw page re-read returned nothing."))
    if task_page is None:
        mismatches.append(Mismatch("task_page", "accessible", "missing", "Task page re-read returned nothing."))

    if task_page is not None:
        observed_title = _title_value(task_page)
        if observed_title != expected.task_title:
            mismatches.append(
                Mismatch("task_title", expected.task_title, observed_title)
            )

    if raw_page is not None:
        observed_destino = _select_text(raw_page, "Destino canonico", "Destino canónico")
        if observed_destino != expected.destino_canonico:
            mismatches.append(
                Mismatch("Destino canonico", expected.destino_canonico, observed_destino)
            )

        observed_estado = _select_text(raw_page, "Estado")
        if observed_estado != expected.estado:
            mismatches.append(Mismatch("Estado", expected.estado, observed_estado))

        observed_estado_agente = _select_text(raw_page, "Estado agente")
        if observed_estado_agente != expected.estado_agente:
            mismatches.append(
                Mismatch("Estado agente", expected.estado_agente, observed_estado_agente)
            )

        observed_accion_agente = _select_text(raw_page, "Accion agente", "Acción agente")
        if observed_accion_agente != expected.accion_agente:
            mismatches.append(
                Mismatch("Accion agente", expected.accion_agente, observed_accion_agente)
            )

        observed_procesar = _checkbox_value(raw_page, "Procesar con agente")
        if observed_procesar is None or observed_procesar != expected.procesar_con_agente:
            mismatches.append(
                Mismatch("Procesar con agente", expected.procesar_con_agente, observed_procesar)
            )

        for field_name in expected.required_v2_fields:
            if not _property_nonempty(raw_page, field_name):
                mismatches.append(
                    Mismatch(field_name, "non_empty", "empty_or_missing", "Required V2 field not present.")
                )

        # URL artefacto must point to the task's real (re-read) URL — not to
        # whatever the write call claimed.
        observed_url_artefacto = _url_value(raw_page, "URL artefacto", "URL artifact")
        real_task_url = (task_page or {}).get("url", "") if task_page is not None else ""
        if task_page is not None and observed_url_artefacto != real_task_url:
            mismatches.append(
                Mismatch("URL artefacto", real_task_url, observed_url_artefacto)
            )

        # Trazabilidad: re-parse and check ingest preservation + capitalization block.
        trazabilidad_text = _rich_text_value(raw_page, "Trazabilidad", "Traceability")
        parsed_lines, parse_error = _parse_traceability_lines(trazabilidad_text)
        if parse_error is not None:
            mismatches.append(
                Mismatch(
                    "Trazabilidad_format",
                    "clave=valor limpio",
                    parse_error.code,
                    parse_error.message,
                )
            )
        else:
            observed_ingest_lines = tuple(
                p.raw for p in parsed_lines if p.key not in CAPITALIZATION_TRACEABILITY_KEYS
            )
            if expected.ingest_lines_before and observed_ingest_lines != expected.ingest_lines_before:
                missing = [
                    line for line in expected.ingest_lines_before if line not in observed_ingest_lines
                ]
                if missing:
                    mismatches.append(
                        Mismatch(
                            "Trazabilidad_ingest_lines",
                            list(expected.ingest_lines_before),
                            list(observed_ingest_lines),
                            f"Missing or altered ingest line(s): {missing}",
                        )
                    )
                else:
                    mismatches.append(
                        Mismatch(
                            "Trazabilidad_ingest_lines_order",
                            list(expected.ingest_lines_before),
                            list(observed_ingest_lines),
                            "Ingest lines present but reordered.",
                        )
                    )

            observed_cap = {p.key: p.value for p in parsed_lines if p.key in CAPITALIZATION_TRACEABILITY_KEYS}
            expected_cap = {
                "source": None,  # presence-only; the task decides the exact literal
                "capitalization_mode": expected.capitalization_mode,
                "canonical_target_type": expected.canonical_target_type,
                "canonical_target_name": expected.canonical_target_name,
                "processed_at": expected.processed_at,
            }
            for key, expected_value in expected_cap.items():
                if key not in observed_cap:
                    mismatches.append(
                        Mismatch(f"Trazabilidad.{key}", expected_value, None, "Capitalization key missing from re-read Trazabilidad.")
                    )
                elif expected_value is not None and observed_cap[key] != expected_value:
                    mismatches.append(
                        Mismatch(f"Trazabilidad.{key}", expected_value, observed_cap[key])
                    )

    for relation in expected.expected_relations:
        page_obj = raw_page if relation.page == "raw" else task_page
        if page_obj is None:
            mismatches.append(
                Mismatch(
                    f"relation:{relation.page}:{relation.property_name}",
                    list(relation.expected_ids),
                    None,
                    f"'{relation.page}' page was not accessible for relation check.",
                )
            )
            continue
        observed_ids = _relation_id_tuple(page_obj, relation.property_name)
        if observed_ids is None or set(observed_ids) != set(relation.expected_ids):
            mismatches.append(
                Mismatch(
                    f"relation:{relation.page}:{relation.property_name}",
                    list(relation.expected_ids),
                    list(observed_ids) if observed_ids is not None else None,
                )
            )

    return VerificationResult(ok=not mismatches, mismatches=tuple(mismatches))


__all__ = [
    "INGEST_TRACEABILITY_KEYS",
    "CAPITALIZATION_TRACEABILITY_KEYS",
    "ERR_INVALID_FORMAT",
    "ERR_COMPACTED_LINE",
    "ERR_LEGACY_AMBIGUOUS_CONTENT",
    "ERR_DUPLICATE_KEY",
    "ERR_FORBIDDEN_NEW_VALUE",
    "TraceabilityError",
    "TraceabilityResult",
    "append_capitalization_traceability",
    "RelationExpectation",
    "ExpectedCapitalization",
    "Mismatch",
    "VerificationResult",
    "verify_task_capitalization",
]
