"""
Tests for editorial.promote_shortlist_approval (P2.1 — Shortlist Aprobar ->
Publicaciones). See worker/tasks/editorial_promote.py and
docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.1.
"""

from unittest.mock import patch

import pytest


def _title_prop(text):
    return {"type": "title", "title": [{"plain_text": text}]}


def _rich_text_prop(text):
    return {"type": "rich_text", "rich_text": [{"plain_text": text}]}


def _select_prop(name):
    return {"type": "select", "select": {"name": name} if name else None}


def _url_prop(url):
    return {"type": "url", "url": url}


def _relation_prop(ids):
    return {"type": "relation", "relation": [{"id": i} for i in ids]}


def _shortlist_page(
    page_id="shortlist-1",
    titulo="Un ángulo interesante",
    alternativa_id="ALT-001",
    resultado_revision="Aprobar",
    promovido_a=None,
    premisa="Tesis condensada.",
    arco_narrativo="De X a Y tensionando Z.",
    estructura_discurso="Estructura de discurso usada: [hipótesis, ...]",
    fuente_pieza_url="https://example.com/piece",
    canal_sugerido="blog",
):
    return {
        "id": page_id,
        "properties": {
            "Título": _title_prop(titulo),
            "alternativa_id": _rich_text_prop(alternativa_id),
            "Resultado revisión": _select_prop(resultado_revision),
            "promovido_a": _relation_prop(promovido_a or []),
            "premisa": _rich_text_prop(premisa),
            "arco_narrativo": _rich_text_prop(arco_narrativo),
            "estructura_discurso": _rich_text_prop(estructura_discurso),
            "fuente_pieza_url": _url_prop(fuente_pieza_url),
            "canal_sugerido": _select_prop(canal_sugerido),
        },
    }


def test_requires_shortlist_page_id():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    result = handle_editorial_promote_shortlist_approval({})
    assert result["ok"] is False
    assert "shortlist_page_id" in result["error"]


def test_no_db_configured():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = None
        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert "NOTION_PUBLICACIONES_DB_ID" in result["error"]


def test_not_approved_blocks_without_writes():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page(resultado_revision="Pendiente")

        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert result["error"] == "not_approved"
    assert result["resultado_revision"] == "Pendiente"
    mock_nc.create_database_page.assert_not_called()
    mock_nc.update_page_properties.assert_not_called()


def test_already_promoted_is_idempotent_noop():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page(promovido_a=["pub-existing"])

        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["created"] is False
    assert result["already_promoted"] is True
    assert result["publicacion_page_id"] == "pub-existing"
    mock_nc.query_database.assert_not_called()
    mock_nc.create_database_page.assert_not_called()
    mock_nc.update_page_properties.assert_not_called()


def test_fuente_pieza_url_home_page_blocks_promotion():
    """Real regression: CAND-OLA3-03 promoted with buildingsmart.org (the
    bare org home page) instead of the concrete piece. This must now be
    refused, not silently promoted with a bad source."""
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page(
            fuente_pieza_url="https://www.buildingsmart.org/"
        )

        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert result["error"] == "fuente_pieza_url_is_home_or_feed"
    assert result["fuente_pieza_url"] == "https://www.buildingsmart.org/"
    mock_nc.query_database.assert_not_called()
    mock_nc.create_database_page.assert_not_called()
    mock_nc.update_page_properties.assert_not_called()


def test_fuente_pieza_url_feed_url_blocks_promotion():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page(
            fuente_pieza_url="https://blog.example.com/feed"
        )

        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert result["error"] == "fuente_pieza_url_is_home_or_feed"
    mock_nc.create_database_page.assert_not_called()


def test_fuente_pieza_url_home_page_blocks_dry_run_too():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page(
            fuente_pieza_url="https://www.buildingsmart.org/"
        )

        result = handle_editorial_promote_shortlist_approval(
            {"shortlist_page_id": "shortlist-1", "dry_run": True}
        )

    assert result["ok"] is False
    assert result["error"] == "fuente_pieza_url_is_home_or_feed"


def test_fuente_pieza_url_concrete_piece_still_promotes():
    """The item-URL sibling of the buildingsmart.org negative example
    (docs/ops/candidates/ola3-pitch02-...) — a specific article path on the
    same domain must NOT be blocked by the guard."""
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page(
            fuente_pieza_url="https://www.buildingsmart.org/ifc-4-3-approved-as-a-final-standard/"
        )
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {"page_id": "pub-new", "url": "https://notion.so/pub-new"}

        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["created"] is True
    mock_nc.create_database_page.assert_called_once()


