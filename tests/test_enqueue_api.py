"""
Tests for POST /enqueue and GET /task/{task_id}/status endpoints.

Uses fakeredis to mock Redis. Run:
    WORKER_TOKEN=test python -m pytest tests/test_enqueue_api.py -v
"""

import json
import os
import uuid
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

# Force test token before importing the app
os.environ["WORKER_TOKEN"] = "test-token-12345"

from worker.app import app  # noqa: E402

AUTH = {"Authorization": "Bearer test-token-12345"}
BAD_AUTH = {"Authorization": "Bearer wrong-token"}
TASK_KEY_PREFIX = "umbral:task:"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_redis():
    """Return a fakeredis client (or skip if not installed)."""
    if not HAS_FAKEREDIS:
        pytest.skip("fakeredis not installed")
    return fakeredis.FakeRedis(decode_responses=True)


# ==========================================================================
# POST /enqueue
# ==========================================================================


class TestEnqueueAuth:
    """Auth is required for /enqueue."""

    def test_enqueue_no_auth_returns_401(self, client):
        resp = client.post("/enqueue", json={"task": "ping"})
        assert resp.status_code == 401

    def test_enqueue_bad_token_returns_401(self, client):
        resp = client.post(
            "/enqueue",
            json={"task": "ping"},
            headers=BAD_AUTH,
        )
        assert resp.status_code == 401


