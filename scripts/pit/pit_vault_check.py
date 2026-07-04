#!/usr/bin/env python3
"""Read-only checks for the umbral-pit-vault (PIT tournaments vault).

Basado en ``scripts/obsidian_context_check.py`` (mismo estilo de resultado y
mismas reglas de secretos), con la diferencia clave de gobernanza:

- El vault personal de David es **pull-only** desde la VPS.
- El **umbral-pit-vault** es un vault separado donde los agentes PIT *sí*
  escriben, pero SOLO bajo ``pit/`` (write scope acotado). ``templates/`` y
  ``archive/`` son de lectura para las lanes; la raíz no admite archivos
  sueltos fuera de un allowlist.

El check es read-only: valida estructura, secretos y declaración de write
scope; no modifica nada.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Reglas de secretos compartidas con el vault personal (no duplicar).
try:
    from scripts.obsidian_context_check import SUSPICIOUS_EXACT_NAMES, SUSPICIOUS_SUFFIXES
except ImportError:  # invocado como script directo (python scripts/pit/pit_vault_check.py)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.obsidian_context_check import SUSPICIOUS_EXACT_NAMES, SUSPICIOUS_SUFFIXES

REQUIRED_FOLDERS = ("pit", "templates", "archive")

# Único árbol donde los agentes PIT pueden escribir.
WRITABLE_ROOTS = ("pit",)

# Archivos tolerados en la raíz del vault (todo lo demás es error).
ROOT_ALLOWLIST = {"readme.md", ".gitignore", ".gitattributes"}

EXPECTED_WRITE_SCOPE_ENV = "pit"

# PIT-DEV (FASE 2): un directorio ``workspace/`` (snapshot curado por lane)
# SOLO es válido en pit/<pit_id>/lanes/<lane_id>/workspace/ — o anidado bajo
# uno válido (el snapshot del repo puede contener sus propios "workspace").
WORKSPACE_DIR_NAME = "workspace"


def _workspace_dir_is_valid(rel_parts: tuple[str, ...]) -> bool:
    """True si el dir cuelga de un workspace bien ubicado.

    Ubicación canónica: ``pit/<pit_id>/lanes/<lane_id>/workspace`` (índice 4).
    Un dir ``workspace`` anidado más adentro (p. ej. dentro del snapshot del
    repo) es válido mientras el de índice 4 exista en su path.
    """
    return (
        len(rel_parts) >= 5
        and rel_parts[0] == "pit"
        and rel_parts[2] == "lanes"
        and rel_parts[4] == WORKSPACE_DIR_NAME
    )


def _is_suspicious(path: Path) -> bool:
    name = path.name.lower()
    return name in SUSPICIOUS_EXACT_NAMES or name.endswith(SUSPICIOUS_SUFFIXES)


def check_pit_vault(
    vault_path: Path,
    *,
    require_write_scope: bool = False,
    max_files: int = 5000,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checked_files = 0
    suspicious_files: list[str] = []
    nested_vaults: list[str] = []
    stray_root_files: list[str] = []
    tournaments: list[str] = []
    misplaced_workspaces: list[str] = []

    if not vault_path.exists():
        errors.append(f"vault path not found: {vault_path}")
        return _result(
            vault_path, errors, warnings, checked_files, suspicious_files,
            nested_vaults, stray_root_files, tournaments, misplaced_workspaces,
        )
    if not vault_path.is_dir():
        errors.append(f"vault path is not a directory: {vault_path}")
        return _result(
            vault_path, errors, warnings, checked_files, suspicious_files,
            nested_vaults, stray_root_files, tournaments, misplaced_workspaces,
        )

    for folder in REQUIRED_FOLDERS:
        if not (vault_path / folder).is_dir():
            errors.append(f"missing required folder: {folder}")

    write_scope = os.getenv("PIT_VAULT_WRITE_SCOPE")
    if require_write_scope and write_scope != EXPECTED_WRITE_SCOPE_ENV:
        errors.append(
            "PIT_VAULT_WRITE_SCOPE must be 'pit' (agents may write only under pit/)"
        )
    elif write_scope and write_scope != EXPECTED_WRITE_SCOPE_ENV:
        warnings.append(
            f"PIT_VAULT_WRITE_SCOPE is '{write_scope}', expected '{EXPECTED_WRITE_SCOPE_ENV}'"
        )

    # Archivos sueltos en la raíz fuera del allowlist (la estructura es cerrada).
    for child in vault_path.iterdir():
        if child.is_file() and child.name.lower() not in ROOT_ALLOWLIST:
            stray_root_files.append(child.name)
    for stray in stray_root_files:
        errors.append(f"unexpected file at vault root (move under pit/): {stray}")

    root_obsidian = (vault_path / ".obsidian").resolve()
    for path in vault_path.rglob("*"):
        if checked_files >= max_files:
            warnings.append(f"file scan truncated at {max_files} paths")
            break
        checked_files += 1
        if path.is_dir() and path.name == ".obsidian" and path.resolve() != root_obsidian:
            nested_vaults.append(str(path.relative_to(vault_path)))
        if path.is_dir() and path.name == WORKSPACE_DIR_NAME:
            rel_parts = path.relative_to(vault_path).parts
            if not _workspace_dir_is_valid(rel_parts):
                misplaced_workspaces.append(str(path.relative_to(vault_path)))
        if path.is_file() and _is_suspicious(path):
            suspicious_files.append(str(path.relative_to(vault_path)))

    for nested in nested_vaults:
        errors.append(f"nested Obsidian vault detected: {nested}")
    for misplaced in misplaced_workspaces:
        errors.append(
            "workspace/ only allowed under pit/<pit_id>/lanes/<lane_id>/ "
            f"(found: {misplaced})"
        )
    for secret_like in suspicious_files:
        errors.append(f"secret-like file detected in vault: {secret_like}")

    for workspace_file in ("workspace.json", "workspaces.json"):
        if (vault_path / ".obsidian" / workspace_file).exists():
            warnings.append(f".obsidian/{workspace_file} is local UI state; do not version it")

    # Estructura por torneo: cada pit/<pit_id>/ debería tener su spec.
    pit_root = vault_path / "pit"
    if pit_root.is_dir():
        for tournament_dir in sorted(p for p in pit_root.iterdir() if p.is_dir()):
            tournaments.append(tournament_dir.name)
            spec_yaml = tournament_dir / "spec" / "pit_spec.yaml"
            spec_yml = tournament_dir / "spec" / "pit_spec.yml"
            if not spec_yaml.is_file() and not spec_yml.is_file():
                warnings.append(
                    f"tournament without spec yet: pit/{tournament_dir.name}/spec/pit_spec.yaml"
                )

    return _result(
        vault_path, errors, warnings, checked_files, suspicious_files,
        nested_vaults, stray_root_files, tournaments, misplaced_workspaces,
    )


def _result(
    vault_path: Path,
    errors: list[str],
    warnings: list[str],
    checked_files: int,
    suspicious_files: list[str],
    nested_vaults: list[str],
    stray_root_files: list[str],
    tournaments: list[str],
    misplaced_workspaces: list[str] | None = None,
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
        "stray_root_files": stray_root_files,
        "tournaments": tournaments,
        "misplaced_workspaces": misplaced_workspaces or [],
        "write_scope": os.getenv("PIT_VAULT_WRITE_SCOPE"),
        "writable_roots": list(WRITABLE_ROOTS),
        "required_folders": list(REQUIRED_FOLDERS),
    }


def format_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# PIT Vault Check",
        "",
        f"- Status: `{result['status']}`",
        f"- Vault: `{result['vault_path']}`",
        f"- Write scope: `{result.get('write_scope') or 'unset'}` "
        f"(writable roots: {', '.join(result['writable_roots'])})",
        f"- Tournaments: `{len(result['tournaments'])}`",
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
    parser = argparse.ArgumentParser(description="Validate the umbral-pit-vault structure.")
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path(os.environ["PIT_VAULT_PATH"]) if os.getenv("PIT_VAULT_PATH") else None,
        help="Vault path. Defaults to PIT_VAULT_PATH.",
    )
    parser.add_argument(
        "--require-write-scope",
        action="store_true",
        help="Fail unless PIT_VAULT_WRITE_SCOPE=pit.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )
    args = parser.parse_args(argv)

    if args.vault_path is None:
        print("ERROR: --vault-path or PIT_VAULT_PATH is required", file=sys.stderr)
        return 2

    result = check_pit_vault(args.vault_path, require_write_scope=args.require_write_scope)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_markdown(result), end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
