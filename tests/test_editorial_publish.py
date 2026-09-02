"""Tests for the editorial blog publish handler (web.publish_editorial_post).

No Azure / Notion network — urllib and notion_client are mocked.

Covers:
- handler registration
- input validation (missing source, malformed payload, bad slug)
- the HARD gate: never POST without autorizar_publicacion=true (no network call)
- Notion-source gate read + block
- dry_run (no network, content_hash computed)
- content_hash auto-compute (parity with the function's shared helper)
- success path: headers (function key + worker token), POST body, response mapping
- function-not-configured + HTTP error handling
- Notion-source success + published_url write-back
- visual-asset resolution from the versioned Publicaciones v2 schema

Run with:
    WORKER_TOKEN=test python -m pytest tests/test_editorial_publish.py -v
"""

import base64
import json
import urllib.error
from io import BytesIO
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.editorial_publish import (
    _content_hash,
    _missing_required_fields,
    _resolve_publication_id_to_page_id,
    handle_web_publish_editorial_post,
    resolve_visual_asset_urls,
)

FUNCTION_URL = "https://func-umbral-editorial-prod.azurewebsites.net/api/publish-editorial-post"


# ======================================================================
# Helpers
# ======================================================================


def _authorized_payload(**overrides: Any) -> Dict[str, Any]:
    payload = {
        "slug": "ia-en-coordinacion-bim",
        "title": "IA en la coordinación BIM",
        "excerpt": "Criterios de aceptación explícitos antes de escalar.",
        "body_markdown": "## Intro\n\nTexto del cuerpo.",
        "hero_image_url": "https://cdn.umbralbim.io/heroes/ia-bim.jpg",
        "notion_page_id": "11111111-1111-1111-1111-111111111111",
        "tags": ["BIM", "IA"],
        "autorizar_publicacion": True,
        "aprobado_contenido": True,
    }
    payload.update(overrides)
    return payload


class FakeHTTPResponse:
    def __init__(self, status: int = 200, body: str = ""):
        self.status = status
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _ok_function_body(**overrides: Any) -> str:
    body = {
        "ok": True,
        "published_url": "https://umbralbim.io/noticias/ia-en-coordinacion-bim",
        "blob_path": "posts/ia-en-coordinacion-bim.json",
        "index_updated": True,
        "slug": "ia-en-coordinacion-bim",
        "content_hash": "deadbeef",
    }
    body.update(overrides)
    return json.dumps(body)


def _notion_page(authorized: bool = True, approved: bool = True) -> Dict[str, Any]:
    return {
        "id": "22222222-2222-2222-2222-222222222222",
        "properties": {
            "Title": {"type": "title", "title": [{"plain_text": "Post desde Notion"}]},
            "Slug": {"type": "rich_text", "rich_text": [{"plain_text": "post-desde-notion"}]},
            "Copy Blog": {"type": "rich_text", "rich_text": [{"plain_text": "## Cuerpo\n\nContenido."}]},
            "Bajada": {"type": "rich_text", "rich_text": [{"plain_text": "Una bajada."}]},
            "Hero Image": {"type": "url", "url": "https://cdn.umbralbim.io/h.jpg"},
            "Tags": {"type": "multi_select", "multi_select": [{"name": "BIM"}]},
            "Fecha publicación": {"type": "date", "date": {"start": "2026-06-07"}},
            "autorizar_publicacion": {"type": "checkbox", "checkbox": authorized},
            "aprobado_contenido": {"type": "checkbox", "checkbox": approved},
        },
    }


_RAG_ENV = (
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.setenv("EDITORIAL_BLOG_FUNCTION_URL", FUNCTION_URL)
    monkeypatch.setenv("EDITORIAL_BLOG_FUNCTION_KEY", "fn-key-123")
    monkeypatch.setenv("WORKER_TOKEN", "wt-456")
    monkeypatch.delenv("EDITORIAL_BLOG_CANONICAL_BASE_URL", raising=False)
    # RAG hook env off by default → deterministic skip unless a test sets it.
    for _k in (*_RAG_ENV, "EDITORIAL_RAG_INDEX_NAME", "EDITORIAL_BLOG_ASSET_UPLOAD"):
        monkeypatch.delenv(_k, raising=False)


def _set_rag_env(monkeypatch):
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://search.example.net")
    monkeypatch.setenv("AZURE_SEARCH_API_KEY", "search-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://oai.example.net")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "oai-key")


# ======================================================================
# Registration
# ======================================================================


class TestRegistration:
    def test_handler_registered(self):
        from worker.tasks import TASK_HANDLERS

        assert "web.publish_editorial_post" in TASK_HANDLERS
        assert TASK_HANDLERS["web.publish_editorial_post"] is handle_web_publish_editorial_post


# ======================================================================
# Input validation
# ======================================================================


class TestInputValidation:
    def test_no_source(self):
        with pytest.raises(ValueError, match="payload.*or.*notion_page_id"):
            handle_web_publish_editorial_post({})

    def test_no_source_message_mentions_publication_id(self):
        # The B1 bridge may send publication_id instead of notion_page_id, so
        # the "no source" message has to name it too.
        with pytest.raises(ValueError, match="publication_id"):
            handle_web_publish_editorial_post({})

    def test_missing_required_fields_is_structured_not_a_raise(self):
        # Gates open, content still empty -> structured refusal, no ValueError
        # (a raise would mark the task failed). Full coverage in
        # TestGatesBeforeNormalize.
        result = handle_web_publish_editorial_post(
            {"payload": {"autorizar_publicacion": True}, "telegram_confirmed": True}
        )
        assert result["ok"] is False
        assert result["error"] == "missing_required_fields"

    def test_bad_slug(self):
        # A present-but-malformed slug is a caller bug, not a gate state: it
        # still raises (all three gates open here so normalization is reached).
        with pytest.raises(ValueError, match="slug.*kebab-case"):
            handle_web_publish_editorial_post(
                {
                    "payload": _authorized_payload(slug="Not A Slug"),
                    "telegram_confirmed": True,
                }
            )

    def test_bad_timeout(self):
        with pytest.raises(ValueError, match="timeout.*between 1 and 120"):
            handle_web_publish_editorial_post(
                {"payload": _authorized_payload(), "timeout": 0}
            )


# ======================================================================
# Hard authorization gate (no network)
# ======================================================================


class TestAuthorizationGate:
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_payload_not_authorized_blocks(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(autorizar_publicacion=False)}
        )
        assert result["ok"] is False
        assert result["error"] == "publication_not_authorized"
        assert result["would_publish"] is False
        assert result["gates"]["autorizar_publicacion"] is False
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_payload_authorized_but_not_approved_blocks(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(aprobado_contenido=False)}
        )
        assert result["ok"] is False
        assert result["error"] == "publication_not_authorized"
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_notion_gate_blocks(self, mock_get_page, mock_urlopen):
        mock_get_page.return_value = _notion_page(authorized=False)
        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222"}
        )
        assert result["ok"] is False
        assert result["error"] == "publication_not_authorized"
        assert result["source"] == "notion"
        mock_urlopen.assert_not_called()


