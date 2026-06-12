"""Tests P5.2b — judge UX v2 (/pit/access, /pit/judge/*) + compute_compare.

Cubre: shells HTML sin bearer (y sin datos de vault server-rendered), 422 con
pit_id inválido, guardrails de templates (cero __PASTE_TOKEN__, sessionStorage,
sin <form>/hx-post/assets remotos nuevos), unit tests de compute_compare
(badges direction-aware, empates estrictos sin badge, líder fulfillment,
synthetic_all, bullets "Qué mirar"), payload deep del detail (fulfillment_series
+ kpis_final + compare) y no-regresión del JSON API + /pit v1.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mission_control.adapters.pit_vault import compute_compare
from tests.mission_control._pit_fixtures import (
    DEMO_PIT_ID,
    TOKEN,
    build_demo_vault,
    build_evidence,
)

AUTH = {"Authorization": f"Bearer {TOKEN}"}

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "mission_control" / "templates"


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
# Shells HTML sin bearer (las páginas no exponen datos; el JSON sigue cerrado)
# ---------------------------------------------------------------------------


def test_access_page_200_without_token(client):
    res = client.get("/pit/access")
    assert res.status_code == 200
    assert "MISSION_CONTROL_TOKEN" in res.text
    assert "sessionStorage" in res.text


def test_judge_picker_200_without_token(client):
    res = client.get("/pit/judge")
    assert res.status_code == 200
    assert "sessionStorage" in res.text


def test_judge_detail_200_without_token(client):
    res = client.get(f"/pit/judge/{DEMO_PIT_ID}")
    assert res.status_code == 200
    assert DEMO_PIT_ID in res.text


def test_judge_shells_serve_no_vault_data(client):
    """El shell se renderiza sin tocar el vault: cero lane ids ni KPIs."""
    for url in ("/pit/judge", f"/pit/judge/{DEMO_PIT_ID}"):
        html = client.get(url).text
        assert "lane-alpha" not in html
        assert "lane-beta" not in html
        assert "kpi-activation" not in html
        assert "0.82" not in html


@pytest.mark.parametrize(
    "bad_id",
    ["UPPER-case", "x", "-leading-dash", "tiene_underscore", "a" * 65],
)
def test_judge_detail_invalid_pit_id_422(client, bad_id):
    assert client.get(f"/pit/judge/{bad_id}").status_code == 422


def test_judge_detail_path_traversal_422_no_fs(client):
    res = client.get("/pit/judge/%2E%2E%2Fetc")
    assert res.status_code in (404, 422)


def test_json_api_still_requires_bearer(client):
    """Las páginas abiertas NO aflojan el JSON API (fail-closed intacto)."""
    assert client.get("/pit/tournaments").status_code == 401
    assert client.get(f"/pit/tournaments/{DEMO_PIT_ID}").status_code == 401


# ---------------------------------------------------------------------------
# Guardrails de templates (bugfix __PASTE_TOKEN__ + ADR-009)
# ---------------------------------------------------------------------------


def test_no_paste_token_in_judge_templates():
    """Bugfix P5.2b: cero __PASTE_TOKEN__ en las superficies PIT (pit*.html)."""
    paths = sorted(TEMPLATES_DIR.glob("pit*.html"))
    assert {p.name for p in paths} >= {"pit.html", "pit_access.html", "pit_judge.html"}
    for path in paths:
        assert "__PASTE_TOKEN__" not in path.read_text(encoding="utf-8"), path.name


@pytest.mark.parametrize("name", ["pit_access.html", "pit_judge.html", "pit.html"])
def test_templates_use_sessionstorage_token(name):
    html = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    assert "sessionStorage" in html
    assert "mc_token" in html


@pytest.mark.parametrize("name", ["pit_access.html", "pit_judge.html"])
def test_new_templates_no_action_surface(name):
    html = (TEMPLATES_DIR / name).read_text(encoding="utf-8").lower()
    assert "<form" not in html
    assert "hx-post" not in html
    assert "launch" not in html
    assert "re-run" not in html


@pytest.mark.parametrize("name", ["pit_access.html", "pit_judge.html"])
def test_new_templates_zero_remote_assets(name):
    html = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    assert "https://" not in html.replace("https://developer.mozilla.org", "")
    assert "http://cdn" not in html


@pytest.mark.parametrize("name", ["pit_access.html", "pit_judge.html", "pit.html"])
def test_templates_human_error_messages(name):
    html = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    assert "Túnel caído" in html
    assert "/pit/access" in html


# ---------------------------------------------------------------------------
# compute_compare — unit tests (función pura)
# ---------------------------------------------------------------------------


def _lane(
    lane_id: str,
    fulfillment: float | None,
    kpis: list[dict] | None = None,
    *,
    synthetic_share: float | None = 1.0,
    validated: bool | None = True,
) -> dict:
    return {
        "lane_id": lane_id,
        "fulfillment_score": fulfillment,
        "synthetic_share": synthetic_share,
        "kpis_final": kpis or [],
        "hypothesis_final": {
            "variable": "v",
            "statement": None,
            "kpi_id": "kpi-x",
            "validated": validated,
        },
    }


def _kpi(kpi_id: str, achieved: float, direction: str = "increase", **kw) -> dict:
    return {
        "kpi_id": kpi_id,
        "name": kw.get("name", kpi_id),
        "unit": kw.get("unit", "%"),
        "expected": kw.get("expected", 50),
        "achieved": achieved,
        "direction": direction,
        "synthetic": True,
    }


def test_compare_direction_aware_badges():
    lanes = [
        _lane("lane-a", 1.0, [_kpi("checkin", 74), _kpi("time", 9, "decrease")]),
        _lane("lane-b", 1.0, [_kpi("checkin", 83.3), _kpi("time", 17, "decrease")]),
    ]
    compare = compute_compare(lanes)
    by_kpi = {hl["kpi_id"]: hl["lane_id"] for hl in compare["highlights"]}
    assert by_kpi == {"checkin": "lane-b", "time": "lane-a"}
    labels = [hl["label"] for hl in compare["highlights"]]
    assert all(label.startswith("Mejor ") for label in labels)


def test_compare_strict_tie_no_badge():
    lanes = [
        _lane("lane-a", 1.0, [_kpi("opt-in", 7)]),
        _lane("lane-b", 1.0, [_kpi("opt-in", 7)]),
        _lane("lane-c", 1.0, [_kpi("opt-in", 5)]),
    ]
    compare = compute_compare(lanes)
    assert compare["highlights"] == []


def test_compare_fulfillment_tie_flag():
    lanes = [_lane("lane-a", 1.0), _lane("lane-b", 1.0), _lane("lane-c", 0.999)]
    compare = compute_compare(lanes)
    assert compare["fulfillment_tie"] is True
    assert compare["best_fulfillment"] is None
    assert any("empatado" in bullet for bullet in compare["watch"])


def test_compare_unique_fulfillment_leader():
    lanes = [_lane("lane-a", 0.9), _lane("lane-b", 0.7)]
    compare = compute_compare(lanes)
    assert compare["fulfillment_tie"] is False
    assert compare["best_fulfillment"] == "lane-a"
    assert any("lane-a lidera fulfillment" in bullet for bullet in compare["watch"])


def test_compare_synthetic_all():
    all_synth = compute_compare([_lane("lane-a", 1.0), _lane("lane-b", 1.0)])
    assert all_synth["synthetic_all"] is True
    mixed = compute_compare(
        [_lane("lane-a", 1.0), _lane("lane-b", 1.0, synthetic_share=0.5)]
    )
    assert mixed["synthetic_all"] is False


def test_compare_hypothesis_bullet_counts_validation():
    lanes = [
        _lane("lane-a", 0.9, validated=True),
        _lane("lane-b", 0.7, validated=False),
    ]
    compare = compute_compare(lanes)
    assert any("1/2" in bullet for bullet in compare["watch"])


def test_compare_watch_capped_at_three():
    lanes = [
        _lane("lane-a", 0.9, [_kpi("k1", 10), _kpi("k2", 5, "decrease")]),
        _lane("lane-b", 0.7, [_kpi("k1", 8), _kpi("k2", 9, "decrease")]),
    ]
    compare = compute_compare(lanes)
    assert 1 <= len(compare["watch"]) <= 3
    assert all(isinstance(bullet, str) for bullet in compare["watch"])


def test_compare_empty_lanes():
    compare = compute_compare([])
    assert compare == {
        "fulfillment_tie": False,
        "best_fulfillment": None,
        "highlights": [],
        "watch": [],
        "synthetic_all": False,
    }


# ---------------------------------------------------------------------------
# Payload deep del detail (consumido por pit_judge.html vía fetch)
# ---------------------------------------------------------------------------


def test_detail_payload_has_judge_fields(client):
    body = client.get(f"/pit/tournaments/{DEMO_PIT_ID}", headers=AUTH).json()
    assert "compare" in body
    compare = body["compare"]
    for key in (
        "fulfillment_tie",
        "best_fulfillment",
        "highlights",
        "watch",
        "synthetic_all",
    ):
        assert key in compare
    lanes = {lane["lane_id"]: lane for lane in body["lanes"]}
    alpha = lanes["lane-alpha"]
    assert alpha["fulfillment_series"] == [
        {"n": 1, "fulfillment": 0.4},
        {"n": 2, "fulfillment": 0.82},
    ]
    assert isinstance(alpha["kpis_final"], list) and alpha["kpis_final"]
    final = alpha["kpis_final"][0]
    for key in ("kpi_id", "name", "unit", "expected", "achieved", "direction"):
        assert key in final
    assert body["spec"]["hypothesis_seed"] is None  # fixture sin seed


def test_list_payload_stays_lean(client):
    body = client.get("/pit/tournaments", headers=AUTH).json()
    demo = next(t for t in body["tournaments"] if t["pit_id"] == DEMO_PIT_ID)
    assert "lanes" not in demo
    assert "compare" not in demo
    assert "fulfillment_series" not in str(demo)


# ---------------------------------------------------------------------------
# No-regresión v1
# ---------------------------------------------------------------------------


def test_pit_v1_html_still_renders(client):
    res = client.get("/pit", headers=AUTH)
    assert res.status_code == 200
    assert "__PASTE_TOKEN__" not in res.text
    assert 'hx-trigger="load, click from:#pit-refresh"' in res.text
