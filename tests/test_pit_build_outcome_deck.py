"""Tests — scripts/pit/pit_build_outcome_deck.py (PIT-TG-DRIVE Fase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.pit import pit_build_outcome_deck as deck_mod

PIT_ID = "pit-deck-test"


def _outcome_dict(with_stuck: bool = False) -> dict:
    outcome = {
        "schema_version": 1,
        "pit_id": PIT_ID,
        "title": "Torneo de prueba",
        "dates": {"started_at": "2026-07-01", "closed_at": "2026-07-03"},
        "budget": {"budget_usd": 200, "usd_estimated_spent": 57.5},
        "lanes": [
            {
                "lane_id": "lane-a",
                "hypothesis_final": "menos fricción sube adopción",
                "hypothesis_validated": True,
                "iterations_run": 4,
                "prototype_url": "http://127.0.0.1:18089/pit/preview/x",
                "fulfillment_score": 0.82,
                "status": "complete",
            },
            {
                "lane_id": "lane-b",
                "hypothesis_validated": False,
                "fulfillment_score": 0.4,
                "status": "complete",
            },
        ],
        "winner": {
            "lane_id": "lane-a",
            "rationale": "- mayor fulfillment\n- hipótesis validada\n- señal KPI real",
            "david_gate": "ok, cierro el torneo",
        },
        "kpi_summary": [
            {
                "kpi_id": "adopcion",
                "unit": "%",
                "kpi_expected": 60,
                "kpi_achieved": 72,
                "synthetic_share": 1.0,
            }
        ],
        "learnings": {
            "validated": ["la fricción es la variable clave"],
            "refuted": ["el tono formal no mejora opt-in"],
            "inconclusive": [],
        },
        "stuck_log": [],
        "fulfillment_decision": {"next_step": "fulfillment-track", "notes": "seguir con lane-a"},
    }
    if with_stuck:
        outcome["stuck_log"] = [
            {
                "lane_id": "lane-b",
                "card": "research nudges",
                "blocker": "sin fuentes",
                "resolution": "re-scope",
            }
        ]
    return outcome


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    outcome_dir = root / "pit" / PIT_ID / "outcome"
    outcome_dir.mkdir(parents=True)
    (outcome_dir / "pit_outcome_report.yaml").write_text(
        yaml.safe_dump(_outcome_dict(), allow_unicode=True), encoding="utf-8"
    )
    spec_dir = root / "pit" / PIT_ID / "spec"
    spec_dir.mkdir(parents=True)
    (spec_dir / "pit_spec.yaml").write_text(
        yaml.safe_dump(
            {
                "pit_id": PIT_ID,
                "title": "Torneo de prueba",
                "problem_statement": "Carga mental sin señales tempranas.",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return root


# ---------------------------------------------------------------------------
# build_slides — mapeo puro
# ---------------------------------------------------------------------------


def test_build_slides_core_structure() -> None:
    slides = deck_mod.build_slides(_outcome_dict(), spec={"problem_statement": "El problema."})
    titles = [s["title"] for s in slides]
    assert len(slides) == 7  # sin stuck_log
    assert titles[0].startswith("Torneo PIT")
    assert "Winner y rationale" in titles
    assert "Aprendizajes" in titles

    joined = "\n".join(s["content"] for s in slides)
    assert "lane-a" in joined
    assert "57.5 / 200 USD" in joined
    assert "ok, cierro el torneo" in joined
    assert "72 vs 60 %" in joined
    assert "El problema." in joined
    # preview siempre como hint de túnel, nunca URL pública
    assert f"/pit/judge/{PIT_ID}" in joined


def test_build_slides_includes_stuck_when_present() -> None:
    slides = deck_mod.build_slides(_outcome_dict(with_stuck=True))
    assert len(slides) == 8
    assert slides[-1]["title"] == "Stuck log"
    assert "research nudges" in slides[-1]["content"]


def test_build_slides_handles_template_placeholders() -> None:
    outcome = _outcome_dict()
    outcome["winner"]["david_gate"] = "<frase literal de David que autorizó el cierre, o pending>"
    slides = deck_mod.build_slides(outcome)
    winner_slide = next(s for s in slides if s["title"] == "Winner y rationale")
    assert "Gate David: pending" in winner_slide["content"]


# ---------------------------------------------------------------------------
# build_deck + CLI
# ---------------------------------------------------------------------------


def test_default_output_path_convention(vault: Path) -> None:
    outcome_path = vault / "pit" / PIT_ID / "outcome" / "pit_outcome_report.yaml"
    out = deck_mod.default_output_path(outcome_path, PIT_ID)
    assert out == vault / "pit" / PIT_ID / "deliverables" / f"{PIT_ID}-outcome-deck.pptx"


def test_build_deck_writes_pptx(vault: Path) -> None:
    pytest.importorskip("pptx")
    outcome_path = vault / "pit" / PIT_ID / "outcome" / "pit_outcome_report.yaml"
    result = deck_mod.build_deck(outcome_path)
    assert result["ok"] is True
    assert result["pit_id"] == PIT_ID
    deck_path = Path(result["path"])
    assert deck_path.is_file()
    assert deck_path.name == f"{PIT_ID}-outcome-deck.pptx"
    assert deck_path.parent.name == "deliverables"


def test_main_verdict_ok(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pytest.importorskip("pptx")
    outcome_path = vault / "pit" / PIT_ID / "outcome" / "pit_outcome_report.yaml"
    rc = deck_mod.main(["--outcome", str(outcome_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PIT_DECK_BUILD_OK" in out


def test_main_fails_on_missing_outcome(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = deck_mod.main(["--outcome", str(tmp_path / "nope.yaml")])
    out = capsys.readouterr().out
    assert rc == 1
    assert "PIT_DECK_BUILD_FAIL" in out
    assert "outcome_missing" in out
