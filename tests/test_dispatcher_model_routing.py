"""
Tests for Task 024: Dispatcher Model Routing integration.

Verifies:
- PROVIDER_MODEL_MAP mapping
- map_provider_to_model helper
- Model injection into LLM task envelopes
- Non-LLM tasks don't get model injection
- QuotaTracker updates post-execution
- Fallback when preferred model is in restrict

Uses fakeredis for Redis mocking.

Run:
    python -m pytest tests/test_dispatcher_model_routing.py -v
"""

import pytest

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")

from dispatcher.model_router import (
    ModelRouter,
    ModelSelectionDecision,
)
from dispatcher.service import PROVIDER_MODEL_MAP
from dispatcher.quota_tracker import QuotaTracker


# Keep compatibility with older tests while mapping through the current source of truth.
def map_provider_to_model(provider: str) -> str:
    return PROVIDER_MODEL_MAP.get(provider, provider)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def provider_config():
    return {
        "claude_pro": {"limit_requests": 100, "window_seconds": 3600, "warn": 0.8, "restrict": 0.9},
        "gemini_pro": {"limit_requests": 200, "window_seconds": 86400, "warn": 0.8, "restrict": 0.95},
        "gemini_flash": {"limit_requests": 500, "window_seconds": 86400, "warn": 0.8, "restrict": 0.95},
        "azure_foundry": {"limit_requests": 150, "window_seconds": 3600, "warn": 0.8, "restrict": 0.9},
        "claude_opus": {"limit_requests": 50, "window_seconds": 3600, "warn": 0.8, "restrict": 0.9},
    }


@pytest.fixture
def quota_tracker(redis_client, provider_config):
    return QuotaTracker(redis_client, provider_config)


@pytest.fixture(autouse=True)
def provider_env(monkeypatch):
    # Ensure ModelRouter considers these providers configured during tests.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.test")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test")


@pytest.fixture
def model_router(quota_tracker):
    return ModelRouter(quota_tracker)


# ---------------------------------------------------------------------------
# PROVIDER_MODEL_MAP tests
# ---------------------------------------------------------------------------


class TestProviderModelMap:
    def test_all_providers_have_mapping(self):
        expected_subset = {"azure_foundry", "claude_pro", "gemini_pro"}
        assert expected_subset.issubset(set(PROVIDER_MODEL_MAP.keys()))

    def test_azure_foundry_maps_to_gpt52_chat(self):
        assert PROVIDER_MODEL_MAP["azure_foundry"] == "gpt-5.2-chat"

    def test_gemini_maps_to_gemini_pro_model(self):
        assert PROVIDER_MODEL_MAP["gemini_pro"] == "gemini-2.5-pro"

    def test_claude_maps_to_sonnet(self):
        assert PROVIDER_MODEL_MAP["claude_pro"] == "claude-sonnet-4-6"


class TestMapProviderToModel:
    def test_known_provider(self):
        assert map_provider_to_model("gemini_pro") == "gemini-2.5-pro"

    def test_unknown_provider_returns_itself(self):
        assert map_provider_to_model("unknown_provider") == "unknown_provider"

    def test_empty_string(self):
        assert map_provider_to_model("") == ""


# ---------------------------------------------------------------------------
# Model injection simulation tests
# ---------------------------------------------------------------------------


class TestModelInjection:
    """Simulates the logic in dispatcher/service.py _run_worker for model injection."""

    LLM_TASKS = ("llm.generate", "composite.research_report")

    def _simulate_injection(self, model_router, task: str, task_type: str) -> dict:
        """Simulates the dispatch flow for a single task."""
        input_data = {}
        decision = model_router.select_model(task_type)

        selected_model = decision.model
        mapped_model = map_provider_to_model(selected_model)
        input_data["selected_model"] = selected_model

        if task in self.LLM_TASKS:
            input_data["model"] = mapped_model

        return input_data

    def test_llm_generate_gets_model_injected(self, model_router):
        result = self._simulate_injection(model_router, "llm.generate", "coding")
        assert "model" in result
        assert result["model"] == PROVIDER_MODEL_MAP.get(result["selected_model"], result["selected_model"])

    def test_composite_research_report_gets_model_injected(self, model_router):
        result = self._simulate_injection(model_router, "composite.research_report", "research")
        assert "model" in result
        assert result["selected_model"] == "gemini_pro"
        assert result["model"] == PROVIDER_MODEL_MAP["gemini_pro"]

    def test_non_llm_task_no_model_field(self, model_router):
        result = self._simulate_injection(model_router, "notion.upsert_task", "general")
        assert "model" not in result
        assert "selected_model" in result

    def test_ping_task_no_model_field(self, model_router):
        result = self._simulate_injection(model_router, "ping", "general")
        assert "model" not in result

    def test_research_web_no_model_field(self, model_router):
        result = self._simulate_injection(model_router, "research.web", "research")
        assert "model" not in result
        assert "selected_model" in result


# ---------------------------------------------------------------------------
# Quota update post-execution tests
# ---------------------------------------------------------------------------


class TestQuotaPostExecution:
    def test_quota_increments_after_task(self, model_router, quota_tracker):
        decision = model_router.select_model("coding")
        selected = decision.model

        state_before = quota_tracker.get_quota_state(selected)
        quota_tracker.record_usage(selected)
        state_after = quota_tracker.get_quota_state(selected)

        assert state_after > state_before

    def test_quota_multiple_recordings(self, model_router, quota_tracker):
        decision = model_router.select_model("writing")
        selected = decision.model

        for _ in range(10):
            quota_tracker.record_usage(selected)

        state = quota_tracker.get_quota_state(selected)
        # claude_pro: 10/100 = 0.1
        assert abs(state - 0.1) < 0.01


# ---------------------------------------------------------------------------
# Fallback when preferred model in restrict
# ---------------------------------------------------------------------------


class TestFallbackOnRestrict:
    def test_fallback_when_preferred_restricted(self, model_router):
        # coding preferred = claude_pro; mark it as restricted
        quota_state = {
            "claude_pro": 0.95,  # over restrict (0.9)
            "gemini_pro": 0.0,
            "azure_foundry": 0.0,
            "gemini_flash": 0.0,
        }
        decision = model_router.select_model("coding", quota_state=quota_state)
        # Should fall back to something else from coding fallback chain.
        assert decision.model != "claude_pro"
        assert decision.requires_approval is False

    def test_all_restricted_requires_approval(self, model_router):
        quota_state = {
            "claude_pro": 1.0,
            "gemini_pro": 1.0,
            "azure_foundry": 1.0,
            "gemini_flash": 1.0,
        }
        decision = model_router.select_model("coding", quota_state=quota_state)
        assert decision.requires_approval is True

    def test_critical_overrides_restriction(self, model_router):
        # critical preferred = claude_opus; mark it as warn but not restrict
        quota_state = {
            "claude_opus": 0.85,  # between warn and restrict
            "claude_pro": 0.0,
            "gemini_pro": 0.0,
            "azure_foundry": 0.0,
        }
        decision = model_router.select_model("critical", quota_state=quota_state)
        # critical tasks get high_priority_override
        assert decision.model == "claude_opus"
        assert "high_priority" in decision.reason

    def test_mapped_model_for_fallback(self, model_router):
        # Verify the fallback model also maps correctly
        quota_state = {
            "claude_pro": 0.95,
            "gemini_pro": 0.0,
            "azure_foundry": 0.0,
            "gemini_flash": 0.0,
        }
        decision = model_router.select_model("coding", quota_state=quota_state)
        mapped = map_provider_to_model(decision.model)
        assert mapped in PROVIDER_MODEL_MAP.values()
