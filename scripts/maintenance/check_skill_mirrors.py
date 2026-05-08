#!/usr/bin/env python3
"""Check that user-level canonical skills match their repo mirrors.

Usage:
    python scripts/maintenance/check_skill_mirrors.py [--fix]

Without --fix: report drift and exit non-zero on mismatch.
With --fix:    overwrite each drifted mirror from its canonical source.

Origin: O7c (2026-05-08). After F-INC-001 + O7c we discovered repo mirrors of
secret-output-guard had silently drifted from the canonical user-level copy
(notion-governance was 1943B vs canonical 5650B; umbral-agent-stack was
3350B). This script prevents recurrence.

Add a new entry to MIRRORED_SKILLS when a skill is required to stay in sync
across repo mirrors. Stub-pointer mirrors (files that intentionally only
reference the canonical, like notion-governance/skills/secret-output-guard/
SKILL.md) must NOT be listed here.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))

# Each entry: canonical path -> list of full-mirror paths that must match it
# byte-for-byte. Stub-pointer mirrors (e.g. notion-governance/skills/<name>/
# SKILL.md that intentionally only references the canonical) must NOT be
# listed here.
#
# Canonical conventions:
# - secret-output-guard: ~/.copilot/skills/ (cross-cutting agent contract)
# - notion-governance-* and friends: notion-governance/.agents/skills/
#   (governance contract owns them; ~/.codex and ~/.copilot are mirrors)
MIRRORED_SKILLS: dict[Path, list[Path]] = {
    HOME / ".copilot" / "skills" / "secret-output-guard" / "SKILL.md": [
        HOME / ".codex" / "skills" / "secret-output-guard" / "SKILL.md",
        Path("C:/GitHub/notion-governance/.agents/skills/secret-output-guard/SKILL.md"),
        Path("C:/GitHub/umbral-agent-stack/.agents/skills/secret-output-guard/SKILL.md"),
    ],
}

# Skills owned by notion-governance that are mirrored to ~/.codex (and
# sometimes ~/.copilot). Auto-built below to keep the entry list compact.
_NOTION_GOV_REPO = Path("C:/GitHub/notion-governance/.agents/skills")
_NOTION_GOV_MIRRORED = [
    "agents-canonical-registry",
    "notion-context-routing",
    "notion-contextual-email-draft",
    "notion-duplicate-consolidation",
    "notion-normalize-page",
    "notion-page-audit",
    "notion-session-capitalization",
    "notion-system-card",
]
for _name in _NOTION_GOV_MIRRORED:
    MIRRORED_SKILLS[_NOTION_GOV_REPO / _name / "SKILL.md"] = [
        HOME / ".codex" / "skills" / _name / "SKILL.md",
    ]

# notion-governance-expert: 3-way (also lives in ~/.copilot)
MIRRORED_SKILLS[
    _NOTION_GOV_REPO / "notion-governance-expert" / "SKILL.md"
] = [
    HOME / ".codex" / "skills" / "notion-governance-expert" / "SKILL.md",
    HOME / ".copilot" / "skills" / "notion-governance-expert" / "SKILL.md",
]

# Known-drift skills NOT registered here (need David's call on canonical):
#   - cursor-hooks-sync (.codex 2106B vs notion-governance 2166B)
#   - q-friday-retro (.codex 3921B vs notion-governance 4588B)
# Add to MIRRORED_SKILLS once a canonical is chosen.


def sha256_prefix(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h[:12].upper()


def check(fix: bool) -> int:
    drift_count = 0
    for canonical, mirrors in MIRRORED_SKILLS.items():
        if not canonical.exists():
            print(f"[ERR ] canonical missing: {canonical}", file=sys.stderr)
            drift_count += 1
            continue
        canonical_hash = sha256_prefix(canonical)
        canonical_size = canonical.stat().st_size
        print(f"[CANON] {canonical_hash}  {canonical_size:>6}B  {canonical}")
        for mirror in mirrors:
            if not mirror.exists():
                status = "MISSING"
                drift_count += 1
                if fix:
                    mirror.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(canonical, mirror)
                    status = "MISSING -> created"
                print(f"  [{status}] {mirror}")
                continue
            mirror_hash = sha256_prefix(mirror)
            mirror_size = mirror.stat().st_size
            if mirror_hash == canonical_hash:
                print(f"  [OK   ] {mirror_hash}  {mirror_size:>6}B  {mirror}")
            else:
                drift_count += 1
                if fix:
                    shutil.copy2(canonical, mirror)
                    new_hash = sha256_prefix(mirror)
                    print(
                        f"  [FIXED] {mirror_hash}->{new_hash}  "
                        f"{mirror_size:>6}B->{canonical_size}B  {mirror}"
                    )
                else:
                    print(
                        f"  [DRIFT] {mirror_hash}  {mirror_size:>6}B  {mirror}",
                        file=sys.stderr,
                    )
    if drift_count == 0:
        print("\nAll mirrors in sync.")
        return 0
    if fix:
        print(f"\nFixed {drift_count} drift(s).")
        return 0
    print(f"\nFAIL: {drift_count} drift(s). Re-run with --fix to sync.", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Overwrite drifted mirrors from canonical source.",
    )
    args = parser.parse_args()
    return check(fix=args.fix)


if __name__ == "__main__":
    sys.exit(main())
