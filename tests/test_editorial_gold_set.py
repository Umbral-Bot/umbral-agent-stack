"""
Tests for the editorial gold set: schema, dimensions, cases, and CLI.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from infra.editorial_gold_set import (
    VALID_CHANNELS,
    VALID_INPUT_TYPES,
    load_dimensions,
    load_gold_set,
    load_schema,
    summarize_gold_set,
    validate_dimension_weights,
    validate_gold_set_cases,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GOLD_SET_PATH = _REPO_ROOT / "evals" / "editorial" / "gold-set-minimum.yaml"
_DIMENSIONS_PATH = _REPO_ROOT / "evals" / "editorial" / "dimensions.yaml"
_SCHEMA_PATH = _REPO_ROOT / "evals" / "editorial" / "gold-set.schema.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dimensions():
    return load_dimensions(_DIMENSIONS_PATH)


@pytest.fixture(scope="module")
def cases():
    return load_gold_set(_GOLD_SET_PATH)


@pytest.fixture(scope="module")
def schema():
    return load_schema(_SCHEMA_PATH)


# ---------------------------------------------------------------------------
# Data loads correctly
# ---------------------------------------------------------------------------


class TestDataLoads:
    def test_schema_loads(self, schema):
        assert isinstance(schema, dict)
        assert schema.get("title") == "Editorial Gold Set Case"

    def test_dimensions_load(self, dimensions):
        assert isinstance(dimensions, list)
        assert len(dimensions) >= 10

    def test_gold_set_loads(self, cases):
        assert isinstance(cases, list)


# ---------------------------------------------------------------------------
# Gold set structural requirements
# ---------------------------------------------------------------------------


class TestGoldSetStructure:
    def test_at_least_8_cases(self, cases):
        assert len(cases) >= 8

    def test_at_most_12_cases(self, cases):
        assert len(cases) <= 12

    def test_all_ids_unique(self, cases):
        ids = [c["id"] for c in cases]
        assert len(ids) == len(set(ids))

    def test_all_ids_start_with_ed_gold(self, cases):
        for case in cases:
            assert case["id"].startswith("ED-GOLD-"), f"Bad id: {case['id']}"

    def test_all_channels_valid(self, cases):
        for case in cases:
            for ch in case["target_channels"]:
                assert ch in VALID_CHANNELS, f"Case {case['id']} bad channel: {ch}"

    def test_all_input_types_valid(self, cases):
        for case in cases:
            assert case["input_type"] in VALID_INPUT_TYPES, (
                f"Case {case['id']} bad input_type: {case['input_type']}"
            )

    def test_all_dimensions_referenced_exist(self, cases, dimensions):
        dim_ids = {d["id"] for d in dimensions}
        for case in cases:
            for dim_ref in case["evaluation_dimensions"]:
                assert dim_ref in dim_ids, (
                    f"Case {case['id']} references unknown dim: {dim_ref}"
                )

    def test_each_case_has_human_gate(self, cases):
        for case in cases:
            assert "human_gate_required" in case, f"Case {case['id']} missing human_gate_required"
            assert isinstance(case["human_gate_required"], bool)

    def test_minimum_score_in_range(self, cases):
        for case in cases:
            score = case["minimum_score"]
            assert 0 <= score <= 1, f"Case {case['id']} score out of range: {score}"


# ---------------------------------------------------------------------------
# Dimension weights
# ---------------------------------------------------------------------------


class TestDimensionWeights:
    def test_weights_sum_to_one(self, dimensions):
        total = sum(d["weight"] for d in dimensions)
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}"

    def test_all_dimensions_have_required_fields(self, dimensions):
        for dim in dimensions:
            for field in ("id", "name", "weight", "description", "good", "bad"):
                assert field in dim, f"Dimension '{dim.get('id', '?')}' missing '{field}'"

    def test_dimension_ids_unique(self, dimensions):
        ids = [d["id"] for d in dimensions]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Thematic coverage
# ---------------------------------------------------------------------------


class TestThematicCoverage:
    def test_covers_referente_as_discovery_signal(self, cases):
        """At least one case covers referentes as discovery signal (ED-GOLD-002)."""
        found = any(
            "referent" in c.get("scenario", "").lower()
            or "referente" in c.get("scenario", "").lower()
            or "discovery signal" in c.get("scenario", "").lower()
            for c in cases
        )
        assert found, "No case covers referentes as discovery signal"

    def test_covers_visual_automation_ua13(self, cases):
        """At least one case covers visual automation / UA-13."""
        found = any(
            "ua-13" in c.get("notes", "").lower()
            or "ui automation" in c.get("scenario", "").lower()
            or "visual" in c.get("title", "").lower() and "api" in c.get("scenario", "").lower()
            for c in cases
        )
        assert found, "No case covers visual automation / UA-13"

    def test_covers_orchestration_ua14(self, cases):
        """At least one case covers n8n/Make/Agent Stack orchestration / UA-14."""
        found = any(
            "ua-14" in c.get("notes", "").lower()
            or "n8n" in c.get("scenario", "").lower()
            or "orquest" in c.get("scenario", "").lower()
            for c in cases
        )
        assert found, "No case covers orchestration / UA-14"

    def test_covers_post_approval_invalidation(self, cases):
        """At least one case covers comment post-approval gate invalidation."""
        found = any(
            "post-aprobaci" in c.get("scenario", "").lower()
            or "invalidar" in c.get("scenario", "").lower()
            or "invalidar" in " ".join(c.get("expected_behavior", [])).lower()
            or "post-aprobaci" in " ".join(c.get("expected_behavior", [])).lower()
            for c in cases
        )
        assert found, "No case covers post-approval invalidation"


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


class TestValidators:
    def test_validate_gold_set_cases_clean(self, cases, dimensions):
        errors = validate_gold_set_cases(cases, dimensions)
        assert errors == [], f"Validation errors: {errors}"

    def test_validate_dimension_weights_clean(self, dimensions):
        errors = validate_dimension_weights(dimensions)
        assert errors == [], f"Validation errors: {errors}"

    def test_validate_catches_bad_weight(self):
        bad_dims = [
            {"id": "d1", "name": "D1", "weight": 0.5, "description": "x", "good": "y", "bad": "z"},
            {"id": "d2", "name": "D2", "weight": 0.3, "description": "x", "good": "y", "bad": "z"},
        ]
        errors = validate_dimension_weights(bad_dims)
        assert any("sum" in e.lower() for e in errors)

    def test_validate_catches_unknown_dimension(self, dimensions):
        bad_cases = [{
            "id": "ED-GOLD-999",
            "title": "Test",
            "scenario": "Test scenario",
            "input_type": "raw_idea",
            "target_channels": ["linkedin"],
            "audience_stage": "awareness",
            "source_policy": "no_external_source",
            "expected_behavior": ["test"],
            "must_include": ["test"],
            "must_avoid": ["test"],
            "evaluation_dimensions": ["nonexistent_dimension"],
            "minimum_score": 0.5,
            "human_gate_required": True,
        }]
        errors = validate_gold_set_cases(bad_cases, dimensions)
        assert any("nonexistent_dimension" in e for e in errors)

    def test_validate_catches_duplicate_id(self, dimensions):
        dup_cases = [
            {
                "id": "ED-GOLD-001",
                "title": "A", "scenario": "S", "input_type": "raw_idea",
                "target_channels": ["linkedin"], "audience_stage": "awareness",
                "source_policy": "no_external_source",
                "expected_behavior": ["x"], "must_include": ["x"], "must_avoid": ["x"],
                "evaluation_dimensions": ["strategic_fit"],
                "minimum_score": 0.5, "human_gate_required": True,
            },
            {
                "id": "ED-GOLD-001",
                "title": "B", "scenario": "S", "input_type": "raw_idea",
                "target_channels": ["linkedin"], "audience_stage": "awareness",
                "source_policy": "no_external_source",
                "expected_behavior": ["x"], "must_include": ["x"], "must_avoid": ["x"],
                "evaluation_dimensions": ["strategic_fit"],
                "minimum_score": 0.5, "human_gate_required": True,
            },
        ]
        errors = validate_gold_set_cases(dup_cases, dimensions)
        assert any("Duplicate" in e for e in errors)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summarize_gold_set(self, cases):
        summary = summarize_gold_set(cases)
        assert summary["total_cases"] >= 8
        assert "linkedin" in summary["channels_covered"]
        assert len(summary["input_types_covered"]) >= 3
        assert len(summary["dimensions_used"]) >= 5
        assert summary["all_have_human_gate"] is True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_cli_returns_0(self):
        from scripts.validate_editorial_gold_set import main
        ret = main([
            "--gold-set", str(_GOLD_SET_PATH),
            "--dimensions", str(_DIMENSIONS_PATH),
        ])
        assert ret == 0

    def test_cli_returns_1_for_missing_file(self):
        from scripts.validate_editorial_gold_set import main
        ret = main(["--gold-set", "/nonexistent/path.yaml"])
        assert ret == 1
