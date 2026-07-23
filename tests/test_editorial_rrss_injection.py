"""
Tests for Fila I = B RRSS injection (P2.7): after a successful blog publish,
inject published_url into the per-channel RRSS copies and mark
listo_rrss=true. See worker/tasks/editorial_publish.py::
inject_rrss_copies_and_mark_ready / handle_editorial_inject_rrss_ready and
docs/ops/editorial-rrss-injection-p27-2026-07-23.md.

No LinkedIn/X API is ever called here — only Notion rich_text/checkbox
properties.
"""

from unittest.mock import patch

from worker.tasks.editorial_publish import (
    _DEFAULT_NOTION_PROP_MAP,
    handle_editorial_inject_rrss_ready,
    inject_rrss_copies_and_mark_ready,
)


def _rich_text_prop(text):
    return {"type": "rich_text", "rich_text": [{"plain_text": text}]} if text else {"type": "rich_text", "rich_text": []}


def _url_prop(url):
    return {"type": "url", "url": url}


def _checkbox_prop(value):
    return {"type": "checkbox", "checkbox": bool(value)}


def _publicaciones_page(
    page_id="pub-1",
    copy_linkedin="Un teaser de LinkedIn.",
    copy_x="Un post de X.",
    copy_linkedin_empresa="Texto para compartir.",
    published_url="https://umbralbim.io/noticias/x",
    listo_rrss=False,
):
    return {
        "id": page_id,
        "properties": {
            "Copy LinkedIn": _rich_text_prop(copy_linkedin),
            "Copy X": _rich_text_prop(copy_x),
            "Copy LinkedIn empresa": _rich_text_prop(copy_linkedin_empresa),
            "published_url": _url_prop(published_url),
            "listo_rrss": _checkbox_prop(listo_rrss),
        },
    }


# ---------------------------------------------------------------------------
# inject_rrss_copies_and_mark_ready
# ---------------------------------------------------------------------------


def test_already_ready_is_idempotent_noop():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page(listo_rrss=True)

        result = inject_rrss_copies_and_mark_ready(
            "pub-1", _DEFAULT_NOTION_PROP_MAP, published_url="https://umbralbim.io/noticias/x"
        )

    assert result["ok"] is True
    assert result["already_ready"] is True
    assert result["injected_channels"] == []
    mock_update.assert_not_called()


def test_missing_published_url_fails_closed():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page(published_url=None)

        result = inject_rrss_copies_and_mark_ready("pub-1", _DEFAULT_NOTION_PROP_MAP)

    assert result["ok"] is False
    assert result["error"] == "published_url_missing"
    mock_update.assert_not_called()


def test_injects_link_into_all_nonempty_channels_and_marks_ready():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page()

        result = inject_rrss_copies_and_mark_ready(
            "pub-1", _DEFAULT_NOTION_PROP_MAP, published_url="https://umbralbim.io/noticias/x"
        )

    assert result["ok"] is True
    assert result["already_ready"] is False
    assert set(result["injected_channels"]) == {"copy_linkedin", "copy_x", "copy_linkedin_empresa"}

    props = mock_update.call_args.kwargs["properties"]
    assert props["listo_rrss"] == {"checkbox": True}
    assert props["published_url"] == {"url": "https://umbralbim.io/noticias/x"}
    li_text = props["Copy LinkedIn"]["rich_text"][0]["text"]["content"]
    assert li_text.startswith("Un teaser de LinkedIn.")
    assert li_text.endswith("https://umbralbim.io/noticias/x")


def test_empty_channel_copy_is_skipped_not_fabricated():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page(copy_linkedin_empresa="")

        result = inject_rrss_copies_and_mark_ready(
            "pub-1", _DEFAULT_NOTION_PROP_MAP, published_url="https://umbralbim.io/noticias/x"
        )

    assert "copy_linkedin_empresa" not in result["injected_channels"]
    props = mock_update.call_args.kwargs["properties"]
    assert "Copy LinkedIn empresa" not in props