def test_dry_run_previews_without_writes():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page()

        result = handle_editorial_promote_shortlist_approval(
            {"shortlist_page_id": "shortlist-1", "dry_run": True}
        )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["would_promote"] is True
    assert result["properties_preview"]["Título"]["title"][0]["text"]["content"] == "Un ángulo interesante"
    assert result["properties_preview"]["origen_alternativa"] == {"relation": [{"id": "shortlist-1"}]}
    mock_nc.query_database.assert_not_called()
    mock_nc.create_database_page.assert_not_called()
    mock_nc.update_page_properties.assert_not_called()


def test_creates_publicacion_and_writes_back_relation():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page()
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {
            "page_id": "new-pub-page",
            "url": "https://www.notion.so/new-pub-page",
            "created": True,
        }

        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["created"] is True
    assert result["already_promoted"] is False
    assert result["publicacion_page_id"] == "new-pub-page"

    mock_nc.query_database.assert_called_once_with(
        database_id="pub-db",
        filter={"property": "origen_alternativa", "relation": {"contains": "shortlist-1"}},
    )
    create_kwargs = mock_nc.create_database_page.call_args.kwargs
    assert create_kwargs["database_id_or_url"] == "pub-db"
    props = create_kwargs["properties"]
    assert props["Tipo de contenido"] == {"select": {"name": "blog_post"}}
    assert props["Canal"] == {"select": {"name": "blog"}}
    assert props["Estado"] == {"status": {"name": "Borrador"}}
    assert props["aprobado_contenido"] == {"checkbox": False}
    assert props["autorizar_publicacion"] == {"checkbox": False}
    assert props["Creado por sistema"] == {"checkbox": True}
    assert props["Fuente primaria"] == {"url": "https://example.com/piece"}
    assert "Arco narrativo" in props["Notas"]["rich_text"][0]["text"]["content"]
    assert "Estructura de discurso" in props["Notas"]["rich_text"][0]["text"]["content"]

    mock_nc.update_page_properties.assert_called_once_with(
        page_id_or_url="shortlist-1",
        properties={"promovido_a": {"relation": [{"id": "new-pub-page"}]}},
    )


@pytest.mark.parametrize(
    "canal,expected_tipo",
    [
        ("linkedin", "linkedin_post"),
        ("x", "x_post"),
        ("newsletter", "newsletter"),
        ("", "blog_post"),
        (None, "blog_post"),
    ],
)
def test_canal_to_tipo_contenido_mapping(canal, expected_tipo):
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page(canal_sugerido=canal)
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {"page_id": "p", "url": "u", "created": True}

        handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    props = mock_nc.create_database_page.call_args.kwargs["properties"]
    assert props["Tipo de contenido"] == {"select": {"name": expected_tipo}}
    if canal:
        assert props["Canal"] == {"select": {"name": canal}}
    else:
        assert "Canal" not in props


def test_race_safety_net_finds_existing_row_instead_of_duplicating():
    """If a previous run created the row but failed before writing back
    promovido_a, re-running must find the existing row via origen_alternativa
    instead of creating a duplicate (roadmap P2.1 done-criterion: re-run does
    not duplicate)."""
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page()
        mock_nc.query_database.return_value = [
            {"id": "already-created-pub", "url": "https://www.notion.so/already-created-pub"}
        ]

        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["created"] is False
    assert result["publicacion_page_id"] == "already-created-pub"
    mock_nc.create_database_page.assert_not_called()
    mock_nc.update_page_properties.assert_called_once_with(
        page_id_or_url="shortlist-1",
        properties={"promovido_a": {"relation": [{"id": "already-created-pub"}]}},
    )


def test_get_page_failure_returns_ok_false():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.side_effect = RuntimeError("Notion API error (404)")

        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert "Failed to read shortlist page" in result["error"]


def test_create_failure_does_not_write_back_relation():
    from worker.tasks.editorial_promote import handle_editorial_promote_shortlist_approval

    with patch("worker.tasks.editorial_promote.config") as mock_cfg, patch(
        "worker.tasks.editorial_promote.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page()
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.side_effect = RuntimeError("Notion API error (500)")

        result = handle_editorial_promote_shortlist_approval({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    mock_nc.update_page_properties.assert_not_called()
