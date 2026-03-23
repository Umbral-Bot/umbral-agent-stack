"""Tests for Tavily-first web discovery behavior."""

import scripts.web_discovery as web_discovery


def test_search_uses_tavily_by_default(monkeypatch):
    monkeypatch.setattr(
        web_discovery,
        "_search_tavily",
        lambda query, count: (
            [{"title": "Tavily result", "url": "https://example.com", "snippet": "ok", "source": "tavily"}],
            None,
        ),
    )

    def _unexpected_google(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("Google legacy fallback should stay disabled by default")

    monkeypatch.setattr(web_discovery, "_search_google", _unexpected_google)

    result = web_discovery.search("bim latam", count=3)

    assert result["engine_used"] == "tavily"
    assert result["fallback_reason"] is None
    assert result["error"] is None
    assert result["results"][0]["source"] == "tavily"


def test_search_returns_tavily_error_when_google_legacy_is_disabled(monkeypatch):
    monkeypatch.setattr(
        web_discovery,
        "_search_tavily",
        lambda query, count: ([], "skip:no_key_TAVILY_API_KEY"),
    )

    def _unexpected_google(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("Google legacy fallback should stay disabled by default")

    monkeypatch.setattr(web_discovery, "_search_google", _unexpected_google)

    result = web_discovery.search("bim latam", count=3)

    assert result["engine_used"] == "none"
    assert result["fallback_reason"] is None
    assert result["error"] == "skip:no_key_TAVILY_API_KEY"


def test_search_can_fallback_to_google_when_explicitly_enabled(monkeypatch):
    monkeypatch.setattr(
        web_discovery,
        "_search_tavily",
        lambda query, count: ([], "http:432:quota"),
    )
    monkeypatch.setattr(
        web_discovery,
        "_search_google",
        lambda query, count: (
            [{"title": "Legacy google result", "url": "https://google.example", "snippet": "ok", "source": "google"}],
            None,
        ),
    )

    result = web_discovery.search("bim latam", count=3, allow_google_legacy=True)

    assert result["engine_used"] == "google"
    assert result["fallback_reason"] == "http:432:quota"
    assert result["error"] is None
    assert result["results"][0]["source"] == "google"


def test_search_env_flag_can_enable_google_legacy(monkeypatch):
    monkeypatch.setenv("WEB_DISCOVERY_ENABLE_GOOGLE_CSE", "1")
    monkeypatch.setattr(
        web_discovery,
        "_search_tavily",
        lambda query, count: ([], "skip:no_key_TAVILY_API_KEY"),
    )
    monkeypatch.setattr(
        web_discovery,
        "_search_google",
        lambda query, count: (
            [{"title": "Legacy google result", "url": "https://google.example", "snippet": "ok", "source": "google"}],
            None,
        ),
    )

    result = web_discovery.search("bim latam", count=3)

    assert result["engine_used"] == "google"
    assert result["fallback_reason"] == "skip:no_key_TAVILY_API_KEY"
    assert result["error"] is None


def test_force_tavily_skips_google_even_when_legacy_is_enabled(monkeypatch):
    monkeypatch.setenv("WEB_DISCOVERY_ENABLE_GOOGLE_CSE", "1")
    monkeypatch.setattr(
        web_discovery,
        "_search_tavily",
        lambda query, count: ([], "http:503:tavily-down"),
    )

    def _unexpected_google(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("Google legacy fallback must be skipped when force_tavily is set")

    monkeypatch.setattr(web_discovery, "_search_google", _unexpected_google)

    result = web_discovery.search("bim latam", count=3, force_tavily=True)

    assert result["engine_used"] == "none"
    assert result["fallback_reason"] is None
    assert result["error"] == "http:503:tavily-down"
