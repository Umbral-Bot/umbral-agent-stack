"""
Task: editorial.dedupe_candidate_vs_backlog — P2.4 poller/handler.

Consults the Publicaciones backlog (rows in `Borrador` and `Publicado`) for a
Shortlist ("Alternativas / Shortlist") row and marks its `dedupe_status`
(+ `publicacion_relacionada` if a match is found), per:

    docs/ops/editorial-norte-hitl-contract-2026-07-22.md §5.J (dedupe de
      candidato), §6 (Shortlist schema: topic_key / dedupe_status /
      publicacion_relacionada)
    docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md P2.4
    notion/schemas/alternativas-shortlist.schema.yaml (source fields)
    notion/schemas/publicaciones.schema.yaml (backlog fields queried)

This is deliberately **separate** from the idempotency of *publish*
(`content_hash` / `idempotency_key` on Publicaciones, guarded in
worker/tasks/editorial_publish.py and scripts/discovery/lib/dedup.py's SQLite
`published_history`). Publish idempotency asks "have we already published
this exact rendered content?"; this task asks "has anyone already
curated/drafted/published *this topic or source* before?" — a pre-registration
check on the Notion side, not a post-render hash check.

Contract (do not weaken):
- Writing to Notion is Worker/core's exclusive job (ADR-011 #1) — the
  dispatcher poller only decides *which* Shortlist rows still need a dedupe
  verdict; it never writes to Notion itself.
- Fail-closed: this handler re-fetches the Shortlist page itself and computes
  the verdict from a live backlog query — it never trusts a caller-supplied
  snapshot.
- Idempotent: once a Shortlist row already has a non-empty `dedupe_status`,
  this is a no-op (`already_evaluated=True`) — the check runs once per
  candidate, before it enters HITL-1 review, not on every scan cycle.
- Read-then-preview, like editorial_promote.py: `dry_run=True` still performs
  the Publicaciones backlog query (a read, no side effects) so the preview is
  meaningful (an accurate `nuevo`/`duplicado_*` verdict), and only skips the
  final `update_page_properties` write to the Shortlist row. This differs from
  a fully offline dry-run because the backlog query IS the computation this
  task exists to do; skipping it would make the preview vacuous.
- Never touches gates, never promotes, never generates copy or images, never
  autopublishes — this task only ever writes `dedupe_status` /
  `publicacion_relacionada` on a Shortlist page.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from .. import config, notion_client

_BACKLOG_STATES = ("Borrador", "Publicado")
_DEDUPE_FILTER = {
    "or": [{"property": "Estado", "status": {"equals": name}} for name in _BACKLOG_STATES]
}


def _flatten_prop(prop: Any) -> Any:
    """Flatten a single raw Notion property value (as returned by get_page)."""
    if not isinstance(prop, dict):
        return None
    ptype = prop.get("type")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if ptype == "url":
        return prop.get("url")
    if ptype == "select":
        return (prop.get("select") or {}).get("name")
    if ptype == "status":
        return (prop.get("status") or {}).get("name")
    if ptype == "checkbox":
        return bool(prop.get("checkbox"))
    if ptype == "relation":
        return [item.get("id", "") for item in prop.get("relation", [])]
    return None


def normalize_topic_key(text: Optional[str]) -> str:
    """Normalize free text into a comparable topic key.

    Casefolds, strips accents/diacritics, drops punctuation, and collapses
    whitespace, so "Gobernanza en BIM" and "gobernanza  en bim." normalize to
    the same key. Deliberately simple (no stemming/synonyms) — a documented v1
    limitation, not a bug: see docs/ops/editorial-candidate-dedupe-2026-07-23.md.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = stripped_accents.casefold()
    collapsed = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(collapsed.split())


def _read_shortlist_fields(page: Dict[str, Any]) -> Dict[str, Any]:
    props = page.get("properties") or {}

    def get(name: str) -> Any:
        return _flatten_prop(props.get(name))

    return {
        "titulo": get("Título"),
        "topic_key": get("topic_key"),
        "fuente_pieza_url": get("fuente_pieza_url"),
        "dedupe_status": get("dedupe_status"),
        "publicacion_relacionada": get("publicacion_relacionada") or [],
    }


def _read_backlog_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    props = row.get("properties") or {}

    def get(name: str) -> Any:
        return _flatten_prop(props.get(name))

    return {
        "id": row.get("id", ""),
        "url": row.get("url", ""),
        "estado": get("Estado"),
        "titulo": get("Título"),
        "fuente_primaria": get("Fuente primaria"),
    }


