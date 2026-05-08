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


# ---------------------------------------------------------------------------
# v2 tests: R13 (batch n-gram), R14 (organizational), R15 (balance),
# R16 (muletilla), R17 (verifiability), weighted scoring, batch mode.
# ---------------------------------------------------------------------------


def test_r14_organizational_token_present(rules_cfg, proposals):
    res = ev.score_copy(_good_copy(), _good_fixture(proposals), rules_cfg)
    r14 = next(r for r in res.rules if r.rule_id == "R14")
    assert r14.passed, f"good copy mentions 'criterio'/'decisión' but R14 failed: {r14.detail}"
    assert r14.severity == "hard"


def test_r14_organizational_token_missing(rules_cfg, proposals):
    # Rebuild a copy that mentions BIM but no organizational token.
    body = (
        "Vi un dato sobre BIM en hospitales chilenos: el 41% del retrabajo MEP era prevenible "
        "con un modelo federado revisado.\n\n"
        "El IFC sin BEP tampoco mueve la aguja. La detecci\u00f3n de clashes en s\u00ed no es el problema, "
        "es la cadena posterior la que falla.\n\n"
        "Si el modelo federado nunca gener\u00f3 un cambio de revisi\u00f3n, BIM se queda en modelado decorativo."
    )
    hook = "Un dato sobre BIM en hospitales chilenos."
    tail = "Fuente: https://example.cl/x.pdf\n\n#BIM #AECO #Construccion"
    copy = f"{hook}\n\n{body}\n\n{tail}"
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    r14 = next(r for r in res.rules if r.rule_id == "R14")
    assert not r14.passed, f"copy without org tokens should fail R14, detail={r14.detail}"


def test_r15_confrontational_hook_requires_propositive_body(rules_cfg, proposals):
    hook = "No estás coordinando, est\u00e1s dibujando planos en pantalla."  # confrontational
    body = (
        "Vi muchos estudios que llaman BIM a algo que no coordina nada. La detecci\u00f3n de clash llega tarde "
        "porque nadie quiere asumir el costo de revisi\u00f3n.\n\n"
        "Te falta protocolo, te falta criterio, y te falta dejar el plano firmado como entregable \u00fanico.\n\n"
        "El BIM federado existe para gestionar decisi\u00f3n, no para imprimir PDFs."
    )
    tail = "Fuente: https://example.cl/x.pdf\n\n#BIM #AECO #Construccion"
    copy = f"{hook}\n\n{body}\n\n{tail}"
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    r15 = next(r for r in res.rules if r.rule_id == "R15")
    assert not r15.passed, "confrontational hook without 2 propositive tokens should fail R15"
    assert r15.severity == "soft"


def test_r15_confrontational_hook_with_propositive_body_passes(rules_cfg, proposals):
    hook = "No estás coordinando si solo dibujás planos firmados como entregable \u00fanico."
    body = (
        "Lo que sirve, en estudios que vimos, es separar 'modelar' de 'coordinar'. Son tareas distintas, "
        "con criterio distinto y rol distinto.\n\n"
        "El camino \u00fatil pasa por un BEP que diga qui\u00e9n decide qu\u00e9, en qu\u00e9 revisi\u00f3n, y con qu\u00e9 trazabilidad.\n\n"
        "Mi propuesta operativa: registrar cada hallazgo BIM con due\u00f1o y due-date. Eso ordena la decisi\u00f3n del equipo."
    )
    tail = "Fuente: https://example.cl/x.pdf\n\n#BIM #AECO #Construccion"
    copy = f"{hook}\n\n{body}\n\n{tail}"
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    r15 = next(r for r in res.rules if r.rule_id == "R15")
    assert r15.passed, f"propositive body should satisfy R15, detail={r15.detail}"


def test_r15_non_confrontational_hook_passes_by_default(rules_cfg, proposals):
    res = ev.score_copy(_good_copy(), _good_fixture(proposals), rules_cfg)
    r15 = next(r for r in res.rules if r.rule_id == "R15")
    assert r15.passed
    assert "not confrontational" in r15.detail


def test_r16_muletilla_per_copy_cap(rules_cfg, proposals):
    base = _good_copy()
    # Inject 'Mi lectura es simple' twice in the same copy.
    bad = base.replace(
        "Mi lectura:",
        "Mi lectura es simple: el problema es de protocolo.\n\nMi lectura es simple, otra vez:",
    )
    res = ev.score_copy(bad, _good_fixture(proposals), rules_cfg)
    r16 = next(r for r in res.rules if r.rule_id == "R16")
    assert not r16.passed, "two occurrences of muletilla in one copy should fail R16"
    assert r16.severity == "soft"


def test_r17_verifiability_dedicated_source_line(rules_cfg, proposals):
    res = ev.score_copy(_good_copy(), _good_fixture(proposals), rules_cfg)
    r17 = next(r for r in res.rules if r.rule_id == "R17")
    assert r17.passed
    assert r17.severity == "soft"


def test_r17_verifiability_url_inline_only_fails(rules_cfg, proposals):
    # URL inline in body, no dedicated 'Fuente:' line.
    body = (
        "Vi un estudio en https://example.cl/uc/bim-coordinacion-hospitales-2026.pdf que muestra "
        "que el 41% del retrabajo MEP era prevenible con coordinaci\u00f3n BIM.\n\n"
        "El criterio del equipo cambia cuando el modelo federado entra al BEP.\n\n"
        "Si no hay protocolo de revisi\u00f3n, el modelo se queda en modelado decorativo."
    )
    hook = "Un dato BIM que merece pausa."
    tail = "#BIM #AECO #Construccion"
    copy = f"{hook}\n\n{body}\n\n{tail}"
    res = ev.score_copy(copy, _good_fixture(proposals), rules_cfg)
    r17 = next(r for r in res.rules if r.rule_id == "R17")
    assert not r17.passed, "URL only inline (no Fuente:/Vía:/Origen: line) should fail R17"