def test_channel_already_containing_link_is_left_untouched():
    already = "Un teaser.\n\nhttps://umbralbim.io/noticias/x"
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page(copy_linkedin=already)

        result = inject_rrss_copies_and_mark_ready(
            "pub-1", _DEFAULT_NOTION_PROP_MAP, published_url="https://umbralbim.io/noticias/x"
        )

    assert "copy_linkedin" not in result["injected_channels"]
    props = mock_update.call_args.kwargs["properties"]
    assert "Copy LinkedIn" not in props
    # the other two channels (no link yet) still get injected
    assert "copy_x" in result["injected_channels"]


def test_dry_run_previews_without_writing():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page()

        result = inject_rrss_copies_and_mark_ready(
            "pub-1",
            _DEFAULT_NOTION_PROP_MAP,
            published_url="https://umbralbim.io/noticias/x",
            dry_run=True,
        )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["would_inject"] is True
    assert set(result["injected_channels"]) == {"copy_linkedin", "copy_x", "copy_linkedin_empresa"}
    mock_update.assert_not_called()


def test_published_url_falls_back_to_notion_property_when_not_passed():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page(published_url="https://umbralbim.io/noticias/from-notion")

        result = inject_rrss_copies_and_mark_ready("pub-1", _DEFAULT_NOTION_PROP_MAP)

    assert result["ok"] is True
    props = mock_update.call_args.kwargs["properties"]
    assert props["published_url"] == {"url": "https://umbralbim.io/noticias/from-notion"}
    li_text = props["Copy LinkedIn"]["rich_text"][0]["text"]["content"]
    assert li_text.endswith("https://umbralbim.io/noticias/from-notion")


def test_get_page_failure_returns_ok_false():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties"):
        mock_get_page.side_effect = RuntimeError("Notion API error (404)")

        result = inject_rrss_copies_and_mark_ready(
            "pub-1", _DEFAULT_NOTION_PROP_MAP, published_url="https://umbralbim.io/noticias/x"
        )

    assert result["ok"] is False
    assert "notion_page_id" in result


def test_update_failure_returns_ok_false():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page()
        mock_update.side_effect = RuntimeError("Notion API error (500)")

        result = inject_rrss_copies_and_mark_ready(
            "pub-1", _DEFAULT_NOTION_PROP_MAP, published_url="https://umbralbim.io/noticias/x"
        )

    assert result["ok"] is False


# ---------------------------------------------------------------------------
# handle_editorial_inject_rrss_ready
# ---------------------------------------------------------------------------


def test_handler_requires_notion_page_id():
    result = handle_editorial_inject_rrss_ready({})
    assert result["ok"] is False
    assert "notion_page_id" in result["error"]


def test_handler_reads_published_url_from_notion_and_injects():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page(published_url="https://umbralbim.io/noticias/y")

        result = handle_editorial_inject_rrss_ready({"notion_page_id": "pub-1"})

    assert result["ok"] is True
    assert result["already_ready"] is False
    props = mock_update.call_args.kwargs["properties"]
    assert props["published_url"] == {"url": "https://umbralbim.io/noticias/y"}


def test_handler_dry_run_does_not_write():
    with patch("worker.notion_client.get_page") as mock_get_page, patch("worker.notion_client.update_page_properties") as mock_update:
        mock_get_page.return_value = _publicaciones_page()

        result = handle_editorial_inject_rrss_ready({"notion_page_id": "pub-1", "dry_run": True})

    assert result["ok"] is True
    assert result["dry_run"] is True
    mock_update.assert_not_called()


def test_handler_registered():
    from worker.tasks import TASK_HANDLERS

    assert "editorial.inject_rrss_ready" in TASK_HANDLERS
    assert TASK_HANDLERS["editorial.inject_rrss_ready"] is handle_editorial_inject_rrss_ready
