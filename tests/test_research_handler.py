"""Unit tests for research.web task handler with provider fallback."""

import pytest

from worker.task_errors import TaskExecutionError
from worker.tasks import research as research_task


def test_handle_research_web_requires_query():
    with pytest.raises(ValueError, match="query"):
        research_task.handle_research_web({})


def test_handle_research_web_re_raises_gemini_not_configured_when_no_fallback(monkeypatch):
    monkeypatch.setattr(
        research_task,
        "search_gemini_google_search",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            TaskExecutionError(
                "research.web unavailable: GOOGLE_API_KEY not configured",
                status_code=503,
                error_code="research_provider_not_configured",
                error_kind="configuration",
                provider=research_task.GEMINI_SEARCH_PROVIDER,
            )
        ),
    )
    monkeypatch.setattr(
        research_task,
        "search_tavily",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            TaskExecutionError(
                "research.web unavailable: TAVILY_API_KEY not configured",
                status_code=503,
                error_code="research_provider_not_configured",
                error_kind="configuration",
                provider=research_task.TAVILY_PROVIDER,
            )
        ),
    )

    with pytest.raises(TaskExecutionError) as exc_info:
        research_task.handle_research_web({"query": "tendencias BIM 2026"})

    err = exc_info.value
    assert err.error_code == "research_provider_not_configured"
    assert err.provider == research_task.GEMINI_SEARCH_PROVIDER


def test_handle_research_web_success_with_gemini(monkeypatch):
    monkeypatch.setattr(
        research_task,
        "search_gemini_google_search",
        lambda *args, **kwargs: [
            {
                "title": "Gemini result",
                "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/example",
                "snippet": "Adopcion BIM en Latinoamerica.",
            }
        ],
    )

    def _unexpected_tavily(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("Tavily fallback should not run when Gemini succeeds")

    monkeypatch.setattr(research_task, "search_tavily", _unexpected_tavily)

    result = research_task.handle_research_web({"query": "BIM LATAM", "count": 3, "search_depth": "advanced"})

    assert result["engine"] == research_task.GEMINI_SEARCH_PROVIDER
    assert result["count"] == 1
    assert result["results"][0]["title"] == "Gemini result"


def test_handle_research_web_falls_back_to_tavily_on_gemini_quota(monkeypatch):
    monkeypatch.setattr(
        research_task,
        "search_gemini_google_search",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            TaskExecutionError(
                "research.web unavailable: Gemini grounded search quota exceeded",
                status_code=503,
                error_code="research_provider_quota_exceeded",
                error_kind="quota",
                provider=research_task.GEMINI_SEARCH_PROVIDER,
                upstream_status=429,
            )
        ),
    )
    monkeypatch.setattr(
        research_task,
        "search_tavily",
        lambda *args, **kwargs: [
            {
                "title": "Tavily result",
                "url": "https://example.com/bim-report",
                "snippet": "La automatizacion e IA lideran las tendencias BIM.",
            }
        ],
    )

    result = research_task.handle_research_web({"query": "BIM LATAM"})

    assert result["engine"] == research_task.TAVILY_PROVIDER
    assert result["fallback_reason"] == "research_provider_quota_exceeded"
    assert result["count"] == 1
    assert result["results"][0]["url"].startswith("https://")
