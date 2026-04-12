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
    """Config para QuotaTracker — alineado con config/quota_policy.yaml."""
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
def quota_tracker(redis_client, provider_config):
    return QuotaTracker(redis_client, provider_config)


@pytest.fixture(autouse=True)
def _set_provider_env_vars(monkeypatch):
    """Simula que los providers principales están configurados."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")
    monkeypatch.setenv("GOOGLE_API_KEY_RICK_UMBRAL", "goog-vertex-test")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT_RICK_UMBRAL", "proj-test")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)


@pytest.fixture
def model_router(quota_tracker):
    return ModelRouter(quota_tracker)


class TestQuotaTracker:
    def test_get_quota_state_zero_initially(self, quota_tracker):
        assert quota_tracker.get_quota_state("claude_pro") == 0.0
        assert quota_tracker.get_quota_state("gemini_pro") == 0.0

    def test_record_usage_increments_state(self, quota_tracker):
        for _ in range(20):
            quota_tracker.record_usage("claude_pro")
        # 20/200 = 0.1
        assert abs(quota_tracker.get_quota_state("claude_pro") - 0.1) < 0.01

    def test_unknown_provider_returns_zero(self, quota_tracker):
        assert quota_tracker.get_quota_state("unknown_provider") == 0.0

    def test_get_all_quota_states(self, quota_tracker):
        quota_tracker.record_usage("claude_pro")
        quota_tracker.record_usage("claude_pro")
        states = quota_tracker.get_all_quota_states()
        assert "claude_pro" in states
        assert states["claude_pro"] == 0.01  # 2/200


class TestModelRouter:
    def test_select_model_coding_prefers_claude_pro(self, model_router):
        """coding usa claude_pro como preferido (provider ya configurado)."""
        decision = model_router.select_model("coding")
        assert isinstance(decision, ModelSelectionDecision)
        assert decision.model == "claude_pro"
        assert decision.requires_approval is False

    def test_select_model_general_prefers_claude_pro(self, model_router):
        """general usa claude_pro (azure_foundry no configurado, se salta)."""
        decision = model_router.select_model("general")
        assert decision.model == "claude_pro"
        assert decision.requires_approval is False

    def test_select_model_writing_prefers_claude(self, model_router):
        decision = model_router.select_model("writing")
        assert decision.model == "claude_pro"
        assert decision.requires_approval is False

    def test_select_model_critical_prefers_claude_opus(self, model_router):
        decision = model_router.select_model("critical")
        assert decision.model == "claude_opus"

    def test_select_model_research_prefers_gemini(self, model_router):
        decision = model_router.select_model("research")
        assert decision.model == "gemini_pro"

    def test_select_model_light_prefers_gemini_flash(self, model_router):
        decision = model_router.select_model("light")
        assert decision.model == "gemini_flash"

    def test_select_model_unknown_task_type_defaults_to_general(self, model_router):
        decision = model_router.select_model("unknown_type")
        assert isinstance(decision, ModelSelectionDecision)
        assert decision.model in ("claude_pro", "gemini_pro", "gemini_flash")

    def test_select_model_with_explicit_quota_state(self, model_router):
        quota_state = {
            "claude_pro": 0, "claude_opus": 0,
            "claude_haiku": 0, "gemini_pro": 0, "gemini_flash": 0,
            "gemini_flash_lite": 0, "gemini_vertex": 0,
        }
        decision = model_router.select_model("coding", quota_state=quota_state)
        assert decision.model == "claude_pro"

    def test_coding_falls_back_when_claude_restricted(self, model_router):
        """Si claude_pro está en restrict, cae a gemini_pro."""
        quota_state = {
            "claude_pro": 0.91,
            "claude_opus": 0.0,
            "claude_haiku": 0.0,
            "gemini_pro": 0.0,
            "gemini_flash": 0.0,
            "gemini_flash_lite": 0.0,
            "gemini_vertex": 0.0,
        }
        decision = model_router.select_model("coding", quota_state=quota_state)
        assert decision.model in ("gemini_pro", "gemini_flash")

    def test_foundry_used_when_configured(self, quota_tracker, monkeypatch):
        """Si Foundry está configurado, aparece en fallback y puede ser seleccionado."""
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "az-key")
        router = ModelRouter(quota_tracker)
        quota_state = {"claude_pro": 0.91, "gemini_pro": 0.96, "azure_foundry": 0.0}
        decision = router.select_model("coding", quota_state=quota_state)
        assert decision.model == "azure_foundry"

    def test_unconfigured_provider_skipped(self, quota_tracker, monkeypatch):
        """azure_foundry sin env vars se salta, no aparece en seleccion."""
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        router = ModelRouter(quota_tracker)
        quota_state = {"claude_pro": 0.91, "gemini_pro": 0.0}
        decision = router.select_model("coding", quota_state=quota_state)
        assert decision.model == "gemini_pro"


class TestLoadQuotaPolicy:
    def test_load_returns_routing_and_providers(self):
        routing, providers = load_quota_policy()
        assert "coding" in routing
        assert routing["coding"]["preferred"] == "azure_foundry"
        assert "claude_pro" in providers


class TestUmbralDefaultModel:
    """Tests for UMBRAL_DEFAULT_MODEL env var override."""

    def test_default_model_overrides_preferred(self, quota_tracker, monkeypatch):
        monkeypatch.setenv("UMBRAL_DEFAULT_MODEL", "gemini_pro")
        router = ModelRouter(quota_tracker)
        decision = router.select_model("coding")
        assert decision.model == "gemini_pro"
        assert decision.requires_approval is False

    def test_default_model_invalid_provider_ignored(self, quota_tracker, monkeypatch):
        monkeypatch.setenv("UMBRAL_DEFAULT_MODEL", "nonexistent_model")
        router = ModelRouter(quota_tracker)
        decision = router.select_model("coding")
        assert decision.model == "claude_pro"

    def test_default_model_empty_string_no_effect(self, quota_tracker, monkeypatch):
        monkeypatch.setenv("UMBRAL_DEFAULT_MODEL", "")
        router = ModelRouter(quota_tracker)
        decision = router.select_model("writing")
        assert decision.model == "claude_pro"

    def test_default_model_keeps_fallback_chain(self, quota_tracker, monkeypatch):
        monkeypatch.setenv("UMBRAL_DEFAULT_MODEL", "gemini_pro")
        router = ModelRouter(quota_tracker)
        quota_state = {
            "gemini_pro": 0.96, "claude_pro": 0.0,
        }
        decision = router.select_model("coding", quota_state=quota_state)
        assert decision.model != "gemini_pro" or decision.requires_approval is True


class TestAutoApproveQuota:
    """Tests for auto_approve_quota behaviour."""

    def _make_router(self, quota_tracker, auto_approve: bool):
        router = ModelRouter(quota_tracker)
        router.auto_approve_quota = auto_approve
        return router

    def test_auto_approve_skips_block_when_all_over_restrict(self, quota_tracker):
        """When auto_approve_quota=True and all providers are over restrict, task proceeds."""
        router = self._make_router(quota_tracker, auto_approve=True)
        quota_state = {
            "claude_pro": 0.95,
            "gemini_pro": 0.97,
            "gemini_flash": 0.98,
            "gemini_flash_lite": 0.99,
            "gemini_vertex": 0.96,
            "claude_opus": 0.85,
            "claude_haiku": 0.96,
        }
        decision = router.select_model("coding", quota_state=quota_state)
        assert decision.requires_approval is False
        assert decision.reason == "auto_approved_over_quota"
        assert decision.model != ""

    def test_auto_approve_disabled_blocks_when_all_over_restrict(self, quota_tracker):
        """When auto_approve_quota=False, all-over-restrict still blocks."""
        router = self._make_router(quota_tracker, auto_approve=False)
        quota_state = {
            "claude_pro": 0.95,
            "gemini_pro": 0.97,
            "gemini_flash": 0.98,
            "gemini_flash_lite": 0.99,
            "gemini_vertex": 0.96,
            "claude_opus": 0.85,
            "claude_haiku": 0.96,
        }
        decision = router.select_model("coding", quota_state=quota_state)
        assert decision.requires_approval is True
        assert decision.reason == "quota_exceeded"

    def test_auto_approve_critical_at_100_percent(self, quota_tracker):
        """Critical task at 100% quota is auto-approved when enabled."""
        router = self._make_router(quota_tracker, auto_approve=True)
        quota_state = {
            "claude_opus": 1.0,
            "claude_pro": 0.95,
            "gemini_pro": 0.97,
        }
        decision = router.select_model("critical", quota_state=quota_state)
        assert decision.requires_approval is False
        assert decision.reason == "auto_approved_over_quota"

    def test_auto_approve_does_not_affect_under_quota(self, quota_tracker):
        """When under quota, auto_approve has no effect — normal path used."""
        router = self._make_router(quota_tracker, auto_approve=True)
        quota_state = {"claude_pro": 0.1, "gemini_pro": 0.1}
        decision = router.select_model("coding", quota_state=quota_state)
        assert decision.model == "claude_pro"
        assert decision.reason == "under_quota"
        assert decision.requires_approval is False

    def test_auto_approve_does_not_affect_fallback(self, quota_tracker):
        """When preferred is over restrict but fallback is available, normal fallback used."""
        router = self._make_router(quota_tracker, auto_approve=True)
        quota_state = {"claude_pro": 0.95, "gemini_pro": 0.1}
        decision = router.select_model("coding", quota_state=quota_state)
        assert decision.model == "gemini_pro"
        assert decision.reason == "fallback_under_restrict"
