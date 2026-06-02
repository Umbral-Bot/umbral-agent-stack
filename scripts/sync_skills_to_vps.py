#!/usr/bin/env python3
"""Compatibility wrapper for sync-skills adapter planning.

Historically this file handled VPS SCP copying. For D3.3 we keep the filename as a
stable entrypoint for tests and operator muscle memory, while the adapter logic now
lives in ``scripts/sync_skills_adapters.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sync_skills_adapters import (  # noqa: E402,F401
    DEFAULT_CODEX_ROOT,
    DEFAULT_CURSOR_ROOT,
    DEFAULT_SKILLS_DIR,
    PLATFORM_CHOICES,
    REPO_ROOT,
    SyncPlanEntry,
    SkillDocument,
    apply_local_sync,
    apply_plan,
    build_parser,
    build_plan,
    build_sync_plan,
    discover_skills,
    main,
    normalize_platform,
    parse_skill_frontmatter,
    resolve_platforms,
    plan_to_json,
    plan_to_text,
    render_cursor_rule,
    summarize_plan,
)


if __name__ == "__main__":
    raise SystemExit(main())
