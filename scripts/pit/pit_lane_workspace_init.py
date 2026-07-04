#!/usr/bin/env python3
"""PIT-DEV — workspace curado por lane (visión David §1, FASE 2).

Prepara el workspace de UNA lane de un torneo PIT-DEV dentro del pit-vault:

- ``pit/<pit_id>/lanes/<lane_id>/workspace/snapshot/`` — snapshot **read-only**
  del repo en un ref pinneado (``git archive``, NUNCA un worktree sobre main
  vivo);
- ``pit/<pit_id>/lanes/<lane_id>/workspace/CONTEXT_INDEX.md`` — índice generado
  con "toda la información que la lane necesita": mapa de ``docs/``,
  ``worker/``, ``dispatcher/``, ``client/``, ``scripts/``; endpoints del Worker
  (parseados de ``worker/app.py``); tasks registradas (``worker/tasks/``); y
  env vars **lógicas** (solo NOMBRES desde ``.env.example`` — JAMÁS valores).

La lane escribe su producto en ``deliverable/`` (fuera del snapshot): el torneo
produce un artefacto nuevo, no un PR. Guard complementario en
``pit_vault_check.py``: un directorio ``workspace/`` solo es válido bajo
``pit/<pit_id>/lanes/<lane_id>/``.

Contrato: ``docs/ops/pit-dev-mode-vision-2026-07-03.md`` §4.

Uso::

    python scripts/pit/pit_lane_workspace_init.py \
        --pit-id pit-dev-mcp-ide --lane-id lane-stdio-first \
        --repo ~/umbral-agent-stack --ref v1.2.3 \
        --vault-path ~/umbral-pit-vault
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.pit.pit_runner_core import LANE_ID_RE, PIT_ID_RE
except ImportError:  # invocado como script directo
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.pit.pit_runner_core import LANE_ID_RE, PIT_ID_RE

SNAPSHOT_DIR_NAME = "snapshot"
CONTEXT_INDEX_NAME = "CONTEXT_INDEX.md"

# Módulos top-level del stack que el índice mapea para la lane.
INDEXED_TREES = ("docs", "worker", "dispatcher", "client", "scripts")

# Endpoints FastAPI del Worker: @app.get("/health") / @app.post("/run") ...
_ENDPOINT_RE = re.compile(
    r"@app\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']"
)

# Nombres de env vars lógicas en .env.example (activas o comentadas).
_ENV_NAME_RE = re.compile(r"^#?\s*([A-Z][A-Z0-9_]{1,63})=")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_ref(repo: Path, ref: str) -> str:
    """Resuelve el ref pinneado a un commit SHA (falla si no existe)."""
    result = _run_git(repo, ["rev-parse", "--verify", f"{ref}^{{commit}}"])
    if result.returncode != 0:
        raise ValueError(
            f"ref {ref!r} not resolvable in {repo}: {(result.stderr or '').strip()}"
        )
    return result.stdout.strip()


def snapshot_repo(repo: Path, ref: str, dest: Path) -> int:
    """``git archive <ref>`` extraído en ``dest`` (solo archivos trackeados).

    Devuelve la cantidad de archivos extraídos. Nunca usa un worktree: el
    snapshot es una copia inmutable del ref, sin ``.git``.
    """
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "snapshot.tar"
        result = _run_git(
            repo, ["archive", "--format=tar", "-o", str(tar_path), ref]
        )
        if result.returncode != 0:
            raise ValueError(
                f"git archive failed for ref {ref!r}: {(result.stderr or '').strip()}"
            )
        with tarfile.open(tar_path) as tar:
            members = tar.getmembers()
            # Python 3.12+: filtro data evita paths hostiles en el tar.
            try:
                tar.extractall(dest, filter="data")
            except TypeError:  # pragma: no cover - py<3.12 fallback
                tar.extractall(dest)
            file_count = sum(1 for m in members if m.isfile())
    _make_read_only(dest)
    return file_count


def _make_read_only(root: Path) -> None:
    """Best-effort: quita el bit de escritura del snapshot (read-only)."""
    for path in root.rglob("*"):
        try:
            if path.is_file():
                path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        except OSError:  # pragma: no cover - FS sin permisos POSIX
            continue


def _tree_summary(snapshot: Path, tree: str, *, max_entries: int = 40) -> list[str]:
    root = snapshot / tree
    if not root.is_dir():
        return [f"- `{tree}/` — (no presente en este ref)"]
    files = [p for p in root.rglob("*") if p.is_file()]
    top_level = sorted(
        p.name + ("/" if p.is_dir() else "")
        for p in root.iterdir()
        if not p.name.startswith("__pycache__")
    )
    lines = [f"- `{tree}/` — {len(files)} archivos"]
    shown = top_level[:max_entries]
    lines.extend(f"  - `{tree}/{entry}`" for entry in shown)
    if len(top_level) > max_entries:
        lines.append(f"  - … (+{len(top_level) - max_entries} entradas)")
    return lines


def _worker_endpoints(snapshot: Path) -> list[str]:
    app_py = snapshot / "worker" / "app.py"
    if not app_py.is_file():
        return []
    endpoints: list[str] = []
    for match in _ENDPOINT_RE.finditer(app_py.read_text(encoding="utf-8", errors="replace")):
        endpoints.append(f"{match.group(1).upper()} {match.group(2)}")
    return endpoints


def _worker_tasks(snapshot: Path) -> list[str]:
    tasks_dir = snapshot / "worker" / "tasks"
    if not tasks_dir.is_dir():
        return []
    return sorted(
        p.stem
        for p in tasks_dir.glob("*.py")
        if p.stem not in {"__init__"} and not p.stem.startswith("_")
    )


def _logical_env_names(snapshot: Path) -> list[str]:
    """Nombres lógicos de env vars desde .env.example — NUNCA valores."""
    env_example = snapshot / ".env.example"
    if not env_example.is_file():
        return []
    names: set[str] = set()
    for line in env_example.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _ENV_NAME_RE.match(line.strip())
        if match:
            names.add(match.group(1))
    return sorted(names)


def build_context_index(
    snapshot: Path,
    *,
    pit_id: str,
    lane_id: str,
    ref: str,
    commit_sha: str,
    deliverable_spec: str | None = None,
) -> str:
    """Genera el CONTEXT_INDEX.md de la lane a partir del snapshot."""
    endpoints = _worker_endpoints(snapshot)
    tasks = _worker_tasks(snapshot)
    env_names = _logical_env_names(snapshot)

    lines: list[str] = [
        f"# CONTEXT_INDEX — {pit_id} · {lane_id}",
        "",
        f"- Generado: {_utcnow_iso()} por `scripts/pit/pit_lane_workspace_init.py`",
        f"- Snapshot: ref `{ref}` (commit `{commit_sha}`) — **read-only**, "
        "NO es main vivo y NO se parchea.",
        f"- Tu producto va en `pit/{pit_id}/lanes/{lane_id}/deliverable/` "
        "(FUERA del snapshot). El torneo produce un artefacto nuevo, no un PR.",
        "",
    ]
    if deliverable_spec:
        lines.extend(["## Deliverable spec (qué debe hacer tu producto)", "", deliverable_spec, ""])
    lines.extend(["## Mapa del repo (snapshot)", ""])
    for tree in INDEXED_TREES:
        lines.extend(_tree_summary(snapshot, tree))
    lines.extend(["", "## Endpoints del Worker (worker/app.py)", ""])
    if endpoints:
        lines.extend(f"- `{endpoint}`" for endpoint in endpoints)
    else:
        lines.append("- (worker/app.py no presente en este ref)")
    lines.extend(["", "## Tasks registradas (worker/tasks/)", ""])
    if tasks:
        lines.extend(f"- `{task}`" for task in tasks)
    else:
        lines.append("- (worker/tasks/ no presente en este ref)")
    lines.extend(
        [
            "",
            "## Env vars lógicas (.env.example — SOLO nombres, jamás valores)",
            "",
        ]
    )
    if env_names:
        lines.extend(f"- `{name}`" for name in env_names)
    else:
        lines.append("- (.env.example no presente en este ref)")
    lines.extend(
        [
            "",
            "## Reglas duras",
            "",
            "- Escribís SOLO bajo tu lane; el snapshot es de lectura.",
            "- Egress declarado por iteración en `iterations/<n>/egress.jsonl` "
            "(supervisión security).",
            "- Magnific PROHIBIDO (todos los modos). Pedirlo ⇒ `lane_blocked`.",
            "- Sin secretos: nombres lógicos sí, valores jamás.",
            "",
        ]
    )
    return "\n".join(lines)


def init_workspace(
    *,
    vault_path: Path,
    repo: Path,
    ref: str,
    pit_id: str,
    lane_id: str,
    deliverable_spec: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Inicializa el workspace curado de una lane (snapshot + CONTEXT_INDEX)."""
    if not PIT_ID_RE.fullmatch(pit_id or ""):
        raise ValueError(f"pit_id must match {PIT_ID_RE.pattern} (got {pit_id!r})")
    if not LANE_ID_RE.fullmatch(lane_id or ""):
        raise ValueError(f"lane_id must match {LANE_ID_RE.pattern} (got {lane_id!r})")
    vault = Path(vault_path).expanduser().resolve()
    if not vault.is_dir():
        raise ValueError(f"vault_path is not a directory: {vault}")
    repo = Path(repo).expanduser().resolve()
    if not (repo / ".git").exists():
        raise ValueError(f"repo is not a git checkout: {repo}")

    commit_sha = resolve_ref(repo, ref)

    lane_root = vault / "pit" / pit_id / "lanes" / lane_id
    workspace = lane_root / "workspace"
    snapshot = workspace / SNAPSHOT_DIR_NAME
    if snapshot.exists() and any(snapshot.iterdir()):
        if not force:
            raise ValueError(
                f"workspace snapshot already exists: {snapshot} (use --force to rebuild)"
            )
        _make_writable(snapshot)
        _rmtree(snapshot)

    file_count = snapshot_repo(repo, commit_sha, snapshot)

    index_text = build_context_index(
        snapshot,
        pit_id=pit_id,
        lane_id=lane_id,
        ref=ref,
        commit_sha=commit_sha,
        deliverable_spec=deliverable_spec,
    )
    index_path = workspace / CONTEXT_INDEX_NAME
    index_path.write_text(index_text, encoding="utf-8")

    # deliverable/ pre-creado FUERA del snapshot: ahí va el producto de la lane.
    deliverable_dir = lane_root / "deliverable"
    deliverable_dir.mkdir(parents=True, exist_ok=True)

    return {
        "pit_id": pit_id,
        "lane_id": lane_id,
        "ref": ref,
        "commit_sha": commit_sha,
        "workspace": str(workspace),
        "snapshot": str(snapshot),
        "snapshot_files": file_count,
        "context_index": str(index_path),
        "deliverable_dir": str(deliverable_dir),
    }