# ======================================================================
# P2.6 / D3 (locked): the third hard gate — Telegram "ok publica"
# confirmation, asserted via telegram_confirmed. See
# docs/ops/editorial-hitl2-publish-bridge-p26-2026-07-23.md.
# ======================================================================


class TestTelegramConfirmationGate:
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_payload_source_blocks_without_telegram_confirmed(self, mock_urlopen):
        # authorized + approved are both true, but telegram_confirmed is
        # omitted — must still block, with no network call.
        result = handle_web_publish_editorial_post({"payload": _authorized_payload()})
        assert result["ok"] is False
        assert result["error"] == "telegram_confirmation_missing"
        assert result["would_publish"] is False
        assert result["gates"]["telegram_confirmed"] is False
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_payload_source_blocks_with_telegram_confirmed_false(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": False}
        )
        assert result["ok"] is False
        assert result["error"] == "telegram_confirmation_missing"
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_notion_source_blocks_without_telegram_confirmed(self, mock_get_page, mock_urlopen):
        # Notion-side gates (autorizar_publicacion/aprobado_contenido) both
        # true, but telegram_confirmed still isn't inferred from anywhere.
        mock_get_page.return_value = _notion_page()
        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222"}
        )
        assert result["ok"] is False
        assert result["error"] == "telegram_confirmation_missing"
        assert result["gates"]["telegram_confirmed"] is False
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_visual_or_authorization_gate_blocks_before_telegram_check(self, mock_urlopen):
        # Order matters for diagnostics: an unauthorized payload must report
        # publication_not_authorized, not telegram_confirmation_missing, even
        # though telegram_confirmed is also missing here.
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(autorizar_publicacion=False)}
        )
        assert result["error"] == "publication_not_authorized"
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_dry_run_still_blocked_without_telegram_confirmed(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "dry_run": True}
        )
        assert result["ok"] is False
        assert result["error"] == "telegram_confirmation_missing"
        assert result["would_publish"] is False
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_all_three_gates_true_dry_run_succeeds(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "dry_run": True, "telegram_confirmed": True}
        )
        assert result["ok"] is True
        assert result["would_publish"] is True
        assert result["gates"]["telegram_confirmed"] is True
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_all_three_gates_true_live_publishes(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is True
        assert result["published"] is True
        mock_urlopen.assert_called_once()


# ======================================================================
# dry_run + content_hash
# ======================================================================


class TestDryRunAndHash:
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_dry_run_no_network(self, mock_urlopen):
        payload = _authorized_payload()
        result = handle_web_publish_editorial_post(
            {"payload": payload, "dry_run": True, "telegram_confirmed": True}
        )
        assert result["ok"] is True
        assert result["would_publish"] is True
        assert result["dry_run"] is True
        assert result["blob_path"] == "posts/ia-en-coordinacion-bim.json"
        assert result["published_url"] == "https://umbralbim.io/noticias/ia-en-coordinacion-bim"
        # gate fields must not leak into the function payload
        assert "autorizar_publicacion" not in result["payload"]
        assert "aprobado_contenido" not in result["payload"]
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_content_hash_autocomputed(self, mock_urlopen):
        payload = _authorized_payload()
        result = handle_web_publish_editorial_post(
            {"payload": payload, "dry_run": True, "telegram_confirmed": True}
        )
        expected = _content_hash(payload["body_markdown"], payload["title"], payload["excerpt"])
        assert result["content_hash"] == expected
        assert result["payload"]["content_hash"] == expected

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_explicit_content_hash_preserved(self, mock_urlopen):
        payload = _authorized_payload(content_hash="0" * 64)
        result = handle_web_publish_editorial_post(
            {"payload": payload, "dry_run": True, "telegram_confirmed": True}
        )
        assert result["content_hash"] == "0" * 64

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_canonical_base_override(self, mock_urlopen, monkeypatch):
        monkeypatch.setenv("EDITORIAL_BLOG_CANONICAL_BASE_URL", "https://staging.umbralbim.io/")
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "dry_run": True, "telegram_confirmed": True}
        )
        assert result["published_url"] == "https://staging.umbralbim.io/noticias/ia-en-coordinacion-bim"


# ======================================================================
# Success path
# ======================================================================


class TestSuccessPath:
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_success_posts_and_maps_response(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )

        assert result["ok"] is True
        assert result["published"] is True
        assert result["status_code"] == 200
        assert result["published_url"] == "https://umbralbim.io/noticias/ia-en-coordinacion-bim"
        assert result["blob_path"] == "posts/ia-en-coordinacion-bim.json"
        assert result["index_updated"] is True

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_request_headers_and_body(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        handle_web_publish_editorial_post({"payload": _authorized_payload(), "telegram_confirmed": True})

        req = mock_urlopen.call_args[0][0]
        assert req.method == "POST"
        assert req.full_url == FUNCTION_URL
        assert req.get_header("X-functions-key") == "fn-key-123"
        assert req.get_header("X-worker-token") == "wt-456"

        body = json.loads(req.data.decode("utf-8"))
        assert body["slug"] == "ia-en-coordinacion-bim"
        assert body["author"] == "David Moreira"  # default
        assert "content_hash" in body
        assert "autorizar_publicacion" not in body  # gate stripped

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_no_worker_token_header_when_unset(self, mock_urlopen, monkeypatch):
        monkeypatch.delenv("WORKER_TOKEN", raising=False)
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        handle_web_publish_editorial_post({"payload": _authorized_payload(), "telegram_confirmed": True})
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("X-worker-token") is None


# ======================================================================
# Configuration + error handling
# ======================================================================


class TestConfigAndErrors:
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_function_url_not_configured(self, mock_urlopen, monkeypatch):
        monkeypatch.delenv("EDITORIAL_BLOG_FUNCTION_URL", raising=False)
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is False
        assert result["error"] == "not_configured"
        mock_urlopen.assert_not_called()

    def test_http_error_url_rejected(self, monkeypatch):
        monkeypatch.setenv("EDITORIAL_BLOG_FUNCTION_URL", "http://evil.example.com/api/publish")
        with pytest.raises(ValueError, match="https"):
            handle_web_publish_editorial_post(
                {"payload": _authorized_payload(), "telegram_confirmed": True}
            )

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_function_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            FUNCTION_URL, 400, "Bad Request", {}, BytesIO(b'{"ok":false,"error":"invalid_payload"}')
        )
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is False
        assert result["status_code"] == 400
        assert result["error"] == "invalid_payload"

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_function_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("refused")
        with pytest.raises(RuntimeError, match="connection failed"):
            handle_web_publish_editorial_post(
                {"payload": _authorized_payload(), "telegram_confirmed": True}
            )


# ======================================================================
# Notion source success + write-back
# ======================================================================


