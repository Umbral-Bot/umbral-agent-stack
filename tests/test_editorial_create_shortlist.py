"""
Tests for editorial.create_shortlist_alternativa (P1 — V1 alternativa
registration in the "Alternativas / Shortlist" DB). See
worker/tasks/editorial_create_shortlist.py and
docs/ops/rick-editorial-agent.md (PKG-MACRO-P5-Q12-T5).
"""

from unittest.mock import patch

# A syntactically valid (but fake) 32-hex Notion id — round-trips unchanged
# through the real _extract_notion_page_id (not mocked; it's a pure function
# imported directly, immune to the notion_client module patch below).
_DS_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _valid_input(**overrides):
    payload = {
        "alternativa_id": "CAND-OLA3-03-SHORTLIST-V1",
        "titulo": "openBIM antes de automatizar",
        "arco_narrativo": "De X a Y tensionando Z.",
        "estructura_discurso": "Estructura de discurso usada: [hipótesis, ...]",
        "fuente_pieza_url": (
            "https://raw.githubusercontent.com/buildingSMART/IDS/"
            "development/Documentation/UserManual/README.md"
        ),
    }
    payload.update(overrides)
    return payload


def test_requires_v1_obligatory_fields():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    result = handle_editorial_create_shortlist_alternativa({})

    assert result["ok"] is False
    assert "alternativa_id" in result["error"]
    assert "titulo" in result["error"]
    assert "arco_narrativo" in result["error"]
    assert "estructura_discurso" in result["error"]
    assert "fuente_pieza_url" in result["error"]


def test_missing_single_obligatory_field_is_an_error():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    payload = _valid_input()
    del payload["arco_narrativo"]

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        result = handle_editorial_create_shortlist_alternativa(payload)

    assert result["ok"] is False
    assert result["error"] == "missing required field(s): arco_narrativo"


def test_no_ds_id_configured():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg:
        mock_cfg.NOTION_SHORTLIST_DS_ID = None
        result = handle_editorial_create_shortlist_alternativa(_valid_input())

    assert result["ok"] is False
    assert "NOTION_SHORTLIST_DS_ID" in result["error"]


def test_fuente_pieza_url_home_page_blocks_creation():
    """Real regression source: CAND-OLA3-03's Fuente primaria is
    buildingsmart.org (the bare org home page). A V1 alternativa citing the
    same home URL must be refused, not silently created."""
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        payload = _valid_input(fuente_pieza_url="https://www.buildingsmart.org/")

        result = handle_editorial_create_shortlist_alternativa(payload)

    assert result["ok"] is False
    assert result["error"] == "fuente_pieza_url_is_home_or_feed"
    assert result["fuente_pieza_url"] == "https://www.buildingsmart.org/"
    mock_nc.query_database.assert_not_called()
    mock_nc.create_database_page.assert_not_called()


def test_fuente_pieza_url_home_page_blocks_dry_run_too():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        payload = _valid_input(
            fuente_pieza_url="https://www.buildingsmart.org/", dry_run=True
        )

        result = handle_editorial_create_shortlist_alternativa(payload)

    assert result["ok"] is False
    assert result["error"] == "fuente_pieza_url_is_home_or_feed"
    mock_nc.create_database_page.assert_not_called()


def test_empty_fuente_pieza_url_blocks_creation():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    payload = _valid_input(fuente_pieza_url="")

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        result = handle_editorial_create_shortlist_alternativa(payload)

    # Empty fuente_pieza_url is caught by the required-field check first.
    assert result["ok"] is False
    assert "fuente_pieza_url" in result["error"]


