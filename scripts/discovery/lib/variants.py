"""Multi-platform variant Pydantic models — Hilo 5 (design only).

Defines the contract for editorial content variants across platforms
(LinkedIn, X, Blog, Newsletter, Carousel, Video). Stage 7.5 LinkedIn writer
remains the only runtime-active variant; all other platforms are stubbed
behind these schemas in Wave 2.

NO runtime publication, NO external API calls — pure schema + validators.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Constants — per-platform limits
# ---------------------------------------------------------------------------

PLATFORMS = ("linkedin", "x", "blog", "newsletter", "carousel", "video")
ASPECT_RATIOS = ("1:1", "16:9", "9:16", "4:5")

X_MAX_CHARS_PER_TWEET = 280
X_MAX_HASHTAGS = 2
X_MIN_TWEETS = 1
X_MAX_TWEETS = 5

BLOG_MIN_WORDS = 800
BLOG_MAX_WORDS = 1500
BLOG_SEO_TITLE_MAX = 60
BLOG_META_DESC_MAX = 160

NEWSLETTER_MIN_WORDS = 400
NEWSLETTER_MAX_WORDS = 700
NEWSLETTER_SUBJECT_MAX = 60
NEWSLETTER_PREHEADER_MAX = 90

CAROUSEL_MIN_SLIDES = 6
CAROUSEL_MAX_SLIDES = 10

VIDEO_MIN_SECONDS = 30
VIDEO_MAX_SECONDS = 60
VIDEO_HOOK_MAX_SECONDS = 3
VIDEO_MIN_SCENES = 4
VIDEO_MAX_SCENES = 6


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class VariantBase(BaseModel):
    """Common fields shared by every platform variant."""

    platform: Literal["linkedin", "x", "blog", "newsletter", "carousel", "video"]
    content: str = Field(..., min_length=1)
    char_count: int = Field(..., ge=0)
    word_count: int = Field(..., ge=0)
    hashtags: list[str] = Field(default_factory=list)
    cta: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_used: str = Field(..., min_length=1)
    voice_match_score: float = Field(..., ge=0.0, le=1.0)

    @field_validator("hashtags")
    @classmethod
    def _no_blank_hashtags(cls, v: list[str]) -> list[str]:
        for h in v:
            if not h or not h.strip():
                raise ValueError("hashtag cannot be blank")
        return v


# ---------------------------------------------------------------------------
# LinkedIn — runtime via Stage 7.5
# ---------------------------------------------------------------------------


class LinkedInVariant(VariantBase):
    platform: Literal["linkedin"] = "linkedin"


# ---------------------------------------------------------------------------
# X / Twitter
# ---------------------------------------------------------------------------


class XVariant(VariantBase):
    platform: Literal["x"] = "x"
    tweets: list[str] = Field(..., min_length=X_MIN_TWEETS, max_length=X_MAX_TWEETS)
    hook: str = Field(..., min_length=1)

    @field_validator("tweets")
    @classmethod
    def _tweet_lengths(cls, v: list[str]) -> list[str]:
        for i, t in enumerate(v):
            if len(t) > X_MAX_CHARS_PER_TWEET:
                raise ValueError(
                    f"tweet[{i}] exceeds {X_MAX_CHARS_PER_TWEET} chars (got {len(t)})"
                )
            if not t.strip():
                raise ValueError(f"tweet[{i}] is empty")
        return v

    @field_validator("hashtags")
    @classmethod
    def _x_hashtag_limit(cls, v: list[str]) -> list[str]:
        if len(v) > X_MAX_HASHTAGS:
            raise ValueError(
                f"X allows at most {X_MAX_HASHTAGS} hashtags (got {len(v)})"
            )
        return v

    @model_validator(mode="after")
    def _hook_in_first_tweet(self) -> "XVariant":
        if self.tweets and self.hook not in self.tweets[0]:
            # Hook should be present in tweet 1 (case-insensitive substring).
            if self.hook.lower() not in self.tweets[0].lower():
                raise ValueError("hook must appear in the first tweet")
        return self


# ---------------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------------


class BlogVariant(VariantBase):
    platform: Literal["blog"] = "blog"
    h2_outline: list[str] = Field(..., min_length=1)
    seo_title: str = Field(..., min_length=1, max_length=BLOG_SEO_TITLE_MAX)
    meta_description: str = Field(..., min_length=1, max_length=BLOG_META_DESC_MAX)

    @model_validator(mode="after")
    def _word_count_range(self) -> "BlogVariant":
        wc = self.word_count or _word_count(self.content)
        if not (BLOG_MIN_WORDS <= wc <= BLOG_MAX_WORDS):
            raise ValueError(
                f"blog word_count must be between {BLOG_MIN_WORDS} and {BLOG_MAX_WORDS} (got {wc})"
            )
        return self


# ---------------------------------------------------------------------------
# Newsletter
# ---------------------------------------------------------------------------


class NewsletterVariant(VariantBase):
    platform: Literal["newsletter"] = "newsletter"
    subject_line: str = Field(..., min_length=1, max_length=NEWSLETTER_SUBJECT_MAX)
    preheader: str = Field(..., min_length=1, max_length=NEWSLETTER_PREHEADER_MAX)

    @model_validator(mode="after")
    def _word_count_range(self) -> "NewsletterVariant":
        wc = self.word_count or _word_count(self.content)
        if not (NEWSLETTER_MIN_WORDS <= wc <= NEWSLETTER_MAX_WORDS):
            raise ValueError(
                f"newsletter word_count must be between "
                f"{NEWSLETTER_MIN_WORDS} and {NEWSLETTER_MAX_WORDS} (got {wc})"
            )
        return self


# ---------------------------------------------------------------------------
# Carousel
# ---------------------------------------------------------------------------


class Slide(BaseModel):
    title: str = Field(..., min_length=1)
    bullet: str = Field(..., min_length=1)
    visual_hint: str = Field(..., min_length=1)

    @field_validator("bullet")
    @classmethod
    def _bullet_lines(cls, v: str) -> str:
        # 1-3 lines (newline separated) per spec.
        lines = [ln for ln in v.splitlines() if ln.strip()]
        if not (1 <= len(lines) <= 3):
            raise ValueError(f"slide bullet must have 1-3 lines (got {len(lines)})")
        return v


class CarouselVariant(VariantBase):
    platform: Literal["carousel"] = "carousel"
    slides: list[Slide] = Field(
        ..., min_length=CAROUSEL_MIN_SLIDES, max_length=CAROUSEL_MAX_SLIDES
    )


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------


class Scene(BaseModel):
    description: str = Field(..., min_length=1)
    on_screen_text: str = Field(default="")
    duration_seconds: float = Field(..., gt=0)


class VideoVariant(VariantBase):
    platform: Literal["video"] = "video"
    hook: str = Field(..., min_length=1)
    hook_seconds: float = Field(..., gt=0, le=VIDEO_HOOK_MAX_SECONDS)
    duration_seconds: float = Field(..., ge=VIDEO_MIN_SECONDS, le=VIDEO_MAX_SECONDS)
    storyboard: list[Scene] = Field(
        ..., min_length=VIDEO_MIN_SCENES, max_length=VIDEO_MAX_SCENES
    )


# ---------------------------------------------------------------------------
# Visual brief
# ---------------------------------------------------------------------------


class VisualBrief(BaseModel):
    """Brief contract for image / visual asset generation (Stage 7).

    Derives from ``(angle, variant)``. Does NOT itself trigger image generation;
    it is the schema the dispatcher hands off to Stage 8.
    """

    concept: str = Field(..., min_length=1)
    composition: str = Field(..., min_length=1)
    style: str = Field(..., min_length=1)
    mood: str = Field(..., min_length=1)
    text_overlay: str | None = None
    negative_prompts: list[str] = Field(..., min_length=1)
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:5"]
    target_platform: Literal[
        "linkedin", "x", "blog", "newsletter", "carousel", "video"
    ]


__all__ = [
    "VariantBase",
    "LinkedInVariant",
    "XVariant",
    "BlogVariant",
    "NewsletterVariant",
    "CarouselVariant",
    "VideoVariant",
    "Slide",
    "Scene",
    "VisualBrief",
    "PLATFORMS",
    "ASPECT_RATIOS",
]
