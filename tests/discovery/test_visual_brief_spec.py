"""Tests for the VisualBrief contract (Stage 7 design)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from scripts.discovery.lib.variants import VisualBrief


def _valid_kwargs(**overrides) -> dict:
    base = dict(
        concept="Construction crew using AR overlay on site",
        composition="Wide shot, foreground worker, background scaffolding",
        style="photorealistic, editorial",
        mood="optimistic, focused",
        text_overlay=None,
        negative_prompts=["no logos", "no faces"],
        aspect_ratio="1:1",
        target_platform="linkedin",
    )
    base.update(overrides)
    return base


def test_visual_brief_valid_minimal():
    vb = VisualBrief(**_valid_kwargs())
    assert vb.aspect_ratio == "1:1"
    assert vb.target_platform == "linkedin"
    assert vb.negative_prompts == ["no logos", "no faces"]


def test_visual_brief_requires_all_core_fields():
    for missing in ("concept", "composition", "style", "mood"):
        kwargs = _valid_kwargs()
        kwargs.pop(missing)
        with pytest.raises(ValidationError):
            VisualBrief(**kwargs)


def test_visual_brief_negative_prompts_non_empty():
    with pytest.raises(ValidationError):
        VisualBrief(**_valid_kwargs(negative_prompts=[]))


def test_visual_brief_aspect_ratio_allowed_set():
    for ratio in ("1:1", "16:9", "9:16", "4:5"):
        VisualBrief(**_valid_kwargs(aspect_ratio=ratio))
    with pytest.raises(ValidationError):
        VisualBrief(**_valid_kwargs(aspect_ratio="3:2"))


def test_visual_brief_target_platform_allowed_set():
    for p in ("linkedin", "x", "blog", "newsletter", "carousel", "video"):
        VisualBrief(**_valid_kwargs(target_platform=p))
    with pytest.raises(ValidationError):
        VisualBrief(**_valid_kwargs(target_platform="tiktok"))


def test_visual_brief_text_overlay_optional():
    vb = VisualBrief(**_valid_kwargs(text_overlay="3 días → 3 horas"))
    assert vb.text_overlay == "3 días → 3 horas"
    vb2 = VisualBrief(**_valid_kwargs(text_overlay=None))
    assert vb2.text_overlay is None
