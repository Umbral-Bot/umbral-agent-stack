"""Unit tests for research.web task handler."""

import json
from io import BytesIO
from unittest.mock import patch
import urllib.error

import pytest

from worker.tasks.research import TAVILY_API_URL, handle_research_web
from worker.task_errors import TaskExecutionError


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_handle_research_web_requires_query():
    with pytest.raises(ValueError, match="query"):
        handle_research_web({})


def test_handle_research_web_requires_tavily_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    with pytest.raises(TaskExecutionError) as exc_info:
        handle_research_web({"query": "tendencias BIM 2026"})

    err = exc_info.value
    assert err.status_code == 503
    assert err.error_code == "research_provider_not_configured"
    assert "TAVILY_API_KEY not configured" in err.detail


def test_handle_research_web_success_with_mocked_tavily(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test-key")
    fake_payload = {
        "results": [
            {
                "title": "Reporte BIM LATAM",
                "url": "https://example.com/bim-report",
                "content": "Adopcion BIM en Latinoamerica.\nCrecimiento sostenido.",
            }
        ]
    }

    with patch(
        "worker.tasks.research.urllib.request.urlopen",
        return_value=_DummyResponse(fake_payload),
    ) as mock_urlopen:
        result = handle_research_web({"query": "BIM LATAM", "count": 3, "search_depth": "advanced"})

    assert result["engine"] == "tavily"
    assert result["count"] == 1
    assert result["results"][0]["title"] == "Reporte BIM LATAM"
    assert result["results"][0]["url"] == "https://example.com/bim-report"
    assert "Adopcion BIM en Latinoamerica." in result["results"][0]["snippet"]

    req = mock_urlopen.call_args.args[0]
    assert req.full_url == TAVILY_API_URL
    body = json.loads(req.data.decode("utf-8"))
    assert body["query"] == "BIM LATAM"
    assert body["max_results"] == 3
    assert body["search_depth"] == "advanced"
    auth = req.headers.get("Authorization") or req.headers.get("authorization")
    assert auth == "Bearer tavily-test-key"


def test_handle_research_web_classifies_quota_error(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test-key")
    error_body = b"{\"detail\":{\"error\":\"This request exceeds your plan's set usage limit.\"}}"
    http_error = urllib.error.HTTPError(
        TAVILY_API_URL,
        432,
        "quota exceeded",
        hdrs=None,
        fp=BytesIO(error_body),
    )

    with patch("worker.tasks.research.urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(TaskExecutionError) as exc_info:
            handle_research_web({"query": "BIM LATAM"})

    err = exc_info.value
    assert err.status_code == 503
    assert err.error_code == "research_provider_quota_exceeded"
    assert err.error_kind == "quota"
    assert err.provider == "tavily"
    assert err.upstream_status == 432


def test_handle_research_web_classifies_timeout(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test-key")

    with patch("worker.tasks.research.urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        with pytest.raises(TaskExecutionError) as exc_info:
            handle_research_web({"query": "BIM LATAM"})

    err = exc_info.value
    assert err.status_code == 504
    assert err.error_code == "research_provider_timeout"
    assert err.retryable is True
