"""Tests for the PIT spec v1 contract (schema + pydantic validator)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from scripts.pit.pit_spec_validate import (
    PIT_ASPECT_RATIOS,
    PIT_DEFAULT_ASPECT_RATIO,
    PROTOTYPE_OUTPUTS,
    RESEARCH_PROFILES,
    PitSpec,
    PitSpecV2,
    compute_fulfillment,
    is_broker_spec,
    main,
    validate_broker_file,
    validate_file,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = REPO_ROOT / "examples" / "pit-salud-mental-pilot.yaml"
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "pit-spec-v1.schema.json"
KPI_PACK_SCHEMA_PATH = (
    REPO_ROOT
    / "openclaw"
    / "workspace-templates"
    / "pit-vault"
    / "templates"
    / "kpi-pack.schema.json"
)


def _valid_spec(**overrides) -> dict:
    base = dict(
        pit_id="pit-test-run",
        title="Test tournament",
        problem_statement="Explore a test problem",
        lane_count=3,
        iteration_count=5,
        budget_usd=200,
        kpi_definitions=[
            {"kpi_id": "kpi_a", "name": "KPI A", "unit": "%", "kpi_expected": 60},
        ],
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Example file — canonical pilot
# ---------------------------------------------------------------------------


def test_example_pilot_passes_pydantic():
    result = validate_file(EXAMPLE_PATH)
    assert result["status"] == "pass", result["errors"]
    assert result["spec"]["pit_id"] == "pit-salud-mental-pilot"
    assert result["spec"]["lane_count"] == 3
    assert result["spec"]["iteration_count"] == 5
    assert result["spec"]["budget_usd"] == 200
    assert result["spec"]["prototype_output"] == "html"
    assert result["spec"]["research_profile"] == "mixed"
    assert result["spec"]["visual_aspect_ratio"] == "4:3"
    assert result["spec"]["preview_mode"] == "tunnel+mission-control"


def test_example_pilot_passes_json_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    data = yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=schema)


def test_validate_file_missing_path_fails(tmp_path):
    result = validate_file(tmp_path / "nope.yaml")
    assert result["status"] == "fail"
    assert any("not found" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# Required-from-David fields: no silent defaults
# ---------------------------------------------------------------------------


def test_budget_usd_is_required_no_default():
    spec = _valid_spec()
    spec.pop("budget_usd")
    with pytest.raises(ValidationError):
        PitSpec.model_validate(spec)


def test_budget_usd_must_be_positive():
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(budget_usd=0))


def test_iteration_count_is_required():
    spec = _valid_spec()
    spec.pop("iteration_count")
    with pytest.raises(ValidationError):
        PitSpec.model_validate(spec)


@pytest.mark.parametrize("iterations", [1, 11])
def test_iteration_count_range_2_10(iterations):
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(iteration_count=iterations))


@pytest.mark.parametrize("lanes", [1, 6])
def test_lane_count_range_2_5(lanes):
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(lane_count=lanes))


# ---------------------------------------------------------------------------
# Enums + invariants
# ---------------------------------------------------------------------------


def test_mode_is_product_only():
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(mode="code"))


def test_prototype_output_enum():
    for output in PROTOTYPE_OUTPUTS:
        PitSpec.model_validate(_valid_spec(prototype_output=output))
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(prototype_output="pdf"))


def test_research_profile_enum():
    for profile in RESEARCH_PROFILES:
        PitSpec.model_validate(_valid_spec(research_profile=profile))
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(research_profile="vibes"))


def test_kpi_definitions_require_at_least_one():
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(kpi_definitions=[]))


def test_kpi_ids_must_be_unique():
    kpis = [
        {"kpi_id": "kpi_a", "name": "A", "unit": "%", "kpi_expected": 10},
        {"kpi_id": "kpi_a", "name": "A2", "unit": "%", "kpi_expected": 20},
    ]
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(kpi_definitions=kpis))


def test_kpi_expected_positive_for_increase():
    kpis = [{"kpi_id": "kpi_a", "name": "A", "unit": "%", "kpi_expected": 0}]
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(kpi_definitions=kpis))


def test_unknown_top_level_field_rejected():
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(public_url="https://example.com"))


# ---------------------------------------------------------------------------
# Visual Magnific 4:3 canonical default
# ---------------------------------------------------------------------------


def test_visual_generation_defaults_to_4_3_magnific():
    spec = PitSpec.model_validate(_valid_spec())
    assert spec.visual_generation.provider == "magnific"
    assert spec.visual_generation.aspect_ratio == "4:3"
    assert PIT_DEFAULT_ASPECT_RATIO == "4:3"


def test_visual_aspect_ratio_allowed_set():
    for ratio in PIT_ASPECT_RATIOS:
        PitSpec.model_validate(
            _valid_spec(visual_generation={"enabled": True, "aspect_ratio": ratio})
        )
    with pytest.raises(ValidationError):
        PitSpec.model_validate(
            _valid_spec(visual_generation={"enabled": True, "aspect_ratio": "3:2"})
        )


def test_synthetic_personas_always_labeled():
    with pytest.raises(ValidationError):
        PitSpec.model_validate(
            _valid_spec(synthetic_personas={"enabled": True, "labeled": False})
        )


def test_preview_mode_rejects_public_url():
    with pytest.raises(ValidationError):
        PitSpec.model_validate(_valid_spec(preview_mode="public-url"))


def test_budget_per_lane():
    spec = PitSpec.model_validate(_valid_spec(budget_usd=200, lane_count=4))
    assert spec.budget_per_lane_usd == 50


# ---------------------------------------------------------------------------
# fulfillment_score formula (docs/ops/pit-kanban-kpi-protocol.md)
# ---------------------------------------------------------------------------


def test_fulfillment_increase_partial():
    kpis = [{"kpi_expected": 60, "kpi_achieved": 30, "direction": "increase"}]
    assert compute_fulfillment(kpis) == 0.5


def test_fulfillment_increase_clamps_overshoot_to_1():
    kpis = [{"kpi_expected": 60, "kpi_achieved": 120, "direction": "increase"}]
    assert compute_fulfillment(kpis) == 1.0


def test_fulfillment_decrease_at_or_below_target_is_1():
    kpis = [{"kpi_expected": 30, "kpi_achieved": 30, "direction": "decrease"}]
    assert compute_fulfillment(kpis) == 1.0
    kpis = [{"kpi_expected": 30, "kpi_achieved": 0, "direction": "decrease"}]
    assert compute_fulfillment(kpis) == 1.0


def test_fulfillment_decrease_above_target_scales_down():
    kpis = [{"kpi_expected": 30, "kpi_achieved": 60, "direction": "decrease"}]
    assert compute_fulfillment(kpis) == 0.5


def test_fulfillment_weighted_mix():
    kpis = [
        {"kpi_expected": 60, "kpi_achieved": 60, "direction": "increase", "weight": 2.0},
        {"kpi_expected": 30, "kpi_achieved": 60, "direction": "decrease", "weight": 1.0},
        {"kpi_expected": 5, "kpi_achieved": 0, "direction": "increase", "weight": 1.0},
    ]
    # (2*1.0 + 1*0.5 + 1*0.0) / 4 = 0.625 -> 0.62 (banker's) o 0.63; round() de
    # Python usa banker's rounding: round(0.625, 2) == 0.62
    assert compute_fulfillment(kpis) == round(2.5 / 4, 2)


def test_fulfillment_rejects_empty_and_bad_inputs():
    with pytest.raises(ValueError):
        compute_fulfillment([])
    with pytest.raises(ValueError):
        compute_fulfillment(
            [{"kpi_expected": 0, "kpi_achieved": 1, "direction": "increase"}]
        )
    with pytest.raises(ValueError):
        compute_fulfillment(
            [{"kpi_expected": 1, "kpi_achieved": 1, "direction": "sideways"}]
        )
    with pytest.raises(ValueError):
        compute_fulfillment(
            [{"kpi_expected": 1, "kpi_achieved": 1, "weight": 0}]
        )


# ---------------------------------------------------------------------------
# JSON Schema <-> pydantic coherence (anti-drift)
# ---------------------------------------------------------------------------


def test_schema_file_matches_model_invariants():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    props = schema["properties"]

    assert set(schema["required"]) == {
        "pit_id",
        "title",
        "problem_statement",
        "lane_count",
        "iteration_count",
        "budget_usd",
        "kpi_definitions",
    }
    assert props["lane_count"]["minimum"] == 2
    assert props["lane_count"]["maximum"] == 5
    assert props["iteration_count"]["minimum"] == 2
    assert props["iteration_count"]["maximum"] == 10
    assert props["budget_usd"]["exclusiveMinimum"] == 0
    assert "default" not in props["budget_usd"], "budget_usd must not have a default"
    assert "default" not in props["iteration_count"]
    assert tuple(props["prototype_output"]["enum"]) == PROTOTYPE_OUTPUTS
    assert tuple(props["research_profile"]["enum"]) == RESEARCH_PROFILES
    assert props["mode"]["const"] == "product"
    assert props["preview_mode"]["const"] == "tunnel+mission-control"
    assert props["vault"]["const"] == "umbral-pit-vault"

    visual = schema["$defs"]["VisualGeneration"]["properties"]
    assert visual["aspect_ratio"]["default"] == "4:3"
    assert tuple(visual["aspect_ratio"]["enum"]) == PIT_ASPECT_RATIOS
    assert visual["provider"]["const"] == "magnific"

    personas = schema["$defs"]["SyntheticPersonas"]["properties"]
    assert personas["labeled"]["const"] is True


# ---------------------------------------------------------------------------
# kpi-pack.schema.json — lane closeout contract
# ---------------------------------------------------------------------------


def _sample_kpi_pack() -> dict:
    kpis = [
        {
            "kpi_id": "checkin_completion",
            "unit": "%",
            "kpi_expected": 60,
            "kpi_achieved": 45,
            "direction": "increase",
            "weight": 2.0,
            "synthetic": True,
        },
        {
            "kpi_id": "time_to_checkin",
            "unit": "segundos",
            "kpi_expected": 30,
            "kpi_achieved": 25,
            "direction": "decrease",
            "weight": 1.0,
        },
    ]
    return {
        "schema_version": 1,
        "pit_id": "pit-salud-mental-pilot",
        "lane_id": "lane-friccion",
        "iteration": 3,
        "hypothesis": {
            "variable": "taps hasta completar el check-in",
            "statement": "Si bajo los taps de 5 a 2, sube checkin_completion",
            "kpi_id": "checkin_completion",
            "validated": True,
        },
        "kpis": kpis,
        "fulfillment_score": compute_fulfillment(kpis),
        "prototype_url": "https://tunnel.internal/mc/pit-salud-mental-pilot/lane-friccion",
        "visual_assets": [
            {"url": "https://assets.internal/magnific/abc", "provider": "magnific", "aspect_ratio": "4:3"}
        ],
        "synthetic_personas": {"used": True, "labeled": True, "count": 6},
        "kanban_column": "Fulfillment",
    }


def test_kpi_pack_schema_is_valid_json_and_accepts_sample():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(KPI_PACK_SCHEMA_PATH.read_text(encoding="utf-8"))
    pack = _sample_kpi_pack()
    jsonschema.validate(instance=pack, schema=schema)
    # fulfillment del pack es reproducible con la fórmula del protocolo
    assert pack["fulfillment_score"] == compute_fulfillment(pack["kpis"])


def test_kpi_pack_schema_rejects_unlabeled_synthetic_and_bad_score():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(KPI_PACK_SCHEMA_PATH.read_text(encoding="utf-8"))

    unlabeled = _sample_kpi_pack()
    unlabeled["synthetic_personas"]["labeled"] = False
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=unlabeled, schema=schema)

    bad_score = _sample_kpi_pack()
    bad_score["fulfillment_score"] = 1.5
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad_score, schema=schema)

    missing_hypothesis = _sample_kpi_pack()
    missing_hypothesis.pop("hypothesis")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=missing_hypothesis, schema=schema)


# ---------------------------------------------------------------------------
# PIT spec v2 — broker-only contract (P5)
# ---------------------------------------------------------------------------

EXAMPLE_V2_PATH = REPO_ROOT / "examples" / "pit" / "pit_spec.v2.yaml"


def _broker_spec(**overrides) -> dict:
    base = dict(
        schema_version=2,
        pit_id="pit-broker-smoke-01",
        title="broker smoke",
        repo_path="/home/rick/umbral-agent-stack",
        budget_usd_total=25.0,
        lanes=[
            {
                "lane_id": "lane-a",
                "model": "claude-opus-4.7",
                "reasoning_effort": "xhigh",
                "mission": "research",
                "max_iterations": 3,
            }
        ],
        secrets_scope={"allow": [], "deny": ["WORKER_TOKEN"]},
        broker_contract={
            "required_task": "copilot_cli.run",
            "forbid_direct_llm_repo_analysis": True,
        },
    )
    base.update(overrides)
    return base


def _write_and_validate(tmp_path: Path, spec: dict) -> dict:
    path = tmp_path / "pit_spec.v2.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    return validate_broker_file(path)


def test_v2_detection_routes_broker():
    assert is_broker_spec({"schema_version": 2})
    assert is_broker_spec({"broker_contract": {}})
    assert not is_broker_spec({"schema_version": 1, "pit_id": "x"})


def test_v2_example_spec_passes():
    result = validate_broker_file(EXAMPLE_V2_PATH)
    assert result["status"] == "pass", result["errors"]
    assert result["spec"]["lane_count"] == 2


def test_v2_main_exit_zero_for_example():
    assert main([str(EXAMPLE_V2_PATH)]) == 0


def test_v2_valid_minimal_spec_passes(tmp_path):
    result = _write_and_validate(tmp_path, _broker_spec())
    assert result["status"] == "pass", result["errors"]


def test_v2_invalid_lane_id_fails(tmp_path):
    spec = _broker_spec()
    spec["lanes"][0]["lane_id"] = "lane id with spaces!"
    result = _write_and_validate(tmp_path, spec)
    assert result["status"] == "fail"
    assert any("lane_id" in e for e in result["errors"])


def test_v2_invalid_model_fails(tmp_path):
    spec = _broker_spec()
    spec["lanes"][0]["model"] = "totally-not-a-model"
    result = _write_and_validate(tmp_path, spec)
    assert result["status"] == "fail"
    assert any("invalid_model" in e for e in result["errors"])


def test_v2_invalid_reasoning_effort_fails(tmp_path):
    spec = _broker_spec()
    spec["lanes"][0]["reasoning_effort"] = "turbo"
    result = _write_and_validate(tmp_path, spec)
    assert result["status"] == "fail"
    assert any("invalid_reasoning_effort" in e for e in result["errors"])


def test_v2_display_model_alias_passes(tmp_path):
    spec = _broker_spec()
    spec["lanes"][0]["model"] = "Claude Opus 4.7"
    spec["lanes"][0]["reasoning_effort"] = "max"
    result = _write_and_validate(tmp_path, spec)
    assert result["status"] == "pass", result["errors"]
    assert result["spec"]["lanes"][0]["model_slug"] == "claude-opus-4.7"


def test_v2_forbid_flag_must_be_true(tmp_path):
    spec = _broker_spec()
    spec["broker_contract"]["forbid_direct_llm_repo_analysis"] = False
    result = _write_and_validate(tmp_path, spec)
    assert result["status"] == "fail"
    assert any("forbid_direct_llm_repo_analysis" in e for e in result["errors"])


def test_v2_secrets_deny_requires_worker_token(tmp_path):
    spec = _broker_spec()
    spec["secrets_scope"]["deny"] = ["NOTION_API_KEY"]
    result = _write_and_validate(tmp_path, spec)
    assert result["status"] == "fail"
    assert any("WORKER_TOKEN" in e for e in result["errors"])


def test_v2_required_task_enforced(tmp_path):
    spec = _broker_spec()
    spec["broker_contract"]["required_task"] = "something.else"
    result = _write_and_validate(tmp_path, spec)
    assert result["status"] == "fail"
    assert any("required_task" in e for e in result["errors"])


def test_v2_pitspec_model_importable():
    assert PitSpecV2.__name__ == "PitSpecV2"