class TestNotionSource:
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_notion_success_maps_fields(self, mock_get_page, mock_urlopen):
        mock_get_page.return_value = _notion_page()
        mock_urlopen.return_value = FakeHTTPResponse(
            200, _ok_function_body(published_url="https://umbralbim.io/noticias/post-desde-notion")
        )
        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222", "telegram_confirmed": True}
        )
        assert result["ok"] is True
        assert result["source"] == "notion"

        body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert body["slug"] == "post-desde-notion"
        assert body["title"] == "Post desde Notion"
        assert body["tags"] == ["BIM"]

    @patch("worker.notion_client.update_page_properties", autospec=True)
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_notion_write_back_uses_real_update_signature(
        self, mock_get_page, mock_urlopen, mock_update
    ):
        mock_get_page.return_value = _notion_page()
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {
                "notion_page_id": "22222222-2222-2222-2222-222222222222",
                "write_back_to_notion": True,
                "telegram_confirmed": True,
            }
        )
        assert result["ok"] is True
        assert result["notion_write_back"]["ok"] is True
        mock_update.assert_called_once_with(
            page_id_or_url="22222222-2222-2222-2222-222222222222",
            properties={
                "published_url": {
                    "url": "https://umbralbim.io/noticias/ia-en-coordinacion-bim"
                }
            },
        )

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_notion_visual_selection_overrides_legacy_hero(
        self, mock_get_page, mock_urlopen
    ):
        page = _notion_page()
        page["properties"].update(
            {
                "Selección imagen": {
                    "type": "select",
                    "select": {"name": "Alt 2"},
                },
                "imagen_alt_2_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/heroes/selected-alt-2.jpg",
                },
                "Estado imagen": {
                    "type": "select",
                    "select": {"name": "Seleccionada"},
                },
                "Visual asset URL": {"type": "url", "url": None},
            }
        )
        mock_get_page.return_value = page
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())

        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222", "telegram_confirmed": True}
        )

        assert result["ok"] is True
        body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert body["hero_image_url"] == (
            "https://cdn.umbralbim.io/heroes/selected-alt-2.jpg"
        )
        assert "gates" not in body
        assert "visual_asset" not in body
        visual_gate = result["gates"]["visual_asset"]
        assert visual_gate["ready"] is True
        assert visual_gate["reason"] == "selected_alt_transition"
        assert visual_gate["hero_source"] == "selected_alt"

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_notion_sin_imagen_clears_legacy_hero(
        self, mock_get_page, mock_urlopen
    ):
        page = _notion_page()
        page["properties"]["Selección imagen"] = {
            "type": "select",
            "select": {"name": "Sin imagen"},
        }
        mock_get_page.return_value = page
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())

        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222", "telegram_confirmed": True}
        )

        assert result["ok"] is True
        body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert body["hero_image_url"] == ""
        assert result["gates"]["visual_asset"]["reason"] == "explicit_no_image"

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_legacy_page_prefers_visual_asset_url_over_hero_image(
        self, mock_get_page, mock_urlopen
    ):
        page = _notion_page()
        page["properties"]["Visual asset URL"] = {
            "type": "url",
            "url": "https://cdn.umbralbim.io/heroes/canonical.jpg",
        }
        mock_get_page.return_value = page
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())

        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222", "telegram_confirmed": True}
        )

        assert result["ok"] is True
        body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert body["hero_image_url"] == (
            "https://cdn.umbralbim.io/heroes/canonical.jpg"
        )
        visual_gate = result["gates"]["visual_asset"]
        assert visual_gate["selection_property_present"] is False
        assert visual_gate["reason"] == "legacy_compatible"
        assert visual_gate["hero_source"] == "visual_asset_url"

    @pytest.mark.parametrize(
        ("selection", "expected_reason"),
        [
            (None, "selection_missing"),
            ("Pendiente", "selection_pending"),
            ("Regenerar", "regeneration_requested"),
        ],
    )
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_visual_gate_blocks_unready_selection(
        self,
        mock_get_page,
        mock_urlopen,
        selection,
        expected_reason,
    ):
        page = _notion_page()
        page["properties"]["Selección imagen"] = {
            "type": "select",
            "select": {"name": selection} if selection is not None else None,
        }
        mock_get_page.return_value = page

        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222"}
        )

        assert result["ok"] is False
        assert result["error"] == "visual_asset_not_ready"
        assert result["would_publish"] is False
        assert result["gates"]["visual_asset"]["reason"] == expected_reason
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_visual_gate_blocks_selected_alt_without_url(
        self, mock_get_page, mock_urlopen
    ):
        page = _notion_page()
        page["properties"].update(
            {
                "Selección imagen": {
                    "type": "select",
                    "select": {"name": "Alt 2"},
                },
                "Estado imagen": {
                    "type": "select",
                    "select": {"name": "Seleccionada"},
                },
            }
        )
        mock_get_page.return_value = page

        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222"}
        )

        assert result["error"] == "visual_asset_not_ready"
        visual_gate = result["gates"]["visual_asset"]
        assert visual_gate["reason"] == "selected_alt_url_missing"
        assert visual_gate["selected_property"] == "imagen_alt_2_url"
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_visual_gate_blocks_alt_until_state_is_selected(
        self, mock_get_page, mock_urlopen
    ):
        page = _notion_page()
        page["properties"].update(
            {
                "Selección imagen": {
                    "type": "select",
                    "select": {"name": "Alt 2"},
                },
                "imagen_alt_2_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/heroes/alt-2.jpg",
                },
                "Estado imagen": {
                    "type": "select",
                    "select": {"name": "Listo para selección"},
                },
            }
        )
        mock_get_page.return_value = page

        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222"}
        )

        assert result["error"] == "visual_asset_not_ready"
        assert result["gates"]["visual_asset"]["reason"] == (
            "image_state_not_selected"
        )
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_visual_gate_blocks_canonical_url_mismatch(
        self, mock_get_page, mock_urlopen
    ):
        page = _notion_page()
        page["properties"].update(
            {
                "Selección imagen": {
                    "type": "select",
                    "select": {"name": "Alt 2"},
                },
                "imagen_alt_2_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/heroes/alt-2.jpg",
                },
                "Estado imagen": {
                    "type": "select",
                    "select": {"name": "Seleccionada"},
                },
                "Visual asset URL": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/heroes/stale-alt-1.jpg",
                },
            }
        )
        mock_get_page.return_value = page

        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222"}
        )

        assert result["error"] == "visual_asset_not_ready"
        visual_gate = result["gates"]["visual_asset"]
        assert visual_gate["reason"] == "canonical_url_mismatch"
        assert visual_gate["selected_url"].endswith("/alt-2.jpg")
        assert visual_gate["canonical_url"].endswith("/stale-alt-1.jpg")
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_visual_gate_uses_matching_canonical_url(
        self, mock_get_page, mock_urlopen
    ):
        selected_url = "https://cdn.umbralbim.io/heroes/alt-2.jpg"
        page = _notion_page()
        page["properties"].update(
            {
                "Selección imagen": {
                    "type": "select",
                    "select": {"name": "Alt 2"},
                },
                "imagen_alt_2_url": {"type": "url", "url": selected_url},
                "Estado imagen": {
                    "type": "select",
                    "select": {"name": "Seleccionada"},
                },
                "Visual asset URL": {"type": "url", "url": selected_url},
            }
        )
        mock_get_page.return_value = page
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())

        result = handle_web_publish_editorial_post(
            {"notion_page_id": "22222222-2222-2222-2222-222222222222", "telegram_confirmed": True}
        )

        assert result["ok"] is True
        body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert body["hero_image_url"] == selected_url
        visual_gate = result["gates"]["visual_asset"]
        assert visual_gate["reason"] == "selected_canonical"
        assert visual_gate["hero_source"] == "visual_asset_url"


