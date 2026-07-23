"""
Tests for editorial.dedupe_candidate_vs_backlog (P2.4 — Shortlist candidate vs
Publicaciones backlog). See worker/tasks/editorial_dedupe.py and
docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.4.
"""

from unittest.mock import patch

from worker.tasks.editorial_dedupe import find_backlog_match, normalize_topic_key


def _title_prop(text):
    return {"type": "title", "title": [{"plain_text": text}]}


def _rich_text_prop(text):
    return {"type": "rich_text", "rich_text": [{"plain_text": text}]} if text else {"type": "rich_text", "rich_text": []}


def _select_prop(name):
    return {"type": "select", "select": {"name": name} if name else None}


def _status_prop(name):
    return {"type": "status", "status": {"name": name} if name else None}


def _url_prop(url):
    return {"type": "url", "url": url}


def _relation_prop(ids):
    return {"type": "relation", "relation": [{"id": i} for i in ids]}


def _shortlist_page(
    page_id="shortlist-1",
    titulo="Gobernanza minima en BIM",
    topic_key=None,
    fuente_pieza_url="https://example.com/piece",
    dedupe_status=None,
    publicacion_relacionada=None,
):
    return {
        "id": page_id,
        "properties": {
            "Título": _title_prop(titulo),
            "topic_key": _rich_text_prop(topic_key),
            "fuente_pieza_url": _url_prop(fuente_pieza_url),
            "dedupe_status": _select_prop(dedupe_status),
            "publicacion_relacionada": _relation_prop(publicacion_relacionada or []),
        },
    }


def _publicacion_row(row_id="pub-1", url="https://www.notion.so/pub-1", estado="Borrador", titulo="Otro tema", fuente_primaria=None):
    return {
        "id": row_id,
        "url": url,
        "properties": {
            "Estado": _status_prop(estado),
            "Título": _title_prop(titulo),
            "Fuente primaria": _url_prop(fuente_primaria),
        },
    }


# ---------------------------------------------------------------------------
# normalize_topic_key (pure function)
# ---------------------------------------------------------------------------


def test_normalize_topic_key_casefolds_and_strips_accents():
    assert normalize_topic_key("Gobernanza en BIM") == normalize_topic_key("gobernanza  en bim.")
    assert normalize_topic_key("Automatización") == normalize_topic_key("automatizacion")


def test_normalize_topic_key_collapses_punctuation_and_whitespace():
    assert normalize_topic_key("¿Gobernanza, minima?  en BIM!") == "gobernanza minima en bim"


def test_normalize_topic_key_empty_for_falsy_input():
    assert normalize_topic_key(None) == ""
    assert normalize_topic_key("") == ""


# ---------------------------------------------------------------------------
# find_backlog_match (pure function)
# ---------------------------------------------------------------------------


def test_find_backlog_match_nuevo_when_no_rows():
    status, match = find_backlog_match({"topic_key": "algo nuevo", "fuente_pieza_url": "https://x.test/a"}, [])
    assert status == "nuevo"
    assert match is None


def test_find_backlog_match_url_match_marks_duplicado_borrador():
    candidate = {"fuente_pieza_url": "https://example.com/piece", "topic_key": "no coincide"}
    backlog = [_publicacion_row(estado="Borrador", titulo="Distinto", fuente_primaria="https://example.com/piece")]
    status, match = find_backlog_match(candidate, backlog)
    assert status == "duplicado_borrador"
    assert match["id"] == "pub-1"


def test_find_backlog_match_topic_match_via_normalized_title():
    candidate = {"topic_key": None, "titulo": "Gobernanza  en BIM", "fuente_pieza_url": ""}
    backlog = [_publicacion_row(estado="Publicado", titulo="gobernanza en bim!", fuente_primaria=None)]
    status, match = find_backlog_match(candidate, backlog)
    assert status == "duplicado_publicado"
    assert match["id"] == "pub-1"


def test_find_backlog_match_publicado_outranks_borrador():
    candidate = {"topic_key": "gobernanza", "fuente_pieza_url": ""}
    backlog = [
        _publicacion_row(row_id="pub-borrador", estado="Borrador", titulo="gobernanza"),
        _publicacion_row(row_id="pub-publicado", estado="Publicado", titulo="gobernanza"),
    ]
    status, match = find_backlog_match(candidate, backlog)
    assert status == "duplicado_publicado"
    assert match["id"] == "pub-publicado"


def test_find_backlog_match_no_match_is_nuevo():
    candidate = {"topic_key": "tema completamente distinto", "fuente_pieza_url": "https://example.com/other"}
    backlog = [_publicacion_row(estado="Borrador", titulo="otro tema", fuente_primaria="https://example.com/piece")]
    status, match = find_backlog_match(candidate, backlog)
    assert status == "nuevo"
    assert match is None


# ---------------------------------------------------------------------------
# handle_editorial_dedupe_candidate_vs_backlog
# ---------------------------------------------------------------------------


def test_requires_shortlist_page_id():
    from worker.tasks.editorial_dedupe import handle_editorial_dedupe_candidate_vs_backlog

    result = handle_editorial_dedupe_candidate_vs_backlog({})
    assert result["ok"] is False
    assert "shortlist_page_id" in result["error"]


