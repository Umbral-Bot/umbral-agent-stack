"""Tests for ADR-010 unpublish support.

No Azure network calls. Worker urllib calls are mocked; Azure Functions runtime
objects are stubbed just enough to load and exercise function_app.py.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.editorial_publish import handle_web_unpublish_editorial_post

PUBLISH_URL = "https://func-umbral-editorial-prod.azurewebsites.net/api/publish-editorial-post"
UNPUBLISH_URL = "https://func-umbral-editorial-prod.azurewebsites.net/api/unpublish-editorial-post"
FUNCTION_DIR = Path(__file__).resolve().parent.parent / "functions" / "editorial-publish"


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


def _ok_unpublish_body(**overrides: Any) -> str:
    body = {
        "ok": True,
        "slug": "criterios-de-aceptacion-antes-de-automatizar-bim",
        "index_updated": True,
        "post_blob_deleted": True,
        "removed_from_index": True,
    }
    body.update(overrides)
    return json.dumps(body)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.setenv("EDITORIAL_BLOG_FUNCTION_URL", PUBLISH_URL)
    monkeypatch.setenv("EDITORIAL_BLOG_FUNCTION_KEY", "fn-key")
    monkeypatch.setenv("WORKER_TOKEN", "worker-token")


class TestWorkerUnpublish:
    def test_registered(self):
        from worker.tasks import TASK_HANDLERS

        assert "web.unpublish_editorial_post" in TASK_HANDLERS
        assert TASK_HANDLERS["web.unpublish_editorial_post"] is handle_web_unpublish_editorial_post

    def test_input_validation(self):
        with pytest.raises(ValueError, match="slug.*notion_page_id"):
            handle_web_unpublish_editorial_post({})
        with pytest.raises(ValueError, match="kebab-case"):
            handle_web_unpublish_editorial_post({"slug": "Bad Slug"})
        with pytest.raises(ValueError, match="delete_post_blob"):
            handle_web_unpublish_editorial_post(
                {"slug": "valid-slug", "delete_post_blob": "true"}
            )

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_dry_run_no_network(self, mock_urlopen):
        result = handle_web_unpublish_editorial_post(
            {"slug": "criterios-de-aceptacion-antes-de-automatizar-bim", "dry_run": True}
        )
        assert result["ok"] is True
        assert result["would_unpublish"] is True
        assert result["payload"] == {
            "delete_post_blob": True,
            "slug": "criterios-de-aceptacion-antes-de-automatizar-bim",
        }
        mock_urlopen.assert_not_called()

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_posts_to_derived_unpublish_url(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_unpublish_body())
        result = handle_web_unpublish_editorial_post(
            {"slug": "criterios-de-aceptacion-antes-de-automatizar-bim"}
        )

        assert result["ok"] is True
        assert result["unpublished"] is True
        assert result["removed_from_index"] is True
        assert result["post_blob_deleted"] is True

        req = mock_urlopen.call_args[0][0]
        assert req.method == "POST"
        assert req.full_url == UNPUBLISH_URL
        assert req.get_header("X-functions-key") == "fn-key"
        assert req.get_header("X-worker-token") == "worker-token"
        body = json.loads(req.data.decode("utf-8"))
        assert body == {
            "delete_post_blob": True,
            "slug": "criterios-de-aceptacion-antes-de-automatizar-bim",
        }

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_accepts_explicit_unpublish_url(self, mock_urlopen, monkeypatch):
        monkeypatch.setenv("EDITORIAL_BLOG_FUNCTION_URL", UNPUBLISH_URL)
        mock_urlopen.return_value = FakeHTTPResponse(200, _ok_unpublish_body())
        handle_web_unpublish_editorial_post({"slug": "valid-slug"})
        assert mock_urlopen.call_args[0][0].full_url == UNPUBLISH_URL

    @patch("worker.tasks.editorial_publish.urllib.request.urlopen")
    def test_can_unpublish_by_notion_page_id(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            200, _ok_unpublish_body(slug="resolved-from-index")
        )
        result = handle_web_unpublish_editorial_post(
            {"notion_page_id": "34b5f443-fb5c-81dd-8338-cb0b46699250"}
        )
        assert result["ok"] is True
        assert result["slug"] == "resolved-from-index"
        body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        assert body["notion_page_id"] == "34b5f443-fb5c-81dd-8338-cb0b46699250"
        assert "slug" not in body


class FakeRequest:
    def __init__(self, payload: Any, headers: Dict[str, str] | None = None):
        self._payload = payload
        self.headers = headers or {}

    def get_json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _install_azure_function_stubs(monkeypatch):
    azure = types.ModuleType("azure")
    functions = types.ModuleType("azure.functions")
    core = types.ModuleType("azure.core")
    exceptions = types.ModuleType("azure.core.exceptions")

    class AuthLevel:
        FUNCTION = "function"

    class FunctionApp:
        def __init__(self, http_auth_level=None):
            self.http_auth_level = http_auth_level

        def route(self, **_kwargs):
            def decorator(fn):
                return fn

            return decorator

    class HttpResponse:
        def __init__(self, body, status_code=200, mimetype=None):
            self.status_code = status_code
            self.mimetype = mimetype
            self._body = body.encode("utf-8") if isinstance(body, str) else body

        def get_body(self):
            return self._body

    class HttpResponseError(Exception):
        def __init__(self, *args, status_code=None, **kwargs):
            super().__init__(*args)
            self.status_code = status_code

    class ResourceModifiedError(HttpResponseError):
        pass

    class ResourceNotFoundError(HttpResponseError):
        pass

    functions.AuthLevel = AuthLevel
    functions.FunctionApp = FunctionApp
    functions.HttpRequest = object
    functions.HttpResponse = HttpResponse
    exceptions.HttpResponseError = HttpResponseError
    exceptions.ResourceModifiedError = ResourceModifiedError
    exceptions.ResourceNotFoundError = ResourceNotFoundError
    azure.functions = functions
    azure.core = core
    core.exceptions = exceptions

    monkeypatch.setitem(sys.modules, "azure", azure)
    monkeypatch.setitem(sys.modules, "azure.functions", functions)
    monkeypatch.setitem(sys.modules, "azure.core", core)
    monkeypatch.setitem(sys.modules, "azure.core.exceptions", exceptions)


@pytest.fixture
def function_app_module(monkeypatch):
    _install_azure_function_stubs(monkeypatch)
    monkeypatch.syspath_prepend(str(FUNCTION_DIR))
    spec = importlib.util.spec_from_file_location(
        "editorial_unpublish_function_app", FUNCTION_DIR / "function_app.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _response_json(resp) -> Dict[str, Any]:
    return json.loads(resp.get_body().decode("utf-8"))


class TestFunctionUnpublish:
    def test_unauthorized(self, function_app_module, monkeypatch):
        monkeypatch.setenv("WORKER_TOKEN", "expected")
        req = FakeRequest({"slug": "valid-slug"}, headers={"x-worker-token": "wrong"})
        resp = function_app_module.unpublish_editorial_post(req)
        assert resp.status_code == 401
        assert _response_json(resp)["error"] == "unauthorized"

    def test_invalid_payload(self, function_app_module, monkeypatch):
        monkeypatch.delenv("WORKER_TOKEN", raising=False)
        req = FakeRequest({"slug": "Bad Slug"})
        resp = function_app_module.unpublish_editorial_post(req)
        assert resp.status_code == 400
        assert _response_json(resp)["error"] == "invalid_payload"

    def test_success_removes_index_and_deletes_blob(self, function_app_module, monkeypatch):
        monkeypatch.delenv("WORKER_TOKEN", raising=False)
        monkeypatch.setattr(function_app_module, "_get_container_client", lambda: object())
        monkeypatch.setattr(function_app_module, "_ensure_container", lambda _client: None)
        monkeypatch.setattr(
            function_app_module,
            "_remove_index_with_retry",
            MagicMock(return_value=(True, {"slug": "valid-slug"})),
        )
        monkeypatch.setattr(function_app_module, "_delete_post", MagicMock(return_value=True))

        resp = function_app_module.unpublish_editorial_post(
            FakeRequest({"slug": "valid-slug"})
        )

        assert resp.status_code == 200
        body = _response_json(resp)
        assert body == {
            "ok": True,
            "slug": "valid-slug",
            "index_updated": True,
            "post_blob_deleted": True,
            "removed_from_index": True,
        }
        function_app_module._delete_post.assert_called_once()

    def test_notion_id_without_match_skips_blob_delete(self, function_app_module, monkeypatch):
        monkeypatch.delenv("WORKER_TOKEN", raising=False)
        monkeypatch.setattr(function_app_module, "_get_container_client", lambda: object())
        monkeypatch.setattr(function_app_module, "_ensure_container", lambda _client: None)
        monkeypatch.setattr(
            function_app_module,
            "_remove_index_with_retry",
            MagicMock(return_value=(False, None)),
        )
        monkeypatch.setattr(function_app_module, "_delete_post", MagicMock())

        resp = function_app_module.unpublish_editorial_post(
            FakeRequest({"notion_page_id": "n1"})
        )

        body = _response_json(resp)
        assert body["ok"] is True
        assert body["index_updated"] is False
        assert body["post_blob_deleted"] == "skipped"
        function_app_module._delete_post.assert_not_called()
