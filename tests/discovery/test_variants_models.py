"""Tests for multi-platform variant Pydantic models (Hilo 5)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from scripts.discovery.lib.variants import (
    ASPECT_RATIOS,
    BlogVariant,
    CarouselVariant,
    LinkedInVariant,
    NewsletterVariant,
    Scene,
    Slide,
    VideoVariant,
    VisualBrief,
    XVariant,
    _word_count,
)


def _common_kwargs(content: str = "Body") -> dict:
    return {
        "content": content,
        "char_count": len(content),
        "word_count": _word_count(content),
        "model_used": "test-model",
        "voice_match_score": 0.8,
    }


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


def test_voice_match_score_out_of_range_rejected():
    with pytest.raises(ValidationError):
        LinkedInVariant(**{**_common_kwargs(), "voice_match_score": 1.5})
    with pytest.raises(ValidationError):
        LinkedInVariant(**{**_common_kwargs(), "voice_match_score": -0.1})


def test_voice_match_score_boundaries_ok():
    LinkedInVariant(**{**_common_kwargs(), "voice_match_score": 0.0})
    LinkedInVariant(**{**_common_kwargs(), "voice_match_score": 1.0})


def test_blank_hashtag_rejected():
    with pytest.raises(ValidationError):
        LinkedInVariant(**{**_common_kwargs(), "hashtags": ["#ok", "  "]})


def test_default_generated_at_is_utc():
    v = LinkedInVariant(**_common_kwargs())
    assert isinstance(v.generated_at, datetime)
    assert v.generated_at.tzinfo is not None


# ---------------------------------------------------------------------------
# X
# ---------------------------------------------------------------------------


def test_x_tweet_over_280_rejected():
    long_tweet = "x" * 281
    with pytest.raises(ValidationError) as exc:
        XVariant(
            **_common_kwargs(),
            tweets=[long_tweet],
            hook="x",
        )
    assert "280" in str(exc.value)


def test_x_max_2_hashtags():
    XVariant(
        **_common_kwargs(),
        hashtags=["#a", "#b"],
        tweets=["hook here is something"],
        hook="hook",
    )
    with pytest.raises(ValidationError) as exc:
        XVariant(
            **{**_common_kwargs(), "hashtags": ["#a", "#b", "#c"]},
            tweets=["hook here is something"],
            hook="hook",
        )
    assert "hashtag" in str(exc.value).lower()


def test_x_thread_2_to_5_tweets():
    XVariant(
        **_common_kwargs(),
        tweets=["hook 1", "two", "three", "four", "five"],
        hook="hook",
    )
    with pytest.raises(ValidationError):
        XVariant(
            **_common_kwargs(),
            tweets=["a", "b", "c", "d", "e", "f"],
            hook="a",
        )
    with pytest.raises(ValidationError):
        XVariant(**_common_kwargs(), tweets=[], hook="hook")


def test_x_hook_must_be_in_first_tweet():
    XVariant(
        **_common_kwargs(),
        tweets=["This contains MyHook here", "second"],
        hook="MyHook",
    )
    with pytest.raises(ValidationError) as exc:
        XVariant(
            **_common_kwargs(),
            tweets=["no hook present", "second"],
            hook="UniqueHookNotFound",
        )
    assert "hook" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------------


def _blog_text(words: int) -> str:
    return " ".join(["word"] * words)


def test_blog_word_count_in_range():
    text = _blog_text(900)
    BlogVariant(
        **{
            **_common_kwargs(text),
            "voice_match_score": 0.9,
        },
        h2_outline=["Intro", "Body"],
        seo_title="Title",
        meta_description="Meta description.",
    )


def test_blog_word_count_below_min_rejected():
    text = _blog_text(500)
    with pytest.raises(ValidationError) as exc:
        BlogVariant(
            **_common_kwargs(text),
            h2_outline=["Intro"],
            seo_title="Title",
            meta_description="Meta description.",
        )
    assert "800" in str(exc.value)


def test_blog_word_count_above_max_rejected():
    text = _blog_text(1600)
    with pytest.raises(ValidationError):
        BlogVariant(
            **_common_kwargs(text),
            h2_outline=["Intro"],
            seo_title="Title",
            meta_description="Meta description.",
        )


def test_blog_seo_title_max_60():
    text = _blog_text(900)
    with pytest.raises(ValidationError):
        BlogVariant(
            **_common_kwargs(text),
            h2_outline=["Intro"],
            seo_title="x" * 61,
            meta_description="Meta description.",
        )


def test_blog_meta_description_max_160():
    text = _blog_text(900)
    with pytest.raises(ValidationError):
        BlogVariant(
            **_common_kwargs(text),
            h2_outline=["Intro"],
            seo_title="Title",
            meta_description="x" * 161,
        )


# ---------------------------------------------------------------------------
# Newsletter
# ---------------------------------------------------------------------------


def test_newsletter_subject_max_60():
    text = " ".join(["w"] * 500)
    with pytest.raises(ValidationError):
        NewsletterVariant(
            **_common_kwargs(text),
            subject_line="x" * 61,
            preheader="ok",
        )


def test_newsletter_preheader_max_90():
    text = " ".join(["w"] * 500)
    with pytest.raises(ValidationError):
        NewsletterVariant(
            **_common_kwargs(text),
            subject_line="ok",
            preheader="x" * 91,
        )


def test_newsletter_word_count_range():
    NewsletterVariant(
        **_common_kwargs(" ".join(["w"] * 500)),
        subject_line="ok",
        preheader="ok",
    )
    with pytest.raises(ValidationError):
        NewsletterVariant(
            **_common_kwargs(" ".join(["w"] * 300)),
            subject_line="ok",
            preheader="ok",
        )
    with pytest.raises(ValidationError):
        NewsletterVariant(
            **_common_kwargs(" ".join(["w"] * 800)),
            subject_line="ok",
            preheader="ok",
        )


# ---------------------------------------------------------------------------
# Carousel
# ---------------------------------------------------------------------------


def _make_slides(n: int) -> list[Slide]:
    return [Slide(title=f"t{i}", bullet=f"b{i}", visual_hint="hint") for i in range(n)]


def test_carousel_6_to_10_slides():
    CarouselVariant(**_common_kwargs(), slides=_make_slides(6))
    CarouselVariant(**_common_kwargs(), slides=_make_slides(10))
    with pytest.raises(ValidationError):
        CarouselVariant(**_common_kwargs(), slides=_make_slides(5))
    with pytest.raises(ValidationError):
        CarouselVariant(**_common_kwargs(), slides=_make_slides(11))


def test_slide_bullet_lines_1_to_3():
    Slide(title="t", bullet="one line", visual_hint="h")
    Slide(title="t", bullet="line1\nline2\nline3", visual_hint="h")
    with pytest.raises(ValidationError):
        Slide(title="t", bullet="l1\nl2\nl3\nl4", visual_hint="h")


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------


def _make_storyboard(n: int) -> list[Scene]:
    return [
        Scene(description=f"s{i}", on_screen_text=f"t{i}", duration_seconds=10.0)
        for i in range(n)
    ]


def test_video_duration_30_to_60_seconds():
    VideoVariant(
        **_common_kwargs(),
        hook="hook",
        hook_seconds=2.0,
        duration_seconds=30.0,
        storyboard=_make_storyboard(4),
    )
    VideoVariant(
        **_common_kwargs(),
        hook="hook",
        hook_seconds=3.0,
        duration_seconds=60.0,
        storyboard=_make_storyboard(6),
    )
    with pytest.raises(ValidationError):
        VideoVariant(
            **_common_kwargs(),
            hook="hook",
            hook_seconds=2.0,
            duration_seconds=29.0,
            storyboard=_make_storyboard(4),
        )
    with pytest.raises(ValidationError):
        VideoVariant(
            **_common_kwargs(),
            hook="hook",
            hook_seconds=2.0,
            duration_seconds=61.0,
            storyboard=_make_storyboard(4),
        )


def test_video_hook_max_3_seconds():
    with pytest.raises(ValidationError):
        VideoVariant(
            **_common_kwargs(),
            hook="hook",
            hook_seconds=3.5,
            duration_seconds=40.0,
            storyboard=_make_storyboard(4),
        )


def test_video_storyboard_4_to_6_scenes():
    with pytest.raises(ValidationError):
        VideoVariant(
            **_common_kwargs(),
            hook="hook",
            hook_seconds=2.0,
            duration_seconds=40.0,
            storyboard=_make_storyboard(3),
        )
    with pytest.raises(ValidationError):
        VideoVariant(
            **_common_kwargs(),
            hook="hook",
            hook_seconds=2.0,
            duration_seconds=40.0,
            storyboard=_make_storyboard(7),
        )


# ---------------------------------------------------------------------------
# VisualBrief — see test_visual_brief_spec.py for full coverage
# ---------------------------------------------------------------------------


def test_visual_brief_aspect_ratio_constants_match():
    assert set(ASPECT_RATIOS) == {"1:1", "16:9", "9:16", "4:5"}
