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


# ----------- Voice v3 tests (T10) -----------

def test_score_copy_backwards_compatible_three_args(rules_cfg, proposals):
    """Calling score_copy with the legacy 3-arg signature must still work."""
    res = ev.score_copy(_good_copy(), _good_fixture(proposals), rules_cfg)
    assert isinstance(res, ev.CopyEval)
    # voice fields exist with defaults
    assert hasattr(res, "voice_match_score")
    assert hasattr(res, "voice_dimensions")
    assert hasattr(res, "approved")
    assert hasattr(res, "hard_rejects")


def test_voice_match_score_dimensions_present(rules_cfg, proposals):
    res = ev.score_copy(_good_copy(), _good_fixture(proposals), rules_cfg)
    expected = {
        "technical_clarity",
        "operational_criteria",
        "david_voice_fit",
        "low_repetition",
        "organizational_sensitivity",
        "source_verifiability",
    }
    assert expected.issubset(set(res.voice_dimensions.keys()))
    assert 0.0 <= res.voice_match_score <= 1.0


def test_score_batch_flags_repeated_moderated_phrase(rules_cfg, proposals):
    """If the same moderated phrase appears in >1 copies, V3_HR1 fires."""
    base = _good_copy()
    fixture = _good_fixture(proposals)
    # Both copies contain the moderated phrase "Mi lectura es" already.
    results = ev.score_batch([base, base], [fixture, fixture], rules_cfg)
    rids = [rid for r in results for rid in r.hard_reject_rule_ids]
    assert "V3_HR1_BATCH_REPETITION" in rids


def test_score_batch_flags_repeated_4gram(rules_cfg, proposals):
    """An identical 4-gram appearing in >ngram_max_copies copies triggers HR1."""
    fixture = _good_fixture(proposals)
    # ngram_max_copies = 2, so 3 identical copies must trigger.
    base = _good_copy()
    results = ev.score_batch([base, base, base], [fixture] * 3, rules_cfg)
    rids = [rid for r in results for rid in r.hard_reject_rule_ids]
    assert "V3_HR1_BATCH_REPETITION" in rids


def test_fixture_skip_source_verify_allows_example_domain(rules_cfg, proposals):
    """In fixture mode with skip flag, example.cl source must NOT trigger HR3."""
    fixture = _good_fixture(proposals)
    payload = {
        "id": fixture["id"],
        "titular": fixture["titular"],
        "summary": fixture.get("angulo", ""),
        "key_points": fixture.get("key_points", []),
        "source_url": "https://example.cl/whatever.pdf",
        "fixture_skip_source_verify": True,
    }
    res = ev.score_copy(
        _good_copy(), fixture, rules_cfg,
        source_payload=payload, source_verification_mode="fixture",
    )
    assert "V3_HR3_UNVERIFIED_SOURCE_LIVE" not in res.hard_reject_rule_ids


def test_live_source_verify_rejects_example_domain(rules_cfg, proposals):
    """In live mode, an example.* domain MUST trigger HR3."""
    fixture = {**_good_fixture(proposals), "fixture_skip_source_verify": False}
    payload = {
        "id": fixture["id"],
        "titular": fixture["titular"],
        "summary": fixture.get("angulo", ""),
        "key_points": fixture.get("key_points", []),
        "source_url": "https://example.cl/whatever.pdf",
        "fixture_skip_source_verify": False,
    }
    res = ev.score_copy(
        _good_copy(), fixture, rules_cfg,
        source_payload=payload, source_verification_mode="live",
    )
    assert "V3_HR3_UNVERIFIED_SOURCE_LIVE" in res.hard_reject_rule_ids


def test_unsupported_percentage_rejected(rules_cfg, proposals):
    """A percentage in the copy that does not appear in the source blob → HR2."""
    fixture = _good_fixture(proposals)
    text = (
        "Hook técnico sobre BIM y coordinación de modelos federados.\n\n"
        "Encontré que un 87% de los proyectos AECO en LATAM fallan en gestión "
        "de hallazgos cuando no hay un BEP firmado. Mi lectura es que sin "
        "criterios de revisión claros, BIM se queda en modelado decorativo y "
        "no aporta valor de obra. Lo concreto: definir disciplina de "
        "coordinación entre equipos antes de la primera revisión federada.\n\n"
        "Si tu modelo federado nunca generó un cambio de revisión, "
        "probablemente no lo estás usando para coordinar.\n\n"
        "Fuente: https://example.cl/uc/bim-coordinacion-hospitales-2026.pdf\n\n"
        "#BIM #AECO #Construccion"
    )
    payload = {
        "id": fixture["id"],
        "titular": fixture["titular"],
        "summary": "BIM coordinacion sin porcentajes",
        "key_points": ["coordinación", "hallazgos"],
        "source_url": "https://example.cl/uc/bim-coordinacion-hospitales-2026.pdf",
        "fixture_skip_source_verify": True,
    }
    res = ev.score_copy(
        text, fixture, rules_cfg,
        source_payload=payload, source_verification_mode="fixture",
    )
    assert "V3_HR2_UNSUPPORTED_FACT" in res.hard_reject_rule_ids


