"""Tests de routes/health.py y auth/bearer."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MISSION_CONTROL_TOKEN", "test-token-123")
    # Forzar reimport para que config.TOKEN tome el env nuevo.
    import mission_control.config as cfg
    importlib.reload(cfg)
    import mission_control.auth as auth
    importlib.reload(auth)
    import mission_control.app as app_module
    importlib.reload(app_module)
    return TestClient(app_module.app)


def test_health_is_anonymous(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "mission_control"
    assert "timestamp" in body


def test_authenticated_endpoint_requires_bearer(client):
    res = client.get("/tournaments")
    assert res.status_code == 401


def test_authenticated_endpoint_rejects_wrong_bearer(client):
    res = client.get("/tournaments", headers={"Authorization": "Bearer wrong"})
    assert res.status_code == 403


def test_authenticated_endpoint_accepts_valid_bearer(client):
    res = client.get(
        "/tournaments", headers={"Authorization": "Bearer test-token-123"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["active"] == []
    assert "note" in body


def test_503_when_token_unset(monkeypatch):
    monkeypatch.delenv("MISSION_CONTROL_TOKEN", raising=False)
    import mission_control.config as cfg
    importlib.reload(cfg)
    import mission_control.auth as auth
    importlib.reload(auth)
    import mission_control.app as app_module
    importlib.reload(app_module)
    c = TestClient(app_module.app)
    # /health sigue funcionando.
    assert c.get("/health").status_code == 200
    # Rutas autenticadas: 503 (fail-closed).
    res = c.get("/tournaments", headers={"Authorization": "Bearer x"})
    assert res.status_code == 503
