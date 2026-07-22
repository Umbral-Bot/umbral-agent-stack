"""
Task: editorial.promote_shortlist_approval — P2.1 poller/handler.

Promotes a Shortlist ("Alternativas / Shortlist") row marked
`Resultado revisión = Aprobar` into a `Publicaciones` draft row, per:

    docs/ops/editorial-norte-hitl-contract-2026-07-22.md §4 (HITL-1), §6
      (hybrid schema, promotion contract)
    docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md P2.1
    notion/schemas/alternativas-shortlist.schema.yaml (source fields)
    notion/schemas/publicaciones.schema.yaml (origen_alternativa target field)

Contract (do not weaken):
- Promotion is unidirectional and single-event (Aprobar -> create once), never
  a continuous sync. Writing to Notion is Worker/core's exclusive job (ADR-011
  #1) — the dispatcher poller only decides *which* rows to ask this handler to
  (re-)evaluate; it never writes to Notion itself.
- Fail-closed: this handler re-fetches the Shortlist page itself and only acts
  when `Resultado revisión == "Aprobar"` is verified live — it never trusts a
  caller-supplied snapshot for the actual gate check.
- Idempotent: if the Shortlist row's own `promovido_a` relation is already
  set, this is a no-op (`already_promoted=True`). As a second safety net
  against a partial previous run (create succeeded, write-back of
  `promovido_a` failed), Publicaciones is also queried for an existing row
  whose `origen_alternativa` already points back at this Shortlist page before
  creating a new one.
- The new Publicaciones row is always created in `Borrador` with both human
  gates (`aprobado_contenido`, `autorizar_publicacion`) false — this handler
  never opens a gate, never publishes, never writes copy/images (those are
  P2.2/P2.3, separate packages).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .. import config, notion_client

logger = logging.getLogger("worker.tasks.editorial_promote")

_APPROVED_VALUE = "Aprobar"

# Shortlist canal_sugerido -> Publicaciones Tipo de contenido (both schemas
# share the blog/linkedin/x/newsletter vocabulary for Canal; Tipo de contenido
# needs a content-shape guess since Shortlist doesn't carry one yet).
_CANAL_TO_TIPO_CONTENIDO = {
    "blog": "blog_post",
    "linkedin": "linkedin_post",
    "x": "x_post",
    "newsletter": "newsletter",
}
_DEFAULT_TIPO_CONTENIDO = "blog_post"


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
    if ptype == "checkbox":
        return bool(prop.get("checkbox"))
    if ptype == "relation":
        return [item.get("id", "") for item in prop.get("relation", [])]
    return None


def _rt(text: str, limit: int) -> List[Dict[str, Any]]:
    return [{"text": {"content": (text or "")[:limit]}}]


def _read_shortlist_fields(page: Dict[str, Any]) -> Dict[str, Any]:
    props = page.get("properties") or {}

    def get(name: str) -> Any:
        return _flatten_prop(props.get(name))

    return {
        "titulo": get("Título"),
        "alternativa_id": get("alternativa_id"),
        "resultado_revision": get("Resultado revisión"),
        "promovido_a": get("promovido_a") or [],
        "premisa": get("premisa"),
        "arco_narrativo": get("arco_narrativo"),
        "estructura_discurso": get("estructura_discurso"),
        "fuente_pieza_url": get("fuente_pieza_url"),
        "canal_sugerido": get("canal_sugerido"),
    }


def _build_publicacion_properties(shortlist_page_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    titulo = fields.get("titulo") or "(sin título)"
    canal = fields.get("canal_sugerido") or ""
    tipo_contenido = _CANAL_TO_TIPO_CONTENIDO.get(canal, _DEFAULT_TIPO_CONTENIDO)
    alternativa_id = fields.get("alternativa_id") or shortlist_page_id

    props: Dict[str, Any] = {
        "Título": {"title": _rt(titulo, 300)},
        "publication_id": {"rich_text": _rt(f"shortlist-{alternativa_id}", 200)},
        "Tipo de contenido": {"select": {"name": tipo_contenido}},
        "Estado": {"status": {"name": "Borrador"}},
        "aprobado_contenido": {"checkbox": False},
        "autorizar_publicacion": {"checkbox": False},
        "Creado por sistema": {"checkbox": True},
        "origen_alternativa": {"relation": [{"id": shortlist_page_id}]},
    }
    if canal:
        props["Canal"] = {"select": {"name": canal}}
    if fields.get("premisa"):
        props["Premisa"] = {"rich_text": _rt(fields["premisa"], 500)}
    if fields.get("fuente_pieza_url"):
        props["Fuente primaria"] = {"url": fields["fuente_pieza_url"]}

    notes_parts = []
    if fields.get("arco_narrativo"):
        notes_parts.append(f"Arco narrativo: {fields['arco_narrativo']}")
    if fields.get("estructura_discurso"):
        notes_parts.append(f"Estructura de discurso: {fields['estructura_discurso']}")
    if notes_parts:
        props["Notas"] = {"rich_text": _rt("\n\n".join(notes_parts), 2000)}

    return props


def handle_editorial_promote_shortlist_approval(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Promote one approved Shortlist row into a Publicaciones draft (P2.1).

    Input:
        shortlist_page_id (str, required): Notion page id (or URL) of the
            Shortlist row to evaluate.
        dry_run (bool, optional): if True, verify the gate and return the
            properties that would be written, without calling Notion to
            create or update anything.

    Returns:
        {"ok": bool, "created": bool, "already_promoted": bool,
         "publicacion_page_id": str|None, "publicacion_url": str|None,
         "shortlist_page_id": str, "error": str|None}
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

    fields = _read_shortlist_fields(page)

    if fields["resultado_revision"] != _APPROVED_VALUE:
        return {
            "ok": False,
            "error": "not_approved",
            "resultado_revision": fields["resultado_revision"],
            "shortlist_page_id": shortlist_page_id,
        }

    if fields["promovido_a"]:
        return {
            "ok": True,
            "created": False,
            "already_promoted": True,
            "publicacion_page_id": fields["promovido_a"][0],
            "shortlist_page_id": shortlist_page_id,
        }

    props = _build_publicacion_properties(shortlist_page_id, fields)

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_promote": True,
            "created": False,
            "already_promoted": False,
            "properties_preview": props,
            "shortlist_page_id": shortlist_page_id,
        }

    try:
        existing = notion_client.query_database(
            database_id=db_id,
            filter={"property": "origen_alternativa", "relation": {"contains": shortlist_page_id}},
        )
    except Exception as e:
        return {"ok": False, "error": f"Failed to query Publicaciones DB: {e}", "shortlist_page_id": shortlist_page_id}

    try:
        if existing:
            publicacion_page_id = existing[0]["id"]
            publicacion_url = existing[0].get("url", "")
            created = False
        else:
            result = notion_client.create_database_page(
                database_id_or_url=db_id,
                properties=props,
            )
            publicacion_page_id = result["page_id"]
            publicacion_url = result.get("url", "")
            created = True

        notion_client.update_page_properties(
            page_id_or_url=shortlist_page_id,
            properties={"promovido_a": {"relation": [{"id": publicacion_page_id}]}},
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "shortlist_page_id": shortlist_page_id}

    logger.info(
        "Promoted shortlist page %s -> publicacion %s (created=%s)",
        shortlist_page_id[:8],
        publicacion_page_id[:8],
        created,
    )
    return {
        "ok": True,
        "created": created,
        "already_promoted": False,
        "publicacion_page_id": publicacion_page_id,
        "publicacion_url": publicacion_url,
        "shortlist_page_id": shortlist_page_id,
    }
