"""
Editorial Gold Set — Loader and structural validator.

Loads gold-set cases and evaluation dimensions from YAML files and
validates their structural integrity.  No LLM evaluation.  No network.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Valid enums (must match gold-set.schema.json)
# ---------------------------------------------------------------------------

VALID_INPUT_TYPES = frozenset({
    "source_signal",
    "reference_post",
    "raw_idea",
    "news_reactive",
    "technical_explainer",
    "cta_variant",
})

VALID_CHANNELS = frozenset({"linkedin", "blog", "x"})

VALID_AUDIENCE_STAGES = frozenset({
    "awareness",
    "consideration",
    "trust",
    "conversion",
})

VALID_SOURCE_POLICIES = frozenset({
    "requires_primary_source",
    "opinion_allowed_with_attribution",
    "no_external_source",
})


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _require_yaml() -> None:
    if yaml is None:
        raise ImportError(
            "PyYAML is required. Install with: pip install pyyaml"
        )


def load_yaml_file(path: str | Path) -> Any:
    """Load and parse a YAML file."""
    _require_yaml()
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_gold_set(path: str | Path) -> list[dict[str, Any]]:
    """Load gold-set cases from a YAML file."""
    data = load_yaml_file(path)
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError(f"Gold set file must have a 'cases' key: {path}")
    cases = data["cases"]
    if not isinstance(cases, list):
        raise ValueError(f"'cases' must be a list: {path}")
    return cases


def load_dimensions(path: str | Path) -> list[dict[str, Any]]:
    """Load evaluation dimensions from a YAML file."""
    data = load_yaml_file(path)
    if not isinstance(data, dict) or "dimensions" not in data:
        raise ValueError(f"Dimensions file must have a 'dimensions' key: {path}")
    dims = data["dimensions"]
    if not isinstance(dims, list):
        raise ValueError(f"'dimensions' must be a list: {path}")
    return dims


def load_schema(path: str | Path) -> dict[str, Any]:
    """Load JSON schema for gold-set cases."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Schema not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_dimension_weights(dimensions: list[dict[str, Any]]) -> list[str]:
    """Validate dimension weights sum to 1.0 (within tolerance)."""
    errors: list[str] = []

    if not dimensions:
        errors.append("No dimensions defined")
        return errors

    ids_seen: set[str] = set()
    for dim in dimensions:
        dim_id = dim.get("id", "")
        if not dim_id:
            errors.append("Dimension missing 'id'")
        elif dim_id in ids_seen:
            errors.append(f"Duplicate dimension id: {dim_id}")
        ids_seen.add(dim_id)

        for field in ("name", "weight", "description", "good", "bad"):
            if field not in dim:
                errors.append(f"Dimension '{dim_id}' missing '{field}'")

        weight = dim.get("weight")
        if weight is not None:
            if not isinstance(weight, (int, float)):
                errors.append(f"Dimension '{dim_id}' weight must be numeric")
            elif weight < 0 or weight > 1:
                errors.append(f"Dimension '{dim_id}' weight out of range: {weight}")

    total = sum(d.get("weight", 0) for d in dimensions)
    if abs(total - 1.0) > 0.01:
        errors.append(f"Dimension weights sum to {total:.4f}, expected 1.0")

    return errors


def validate_gold_set_cases(
    cases: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
) -> list[str]:
    """Validate gold-set cases against structural rules."""
    errors: list[str] = []
    dimension_ids = {d["id"] for d in dimensions if "id" in d}

    if not cases:
        errors.append("No cases defined")
        return errors

    ids_seen: set[str] = set()
    for case in cases:
        case_id = case.get("id", "MISSING")

        # ID format
        if not isinstance(case_id, str) or not case_id.startswith("ED-GOLD-"):
            errors.append(f"Case '{case_id}' id must start with 'ED-GOLD-'")
        if case_id in ids_seen:
            errors.append(f"Duplicate case id: {case_id}")
        ids_seen.add(case_id)

        # Required fields
        for field in (
            "title", "scenario", "input_type", "target_channels",
            "audience_stage", "source_policy", "expected_behavior",
            "must_include", "must_avoid", "evaluation_dimensions",
            "minimum_score", "human_gate_required",
        ):
            if field not in case:
                errors.append(f"Case '{case_id}' missing required field '{field}'")

        # Enum validations
        input_type = case.get("input_type")
        if input_type and input_type not in VALID_INPUT_TYPES:
            errors.append(f"Case '{case_id}' invalid input_type: {input_type}")

        channels = case.get("target_channels", [])
        for ch in channels:
            if ch not in VALID_CHANNELS:
                errors.append(f"Case '{case_id}' invalid channel: {ch}")

        stage = case.get("audience_stage")
        if stage and stage not in VALID_AUDIENCE_STAGES:
            errors.append(f"Case '{case_id}' invalid audience_stage: {stage}")

        policy = case.get("source_policy")
        if policy and policy not in VALID_SOURCE_POLICIES:
            errors.append(f"Case '{case_id}' invalid source_policy: {policy}")

        # Dimension references
        dims_ref = case.get("evaluation_dimensions", [])
        for dim_id in dims_ref:
            if dim_id not in dimension_ids:
                errors.append(
                    f"Case '{case_id}' references unknown dimension: {dim_id}"
                )

        # Score range
        score = case.get("minimum_score")
        if score is not None and (score < 0 or score > 1):
            errors.append(f"Case '{case_id}' minimum_score out of range: {score}")

        # human_gate_required type
        gate = case.get("human_gate_required")
        if gate is not None and not isinstance(gate, bool):
            errors.append(f"Case '{case_id}' human_gate_required must be boolean")

    return errors


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarize_gold_set(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a summary of the gold set for reporting."""
    channels: set[str] = set()
    input_types: set[str] = set()
    dimensions_used: set[str] = set()
    stages: set[str] = set()

    for case in cases:
        for ch in case.get("target_channels", []):
            channels.add(ch)
        input_types.add(case.get("input_type", ""))
        stages.add(case.get("audience_stage", ""))
        for dim in case.get("evaluation_dimensions", []):
            dimensions_used.add(dim)

    return {
        "total_cases": len(cases),
        "channels_covered": sorted(channels),
        "input_types_covered": sorted(input_types),
        "audience_stages_covered": sorted(stages),
        "dimensions_used": sorted(dimensions_used),
        "all_have_human_gate": all(
            case.get("human_gate_required") is True for case in cases
        ),
    }
