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

HOME = Path.home()
SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_UMBRAL_AGENT_STACK_REPO = SCRIPT_PATH.parents[2]
UMBRAL_AGENT_STACK_ENV = "UMBRAL_AGENT_STACK_REPO"
NOTION_GOVERNANCE_ENV = "NOTION_GOVERNANCE_REPO"


def _resolved_path(path_text: str) -> Path:
    return Path(path_text).expanduser().resolve()


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path).casefold() if os.name == "nt" else str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _windows_github_repo(repo_name: str) -> Path | None:
    if os.name != "nt":
        return None
    system_drive = os.environ.get("SystemDrive", "C:")
    return Path(system_drive) / "GitHub" / repo_name


def resolve_umbral_agent_stack_repo() -> Path:
    override = os.environ.get(UMBRAL_AGENT_STACK_ENV)
    if override:
        repo = _resolved_path(override)
        if not (repo / "scripts" / "maintenance" / "check_skill_mirrors.py").is_file():
            raise RuntimeError(
                f"{UMBRAL_AGENT_STACK_ENV} does not look like umbral-agent-stack: {repo}"
            )
        return repo
    return DEFAULT_UMBRAL_AGENT_STACK_REPO


def resolve_notion_governance_repo(umbral_agent_stack_repo: Path) -> Path:
    override = os.environ.get(NOTION_GOVERNANCE_ENV)
    if override:
        candidates = [_resolved_path(override)]
    else:
        candidates = [
            umbral_agent_stack_repo.parent / "notion-governance",
            Path.home() / "notion-governance",
        ]
        windows_repo = _windows_github_repo("notion-governance")
        if windows_repo is not None:
            candidates.append(windows_repo)

    checked = _unique_paths([path.resolve() for path in candidates])
    for repo in checked:
        if (repo / ".agents" / "skills").is_dir():
            return repo

    checked_text = "; ".join(str(path) for path in checked)
    if override:
        raise RuntimeError(
            f"{NOTION_GOVERNANCE_ENV} was set but does not contain .agents/skills: "
            f"{checked_text}"
        )
    raise RuntimeError(
        "Could not locate notion-governance. Set "
        f"{NOTION_GOVERNANCE_ENV}=<repo-root>. Checked: {checked_text}"
    )

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


def build_mirrored_skills() -> dict[Path, list[Path]]:
    umbral_agent_stack_repo = resolve_umbral_agent_stack_repo()
    notion_governance_repo = resolve_notion_governance_repo(umbral_agent_stack_repo)
    notion_gov_skills = notion_governance_repo / ".agents" / "skills"

    # Canonical repo paths resolve differently on Windows and the VPS; the
    # mirror contract stays byte-for-byte identical. --fix remains explicit.
    mirrored_skills: dict[Path, list[Path]] = {
        notion_gov_skills / "secret-output-guard" / "SKILL.md": [
            HOME / ".copilot" / "skills" / "secret-output-guard" / "SKILL.md",
            HOME / ".codex" / "skills" / "secret-output-guard" / "SKILL.md",
            umbral_agent_stack_repo
            / ".agents"
            / "skills"
            / "secret-output-guard"
            / "SKILL.md",
        ],
    }

    # Skills owned by notion-governance that are mirrored to ~/.codex (and
    # sometimes ~/.copilot). Auto-built below to keep the entry list compact.
    for name in _NOTION_GOV_MIRRORED:
        mirrored_skills[notion_gov_skills / name / "SKILL.md"] = [
            HOME / ".codex" / "skills" / name / "SKILL.md",
        ]

    # notion-governance-expert: 3-way (also lives in ~/.copilot)
    mirrored_skills[
        notion_gov_skills / "notion-governance-expert" / "SKILL.md"
    ] = [
        HOME / ".codex" / "skills" / "notion-governance-expert" / "SKILL.md",
        HOME / ".copilot" / "skills" / "notion-governance-expert" / "SKILL.md",
    ]

    # C8-C1d-b (2026-05-27): cursor-hooks-sync and q-friday-retro are mirrored
    # only into ~/.codex. ~/.copilot is intentionally out of scope for these two
    # because they are not confirmed cross-cutting skills (secret-output-guard
    # remains the separate cross-cutting case handled above). The canonical
    # source for both lives in notion-governance. q-friday-retro is the canonical
    # name; any legacy q2-friday-retro mirror is corrected by --fix from the
    # canonical.
    mirrored_skills[notion_gov_skills / "cursor-hooks-sync" / "SKILL.md"] = [
        HOME / ".codex" / "skills" / "cursor-hooks-sync" / "SKILL.md",
    ]
    mirrored_skills[notion_gov_skills / "q-friday-retro" / "SKILL.md"] = [
        HOME / ".codex" / "skills" / "q-friday-retro" / "SKILL.md",
    ]

    return mirrored_skills


def sha256_prefix(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h[:12].upper()


def check(fix: bool) -> int:
    try:
        mirrored_skills = build_mirrored_skills()
    except RuntimeError as exc:
        print(f"[ERR ] {exc}", file=sys.stderr)
        return 1

    drift_count = 0
    for canonical, mirrors in mirrored_skills.items():
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