# ======================================================================
# Task B — post-publish RAG indexing hook
# ======================================================================


class TestRagHook:
    @patch("worker.tasks.rag.handle_rag_index")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_indexes_on_success(self, mock_urlopen, mock_rag, monkeypatch):
        _set_rag_env(monkeypatch)
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        mock_rag.return_value = {"indexed": 1, "chunks": 2, "documents": 1, "errors": []}

        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )

        assert result["ok"] is True
        assert result["rag_indexed"] is True
        assert result["rag_index_name"] == "umbral-editorial"
        assert result["rag_chunks"] == 2

        mock_rag.assert_called_once()
        rag_input = mock_rag.call_args[0][0]
        assert rag_input["index_name"] == "umbral-editorial"
        doc = rag_input["documents"][0]
        assert doc["content"] == _authorized_payload()["body_markdown"]
        assert doc["source_type"] == "editorial_blog"
        assert doc["source"] == result["published_url"]

    @patch("worker.tasks.rag.handle_rag_index")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_skipped_when_env_missing(self, mock_urlopen, mock_rag):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )

        assert result["ok"] is True  # publish stays ok
        assert result["rag_indexed"] is False
        assert result["rag_skipped_reason"].startswith("missing_env:")
        assert "AZURE_SEARCH_ENDPOINT" in result["rag_skipped_reason"]
        mock_rag.assert_not_called()

    @patch("worker.tasks.rag.handle_rag_index")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_skip_rag_index_flag(self, mock_urlopen, mock_rag, monkeypatch):
        _set_rag_env(monkeypatch)
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "skip_rag_index": True, "telegram_confirmed": True}
        )
        assert result["ok"] is True
        assert result["rag_indexed"] is False
        assert result["rag_skipped_reason"] == "skip_rag_index"
        mock_rag.assert_not_called()

    @patch("worker.tasks.rag.handle_rag_index")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_index_after_publish_false(self, mock_urlopen, mock_rag, monkeypatch):
        _set_rag_env(monkeypatch)
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "index_after_publish": False, "telegram_confirmed": True}
        )
        assert result["rag_indexed"] is False
        assert result["rag_skipped_reason"] == "index_after_publish_false"
        mock_rag.assert_not_called()

    @patch("worker.tasks.rag.handle_rag_index")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_custom_index_name(self, mock_urlopen, mock_rag, monkeypatch):
        _set_rag_env(monkeypatch)
        monkeypatch.setenv("EDITORIAL_RAG_INDEX_NAME", "umbral-editorial-staging")
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        mock_rag.return_value = {"indexed": 1, "chunks": 1, "documents": 1, "errors": []}
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )
        assert result["rag_index_name"] == "umbral-editorial-staging"
        assert mock_rag.call_args[0][0]["index_name"] == "umbral-editorial-staging"

    @patch("worker.tasks.rag.handle_rag_index")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_rag_error_keeps_publish_ok(self, mock_urlopen, mock_rag, monkeypatch):
        _set_rag_env(monkeypatch)
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        mock_rag.side_effect = RuntimeError("search down")
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is True  # publish already happened; RAG is best-effort
        assert result["rag_indexed"] is False
        assert "search down" in result["rag_error"]

    @patch("worker.tasks.rag.handle_rag_index")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_dry_run_skips_rag(self, mock_urlopen, mock_rag, monkeypatch):
        _set_rag_env(monkeypatch)
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "dry_run": True, "telegram_confirmed": True}
        )
        assert result["rag_indexed"] is False
        assert result["rag_skipped_reason"] == "dry_run"
        mock_rag.assert_not_called()
        mock_urlopen.assert_not_called()


# ======================================================================
# P2.7 / Fila I = B — post-publish RRSS injection hook
# (inject_rrss_after_publish). See
# docs/ops/editorial-rrss-injection-p27-2026-07-23.md.
# ======================================================================


class TestRrssInjectionHook:
    @patch("worker.notion_client.update_page_properties")
    @patch("worker.notion_client.get_page")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_off_by_default_no_injection_attempted(self, mock_urlopen, mock_get_page, mock_update):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is True
        assert "rrss_injection" not in result
        mock_get_page.assert_not_called()
        mock_update.assert_not_called()

    @patch("worker.notion_client.update_page_properties")
    @patch("worker.notion_client.get_page")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_enabled_injects_using_the_just_published_url(self, mock_urlopen, mock_get_page, mock_update):
        mock_urlopen.return_value = FakeHTTPResponse(
            200, _ok_function_body(published_url="https://umbralbim.io/noticias/ia-en-coordinacion-bim")
        )
        mock_get_page.return_value = {
            "id": "pub-1",
            "properties": {
                "Copy LinkedIn": {"type": "rich_text", "rich_text": [{"plain_text": "Un teaser."}]},
                "Copy X": {"type": "rich_text", "rich_text": []},
                "Copy LinkedIn empresa": {"type": "rich_text", "rich_text": []},
                "listo_rrss": {"type": "checkbox", "checkbox": False},
            },
        }

        result = handle_web_publish_editorial_post(
            {
                "payload": _authorized_payload(),
                "telegram_confirmed": True,
                "inject_rrss_after_publish": True,
            }
        )

        assert result["ok"] is True
        assert result["rrss_injection"]["ok"] is True
        assert result["rrss_injection"]["injected_channels"] == ["copy_linkedin"]
        props = mock_update.call_args.kwargs["properties"]
        assert props["Copy LinkedIn"]["rich_text"][0]["text"]["content"].endswith(
            "https://umbralbim.io/noticias/ia-en-coordinacion-bim"
        )
        assert props["listo_rrss"] == {"checkbox": True}

    @patch("worker.notion_client.update_page_properties")
    @patch("worker.notion_client.get_page")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_injection_failure_never_fails_the_publish(self, mock_urlopen, mock_get_page, mock_update):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        mock_get_page.side_effect = RuntimeError("Notion down")

        result = handle_web_publish_editorial_post(
            {
                "payload": _authorized_payload(),
                "telegram_confirmed": True,
                "inject_rrss_after_publish": True,
            }
        )

        assert result["ok"] is True  # publish already happened; injection is best-effort
        assert result["rrss_injection"]["ok"] is False

    @patch("worker.notion_client.update_page_properties")
    @patch("worker.notion_client.get_page")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_not_attempted_on_blocked_publish(self, mock_urlopen, mock_get_page, mock_update):
        # telegram_confirmed omitted -> blocked before ever reaching the hook.
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "inject_rrss_after_publish": True}
        )
        assert result["ok"] is False
        assert "rrss_injection" not in result
        mock_get_page.assert_not_called()
        mock_urlopen.assert_not_called()

    @patch("worker.notion_client.update_page_properties")
    @patch("worker.notion_client.get_page")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_not_attempted_on_dry_run(self, mock_urlopen, mock_get_page, mock_update):
        result = handle_web_publish_editorial_post(
            {
                "payload": _authorized_payload(),
                "telegram_confirmed": True,
                "dry_run": True,
                "inject_rrss_after_publish": True,
            }
        )
        assert result["ok"] is True
        assert "rrss_injection" not in result
        mock_get_page.assert_not_called()
        mock_urlopen.assert_not_called()


