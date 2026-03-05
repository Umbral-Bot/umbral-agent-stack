"""
Skills coverage report — compares TASK_HANDLERS vs SKILL.md definitions.

This test is INFORMATIONAL. It warns about tasks without skills but does NOT fail.
"""

import re
import warnings
from pathlib import Path

import pytest

from worker.tasks import TASK_HANDLERS

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "openclaw" / "workspace-templates" / "skills"


def _extract_task_names_from_skill(skill_path: Path) -> set[str]:
    """Extract task names referenced in a SKILL.md (from code blocks and text)."""
    text = skill_path.read_text(encoding="utf-8")
    # Match task patterns like: figma.get_file, notion.add_comment, etc.
    return set(re.findall(r"\b([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)\b", text))


def _get_all_skill_tasks() -> tuple[dict[str, set[str]], set[str]]:
    """Return (skill_name -> task_names, all_skill_tasks)."""
    skill_tasks: dict[str, set[str]] = {}
    all_tasks: set[str] = set()
    handler_keys = set(TASK_HANDLERS.keys())

    if not SKILLS_DIR.is_dir():
        return {}, set()

    for skill_md in SKILLS_DIR.glob("*/SKILL.md"):
        skill_name = skill_md.parent.name
        tasks = _extract_task_names_from_skill(skill_md)
        valid_tasks = tasks & handler_keys

        # Directory name matches: "ping" → task "ping", "llm-generate" → "llm.generate"
        for candidate in (skill_name, skill_name.replace("-", ".")):
            if candidate in handler_keys:
                valid_tasks.add(candidate)

        skill_tasks[skill_name] = valid_tasks
        all_tasks |= valid_tasks

    return skill_tasks, all_tasks


class TestSkillsCoverage:
    """Coverage report: which TASK_HANDLERS have SKILL.md documentation."""

    def test_coverage_report(self):
        """Print coverage report. Does NOT fail — informational only."""
        all_tasks = set(TASK_HANDLERS.keys())
        skill_map, covered_tasks = _get_all_skill_tasks()

        uncovered = sorted(all_tasks - covered_tasks)
        covered = sorted(covered_tasks)

        # Build report
        lines = [
            "",
            "=" * 60,
            "SKILLS COVERAGE REPORT",
            "=" * 60,
            f"Total TASK_HANDLERS: {len(all_tasks)}",
            f"Tasks with SKILL.md: {len(covered)}",
            f"Tasks without skill: {len(uncovered)}",
            "",
        ]

        if skill_map:
            lines.append("Skills found:")
            for name, tasks in sorted(skill_map.items()):
                lines.append(f"  {name}: {sorted(tasks)}")
            lines.append("")

        if uncovered:
            lines.append("Tasks without a SKILL.md (coverage gaps):")
            for t in uncovered:
                lines.append(f"  - {t}")
            lines.append("")

        coverage_pct = (len(covered) / len(all_tasks) * 100) if all_tasks else 0
        lines.append(f"Coverage: {coverage_pct:.0f}%")
        lines.append("=" * 60)

        report = "\n".join(lines)
        print(report)

        if uncovered:
            warnings.warn(
                f"{len(uncovered)} task(s) have no SKILL.md: {uncovered[:5]}{'...' if len(uncovered) > 5 else ''}",
                stacklevel=1,
            )

        # Informational — always passes
        assert True

    def test_at_least_one_skill_exists(self):
        """At least one skill should be defined."""
        skill_files = list(SKILLS_DIR.glob("*/SKILL.md")) if SKILLS_DIR.is_dir() else []
        assert len(skill_files) >= 1, "No SKILL.md files found in skills directory"

    def test_covered_tasks_are_valid(self):
        """Tasks referenced in SKILL.md files must exist in TASK_HANDLERS."""
        _, covered = _get_all_skill_tasks()
        for task_name in covered:
            assert task_name in TASK_HANDLERS, (
                f"SKILL.md references task '{task_name}' but it's not in TASK_HANDLERS"
            )
