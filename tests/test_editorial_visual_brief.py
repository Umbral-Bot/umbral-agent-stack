"""Unit tests for the deterministic Visual brief v2 contract."""

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from worker.tasks.editorial_visual_brief import (
    VisualBriefV2Error,
    build_visual_brief_v2_prompts,
    is_visual_brief_v2,
    parse_visual_brief_v2,
    raw_declares_visual_brief_v2,
)


def _brief_v2() -> dict:
    return {
        "version": "2",
        "central_fact": "A fast workflow repeats whatever premise it receives.",
        "ignored_consequence": "The output looks finished while its weak premise spreads.",
        "core_metaphor": "One paper vessel crosses the same accelerating current.",
        "invariants": [
            "the same vessel remains the subject",
            "the terminal weakness is always visible",
        ],
        "variation_axes": [
            {"axis": f"axis-{index}", "direction": f"direction-sentinel-{index}"}
            for index in range(1, 6)
        ],
        "negative_prohibitions": [
            "no rescue device",
            "no corrected result",
        ],
        "avoid": ["embedded words", "stock-photo poses"],
    }


def test_v2_activation_is_explicit_and_legacy_versions_stay_legacy():
    assert is_visual_brief_v2({"version": "2"}) is True
    assert is_visual_brief_v2({"version": "v2"}) is True
    assert is_visual_brief_v2({}) is False
    assert is_visual_brief_v2({"version": "1", "scene": "legacy"}) is False
    assert is_visual_brief_v2({"version": "3", "scene": "legacy"}) is False


def test_raw_v2_marker_survives_a_later_yaml_syntax_error():
    assert raw_declares_visual_brief_v2("version: 2\nvariation_axes: [broken")
    assert raw_declares_visual_brief_v2("\"version\": 'v2'\ninvalid: [")
    assert not raw_declares_visual_brief_v2("scene: legacy\navoid: [broken")


def test_v2_builds_five_distinct_prompts_with_one_controlled_axis_each():
    parsed, prompts = build_visual_brief_v2_prompts(
        _brief_v2(), anti_slop_suffix="ANTI-SLOP-SENTINEL", max_prompt_chars=3000
    )

    assert parsed.engine is None
    assert len(prompts) == len(set(prompts)) == 5
    for index, prompt in enumerate(prompts, start=1):
        assert "One paper vessel" in prompt
        assert "weak premise spreads" in prompt
        assert "no rescue device" in prompt
        assert prompt.endswith("ANTI-SLOP-SENTINEL")
        assert f"direction-sentinel-{index}" in prompt
        for other in range(1, 6):
            if other != index:
                assert f"direction-sentinel-{other}" not in prompt


@pytest.mark.parametrize("missing_key", ["central_fact", "ignored_consequence", "core_metaphor"])
def test_v2_requires_general_semantic_fields(missing_key):
    brief = _brief_v2()
    brief.pop(missing_key)

    with pytest.raises(VisualBriefV2Error, match=missing_key):
        parse_visual_brief_v2(brief)


@pytest.mark.parametrize("axis_count", [0, 1, 4, 6])
def test_v2_requires_exactly_five_axes(axis_count):
    brief = _brief_v2()
    brief["variation_axes"] = brief["variation_axes"][:axis_count]
    if axis_count == 6:
        brief["variation_axes"].append(
            {"axis": "axis-6", "direction": "direction-sentinel-6"}
        )

    with pytest.raises(VisualBriefV2Error, match="exactly five"):
        parse_visual_brief_v2(brief)


@pytest.mark.parametrize("duplicate_key", ["axis", "direction"])
def test_v2_rejects_duplicate_controlled_axes_or_directions(duplicate_key):
    brief = _brief_v2()
    brief["variation_axes"][1][duplicate_key] = brief["variation_axes"][0][duplicate_key]

    with pytest.raises(VisualBriefV2Error, match="must be unique"):
        parse_visual_brief_v2(brief)


def test_v2_requires_explicit_negative_prohibitions():
    brief = _brief_v2()
    brief["negative_prohibitions"] = []

    with pytest.raises(VisualBriefV2Error, match="negative_prohibitions"):
        parse_visual_brief_v2(brief)


def test_v2_long_inputs_keep_axis_prohibitions_and_suffix_inside_limit():
    brief = deepcopy(_brief_v2())
    brief["central_fact"] = "fact " * 1500
    brief["ignored_consequence"] = "consequence " * 1500
    brief["core_metaphor"] = "metaphor " * 1500
    brief["negative_prohibitions"] = ["NO-RESCUER " * 500]
    brief["avoid"] = ["AVOID-SENTINEL " * 500]

    _, prompts = build_visual_brief_v2_prompts(
        brief, anti_slop_suffix="ANTI-SLOP-SENTINEL", max_prompt_chars=3000
    )

    assert len(prompts) == 5
    assert all(len(prompt) <= 3000 for prompt in prompts)
    assert all("direction-sentinel-" in prompt for prompt in prompts)
    assert all("NO-RESCUER" in prompt for prompt in prompts)
    assert all(prompt.endswith("ANTI-SLOP-SENTINEL") for prompt in prompts)


def test_offline_second_domain_preview_has_zero_external_calls():
    from scripts.editorial.preview_visual_brief_v2 import preview_file

    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "editorial"
        / "visual_brief_v2_rfi.yaml"
    )
    with patch("worker.tasks.magnific.notion_client.get_page") as notion_read, patch(
        "worker.tasks.magnific.notion_client.update_page_properties"
    ) as notion_write, patch("worker.tasks.magnific.httpx.Client") as http_client:
        result = preview_file(fixture)

    assert result["ok"] is True
    assert result["offline"] is True
    assert result["count"] == 5
    assert len(set(result["prompts"])) == 5
    assert result["model"] == "nano-banana-pro"
    assert result["notion_reads"] == 0
    assert result["notion_writes"] == 0
    assert result["drive_calls"] == 0
    assert result["magnific_calls"] == 0
    assert any("ficha" in prompt for prompt in result["prompts"])
    c7_case_terms = (
        "objeto técnico",
        "cubo",
        "bim",
        "grieta",
        "núcleo hueco",
        "corte seccionado",
    )
    assert all(
        term not in prompt.casefold()
        for term in c7_case_terms
        for prompt in result["prompts"]
    )
    notion_read.assert_not_called()
    notion_write.assert_not_called()
    http_client.assert_not_called()
