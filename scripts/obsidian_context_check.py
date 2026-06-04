#!/usr/bin/env python3
"""Read-only checks for the Umbral Obsidian context vault mirror."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_REQUIRED_FOLDER_ALIASES = (
    ("00_inbox", "00-inbox"),
    ("10_decisiones", "10-decisiones", "10-decisions"),
    ("20_reuniones", "20-reuniones", "20-meetings"),
    ("30_investigacion", "30-investigacion", "30-research"),
    ("40_runbooks", "40-runbooks"),
    ("90_evals", "90-evals"),
)

DEFAULT_REQUIRED_FOLDERS = tuple(aliases[0] for aliases in DEFAULT_REQUIRED_FOLDER_ALIASES)

SUSPICIOUS_EXACT_NAMES = {
    ".env",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials.json",
    "token.json",
}

SUSPICIOUS_SUFFIXES = (".pem", ".pfx", ".p12", ".key", ".kdbx")


def _is_suspicious(path: Path) -> bool:
    name = path.name.lower()
    return name in SUSPICIOUS_EXACT_NAMES or name.endswith(SUSPICIOUS_SUFFIXES)


def check_vault(
    vault_path: Path,
    *,
    required_folders: tuple[str, ...] = DEFAULT_REQUIRED_FOLDERS,
    required_folder_aliases: tuple[tuple[str, ...], ...] | None = DEFAULT_REQUIRED_FOLDER_ALIASES,
    require_pull_only: bool = False,
    max_files: int = 5000,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checked_files = 0
    suspicious_files: list[str] = []
    nested_vaults: list[str] = []

    if not vault_path.exists():
        errors.append(f"vault path not found: {vault_path}")
        return _result(vault_path, errors, warnings, checked_files, suspicious_files, nested_vaults)
    if not vault_path.is_dir():
        errors.append(f"vault path is not a directory: {vault_path}")
        return _result(vault_path, errors, warnings, checked_files, suspicious_files, nested_vaults)

    folder_groups = required_folder_aliases or tuple((name,) for name in required_folders)
    missing_folder_groups = [
        aliases for aliases in folder_groups if not any((vault_path / name).is_dir() for name in aliases)
    ]
    for aliases in missing_folder_groups:
        errors.append(f"missing required folder: one of {', '.join(aliases)}")

    sync_mode = os.getenv("OBSIDIAN_SYNC_MODE")
    if require_pull_only and sync_mode != "pull-only":
        errors.append("OBSIDIAN_SYNC_MODE must be 'pull-only' for server mirror checks")
    elif sync_mode and sync_mode != "pull-only":
        warnings.append(f"OBSIDIAN_SYNC_MODE is '{sync_mode}', expected 'pull-only' on VPS")

    root_obsidian = (vault_path / ".obsidian").resolve()
    for path in vault_path.rglob("*"):
        if checked_files >= max_files:
            warnings.append(f"file scan truncated at {max_files} paths")
            break
        checked_files += 1
        if path.is_dir() and path.name == ".obsidian" and path.resolve() != root_obsidian:
            nested_vaults.append(str(path.relative_to(vault_path)))
        if path.is_file() and _is_suspicious(path):
            suspicious_files.append(str(path.relative_to(vault_path)))

    for nested in nested_vaults:
        errors.append(f"nested Obsidian vault detected: {nested}")
    for secret_like in suspicious_files:
        errors.append(f"secret-like file detected in vault: {secret_like}")

    for workspace_file in ("workspace.json", "workspaces.json"):
        if (vault_path / ".obsidian" / workspace_file).exists():
            warnings.append(f".obsidian/{workspace_file} is local UI state; do not version it")

    return _result(vault_path, errors, warnings, checked_files, suspicious_files, nested_vaults)


def _result(
    vault_path: Path,
    errors: list[str],
    warnings: list[str],
    checked_files: int,
    suspicious_files: list[str],
    nested_vaults: list[str],
) -> dict[str, Any]:
    return {
        "read_only": True,
        "vault_path": str(vault_path),
        "status": "fail" if errors else "pass",
        "errors": errors,
        "warnings": warnings,
        "checked_files": checked_files,
        "suspicious_files": suspicious_files,
        "nested_vaults": nested_vaults,
        "sync_mode": os.getenv("OBSIDIAN_SYNC_MODE"),
        "required_folder_aliases": [list(aliases) for aliases in DEFAULT_REQUIRED_FOLDER_ALIASES],
    }


def format_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Obsidian Context Vault Check",
        "",
        f"- Status: `{result['status']}`",
        f"- Vault: `{result['vault_path']}`",
        f"- Sync mode: `{result.get('sync_mode') or 'unset'}`",
        f"- Checked paths: `{result['checked_files']}`",
    ]
    if result["errors"]:
        lines.extend(["", "## Errors"])
        lines.extend(f"- {error}" for error in result["errors"])
    if result["warnings"]:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in result["warnings"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an Obsidian context vault mirror.")
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path(os.environ["OBSIDIAN_VAULT_PATH"])
        if os.getenv("OBSIDIAN_VAULT_PATH")
        else None,
        help="Vault path. Defaults to OBSIDIAN_VAULT_PATH.",
    )
    parser.add_argument(
        "--require-pull-only",
        action="store_true",
        help="Fail unless OBSIDIAN_SYNC_MODE=pull-only.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )
    args = parser.parse_args(argv)

    if args.vault_path is None:
        print("ERROR: --vault-path or OBSIDIAN_VAULT_PATH is required", file=sys.stderr)
        return 2

    result = check_vault(args.vault_path, require_pull_only=args.require_pull_only)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_markdown(result), end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