# ======================================================================
# Deliverable F — visual asset resolution (Publicaciones schema v2)
# ======================================================================


class TestVisualAssets:
    def test_missing_properties_returns_empty(self):
        assert resolve_visual_asset_urls({}) == {}

    def test_no_selection_returns_empty_even_with_candidates(self):
        page = {
            "properties": {
                "imagen_alt_1_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/alt-1.jpg",
                }
            }
        }

        assert resolve_visual_asset_urls(page) == {}

    def test_pending_selection_returns_empty(self):
        page = {
            "properties": {
                "Selección imagen": {
                    "type": "select",
                    "select": {"name": "Pendiente"},
                },
                "imagen_alt_1_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/alt-1.jpg",
                },
            }
        }

        assert resolve_visual_asset_urls(page) == {}

    def test_null_selection_returns_empty(self):
        page = {
            "properties": {
                "Selección imagen": {"type": "select", "select": None},
                "imagen_alt_1_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/alt-1.jpg",
                },
            }
        }

        assert resolve_visual_asset_urls(page) == {}

    def test_resolve_visual_asset_urls_from_selection(self):
        page = {
            "properties": {
                "Selección imagen": {
                    "type": "select",
                    "select": {"name": "Alt 2"},
                },
                "imagen_alt_1_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/alt-1.jpg",
                },
                "imagen_alt_2_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/alt-2.jpg",
                },
                "imagen_alt_3_url": {"type": "url", "url": None},
            }
        }

        assert resolve_visual_asset_urls(page) == {
            "hero_image_url": "https://cdn.umbralbim.io/alt-2.jpg",
            "imagen_alt_1_url": "https://cdn.umbralbim.io/alt-1.jpg",
            "imagen_alt_2_url": "https://cdn.umbralbim.io/alt-2.jpg",
        }

    def test_multiple_selection_uses_first_resolvable_alt_in_order(self):
        page = {
            "properties": {
                "imagen_alt_1_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/alt-1.jpg",
                },
                "imagen_alt_3_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/alt-3.jpg",
                },
            }
        }

        assert resolve_visual_asset_urls(
            page, ["Pendiente", "Alt 2", "Alt 3", "Alt 1"]
        ) == {
            "hero_image_url": "https://cdn.umbralbim.io/alt-3.jpg",
            "imagen_alt_1_url": "https://cdn.umbralbim.io/alt-1.jpg",
            "imagen_alt_3_url": "https://cdn.umbralbim.io/alt-3.jpg",
        }

    def test_selected_url_property_absent_returns_empty(self):
        page = {
            "properties": {
                "Selección imagen": {
                    "type": "select",
                    "select": {"name": "Alt 2"},
                },
                "imagen_alt_1_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/alt-1.jpg",
                },
            }
        }

        assert resolve_visual_asset_urls(page) == {}

    def test_sin_imagen_returns_empty_without_candidates(self):
        page = {
            "properties": {
                "Selección imagen": {
                    "type": "select",
                    "select": {"name": "Sin imagen"},
                },
                "imagen_alt_1_url": {
                    "type": "url",
                    "url": "https://cdn.umbralbim.io/alt-1.jpg",
                },
            }
        }

        assert resolve_visual_asset_urls(page) == {}


# ======================================================================
# N1 / B1 — publication_id -> notion_page_id resolution (Telegram bridge)
# ======================================================================


def _pub_lookup(
    publication_id: str = "shortlist-abc",
    page_id: str = "22222222-2222-2222-2222-222222222222",
    count: int = 1,
) -> Dict[str, Any]:
    """Fake worker.notion_client.read_database result for the resolver."""
    item = {
        "page_id": page_id,
        "title": "Post desde Notion",
        "properties": {"publication_id": publication_id},
    }
    return {"items": [dict(item) for _ in range(count)], "count": count}


