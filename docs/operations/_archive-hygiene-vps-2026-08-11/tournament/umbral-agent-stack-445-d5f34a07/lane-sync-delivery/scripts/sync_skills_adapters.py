#!/usr/bin/env python3
"""Plan and optionally sync OpenClaw skills into Codex or Cursor adapters.

The default mode is dry-run. This script is workstation-safe by design:
- Codex targets ``~/.codex/skills/<slug>/SKILL.md``
- Cursor targets ``.cursor/rules/<slug>.mdc``

Parsing is intentionally tolerant so dry-runs remain useful even when a fixture or
work-in-progress skill has missing or malformed frontmatter. In those cases the
slug falls back to the directory name and description/env metadata become empty.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime safeguard only
    raise SystemExit("PyYAML is required. Install it with: pip install pyyaml") from exc


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SKILLS_DIR = REPO_ROOT / "openclaw" / "workspace-templates" / "skills"
DEFAULT_CODEX_ROOT = Path.home() / ".codex" / "skills"
DEFAULT_CURSOR_ROOT = REPO_ROOT / ".cursor" / "rules"
PLATFORM_CHOICES = ("codex", "cursor", "all")
PLATFORM_ORDER = {"codex": 0, "cursor": 1}


@dataclass(frozen=True)
class SkillDocument:
    slug: str
    name: str
    description: str
    emoji: str
    env_vars: list[str]
    source_path: Path
    source_text: str
    body: str


@dataclass(frozen=True)
class SyncPlanEntry:
    platform: str
    slug: str
    source_path: Path
    target_path: Path
    content: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:12]

    @property
    def action(self) -> str:
        if not self.target_path.exists():
            return "create"
        existing = self.target_path.read_text(encoding="utf-8", errors="replace")
        return "unchanged" if existing == self.content else "update"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Best-effort YAML frontmatter extraction.

    Missing or malformed frontmatter is tolerated by returning an empty mapping and
    the original markdown body.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_idx = None
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        return {}, text

    yaml_text = "\n".join(lines[1:end_idx])
    try:
        frontmatter = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return {}, text

    if not isinstance(frontmatter, dict):
        return {}, text

    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    return frontmatter, body


def parse_skill_frontmatter(skill_md: Path) -> dict:
    """Parse a SKILL.md file with graceful fallback on malformed frontmatter."""
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    frontmatter, _body = _split_frontmatter(text)

    name = str(frontmatter.get("name") or skill_md.parent.name).strip()
    description = str(frontmatter.get("description") or "").strip()
    emoji = ""
    env_vars: list[str] = []

    metadata = frontmatter.get("metadata", {})
    if isinstance(metadata, dict):
        openclaw = metadata.get("openclaw", {})
        if isinstance(openclaw, dict):
            emoji = str(openclaw.get("emoji") or "").strip().strip('"').strip("'")
            requires = openclaw.get("requires", {})
            if isinstance(requires, dict):
                nested_env = requires.get("env", [])
                if isinstance(nested_env, list):
                    env_vars.extend(str(item).strip() for item in nested_env if str(item).strip())

    top_level_env = frontmatter.get("env", [])
    if isinstance(top_level_env, list):
        env_vars.extend(str(item).strip() for item in top_level_env if str(item).strip())

    rel_path = skill_md.parent
    try:
        rel_path_str = str(rel_path.relative_to(REPO_ROOT))
    except ValueError:
        rel_path_str = str(rel_path)

    deduped_env = list(dict.fromkeys(env_vars))
    return {
        "name": name,
        "description": description,
        "emoji": emoji,
        "env_vars": deduped_env,
        "path": rel_path_str,
        "parse_error": "" if frontmatter else "frontmatter_missing_or_invalid",
    }


def discover_skills(skills_dir: Path) -> list[SkillDocument]:
    """Discover skill documents in deterministic slug order."""
    if not skills_dir.is_dir():
        return []

    skills: list[SkillDocument] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        metadata = parse_skill_frontmatter(skill_md)
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        _frontmatter, body = _split_frontmatter(text)
        skills.append(
            SkillDocument(
                slug=skill_md.parent.name,
                name=metadata["name"],
                description=metadata["description"],
                emoji=metadata["emoji"],
                env_vars=metadata["env_vars"],
                source_path=skill_md,
                source_text=text,
                body=body,
            )
        )
    return sorted(skills, key=lambda skill: skill.slug)


def normalize_platform(platform: str) -> tuple[str, ...]:
    if platform not in PLATFORM_CHOICES:
        raise ValueError(f"Unknown platform: {platform}")
    return ("codex", "cursor") if platform == "all" else (platform,)


def resolve_platforms(platform: str) -> tuple[str, ...]:
    """Backward-compatible alias used by tests and older callers."""
    return normalize_platform(platform)


def render_cursor_rule(skill: SkillDocument) -> str:
    """Render a deterministic Cursor rule stub."""
    description = skill.description or f"Imported OpenClaw skill: {skill.slug}"
    description_yaml = json.dumps(description, ensure_ascii=False)
    rel_source = skill.source_path
    try:
        rel_source = skill.source_path.relative_to(REPO_ROOT)
    except ValueError:
        pass

    lines = [
        "---",
        f"description: {description_yaml}",
        "globs:",
        "alwaysApply: false",
        "---",
        "",
        f"# Imported OpenClaw skill: {skill.name}",
        "",
        "Generated by: `scripts/sync_skills_to_vps.py --platform cursor`",
        "",
        f"- slug: `{skill.slug}`",
        f"- source: `{rel_source}`",
        "",
        "<!-- BEGIN OPENCLAW SKILL -->",
        skill.source_text.rstrip(),
        "<!-- END OPENCLAW SKILL -->",
    ]
    return "\n".join(lines).rstrip() + "\n"


def build_sync_plan(
    *,
    platform: str,
    skills_dir: Path | str = DEFAULT_SKILLS_DIR,
    codex_root: Path | str | None = None,
    cursor_root: Path | str | None = None,
    cwd: Path | str | None = None,
) -> list[SyncPlanEntry]:
    """Create a deterministic sync plan for codex, cursor, or both."""
    skills_dir = Path(skills_dir)
    codex_root_path = Path(codex_root) if codex_root else DEFAULT_CODEX_ROOT
    if cursor_root:
        cursor_root_path = Path(cursor_root)
    elif cwd:
        cursor_root_path = Path(cwd) / ".cursor" / "rules"
    else:
        cursor_root_path = DEFAULT_CURSOR_ROOT

    skills = discover_skills(skills_dir)
    platforms = normalize_platform(platform)
    plan: list[SyncPlanEntry] = []

    for platform_name in platforms:
        for skill in skills:
            if platform_name == "codex":
                target = codex_root_path / skill.slug / "SKILL.md"
                content = skill.source_text
            elif platform_name == "cursor":
                target = cursor_root_path / f"{skill.slug}.mdc"
                content = render_cursor_rule(skill)
            else:  # pragma: no cover - normalize_platform guards this
                raise ValueError(f"Unsupported platform: {platform_name}")

            plan.append(
                SyncPlanEntry(
                    platform=platform_name,
                    slug=skill.slug,
                    source_path=skill.source_path,
                    target_path=target,
                    content=content,
                )
            )

    return sorted(plan, key=lambda entry: (PLATFORM_ORDER[entry.platform], entry.slug))


def build_plan(
    *,
    skills_dir: Path,
    platform: str,
    codex_root: Path,
    cursor_rules_dir: Path,
) -> list[SyncPlanEntry]:
    """Compatibility helper used by newer tests."""
    return build_sync_plan(
        platform=platform,
        skills_dir=skills_dir,
        codex_root=codex_root,
        cursor_root=cursor_rules_dir,
    )


def apply_local_sync(plan: Iterable[SyncPlanEntry]) -> int:
    """Write planned files to disk and return the number of changed writes."""
    changed = 0
    for entry in plan:
        if entry.action == "unchanged":
            continue
        entry.target_path.parent.mkdir(parents=True, exist_ok=True)
        entry.target_path.write_text(entry.content, encoding="utf-8")
        changed += 1
    return changed


def apply_plan(plan: Iterable[SyncPlanEntry]) -> None:
    """Compatibility helper used by newer code paths."""
    apply_local_sync(plan)


def summarize_plan(plan: list[SyncPlanEntry], skills_dir: Path) -> dict:
    actions = {"create": 0, "update": 0, "unchanged": 0}
    for entry in plan:
        actions[entry.action] += 1

    skills = 0
    if skills_dir.is_dir():
        skills = len(list(skills_dir.glob("*/SKILL.md")))

    return {
        "skills": skills,
        "planned_writes": len(plan),
        **actions,
    }


def plan_to_text(plan: list[SyncPlanEntry], *, requested_platform: str, skills_dir: Path, dry_run: bool) -> str:
    summary = summarize_plan(plan, skills_dir)
    mode = "dry-run" if dry_run else "execute"
    lines = [
        f"[{mode}] platform={requested_platform} skills_dir={skills_dir}",
        (
            f"skills={summary['skills']} planned_writes={summary['planned_writes']} "
            f"create={summary['create']} update={summary['update']} unchanged={summary['unchanged']}"
        ),
    ]

    if not plan:
        lines.append("No skills found.")
        return "\n".join(lines) + "\n"

    lines.append("")
    for entry in plan:
        lines.append(
            " | ".join(
                [
                    entry.platform,
                    entry.slug,
                    entry.action,
                    str(entry.source_path),
                    str(entry.target_path),
                    entry.sha256,
                ]
            )
        )
    return "\n".join(lines) + "\n"


def plan_to_json(plan: list[SyncPlanEntry], *, requested_platform: str, skills_dir: Path, dry_run: bool) -> str:
    payload = {
        "mode": "dry-run" if dry_run else "execute",
        "platform": requested_platform,
        "skills_dir": str(skills_dir),
        "summary": summarize_plan(plan, skills_dir),
        "planned_writes": [
            {
                "platform": entry.platform,
                "slug": entry.slug,
                "action": entry.action,
                "source_path": str(entry.source_path),
                "target_path": str(entry.target_path),
                "sha256": entry.sha256,
            }
            for entry in plan
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync OpenClaw skills into Codex or Cursor adapters")
    parser.add_argument("--platform", default="all", choices=PLATFORM_CHOICES)
    parser.add_argument("--skills-dir", type=Path, default=DEFAULT_SKILLS_DIR)
    parser.add_argument("--codex-root", type=Path, default=DEFAULT_CODEX_ROOT)
    parser.add_argument("--cursor-root", "--cursor-rules-dir", dest="cursor_root", type=Path, default=DEFAULT_CURSOR_ROOT)
    parser.add_argument("--dry-run", action="store_true", help="Preview planned writes (default behavior)")
    parser.add_argument("--execute", action="store_true", help="Apply planned writes")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dry_run = not args.execute

    plan = build_sync_plan(
        platform=args.platform,
        skills_dir=args.skills_dir,
        codex_root=args.codex_root,
        cursor_root=args.cursor_root,
    )

    output = plan_to_json(plan, requested_platform=args.platform, skills_dir=args.skills_dir, dry_run=dry_run)
    if not args.json:
        output = plan_to_text(plan, requested_platform=args.platform, skills_dir=args.skills_dir, dry_run=dry_run)
    print(output, end="")

    if not dry_run:
        apply_local_sync(plan)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
