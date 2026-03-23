"""
Tests for the Umbral Worker — v0.3.0 with TaskEnvelope support.

Run with:
    cd worker
    python -m pytest ../tests/ -v
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient


# Force-set a test token before importing the app.
# Uses os.environ[...] (not setdefault) so it overrides any existing value.
os.environ["WORKER_TOKEN"] = "test-token-12345"


from worker.app import app  # noqa: E402
from worker.models import LegacyRunRequest, TaskEnvelope, TaskStatus, Team, TaskType  # noqa: E402


AUTH = {"Authorization": "Bearer test-token-12345"}


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "ts" in data
        assert data["version"] == "0.4.0"
        assert "tasks_registered" in data

    def test_health_no_auth_required(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /run — Auth
# ---------------------------------------------------------------------------


class TestRunAuth:
    def test_run_without_auth_returns_401(self, client):
        resp = client.post("/run", json={"task": "ping", "input": {}})
        assert resp.status_code == 401

    def test_run_with_wrong_token_returns_401(self, client):
        resp = client.post(
            "/run",
            json={"task": "ping", "input": {}},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_run_with_valid_token_returns_200(self, client):
        resp = client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "hello"}},
            headers=AUTH,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["task"] == "ping"
        assert data["result"]["echo"]["msg"] == "hello"

    def test_run_with_empty_bearer_returns_401(self, client):
        resp = client.post(
            "/run",
            json={"task": "ping", "input": {}},
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    def test_run_unsafe_input_returns_422(self, client):
        resp = client.post(
            "/run",
            json={"task": "ping", "input": {"cmd": "; rm -rf /"}},
            headers=AUTH,
        )
        assert resp.status_code == 422
        assert "unsafe input" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# /run — Legacy format (backward compat)
# ---------------------------------------------------------------------------


class TestRunLegacy:
    def test_ping_echoes_input(self, client):
        resp = client.post(
            "/run",
            json={"task": "ping", "input": {"foo": "bar", "n": 42}},
            headers=AUTH,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["echo"] == {"foo": "bar", "n": 42}

    def test_unknown_task_returns_400(self, client):
        resp = client.post(
            "/run",
            json={"task": "nonexistent_task", "input": {}},
            headers=AUTH,
        )
        assert resp.status_code == 400
        assert "Unknown task" in resp.json()["detail"]

    def test_invalid_json_returns_422(self, client):
        resp = client.post(
            "/run",
            content="not json",
            headers={**AUTH, "Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_legacy_returns_task_id(self, client):
        """Legacy format should still get a generated task_id."""
        resp = client.post(
            "/run",
            json={"task": "ping", "input": {}},
            headers=AUTH,
        )
        data = resp.json()
        assert "task_id" in data
        # Should be a valid UUID
        uuid.UUID(data["task_id"])

    def test_legacy_returns_trace_id(self, client):
        resp = client.post(
            "/run",
            json={"task": "ping", "input": {}},
            headers=AUTH,
        )
        data = resp.json()
        assert "trace_id" in data
        uuid.UUID(data["trace_id"])

    def test_legacy_uses_sanitized_input(self, client):
        from worker.sanitize import MAX_STRING_VALUE_LEN

        resp = client.post(
            "/run",
            json={"task": "ping", "input": {"msg": "x" * 20_000}},
            headers=AUTH,
        )
        assert resp.status_code == 200
        assert len(resp.json()["result"]["echo"]["msg"]) == MAX_STRING_VALUE_LEN


# ---------------------------------------------------------------------------
# /run — TaskEnvelope format
# ---------------------------------------------------------------------------


class TestRunEnvelope:
    def test_envelope_with_all_fields(self, client):
        task_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        resp = client.post(
            "/run",
            json={
                "schema_version": "0.1",
                "task_id": task_id,
                "team": "system",
                "task_type": "general",
                "selected_model": None,
                "status": "queued",
                "trace_id": trace_id,
                "task": "ping",
                "input": {"x": 1},
            },
            headers=AUTH,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["task_id"] == task_id
        assert data["trace_id"] == trace_id
        assert data["team"] == "system"
        assert data["result"]["echo"]["x"] == 1

    def test_envelope_marketing_team(self, client):
        resp = client.post(
            "/run",
            json={
                "schema_version": "0.1",
                "team": "marketing",
                "task_type": "writing",
                "task": "ping",
                "input": {"content": "test"},
            },
            headers=AUTH,
        )
        assert resp.status_code == 200
        assert resp.json()["team"] == "marketing"

    def test_envelope_invalid_team(self, client):
        resp = client.post(
            "/run",
            json={
                "schema_version": "0.1",
                "team": "invalid_team",
                "task": "ping",
                "input": {},
            },
            headers=AUTH,
        )
        assert resp.status_code == 400  # Pydantic validation error

    def test_envelope_fields_without_schema_version_are_preserved(self, client):
        task_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        resp = client.post(
            "/run",
            json={
                "task_id": task_id,
                "team": "improvement",
                "task_type": "coding",
                "trace_id": trace_id,
                "source": "openclaw_gateway",
                "source_kind": "tool_enqueue",
                "task": "ping",
                "input": {"x": 7},
            },
            headers=AUTH,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert data["trace_id"] == trace_id
        assert data["team"] == "improvement"
        assert data["result"]["echo"]["x"] == 7


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}
# ---------------------------------------------------------------------------


class TestGetTask:
    def test_get_task_after_run(self, client):
        task_id = str(uuid.uuid4())
        # Run a task first
        client.post(
            "/run",
            json={
                "schema_version": "0.1",
                "task_id": task_id,
                "task": "ping",
                "input": {"check": True},
            },
            headers=AUTH,
        )
        # Now query it
        resp = client.get(f"/tasks/{task_id}", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert data["status"] == "done"
        assert data["result"]["echo"]["check"] is True
        assert data["started_at"] is not None
        assert data["completed_at"] is not None

    def test_get_nonexistent_task_returns_404(self, client):
        resp = client.get(f"/tasks/{uuid.uuid4()}", headers=AUTH)
        assert resp.status_code == 404

    def test_get_task_requires_auth(self, client):
        resp = client.get(f"/tasks/{uuid.uuid4()}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /tasks (list)
# ---------------------------------------------------------------------------


class TestListTasks:
    def test_list_tasks(self, client):
        # Run a couple tasks
        for i in range(3):
            client.post(
                "/run",
                json={"task": "ping", "input": {"i": i}},
                headers=AUTH,
            )
        resp = client.get("/tasks", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert "total" in data
        assert len(data["tasks"]) > 0

    def test_list_tasks_requires_auth(self, client):
        resp = client.get("/tasks")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Models unit tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_envelope_defaults(self):
        env = TaskEnvelope(task="ping")
        assert env.schema_version == "0.1"
        assert env.team == Team.SYSTEM
        assert env.task_type == TaskType.GENERAL
        assert env.status == TaskStatus.QUEUED
        uuid.UUID(env.task_id)
        uuid.UUID(env.trace_id)
        assert env.input == {}

    def test_legacy_to_envelope(self):
        legacy = LegacyRunRequest(task="ping", input={"a": 1})
        env = legacy.to_envelope()
        assert env.task == "ping"
        assert env.input == {"a": 1}
        assert env.schema_version == "0.1"
        assert env.team == Team.SYSTEM

    def test_from_run_payload_upgrades_envelope_without_schema_version(self):
        env = TaskEnvelope.from_run_payload(
            {
                "task_id": "task-123",
                "team": "marketing",
                "task_type": "writing",
                "trace_id": "trace-123",
                "task": "ping",
                "input": {"a": 1},
            }
        )
        assert env.schema_version == "0.1"
        assert env.task_id == "task-123"
        assert env.team == Team.MARKETING
        assert env.task_type == TaskType.WRITING
        assert env.trace_id == "trace-123"

    def test_task_status_enum(self):
        assert TaskStatus.QUEUED == "queued"
        assert TaskStatus.DONE == "done"
        assert TaskStatus.DEGRADED == "degraded"