def test_concrete_piece_dry_run_previews_pendiente_without_writes():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID

        result = handle_editorial_create_shortlist_alternativa(
            _valid_input(dry_run=True)
        )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["would_create"] is True
    assert result["created"] is False
    assert result["already_exists"] is False
    props = result["properties_preview"]
    assert props["Resultado revisión"] == {"select": {"name": "Pendiente"}}
    assert props["Título"]["title"][0]["text"]["content"] == "openBIM antes de automatizar"
    assert props["fuente_pieza_url"] == {
        "url": (
            "https://raw.githubusercontent.com/buildingSMART/IDS/"
            "development/Documentation/UserManual/README.md"
        )
    }
    mock_nc.query_database.assert_not_called()
    mock_nc.create_database_page.assert_not_called()


def test_concrete_piece_creates_row_with_resultado_revision_pendiente():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {
            "page_id": "new-shortlist-page",
            "url": "https://www.notion.so/new-shortlist-page",
            "created": True,
        }

        result = handle_editorial_create_shortlist_alternativa(_valid_input())

    assert result["ok"] is True
    assert result["created"] is True
    assert result["already_exists"] is False
    assert result["shortlist_page_id"] == "new-shortlist-page"

    mock_nc.query_database.assert_called_once_with(
        database_id=_DS_ID,
        filter={
            "property": "alternativa_id",
            "rich_text": {"equals": "CAND-OLA3-03-SHORTLIST-V1"},
        },
    )
    create_kwargs = mock_nc.create_database_page.call_args.kwargs
    assert create_kwargs["database_id_or_url"] == _DS_ID
    assert create_kwargs["properties"]["Resultado revisión"] == {
        "select": {"name": "Pendiente"}
    }


def test_idempotent_by_alternativa_id_does_not_duplicate():
    """Second call with the same alternativa_id must not create a duplicate
    row — matches the roadmap done-criterion already enforced for promote."""
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        mock_nc.query_database.return_value = [
            {"id": "already-created", "url": "https://www.notion.so/already-created"}
        ]

        result = handle_editorial_create_shortlist_alternativa(_valid_input())

    assert result["ok"] is True
    assert result["created"] is False
    assert result["already_exists"] is True
    assert result["shortlist_page_id"] == "already-created"
    mock_nc.create_database_page.assert_not_called()


def test_whitespace_is_stripped_consistently_in_dedup_and_stored_properties():
    """Regression: alternativa_id/fuente_pieza_url must be normalized the
    SAME way for the idempotency lookup and for what actually gets written —
    otherwise a value with incidental whitespace is stored raw while every
    later dedup check strips first, breaking idempotency for that row."""
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {
            "page_id": "p",
            "url": "u",
            "created": True,
        }

        result = handle_editorial_create_shortlist_alternativa(
            _valid_input(
                alternativa_id="  CAND-OLA3-03-SHORTLIST-V1  ",
                fuente_pieza_url=(
                    "  https://raw.githubusercontent.com/buildingSMART/IDS/"
                    "development/Documentation/UserManual/README.md  "
                ),
            )
        )

    assert result["ok"] is True
    assert result["alternativa_id"] == "CAND-OLA3-03-SHORTLIST-V1"

    query_filter = mock_nc.query_database.call_args.kwargs["filter"]
    stripped_id = query_filter["rich_text"]["equals"]
    assert stripped_id == "CAND-OLA3-03-SHORTLIST-V1"

    create_props = mock_nc.create_database_page.call_args.kwargs["properties"]
    stored_id = create_props["alternativa_id"]["rich_text"][0]["text"]["content"]
    stored_url = create_props["fuente_pieza_url"]["url"]
    assert stored_id == stripped_id, "stored alternativa_id must match the id used for dedup"
    assert stored_url == (
        "https://raw.githubusercontent.com/buildingSMART/IDS/"
        "development/Documentation/UserManual/README.md"
    )


