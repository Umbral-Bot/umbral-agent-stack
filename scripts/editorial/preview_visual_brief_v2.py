#!/usr/bin/env python3
"""Offline, side-effect-free preview for a Visual brief v2 YAML fixture.

This command performs no Notion, Worker, Drive, or Magnific call.  It uses the
same deterministic parser, prompt builder, engine aliases, dimensions, and
anti-slop suffix as ``magnific.generate_variants`` so a synthetic second-domain
brief can exercise the production contract without credentials or credits.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from worker.tasks import editorial_visual_brief, magnific  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def _load_brief(path: Path) -> tuple[str, dict]:
    raw = path.read_text(encoding="utf-8")
    if len(raw) > editorial_visual_brief.MAX_VISUAL_BRIEF_V2_CHARS:
        raise editorial_visual_brief.VisualBriefV2Error(
            "Visual brief v2 exceeds the 2000-character Notion contract"
        )
    try:
        parsed = yaml.load(raw, Loader=yaml.BaseLoader)
    except yaml.YAMLError as exc:
        raise editorial_visual_brief.VisualBriefV2Error(
            "Visual brief v2 is not valid YAML"
        ) from exc
    if not isinstance(parsed, dict):
        raise editorial_visual_brief.VisualBriefV2Error(
            "Visual brief v2 must be a YAML mapping"
        )
    return raw, {str(key).strip().lower(): value for key, value in parsed.items()}


def preview_file(path: Path) -> dict:
    raw, brief = _load_brief(path)
    parsed, prompts = editorial_visual_brief.build_visual_brief_v2_prompts(
        brief,
        anti_slop_suffix=magnific._ANTI_SLOP_SUFFIX,
        max_prompt_chars=magnific.MAX_PROMPT_CHARS,
    )
    target = magnific._resolve_v2_generation_target(
        parsed.engine or editorial_visual_brief.V2_DEFAULT_ENGINE
    )
    aspect_ratio, resolution = magnific._normalize_generation_params(
        target,
        brief.get("aspect_ratio") or magnific.DEFAULT_ASPECT_RATIO,
        brief.get("resolution") or magnific.DEFAULT_RESOLUTION,
    )
    return {
        "ok": True,
        "dry_run": True,
        "offline": True,
        "visual_brief_version": editorial_visual_brief.VISUAL_BRIEF_V2_VERSION,
        "prompt_strategy": editorial_visual_brief.V2_PROMPT_STRATEGY,
        "brief_chars": len(raw),
        "count": len(prompts),
        "prompts": prompts,
        "variation_axes": [variation.axis for variation in parsed.variation_axes],
        "model": target.model,
        "endpoint": target.endpoint,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "notion_reads": 0,
        "notion_writes": 0,
        "drive_calls": 0,
        "magnific_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview five Visual brief v2 prompts locally with zero external calls"
    )
    parser.add_argument("--brief-file", required=True, help="UTF-8 Visual brief v2 YAML")
    args = parser.parse_args()

    try:
        result = preview_file(Path(args.brief_file))
    except (OSError, ValueError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2
            )
        )
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(
        "VISUAL_BRIEF_V2_DRY_RUN_OK "
        f"count={result['count']} model={result['model']} external_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
