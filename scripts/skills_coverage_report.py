#!/usr/bin/env python3
"""
skills_coverage_report.py — Compare Worker tasks vs OpenClaw skills.

Reads TASK_HANDLERS from worker/tasks/__init__.py and scans
openclaw/workspace-templates/skills/*/SKILL.md to detect coverage gaps.

Usage: python scripts/skills_coverage_report.py
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent

TASK_TO_SKILL: Dict[str, str] = {
    "ping": "ping",
    "notion.write_transcript": "notion",
    "notion.add_comment": "notion",
    "notion.poll_comments": "notion",
    "notion.upsert_task": "notion",
    "notion.update_dashboard": "notion",
    "notion.create_report_page": "notion",
    "windows.pad.run_flow": "windows",
    "windows.open_notepad": "windows",
    "windows.write_worker_token": "windows",
    "windows.firewall_allow_port": "windows",
    "windows.start_interactive_worker": "windows",
    "windows.add_interactive_worker_to_startup": "windows",
    "windows.fs.ensure_dirs": "windows",
    "windows.fs.list": "windows",
    "windows.fs.read_text": "windows",
    "windows.fs.write_text": "windows",
    "windows.fs.write_bytes_b64": "windows",
    "system.ooda_report": "observability",
    "system.self_eval": "observability",
    "linear.create_issue": "linear",
    "linear.list_teams": "linear",
    "linear.update_issue_status": "linear",
    "research.web": "research",
    "llm.generate": "llm-generate",
    "composite.research_report": "composite",
    "make.post_webhook": "make-webhook",
    "azure.audio.generate": "azure-audio",
    "figma.get_file": "figma",
    "figma.get_node": "figma",
    "figma.export_image": "figma",
    "figma.add_comment": "figma",
    "figma.list_comments": "figma",
    "document.create_word": "document-generation",
    "document.create_pdf": "document-generation",
    "document.create_presentation": "document-generation",
    "granola.process_transcript": "granola-pipeline",
    "granola.create_followup": "granola-pipeline",
}


def extract_task_names() -> List[str]:
    """Extract task names from TASK_HANDLERS dict in worker/tasks/__init__.py."""
    init_path = REPO_ROOT / "worker" / "tasks" / "__init__.py"
    text = init_path.read_text(encoding="utf-8")
    return re.findall(r'"([a-z][a-z0-9._]*)":', text)


def extract_skill_names() -> Set[str]:
    """Read skill directory names from the skills folder."""
    skills_dir = REPO_ROOT / "openclaw" / "workspace-templates" / "skills"
    return {d.name for d in skills_dir.iterdir() if (d / "SKILL.md").exists()}


def generate_report() -> Tuple[str, int, int]:
    """Build coverage report. Returns (report_text, covered, total)."""
    task_names = extract_task_names()
    skill_names = extract_skill_names()

    covered: List[Tuple[str, str]] = []
    uncovered: List[Tuple[str, str]] = []

    for task in task_names:
        expected_skill = TASK_TO_SKILL.get(task, "")
        if expected_skill and expected_skill in skill_names:
            covered.append((task, expected_skill))
        else:
            uncovered.append((task, expected_skill))

    unique_skills_covered = {s for _, s in covered}
    skills_without_task = skill_names - unique_skills_covered

    total = len(task_names)
    n_covered = len(covered)
    pct = (n_covered / total * 100) if total else 0

    lines = [
        "# Skills Coverage Report R12\n",
        f"**Fecha:** 2026-03-04  ",
        f"**Total Worker tasks:** {total}  ",
        f"**Tasks con skill:** {n_covered}  ",
        f"**Tasks sin skill:** {len(uncovered)}  ",
        f"**Cobertura:** {n_covered}/{total} ({pct:.0f}%)\n",
        "---\n",
        "## ✅ Tasks CON skill\n",
        "| Task | Skill |",
        "|------|-------|",
    ]
    for task, skill in sorted(covered):
        lines.append(f"| `{task}` | `{skill}` |")

    lines.append("")
    if uncovered:
        lines.append("## ❌ Tasks SIN skill\n")
        lines.append("| Task | Skill esperado |")
        lines.append("|------|----------------|")
        for task, skill in sorted(uncovered):
            lines.append(f"| `{task}` | `{skill or '—'}` |")
        lines.append("")

    lines.append("## 📚 Skills sin Worker task (knowledge-only)\n")
    lines.append("| Skill |")
    lines.append("|-------|")
    for s in sorted(skills_without_task):
        lines.append(f"| `{s}` |")
    lines.append("")

    return "\n".join(lines), n_covered, total


def main() -> int:
    report_text, n_covered, total = generate_report()

    print(report_text)

    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    out = reports_dir / "skills-coverage-r12.md"
    out.write_text(report_text, encoding="utf-8")
    print(f"\nReport saved to {out.relative_to(REPO_ROOT)}")

    return 0 if n_covered == total else 1


if __name__ == "__main__":
    sys.exit(main())
