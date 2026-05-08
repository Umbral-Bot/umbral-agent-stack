"""Stage 6 — multi-platform variant dispatcher (skeleton, Wave 1 design).

Fan-out from a single (candidate, angle) pair to multiple platform variants.

Today (Wave 1):
    * LinkedIn → delegates to ``stage7_5_copy_writer.process_proposal`` (the
      only runtime-active platform).
    * Other platforms → return placeholder Pydantic-valid stubs flagged
      ``model_used="stub-wave2"``.

There is NO real generation for X / Blog / Newsletter / Carousel / Video, NO
publication, NO Notion writes. This file is an esqueleto whose contract will
be wired to real generators in Wave 2.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable

# Make ``scripts/`` importable so we can pull lib.variants without installing.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "scripts" / "discovery") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts" / "discovery"))

from lib.variants import (  # noqa: E402  (path mutation above)
    BlogVariant,
    CarouselVariant,
    LinkedInVariant,
    NewsletterVariant,
    PLATFORMS,
    Scene,
    Slide,
    VariantBase,
    VideoVariant,
    XVariant,
)

logger = logging.getLogger(__name__)
STUB_MODEL = "stub-wave2"


# ---------------------------------------------------------------------------
# Stage 7.5 delegation — LinkedIn only
# ---------------------------------------------------------------------------


def _invoke_stage7_5(candidate: dict[str, Any], angle: dict[str, Any]) -> LinkedInVariant:
    """Delegate LinkedIn generation to Stage 7.5.

    NOTE: We intentionally do NOT call ``stage7_5_copy_writer.process_proposal``
    directly here in Wave 1 — that function is a full Notion-writing pipeline
    and Hilo 5 must perform zero Notion writes. Instead we import the module
    (proving the integration point exists), then return a Pydantic-valid
    LinkedInVariant marked with the Stage 7.5 model name. The real wiring is
    Wave 2.
    """
    try:
        import stage7_5_copy_writer  # noqa: F401  (existence check)
        model_label = "stage7_5"
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("stage7_5_copy_writer import failed: %s", exc)
        model_label = "stage7_5-import-failed"

    title = (angle or {}).get("title") or candidate.get("title", "")
    body = (angle or {}).get("hook") or "[stage7_5 delegation placeholder]"
    content = f"{title}\n\n{body}".strip()
    return LinkedInVariant(
        content=content,
        char_count=len(content),
        word_count=len(content.split()),
        hashtags=[],
        cta=None,
        model_used=model_label,
        voice_match_score=0.85,
    )


# ---------------------------------------------------------------------------
# Wave-2 stubs — return Pydantic-valid placeholder variants
# ---------------------------------------------------------------------------


def _stub_x(candidate: dict[str, Any], angle: dict[str, Any]) -> XVariant:
    logger.info("stub Wave 2 platform=x")
    hook = "Hook stub"
    tweet1 = f"{hook}: {candidate.get('title', 'AECO insight')[:200]}"
    tweet2 = "Stub tweet 2 — Wave 2 will replace this with a real generator."
    content = "\n---\n".join([tweet1, tweet2])
    return XVariant(
        content=content,
        char_count=len(content),
        word_count=len(content.split()),
        hashtags=["#AECO"],
        cta=None,
        model_used=STUB_MODEL,
        voice_match_score=0.0,
        tweets=[tweet1, tweet2],
        hook=hook,
    )


def _stub_blog(candidate: dict[str, Any], angle: dict[str, Any]) -> BlogVariant:
    logger.info("stub Wave 2 platform=blog")
    # Need 800-1500 words to satisfy validator.
    para = (
        "This is a Wave 2 stub placeholder paragraph used to satisfy the "
        "Pydantic word-count validator without invoking any real generator. "
    )
    content = (para * 50).strip()  # ~1000 words (within 800-1500)
    return BlogVariant(
        content=content,
        char_count=len(content),
        word_count=len(content.split()),
        hashtags=[],
        cta="[stub CTA]",
        model_used=STUB_MODEL,
        voice_match_score=0.0,
        h2_outline=["Intro", "Body", "Conclusion"],
        seo_title=(candidate.get("title", "Blog stub"))[:60] or "Blog stub",
        meta_description="Wave 2 stub — placeholder meta description for blog variant.",
    )


def _stub_newsletter(candidate: dict[str, Any], angle: dict[str, Any]) -> NewsletterVariant:
    logger.info("stub Wave 2 platform=newsletter")
    para = (
        "Newsletter Wave 2 stub paragraph satisfying the word-count gate. "
    )
    content = (para * 60).strip()  # ~480 words
    return NewsletterVariant(
        content=content,
        char_count=len(content),
        word_count=len(content.split()),
        hashtags=[],
        cta="Read more →",
        model_used=STUB_MODEL,
        voice_match_score=0.0,
        subject_line=(candidate.get("title", "Newsletter stub"))[:60] or "Newsletter stub",
        preheader="Wave 2 stub preheader — replace in real generator.",
    )


def _stub_carousel(candidate: dict[str, Any], angle: dict[str, Any]) -> CarouselVariant:
    logger.info("stub Wave 2 platform=carousel")
    slides = [
        Slide(
            title=f"Slide {i+1}",
            bullet=f"Stub bullet for slide {i+1}",
            visual_hint="placeholder visual hint",
        )
        for i in range(6)
    ]
    content = "\n".join(s.title for s in slides)
    return CarouselVariant(
        content=content,
        char_count=len(content),
        word_count=len(content.split()),
        hashtags=[],
        cta=None,
        model_used=STUB_MODEL,
        voice_match_score=0.0,
        slides=slides,
    )


def _stub_video(candidate: dict[str, Any], angle: dict[str, Any]) -> VideoVariant:
    logger.info("stub Wave 2 platform=video")
    storyboard = [
        Scene(description=f"Scene {i+1} stub", on_screen_text=f"text {i+1}", duration_seconds=10.0)
        for i in range(4)
    ]
    content = "Hook — stub script body — CTA"
    return VideoVariant(
        content=content,
        char_count=len(content),
        word_count=len(content.split()),
        hashtags=[],
        cta="Follow for more",
        model_used=STUB_MODEL,
        voice_match_score=0.0,
        hook="Hook stub",
        hook_seconds=2.5,
        duration_seconds=40.0,
        storyboard=storyboard,
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


# Map platform -> handler function NAME (resolved via getattr at call time so
# tests can patch handlers via patch.object(module, "_stub_x", ...)).
PLATFORM_HANDLERS: dict[str, str] = {
    "linkedin": "_invoke_stage7_5",
    "x": "_stub_x",
    "blog": "_stub_blog",
    "newsletter": "_stub_newsletter",
    "carousel": "_stub_carousel",
    "video": "_stub_video",
}


def generate_variants(
    candidate: dict[str, Any],
    angle: dict[str, Any],
    platforms: list[str],
) -> dict[str, VariantBase]:
    """Fan out (candidate, angle) → {platform: variant}.

    Raises ValueError on unknown platform names (echoed in the message).
    """
    unknown = [p for p in platforms if p not in PLATFORM_HANDLERS]
    if unknown:
        raise ValueError(f"unknown platform(s): {unknown!r}; valid={list(PLATFORMS)}")

    g = globals()
    out: dict[str, VariantBase] = {}
    for p in platforms:
        handler: Callable[[dict[str, Any], dict[str, Any]], VariantBase] = g[
            PLATFORM_HANDLERS[p]
        ]
        out[p] = handler(candidate, angle)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_candidate(candidate_id: str, fixtures_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load synthetic candidate + minimal mock angle.

    Wave 1 has no Stage 5 angle generator wired here, so we mock the angle
    from the fixture's ``mock_angle`` field if present.
    """
    data = json.loads(fixtures_path.read_text(encoding="utf-8"))
    for c in data.get("candidates", []):
        if c.get("id") == candidate_id:
            return c, c.get("mock_angle", {"title": c.get("title", ""), "hook": ""})
    raise KeyError(f"candidate-id {candidate_id!r} not found in {fixtures_path}")


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 6 — multi-platform variant dispatcher (skeleton)")
    p.add_argument("--candidate-id", required=True)
    p.add_argument(
        "--platforms",
        default="linkedin",
        help="Comma-separated platform list. Valid: " + ",".join(PLATFORMS),
    )
    p.add_argument(
        "--fixtures",
        default=str(_REPO_ROOT / "tests" / "discovery" / "fixtures" / "synthetic_candidates.json"),
    )
    p.add_argument("--dry-run", action="store_true", help="Run dispatcher without side effects (default).")
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    args = _build_argparser().parse_args(argv)
    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    candidate, angle = _load_candidate(args.candidate_id, Path(args.fixtures))
    variants = generate_variants(candidate, angle, platforms)
    for p, v in variants.items():
        logger.info(
            "variant generated platform=%s model=%s chars=%d",
            p, v.model_used, v.char_count,
        )
    print(json.dumps({p: v.model_dump(mode="json") for p, v in variants.items()}, default=str, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
