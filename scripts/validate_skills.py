#!/usr/bin/env python3
"""
validate_skills.py — Validates SKILL.md frontmatter across all skills.

Searches openclaw/workspace-templates/skills/*/SKILL.md and verifies:
  1. Frontmatter YAML is parseable (delimited by ---)
  2. Required fields: name, description
  3. metadata.openclaw.emoji present
  4. metadata.openclaw.requires.env is a list of strings
  5. Directory name matches frontmatter 'name'

Exit code 0 if all pass, 1 if any fail.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(2)


def find_skill_files(repo_root: Path) -> List[Path]:
    """Find all SKILL.md files in the skills directory."""
    skills_dir = repo_root / "openclaw" / "workspace-templates" / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(skills_dir.glob("*/SKILL.md"))


def parse_frontmatter(text: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter from markdown text.

    Returns (frontmatter_dict, error_message).
    error_message is empty string on success.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, "No frontmatter delimiter (---) found at start"

    end_idx = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return {}, "No closing frontmatter delimiter (---) found"

    yaml_text = "\n".join(lines[1:end_idx])
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        return {}, f"Invalid YAML: {e}"

    if not isinstance(data, dict):
        return {}, f"Frontmatter is not a dict (got {type(data).__name__})"

    return data, ""


def validate_skill(skill_path: Path) -> List[str]:
    """Validate a single SKILL.md file. Returns list of error messages."""
    errors: List[str] = []
    dir_name = skill_path.parent.name

    try:
        text = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Cannot read file: {e}"]

    fm, parse_err = parse_frontmatter(text)
    if parse_err:
        return [parse_err]

    # Required top-level fields
    if not fm.get("name"):
        errors.append("Missing required field: 'name'")
    if not fm.get("description"):
        errors.append("Missing required field: 'description'")

    # metadata.openclaw.emoji
    metadata = fm.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append("'metadata' must be a dict")
        return errors

    openclaw = metadata.get("openclaw", {})
    if not isinstance(openclaw, dict):
        errors.append("'metadata.openclaw' must be a dict")
        return errors

    if not openclaw.get("emoji"):
        errors.append("Missing 'metadata.openclaw.emoji'")

    # metadata.openclaw.requires.env
    requires = openclaw.get("requires", {})
    if not isinstance(requires, dict):
        errors.append("'metadata.openclaw.requires' must be a dict")
    else:
        env_list = requires.get("env")
        if env_list is None:
            errors.append("Missing 'metadata.openclaw.requires.env'")
        elif not isinstance(env_list, list):
            errors.append("'metadata.openclaw.requires.env' must be a list")
        elif not all(isinstance(v, str) for v in env_list):
            errors.append("All items in 'metadata.openclaw.requires.env' must be strings")

    # Directory name matches frontmatter name
    fm_name = fm.get("name", "")
    if fm_name and fm_name != dir_name:
        errors.append(f"Directory name '{dir_name}' does not match frontmatter name '{fm_name}'")

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    skill_files = find_skill_files(repo_root)

    if not skill_files:
        print("WARNING: No SKILL.md files found.")
        return 0

    print(f"Found {len(skill_files)} skill(s) to validate.\n")

    all_ok = True
    for path in skill_files:
        rel = path.relative_to(repo_root)
        errors = validate_skill(path)
        if errors:
            all_ok = False
            print(f"  FAIL  {rel}")
            for err in errors:
                print(f"        - {err}")
        else:
            print(f"  OK    {rel}")

    print()
    if all_ok:
        print("All skills validated successfully.")
        return 0
    else:
        print("Some skills have validation errors.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
