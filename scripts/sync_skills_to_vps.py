"""
sync_skills_to_vps.py — List and optionally deploy skills to VPS

Reads openclaw/workspace-templates/skills/*/SKILL.md, parses YAML frontmatter,
and either lists skills (--dry-run) or copies them via SCP (--execute).

Usage:
    python scripts/sync_skills_to_vps.py --dry-run   # list skills
    python scripts/sync_skills_to_vps.py --execute    # copy to VPS via SCP
"""

import argparse
import logging
import os
import pathlib
import re
import subprocess
import sys

logger = logging.getLogger(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "openclaw" / "workspace-templates" / "skills"
VPS_SKILLS_PATH = "~/.openclaw/workspace/skills/"


def parse_skill_frontmatter(skill_md: pathlib.Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md file."""
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)

    name = skill_md.parent.name
    description = ""
    emoji = ""
    env_vars: list[str] = []

    if fm_match:
        fm = fm_match.group(1)
        in_desc = False
        in_env = False
        for line in fm.splitlines():
            stripped = line.strip()
            # name
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
                in_desc = False
                in_env = False
            # description
            elif line.startswith("description:"):
                val = line.split(":", 1)[1].strip()
                if val and val not in (">-", "|"):
                    description = val
                in_desc = True
                in_env = False
            elif in_desc and line.startswith("  ") and not stripped.startswith("metadata"):
                if not description:
                    description = stripped
                else:
                    description += " " + stripped
            elif in_desc and not line.startswith(" "):
                in_desc = False
            # emoji
            if "emoji:" in line:
                emoji = line.split("emoji:", 1)[1].strip().strip('"').strip("'")
            # env vars
            if stripped == "env:":
                in_env = True
                continue
            if in_env:
                if stripped.startswith("- "):
                    env_vars.append(stripped[2:].strip())
                elif not line.startswith(" "):
                    in_env = False

    return {
        "name": name,
        "description": description,
        "emoji": emoji,
        "env_vars": env_vars,
        "path": str(skill_md.parent.relative_to(REPO_ROOT)),
    }


def discover_skills() -> list[dict]:
    """Find all SKILL.md files and parse their metadata."""
    skills = []
    if not SKILLS_DIR.is_dir():
        logger.warning("Skills directory not found: %s", SKILLS_DIR)
        return skills

    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        skill = parse_skill_frontmatter(skill_md)
        skills.append(skill)
    return skills


def print_skills_table(skills: list[dict]):
    """Print a formatted table of discovered skills."""
    if not skills:
        print("No skills found.")
        return

    print(f"\n[skills] Discovered {len(skills)} skill(s):\n")
    print(f"  {'Name':<20} {'Emoji':<6} {'Env Vars':<35} Description")
    print(f"  {'-' * 20} {'-' * 5} {'-' * 35} {'-' * 40}")
    for s in skills:
        env_str = ", ".join(s["env_vars"]) if s["env_vars"] else "-"
        desc = s["description"][:50] + "..." if len(s["description"]) > 50 else s["description"]
        emoji = s.get("emoji", "") or "-"
        print(f"  {s['name']:<20} {emoji:<6} {env_str:<35} {desc}")
    print()


def scp_skills_to_vps(skills: list[dict], vps_host: str):
    """Copy skill directories to VPS via SCP."""
    for skill in skills:
        src = REPO_ROOT / skill["path"]
        dest = f"{vps_host}:{VPS_SKILLS_PATH}"
        print(f"  -> Copying {skill['name']} -> {dest}")
        try:
            subprocess.run(
                ["scp", "-r", str(src), dest],
                check=True, capture_output=True, text=True, timeout=30,
            )
            print(f"    [OK] {skill['name']} copied")
        except subprocess.CalledProcessError as e:
            print(f"    [FAIL] Failed: {e.stderr.strip()}", file=sys.stderr)
        except FileNotFoundError:
            print("    [FAIL] scp not found -- install OpenSSH or use WSL", file=sys.stderr)
            break


def main():
    parser = argparse.ArgumentParser(description="List and sync OpenClaw skills to VPS")
    parser.add_argument("--dry-run", action="store_true", help="List skills without copying (default)")
    parser.add_argument("--execute", action="store_true", help="Copy skills to VPS via SCP")
    parser.add_argument("--vps-host", default=os.environ.get("VPS_HOST", "vps"),
                        help="VPS hostname (default: $VPS_HOST or 'vps')")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    skills = discover_skills()

    if args.json:
        import json
        print(json.dumps(skills, indent=2, ensure_ascii=False))
        return

    print_skills_table(skills)

    if args.execute:
        if not skills:
            print("No skills to sync.")
            return
        print(f"🚀 Syncing {len(skills)} skill(s) to {args.vps_host}...")
        scp_skills_to_vps(skills, args.vps_host)
        print("Done.")
    else:
        print("[dry-run] Use --execute to copy skills to VPS")


if __name__ == "__main__":
    main()
