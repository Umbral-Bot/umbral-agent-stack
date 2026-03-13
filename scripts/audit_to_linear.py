#!/usr/bin/env python3
"""
audit_to_linear.py — Parse unchecked audit checklist items and create Linear issues.

Reads a Markdown audit file, extracts unchecked [ ] items, and creates Linear issues
under the specified project. Skips items that already have a matching open issue.

Usage:
    python scripts/audit_to_linear.py [--dry-run] [--file PATH] [--project PROJECT]

Environment:
    LINEAR_API_KEY  — required
    LINEAR_TEAM_ID  — required (UUID, not key)

Default audit file: docs/audits/codebase-audit-2026-03/05-cierre.md
Default project:    Auditoría Mejora Continua
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Allow running from repo root
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from worker import linear_client  # noqa: E402


DEFAULT_AUDIT_FILE = REPO_ROOT / "docs/audits/codebase-audit-2026-03/05-cierre.md"
DEFAULT_PROJECT = "Auditoría Mejora Continua"


def parse_unchecked_items(text: str) -> list[str]:
    """Return text of every unchecked `- [ ] ...` checklist item."""
    pattern = re.compile(r"^- \[ \] (.+)$", re.MULTILINE)
    return [m.group(1).strip() for m in pattern.finditer(text)]


def get_existing_issue_titles(api_key: str, team_id: str) -> set[str]:
    """Fetch titles of open issues to avoid duplicates."""
    query = """
    query TeamIssues($teamId: String!) {
      team(id: $teamId) {
        issues(filter: { state: { type: { nin: ["completed", "cancelled"] } } }, first: 250) {
          nodes { title }
        }
      }
    }
    """
    try:
        data = linear_client._graphql(api_key, query, {"teamId": team_id})
        nodes = data.get("team", {}).get("issues", {}).get("nodes", [])
        return {n["title"] for n in nodes}
    except Exception as exc:
        print(f"[WARN] Could not fetch existing issues: {exc}", file=sys.stderr)
        return set()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync audit checklist → Linear issues")
    parser.add_argument("--dry-run", action="store_true", help="List items without creating issues")
    parser.add_argument("--file", default=str(DEFAULT_AUDIT_FILE), help="Path to audit markdown file")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Linear project name to attach issues to")
    args = parser.parse_args()

    api_key = os.environ.get("LINEAR_API_KEY", "")
    team_id = os.environ.get("LINEAR_TEAM_ID", "")

    if not args.dry_run:
        if not api_key:
            print("ERROR: LINEAR_API_KEY env var not set", file=sys.stderr)
            sys.exit(1)
        if not team_id:
            print("ERROR: LINEAR_TEAM_ID env var not set", file=sys.stderr)
            sys.exit(1)

    audit_path = Path(args.file)
    if not audit_path.exists():
        print(f"ERROR: Audit file not found: {audit_path}", file=sys.stderr)
        sys.exit(1)

    text = audit_path.read_text(encoding="utf-8")
    items = parse_unchecked_items(text)

    if not items:
        print("No unchecked items found. Audit is complete!")
        return

    print(f"Found {len(items)} unchecked item(s) in {audit_path.name}")

    if args.dry_run:
        for i, item in enumerate(items, 1):
            print(f"  [{i}] {item}")
        print("\n[DRY RUN] No issues created.")
        return

    existing = get_existing_issue_titles(api_key, team_id)
    created = 0
    skipped = 0

    for item in items:
        title = f"[Audit] {item[:120]}"
        if title in existing:
            print(f"  SKIP (exists): {title}")
            skipped += 1
            continue
        try:
            result = linear_client.create_issue(
                api_key=api_key,
                team_id=team_id,
                title=title,
                description=(
                    f"Checklist item from audit `{audit_path.name}`:\n\n"
                    f"> {item}\n\n"
                    f"_Created automatically by `scripts/audit_to_linear.py`._"
                ),
                priority=3,  # Normal
            )
            identifier = result.get("identifier", "?")
            print(f"  CREATED {identifier}: {title}")
            created += 1
        except Exception as exc:
            print(f"  ERROR creating issue for '{title}': {exc}", file=sys.stderr)

    print(f"\nDone: {created} created, {skipped} skipped.")


if __name__ == "__main__":
    main()
