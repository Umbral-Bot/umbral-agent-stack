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

import json
import urllib.error
from io import BytesIO
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.editorial_publish import (
    _content_hash,
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
    for _k in (*_RAG_ENV, "EDITORIAL_RAG_INDEX_NAME"):
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

    def test_missing_required_fields(self):
        with pytest.raises(ValueError, match="missing required field"):
            handle_web_publish_editorial_post({"payload": {"autorizar_publicacion": True}})

    def test_bad_slug(self):
        with pytest.raises(ValueError, match="slug.*kebab-case"):
            handle_web_publish_editorial_post(
                {"payload": _authorized_payload(slug="Not A Slug")}
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
