"""
Sync canonical OpenClaw workspace governance files into live VPS workspaces.

This script is intended to run inside the VPS checkout after `git pull`.
It copies `BOOTSTRAP.md` and `HEARTBEAT.md` from the repo into the canonical
OpenClaw workspaces, applying per-agent overrides where present and writing
backups for replaced files.

Usage:
    python3 scripts/sync_openclaw_workspace_governance.py --dry-run
    python3 scripts/sync_openclaw_workspace_governance.py --execute
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "openclaw" / "workspace-templates"
OVERRIDES_DIR = REPO_ROOT / "openclaw" / "workspace-agent-overrides"
FILES = ("BOOTSTRAP.md", "HEARTBEAT.md")
WORKSPACES = {
    "main": Path("~/.openclaw/workspace").expanduser(),
    "rick-delivery": Path("~/.openclaw/workspaces/rick-delivery").expanduser(),
    "rick-ops": Path("~/.openclaw/workspaces/rick-ops").expanduser(),
    "rick-orchestrator": Path("~/.openclaw/workspaces/rick-orchestrator").expanduser(),
    "rick-qa": Path("~/.openclaw/workspaces/rick-qa").expanduser(),
    "rick-tracker": Path("~/.openclaw/workspaces/rick-tracker").expanduser(),
}


@dataclass(frozen=True)
class SyncEntry:
    agent_id: str
    filename: str
    source: Path
    target: Path
    target_exists: bool
    content_changed: bool


def governance_source_for(agent_id: str, filename: str, *, repo_root: Path = REPO_ROOT) -> Path:
    override = repo_root / "openclaw" / "workspace-agent-overrides" / agent_id / filename
    if override.exists():
        return override
    return repo_root / "openclaw" / "workspace-templates" / filename


def build_sync_plan(
    *, repo_root: Path = REPO_ROOT, home: Path | None = None
) -> list[SyncEntry]:
    resolved_home = home or Path.home()
    plan: list[SyncEntry] = []

    for agent_id, raw_target_dir in WORKSPACES.items():
        target_dir = raw_target_dir
        if home is not None:
            target_dir = resolved_home / raw_target_dir.expanduser().relative_to(Path.home())
        for filename in FILES:
            source = governance_source_for(agent_id, filename, repo_root=repo_root)
            if not source.exists():
                raise FileNotFoundError(f"Missing governance source: {source}")
            target = target_dir / filename
            target_exists = target.exists()
            content_changed = True
            if target_exists:
                content_changed = source.read_text(encoding="utf-8") != target.read_text(
                    encoding="utf-8"
                )
            plan.append(
                SyncEntry(
                    agent_id=agent_id,
                    filename=filename,
                    source=source,
                    target=target,
                    target_exists=target_exists,
                    content_changed=content_changed,
                )
            )

    return plan


def _backup_root(home: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return home / ".openclaw" / ".sync-backups" / f"governance-{stamp}"


def apply_sync_plan(plan: list[SyncEntry], *, home: Path | None = None) -> Path:
    resolved_home = home or Path.home()
    backup_root = _backup_root(resolved_home)

    for entry in plan:
        entry.target.parent.mkdir(parents=True, exist_ok=True)
        if entry.target_exists and entry.content_changed:
            backup_target = backup_root / entry.target.relative_to(resolved_home)
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry.target, backup_target)
        if entry.content_changed or not entry.target_exists:
            shutil.copy2(entry.source, entry.target)

    return backup_root


def print_plan(plan: list[SyncEntry]) -> None:
    print("OpenClaw governance sync plan:\n")
    for entry in plan:
        status = "UNCHANGED"
        if not entry.target_exists:
            status = "CREATE"
        elif entry.content_changed:
            status = "UPDATE"
        print(
            f"- {entry.agent_id:<17} {entry.filename:<12} {status:<8} "
            f"{entry.source} -> {entry.target}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync OpenClaw workspace governance files")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing")
    parser.add_argument("--execute", action="store_true", help="Write changes to live workspaces")
    args = parser.parse_args()

    plan = build_sync_plan()
    print_plan(plan)

    if args.execute:
        backup_root = apply_sync_plan(plan)
        print(f"\nApplied. Backups (if any) written under: {backup_root}")
    else:
        print("\n[dry-run] Use --execute to write changes")


if __name__ == "__main__":
    main()
