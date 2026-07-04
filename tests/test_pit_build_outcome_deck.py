"""Tests — scripts/pit/pit_build_outcome_deck.py (PIT-TG-DRIVE Fase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.pit import pit_build_outcome_deck as deck_mod
from tests.pit_qa_helpers import write_real_png

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
    assert len(slides) == 7  # sin stuck_log ni QA screenshots
    assert titles[0].startswith("Torneo PIT")
    assert "Winner y rationale" in titles
    assert "Aprendizajes" in titles

    joined = "\n".join(s["content"] for s in slides)
    assert "lane-a" in joined
    # billing truth: gasto estimado ≠ techo, nunca un "57.5/200" ambiguo
    assert "Gasto estimado: 57.5 USD · techo budget: 200 USD" in joined
    assert "Tokens: not_reported" in joined
    # fulfillment de producto explícito, aunque no esté declarado
    assert "Fulfillment producto: no declarado" in joined
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


def test_build_slides_shows_tokens_and_product_fulfillment() -> None:
    outcome = _outcome_dict()
    outcome["budget"]["tokens_total"] = 6_270_000
    outcome["budget"]["pricing_source"] = "default_gpt5_class_per_mtok_v1"
    outcome["fulfillment_decision"]["product_fulfillment"] = "rejected"
    outcome["human_qa"] = {"status": "QA_PASS"}
    joined = "\n".join(s["content"] for s in deck_mod.build_slides(outcome))
    assert "Tokens: 6270000 · pricing: default_gpt5_class_per_mtok_v1" in joined
    assert "Fulfillment producto: rejected" in joined
    assert "QA producto: QA_PASS" in joined


def test_build_slides_appends_qa_screenshot_slides(tmp_path: Path) -> None:
    shots = [tmp_path / "01-viewer-3d.png", tmp_path / "02-properties.png"]
    for shot in shots:
        write_real_png(shot)
    slides = deck_mod.build_slides(_outcome_dict(), qa_screenshots=shots)
    assert len(slides) == 9  # 7 core + 2 capturas
    assert slides[-2]["title"] == "QA producto — 01-viewer-3d"
    assert slides[-1]["image_path"] == str(shots[1])


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


def test_build_deck_embeds_qa_screenshots(vault: Path) -> None:
    """Con qa-screenshots/ en el vault, el deck ya no sale sin imágenes."""
    pptx = pytest.importorskip("pptx")
    shots_dir = vault / "pit" / PIT_ID / "deliverables" / "qa-screenshots"
    for name in ("01-viewer-3d.png", "02-properties.png", "03-observation.png"):
        write_real_png(shots_dir / name)
    outcome_path = vault / "pit" / PIT_ID / "outcome" / "pit_outcome_report.yaml"
    result = deck_mod.build_deck(outcome_path)
    assert result["ok"] is True
    assert result["slides"] == 10  # 7 core + 3 capturas
    assert result.get("image_count") == 3
    prs = pptx.Presentation(result["path"])
    pictures = [
        shape for slide in prs.slides for shape in slide.shapes if shape.shape_type == 13
    ]
    assert len(pictures) == 3


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
