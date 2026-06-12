"""Tests de routes/pit.py — endpoints /pit/* read-only (PIT-5 P5.1).

Cubre: auth (401/403/200), shapes congelados del plan §4 P5.1, 404s,
422 con ids inválidos SIN tocar filesystem (incl. path traversal %2E%2E),
vault ausente, y no-regresión del namespace /tournaments (D3).
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from tests.mission_control._pit_fixtures import (
    ARCHIVED_PIT_ID,
    DEMO_PIT_ID,
    TOKEN,
    build_demo_vault,
    build_evidence,
)

AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _reload_app():
    import mission_control.config as cfg

    importlib.reload(cfg)
    import mission_control.auth as auth

    importlib.reload(auth)
    import mission_control.app as app_module

    importlib.reload(app_module)
    return app_module


@pytest.fixture
def client(monkeypatch, tmp_path):
    vault = build_demo_vault(tmp_path / "vault")
    evidence = build_evidence(tmp_path / "evidence")
    fallback = tmp_path / "examples"
    fallback.mkdir()
    monkeypatch.setenv("MISSION_CONTROL_TOKEN", TOKEN)
    monkeypatch.setenv("PIT_VAULT_PATH", str(vault))
    monkeypatch.setenv("PIT_EVIDENCE_DIR", str(evidence))
    monkeypatch.setenv("PIT_SPEC_FALLBACK_DIR", str(fallback))
    app_module = _reload_app()
    return TestClient(app_module.app)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_pit_requires_bearer(client):
    assert client.get("/pit/tournaments").status_code == 401


def test_pit_rejects_wrong_bearer(client):
    res = client.get(
        "/pit/tournaments", headers={"Authorization": "Bearer wrong"}
    )
    assert res.status_code == 403


def test_pit_accepts_valid_bearer(client):
    assert client.get("/pit/tournaments", headers=AUTH).status_code == 200


# ---------------------------------------------------------------------------
# GET /pit/tournaments
# ---------------------------------------------------------------------------


def test_list_tournaments_shape(client):
    body = client.get("/pit/tournaments", headers=AUTH).json()
    assert body["read_only"] is True
    assert body["vault"]["available"] is True
    by_id = {t["pit_id"]: t for t in body["tournaments"]}
    assert set(by_id) == {DEMO_PIT_ID, ARCHIVED_PIT_ID}
    demo = by_id[DEMO_PIT_ID]
    assert demo["status"] == "judge_pending"
    assert demo["lanes_complete"] == 2
    assert demo["run_verdict"] == "PIT_RUN_PASS"
    assert demo["archived"] is False
    assert by_id[ARCHIVED_PIT_ID]["status"] == "archived"


def test_list_tournaments_vault_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("MISSION_CONTROL_TOKEN", TOKEN)
    monkeypatch.setenv("PIT_VAULT_PATH", str(tmp_path / "missing"))
    monkeypatch.setenv("PIT_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("PIT_SPEC_FALLBACK_DIR", str(tmp_path / "examples"))
    app_module = _reload_app()
    c = TestClient(app_module.app)
    body = c.get("/pit/tournaments", headers=AUTH).json()
    assert body["vault"]["available"] is False
    assert body["tournaments"] == []


# ---------------------------------------------------------------------------
# GET /pit/tournaments/{pit_id}
# ---------------------------------------------------------------------------


def test_tournament_detail_shape(client):
    res = client.get(f"/pit/tournaments/{DEMO_PIT_ID}", headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["pit_id"] == DEMO_PIT_ID
    assert body["status"] == "judge_pending"
    assert body["spec"]["title"] == "Demo tournament"
    assert len(body["spec"]["kpi_definitions"]) == 2
    lanes = {lane["lane_id"]: lane for lane in body["lanes"]}
    assert list(lanes) == ["lane-alpha", "lane-beta", "lane-gamma"]
    alpha = lanes["lane-alpha"]
    assert alpha["lane_complete"] is True
    assert alpha["fulfillment_score"] == pytest.approx(0.82)
    assert alpha["prototype"]["entry"] == "index.html"
    assert alpha["prototype"]["preview_path"] == (
        f"/pit/preview/{DEMO_PIT_ID}/lane-alpha/2/"
    )
    assert alpha["announce"]["FULFILLMENT"] == "0.82"
    assert lanes["lane-gamma"]["lane_complete"] is False
    assert body["outcome"]["present"] is False
    assert body["evidence"]["verdict"] == "PIT_RUN_PASS"


def test_tournament_detail_archived(client):
    body = client.get(f"/pit/tournaments/{ARCHIVED_PIT_ID}", headers=AUTH).json()
    assert body["archived"] is True
    assert body["outcome"]["winner_lane_id"] == "lane-winner"
    assert body["outcome"]["david_gate"] == "GO"


def test_tournament_detail_unknown_404(client):
    res = client.get("/pit/tournaments/pit-ghost", headers=AUTH)
    assert res.status_code == 404


@pytest.mark.parametrize(
    "bad_pit_id", ["%2E%2E", "PIT-UPPER", "pit_underscore", "ab", "-bad"]
)
def test_tournament_detail_invalid_id_422(client, monkeypatch, bad_pit_id):
    """422 sin tocar filesystem: el adapter no debe ser invocado."""
    from mission_control.adapters import pit_vault

    def _must_not_be_called(*args, **kwargs):
        raise AssertionError("adapter called with invalid pit_id")

    monkeypatch.setattr(pit_vault, "read_tournament", _must_not_be_called)
    res = client.get(f"/pit/tournaments/{bad_pit_id}", headers=AUTH)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# GET /pit/tournaments/{pit_id}/lanes/{lane_id}/kpi/{iteration}
# ---------------------------------------------------------------------------


def test_kpi_pack_happy(client):
    res = client.get(
        f"/pit/tournaments/{DEMO_PIT_ID}/lanes/lane-alpha/kpi/2", headers=AUTH
    )
    assert res.status_code == 200
    body = res.json()
    assert body["pit_id"] == DEMO_PIT_ID
    assert body["lane_id"] == "lane-alpha"
    assert body["iteration"] == 2
    assert body["path"].endswith("/iterations/2/kpi_pack.json")
    assert body["kpi_pack"]["fulfillment_score"] == pytest.approx(0.82)


def test_kpi_pack_missing_404(client):
    res = client.get(
        f"/pit/tournaments/{DEMO_PIT_ID}/lanes/lane-alpha/kpi/9", headers=AUTH
    )
    assert res.status_code == 404
    res = client.get(
        f"/pit/tournaments/{DEMO_PIT_ID}/lanes/lane-ghost/kpi/1", headers=AUTH
    )
    assert res.status_code == 404


@pytest.mark.parametrize(
    ("lane_id", "iteration"),
    [
        ("lane-..", "1"),
        ("%2E%2E", "1"),
        ("notlane", "1"),
        ("lane-alpha", "0"),
        ("lane-alpha", "11"),
        ("lane-alpha", "abc"),
    ],
)
def test_kpi_pack_invalid_input_422(client, monkeypatch, lane_id, iteration):
    from mission_control.adapters import pit_vault

    def _must_not_be_called(*args, **kwargs):
        raise AssertionError("adapter called with invalid input")

    monkeypatch.setattr(pit_vault, "read_kpi_pack", _must_not_be_called)
    res = client.get(
        f"/pit/tournaments/{DEMO_PIT_ID}/lanes/{lane_id}/kpi/{iteration}",
        headers=AUTH,
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# No-regresión: /tournaments (D3) intacto
# ---------------------------------------------------------------------------


def test_d3_tournaments_namespace_unchanged(client):
    res = client.get("/tournaments", headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["read_only"] is True
    assert body["launcher_enabled"] is False
    assert body["active"] == []
