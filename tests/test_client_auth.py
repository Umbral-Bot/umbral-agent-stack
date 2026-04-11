"""
Tests for Phase 6 — Multi-tenant client auth, API key management, and tier enforcement.

Run with:
    WORKER_TOKEN=test python -m pytest tests/test_client_auth.py -v
"""

import os
import time

import pytest

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")

from worker.client_auth import (
    API_KEY_PREFIX,
    ClientRecord,
    InMemoryClientStore,
    generate_api_key,
    get_tier_config,
    hash_api_key,
    is_client_api_key,
    is_task_allowed,
    load_tiers,
    get_client_store,
    set_client_store,
)


# ---------------------------------------------------------------------------
# API key generation
# ---------------------------------------------------------------------------


class TestApiKeyGeneration:
    def test_generate_api_key_has_prefix(self):
        key = generate_api_key()
        assert key.startswith(API_KEY_PREFIX)

    def test_generate_api_key_unique(self):
        keys = {generate_api_key() for _ in range(50)}
        assert len(keys) == 50

    def test_hash_api_key_deterministic(self):
        key = generate_api_key()
        assert hash_api_key(key) == hash_api_key(key)

    def test_hash_api_key_different_keys(self):
        k1 = generate_api_key()
        k2 = generate_api_key()
        assert hash_api_key(k1) != hash_api_key(k2)

    def test_is_client_api_key_true(self):
        assert is_client_api_key("ubim_abc123") is True

    def test_is_client_api_key_false(self):
        assert is_client_api_key("test-token-12345") is False
        assert is_client_api_key("") is False
        assert is_client_api_key("ubim") is False  # too short but has prefix


# ---------------------------------------------------------------------------
# Tier config
# ---------------------------------------------------------------------------


class TestTierConfig:
    def test_load_tiers_returns_dict(self):
        data = load_tiers(force=True)
        assert isinstance(data, dict)
        assert "tiers" in data

    def test_free_tier_exists(self):
        data = load_tiers()
        assert "free" in data.get("tiers", {})

    def test_get_tier_config_free(self):
        cfg = get_tier_config("free")
        assert "rate_limit_rpm" in cfg
        assert "daily_limit" in cfg
        assert "allowed_tasks" in cfg

    def test_get_tier_config_unknown_falls_back(self):
        cfg = get_tier_config("nonexistent_tier")
        # Should fall back to default tier (free)
        assert isinstance(cfg, dict)


# ---------------------------------------------------------------------------
# Task allowlist
# ---------------------------------------------------------------------------


class TestTaskAllowlist:
    def test_ping_allowed_for_free(self):
        assert is_task_allowed("free", "ping") is True

    def test_llm_generate_allowed_for_free(self):
        assert is_task_allowed("free", "llm.generate") is True

    def test_notion_blocked_for_free(self):
        # Free tier only allows specific tasks; notion is not in the list
        assert is_task_allowed("free", "notion.write_transcript") is False

    def test_enterprise_allows_all(self):
        assert is_task_allowed("enterprise", "notion.write_transcript") is True
        assert is_task_allowed("enterprise", "windows.pad.run_flow") is True

    def test_pro_blocks_dangerous_tasks(self):
        # Pro blocks gui.* and windows.pad.*
        assert is_task_allowed("pro", "gui.click") is False
        assert is_task_allowed("pro", "windows.pad.run_flow") is False

    def test_pro_allows_normal_tasks(self):
        assert is_task_allowed("pro", "ping") is True
        assert is_task_allowed("pro", "llm.generate") is True


# ---------------------------------------------------------------------------
# InMemoryClientStore
# ---------------------------------------------------------------------------


class TestInMemoryClientStore:
    @pytest.fixture
    def store(self):
        return InMemoryClientStore()

    def test_register_returns_record_and_key(self, store):
        record, api_key = store.register(name="Test Co", email="test@example.com")
        assert isinstance(record, ClientRecord)
        assert record.name == "Test Co"
        assert record.email == "test@example.com"
        assert record.tier == "free"
        assert record.active is True
        assert api_key.startswith(API_KEY_PREFIX)

    def test_register_with_tier(self, store):
        record, _ = store.register(name="Pro Co", email="pro@example.com", tier="pro")
        assert record.tier == "pro"

    def test_get_by_api_key(self, store):
        record, api_key = store.register(name="Lookup", email="look@example.com")
        found = store.get_by_api_key(api_key)
        assert found is not None
        assert found.client_id == record.client_id

    def test_get_by_api_key_invalid(self, store):
        assert store.get_by_api_key("ubim_nonexistent") is None

    def test_get_by_id(self, store):
        record, _ = store.register(name="ByID", email="byid@example.com")
        found = store.get_by_id(record.client_id)
        assert found is not None
        assert found.email == "byid@example.com"

    def test_revoke(self, store):
        record, api_key = store.register(name="Revoke", email="revoke@example.com")
        assert store.revoke(record.client_id) is True
        # Lookup by key should return None (revoked)
        assert store.get_by_api_key(api_key) is None

    def test_revoke_nonexistent(self, store):
        assert store.revoke("doesnotexist") is False

    def test_rotate_key(self, store):
        record, old_key = store.register(name="Rotate", email="rotate@example.com")
        new_key = store.rotate_key(record.client_id)
        assert new_key is not None
        assert new_key != old_key
        # Old key should not work
        assert store.get_by_api_key(old_key) is None
        # New key should work
        assert store.get_by_api_key(new_key) is not None

    def test_rotate_key_nonexistent(self, store):
        assert store.rotate_key("doesnotexist") is None

    def test_list_clients(self, store):
        store.register(name="A", email="a@example.com")
        store.register(name="B", email="b@example.com")
        clients = store.list_clients()
        assert len(clients) == 2

    def test_list_clients_active_only(self, store):
        r1, _ = store.register(name="Active", email="active@example.com")
        r2, _ = store.register(name="Inactive", email="inactive@example.com")
        store.revoke(r2.client_id)
        active = store.list_clients(active_only=True)
        assert len(active) == 1
        assert active[0].client_id == r1.client_id
        all_clients = store.list_clients(active_only=False)
        assert len(all_clients) == 2

    def test_record_and_get_usage(self, store):
        record, _ = store.register(name="Usage", email="usage@example.com")
        store.record_usage(record.client_id, "ping")
        store.record_usage(record.client_id, "llm.generate")
        usage = store.get_usage(record.client_id)
        assert usage["today_requests"] == 2
        assert usage["total_requests"] == 2
        assert usage["tier"] == "free"

    def test_check_daily_limit(self, store):
        record, _ = store.register(name="Limit", email="limit@example.com")
        # Free tier daily_limit is 100
        assert store.check_daily_limit(record.client_id) is True

    def test_check_daily_limit_nonexistent(self, store):
        assert store.check_daily_limit("doesnotexist") is False


