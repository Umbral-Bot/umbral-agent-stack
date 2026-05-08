"""Unit tests for the Stage 7.5 LinkedIn copy evaluator.

These tests do NOT call the OpenClaw gateway. They exercise:
  * `score_copy` against synthetic copies that are designed to pass / fail
    each rule deterministically.
  * `run_evaluator` with a stub LLM that returns a precomputed copy per
    fixture, to verify the end-to-end pipeline (prompt build → score →
    aggregate) without network.
  * `build_copy_prompt` to verify the placeholder contract used by Hilo A.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "discovery"))

import eval_stage7_5_copy as ev  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "tests" / "discovery" / "fixtures"


@pytest.fixture(scope="module")
def rules_cfg() -> dict:
    return json.loads((FIXTURES_DIR / "stage7_5_golden_copies.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def proposals() -> list[dict]:
    return json.loads((FIXTURES_DIR / "stage7_5_proposals.json").read_text(encoding="utf-8"))


def _good_copy() -> str:
    body = (
        "Leí un estudio que mira coordinación BIM en hospitales chilenos y el dato "
        "que más me hizo pensar es que el 41% del retrabajo MEP era detectable "
        "antes de obra si el modelo federado se hubiera revisado contra el BEP.\n\n"
        "Mi lectura: el problema no es detectar el clash, es decidir quién lo asume "
        "y en qué revisión. Sin un protocolo claro de gestión de hallazgos, BIM se "
        "queda en modelado decorativo.\n\n"
        "Eso aplica a casi cualquier proyecto que vimos acompañando equipos. La "
        "tecnología está. Lo que falta es disciplina de coordinación entre "
        "disciplinas y un BEP firmado que aterrice criterios.\n\n"
        "Si tu modelo federado nunca generó un cambio de revisión, probablemente "
        "no lo estás usando para coordinar."
    )
    hook = "El 41% del retrabajo en hospitales chilenos era prevenible con coordinación BIM real."
    tail = "Fuente: https://example.cl/uc/bim-coordinacion-hospitales-2026.pdf\n\n#BIM #AECO #Construccion"
    return f"{hook}\n\n{body}\n\n{tail}"


def _good_fixture(proposals):
    return next(p for p in proposals if p["id"] == "F1-bim-only-clash-detection")


def test_score_copy_all_rules_pass(rules_cfg, proposals):
    res = ev.score_copy(_good_copy(), _good_fixture(proposals), rules_cfg)
    failed = [r.rule_id for r in res.rules if not r.passed]
    assert failed == [], f"expected zero failures, got {failed} on copy of len={len(_good_copy())}"
    assert res.score >= 0.99
    assert res.hard_pass_ratio == 1.0


def test_r1_total_length_too_short(rules_cfg, proposals):
    short = "hook corto.\n\nfin.\n\nFuente: https://x.com/a\n\n#BIM #AECO #Construccion"
    res = ev.score_copy(short, _good_fixture(proposals), rules_cfg)
    rids = {r.rule_id for r in res.rules if not r.passed}
    assert "R1" in rids


def test_r2_hook_too_long(rules_cfg, proposals):
    long_hook = "x" * 200
    body = "p1 con BIM e IFC y bastante texto para llenar el cuerpo. " * 25
    copy = f"{long_hook}\n\n{body}\n\np2.\n\np3.\n\nFuente: https://x.com/a\n\n#BIM #AECO #Construccion"
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    assert any(r.rule_id == "R2" and not r.passed for r in res.rules)


def test_r4_missing_url(rules_cfg, proposals):
    copy = _good_copy().replace("https://example.cl/uc/bim-coordinacion-hospitales-2026.pdf", "(omitida)")
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    assert any(r.rule_id == "R4" and not r.passed for r in res.rules)


def test_r5_too_few_hashtags(rules_cfg, proposals):
    copy = _good_copy().replace("#BIM #AECO #Construccion", "#BIM #AECO")
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    assert any(r.rule_id == "R5" and not r.passed for r in res.rules)


def test_r5_too_many_hashtags(rules_cfg, proposals):
    copy = _good_copy().replace("#BIM #AECO #Construccion", "#BIM #AECO #Construccion #IFC #Revit #Dynamo")
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    assert any(r.rule_id == "R5" and not r.passed for r in res.rules)


def test_r6_unknown_hashtag_soft_fail(rules_cfg, proposals):
    copy = _good_copy().replace("#Construccion", "#RandomTag")
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    r6 = next(r for r in res.rules if r.rule_id == "R6")
    assert not r6.passed
    assert r6.severity == "soft"


def test_r7_emoji_blocked(rules_cfg, proposals):
    copy = _good_copy().replace("Mi lectura:", "🚀 Mi lectura:")
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    assert any(r.rule_id == "R7" and not r.passed for r in res.rules)


def test_r8_marketing_slop_blocked(rules_cfg, proposals):
    copy = _good_copy().replace("Mi lectura:", "Esta transformación digital powered by AI:")
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    failed = {r.rule_id for r in res.rules if not r.passed}
    assert "R8" in failed


def test_r9_usted_blocked(rules_cfg, proposals):
    copy = _good_copy().replace("tu modelo federado", "su modelo federado, usted sabe")
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    assert any(r.rule_id == "R9" and not r.passed for r in res.rules)


def test_r11_cta_blocked(rules_cfg, proposals):
    copy = _good_copy().replace("no lo estás usando para coordinar.", "Agendá tu demo y descúbrelo.")
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    assert any(r.rule_id == "R11" and not r.passed for r in res.rules)


def test_r12_discipline_present(rules_cfg, proposals):
    res = ev.score_copy(_good_copy(), _good_fixture(proposals), rules_cfg)
    r12 = next(r for r in res.rules if r.rule_id == "R12")
    assert r12.passed


def test_r12_discipline_missing(rules_cfg, proposals):
    proposal = {**_good_fixture(proposals), "disciplines": ["LowCode"]}
    res = ev.score_copy(_good_copy(), proposal, rules_cfg)
    r12 = next(r for r in res.rules if r.rule_id == "R12")
    assert not r12.passed


def test_build_copy_prompt_placeholders(proposals):
    sysmsg, user = ev.build_copy_prompt(proposals[0])
    assert "Rick" in sysmsg
    assert proposals[0]["titular"] in user
    assert proposals[0]["source_url"] in user
    assert "{titular}" not in user
    assert "{summary}" not in user


def test_run_evaluator_with_stub_llm(rules_cfg, proposals):
    canned = _good_copy()

    def stub(_sys, _user):
        return canned

    results = ev.run_evaluator(proposals[:2], rules_cfg, llm_call=stub, model="stub")
    assert len(results) == 2
    # Canned copy mentions "BIM" so R12 passes for any fixture that includes BIM
    f1 = [r for r in results if r.fixture_id == "F1-bim-only-clash-detection"][0]
    assert f1.hard_pass_ratio == 1.0
    r12 = next(r for r in f1.rules if r.rule_id == "R12")
    assert r12.passed


def test_run_evaluator_handles_llm_error(rules_cfg, proposals):
    def boom(_s, _u):
        raise RuntimeError("gateway down")

    results = ev.run_evaluator(proposals[:1], rules_cfg, llm_call=boom, model="stub")
    assert len(results) == 1
    assert results[0].error is not None
    assert "gateway down" in results[0].error


def test_aggregate(rules_cfg, proposals):
    canned = _good_copy()
    results = ev.run_evaluator(proposals, rules_cfg, llm_call=lambda s, u: canned, model="stub")
    agg = ev.aggregate(results, rules_cfg)
    assert agg["n"] == len(proposals)
    assert 0.0 < agg["score"] <= 1.0
    assert "R1" in agg["rule_pass_pct"]


def test_split_post_separates_hashtag_line():
    copy = "hook here.\n\nbody p1.\n\nbody p2.\n\nFuente: https://x.com/a\n\n#BIM #AECO #IFC"
    parts = ev._split_post(copy)
    assert parts["hook"] == "hook here."
    assert "#BIM" in parts["hashtag_line"]
    assert "Fuente" not in parts["body"]
