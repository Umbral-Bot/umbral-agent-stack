"""Unit tests for research.web task handler."""

import json
from unittest.mock import patch

import pytest

from worker.tasks.research import TAVILY_API_URL, handle_research_web


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

    with pytest.raises(RuntimeError, match="TAVILY_API_KEY not configured"):
        handle_research_web({"query": "tendencias BIM 2026"})


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