# ---------------------------------------------------------------------------
# Client admin task handlers
# ---------------------------------------------------------------------------


class TestClientAdminHandlers:
    @pytest.fixture(autouse=True)
    def setup_store(self):
        """Reset the global store to a fresh InMemoryClientStore for each test."""
        fresh = InMemoryClientStore()
        set_client_store(fresh)
        yield
        set_client_store(InMemoryClientStore())

    def test_register_handler(self):
        from worker.tasks.client_admin import handle_client_register
        result = handle_client_register({"name": "Test", "email": "t@example.com"})
        assert "client_id" in result
        assert "api_key" in result
        assert result["tier"] == "free"
        assert result["api_key"].startswith(API_KEY_PREFIX)

    def test_register_handler_missing_name(self):
        from worker.tasks.client_admin import handle_client_register
        with pytest.raises(ValueError, match="name"):
            handle_client_register({"email": "t@example.com"})

    def test_register_handler_invalid_tier(self):
        from worker.tasks.client_admin import handle_client_register
        with pytest.raises(ValueError, match="Invalid tier"):
            handle_client_register({"name": "X", "email": "x@example.com", "tier": "mega"})

    def test_revoke_handler(self):
        from worker.tasks.client_admin import handle_client_register, handle_client_revoke
        reg = handle_client_register({"name": "Rev", "email": "r@example.com"})
        result = handle_client_revoke({"client_id": reg["client_id"]})
        assert result["revoked"] is True

    def test_rotate_key_handler(self):
        from worker.tasks.client_admin import handle_client_register, handle_client_rotate_key
        reg = handle_client_register({"name": "Rot", "email": "rot@example.com"})
        result = handle_client_rotate_key({"client_id": reg["client_id"]})
        assert "new_api_key" in result
        assert result["new_api_key"] != reg["api_key"]

    def test_list_handler(self):
        from worker.tasks.client_admin import handle_client_register, handle_client_list
        handle_client_register({"name": "A", "email": "a@example.com"})
        handle_client_register({"name": "B", "email": "b@example.com"})
        result = handle_client_list({})
        assert result["count"] == 2

    def test_usage_handler(self):
        from worker.tasks.client_admin import handle_client_register, handle_client_usage
        reg = handle_client_register({"name": "U", "email": "u@example.com"})
        result = handle_client_usage({"client_id": reg["client_id"]})
        assert result["today_requests"] == 0
        assert result["tier"] == "free"

    def test_get_handler(self):
        from worker.tasks.client_admin import handle_client_register, handle_client_get
        reg = handle_client_register({"name": "G", "email": "g@example.com"})
        result = handle_client_get({"client_id": reg["client_id"]})
        assert result["name"] == "G"
        assert "tier_config" in result


# ---------------------------------------------------------------------------
# Integration: client API key in /run endpoint
# ---------------------------------------------------------------------------


class TestClientAuthIntegration:
    @pytest.fixture(autouse=True)
    def setup_store(self):
        fresh = InMemoryClientStore()
        set_client_store(fresh)
        yield
        set_client_store(InMemoryClientStore())

    @pytest.fixture
    def http_client(self):
        from fastapi.testclient import TestClient
        from worker.app import app
        return TestClient(app)

    def test_client_api_key_ping(self, http_client):
        store = get_client_store()
        record, api_key = store.register(name="IntTest", email="int@example.com")
        resp = http_client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "hello"}},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_client_blocked_task_returns_403(self, http_client):
        store = get_client_store()
        record, api_key = store.register(name="BlockTest", email="block@example.com")
        resp = http_client.post(
            "/run",
            json={"task": "notion.read_page", "input": {"page_id": "x"}},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 403
        assert "not allowed" in resp.json()["detail"]

    def test_invalid_client_key_returns_401(self, http_client):
        resp = http_client.post(
            "/run",
            json={"task": "ping", "input": {}},
            headers={"Authorization": "Bearer ubim_invalid_key_here"},
        )
        assert resp.status_code == 401

    def test_admin_token_still_works(self, http_client):
        resp = http_client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "admin"}},
            headers={"Authorization": "Bearer test-token-12345"},
        )
        assert resp.status_code == 200

    def test_usage_recorded_after_success(self, http_client):
        store = get_client_store()
        record, api_key = store.register(name="UsageTest", email="usg@example.com")
        http_client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "track"}},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        usage = store.get_usage(record.client_id)
        assert usage["today_requests"] == 1
