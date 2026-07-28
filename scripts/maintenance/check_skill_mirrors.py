#!/usr/bin/env python3
"""Check registry-owned skills against their repo-level mirrors.

Usage:
    python scripts/maintenance/check_skill_mirrors.py [--fix]

Without --fix: report drift and exit non-zero on mismatch.
With --fix:    overwrite each drifted mirror from its canonical source.

Origin: O7c (2026-05-08). ADR 10 / E1 (2026-07-27) reactivated
umbral-skills-registry as the source of truth and removed every user-level
destination from this checker. User-level releases belong exclusively to the
registry's tools/ship_skill.py gate.

This script intentionally maintains only repo mirrors of secret-output-guard.
Content hashes normalize line endings so CRLF/LF checkout policy does not create
false semantic drift. ``--fix`` remains explicit and can never write under a
user home directory.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_UMBRAL_AGENT_STACK_REPO = SCRIPT_PATH.parents[2]
UMBRAL_AGENT_STACK_ENV = "UMBRAL_AGENT_STACK_REPO"
NOTION_GOVERNANCE_ENV = "NOTION_GOVERNANCE_REPO"
UMBRAL_SKILLS_REGISTRY_ENV = "UMBRAL_SKILLS_REGISTRY_REPO"


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


def resolve_umbral_skills_registry_repo(umbral_agent_stack_repo: Path) -> Path:
    override = os.environ.get(UMBRAL_SKILLS_REGISTRY_ENV)
    if override:
        candidates = [_resolved_path(override)]
    else:
        candidates = [
            umbral_agent_stack_repo.parent / "umbral-skills-registry",
            Path.home() / "umbral-skills-registry",
        ]
        windows_repo = _windows_github_repo("umbral-skills-registry")
        if windows_repo is not None:
            candidates.append(windows_repo)

    checked = _unique_paths([path.resolve() for path in candidates])
    for repo in checked:
        canonical = (
            repo
            / "notion-governance-skills"
            / "secret-output-guard"
            / "SKILL.md"
        )
        if canonical.is_file() and (repo / "tools" / "ship_skill.py").is_file():
            return repo

    checked_text = "; ".join(str(path) for path in checked)
    if override:
        raise RuntimeError(
            f"{UMBRAL_SKILLS_REGISTRY_ENV} was set but does not contain the "
            f"secret-output-guard canonical and tools/ship_skill.py: {checked_text}"
        )
    raise RuntimeError(
        "Could not locate umbral-skills-registry. Set "
        f"{UMBRAL_SKILLS_REGISTRY_ENV}=<repo-root>. Checked: {checked_text}"
    )


def build_mirrored_skills() -> dict[Path, list[Path]]:
    umbral_agent_stack_repo = resolve_umbral_agent_stack_repo()
    notion_governance_repo = resolve_notion_governance_repo(umbral_agent_stack_repo)
    registry_repo = resolve_umbral_skills_registry_repo(umbral_agent_stack_repo)
    canonical = (
        registry_repo
        / "notion-governance-skills"
        / "secret-output-guard"
        / "SKILL.md"
    )
    return {
        canonical: [
            notion_governance_repo
            / ".agents"
            / "skills"
            / "secret-output-guard"
            / "SKILL.md",
            umbral_agent_stack_repo
            / ".agents"
            / "skills"
            / "secret-output-guard"
            / "SKILL.md",
        ]
    }


def sha256_prefix(path: Path) -> str:
    text = path.read_bytes().decode("utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
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
