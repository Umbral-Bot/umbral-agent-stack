"""Tests for ``scripts.discovery.lib.notion_publicaciones`` (read-only models).

No HTTP. Fixtures are pure dicts mirroring the Notion API shape and the
flat shape used internally by some scripts.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scripts.discovery.lib.notion_publicaciones import (
    Gates,
    Publicacion,
    Variants,
    Visual,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _full_notion_page() -> dict:
    """Full Notion-API-shaped page, mirrored from the live audit."""
    return {
        "id": "abc-123",
        "properties": {
            "Título": {"rich_text": [{"plain_text": "Mi publicación"}]},
            "publication_id": {"rich_text": [{"plain_text": "pub-001"}]},
            "Canal": {"select": {"name": "linkedin"}},
            "canal_publicado": {"select": {"name": "linkedin"}},
            "Tipo de contenido": {"select": {"name": "linkedin_post"}},
            "Etapa audiencia": {"select": {"name": "awareness"}},
            "Prioridad": {"select": {"name": "alta"}},
            "Estado": {"status": {"name": "Borrador"}},
            "aprobado_contenido": {"checkbox": False},
            "autorizar_publicacion": {"checkbox": False},
            "gate_invalidado": {"checkbox": False},
            "content_hash": {"rich_text": [{"plain_text": "deadbeef"}]},
            "idempotency_key": {"rich_text": [{"plain_text": "linkedin:deadbeef:abc"}]},
            "trace_id": {"rich_text": [{"plain_text": "trace-xyz"}]},
            "Fuente primaria": {"url": "https://example.com/source"},
            "Fuente referente": {"url": "https://example.com/ref"},
            "Resumen fuente": {"rich_text": [{"plain_text": "Resumen…"}]},
            "Premisa": {"rich_text": [{"plain_text": "Una premisa fuerte."}]},
            "Claim principal": {"rich_text": [{"plain_text": "El claim."}]},
            "Ángulo editorial": {"rich_text": [{"plain_text": "Ángulo Umbral."}]},
            "Comentarios revisión": {"rich_text": [{"plain_text": ""}]},
            "Notas": {"rich_text": [{"plain_text": "Notas internas."}]},
            "Copy Blog": {"rich_text": [{"plain_text": "Cuerpo blog"}]},
            "Copy LinkedIn": {"rich_text": [{"plain_text": "Cuerpo LinkedIn"}]},
            "Copy X": {"rich_text": [{"plain_text": "Cuerpo X"}]},
            "Copy Newsletter": {"rich_text": [{"plain_text": "Cuerpo Newsletter"}]},
            "Visual brief": {"rich_text": [{"plain_text": "Brief visual"}]},
            "Visual asset URL": {"url": "https://cdn.example.com/img.png"},
            "visual_hitl_required": {"checkbox": True},
            "platform_post_id": {"rich_text": [{"plain_text": ""}]},
            "publication_url": {"url": None},
            "published_url": {"url": None},
            "published_at": {"date": None},
            "Fecha publicación": {"date": {"start": "2026-05-10"}},
            "publish_error": {"rich_text": [{"plain_text": ""}]},
            "error_kind": {"select": None},
            "Repo reference": {"url": "https://github.com/x/y/pull/1"},
            "Proyecto": {"rich_text": [{"plain_text": "Umbral BIM"}]},
            "Última revisión humana": {"date": {"start": "2026-05-08"}},
            "Última edición": {"rich_text": [{"plain_text": "2026-05-08T10:00:00Z"}]},
            "Creado por sistema": {"checkbox": False},
        },
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_parse_full_notion_page():
    pub = Publicacion.from_notion(_full_notion_page())
    assert pub.page_id == "abc-123"
    assert pub.titulo == "Mi publicación"
    assert pub.canal == "linkedin"
    assert pub.estado == "Borrador"
    assert pub.gates.aprobado_contenido is False
    assert pub.gates.autorizar_publicacion is False
    assert pub.gates.gate_invalidado is False
    assert pub.content_hash == "deadbeef"
    assert pub.idempotency_key == "linkedin:deadbeef:abc"
    assert pub.fuente_primaria == "https://example.com/source"
    assert pub.variants.linkedin == "Cuerpo LinkedIn"
    assert pub.variants.x == "Cuerpo X"
    assert pub.visual.hitl_required is True
    assert pub.fecha_publicacion == "2026-05-10"


# ---------------------------------------------------------------------------
# Defaults: missing fields → safe defaults
# ---------------------------------------------------------------------------


def test_empty_page_yields_safe_defaults():
    pub = Publicacion.from_notion({"properties": {}})
    assert pub.titulo is None
    assert pub.canal is None
    assert pub.estado is None
    # Critical: gates default False (never True by omission)
    assert pub.gates.aprobado_contenido is False
    assert pub.gates.autorizar_publicacion is False
    assert pub.gates.gate_invalidado is False
    assert pub.variants.blog is None
    assert pub.visual.hitl_required is False


def test_partial_page_only_known_fields_kept():
    pub = Publicacion.from_notion(
        {
            "id": "p1",
            "properties": {
                "Título": {"rich_text": [{"plain_text": "Solo título"}]},
                "Canal": {"select": {"name": "blog"}},
            },
        }
    )
    assert pub.titulo == "Solo título"
    assert pub.canal == "blog"
    assert pub.gates.aprobado_contenido is False
    assert pub.fuente_primaria is None


def test_flat_dict_shape_is_accepted():
    pub = Publicacion.from_notion(
        {
            "Título": "Plana",
            "Canal": "x",
            "aprobado_contenido": True,
        }
    )
    assert pub.titulo == "Plana"
    assert pub.canal == "x"
    assert pub.gates.aprobado_contenido is True


# ---------------------------------------------------------------------------
# Validation errors on malformed payloads
# ---------------------------------------------------------------------------


def test_non_dict_page_raises():
    with pytest.raises(TypeError):
        Publicacion.from_notion("not a dict")  # type: ignore[arg-type]


def test_invalid_checkbox_type_raises_validation_error():
    with pytest.raises(ValidationError):
        Publicacion.from_notion(
            {"properties": {"aprobado_contenido": 42}}  # type: ignore[dict-item]
        )


def test_invalid_inner_checkbox_payload_raises_validation_error():
    with pytest.raises(ValidationError):
        Publicacion.from_notion(
            {"properties": {"gate_invalidado": {"checkbox": "yes"}}}
        )


# ---------------------------------------------------------------------------
# Sub-models defaults
# ---------------------------------------------------------------------------


def test_gates_defaults():
    g = Gates()
    assert g.aprobado_contenido is False
    assert g.autorizar_publicacion is False
    assert g.gate_invalidado is False


def test_variants_defaults():
    v = Variants()
    assert v.blog is None
    assert v.linkedin is None
    assert v.x is None
    assert v.newsletter is None


def test_visual_defaults():
    v = Visual()
    assert v.brief is None
    assert v.asset_url is None
    assert v.hitl_required is False


def test_extra_fields_forbidden_on_models():
    with pytest.raises(ValidationError):
        Gates(unknown_field=True)  # type: ignore[call-arg]
