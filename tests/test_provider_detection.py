"""
Tests for get_configured_providers() in dispatcher/model_router.py.

Validates that provider detection correctly reads env vars and that
ModelRouter skips unconfigured providers during model selection.

Run: python -m pytest tests/test_provider_detection.py -v
"""

from __future__ import annotations

import pytest

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")

from dispatcher.model_router import get_configured_providers, ModelRouter
from dispatcher.quota_tracker import QuotaTracker


@pytest.fixture
def provider_config():
    """Standard provider config for QuotaTracker."""
    return {
        "azure_foundry": {"limit_requests": 2000, "window_seconds": 3600, "warn": 0.80, "restrict": 0.95},
        "claude_pro": {"limit_requests": 200, "window_seconds": 18000, "warn": 0.80, "restrict": 0.90},
        "claude_opus": {"limit_requests": 50, "window_seconds": 18000, "warn": 0.60, "restrict": 0.80},
        "claude_haiku": {"limit_requests": 500, "window_seconds": 18000, "warn": 0.85, "restrict": 0.95},
        "gemini_pro": {"limit_requests": 500, "window_seconds": 86400, "warn": 0.80, "restrict": 0.95},
        "gemini_flash": {"limit_requests": 1000, "window_seconds": 86400, "warn": 0.85, "restrict": 0.97},
        "gemini_flash_lite": {"limit_requests": 2000, "window_seconds": 86400, "warn": 0.90, "restrict": 0.98},
        "gemini_vertex": {"limit_requests": 300, "window_seconds": 86400, "warn": 0.80, "restrict": 0.95},
    }


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def quota_tracker(redis_client, provider_config):
    return QuotaTracker(redis_client, provider_config)


# ── get_configured_providers() ─────────────────────────────────


class TestGetConfiguredProviders:

    def test_disable_claude_hides_anthropic_providers(self, monkeypatch):
        monkeypatch.setenv("UMBRAL_DISABLE_CLAUDE", "true")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        providers = get_configured_providers()
        assert "claude_pro" not in providers
        assert "claude_opus" not in providers
        assert "claude_haiku" not in providers

    def test_detects_anthropic_when_key_set(self, monkeypatch):
        """Anthropic providers detected when ANTHROPIC_API_KEY is set."""
        monkeypatch.delenv("UMBRAL_DISABLE_CLAUDE", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        # Clear others to isolate
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY_RICK_UMBRAL", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT_RICK_UMBRAL", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        providers = get_configured_providers()
        assert "claude_pro" in providers
        assert "claude_opus" in providers
        assert "claude_haiku" in providers
        # Should NOT include non-Anthropic
        assert "gemini_pro" not in providers
        assert "azure_foundry" not in providers

    def test_no_azure_foundry_without_env_vars(self, monkeypatch):
        """azure_foundry not included without both env vars."""
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        providers = get_configured_providers()
        assert "azure_foundry" not in providers

    def test_azure_foundry_requires_both_vars(self, monkeypatch):
        """azure_foundry needs BOTH endpoint and key."""
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        providers = get_configured_providers()
        assert "azure_foundry" not in providers

    def test_detects_all_with_complete_env(self, monkeypatch):
        """All providers detected when all env vars are set."""
        # Task 042: strip UMBRAL_DISABLE_CLAUDE leaked from ~/.config/openclaw/env
        # via worker.config import-time hook in conftest.
        monkeypatch.delenv("UMBRAL_DISABLE_CLAUDE", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")
        monkeypatch.setenv("GOOGLE_API_KEY_RICK_UMBRAL", "goog-vertex")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT_RICK_UMBRAL", "proj-test")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key-test")

        providers = get_configured_providers()
        expected = {
            "azure_foundry", "claude_pro", "claude_opus", "claude_haiku",
            "gemini_pro", "gemini_flash", "gemini_flash_lite", "gemini_vertex",
        }
        assert providers == expected

    def test_empty_key_not_detected(self, monkeypatch):
        """Empty string env var is treated as not set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        providers = get_configured_providers()
        assert "claude_pro" not in providers

    def test_whitespace_only_key_not_detected(self, monkeypatch):
        """Whitespace-only env var is treated as not set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        providers = get_configured_providers()
        assert "claude_pro" not in providers

    def test_vertex_requires_both_vars(self, monkeypatch):
        """gemini_vertex needs both GOOGLE_API_KEY_RICK_UMBRAL and GOOGLE_CLOUD_PROJECT_RICK_UMBRAL."""
        monkeypatch.setenv("GOOGLE_API_KEY_RICK_UMBRAL", "goog-vertex")
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT_RICK_UMBRAL", raising=False)

        providers = get_configured_providers()
        assert "gemini_vertex" not in providers


# ── ModelRouter skips unconfigured provider ────────────────────


class TestModelRouterProviderSkipping:

    def test_skips_unconfigured_preferred(self, quota_tracker, monkeypatch):
        """If preferred provider is unconfigured, ModelRouter promotes fallback."""
        # Only configure Google — no Anthropic
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY_RICK_UMBRAL", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT_RICK_UMBRAL", raising=False)

        router = ModelRouter(quota_tracker)
        # coding prefers claude_pro but it's unconfigured
        decision = router.select_model("coding")
        assert decision.model != "claude_pro"
        assert decision.model in ("gemini_pro", "gemini_flash")

    def test_uses_preferred_when_configured(self, quota_tracker, monkeypatch):
        """Normal case: preferred provider is configured and used."""
        # Task 042: strip UMBRAL_DISABLE_CLAUDE leaked from VPS env file.
        monkeypatch.delenv("UMBRAL_DISABLE_CLAUDE", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        router = ModelRouter(quota_tracker)
        decision = router.select_model("coding")
        assert decision.model == "claude_pro"
        assert decision.requires_approval is False

    def test_no_configured_provider_returns_blocking_decision(self, quota_tracker, monkeypatch):
        """If no provider in a route is configured, the router must not return a fake model."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY_RICK_UMBRAL", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT_RICK_UMBRAL", raising=False)

        router = ModelRouter(quota_tracker)
        decision = router.select_model("coding")
        assert decision.model == ""
        assert decision.reason == "no_configured_provider"
        assert decision.requires_approval is True


# ── Full flow: task_type→model→quota ───────────────────────────


class TestFullRoutingFlow:

    def test_coding_selects_claude_then_quota_increments(self, quota_tracker, monkeypatch):
        """coding→claude_pro selected, quota records usage."""
        # Task 042: strip UMBRAL_DISABLE_CLAUDE leaked from VPS env file.
        monkeypatch.delenv("UMBRAL_DISABLE_CLAUDE", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        router = ModelRouter(quota_tracker)
        decision = router.select_model("coding")
        assert decision.model == "claude_pro"

        # Simulate quota recording
        quota_tracker.record_usage("claude_pro")
        state = quota_tracker.get_quota_state("claude_pro")
        assert state > 0.0  # 1/200 = 0.005

    def test_claude_restricted_falls_to_gemini(self, quota_tracker, monkeypatch):
        """If claude_pro is in restrict, coding falls back to gemini_pro."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        router = ModelRouter(quota_tracker)
        quota_state = {
            "claude_pro": 0.91,  # above restrict (0.90)
            "gemini_pro": 0.0,
            "gemini_flash": 0.0,
        }
        decision = router.select_model("coding", quota_state=quota_state)
        assert decision.model in ("gemini_pro", "gemini_flash")
        assert decision.requires_approval is False
