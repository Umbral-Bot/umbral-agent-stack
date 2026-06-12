"""Tests de la página GET /pit — dashboard judge PIT-5 P5.2.

Cubre: auth (401/403/200), render con lane_ids del fixture, colores de
fulfillment, outcome/judge-pending, detalle KPI por iteración, vault
ausente, y los guardrails read-only del template (sin polling, sin
botones de acción, sin assets remotos nuevos).
"""

from __future__ import annotations

import importlib
import re

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


@pytest.fixture
def no_vault_client(monkeypatch, tmp_path):
    monkeypatch.setenv("MISSION_CONTROL_TOKEN", TOKEN)
    monkeypatch.setenv("PIT_VAULT_PATH", str(tmp_path / "missing-vault"))
    monkeypatch.setenv("PIT_EVIDENCE_DIR", str(tmp_path / "missing-evidence"))
    monkeypatch.setenv("PIT_SPEC_FALLBACK_DIR", str(tmp_path / "examples"))
    app_module = _reload_app()
    return TestClient(app_module.app)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_pit_page_requires_bearer(client):
    assert client.get("/pit").status_code == 401


def test_pit_page_rejects_wrong_bearer(client):
    res = client.get("/pit", headers={"Authorization": "Bearer wrong"})
    assert res.status_code == 403


def test_pit_page_renders_with_valid_bearer(client):
    res = client.get("/pit", headers=AUTH)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")


# ---------------------------------------------------------------------------
# Render: contenido del fixture
# ---------------------------------------------------------------------------


def test_pit_page_contains_fixture_lane_ids(client):
    html = client.get("/pit", headers=AUTH).text
    assert DEMO_PIT_ID in html
    assert ARCHIVED_PIT_ID in html
    for lane_id in ("lane-alpha", "lane-beta", "lane-gamma", "lane-winner"):
        assert lane_id in html


def test_pit_page_fulfillment_colors(client):
    html = client.get("/pit", headers=AUTH).text
    # lane-alpha 0.82 → verde; lane-beta 0.55 → ámbar; lane-gamma 0.3 → rojo.
    assert re.search(r'class="fulfillment f-ok">0\.82<', html)
    assert re.search(r'class="fulfillment f-warn">0\.55<', html)
    assert re.search(r'class="fulfillment f-err">0\.30<', html)


def test_pit_page_hypothesis_marks(client):
    html = client.get("/pit", headers=AUTH).text
    # lane-alpha validated=true → ✓; lane-beta validated=false → ✗.
    assert "✓" in html
    assert "✗" in html


def test_pit_page_synthetic_share(client):
    html = client.get("/pit", headers=AUTH).text
    assert "50%" in html  # lane-alpha (True, False)
    assert "100%" in html  # lane-beta (True, True)


def test_pit_page_outcome_and_judge_pending(client):
    html = client.get("/pit", headers=AUTH).text
    # pit-old-closed tiene outcome → winner banner.
    assert "lane-winner" in html
    assert "GO" in html
    # pit-judge-demo sin outcome → banner judge pendiente.
    assert "judge pendiente" in html


def test_pit_page_prototype_link_targets_preview(client):
    html = client.get("/pit", headers=AUTH).text
    # lane-alpha iter 2 con prototype → link a /pit/preview/ (P5.3, puede 404).
    assert f"/pit/preview/{DEMO_PIT_ID}/lane-alpha/2/" in html


def test_pit_page_kpi_detail_per_iteration(client):
    html = client.get("/pit", headers=AUTH).text
    # lane-alpha tiene 2 iteraciones con kpi_pack → 2 botones de descarga.
    assert "dlPack('pit-judge-demo', 'lane-alpha', 1)" in html
    assert "dlPack('pit-judge-demo', 'lane-alpha', 2)" in html
    # KPIs del fixture (kpi-0/kpi-1) en el detalle.
    assert "kpi-0" in html
    assert "kpi-1" in html


def test_pit_page_status_badges(client):
    html = client.get("/pit", headers=AUTH).text
    assert "judge_pending" in html  # demo: 2 announces
    assert "closed" in html  # archived con winner


# ---------------------------------------------------------------------------
# Guardrails read-only (ADR-009 / reglas P5.2)
# ---------------------------------------------------------------------------


def test_pit_page_no_polling(client):
    html = client.get("/pit", headers=AUTH).text
    assert "every " not in html  # sin hx-trigger="every Ns" sobre el vault
    assert 'hx-trigger="load, click from:#pit-refresh"' in html


def test_pit_page_no_action_buttons(client):
    html = client.get("/pit", headers=AUTH).text
    assert "hx-post" not in html
    assert "hx-put" not in html
    assert "hx-delete" not in html
    assert "<form" not in html
    for verb in ("re-run", "relaunch", "launch"):
        assert verb not in html.lower()


def test_pit_page_no_new_remote_assets(client):
    html = client.get("/pit", headers=AUTH).text
    # Único asset remoto permitido: el mismo HTMX de index.html (unpkg).
    remote = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    assert remote == ["https://unpkg.com/htmx.org@1.9.12"]
    assert "<iframe" not in html


# ---------------------------------------------------------------------------
# Vault ausente
# ---------------------------------------------------------------------------


def test_pit_page_vault_absent_banner(no_vault_client):
    res = no_vault_client.get("/pit", headers=AUTH)
    assert res.status_code == 200
    html = res.text
    assert "PIT vault no disponible" in html
    assert "Sin torneos en el vault" in html


# ---------------------------------------------------------------------------
# No-regresión: la página no rompe los endpoints JSON /pit/*
# ---------------------------------------------------------------------------


def test_pit_json_namespace_still_works(client):
    body = client.get("/pit/tournaments", headers=AUTH).json()
    assert body["read_only"] is True
    ids = {t["pit_id"] for t in body["tournaments"]}
    assert {DEMO_PIT_ID, ARCHIVED_PIT_ID} <= ids


def test_index_page_still_renders_and_links_pit(client):
    res = client.get("/", headers=AUTH)
    assert res.status_code == 200
    assert 'href="/pit"' in res.text