class TestPublicationIdResolution:
    """N1: the Worker resolves publication_id -> notion_page_id read-only,
    fail-closed, and never lets that path relax the D3 gate."""

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    @patch("worker.notion_client.read_database")
    def test_resolves_and_publishes_dry_run(
        self, mock_read_db, mock_get_page, mock_urlopen, monkeypatch
    ):
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.return_value = _pub_lookup("shortlist-abc")
        mock_get_page.return_value = _notion_page()

        result = handle_web_publish_editorial_post(
            {
                "publication_id": "shortlist-abc",
                "dry_run": True,
                "telegram_confirmed": True,
            }
        )

        assert result["ok"] is True
        assert result["would_publish"] is True
        assert result["source"] == "notion"
        assert result["publication_id"] == "shortlist-abc"
        mock_read_db.assert_called_once_with(
            "db-pubs-1",
            max_items=5,
            filter={
                "property": "publication_id",
                "rich_text": {"equals": "shortlist-abc"},
            },
        )
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    @patch("worker.notion_client.read_database")
    def test_resolution_still_enforces_d3_gate(
        self, mock_read_db, mock_get_page, mock_urlopen, monkeypatch
    ):
        # publication_id resolves to a fully authorized page, but without
        # telegram_confirmed the D3 gate must still block -- resolution is not a
        # bypass.
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.return_value = _pub_lookup("shortlist-abc")
        mock_get_page.return_value = _notion_page()

        result = handle_web_publish_editorial_post(
            {"publication_id": "shortlist-abc", "dry_run": True}
        )

        assert result["ok"] is False
        assert result["error"] == "telegram_confirmation_missing"
        assert result["would_publish"] is False
        assert result["publication_id"] == "shortlist-abc"
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    @patch("worker.notion_client.read_database")
    def test_not_found_fails_closed(
        self, mock_read_db, mock_get_page, mock_urlopen, monkeypatch
    ):
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.return_value = {"items": [], "count": 0}

        result = handle_web_publish_editorial_post(
            {"publication_id": "shortlist-missing", "telegram_confirmed": True}
        )

        assert result["ok"] is False
        assert result["error"] == "publication_id_not_found"
        assert result["would_publish"] is False
        assert result["source"] == "publication_id"
        assert result["publication_id"] == "shortlist-missing"
        mock_get_page.assert_not_called()
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.read_database")
    def test_ambiguous_fails_closed(self, mock_read_db, mock_urlopen, monkeypatch):
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.return_value = _pub_lookup("shortlist-dup", count=2)

        result = handle_web_publish_editorial_post(
            {"publication_id": "shortlist-dup", "telegram_confirmed": True}
        )

        assert result["ok"] is False
        assert result["error"] == "publication_id_ambiguous"
        assert result["match_count"] == 2
        assert result["would_publish"] is False
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.read_database")
    def test_db_not_configured_fails_closed(
        self, mock_read_db, mock_urlopen, monkeypatch
    ):
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "")

        result = handle_web_publish_editorial_post(
            {"publication_id": "shortlist-abc", "telegram_confirmed": True}
        )

        assert result["ok"] is False
        assert result["error"] == "publicaciones_db_not_configured"
        assert result["would_publish"] is False
        mock_read_db.assert_not_called()
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.read_database")
    def test_lookup_error_fails_closed(self, mock_read_db, mock_urlopen, monkeypatch):
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.side_effect = RuntimeError("Notion API error (503)")

        result = handle_web_publish_editorial_post(
            {"publication_id": "shortlist-abc", "telegram_confirmed": True}
        )

        assert result["ok"] is False
        assert result["error"] == "publication_id_lookup_error"
        assert result["would_publish"] is False
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    @patch("worker.notion_client.read_database")
    def test_notion_page_id_takes_precedence(
        self, mock_read_db, mock_get_page, mock_urlopen, monkeypatch
    ):
        # Both ids present -> notion_page_id wins, the resolver is never called.
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_get_page.return_value = _notion_page()

        result = handle_web_publish_editorial_post(
            {
                "notion_page_id": "22222222-2222-2222-2222-222222222222",
                "publication_id": "shortlist-abc",
                "dry_run": True,
                "telegram_confirmed": True,
            }
        )

        assert result["ok"] is True
        assert result["source"] == "notion"
        assert "publication_id" not in result
        mock_read_db.assert_not_called()
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.read_database")
    def test_payload_takes_precedence(self, mock_read_db, mock_urlopen, monkeypatch):
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")

        result = handle_web_publish_editorial_post(
            {
                "payload": _authorized_payload(),
                "publication_id": "shortlist-abc",
                "dry_run": True,
                "telegram_confirmed": True,
            }
        )

        assert result["ok"] is True
        assert result["source"] == "payload"
        mock_read_db.assert_not_called()
        mock_urlopen.assert_not_called()

    # --- direct resolver unit tests -----------------------------------------

    def test_resolver_empty_id(self):
        assert _resolve_publication_id_to_page_id("  ", {}) == {
            "ok": False,
            "error": "publication_id_empty",
        }

    @patch("worker.notion_client.read_database")
    def test_resolver_defensive_reverify_mismatch(self, mock_read_db, monkeypatch):
        # If Notion ever returns a row whose flattened publication_id doesn't
        # actually equal the query, the defensive re-check drops it -> not_found.
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.return_value = _pub_lookup("shortlist-OTHER")

        result = _resolve_publication_id_to_page_id(
            "shortlist-abc", {"publication_id": "publication_id"}
        )

        assert result == {"ok": False, "error": "publication_id_not_found"}

    @patch("worker.notion_client.read_database")
    def test_resolver_no_page_id(self, mock_read_db, monkeypatch):
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.return_value = _pub_lookup("shortlist-abc", page_id="")

        result = _resolve_publication_id_to_page_id("shortlist-abc", {})

        assert result == {"ok": False, "error": "publication_id_no_page_id"}

    @patch("worker.notion_client.read_database")
    def test_resolver_honors_prop_map_override(self, mock_read_db, monkeypatch):
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.return_value = {
            "items": [
                {"page_id": "p1", "properties": {"pub_id_custom": "shortlist-abc"}}
            ],
            "count": 1,
        }

        result = _resolve_publication_id_to_page_id(
            "shortlist-abc", {"publication_id": "pub_id_custom"}
        )

        assert result == {"ok": True, "notion_page_id": "p1"}
        mock_read_db.assert_called_once_with(
            "db-pubs-1",
            max_items=5,
            filter={
                "property": "pub_id_custom",
                "rich_text": {"equals": "shortlist-abc"},
            },
        )


# ======================================================================
# D3 gates BEFORE _normalize_payload
#
# Smoke B1 / CAND-001 replay: "ok publica <publication_id>" resolved fine, but
# the row was a Borrador (autorizar_publicacion=false, Slug empty) and the
# handler raised ValueError over the missing slug *before* reading the gates —
# so the worker marked the task failed and the exception notifier dropped a
# "Tarea fallida" comment in Control Room for an ordinary not-authorized state.
#
# Contract now: gates first, structured refusals, no raise on any gate state or
# unfinished row. Malformed-but-present input still raises (see test_bad_slug).
# ======================================================================


def _borrador_page(
    *,
    authorized: bool = False,
    approved: bool = False,
    slug: str = "",
    title: str = "Candidato sin publicar",
    body: str = "",
) -> Dict[str, Any]:
    """A Publicaciones row that is NOT publish-ready: empty Slug/Copy Blog."""
    def _rt(value: str) -> Dict[str, Any]:
        return {"type": "rich_text", "rich_text": [{"plain_text": value}] if value else []}

    return {
        "id": "33333333-3333-3333-3333-333333333333",
        "properties": {
            "Title": {"type": "title", "title": [{"plain_text": title}]},
            "Slug": _rt(slug),
            "Copy Blog": _rt(body),
            "autorizar_publicacion": {"type": "checkbox", "checkbox": authorized},
            "aprobado_contenido": {"type": "checkbox", "checkbox": approved},
        },
    }