def test_r13_batch_ngram_repetition(rules_cfg, proposals):
    # Construct 3 nearly identical copies sharing a 4-gram phrase.
    shared_body = (
        "el problema no es el modelo es la decisi\u00f3n del equipo coordinador BIM en obra "
        "porque sin criterio operativo claro la herramienta no resuelve nada relevante."
    )
    hooks = [
        "Hook uno sobre coordinaci\u00f3n BIM en obra.",
        "Hook dos sobre coordinaci\u00f3n BIM en obra.",
        "Hook tres sobre coordinaci\u00f3n BIM en obra.",
    ]
    copies = [
        f"{h}\n\n{shared_body}\n\n{shared_body}\n\nFuente: https://x.com/{i}\n\n#BIM #AECO #Construccion"
        for i, h in enumerate(hooks)
    ]

    canned = iter(copies)

    def stub(_s, _u):
        return next(canned)

    fixture = _good_fixture(proposals)
    results = ev.run_evaluator([fixture, fixture, fixture], rules_cfg, llm_call=stub, model="stub")
    # Before batch rules: R13 passes by default.
    assert all(any(r.rule_id == "R13" and r.passed for r in res.rules) for res in results)
    ev.apply_batch_rules(results, rules_cfg)
    # After batch rules: all 3 should fail R13 (they share many 4-grams across >2 copies).
    failed = [res for res in results if any(r.rule_id == "R13" and not r.passed for r in res.rules)]
    assert len(failed) == 3, f"expected 3 R13 failures, got {len(failed)}"


def test_r13_batch_diverse_copies_pass(rules_cfg, proposals):
    # Two copies, no shared 4-gram of substantive content.
    copy_a = (
        "Hook A sobre BIM hospitalario.\n\n"
        "Vi un dato concreto: el 41% del retrabajo MEP es prevenible. El criterio del equipo coordinador cambia.\n\n"
        "El proceso de revisi\u00f3n importa m\u00e1s que la herramienta. Decisi\u00f3n y rol claro destraban la adopci\u00f3n.\n\n"
        "Fuente: https://example.cl/a.pdf\n\n#BIM #AECO #Construccion"
    )
    copy_b = (
        "Hook B distinto sobre IFC abierto.\n\n"
        "Otro mundo: paper sobre LLM leyendo modelos. Funciona bien para naming, mal para sem\u00e1ntica compleja.\n\n"
        "Lo que cambia para el rol: curaduria humana sigue siendo decisiva. Trazabilidad explicita es la clave.\n\n"
        "Fuente: https://arxiv.org/abs/x\n\n#IFC #IA #BIM"
    )
    canned = iter([copy_a, copy_b])

    def stub(_s, _u):
        return next(canned)

    f1 = _good_fixture(proposals)
    f2 = next(p for p in proposals if p["id"] == "F2-bim-plus-ia-paper")
    results = ev.run_evaluator([f1, f2], rules_cfg, llm_call=stub, model="stub")
    ev.apply_batch_rules(results, rules_cfg)
    for res in results:
        r13 = next(r for r in res.rules if r.rule_id == "R13")
        assert r13.passed, f"diverse copies should not trip R13, detail={r13.detail}"


def test_r16_batch_only_first_muletilla_passes(rules_cfg, proposals):
    base = _good_copy()
    # Two copies, both contain the muletilla once.
    copy_a = base.replace("Mi lectura:", "Mi lectura es simple:")
    copy_b = base.replace("Mi lectura:", "Mi lectura es simple:")
    canned = iter([copy_a, copy_b])

    def stub(_s, _u):
        return next(canned)

    f1 = _good_fixture(proposals)
    f2 = next(p for p in proposals if p["id"] == "F2-bim-plus-ia-paper")
    results = ev.run_evaluator([f1, f2], rules_cfg, llm_call=stub, model="stub")
    ev.apply_batch_rules(results, rules_cfg)
    r16_a = next(r for r in results[0].rules if r.rule_id == "R16")
    r16_b = next(r for r in results[1].rules if r.rule_id == "R16")
    assert r16_a.passed, "first copy with muletilla should still pass R16"
    assert not r16_b.passed, "second copy with muletilla should fail R16 (batch cap=1)"


def test_voice_match_score_weighted_sum(rules_cfg, proposals):
    res = ev.score_copy(_good_copy(), _good_fixture(proposals), rules_cfg)
    # All rules pass on _good_copy → weighted score = sum of weights = 1.0.
    assert res.score == pytest.approx(1.0, abs=1e-3)


def test_voice_match_score_failing_dimension_drops_score(rules_cfg, proposals):
    # Trip R8 (marketing slop) → tono_david dimension drops 1/5 of its weight.
    bad = _good_copy().replace("Mi lectura:", "Esta transformación digital:")
    res = ev.score_copy(bad, _good_fixture(proposals), rules_cfg)
    # tono_david weight is 0.20, dropping 1 of 5 rules in it means -0.04 from score.
    assert res.score < 1.0
    assert res.score >= 0.95, f"single soft-side rule should not crater score, got {res.score}"


def test_hard_rule_set_includes_r13_r14():
    assert "R13" in ev.HARD_RULES
    assert "R14" in ev.HARD_RULES
    assert "R15" in ev.SOFT_RULES
    assert "R16" in ev.SOFT_RULES
    assert "R17" in ev.SOFT_RULES
