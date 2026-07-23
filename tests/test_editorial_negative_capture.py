"""
Tests for editorial.capture_negative_example (P2.5 — Shortlist Descartar ->
negative-example capture, fila D of the gap matrix, previously AUSENTE). See
worker/tasks/editorial_negative_capture.py and
docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.5.
"""

from unittest.mock import patch


def _title_prop(text):
    return {"type": "title", "title": [{"plain_text": text}]}


def _rich_text_prop(text):
    return {"type": "rich_text", "rich_text": [{"plain_text": text}]} if text else {"type": "rich_text", "rich_text": []}


def _select_prop(name):
    return {"type": "select", "select": {"name": name} if name else None}


def _checkbox_prop(value):
    return {"type": "checkbox", "checkbox": bool(value)}


def _multi_select_prop(names):
    return {"type": "multi_select", "multi_select": [{"name": n} for n in (names or [])]}


def _shortlist_page(
    page_id="shortlist-1",
    titulo="Un ángulo descartado",
    resultado_revision="Descartar",
    motivo_descarte="Fuente es la home, no la pieza concreta.",
    ejemplo_negativo=False,
    error_kind=None,
):
    return {
        "id": page_id,
        "properties": {
            "Título": _title_prop(titulo),
            "Resultado revisión": _select_prop(resultado_revision),
            "motivo_descarte": _rich_text_prop(motivo_descarte),
            "ejemplo_negativo": _checkbox_prop(ejemplo_negativo),
            "error_kind": _multi_select_prop(error_kind),
        },
    }


def test_requires_shortlist_page_id():
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    result = handle_editorial_capture_negative_example({})
    assert result["ok"] is False
    assert "shortlist_page_id" in result["error"]


def test_not_discarded_blocks_without_writes():
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    with patch("worker.tasks.editorial_negative_capture.notion_client") as mock_nc:
        mock_nc.get_page.return_value = _shortlist_page(resultado_revision="Pendiente")

        result = handle_editorial_capture_negative_example({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert result["error"] == "not_discarded"
    assert result["resultado_revision"] == "Pendiente"
    mock_nc.update_page_properties.assert_not_called()


def test_already_captured_is_idempotent_noop():
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    with patch("worker.tasks.editorial_negative_capture.notion_client") as mock_nc:
        mock_nc.get_page.return_value = _shortlist_page(ejemplo_negativo=True, error_kind=["fuente_home_no_pieza"])

        result = handle_editorial_capture_negative_example({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["captured"] is False
    assert result["already_captured"] is True
    assert result["motivo_descarte"] == "Fuente es la home, no la pieza concreta."
    assert result["error_kind"] == ["fuente_home_no_pieza"]
    mock_nc.update_page_properties.assert_not_called()


def test_missing_motivo_descarte_fails_closed_without_writes():
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    with patch("worker.tasks.editorial_negative_capture.notion_client") as mock_nc:
        mock_nc.get_page.return_value = _shortlist_page(motivo_descarte="")

        result = handle_editorial_capture_negative_example({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert result["error"] == "motivo_descarte_missing"
    mock_nc.update_page_properties.assert_not_called()


def test_missing_motivo_descarte_whitespace_only_also_fails_closed():
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    with patch("worker.tasks.editorial_negative_capture.notion_client") as mock_nc:
        mock_nc.get_page.return_value = _shortlist_page(motivo_descarte="   ")

        result = handle_editorial_capture_negative_example({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert result["error"] == "motivo_descarte_missing"
    mock_nc.update_page_properties.assert_not_called()


def test_dry_run_previews_without_writes():
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    with patch("worker.tasks.editorial_negative_capture.notion_client") as mock_nc:
        mock_nc.get_page.return_value = _shortlist_page(error_kind=["arco_confuso"])

        result = handle_editorial_capture_negative_example(
            {"shortlist_page_id": "shortlist-1", "dry_run": True}
        )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["would_capture"] is True
    assert result["captured"] is False
    assert result["motivo_descarte"] == "Fuente es la home, no la pieza concreta."
    assert result["error_kind"] == ["arco_confuso"]
    mock_nc.update_page_properties.assert_not_called()


def test_captures_and_flips_ejemplo_negativo():
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    with patch("worker.tasks.editorial_negative_capture.notion_client") as mock_nc:
        mock_nc.get_page.return_value = _shortlist_page(error_kind=["tono_generico"])

        result = handle_editorial_capture_negative_example({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["dry_run"] is False
    assert result["captured"] is True
    assert result["already_captured"] is False
    assert result["error_kind"] == ["tono_generico"]
    mock_nc.update_page_properties.assert_called_once_with(
        page_id_or_url="shortlist-1",
        properties={"ejemplo_negativo": {"checkbox": True}},
    )


def test_captures_with_empty_error_kind_is_not_blocked():
    """error_kind is soft/optional per the schema's own note ('poblar
    empiricamente ... no inventar un enum cerrado') — an empty error_kind
    must not block capture, unlike motivo_descarte."""
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    with patch("worker.tasks.editorial_negative_capture.notion_client") as mock_nc:
        mock_nc.get_page.return_value = _shortlist_page(error_kind=None)

        result = handle_editorial_capture_negative_example({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is True
    assert result["captured"] is True
    assert result["error_kind"] == []
    mock_nc.update_page_properties.assert_called_once()


def test_get_page_failure_returns_ok_false():
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    with patch("worker.tasks.editorial_negative_capture.notion_client") as mock_nc:
        mock_nc.get_page.side_effect = RuntimeError("Notion API error (404)")

        result = handle_editorial_capture_negative_example({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
    assert "Failed to read shortlist page" in result["error"]


def test_update_failure_returns_ok_false():
    from worker.tasks.editorial_negative_capture import handle_editorial_capture_negative_example

    with patch("worker.tasks.editorial_negative_capture.notion_client") as mock_nc:
        mock_nc.get_page.return_value = _shortlist_page()
        mock_nc.update_page_properties.side_effect = RuntimeError("Notion API error (500)")

        result = handle_editorial_capture_negative_example({"shortlist_page_id": "shortlist-1"})

    assert result["ok"] is False
