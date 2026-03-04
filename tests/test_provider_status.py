import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

os.environ["WORKER_TOKEN"] = "test-token-12345"
from worker.app import app

AUTH = {"Authorization": "Bearer test-token-12345"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_redis():
    if not HAS_FAKEREDIS:
        pytest.skip("fakeredis not installed")
    return fakeredis.FakeRedis(decode_responses=True)


# ── Auth ──────────────────────────────────────────────────────────


class TestProviderStatusAuth:
    def test_no_auth_returns_401(self, client):
        resp = client.get("/providers/status")
        assert resp.status_code == 401

    def test_bad_token_returns_401(self, client):
        resp = client.get("/providers/status", headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 401


# ── Redis unavailable ─────────────────────────────────────────────


class TestProviderStatusRedisDown:
    def test_redis_down_returns_503(self, client):
        with patch("worker.app._get_redis", return_value=None):
            resp = client.get("/providers/status", headers=AUTH)
            assert resp.status_code == 503
            assert "Redis" in resp.json()["detail"]


# ── Response format ───────────────────────────────────────────────


class TestProviderStatusFormat:
    def test_response_has_required_keys(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get("/providers/status", headers=AUTH)
            assert resp.status_code == 200
            data = resp.json()
            assert "timestamp" in data
            assert "configured" in data
            assert "unconfigured" in data
            assert "providers" in data

    def test_provider_entry_has_required_fields(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get("/providers/status", headers=AUTH)
            data = resp.json()
            # There should be at least one provider from quota_policy.yaml
            assert len(data["providers"]) > 0
            for _name, info in data["providers"].items():
                assert "configured" in info
                assert "model" in info
                assert "quota_used" in info
                assert "quota_limit" in info
                assert "quota_status" in info
                assert "routing_preferred_for" in info


# ── Configured vs unconfigured detection ──────────────────────────


class TestProviderStatusConfigured:
    """Test that providers with/without env vars are classified correctly."""

    def test_configured_provider_appears_in_configured_list(self, client, fake_redis):
        """When ANTHROPIC_API_KEY is set, claude_pro should be configured."""
        env_override = {"ANTHROPIC_API_KEY": "sk-test-key-12345"}
        with (
            patch("worker.app._get_redis", return_value=fake_redis),
            patch.dict(os.environ, env_override),
        ):
            resp = client.get("/providers/status", headers=AUTH)
            data = resp.json()
            assert "claude_pro" in data["configured"]
            assert data["providers"]["claude_pro"]["configured"] is True

    def test_unconfigured_provider_without_env_vars(self, client, fake_redis):
        """Without AZURE keys, azure_foundry should be unconfigured."""
        env_clear = {
            "AZURE_OPENAI_ENDPOINT": "",
            "AZURE_OPENAI_API_KEY": "",
        }
        with (
            patch("worker.app._get_redis", return_value=fake_redis),
            patch.dict(os.environ, env_clear),
        ):
            resp = client.get("/providers/status", headers=AUTH)
            data = resp.json()
            assert "azure_foundry" in data["unconfigured"]
            assert data["providers"]["azure_foundry"]["configured"] is False


# ── Routing info ──────────────────────────────────────────────────


class TestProviderStatusRouting:
    def test_routing_preferred_for_populated(self, client, fake_redis):
        """claude_pro should be preferred for coding, general, ms_stack, writing."""
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get("/providers/status", headers=AUTH)
            data = resp.json()
            claude_routes = data["providers"]["claude_pro"]["routing_preferred_for"]
            assert isinstance(claude_routes, list)
            # Per quota_policy.yaml, claude_pro is preferred for coding, general, ms_stack, writing
            for expected_type in ["coding", "general"]:
                assert expected_type in claude_routes

    def test_gemini_pro_preferred_for_research(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get("/providers/status", headers=AUTH)
            data = resp.json()
            gemini_routes = data["providers"]["gemini_pro"]["routing_preferred_for"]
            assert "research" in gemini_routes

    def test_model_names_populated(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get("/providers/status", headers=AUTH)
            data = resp.json()
            assert data["providers"]["claude_pro"]["model"] == "claude-sonnet-4-6"
            assert data["providers"]["gemini_pro"]["model"] == "gemini-3.1-pro-preview-customtools"


# ── Quota values ──────────────────────────────────────────────────


class TestProviderStatusQuota:
    def test_quota_defaults_to_zero(self, client, fake_redis):
        """With empty Redis, usage should be 0."""
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get("/providers/status", headers=AUTH)
            data = resp.json()
            for _name, info in data["providers"].items():
                assert info["quota_used"] == 0
