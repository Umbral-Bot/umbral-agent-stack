"""
Tests for S4/R6 — Model routing integration in the Dispatcher service loop.

Validates:
- PROVIDER_MODEL_MAP translations
- LLM tasks receive `model` injection
- Non-LLM tasks do NOT receive `model` injection
- QuotaTracker is updated post-execution
- Fallback when preferred model is in restrict
- Blocked tasks when all models exceed quota

Run: python -m pytest tests/test_model_routing_integration.py -v
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")

from dispatcher.model_router import ModelRouter, ModelSelectionDecision
from dispatcher.quota_tracker import QuotaTracker
from dispatcher.service import PROVIDER_MODEL_MAP, LLM_TASK_PREFIXES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def provider_config():
    """Alineado con config/quota_policy.yaml."""
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


def _make_envelope(task: str, task_type: str = "general", **extra_input):
    """Helper to build a minimal task envelope."""
    return {
        "task_id": str(uuid.uuid4()),
        "team": "system",
        "task": task,
        "task_type": task_type,
        "input": dict(extra_input),
        "status": "queued",
    }


# ---------------------------------------------------------------------------
# PROVIDER_MODEL_MAP tests
# ---------------------------------------------------------------------------

class TestProviderModelMap:
    def test_all_providers_have_mapping(self):
        """Todos los providers activos deben tener mapping."""
        expected = {
            "azure_foundry", "claude_pro", "claude_opus", "claude_haiku",
            "gemini_pro", "gemini_flash", "gemini_flash_lite", "gemini_vertex",
        }
        assert expected.issubset(set(PROVIDER_MODEL_MAP.keys()))

    def test_model_strings_are_not_empty(self):
        for provider, model in PROVIDER_MODEL_MAP.items():
            assert isinstance(model, str) and len(model) > 0, f"{provider} has empty model string"

    def test_known_mappings(self):
        assert PROVIDER_MODEL_MAP["azure_foundry"] == "gpt-5.3-codex"
        assert PROVIDER_MODEL_MAP["claude_pro"] == "claude-sonnet-4-6"
        assert PROVIDER_MODEL_MAP["claude_opus"] == "claude-opus-4-6"
        assert PROVIDER_MODEL_MAP["claude_haiku"] == "claude-haiku-4-5"
        assert PROVIDER_MODEL_MAP["gemini_pro"] == "gemini-3.1-pro-preview-customtools"
        assert PROVIDER_MODEL_MAP["gemini_flash"] == "gemini-flash-latest"
        assert PROVIDER_MODEL_MAP["gemini_flash_lite"] == "gemini-flash-lite-latest"


# ---------------------------------------------------------------------------
# LLM task prefixes
# ---------------------------------------------------------------------------

class TestLLMTaskPrefixes:
    def test_llm_generate_is_llm_task(self):
        assert any("llm.generate".startswith(p) for p in LLM_TASK_PREFIXES)

    def test_composite_research_is_llm_task(self):
        assert any("composite.research_report".startswith(p) for p in LLM_TASK_PREFIXES)

    def test_ping_is_not_llm_task(self):
        assert not any("ping".startswith(p) for p in LLM_TASK_PREFIXES)

    def test_notion_upsert_is_not_llm_task(self):
        assert not any("notion.upsert_task".startswith(p) for p in LLM_TASK_PREFIXES)


# ---------------------------------------------------------------------------
# Model injection in dispatch flow (unit simulation)
# ---------------------------------------------------------------------------

class TestModelInjection:
    """Simulates the model injection logic from _run_worker."""

    def _apply_model_routing(self, model_router, envelope):
        """Replicate the model routing logic from dispatcher/service.py _run_worker."""
        task = envelope.get("task", "unknown")
        task_type = envelope.get("task_type", "general")
        input_data = dict(envelope.get("input", {}))

        is_llm_task = any(task.startswith(p) for p in LLM_TASK_PREFIXES)
        decision = model_router.select_model(task_type)

        if decision.requires_approval and is_llm_task:
            return None, decision  # blocked

        selected_model = decision.model
        if is_llm_task:
            model_string = PROVIDER_MODEL_MAP.get(selected_model, selected_model)
            input_data["model"] = model_string
        input_data["selected_model"] = selected_model
        return input_data, decision

    def test_llm_task_gets_model_injected(self, model_router):
        envelope = _make_envelope("llm.generate", task_type="coding")
        input_data, decision = self._apply_model_routing(model_router, envelope)
        assert input_data is not None
        assert "model" in input_data
        assert input_data["model"] == PROVIDER_MODEL_MAP[decision.model]
        assert "selected_model" in input_data

    def test_composite_task_gets_model_injected(self, model_router):
        envelope = _make_envelope("composite.research_report", task_type="research")
        input_data, decision = self._apply_model_routing(model_router, envelope)
        assert input_data is not None
        assert "model" in input_data
        assert input_data["model"] == PROVIDER_MODEL_MAP[decision.model]

    def test_non_llm_task_no_model_injection(self, model_router):
        envelope = _make_envelope("ping", task_type="general")
        input_data, decision = self._apply_model_routing(model_router, envelope)
        assert input_data is not None
        assert "model" not in input_data
        assert "selected_model" in input_data

    def test_notion_task_no_model_injection(self, model_router):
        envelope = _make_envelope("notion.upsert_task", task_type="general")
        input_data, decision = self._apply_model_routing(model_router, envelope)
        assert input_data is not None
        assert "model" not in input_data

    def test_llm_task_blocked_when_quota_exceeded(self, quota_tracker, model_router):
        """Force all providers to 100% quota → requires_approval for LLM tasks."""
        all_providers = (
            "azure_foundry", "claude_pro", "claude_opus", "claude_haiku",
            "gemini_pro", "gemini_flash", "gemini_flash_lite", "gemini_vertex",
        )
        for provider in all_providers:
            cfg = quota_tracker.config.get(provider, {})
            limit = cfg.get("limit_requests", 100)
            for _ in range(limit):
                quota_tracker.record_usage(provider)

        envelope = _make_envelope("llm.generate", task_type="coding")
        input_data, decision = self._apply_model_routing(model_router, envelope)
        assert input_data is None  # blocked
        assert decision.requires_approval is True

    def test_non_llm_task_not_blocked_even_if_quota_exceeded(self, quota_tracker, model_router):
        """Non-LLM tasks should proceed even when quota is exceeded."""
        all_providers = (
            "azure_foundry", "claude_pro", "claude_opus", "claude_haiku",
            "gemini_pro", "gemini_flash", "gemini_flash_lite", "gemini_vertex",
        )
        for provider in all_providers:
            cfg = quota_tracker.config.get(provider, {})
            limit = cfg.get("limit_requests", 100)
            for _ in range(limit):
                quota_tracker.record_usage(provider)

        envelope = _make_envelope("ping", task_type="general")
        input_data, decision = self._apply_model_routing(model_router, envelope)
        # Non-LLM tasks pass through even with requires_approval
        assert input_data is not None
        assert "model" not in input_data


# ---------------------------------------------------------------------------
# Quota tracking post-execution
# ---------------------------------------------------------------------------

class TestQuotaPostExecution:
    def test_record_usage_after_execution(self, quota_tracker, model_router):
        """After successful execution, record_usage should increment quota."""
        decision = model_router.select_model("coding")
        selected = decision.model  # claude_pro (coding preferred)

        if selected not in quota_tracker.config:
            pytest.skip(f"{selected} not in test provider_config")

        initial_state = quota_tracker.get_quota_state(selected)
        quota_tracker.record_usage(selected)
        after_state = quota_tracker.get_quota_state(selected)

        assert after_state > initial_state

    def test_quota_affects_subsequent_routing(self, quota_tracker, model_router):
        """Pushing preferred model past warn should trigger fallback for non-critical."""
        # coding prefers claude_pro (limit=200, warn=0.80 → 160 requests)
        for _ in range(165):
            quota_tracker.record_usage("claude_pro")

        decision = model_router.select_model("coding")
        assert decision.model != "claude_pro" or decision.reason != "under_quota"


# ---------------------------------------------------------------------------
# Fallback under restrict
# ---------------------------------------------------------------------------

class TestFallbackRouting:
    def test_fallback_when_preferred_past_warn(self, quota_tracker, model_router):
        """When preferred is past warn threshold, use fallback chain."""
        # writing prefers claude_pro (limit=200, warn=0.8 → 160 requests)
        for _ in range(165):
            quota_tracker.record_usage("claude_pro")

        decision = model_router.select_model("writing")
        # writing fallback=[claude_opus, gemini_pro] (azure_foundry not configured)
        assert decision.model in ("claude_opus", "gemini_pro")
        assert "fallback" in decision.reason

    def test_fallback_chain_skips_restricted_models(self, quota_tracker, model_router):
        """If preferred and first fallback are restricted, try next in chain."""
        # writing: preferred=claude_pro, fallback=[claude_opus, azure_foundry, gemini_pro]
        # Restrict claude_pro (restrict=0.90 → 180/200) AND claude_opus (restrict=0.80 → 40/50)
        for _ in range(181):
            quota_tracker.record_usage("claude_pro")
        for _ in range(41):
            quota_tracker.record_usage("claude_opus")

        decision = model_router.select_model("writing")
        # Should skip claude_pro and claude_opus → falls to gemini_pro
        assert decision.model == "gemini_pro"
