"""Read-only typed models for the ``📰 Publicaciones`` Notion DB.

This module exposes Pydantic v2 models that mirror the live Notion schema
audited on 2026-05-08 (see
``docs/audits/2026-05-08-notion-publicaciones-schema-audit.md``).

**Read-only by contract.** The module exposes parsing helpers
(``Publicacion.from_notion``) but **does not** implement any writer. Stage
10 (``stage10_*``) is the only writer and lives outside this module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool


# ---------------------------------------------------------------------------
# Helpers (mirror the lightweight coercion in ``gates.py``)
# ---------------------------------------------------------------------------

def _checkbox(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict) and "checkbox" in value:
        return bool(value["checkbox"])
    return False


def _url(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict) and "url" in value:
        v = value.get("url")
        return v if isinstance(v, str) and v else None
    return None


def _select(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        sel = value.get("select")
        if isinstance(sel, dict):
            name = sel.get("name")
            return name if isinstance(name, str) else None
        if "name" in value and isinstance(value["name"], str):
            return value["name"]
    return None


def _status(value: Any) -> Optional[str]:
    # Notion ``status`` payloads share shape with ``select``.
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        st = value.get("status") or value.get("select")
        if isinstance(st, dict):
            name = st.get("name")
            return name if isinstance(name, str) else None
    return None


def _text(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        rt = value.get("rich_text")
        if isinstance(rt, list):
            parts = [
                item.get("plain_text", "")
                for item in rt
                if isinstance(item, dict)
            ]
            joined = "".join(parts)
            return joined or None
    return None


def _date_start(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        d = value.get("date")
        if isinstance(d, dict):
            start = d.get("start")
            return start if isinstance(start, str) else None
    return None


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class Gates(BaseModel):
    """Mirror of the 3 explicit gate checkboxes plus derived flags.

    Uses :class:`StrictBool` so :meth:`Publicacion.from_notion` raises
    ``ValidationError`` on malformed gate payloads (ints, strings, etc.).
    """

    model_config = ConfigDict(extra="forbid")

    aprobado_contenido: StrictBool = False
    autorizar_publicacion: StrictBool = False
    gate_invalidado: StrictBool = False


class Variants(BaseModel):
    """Per-channel copy variants (text columns in Notion)."""

    model_config = ConfigDict(extra="forbid")

    blog: Optional[str] = Field(default=None, description="Copy Blog")
    linkedin: Optional[str] = Field(default=None, description="Copy LinkedIn")
    x: Optional[str] = Field(default=None, description="Copy X")
    newsletter: Optional[str] = Field(default=None, description="Copy Newsletter")


class Visual(BaseModel):
    """Inline visual asset metadata (no separate Assets DB in v1)."""

    model_config = ConfigDict(extra="forbid")

    brief: Optional[str] = Field(default=None, description="Visual brief")
    asset_url: Optional[str] = Field(default=None, description="Visual asset URL")
    hitl_required: bool = False


class Publicacion(BaseModel):
    """Read-only typed view of a single ``📰 Publicaciones`` page."""

    model_config = ConfigDict(extra="forbid")

    # Identity
    page_id: Optional[str] = None
    titulo: Optional[str] = None
    publication_id: Optional[str] = None

    # Classification
    canal: Optional[str] = None
    canal_publicado: Optional[str] = None
    tipo_contenido: Optional[str] = None
    etapa_audiencia: Optional[str] = None
    prioridad: Optional[str] = None
    estado: Optional[str] = None

    # Gates
    gates: Gates = Field(default_factory=Gates)

    # Integrity
    content_hash: Optional[str] = None
    idempotency_key: Optional[str] = None
    trace_id: Optional[str] = None

    # Sources
    fuente_primaria: Optional[str] = None
    fuente_referente: Optional[str] = None
    resumen_fuente: Optional[str] = None

    # Editorial
    premisa: Optional[str] = None
    claim_principal: Optional[str] = None
    angulo_editorial: Optional[str] = None
    comentarios_revision: Optional[str] = None
    notas: Optional[str] = None

    # Variants & visual
    variants: Variants = Field(default_factory=Variants)
    visual: Visual = Field(default_factory=Visual)

    # Publishing metadata
    platform_post_id: Optional[str] = None
    publication_url: Optional[str] = None
    published_url: Optional[str] = None
    published_at: Optional[str] = None
    fecha_publicacion: Optional[str] = None

    # Errors
    publish_error: Optional[str] = None
    error_kind: Optional[str] = None

    # Audit
    repo_reference: Optional[str] = None
    proyecto: Optional[str] = None
    ultima_revision_humana: Optional[str] = None
    ultima_edicion: Optional[str] = None
    creado_por_sistema: bool = False

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    @classmethod
    def from_notion(cls, page_dict: dict) -> "Publicacion":
        """Parse a Notion page dict into a :class:`Publicacion`.

        Accepts both the official Notion API shape (``{"properties": {...}}``
        with typed property dicts) and a flat dict where values are already
        coerced primitives. Missing fields default to ``None`` / ``False``;
        ``ValidationError`` is only raised when a present value has the wrong
        primitive type (e.g. ``aprobado_contenido=42``).
        """
        if not isinstance(page_dict, dict):
            raise TypeError("page_dict must be a dict")
        props = page_dict.get("properties", page_dict)
        if not isinstance(props, dict):
            props = {}

        page_id = page_dict.get("id") if isinstance(page_dict.get("id"), str) else None

        # Strict primitive validation: if a known field is present with the
        # wrong type (and not a Notion property dict), surface a ValidationError.
        return cls.model_validate(
            {
                "page_id": page_id,
                "titulo": _text(props.get("Título")),
                "publication_id": _text(props.get("publication_id")),
                "canal": _select(props.get("Canal")),
                "canal_publicado": _select(props.get("canal_publicado")),
                "tipo_contenido": _select(props.get("Tipo de contenido")),
                "etapa_audiencia": _select(props.get("Etapa audiencia")),
                "prioridad": _select(props.get("Prioridad")),
                "estado": _status(props.get("Estado")),
                "gates": {
                    "aprobado_contenido": _checkbox_or_passthrough(
                        props.get("aprobado_contenido")
                    ),
                    "autorizar_publicacion": _checkbox_or_passthrough(
                        props.get("autorizar_publicacion")
                    ),
                    "gate_invalidado": _checkbox_or_passthrough(
                        props.get("gate_invalidado")
                    ),
                },
                "content_hash": _text(props.get("content_hash")),
                "idempotency_key": _text(props.get("idempotency_key")),
                "trace_id": _text(props.get("trace_id")),
                "fuente_primaria": _url(props.get("Fuente primaria")),
                "fuente_referente": _url(props.get("Fuente referente")),
                "resumen_fuente": _text(props.get("Resumen fuente")),
                "premisa": _text(props.get("Premisa")),
                "claim_principal": _text(props.get("Claim principal")),
                "angulo_editorial": _text(props.get("Ángulo editorial")),
                "comentarios_revision": _text(props.get("Comentarios revisión")),
                "notas": _text(props.get("Notas")),
                "variants": {
                    "blog": _text(props.get("Copy Blog")),
                    "linkedin": _text(props.get("Copy LinkedIn")),
                    "x": _text(props.get("Copy X")),
                    "newsletter": _text(props.get("Copy Newsletter")),
                },
                "visual": {
                    "brief": _text(props.get("Visual brief")),
                    "asset_url": _url(props.get("Visual asset URL")),
                    "hitl_required": _checkbox(props.get("visual_hitl_required")),
                },
                "platform_post_id": _text(props.get("platform_post_id")),
                "publication_url": _url(props.get("publication_url")),
                "published_url": _url(props.get("published_url")),
                "published_at": _date_start(props.get("published_at")),
                "fecha_publicacion": _date_start(props.get("Fecha publicación")),
                "publish_error": _text(props.get("publish_error")),
                "error_kind": _select(props.get("error_kind")),
                "repo_reference": _url(props.get("Repo reference")),
                "proyecto": _text(props.get("Proyecto")),
                "ultima_revision_humana": _date_start(
                    props.get("Última revisión humana")
                ),
                "ultima_edicion": _text(props.get("Última edición")),
                "creado_por_sistema": _checkbox(props.get("Creado por sistema")),
            }
        )


def _checkbox_or_passthrough(value: Any) -> Any:
    """Coerce Notion checkbox shapes to ``bool``; pass anything else through.

    Returning the raw value on malformed input lets pydantic ``StrictBool``
    surface a clean ``ValidationError`` from :meth:`Publicacion.from_notion`
    instead of a low-level ``TypeError``.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, dict) and "checkbox" in value:
        return value["checkbox"]
    return value


__all__ = ["Publicacion", "Gates", "Variants", "Visual"]