def test_ds_id_as_full_page_url_is_normalized_consistently():
    """Regression: NOTION_SHORTLIST_DS_ID may plausibly be set to the full
    Notion page URL (that's the value shown in alternativas-shortlist.schema.yaml's
    live_binding.notion_page_url) — both the dedup query and the create call
    must resolve to the SAME bare id, not silently disagree."""
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = (
            "https://app.notion.com/p/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {
            "page_id": "p",
            "url": "u",
            "created": True,
        }

        result = handle_editorial_create_shortlist_alternativa(_valid_input())

    assert result["ok"] is True
    expected_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert mock_nc.query_database.call_args.kwargs["database_id"] == expected_id
    assert (
        mock_nc.create_database_page.call_args.kwargs["database_id_or_url"]
        == expected_id
    )


def test_unparseable_ds_id_returns_clean_error():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = "not-a-real-notion-id"

        result = handle_editorial_create_shortlist_alternativa(_valid_input())

    assert result["ok"] is False
    assert "NOTION_SHORTLIST_DS_ID" in result["error"]
    mock_nc.query_database.assert_not_called()
    mock_nc.create_database_page.assert_not_called()


def test_invalid_fuente_tipo_rejected():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID

        result = handle_editorial_create_shortlist_alternativa(
            _valid_input(fuente_tipo="not_a_real_option")
        )

    assert result["ok"] is False
    assert "invalid fuente_tipo" in result["error"]
    mock_nc.create_database_page.assert_not_called()


def test_invalid_canal_sugerido_rejected():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID

        result = handle_editorial_create_shortlist_alternativa(
            _valid_input(canal_sugerido="tiktok")
        )

    assert result["ok"] is False
    assert "invalid canal_sugerido" in result["error"]
    mock_nc.create_database_page.assert_not_called()


def test_optional_fields_included_when_present():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {
            "page_id": "p",
            "url": "u",
            "created": True,
        }

        handle_editorial_create_shortlist_alternativa(
            _valid_input(
                topic_key="openbim-gobierno-datos",
                premisa="Tesis condensada.",
                fuente_tipo="official_doc",
                fuente_discovery_url="https://github.com/buildingSMART/IDS",
                canal_sugerido="blog",
                score_alineacion=0.91,
            )
        )

    props = mock_nc.create_database_page.call_args.kwargs["properties"]
    assert props["topic_key"]["rich_text"][0]["text"]["content"] == "openbim-gobierno-datos"
    assert props["premisa"]["rich_text"][0]["text"]["content"] == "Tesis condensada."
    assert props["fuente_tipo"] == {"select": {"name": "official_doc"}}
    assert props["fuente_discovery_url"] == {
        "url": "https://github.com/buildingSMART/IDS"
    }
    assert props["canal_sugerido"] == {"select": {"name": "blog"}}
    assert props["score_alineacion"] == {"number": 0.91}


def test_optional_fields_omitted_when_absent():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID

        result = handle_editorial_create_shortlist_alternativa(
            _valid_input(dry_run=True)
        )

    props = result["properties_preview"]
    for optional_key in (
        "topic_key",
        "premisa",
        "fuente_tipo",
        "fuente_discovery_url",
        "canal_sugerido",
        "score_alineacion",
    ):
        assert optional_key not in props


def test_query_failure_returns_ok_false():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        mock_nc.query_database.side_effect = RuntimeError("Notion API error (500)")

        result = handle_editorial_create_shortlist_alternativa(_valid_input())

    assert result["ok"] is False
    assert "Failed to query Shortlist DB" in result["error"]
    mock_nc.create_database_page.assert_not_called()


def test_create_failure_returns_ok_false():
    from worker.tasks.editorial_create_shortlist import (
        handle_editorial_create_shortlist_alternativa,
    )

    with patch("worker.tasks.editorial_create_shortlist.config") as mock_cfg, patch(
        "worker.tasks.editorial_create_shortlist.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_SHORTLIST_DS_ID = _DS_ID
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.side_effect = RuntimeError("Notion API error (400)")

        result = handle_editorial_create_shortlist_alternativa(_valid_input())

    assert result["ok"] is False
    assert "Notion API error (400)" in result["error"]