class TestGatesBeforeNormalize:
    # --- gates block first, even with nothing to normalize -----------------

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    @patch("worker.notion_client.read_database")
    def test_cand001_publication_id_borrador_blocks_without_raising(
        self, mock_read_db, mock_get_page, mock_urlopen, monkeypatch
    ):
        # The exact smoke failure: resolver OK -> page_id, gates false, no slug.
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.return_value = _pub_lookup("shortlist-cand-001")
        mock_get_page.return_value = _borrador_page()

        result = handle_web_publish_editorial_post(
            {"publication_id": "shortlist-cand-001", "telegram_confirmed": True}
        )

        assert result["ok"] is False
        assert result["error"] == "publication_not_authorized"
        assert result["would_publish"] is False
        assert result["source"] == "notion"
        assert result["slug"] is None  # slug is optional on the gate path
        assert result["notion_page_id"] == "33333333-3333-3333-3333-333333333333"
        assert result["publication_id"] == "shortlist-cand-001"
        assert result["gates"]["autorizar_publicacion"] is False
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_notion_source_borrador_blocks_without_raising(
        self, mock_get_page, mock_urlopen
    ):
        mock_get_page.return_value = _borrador_page()

        result = handle_web_publish_editorial_post(
            {
                "notion_page_id": "33333333-3333-3333-3333-333333333333",
                "telegram_confirmed": True,
            }
        )

        assert result["ok"] is False
        assert result["error"] == "publication_not_authorized"
        assert result["slug"] is None
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_payload_source_unauthorized_without_slug_blocks(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {
                "payload": {"autorizar_publicacion": False, "title": "Borrador"},
                "telegram_confirmed": True,
            }
        )

        assert result["ok"] is False
        assert result["error"] == "publication_not_authorized"
        assert result["source"] == "payload"
        assert result["slug"] is None
        assert result["notion_page_id"] is None
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_visual_gate_blocks_before_normalize_with_empty_slug(
        self, mock_get_page, mock_urlopen
    ):
        page = _borrador_page(authorized=True, approved=True)
        page["properties"]["Selección imagen"] = {
            "type": "select",
            "select": {"name": "Pendiente"},
        }
        mock_get_page.return_value = page

        result = handle_web_publish_editorial_post(
            {
                "notion_page_id": "33333333-3333-3333-3333-333333333333",
                "telegram_confirmed": True,
            }
        )

        assert result["ok"] is False
        assert result["error"] == "visual_asset_not_ready"
        assert result["gates"]["visual_asset"]["reason"] == "selection_pending"
        assert result["slug"] is None
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_telegram_gate_blocks_before_normalize_with_empty_slug(
        self, mock_get_page, mock_urlopen
    ):
        mock_get_page.return_value = _borrador_page(authorized=True, approved=True)

        result = handle_web_publish_editorial_post(
            {"notion_page_id": "33333333-3333-3333-3333-333333333333"}
        )

        assert result["ok"] is False
        assert result["error"] == "telegram_confirmation_missing"
        assert result["gates"]["telegram_confirmed"] is False
        assert result["slug"] is None
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_authorization_is_reported_before_missing_fields(
        self, mock_get_page, mock_urlopen
    ):
        # Both are wrong (no authorization AND no content). The gate answer is
        # the actionable one for David, so it must win.
        mock_get_page.return_value = _borrador_page()

        result = handle_web_publish_editorial_post(
            {
                "notion_page_id": "33333333-3333-3333-3333-333333333333",
                "telegram_confirmed": True,
            }
        )

        assert result["error"] == "publication_not_authorized"
        assert "missing_fields" not in result
        mock_urlopen.assert_not_called()

    # --- gates open, content still missing -> structured, not a raise ------

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_gates_true_empty_slug_returns_missing_required_fields(
        self, mock_get_page, mock_urlopen
    ):
        mock_get_page.return_value = _borrador_page(
            authorized=True, approved=True, body="## Cuerpo\n\nContenido."
        )

        result = handle_web_publish_editorial_post(
            {
                "notion_page_id": "33333333-3333-3333-3333-333333333333",
                "telegram_confirmed": True,
            }
        )

        assert result["ok"] is False
        assert result["error"] == "missing_required_fields"
        assert result["missing_fields"] == ["slug"]
        assert result["would_publish"] is False
        assert result["source"] == "notion"
        assert result["slug"] is None
        assert result["notion_page_id"] == "33333333-3333-3333-3333-333333333333"
        assert result["gates"]["autorizar_publicacion"] is True
        assert result["gates"]["telegram_confirmed"] is True
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_missing_fields_lists_every_empty_field(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {
                "payload": {"autorizar_publicacion": True, "aprobado_contenido": True},
                "telegram_confirmed": True,
            }
        )

        assert result["error"] == "missing_required_fields"
        assert result["missing_fields"] == [
            "slug",
            "title",
            "body_markdown",
            "notion_page_id",
        ]
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_missing_fields_blocks_dry_run_too(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {
                "payload": _authorized_payload(slug=""),
                "telegram_confirmed": True,
                "dry_run": True,
            }
        )

        assert result["ok"] is False
        assert result["error"] == "missing_required_fields"
        assert result["missing_fields"] == ["slug"]
        assert "payload" not in result  # nothing was built for the function
        mock_urlopen.assert_not_called()

    @patch("worker.notion_client.update_page_properties")
    @patch("worker.tasks.rag.handle_rag_index")
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_missing_fields_never_triggers_a_side_effect(
        self, mock_urlopen, mock_rag, mock_update
    ):
        result = handle_web_publish_editorial_post(
            {
                "payload": _authorized_payload(slug=""),
                "telegram_confirmed": True,
                "write_back_to_notion": True,
                "inject_rrss_after_publish": True,
            }
        )

        assert result["error"] == "missing_required_fields"
        mock_urlopen.assert_not_called()
        mock_rag.assert_not_called()
        mock_update.assert_not_called()

    # --- gates open + complete row -> the normal path is untouched ---------

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_gates_true_valid_slug_dry_run_succeeds(self, mock_get_page, mock_urlopen):
        mock_get_page.return_value = _notion_page()

        result = handle_web_publish_editorial_post(
            {
                "notion_page_id": "22222222-2222-2222-2222-222222222222",
                "telegram_confirmed": True,
                "dry_run": True,
            }
        )

        assert result["ok"] is True
        assert result["would_publish"] is True
        assert result["slug"] == "post-desde-notion"
        assert "missing_fields" not in result
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    @patch("worker.notion_client.read_database")
    def test_publication_id_gates_true_valid_slug_publishes(
        self, mock_read_db, mock_get_page, mock_urlopen, monkeypatch
    ):
        # The happy B1 leg: same entry point as CAND-001, but a ready row.
        monkeypatch.setattr("worker.config.NOTION_PUBLICACIONES_DB_ID", "db-pubs-1")
        mock_read_db.return_value = _pub_lookup("shortlist-ready")
        mock_get_page.return_value = _notion_page()
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())

        result = handle_web_publish_editorial_post(
            {"publication_id": "shortlist-ready", "telegram_confirmed": True}
        )

        assert result["ok"] is True
        assert result["published"] is True
        assert result["publication_id"] == "shortlist-ready"
        mock_urlopen.assert_called_once()


class TestMissingRequiredFieldsHelper:
    def test_complete_payload_reports_nothing(self):
        assert _missing_required_fields(_authorized_payload()) == []

    def test_reports_in_declared_field_order(self):
        assert _missing_required_fields({}) == [
            "slug",
            "title",
            "body_markdown",
            "notion_page_id",
        ]

    def test_whitespace_only_body_counts_as_missing(self):
        assert _missing_required_fields(_authorized_payload(body_markdown="   \n")) == [
            "body_markdown"
        ]

    def test_non_dict_reports_everything(self):
        assert _missing_required_fields(None) == [
            "slug",
            "title",
            "body_markdown",
            "notion_page_id",
        ]


# ======================================================================
# Hero asset — a Drive share link is a viewer page, never an image
# ======================================================================

DRIVE_HERO = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/view?usp=drivesdk"
_PNG = b"\x89PNG\r\n\x1a\n" + b"fake-bytes"


def _drive_hero_payload(**overrides: Any) -> Dict[str, Any]:
    return _authorized_payload(hero_image_url=DRIVE_HERO, **overrides)