def find_backlog_match(
    candidate: Dict[str, Any], backlog_rows: List[Dict[str, Any]]
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Compare a Shortlist candidate against the Publicaciones backlog.

    Two independent match signals, either sufficient on its own:
    - Exact source URL match (`fuente_pieza_url` == `Fuente primaria`) — the
      same concrete piece was already curated.
    - Normalized topic match (`topic_key`, falling back to `Título` when
      `topic_key` is unset) — the same theme was already covered.

    A `Publicado` match outranks a `Borrador` match (more severe duplicate) —
    matching either state at all beats no match (`nuevo`).
    """
    candidate_url = (candidate.get("fuente_pieza_url") or "").strip()
    candidate_topic = normalize_topic_key(candidate.get("topic_key") or candidate.get("titulo"))

    matched_publicado: Optional[Dict[str, Any]] = None
    matched_borrador: Optional[Dict[str, Any]] = None

    for raw_row in backlog_rows:
        row = _read_backlog_fields(raw_row)
        row_url = (row.get("fuente_primaria") or "").strip()
        row_topic = normalize_topic_key(row.get("titulo"))

        is_match = bool(candidate_url and row_url and candidate_url == row_url)
        if not is_match:
            is_match = bool(candidate_topic and row_topic and candidate_topic == row_topic)
        if not is_match:
            continue

        if row.get("estado") == "Publicado" and matched_publicado is None:
            matched_publicado = row
        elif row.get("estado") == "Borrador" and matched_borrador is None:
            matched_borrador = row

    if matched_publicado is not None:
        return "duplicado_publicado", matched_publicado
    if matched_borrador is not None:
        return "duplicado_borrador", matched_borrador
    return "nuevo", None


def handle_editorial_dedupe_candidate_vs_backlog(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate one Shortlist row against the Publicaciones backlog (P2.4).

    Input:
        shortlist_page_id (str, required): Notion page id (or URL) of the
            Shortlist row to evaluate.
        dry_run (bool, optional): if True, still queries the Publicaciones
            backlog (read-only) and returns the computed verdict, but does not
            write `dedupe_status` / `publicacion_relacionada` back to Notion.

    Returns:
        {"ok": bool, "dedupe_status": str|None, "already_evaluated": bool,
         "matched_publicacion_page_id": str|None,
         "matched_publicacion_url": str|None, "shortlist_page_id": str,
         "dry_run": bool, "error": str|None}
    """
    shortlist_page_id = (input_data.get("shortlist_page_id") or "").strip()
    if not shortlist_page_id:
        return {"ok": False, "error": "'shortlist_page_id' is required"}

    db_id = config.NOTION_PUBLICACIONES_DB_ID
    if not db_id:
        return {"ok": False, "error": "NOTION_PUBLICACIONES_DB_ID not configured on server"}

    dry_run = bool(input_data.get("dry_run", False))

    try:
        page = notion_client.get_page(shortlist_page_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to read shortlist page: {e}", "shortlist_page_id": shortlist_page_id}

    candidate = _read_shortlist_fields(page)

    if candidate["dedupe_status"]:
        return {
            "ok": True,
            "dedupe_status": candidate["dedupe_status"],
            "already_evaluated": True,
            "matched_publicacion_page_id": (candidate["publicacion_relacionada"] or [None])[0],
            "shortlist_page_id": shortlist_page_id,
        }

    try:
        backlog_rows = notion_client.query_database(database_id=db_id, filter=_DEDUPE_FILTER)
    except Exception as e:
        return {"ok": False, "error": f"Failed to query Publicaciones backlog: {e}", "shortlist_page_id": shortlist_page_id}

    dedupe_status, match = find_backlog_match(candidate, backlog_rows)
    matched_page_id = match.get("id") if match else None
    matched_url = match.get("url") if match else None

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_write_dedupe_status": dedupe_status,
            "already_evaluated": False,
            "dedupe_status": dedupe_status,
            "matched_publicacion_page_id": matched_page_id,
            "matched_publicacion_url": matched_url,
            "backlog_rows_scanned": len(backlog_rows),
            "shortlist_page_id": shortlist_page_id,
        }

    props: Dict[str, Any] = {"dedupe_status": {"select": {"name": dedupe_status}}}
    if matched_page_id:
        props["publicacion_relacionada"] = {"relation": [{"id": matched_page_id}]}

    try:
        notion_client.update_page_properties(page_id_or_url=shortlist_page_id, properties=props)
    except Exception as e:
        return {"ok": False, "error": str(e), "shortlist_page_id": shortlist_page_id}

    return {
        "ok": True,
        "dedupe_status": dedupe_status,
        "already_evaluated": False,
        "matched_publicacion_page_id": matched_page_id,
        "matched_publicacion_url": matched_url,
        "backlog_rows_scanned": len(backlog_rows),
        "shortlist_page_id": shortlist_page_id,
    }
