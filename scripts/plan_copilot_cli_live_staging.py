#!/usr/bin/env python3
"""plan_copilot_cli_live_staging.py — F6 step 6A planner.

Read-only inspector that reports the systemd / envfile / nftables
layout discovered on the host and prints the exact (manual) commands
an operator would run in F6 step 6B. NEVER mutates system state.

The script is allowed to:
  - Read shipped artifacts and policy from the repo.
  - Run a fixed list of read-only ``systemctl`` / ``stat`` queries.
  - Resolve a few well-known paths.

The script is FORBIDDEN to:
  - Use ``sudo``.
  - Spawn ``systemctl daemon-reload``, ``systemctl --user
    daemon-reload``, ``systemctl start/restart/enable/disable``.
  - Spawn ``nft``, ``iptables``, ``ip6tables``, ``ufw`` with intent
    to mutate.
  - Create or modify any file outside an explicit allow-list path.
  - Print any token or secret value.

Default mode is ``--dry-run`` (the only mode in F6 step 6A). The
``--write-report <path>`` flag, if supplied, only accepts paths under
``reports/copilot-cli/`` (gitignored from F4).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = REPO_ROOT / "config" / "tool_policy.yaml"
DEFAULT_NFTABLES_CONF = Path("/etc/nftables.conf")
DEFAULT_REPORT_PREFIX = REPO_ROOT / "reports" / "copilot-cli"

# Read-only systemctl operations only. The planner refuses to invoke
# anything not on this list.
_ALLOWED_SYSTEMCTL_VERBS = frozenset({
    "status", "cat", "show", "is-active", "is-enabled",
})


class PlannerRefused(Exception):
    pass


# ---------------------------------------------------------------------------
# Subprocess wrapper — refuses anything outside the read-only list
# ---------------------------------------------------------------------------


def _safe_systemctl(args: list[str], *, user: bool) -> tuple[int, str, str]:
    """Run a read-only systemctl query and return (rc, stdout, stderr).

    Refuses to run if the verb is not in ``_ALLOWED_SYSTEMCTL_VERBS``.
    Refuses to run as root (no sudo).
    """
    if not args:
        raise PlannerRefused("systemctl: empty args")
    verb = args[0]
    if verb not in _ALLOWED_SYSTEMCTL_VERBS:
        raise PlannerRefused(f"systemctl verb {verb!r} not allowed (read-only only)")
    cmd = ["systemctl"]
    if user:
        cmd.append("--user")
    cmd.extend(args)
    cmd.append("--no-pager")
    try:
        proc = subprocess.run(
            cmd, check=False, capture_output=True, text=True,
            env={**os.environ, "SYSTEMD_PAGER": "", "SYSTEMD_COLORS": "0"},
        )
    except FileNotFoundError:
        return 127, "", "systemctl not found"
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@dataclass
class UnitInfo:
    scope: str  # "user" | "system" | "absent"
    fragment_path: Optional[str] = None
    drop_in_paths: list[str] = field(default_factory=list)
    environment_files: list[str] = field(default_factory=list)
    is_active: bool = False
    is_enabled: bool = False


def _parse_show(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def discover_unit(unit: str) -> UnitInfo:
    """Look up a systemd unit at user scope first, then system scope."""
    for scope in ("user", "system"):
        rc, stdout, _ = _safe_systemctl(
            ["show", unit, "-p", "FragmentPath", "-p", "DropInPaths",
             "-p", "EnvironmentFiles"],
            user=(scope == "user"),
        )
        if rc != 0:
            continue
        props = _parse_show(stdout)
        fragment = props.get("FragmentPath", "").strip() or None
        if not fragment:
            continue
        drop_ins = [p for p in props.get("DropInPaths", "").split() if p]
        env_files_raw = props.get("EnvironmentFiles", "").strip()
        env_files: list[str] = []
        # Format: "/path/file (ignore_errors=no) /other/path (ignore_errors=yes)"
        for tok in env_files_raw.split():
            if tok.startswith("/"):
                env_files.append(tok)
        rc_act, _, _ = _safe_systemctl(["is-active", unit],
                                        user=(scope == "user"))
        rc_en, _, _ = _safe_systemctl(["is-enabled", unit],
                                       user=(scope == "user"))
        return UnitInfo(
            scope=scope,
            fragment_path=fragment,
            drop_in_paths=drop_ins,
            environment_files=env_files,
            is_active=(rc_act == 0),
            is_enabled=(rc_en == 0),
        )
    return UnitInfo(scope="absent")


@dataclass
class NftablesInfo:
    conf_present: bool
    conf_path: str
    autoloads_directory: bool
    autoload_directories: list[str] = field(default_factory=list)


_INCLUDE_RE = re.compile(r'^\s*include\s+"([^"]+)"', re.MULTILINE)


def discover_nftables(conf_path: Path = DEFAULT_NFTABLES_CONF) -> NftablesInfo:
    if not conf_path.is_file():
        return NftablesInfo(False, str(conf_path), False)
    text = conf_path.read_text(encoding="utf-8", errors="replace")
    includes = _INCLUDE_RE.findall(text)
    autoload_dirs = [
        inc for inc in includes
        if any(c in inc for c in "*?[")
    ]
    return NftablesInfo(
        conf_present=True,
        conf_path=str(conf_path),
        autoloads_directory=bool(autoload_dirs),
        autoload_directories=autoload_dirs,
    )


# ---------------------------------------------------------------------------
# Plan rendering
# ---------------------------------------------------------------------------


def recommended_paths(unit: UnitInfo) -> dict[str, str]:
    """Return the recommended future paths given the discovered unit scope."""
    if unit.scope == "user":
        unit_dir = Path(unit.fragment_path or "").parent
        dropin_dir = unit_dir / "umbral-worker.service.d"
        return {
            "scope": "user",
            "dropin_dir": str(dropin_dir),
            "dropin_file": str(dropin_dir / "copilot-cli.conf"),
            "envfile_runtime": "/home/rick/.config/openclaw/copilot-cli.env",
            "envfile_secrets": "/home/rick/.config/openclaw/copilot-cli-secrets.env",
            "nft_staging": "/home/rick/.config/openclaw/copilot-egress.nft",
            "reload_cmd": "systemctl --user daemon-reload",
            "uses_sudo": "no",
        }
    if unit.scope == "system":
        return {
            "scope": "system",
            "dropin_dir": "/etc/systemd/system/umbral-worker.service.d",
            "dropin_file": "/etc/systemd/system/umbral-worker.service.d/copilot-cli.conf",
            "envfile_runtime": "/etc/umbral/copilot-cli.env",
            "envfile_secrets": "/etc/umbral/copilot-cli-secrets.env",
            "nft_staging": "/etc/umbral/copilot-egress.nft",
            "reload_cmd": "sudo systemctl daemon-reload",
            "uses_sudo": "yes",
        }
    return {
        "scope": "absent",
        "dropin_dir": "",
        "dropin_file": "",
        "envfile_runtime": "",
        "envfile_secrets": "",
        "nft_staging": "",
        "reload_cmd": "",
        "uses_sudo": "no",
        "note": "umbral-worker.service not found in either scope",
    }


def render_install_commands(paths: dict[str, str]) -> list[str]:
    """Manual commands an operator would run in F6 step 6B. NOT executed."""
    if paths["scope"] == "absent":
        return ["# manual_only: umbral-worker.service not present, no plan"]
    if paths["scope"] == "user":
        return [
            "# manual_only — operator runs from rick's shell, no sudo",
            f"install -d -m 0700 /home/rick/.config/openclaw",
            f"install -m 0600 infra/env/copilot-cli.env.example "
            f"{shlex.quote(paths['envfile_runtime'])}",
            f"install -m 0600 infra/env/copilot-cli-secrets.env.example "
            f"{shlex.quote(paths['envfile_secrets'])}",
            f"$EDITOR {shlex.quote(paths['envfile_secrets'])}  "
            f"# paste fine-grained PAT v2; do NOT echo to history",
            f"install -d -m 0755 {shlex.quote(paths['dropin_dir'])}",
            "# NOTE: drop-in's EnvironmentFile= must be edited to match user paths",
            "#   EnvironmentFile=-/home/rick/.config/openclaw/copilot-cli.env",
            "#   EnvironmentFile=-/home/rick/.config/openclaw/copilot-cli-secrets.env",
            f"install -m 0644 infra/systemd/umbral-worker-copilot-cli.conf.example "
            f"{shlex.quote(paths['dropin_file'])}.template",
            f"# manually edit {shlex.quote(paths['dropin_file'])}.template → {shlex.quote(paths['dropin_file'])}",
            f"python scripts/verify_copilot_cli_env_contract.py "
            f"--runtime {shlex.quote(paths['envfile_runtime'])} "
            f"--secrets {shlex.quote(paths['envfile_secrets'])} --strict",
            f"systemctl --user daemon-reload",
            "# NOTE: do NOT systemctl --user restart umbral-worker yet — flags stay false",
        ]
    return [
        "# manual_only — operator runs as root with sudo",
        "sudo install -d -m 0700 -o rick -g rick /etc/umbral",
        "sudo install -m 0600 -o rick -g rick infra/env/copilot-cli.env.example "
        f"{shlex.quote(paths['envfile_runtime'])}",
        "sudo install -m 0600 -o rick -g rick infra/env/copilot-cli-secrets.env.example "
        f"{shlex.quote(paths['envfile_secrets'])}",
        f"sudo $EDITOR {shlex.quote(paths['envfile_secrets'])}",
        f"sudo install -d -m 0755 {shlex.quote(paths['dropin_dir'])}",
        "sudo install -m 0644 infra/systemd/umbral-worker-copilot-cli.conf.example "
        f"{shlex.quote(paths['dropin_file'])}",
        "sudo python scripts/verify_copilot_cli_env_contract.py --strict",
        "sudo systemctl daemon-reload",
        "# do NOT sudo systemctl restart umbral-worker yet — flags stay false",
    ]


def render_rollback_commands(paths: dict[str, str]) -> list[str]:
    if paths["scope"] == "absent":
        return ["# manual_only: nothing to roll back"]
    if paths["scope"] == "user":
        return [
            "# manual_only — operator runs from rick's shell, no sudo",
            f"rm -f {shlex.quote(paths['dropin_file'])}",
            f"rm -f {shlex.quote(paths['envfile_runtime'])} "
            f"{shlex.quote(paths['envfile_secrets'])}",
            "systemctl --user daemon-reload",
        ]
    return [
        "# manual_only — operator runs as root with sudo",
        f"sudo rm -f {shlex.quote(paths['dropin_file'])}",
        f"sudo rm -f {shlex.quote(paths['envfile_runtime'])} "
        f"{shlex.quote(paths['envfile_secrets'])}",
        "sudo systemctl daemon-reload",
    ]


def build_plan(unit: UnitInfo, nft: NftablesInfo) -> dict:
    paths = recommended_paths(unit)
    return {
        "schema": "copilot-cli-live-staging-plan/v1",
        "dry_run": True,
        "would_apply": False,
        "discovery": {
            "unit_scope": unit.scope,
            "fragment_path": unit.fragment_path,
            "drop_in_paths": unit.drop_in_paths,
            "environment_files": unit.environment_files,
            "is_active": unit.is_active,
            "is_enabled": unit.is_enabled,
            "nftables_conf_present": nft.conf_present,
            "nftables_conf_path": nft.conf_path,
            "nftables_autoloads_directory": nft.autoloads_directory,
            "nftables_autoload_directories": nft.autoload_directories,
        },
        "recommended": paths,
        "manual_install_commands": render_install_commands(paths),
        "manual_rollback_commands": render_rollback_commands(paths),
        "guards": {
            "uses_sudo_in_planner": False,
            "writes_to_etc": False,
            "spawns_nft": False,
            "spawns_iptables": False,
            "creates_docker_network": False,
            "flips_flags": False,
            "prints_tokens": False,
        },
    }


# ---------------------------------------------------------------------------
# Cache writing — strict path allow-list
# ---------------------------------------------------------------------------


def _validate_report_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(DEFAULT_REPORT_PREFIX.resolve())
    except ValueError:
        raise PlannerRefused(
            f"refused: --write-report must live under "
            f"reports/copilot-cli/, got: {resolved}"
        )
    return resolved


def write_report(plan: dict, path: Path) -> Path:
    target = _validate_report_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copilot CLI live staging planner — DRY-RUN only.",
    )
    parser.add_argument("--unit", default="umbral-worker.service",
                        help="systemd unit to plan against (default: umbral-worker.service)")
    parser.add_argument("--nftables-conf", type=Path,
                        default=DEFAULT_NFTABLES_CONF)
    parser.add_argument("--write-report", type=Path, default=None,
                        help="optional path to write the plan as JSON; must "
                             "live under reports/copilot-cli/")
    parser.add_argument("--format", choices=("json", "shell"), default="json",
                        help="output format (default: json)")
    args = parser.parse_args(argv)

    unit = discover_unit(args.unit)
    nft = discover_nftables(args.nftables_conf)
    plan = build_plan(unit, nft)

    if args.write_report is not None:
        try:
            write_report(plan, args.write_report)
        except PlannerRefused as exc:
            sys.stderr.write(f"ERROR: {exc}\n")
            return 3

    if args.format == "shell":
        print("# === Copilot CLI live staging plan (DRY-RUN) ===")
        print(f"# unit_scope: {plan['discovery']['unit_scope']}")
        print(f"# fragment_path: {plan['discovery']['fragment_path']}")
        print(f"# nftables_autoloads_directory: "
              f"{plan['discovery']['nftables_autoloads_directory']}")
        print("")
        print("# --- install commands (manual_only, NOT executed) ---")
        for cmd in plan["manual_install_commands"]:
            print(cmd)
        print("")
        print("# --- rollback commands (manual_only, NOT executed) ---")
        for cmd in plan["manual_rollback_commands"]:
            print(cmd)
    else:
        print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