class TestHeroAsset:
    """The blog never receives a Drive URL as its hero, and never silently
    publishes without one: it either ships the downloaded PNG or declines."""

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_drive_hero_without_asset_sink_declines_before_network(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {"payload": _drive_hero_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is False
        assert result["error"] == "hero_asset_sink_unavailable"
        assert result["would_publish"] is False
        assert result["hero_asset"]["input_hero"] == "drive"
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_publish_without_hero_strips_the_drive_url(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {
                "payload": _drive_hero_payload(),
                "telegram_confirmed": True,
                "publish_without_hero": True,
            }
        )
        assert result["ok"] is True
        sent = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert sent["hero_image_url"] == ""
        assert "drive.google.com" not in json.dumps(sent)
        assert result["hero_asset"]["stripped"] is True
        assert result["hero_asset"]["stripped_reason"] == "drive_hero_without_asset_sink"

    @patch("worker.tasks.google_drive.download_drive_png", return_value=_PNG)
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_asset_sink_ships_the_png_and_never_the_link(
        self, mock_urlopen, mock_download, monkeypatch
    ):
        monkeypatch.setenv("EDITORIAL_BLOG_ASSET_UPLOAD", "true")
        hero_url = "https://cdn.umbralbim.io/editorial-posts/assets/ia-en-coordinacion-bim.png"
        mock_urlopen.return_value = FakeHTTPResponse(
            200, _ok_function_body(hero_image_url=hero_url)
        )
        result = handle_web_publish_editorial_post(
            {"payload": _drive_hero_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is True
        mock_download.assert_called_once_with(DRIVE_HERO)
        sent = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert sent["hero_image_url"] == ""
        assert "drive.google.com" not in json.dumps(sent)
        assert base64.b64decode(sent["hero_image_png_base64"]) == _PNG
        assert result["hero_image_url"] == hero_url
        assert result["hero_asset"]["download"] == "ok"

    @patch(
        "worker.tasks.google_drive.download_drive_png",
        side_effect=ValueError("Downloaded editorial hero is not a PNG"),
    )
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_download_failure_is_explicit_not_silent(
        self, mock_urlopen, _mock_download, monkeypatch
    ):
        monkeypatch.setenv("EDITORIAL_BLOG_ASSET_UPLOAD", "1")
        result = handle_web_publish_editorial_post(
            {"payload": _drive_hero_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is False
        assert result["error"] == "hero_image_download_failed"
        assert result["would_publish"] is False
        assert "not a PNG" in result["hero_asset"]["download_error"]
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_public_https_hero_is_forwarded_untouched(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {"payload": _authorized_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is True
        sent = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert sent["hero_image_url"] == "https://cdn.umbralbim.io/heroes/ia-bim.jpg"
        assert "hero_image_png_base64" not in sent

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_dry_run_previews_the_decline(self, mock_urlopen):
        result = handle_web_publish_editorial_post(
            {
                "payload": _drive_hero_payload(),
                "telegram_confirmed": True,
                "dry_run": True,
            }
        )
        assert result["ok"] is False
        assert result["error"] == "hero_asset_sink_unavailable"
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.google_drive.download_drive_png", return_value=_PNG)
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_dry_run_verifies_the_hero_without_shipping_it(
        self, mock_urlopen, mock_download, monkeypatch
    ):
        monkeypatch.setenv("EDITORIAL_BLOG_ASSET_UPLOAD", "true")
        result = handle_web_publish_editorial_post(
            {
                "payload": _drive_hero_payload(),
                "telegram_confirmed": True,
                "dry_run": True,
            }
        )
        assert result["ok"] is True
        assert result["hero_asset"]["download"] == "ok"
        mock_download.assert_called_once_with(DRIVE_HERO)
        # Verified, not shipped: the readiness check performs no publish call
        # and never carries the image in its preview.
        assert "hero_image_png_base64" not in result["payload"]
        mock_urlopen.assert_not_called()

    @patch(
        "worker.tasks.google_drive.download_drive_png",
        side_effect=ValueError("Google Drive download failed for the editorial hero"),
    )
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_dry_run_surfaces_a_broken_hero(self, mock_urlopen, _mock_download, monkeypatch):
        monkeypatch.setenv("EDITORIAL_BLOG_ASSET_UPLOAD", "true")
        result = handle_web_publish_editorial_post(
            {
                "payload": _drive_hero_payload(),
                "telegram_confirmed": True,
                "dry_run": True,
            }
        )
        assert result["ok"] is False
        assert result["error"] == "hero_image_download_failed"
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.google_drive.download_drive_png", return_value=_PNG)
    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_function_that_ignores_the_asset_is_not_a_success(
        self, mock_urlopen, _mock_download, monkeypatch
    ):
        # A build without the assets route drops the unknown key and answers 200.
        monkeypatch.setenv("EDITORIAL_BLOG_ASSET_UPLOAD", "true")
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {"payload": _drive_hero_payload(), "telegram_confirmed": True}
        )
        assert result["ok"] is False
        assert result["error"] == "hero_asset_not_stored"
        assert result["published"] is True

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_legacy_http_hero_keeps_publishing(self, mock_urlopen):
        # Only Drive links take the new path; a legacy http hero is untouched.
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        result = handle_web_publish_editorial_post(
            {
                "payload": _authorized_payload(hero_image_url="http://cdn.example.com/h.jpg"),
                "telegram_confirmed": True,
            }
        )
        assert result["ok"] is True
        sent = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert sent["hero_image_url"] == "http://cdn.example.com/h.jpg"

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    @patch("worker.notion_client.get_page")
    def test_notion_alt_selection_reaches_the_hero_decline(
        self, mock_get_page, mock_urlopen
    ):
        # End to end from the v2 visual gate: Alt 4 resolves to the Drive
        # canonical, which must never be forwarded to the blog.
        page = _notion_page()
        page["properties"].update(
            {
                "Selección imagen": {"type": "select", "select": {"name": "Alt 4"}},
                "Estado imagen": {"type": "select", "select": {"name": "Seleccionada"}},
                "imagen_alt_4_url": {"type": "url", "url": DRIVE_HERO},
                "Visual asset URL": {"type": "url", "url": DRIVE_HERO},
            }
        )
        mock_get_page.return_value = page
        result = handle_web_publish_editorial_post(
            {
                "notion_page_id": "22222222-2222-2222-2222-222222222222",
                "telegram_confirmed": True,
            }
        )
        assert result["ok"] is False
        assert result["error"] == "hero_asset_sink_unavailable"
        assert result["gates"]["visual_asset"]["ready"] is True
        mock_urlopen.assert_not_called()

    def test_worker_and_function_share_the_same_png_cap(self):
        # Cross-process contract: the worker must not send what the function
        # rejects. Both constants live in different deployables.
        import re as _re
        from pathlib import Path as _Path

        from worker.tasks.google_drive import MAX_EDITORIAL_HERO_PNG_BYTES

        source = _Path("functions/editorial-publish/function_app.py").read_text(
            encoding="utf-8"
        )
        match = _re.search(r"MAX_HERO_PNG_BYTES = (\d+) \* 1024 \* 1024", source)
        assert match, "function_app.py no longer declares MAX_HERO_PNG_BYTES"
        assert int(match.group(1)) * 1024 * 1024 == MAX_EDITORIAL_HERO_PNG_BYTES

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_body_markdown_is_forwarded_verbatim(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_function_body())
        body = (
            "## Uno\n\nTexto.\n\n> Una cita.\n\n---\n\n"
            "Fuente: [RICS](https://www.rics.org/x)\n\n"
            "Primero claridad. Después velocidad."
        )
        handle_web_publish_editorial_post(
            {
                "payload": _authorized_payload(body_markdown=body),
                "telegram_confirmed": True,
            }
        )
        sent = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert sent["body_markdown"] == body
        assert "<br" not in sent["body_markdown"]
