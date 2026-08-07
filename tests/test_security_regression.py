"""
Security regression tests — validates fixes for audit findings.

Each test targets a specific vulnerability that was found and patched.
These tests should NEVER be removed or weakened.

Run with:
    WORKER_TOKEN=test python -m pytest tests/test_security_regression.py -v
"""

import os
import sys
import time
import types

import pytest

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")

from fastapi.testclient import TestClient

from worker.app import app
from worker.client_auth import (
    InMemoryClientStore,
    get_client_store,
    get_tier_config,
    is_task_allowed,
    set_client_store,
)
from worker.rag.indexer import chunk_text


AUTH = {"Authorization": "Bearer test-token-12345"}


@pytest.fixture(autouse=True)
def fresh_store():
    """Reset the global client store before each test."""
    fresh = InMemoryClientStore()
    set_client_store(fresh)
    yield
    set_client_store(InMemoryClientStore())


@pytest.fixture
def http_client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# FIX #1 — Privilege escalation: client.* tasks blocked for non-admin
# ---------------------------------------------------------------------------


class TestPrivilegeEscalation:
    """Ensure non-admin clients cannot call client.* admin tasks."""

    ADMIN_TASKS = [
        "client.register",
        "client.revoke",
        "client.rotate_key",
        "client.list",
        "client.usage",
        "client.get",
    ]

    def test_free_tier_cannot_call_admin_tasks(self):
        for task in self.ADMIN_TASKS:
            assert is_task_allowed("free", task) is False, f"free should not access {task}"

    def test_pro_tier_cannot_call_admin_tasks(self):
        for task in self.ADMIN_TASKS:
            assert is_task_allowed("pro", task) is False, f"pro should not access {task}"

    def test_enterprise_tier_cannot_call_admin_tasks(self):
        for task in self.ADMIN_TASKS:
            assert is_task_allowed("enterprise", task) is False, f"enterprise should not access {task}"

    def test_pro_cannot_self_register_enterprise(self, http_client):
        """The actual exploit: a pro client tries to register an enterprise client."""
        store = get_client_store()
        _, api_key = store.register(name="Attacker", email="attacker@example.com", tier="pro")
        resp = http_client.post(
            "/run",
            json={"task": "client.register", "input": {
                "name": "Escalated", "email": "escalated@example.com", "tier": "enterprise"
            }},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 403
        assert "not allowed" in resp.json()["detail"]

    def test_pro_cannot_revoke_other_client(self, http_client):
        store = get_client_store()
        victim, _ = store.register(name="Victim", email="victim@example.com")
        _, attacker_key = store.register(name="Attacker", email="attacker@example.com", tier="pro")
        resp = http_client.post(
            "/run",
            json={"task": "client.revoke", "input": {"client_id": victim.client_id}},
            headers={"Authorization": f"Bearer {attacker_key}"},
        )
        assert resp.status_code == 403

    def test_admin_token_can_still_manage_clients(self, http_client):
        """Admin (WORKER_TOKEN) should still have full access."""
        resp = http_client.post(
            "/run",
            json={"task": "client.register", "input": {
                "name": "Legit", "email": "legit@example.com"
            }},
            headers=AUTH,
        )
        assert resp.status_code == 200
        assert "api_key" in resp.json()["result"]


# ---------------------------------------------------------------------------
# FIX #2 — /enqueue tier bypass
# ---------------------------------------------------------------------------


class TestEnqueueTierEnforcement:
    """Ensure /enqueue also enforces tier restrictions."""

    def test_free_client_cannot_enqueue_blocked_task(self, http_client):
        store = get_client_store()
        _, api_key = store.register(name="Freebie", email="free@example.com")
        resp = http_client.post(
            "/enqueue",
            json={"task": "notion.read_page", "input": {"page_id": "x"}},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        # Should be 403 (blocked) or 503 (no Redis) — but NOT 200
        assert resp.status_code in (403, 503)
        if resp.status_code == 403:
            assert "not allowed" in resp.json()["detail"]

    def test_free_client_over_daily_limit_gets_429(self, http_client):
        store = get_client_store()
        record, api_key = store.register(name="DailyLimit", email="daily@example.com")
        today = time.strftime("%Y-%m-%d", time.gmtime())
        daily_limit = get_tier_config("free").get("daily_limit", 0) or 1
        store._daily_counts[record.client_id][today] = daily_limit

        resp = http_client.post(
            "/enqueue",
            json={"task": "ping", "input": {"msg": "blocked"}},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 429
        assert "Daily limit exceeded" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# FIX #3 — OData filter injection
# ---------------------------------------------------------------------------


class TestODataInjection:
    """Ensure OData filter values are properly escaped."""

    @staticmethod
    def _install_fake_azure_modules(monkeypatch, capture):
        class FakeAzureKeyCredential:
            def __init__(self, key):
                self.key = key

        class FakeVectorizedQuery:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                capture["vector_query_kwargs"] = kwargs

        class FakeSearchClient:
            def __init__(self, endpoint, index_name, credential):
                capture["client_init"] = {
                    "endpoint": endpoint,
                    "index_name": index_name,
                    "key": getattr(credential, "key", None),
                }

            def search(self, search_text=None, **kwargs):
                capture["search_text"] = search_text
                capture["search_kwargs"] = kwargs
                return [
                    {
                        "id": "doc-1",
                        "content": "safe result",
                        "title": "T",
                        "source": "S",
                        "source_type": "file",
                        "chunk_index": 0,
                        "@search.score": 0.99,
                    }
                ]

        azure_module = types.ModuleType("azure")
        core_module = types.ModuleType("azure.core")
        credentials_module = types.ModuleType("azure.core.credentials")
        search_module = types.ModuleType("azure.search")
        documents_module = types.ModuleType("azure.search.documents")
        models_module = types.ModuleType("azure.search.documents.models")

        credentials_module.AzureKeyCredential = FakeAzureKeyCredential
        documents_module.SearchClient = FakeSearchClient
        models_module.VectorizedQuery = FakeVectorizedQuery

        azure_module.core = core_module
        azure_module.search = search_module
        core_module.credentials = credentials_module
        search_module.documents = documents_module
        documents_module.models = models_module

        monkeypatch.setitem(sys.modules, "azure", azure_module)
        monkeypatch.setitem(sys.modules, "azure.core", core_module)
        monkeypatch.setitem(sys.modules, "azure.core.credentials", credentials_module)
        monkeypatch.setitem(sys.modules, "azure.search", search_module)
        monkeypatch.setitem(sys.modules, "azure.search.documents", documents_module)
        monkeypatch.setitem(sys.modules, "azure.search.documents.models", models_module)

    def test_source_filter_with_single_quote(self, monkeypatch):
        from worker.rag import retriever

        capture = {}
        self._install_fake_azure_modules(monkeypatch, capture)
        monkeypatch.setattr(
            retriever,
            "_get_search_credentials",
            lambda: ("https://search.example", "search-key"),
        )

        query_payload = "test' or 1 eq 1 or source eq '"
        source_type_payload = "notion'type"
        results = retriever.search(
            query="safe query",
            mode="keyword",
            source_filter=query_payload,
            source_type_filter=source_type_payload,
        )

        assert capture["search_text"] == "safe query"
        assert capture["search_kwargs"]["filter"] == (
            "source eq 'test'' or 1 eq 1 or source eq ''' and "
            "source_type eq 'notion''type'"
        )
        assert capture["search_kwargs"]["top"] == 5
        assert "vector_queries" not in capture["search_kwargs"]
        assert results[0]["id"] == "doc-1"

    def test_vector_mode_uses_vector_query(self, monkeypatch):
        from worker.rag import retriever

        capture = {}
        self._install_fake_azure_modules(monkeypatch, capture)
        monkeypatch.setattr(
            retriever,
            "_get_search_credentials",
            lambda: ("https://search.example", "search-key"),
        )
        monkeypatch.setattr(
            retriever,
            "generate_embeddings",
            lambda texts: [[0.1, 0.2, 0.3] for _ in texts],
        )

        retriever.search(query="vector query", mode="vector", top=2)

        assert capture["search_text"] is None
        assert len(capture["search_kwargs"]["vector_queries"]) == 1
        assert capture["vector_query_kwargs"]["k_nearest_neighbors"] == 2
        assert capture["vector_query_kwargs"]["fields"] == "content_vector"


# ---------------------------------------------------------------------------
# FIX #4 — _client_limiters memory leak
# ---------------------------------------------------------------------------


class TestLimiterBounds:
    """Ensure the client limiter dict doesn't grow unbounded."""

    def test_client_limiters_are_bounded(self):
        from worker.app import _client_limiters, _MAX_CLIENT_LIMITERS
        assert _MAX_CLIENT_LIMITERS > 0
        # Verify it's an OrderedDict (supports LRU eviction)
        from collections import OrderedDict
        assert isinstance(_client_limiters, OrderedDict)

    def test_client_limiters_lru_eviction(self, http_client, monkeypatch):
        from worker import app as worker_app

        worker_app._client_limiters.clear()
        monkeypatch.setattr(worker_app, "_MAX_CLIENT_LIMITERS", 3)

        try:
            store = get_client_store()
            client_ids = []

            for idx in range(4):
                record, api_key = store.register(
                    name=f"Client {idx}",
                    email=f"client{idx}@example.com",
                    tier="free",
                )
                client_ids.append(record.client_id)
                resp = http_client.post(
                    "/run",
                    json={"task": "ping", "input": {"msg": f"client-{idx}"}},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                assert resp.status_code == 200

            assert len(worker_app._client_limiters) == 3
            assert client_ids[0] not in worker_app._client_limiters
            assert client_ids[-1] in worker_app._client_limiters
        finally:
            worker_app._client_limiters.clear()


# ---------------------------------------------------------------------------
# FIX #8 — Duplicate parse block (structural)
# ---------------------------------------------------------------------------


class TestNoDuplicateParseBlock:
    """Ensure the /run handler doesn't double-parse the request body."""

    def test_run_processes_correctly(self, http_client):
        """A simple ping should work without errors from duplicate parsing."""
        resp = http_client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "dedup test"}},
            headers=AUTH,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# FIX #10 — chunk_text infinite loop guard
# ---------------------------------------------------------------------------


class TestChunkTextSafety:
    def test_overlap_equals_chunk_size_raises(self):
        with pytest.raises(ValueError, match="overlap.*must be less than"):
            chunk_text("hello world " * 100, chunk_size=100, overlap=100)

    def test_overlap_greater_than_chunk_size_raises(self):
        with pytest.raises(ValueError, match="overlap.*must be less than"):
            chunk_text("hello world " * 100, chunk_size=50, overlap=100)

    def test_normal_overlap_works(self):
        chunks = chunk_text("hello world " * 100, chunk_size=100, overlap=20)
        assert len(chunks) > 1

    def test_zero_overlap_works(self):
        chunks = chunk_text("hello world " * 100, chunk_size=100, overlap=0)
        assert len(chunks) > 1


# ---------------------------------------------------------------------------
# FIX #7 — check_daily_limit on base class
# ---------------------------------------------------------------------------


class TestBaseClientStoreInterface:
    """Ensure check_daily_limit is on the base ClientStore."""

    def test_base_class_has_check_daily_limit(self):
        from worker.client_auth import ClientStore
        store = ClientStore()
        with pytest.raises(NotImplementedError):
            store.check_daily_limit("any_id")


# ---------------------------------------------------------------------------
# E2E: Full client lifecycle
# ---------------------------------------------------------------------------


class TestClientLifecycleE2E:
    """End-to-end test: register → use → track → rotate → revoke."""

    def test_full_lifecycle(self, http_client):
        # 1. Admin registers a free client
        reg_resp = http_client.post(
            "/run",
            json={"task": "client.register", "input": {
                "name": "E2E Corp", "email": "e2e@example.com", "tier": "free"
            }},
            headers=AUTH,
        )
        assert reg_resp.status_code == 200
        reg_data = reg_resp.json()["result"]
        client_id = reg_data["client_id"]
        api_key = reg_data["api_key"]
        assert api_key.startswith("ubim_")

        # 2. Client uses allowed task (ping)
        ping_resp = http_client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "lifecycle"}},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert ping_resp.status_code == 200

        # 3. Client is blocked from admin tasks
        admin_resp = http_client.post(
            "/run",
            json={"task": "client.list", "input": {}},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert admin_resp.status_code == 403

        # 4. Client is blocked from non-whitelisted tasks
        notion_resp = http_client.post(
            "/run",
            json={"task": "notion.read_page", "input": {"page_id": "x"}},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert notion_resp.status_code == 403

        # 5. Admin checks usage
        usage_resp = http_client.post(
            "/run",
            json={"task": "client.usage", "input": {"client_id": client_id}},
            headers=AUTH,
        )
        assert usage_resp.status_code == 200
        assert usage_resp.json()["result"]["today_requests"] == 1  # the ping

        # 6. Admin rotates key
        rotate_resp = http_client.post(
            "/run",
            json={"task": "client.rotate_key", "input": {"client_id": client_id}},
            headers=AUTH,
        )
        assert rotate_resp.status_code == 200
        new_key = rotate_resp.json()["result"]["new_api_key"]
        assert new_key != api_key

        # 7. Old key no longer works
        old_resp = http_client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "old key"}},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert old_resp.status_code == 401

        # 8. New key works
        new_resp = http_client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "new key"}},
            headers={"Authorization": f"Bearer {new_key}"},
        )
        assert new_resp.status_code == 200

        # 9. Admin revokes
        revoke_resp = http_client.post(
            "/run",
            json={"task": "client.revoke", "input": {"client_id": client_id}},
            headers=AUTH,
        )
        assert revoke_resp.status_code == 200
        assert revoke_resp.json()["result"]["revoked"] is True

        # 10. Revoked key is rejected
        revoked_resp = http_client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "revoked"}},
            headers={"Authorization": f"Bearer {new_key}"},
        )
        assert revoked_resp.status_code == 401