class TestEnqueueValidation:
    """Input validation for /enqueue."""

    def test_enqueue_missing_task_returns_422(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post("/enqueue", json={}, headers=AUTH)
            assert resp.status_code == 422  # Pydantic validation

    def test_enqueue_invalid_task_name_returns_400(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post(
                "/enqueue",
                json={"task": "../../etc/passwd"},
                headers=AUTH,
            )
            assert resp.status_code == 400

    def test_enqueue_unsafe_input_returns_422(self, client):
        resp = client.post(
            "/enqueue",
            json={"task": "ping", "input": {"cmd": "; rm -rf /"}},
            headers=AUTH,
        )
        assert resp.status_code == 422
        assert "unsafe input" in resp.json()["detail"].lower()


class TestEnqueueSuccess:
    """Successful enqueue operations."""

    def test_enqueue_returns_task_id(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post(
                "/enqueue",
                json={"task": "ping", "team": "system", "input": {"msg": "hello"}},
                headers=AUTH,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["queued"] is True
            assert "task_id" in data
            # Verify UUID format
            uuid.UUID(data["task_id"])

    def test_enqueue_stores_in_redis(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post(
                "/enqueue",
                json={"task": "research.web", "team": "marketing", "input": {"query": "test"}},
                headers=AUTH,
            )
            data = resp.json()
            task_id = data["task_id"]

            # Verify data is in Redis
            raw = fake_redis.get(f"{TASK_KEY_PREFIX}{task_id}")
            assert raw is not None
            stored = json.loads(raw)
            assert stored["task"] == "research.web"
            assert stored["team"] == "marketing"
            assert stored["status"] == "queued"
            assert stored["input"]["query"] == "test"

    def test_enqueue_stores_sanitized_input(self, client, fake_redis):
        from worker.sanitize import MAX_STRING_VALUE_LEN

        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post(
                "/enqueue",
                json={"task": "ping", "input": {"msg": "x" * 20_000}},
                headers=AUTH,
            )
            assert resp.status_code == 200
            task_id = resp.json()["task_id"]
            stored = json.loads(fake_redis.get(f"{TASK_KEY_PREFIX}{task_id}"))
            assert len(stored["input"]["msg"]) == MAX_STRING_VALUE_LEN

    def test_enqueue_granola_transcript_keeps_full_content(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post(
                "/enqueue",
                json={
                    "task": "granola.process_transcript",
                    "input": {"title": "Audit", "content": "x" * 20_000},
                },
                headers=AUTH,
            )
            assert resp.status_code == 200
            task_id = resp.json()["task_id"]
            stored = json.loads(fake_redis.get(f"{TASK_KEY_PREFIX}{task_id}"))
            assert len(stored["input"]["content"]) == 20_000

    def test_enqueue_is_in_pending_queue(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post(
                "/enqueue",
                json={"task": "ping"},
                headers=AUTH,
            )
            # Check pending queue has an entry
            pending_len = fake_redis.llen("umbral:tasks:pending")
            assert pending_len == 1

    def test_enqueue_defaults_team_system(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post(
                "/enqueue",
                json={"task": "ping"},
                headers=AUTH,
            )
            data = resp.json()
            task_id = data["task_id"]
            stored = json.loads(fake_redis.get(f"{TASK_KEY_PREFIX}{task_id}"))
            assert stored["team"] == "system"
            assert stored["task_type"] == "general"

    def test_enqueue_custom_task_type(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post(
                "/enqueue",
                json={"task": "llm.generate", "team": "lab", "task_type": "coding"},
                headers=AUTH,
            )
            data = resp.json()
            task_id = data["task_id"]
            stored = json.loads(fake_redis.get(f"{TASK_KEY_PREFIX}{task_id}"))
            assert stored["task_type"] == "coding"
            assert stored["team"] == "lab"

    def test_enqueue_emits_task_queued_event(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis), patch("worker.app.ops_log.task_queued") as task_queued:
            resp = client.post(
                "/enqueue",
                json={"task": "ping", "team": "system", "task_type": "general"},
                headers=AUTH,
            )
            assert resp.status_code == 200
            task_id = resp.json()["task_id"]
            trace_id = json.loads(fake_redis.get(f"{TASK_KEY_PREFIX}{task_id}"))["trace_id"]

        task_queued.assert_called_once_with(
            task_id=task_id,
            task="ping",
            team="system",
            task_type="general",
            trace_id=trace_id,
        )

    def test_enqueue_persists_source_and_relation_context(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.post(
                "/enqueue",
                json={
                    "task": "research.web",
                    "team": "marketing",
                    "task_type": "research",
                    "source": "openclaw_gateway",
                    "source_kind": "tool_enqueue",
                    "notion_track": True,
                    "project_name": "Proyecto Embudo Ventas",
                    "deliverable_name": "Benchmark Ruben Hassid - sistema contenido y funnel",
                    "input": {"query": "test query"},
                },
                headers=AUTH,
            )
            assert resp.status_code == 200
            task_id = resp.json()["task_id"]
            stored = json.loads(fake_redis.get(f"{TASK_KEY_PREFIX}{task_id}"))

        assert stored["source"] == "openclaw_gateway"
        assert stored["source_kind"] == "tool_enqueue"
        assert stored["notion_track"] is True
        assert stored["project_name"] == "Proyecto Embudo Ventas"
        assert stored["deliverable_name"] == "Benchmark Ruben Hassid - sistema contenido y funnel"
        assert stored["input"]["project_name"] == "Proyecto Embudo Ventas"
        assert stored["input"]["deliverable_name"] == "Benchmark Ruben Hassid - sistema contenido y funnel"
        assert stored["input"]["notion_track"] is True

    def test_enqueue_redis_unavailable_returns_503(self, client):
        with patch("worker.app._get_redis", return_value=None):
            resp = client.post(
                "/enqueue",
                json={"task": "ping"},
                headers=AUTH,
            )
            assert resp.status_code == 503
            assert "Redis" in resp.json()["detail"]


# ==========================================================================
# GET /task/{task_id}/status
# ==========================================================================


class TestTaskStatusAuth:
    """Auth is required for /task/{id}/status."""

    def test_status_no_auth_returns_401(self, client):
        resp = client.get("/task/some-id/status")
        assert resp.status_code == 401

    def test_status_bad_token_returns_401(self, client):
        resp = client.get("/task/some-id/status", headers=BAD_AUTH)
        assert resp.status_code == 401


class TestTaskStatusNotFound:
    """404 when task doesn't exist in Redis."""

    def test_status_nonexistent_returns_404(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get(
                f"/task/{uuid.uuid4()}/status",
                headers=AUTH,
            )
            assert resp.status_code == 404


class TestTaskStatusSuccess:
    """Successful status queries."""

    def test_status_queued_task(self, client, fake_redis):
        task_id = str(uuid.uuid4())
        envelope = {
            "task_id": task_id,
            "task": "ping",
            "team": "system",
            "task_type": "general",
            "status": "queued",
            "created_at": "2026-03-04T10:00:00+00:00",
            "queued_at": 1741082400.0,
        }
        fake_redis.set(f"{TASK_KEY_PREFIX}{task_id}", json.dumps(envelope))

        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get(f"/task/{task_id}/status", headers=AUTH)
            assert resp.status_code == 200
            data = resp.json()
            assert data["task_id"] == task_id
            assert data["status"] == "queued"
            assert data["task"] == "ping"
            assert data["team"] == "system"
            assert data["result"] is None

    def test_status_done_task_includes_result(self, client, fake_redis):
        task_id = str(uuid.uuid4())
        envelope = {
            "task_id": task_id,
            "task": "research.web",
            "team": "marketing",
            "task_type": "research",
            "status": "done",
            "result": {"findings": ["item1", "item2"]},
            "created_at": "2026-03-04T10:00:00+00:00",
            "completed_at": 1741086000.0,
        }
        fake_redis.set(f"{TASK_KEY_PREFIX}{task_id}", json.dumps(envelope))

        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get(f"/task/{task_id}/status", headers=AUTH)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "done"
            assert data["result"] == {"findings": ["item1", "item2"]}

    def test_status_failed_task_includes_error(self, client, fake_redis):
        task_id = str(uuid.uuid4())
        envelope = {
            "task_id": task_id,
            "task": "llm.generate",
            "team": "lab",
            "task_type": "coding",
            "status": "failed",
            "error": "Model timeout",
        }
        fake_redis.set(f"{TASK_KEY_PREFIX}{task_id}", json.dumps(envelope))

        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get(f"/task/{task_id}/status", headers=AUTH)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "failed"
            assert data["error"] == "Model timeout"

    def test_status_redis_unavailable_returns_503(self, client):
        with patch("worker.app._get_redis", return_value=None):
            resp = client.get(f"/task/{uuid.uuid4()}/status", headers=AUTH)
            assert resp.status_code == 503


# ==========================================================================
# Integration: enqueue then check status
# ==========================================================================


class TestEnqueueThenStatus:
    """End-to-end: enqueue a task and then check its status."""

    def test_enqueue_then_status_returns_queued(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            # Enqueue
            resp = client.post(
                "/enqueue",
                json={"task": "ping", "team": "system", "input": {"msg": "e2e"}},
                headers=AUTH,
            )
            assert resp.status_code == 200
            task_id = resp.json()["task_id"]

            # Check status
            resp2 = client.get(f"/task/{task_id}/status", headers=AUTH)
            assert resp2.status_code == 200
            data = resp2.json()
            assert data["task_id"] == task_id
            assert data["status"] == "queued"
            assert data["task"] == "ping"
            assert data["team"] == "system"
