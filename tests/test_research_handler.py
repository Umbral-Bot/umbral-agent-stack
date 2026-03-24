"""Unit tests for research.web task handler with provider fallback."""

import pytest

from worker.task_errors import TaskExecutionError
from worker.tasks import research as research_task


def test_handle_research_web_requires_query():
    with pytest.raises(ValueError, match="query"):
        research_task.handle_research_web({})


def test_handle_research_web_re_raises_tavily_not_configured_when_no_fallback(monkeypatch):
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

    with pytest.raises(TaskExecutionError) as exc_info:
        research_task.handle_research_web({"query": "tendencias BIM 2026"})

    err = exc_info.value
    assert err.error_code == "research_provider_not_configured"
    assert err.provider == research_task.TAVILY_PROVIDER


def test_handle_research_web_success_with_tavily(monkeypatch):
    monkeypatch.setattr(
        research_task,
        "search_tavily",
        lambda *args, **kwargs: [
            {
                "title": "Reporte BIM LATAM",
                "url": "https://example.com/bim-report",
                "snippet": "Adopcion BIM en Latinoamerica.",
            }
        ],
    )

    def _unexpected_gemini(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("Gemini fallback should not run when Tavily succeeds")

    monkeypatch.setattr(research_task, "search_gemini_google_search", _unexpected_gemini)

    result = research_task.handle_research_web({"query": "BIM LATAM", "count": 3, "search_depth": "advanced"})

    assert result["engine"] == research_task.TAVILY_PROVIDER
    assert result["count"] == 1
    assert result["results"][0]["title"] == "Reporte BIM LATAM"


def test_handle_research_web_falls_back_to_gemini_on_tavily_quota(monkeypatch):
    monkeypatch.setattr(
        research_task,
        "search_tavily",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            TaskExecutionError(
                "research.web unavailable: Tavily plan/quota exceeded",
                status_code=503,
                error_code="research_provider_quota_exceeded",
                error_kind="quota",
                provider=research_task.TAVILY_PROVIDER,
                upstream_status=432,
            )
        ),
    )
    monkeypatch.setattr(
        research_task,
        "search_gemini_google_search",
        lambda *args, **kwargs: [
            {
                "title": "5 BIM Trends in 2026",
                "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/example",
                "snippet": "La automatizacion e IA lideran las tendencias BIM.",
            }
        ],
    )

    result = research_task.handle_research_web({"query": "BIM LATAM"})

    assert result["engine"] == research_task.GEMINI_SEARCH_PROVIDER
    assert result["fallback_reason"] == "research_provider_quota_exceeded"
    assert result["count"] == 1
    assert result["results"][0]["url"].startswith("https://")
