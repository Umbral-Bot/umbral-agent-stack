"""
Minimal tests for the Umbral Worker.

Run with:
    cd worker
    python -m pytest ../tests/ -v
"""

import os
import pytest
from fastapi.testclient import TestClient


# Set a test token before importing the app
os.environ.setdefault("WORKER_TOKEN", "test-token-12345")


from worker.app import app  # noqa: E402


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

    def test_health_no_auth_required(self, client):
        # /health should work without any Authorization header
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
            headers={"Authorization": "Bearer test-token-12345"},
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


# ---------------------------------------------------------------------------
# /run — Task dispatch
# ---------------------------------------------------------------------------


class TestRunTasks:
    def test_ping_echoes_input(self, client):
        resp = client.post(
            "/run",
            json={"task": "ping", "input": {"foo": "bar", "n": 42}},
            headers={"Authorization": "Bearer test-token-12345"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["echo"] == {"foo": "bar", "n": 42}

    def test_unknown_task_returns_400(self, client):
        resp = client.post(
            "/run",
            json={"task": "nonexistent_task", "input": {}},
            headers={"Authorization": "Bearer test-token-12345"},
        )
        assert resp.status_code == 400
        assert "Unknown task" in resp.json()["detail"]

    def test_invalid_json_returns_422(self, client):
        resp = client.post(
            "/run",
            content="not json",
            headers={
                "Authorization": "Bearer test-token-12345",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 422