def test_confrontational_without_pedagogy_rejected(rules_cfg, proposals):
    """Multiple confrontational signals + no practical exit term → HR4."""
    fixture = _good_fixture(proposals)
    text = (
        "Si tu BIM no entrega valor, no estás haciendo BIM.\n\n"
        "Es ridículo. Nunca lo verán igual. La gente no entiende. "
        "Solo modelan polígonos sueltos sin sentido. Falla todo. "
        "Está mal hace años. Es vergonzoso para el sector AECO. "
        "Reconozcan de una vez que el problema son ustedes.\n\n"
        "Agenda una llamada y descubre el próximo nivel.\n\n"
        "Fuente: https://example.cl/uc/bim-coordinacion-hospitales-2026.pdf\n\n"
        "#BIM #AECO #Construccion"
    )
    payload = {
        "id": fixture["id"], "titular": fixture["titular"],
        "summary": "", "key_points": [],
        "source_url": "https://example.cl/x.pdf",
        "fixture_skip_source_verify": True,
    }
    res = ev.score_copy(
        text, fixture, rules_cfg,
        source_payload=payload, source_verification_mode="fixture",
    )
    assert "V3_HR4_CONFRONTATIONAL_NO_PEDAGOGY" in res.hard_reject_rule_ids


def test_diagnosis_without_practical_exit_rejected(rules_cfg, proposals):
    """A diagnosis copy with no practical-exit cue triggers HR5."""
    fixture = _good_fixture(proposals)
    text = (
        "El sector AECO arrastra un problema serio en LATAM.\n\n"
        "Hay mucho ruido y mucha falla en cómo se entregan modelos. "
        "Lo veo en cada equipo que conozco. Cuello de botella tras cuello "
        "de botella. Riesgo acumulado en cada entrega. "
        "Mucha fricción entre disciplinas. Una pena, la verdad.\n\n"
        "Fuente: https://example.cl/uc/bim-coordinacion-hospitales-2026.pdf\n\n"
        "#BIM #AECO #Construccion"
    )
    payload = {
        "id": fixture["id"], "titular": fixture["titular"],
        "summary": "", "key_points": [],
        "source_url": "https://example.cl/x.pdf",
        "fixture_skip_source_verify": True,
    }
    res = ev.score_copy(
        text, fixture, rules_cfg,
        source_payload=payload, source_verification_mode="fixture",
    )
    assert "V3_HR5_DIAGNOSIS_WITHOUT_PRACTICAL_EXIT" in res.hard_reject_rule_ids


def test_temperatures_cli_report(tmp_path, monkeypatch):
    """CLI with --temperatures must emit a multi-temperature report shape."""
    fixtures_dir = REPO_ROOT / "tests" / "discovery" / "fixtures"
    out = tmp_path / "report.json"
    canned = _good_copy()

    # Stub the gateway-calling helper used inside run_evaluator.
    monkeypatch.setattr(ev, "_call_gateway", lambda *a, **kw: canned, raising=False)

    rc = ev.main([
        "--fixtures", str(fixtures_dir / "stage7_5_proposals.json"),
        "--rules", str(fixtures_dir / "stage7_5_golden_copies.json"),
        "--report", str(out),
        "--temperatures", "0.6,0.8",
        "--dry-run",
        "--source-verification-mode", "fixture",
    ])
    # rc may be 1 because dry-run produces empty copies that fail rules; we only
    # care that the multi-temperature report is well formed.
    assert rc in (0, 1)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "runs_by_temperature" in payload
    assert set(payload["runs_by_temperature"].keys()) == {"0.6", "0.8"}
    assert "aggregate_by_temperature" in payload
    assert "overall" in payload

