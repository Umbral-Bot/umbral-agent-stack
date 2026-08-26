"""
Task: editorial.create_shortlist_alternativa — P1 writer for the
"Alternativas / Shortlist" DB (V1 registration, pre-HITL-1).

Creates one row per V1 alternativa produced by rick-editorial (see
openclaw/workspace-agent-overrides/rick-editorial/ROLE.md, "Output contract —
V1 Alternativa") in the live "Alternativas / Shortlist" DB, per:

    notion/schemas/alternativas-shortlist.schema.yaml (live schema, P1)
    docs/ops/editorial-norte-hitl-contract-2026-07-22.md §3 (V1 contract)
    docs/ops/rick-editorial-agent.md (PKG-MACRO-P5-Q12-T5 — closes the gap:
      no task previously existed to create a Shortlist row from scratch)

Contract (do not weaken):
- Writing to Notion is Worker/core's exclusive job (ADR-011 #1). rick-editorial
  itself has no umbral_worker_enqueue/umbral_worker_run grant (Phase 1,
  PKG-MACRO-P5-Q12-T4) — an authorized operator calls this task with the
  payload rick-editorial produced.
- `Resultado revisión` is always written as `Pendiente`. This task never
  accepts or writes Archivar/Observar/Descartar/Aprobar — HITL-1 is David's
  decision, made later directly in Notion, never by this task.
- Fail-closed on `fuente_pieza_url`: reuses the same
  `scripts.discovery.lib.url_classify.is_home_or_feed_url` guard as
  `editorial_promote.py`/`gates.py`/`stage7_publish_drafts.py` — a home/feed,
  empty, or non-absolute URL refuses creation outright
  (`error: fuente_pieza_url_is_home_or_feed`), never silently drops the field.
- Idempotent by `alternativa_id`: if a row with this `alternativa_id` already
  exists in the Shortlist DB, this is a no-op (`already_exists=True`,
  existing `shortlist_page_id`) — never a duplicate.
- `dry_run` validates every guard and returns the properties that would be
  written, without calling Notion to query or create anything.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from scripts.discovery.lib.url_classify import is_home_or_feed_url

from .. import config, notion_client
from ..notion_client import _extract_notion_page_id
from .editorial_promote import _rt

logger = logging.getLogger("worker.tasks.editorial_create_shortlist")

_REQUIRED_FIELDS = (
    "alternativa_id",
    "titulo",
    "arco_narrativo",
    "estructura_discurso",
    "fuente_pieza_url",
)

# Mirrors the live select options on the Shortlist DB (verified 2026-08-25,
# notion/schemas/alternativas-shortlist.schema.yaml). Fail-fast defense so a
# bad value is caught by dry_run too, before the Notion API round-trip — not
# a generated source of truth. If David adds/renames an option in Notion,
# update both this set and the schema file to match.
_FUENTE_TIPO_VALUES = {
    "primary_source",
    "original_article",
    "official_doc",
    "analysis_source",
    "discovery_source",
    "contextual_reference",
}
_CANAL_VALUES = {"blog", "linkedin", "x", "newsletter"}


def _build_shortlist_properties(input_data: Dict[str, Any]) -> Dict[str, Any]:
    props: Dict[str, Any] = {
        "Título": {"title": _rt(input_data["titulo"], 300)},
        "alternativa_id": {"rich_text": _rt(input_data["alternativa_id"], 200)},
        "arco_narrativo": {"rich_text": _rt(input_data["arco_narrativo"], 2000)},
        "estructura_discurso": {"rich_text": _rt(input_data["estructura_discurso"], 2000)},
        "fuente_pieza_url": {"url": input_data["fuente_pieza_url"]},
        "Resultado revisión": {"select": {"name": "Pendiente"}},
    }
    if input_data.get("topic_key"):
        props["topic_key"] = {"rich_text": _rt(input_data["topic_key"], 200)}
    if input_data.get("premisa"):
        props["premisa"] = {"rich_text": _rt(input_data["premisa"], 500)}
    if input_data.get("fuente_tipo"):
        props["fuente_tipo"] = {"select": {"name": input_data["fuente_tipo"]}}
    if input_data.get("fuente_discovery_url"):
        props["fuente_discovery_url"] = {"url": input_data["fuente_discovery_url"]}
    if input_data.get("canal_sugerido"):
        props["canal_sugerido"] = {"select": {"name": input_data["canal_sugerido"]}}
    if input_data.get("score_alineacion") is not None:
        props["score_alineacion"] = {"number": input_data["score_alineacion"]}
    return props


def handle_editorial_create_shortlist_alternativa(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create one V1 alternativa row in the Shortlist DB (Resultado revisión =
    Pendiente, never anything else).

    Input:
        alternativa_id, titulo, arco_narrativo, estructura_discurso,
        fuente_pieza_url (str, required).
        topic_key, premisa, fuente_tipo, fuente_discovery_url,
        canal_sugerido (str, optional), score_alineacion (number, optional).
        dry_run (bool, optional): validate every guard and return
            properties_preview without calling Notion.

    Returns:
        {"ok": bool, "created": bool, "already_exists": bool,
         "shortlist_page_id": str|None, "shortlist_url": str|None,
         "alternativa_id": str, "error": str|None}
    """
    missing = [f for f in _REQUIRED_FIELDS if not str(input_data.get(f) or "").strip()]
    if missing:
        return {"ok": False, "error": f"missing required field(s): {', '.join(missing)}"}

    ds_id = config.NOTION_SHORTLIST_DS_ID
    if not ds_id:
        return {"ok": False, "error": "NOTION_SHORTLIST_DS_ID not configured on server"}

    try:
        # Normalize once so both the query and the create call agree on the
        # same id, whether NOTION_SHORTLIST_DS_ID holds a bare id or the full
        # page URL (query_database, unlike create_database_page, does not
        # normalize database_id itself).
        ds_id = _extract_notion_page_id(ds_id)
    except ValueError as e:
        return {"ok": False, "error": f"Invalid NOTION_SHORTLIST_DS_ID: {e}"}

    alternativa_id = input_data["alternativa_id"].strip()
    fuente_pieza_url = input_data["fuente_pieza_url"].strip()
    # Property-building must use the same normalized values as the guard and
    # the idempotency lookup below, not the raw input — otherwise incidental
    # whitespace would be stored verbatim while every later dedup check
    # strips first, breaking idempotency for that row.
    input_data = {**input_data, "alternativa_id": alternativa_id, "fuente_pieza_url": fuente_pieza_url}

    if is_home_or_feed_url(fuente_pieza_url):
        return {
            "ok": False,
            "error": "fuente_pieza_url_is_home_or_feed",
            "fuente_pieza_url": fuente_pieza_url,
            "alternativa_id": alternativa_id,
        }

    fuente_tipo = input_data.get("fuente_tipo")
    if fuente_tipo and fuente_tipo not in _FUENTE_TIPO_VALUES:
        return {
            "ok": False,
            "error": f"invalid fuente_tipo: {fuente_tipo}",
            "alternativa_id": alternativa_id,
        }

    canal_sugerido = input_data.get("canal_sugerido")
    if canal_sugerido and canal_sugerido not in _CANAL_VALUES:
        return {
            "ok": False,
            "error": f"invalid canal_sugerido: {canal_sugerido}",
            "alternativa_id": alternativa_id,
        }

    dry_run = bool(input_data.get("dry_run", False))
    props = _build_shortlist_properties(input_data)

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_create": True,
            "created": False,
            "already_exists": False,
            "properties_preview": props,
            "alternativa_id": alternativa_id,
        }

    try:
        existing = notion_client.query_database(
            database_id=ds_id,
            filter={"property": "alternativa_id", "rich_text": {"equals": alternativa_id}},
        )
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to query Shortlist DB: {e}",
            "alternativa_id": alternativa_id,
        }

    if existing:
        page_id = existing[0]["id"]
        return {
            "ok": True,
            "created": False,
            "already_exists": True,
            "shortlist_page_id": page_id,
            "shortlist_url": existing[0].get("url", ""),
            "alternativa_id": alternativa_id,
        }

    try:
        result = notion_client.create_database_page(
            database_id_or_url=ds_id,
            properties=props,
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "alternativa_id": alternativa_id}

    logger.info(
        "Created shortlist alternativa %s -> page %s",
        alternativa_id,
        result["page_id"][:8],
    )
    return {
        "ok": True,
        "created": True,
        "already_exists": False,
        "shortlist_page_id": result["page_id"],
        "shortlist_url": result.get("url", ""),
        "alternativa_id": alternativa_id,
    }
