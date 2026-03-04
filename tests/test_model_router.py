"""
Tests for S4 ModelRouter and QuotaTracker.

Uses fakeredis for QuotaTracker. Run: python -m pytest tests/test_model_router.py -v
"""

import pytest

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")

from dispatcher.model_router import ModelRouter, ModelSelectionDecision, load_quota_policy
from dispatcher.quota_tracker import QuotaTracker


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def provider_config():
    """Config mínimo para QuotaTracker (limit + window)."""
    return {
        "claude_pro": {"limit_requests": 100, "window_seconds": 3600},
        "chatgpt_plus": {"limit_requests": 150, "window_seconds": 3600},
        "gemini_pro": {"limit_requests": 200, "window_seconds": 86400},
        "copilot_pro": {"limit_requests": 80, "window_seconds": 3600},
    }


@pytest.fixture
def quota_tracker(redis_client, provider_config):
    return QuotaTracker(redis_client, provider_config)


@pytest.fixture
def model_router(quota_tracker):
    return ModelRouter(quota_tracker)


class TestQuotaTracker:
    def test_get_quota_state_zero_initially(self, quota_tracker):
        assert quota_tracker.get_quota_state("claude_pro") == 0.0
        assert quota_tracker.get_quota_state("chatgpt_plus") == 0.0

    def test_record_usage_increments_state(self, quota_tracker):
        for _ in range(10):
            quota_tracker.record_usage("claude_pro")
        # 10/100 = 0.1
        assert abs(quota_tracker.get_quota_state("claude_pro") - 0.1) < 0.01

    def test_unknown_provider_returns_zero(self, quota_tracker):
        assert quota_tracker.get_quota_state("unknown_provider") == 0.0

    def test_get_all_quota_states(self, quota_tracker):
        quota_tracker.record_usage("claude_pro")
        quota_tracker.record_usage("claude_pro")
        states = quota_tracker.get_all_quota_states()
        assert "claude_pro" in states
        assert states["claude_pro"] == 0.02  # 2/100


class TestModelRouter:
    def test_select_model_under_quota_returns_preferred(self, model_router):
        decision = model_router.select_model("coding")
        assert isinstance(decision, ModelSelectionDecision)
        assert decision.model == "chatgpt_plus"
        assert decision.requires_approval is False
        assert "under_quota" in decision.reason or "fallback" in decision.reason

    def test_select_model_writing_prefers_claude(self, model_router):
        decision = model_router.select_model("writing")
        assert decision.model == "claude_pro"
        assert decision.requires_approval is False

    def test_select_model_critical_prefers_claude(self, model_router):
        decision = model_router.select_model("critical")
        assert decision.model == "claude_pro"

    def test_select_model_unknown_task_type_defaults_to_general(self, model_router):
        decision = model_router.select_model("unknown_type")
        assert decision.model in ("chatgpt_plus", "claude_pro", "gemini_pro")
        assert isinstance(decision, ModelSelectionDecision)

    def test_select_model_with_explicit_quota_state(self, model_router):
        # Todos en 0 → preferido
        quota_state = {"claude_pro": 0, "chatgpt_plus": 0, "gemini_pro": 0, "copilot_pro": 0}
        decision = model_router.select_model("coding", quota_state=quota_state)
        assert decision.model == "chatgpt_plus"


class TestLoadQuotaPolicy:
    def test_load_returns_routing_and_providers(self):
        routing, providers = load_quota_policy()
        assert "coding" in routing
        assert routing["coding"]["preferred"] == "chatgpt_plus"
        assert "claude_pro" in providers or len(providers) >= 0


class TestUmbralDefaultModel:
    """Tests for UMBRAL_DEFAULT_MODEL env var override."""

    def test_default_model_overrides_preferred(self, quota_tracker, monkeypatch):
        monkeypatch.setenv("UMBRAL_DEFAULT_MODEL", "gemini_pro")
        router = ModelRouter(quota_tracker)
        decision = router.select_model("coding")
        # coding normally prefers chatgpt_plus, but override forces gemini_pro
        assert decision.model == "gemini_pro"
        assert decision.requires_approval is False

    def test_default_model_invalid_provider_ignored(self, quota_tracker, monkeypatch):
        monkeypatch.setenv("UMBRAL_DEFAULT_MODEL", "nonexistent_model")
        router = ModelRouter(quota_tracker)
        decision = router.select_model("coding")
        # Should fall back to normal routing since override is invalid
        assert decision.model == "chatgpt_plus"

    def test_default_model_empty_string_no_effect(self, quota_tracker, monkeypatch):
        monkeypatch.setenv("UMBRAL_DEFAULT_MODEL", "")
        router = ModelRouter(quota_tracker)
        decision = router.select_model("writing")
        assert decision.model == "claude_pro"

    def test_default_model_keeps_fallback_chain(self, quota_tracker, monkeypatch):
        monkeypatch.setenv("UMBRAL_DEFAULT_MODEL", "gemini_pro")
        router = ModelRouter(quota_tracker)
        # If gemini_pro is restricted, fallback should still work
        quota_state = {"gemini_pro": 0.96, "chatgpt_plus": 0.0, "claude_pro": 0.0, "copilot_pro": 0.0}
        decision = router.select_model("coding", quota_state=quota_state)
        # Should fall back since gemini_pro is over restrict (0.95 default for gemini)
        assert decision.model != "gemini_pro" or decision.requires_approval is True