def test_no_db_configured():
    from worker.tasks.editorial_dedupe import handle_editorial_dedupe_candidate_vs_backlog

    with patch("worker.tasks.editorial_dedupe.config") as mock_cfg:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = None
        result = handle_editorial_dedupe_candidate_vs_backlog({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert "NOTION_PUBLICACIONES_DB_ID" in result["error"]


def test_already_evaluated_is_idempotent_noop():
    from worker.tasks.editorial_dedupe import handle_editorial_dedupe_candidate_vs_backlog

    with patch("worker.tasks.editorial_dedupe.config") as mock_cfg, patch(
        "worker.tasks.editorial_dedupe.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page(
            dedupe_status="nuevo", publicacion_relacionada=["prior-match"]
        )

        result = handle_editorial_dedupe_candidate_vs_backlog({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["already_evaluated"] is True
    assert result["dedupe_status"] == "nuevo"
    assert result["matched_publicacion_page_id"] == "prior-match"
    mock_nc.query_database.assert_not_called()
    mock_nc.update_page_properties.assert_not_called()


def test_dry_run_queries_backlog_but_does_not_write():
    """dry_run still performs the backlog read (needed for a meaningful
    preview) but must never write dedupe_status back to Notion."""
    from worker.tasks.editorial_dedupe import handle_editorial_dedupe_candidate_vs_backlog

    with patch("worker.tasks.editorial_dedupe.config") as mock_cfg, patch(
        "worker.tasks.editorial_dedupe.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page()
        mock_nc.query_database.return_value = []

        result = handle_editorial_dedupe_candidate_vs_backlog(
            {"shortlist_page_id": "shortlist-1", "dry_run": True}
        )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["would_write_dedupe_status"] == "nuevo"
    assert result["dedupe_status"] == "nuevo"
    mock_nc.query_database.assert_called_once()
    mock_nc.update_page_properties.assert_not_called()


def test_writes_nuevo_when_no_match():
    from worker.tasks.editorial_dedupe import handle_editorial_dedupe_candidate_vs_backlog

    with patch("worker.tasks.editorial_dedupe.config") as mock_cfg, patch(
        "worker.tasks.editorial_dedupe.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page()
        mock_nc.query_database.return_value = []

        result = handle_editorial_dedupe_candidate_vs_backlog({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["dedupe_status"] == "nuevo"
    assert result["matched_publicacion_page_id"] is None
    mock_nc.query_database.assert_called_once_with(
        database_id="pub-db",
        filter={
            "or": [
                {"property": "Estado", "status": {"equals": "Borrador"}},
                {"property": "Estado", "status": {"equals": "Publicado"}},
            ]
        },
    )
    mock_nc.update_page_properties.assert_called_once_with(
        page_id_or_url="shortlist-1",
        properties={"dedupe_status": {"select": {"name": "nuevo"}}},
    )


def test_writes_duplicado_borrador_with_relation_on_match():
    from worker.tasks.editorial_dedupe import handle_editorial_dedupe_candidate_vs_backlog

    with patch("worker.tasks.editorial_dedupe.config") as mock_cfg, patch(
        "worker.tasks.editorial_dedupe.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page(fuente_pieza_url="https://example.com/piece")
        mock_nc.query_database.return_value = [
            _publicacion_row(row_id="matched-pub", estado="Borrador", fuente_primaria="https://example.com/piece")
        ]

        result = handle_editorial_dedupe_candidate_vs_backlog({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["dedupe_status"] == "duplicado_borrador"
    assert result["matched_publicacion_page_id"] == "matched-pub"
    mock_nc.update_page_properties.assert_called_once_with(
        page_id_or_url="shortlist-1",
        properties={
            "dedupe_status": {"select": {"name": "duplicado_borrador"}},
            "publicacion_relacionada": {"relation": [{"id": "matched-pub"}]},
        },
    )


def test_get_page_failure_returns_ok_false():
    from worker.tasks.editorial_dedupe import handle_editorial_dedupe_candidate_vs_backlog

    with patch("worker.tasks.editorial_dedupe.config") as mock_cfg, patch(
        "worker.tasks.editorial_dedupe.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.side_effect = RuntimeError("Notion API error (404)")

        result = handle_editorial_dedupe_candidate_vs_backlog({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert "Failed to read shortlist page" in result["error"]


def test_query_database_failure_returns_ok_false_without_writing():
    from worker.tasks.editorial_dedupe import handle_editorial_dedupe_candidate_vs_backlog

    with patch("worker.tasks.editorial_dedupe.config") as mock_cfg, patch(
        "worker.tasks.editorial_dedupe.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page()
        mock_nc.query_database.side_effect = RuntimeError("Notion API error (500)")

        result = handle_editorial_dedupe_candidate_vs_backlog({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert "Failed to query Publicaciones backlog" in result["error"]
    mock_nc.update_page_properties.assert_not_called()


def test_update_failure_returns_ok_false():
    from worker.tasks.editorial_dedupe import handle_editorial_dedupe_candidate_vs_backlog

    with patch("worker.tasks.editorial_dedupe.config") as mock_cfg, patch(
        "worker.tasks.editorial_dedupe.notion_client"
    ) as mock_nc:
        mock_cfg.NOTION_PUBLICACIONES_DB_ID = "pub-db"
        mock_nc.get_page.return_value = _shortlist_page()
        mock_nc.query_database.return_value = []
        mock_nc.update_page_properties.side_effect = RuntimeError("Notion API error (500)")

        result = handle_editorial_dedupe_candidate_vs_backlog({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