def _make_writable(root: Path) -> None:
    for path in root.rglob("*"):
        try:
            path.chmod(path.stat().st_mode | stat.S_IWUSR)
        except OSError:  # pragma: no cover
            continue


def _rmtree(root: Path) -> None:
    import shutil

    def _onerror(func, path, _exc):  # Windows: read-only files need +w first
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
        func(path)

    shutil.rmtree(root, onerror=_onerror)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PIT-DEV — workspace curado por lane (snapshot + CONTEXT_INDEX)."
    )
    parser.add_argument("--pit-id", required=True)
    parser.add_argument("--lane-id", required=True)
    parser.add_argument("--repo", type=Path, required=True,
                        help="Checkout local del repo a snapshotear.")
    parser.add_argument("--ref", required=True,
                        help="Tag/commit pinneado (repo_ref del spec). NO main vivo.")
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path(os.environ["PIT_VAULT_PATH"]) if os.getenv("PIT_VAULT_PATH") else None,
        help="pit-vault (default: $PIT_VAULT_PATH).",
    )
    parser.add_argument("--deliverable-spec", default=None,
                        help="deliverable_spec del pit_spec (se copia al índice).")
    parser.add_argument("--force", action="store_true",
                        help="Reconstruir el snapshot si ya existe.")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args(argv)

    if args.vault_path is None:
        print("ERROR: --vault-path or PIT_VAULT_PATH is required", file=sys.stderr)
        return 2
    try:
        result = init_workspace(
            vault_path=args.vault_path,
            repo=args.repo,
            ref=args.ref,
            pit_id=args.pit_id,
            lane_id=args.lane_id,
            deliverable_spec=args.deliverable_spec,
            force=args.force,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            f"[pit-workspace] {result['pit_id']}/{result['lane_id']}: "
            f"snapshot {result['snapshot_files']} archivos @ {result['commit_sha'][:12]} "
            f"-> {result['workspace']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
