"""Pure workspace helpers for the pytest sandbox — slice 7b-infra.

These helpers are intentionally self-contained: they do not spawn any
docker process, do not import ``subprocess``, and do not read any
environment variable beyond what :mod:`tempfile` needs. Every public
helper returns a plain ``dict`` (``{"ok": bool, ...}``) and never
raises on expected failure modes.

The design constraints:

* **Top-level allowlist**: only the directories enumerated in
  :data:`TOP_LEVEL_ALLOWLIST` (plus ``pyproject.toml``) are ever
  copied into the sandbox workspace. Anything else under the repo
  root (``.git``, ``.rick``, ``.venv``, ``.env*``, ``__pycache__``,
  ``.pytest_cache``, ``node_modules``, …) is silently skipped.
* **Defence-in-depth on paths**: a caller can only overwrite files
  that already resolve strictly *inside* the workspace, after
  ``Path.resolve()``. Traversal attempts return an error.
* **Test allowlist**: the future pytest runner will never resolve a
  ``validation_target`` that is not listed in
  :func:`load_test_allowlist`. The resolver here enforces that
  invariant.

Nothing in this module touches the runtime worker. Slice 7b-runner
will wire these helpers into ``_run_contestant_validation``.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, List, Optional

logger = logging.getLogger("worker.sandbox.workspace")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Directories at the repo root that are allowed to be copied into the
# sandbox workspace. Anything else (dotfiles, build artefacts, venv,
# secrets) is dropped.
TOP_LEVEL_ALLOWLIST: frozenset = frozenset({
    "worker",
    "tests",
    "dispatcher",
})

# Individual files at the repo root that are allowed.
TOP_LEVEL_FILES_ALLOWLIST: frozenset = frozenset({
    "pyproject.toml",
})

# Patterns (matched on basename) that are never copied, even if their
# parent is allowlisted.
_EXCLUDE_BASENAMES: frozenset = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    ".git",
    ".rick",
    ".idea",
    ".vscode",
    ".DS_Store",
})

# Additional patterns on basename (substring or regex). Kept tiny.
_EXCLUDE_SUFFIXES: tuple = (".pyc", ".pyo")
_EXCLUDE_BASENAME_RE: re.Pattern = re.compile(
    r"^(\.env(\..*)?|\.netrc|\.npmrc|\.pypirc)$"
)

# Workspace prefix used inside /tmp. Kept unique enough for humans to
# spot them in ``ls /tmp`` while being clearly owned by Umbral.
WORKSPACE_PREFIX: str = "umbral-sbx-"

# Path to the checked-in allowlist file. Resolved lazily from the
# module's own location rather than from repo_root, so the allowlist
# lives next to the sandbox image definition and cannot be swapped by
# a caller supplying a different repo_root.
ALLOWLIST_PATH: Path = Path(__file__).parent / "test_allowlist.txt"

# Guardrails on the validation_target path shape. Caller-supplied
# ``target_file`` paths come from slice-4b validation already; this
# is an additional, sandbox-specific ring.
_TEST_PATH_RE: re.Pattern = re.compile(
    r"^tests/[A-Za-z0-9_./-]+\.py$"
)


# ---------------------------------------------------------------------------
# Allowlist loader
# ---------------------------------------------------------------------------

def load_test_allowlist(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and validate the test allowlist file.

    Returns ``{"ok": True, "tests": list[str], "error": None}`` or
    ``{"ok": False, "tests": [], "error": str}``. Never raises.

    The file format is one path per line, ``#`` comments and blank
    lines ignored. Every non-empty line must match ``tests/*.py`` and
    must resolve relative to the repo without ``..``.
    """
    target: Path = path if path is not None else ALLOWLIST_PATH
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "tests": [],
                "error": f"cannot read allowlist at {target}: {exc}"}

    tests: List[str] = []
    seen: set = set()
    for lineno, line in enumerate(raw.splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if not _TEST_PATH_RE.match(s):
            return {"ok": False, "tests": [],
                    "error": (f"invalid allowlist entry at line {lineno}: "
                              f"{s!r} (must match tests/*.py, no traversal)")}
        if ".." in Path(s).parts:
            return {"ok": False, "tests": [],
                    "error": f"traversal in allowlist at line {lineno}: {s!r}"}
        if s in seen:
            return {"ok": False, "tests": [],
                    "error": f"duplicate allowlist entry: {s!r}"}
        seen.add(s)
        tests.append(s)

    if not tests:
        return {"ok": False, "tests": [],
                "error": "allowlist is empty"}
    return {"ok": True, "tests": tests, "error": None}


# ---------------------------------------------------------------------------
# Validation target resolution
# ---------------------------------------------------------------------------

def derive_candidate_test_targets(target_file: str) -> List[str]:
    """Given ``target_file``, return a deterministic ordered list of
    conventional pytest file candidates.

    Pure, never raises. Always returns a list (possibly empty). Does
    NOT consult the filesystem and does NOT consult the allowlist.
    """
    if not isinstance(target_file, str) or not target_file:
        return []
    try:
        p = Path(target_file)
    except (TypeError, ValueError):
        return []
    if not p.suffix == ".py":
        return []
    stem = p.stem
    parent = p.parent.name
    candidates: List[str] = []
    seen: set = set()

    def _push(rel: str) -> None:
        if rel not in seen:
            seen.add(rel)
            candidates.append(rel)

    _push(f"tests/test_{stem}.py")
    _push(f"tests/test_{stem}_handler.py")
    if parent:
        _push(f"tests/test_{parent}_{stem}.py")
    return candidates


def resolve_validation_target(
    target_file: str,
    repo_root: Path,
    allowlist: List[str],
) -> Dict[str, Any]:
    """Pick the first candidate that is (a) in the allowlist and (b)
    exists under ``repo_root``.

    Returns ``{"ok": True, "resolved": "tests/test_X.py",
    "candidates_tried": [...], "error": None}`` on success, else
    ``{"ok": False, "resolved": None, "candidates_tried": [...],
    "error": str}``. Never raises.
    """
    if not target_file or not isinstance(target_file, str):
        return {"ok": False, "resolved": None, "candidates_tried": [],
                "error": "target_file must be a non-empty string"}
    if not isinstance(repo_root, Path):
        return {"ok": False, "resolved": None, "candidates_tried": [],
                "error": "repo_root must be a Path"}
    if not allowlist:
        return {"ok": False, "resolved": None, "candidates_tried": [],
                "error": "test allowlist is empty"}

    allow_set = set(allowlist)
    candidates = derive_candidate_test_targets(target_file)
    tried: List[str] = []
    for rel in candidates:
        tried.append(rel)
        if rel not in allow_set:
            continue
        try:
            if (repo_root / rel).is_file():
                return {"ok": True, "resolved": rel,
                        "candidates_tried": tried, "error": None}
        except OSError:
            continue
    return {"ok": False, "resolved": None, "candidates_tried": tried,
            "error": ("no candidate matched both the allowlist and an "
                      "existing file on disk")}


# ---------------------------------------------------------------------------
# Workspace build / overwrite / cleanup
# ---------------------------------------------------------------------------

def _is_excluded_basename(name: str) -> bool:
    if name in _EXCLUDE_BASENAMES:
        return True
    if any(name.endswith(sfx) for sfx in _EXCLUDE_SUFFIXES):
        return True
    if _EXCLUDE_BASENAME_RE.match(name):
        return True
    return False


def _safe_copy_tree(src: Path, dest: Path) -> None:
    """Recursive copy that respects the exclusion rules on basenames.

    Not a generic ``shutil.copytree`` replacement; only used from
    inside :func:`build_workspace` on paths it has already validated.
    """
    dest.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        name = entry.name
        if _is_excluded_basename(name):
            continue
        target = dest / name
        if entry.is_symlink():
            # Skip symlinks entirely — they could point outside the
            # allowlisted tree and defeat the sandbox boundary.
            continue
        if entry.is_dir():
            _safe_copy_tree(entry, target)
        elif entry.is_file():
            shutil.copy2(entry, target)


def build_workspace(
    repo_root: Path,
    tournament_id: str,
    *,
    parent_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Materialise a sandbox workspace under ``parent_dir`` (default
    ``/tmp``) by copying only the allowlisted top-level entries of
    ``repo_root``.

    Returns ``{"ok": True, "path": Path, "copied": list[str],
    "error": None}`` or ``{"ok": False, "path": None, "copied": [],
    "error": str}``. Never raises.

    The workspace is owned by the calling uid and is safe to
    ``cleanup_workspace`` afterwards.
    """
    if not isinstance(repo_root, Path):
        return {"ok": False, "path": None, "copied": [],
                "error": "repo_root must be a Path"}
    if not repo_root.is_dir():
        return {"ok": False, "path": None, "copied": [],
                "error": f"repo_root does not exist: {repo_root}"}
    if not tournament_id or not isinstance(tournament_id, str):
        return {"ok": False, "path": None, "copied": [],
                "error": "tournament_id must be a non-empty string"}
    # Charset guard: tournament_id feeds the workspace name under
    # /tmp, so we constrain it to a safe shape. Slice 4a uses the
    # same charset for branch labels.
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", tournament_id):
        return {"ok": False, "path": None, "copied": [],
                "error": "tournament_id charset: [A-Za-z0-9_.-] only"}

    base = parent_dir if parent_dir is not None else Path(tempfile.gettempdir())
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"ok": False, "path": None, "copied": [],
                "error": f"cannot prepare parent dir {base}: {exc}"}

    # Add a short uuid tail so two runs with the same tournament_id
    # never collide on /tmp.
    ws_name = f"{WORKSPACE_PREFIX}{tournament_id}-{uuid.uuid4().hex[:8]}"
    ws_path = base / ws_name

    copied: List[str] = []
    try:
        ws_path.mkdir(parents=True, exist_ok=False)
        for entry in sorted(repo_root.iterdir()):
            name = entry.name
            if entry.is_symlink():
                continue
            if name in TOP_LEVEL_FILES_ALLOWLIST and entry.is_file():
                shutil.copy2(entry, ws_path / name)
                copied.append(name)
                continue
            if name in TOP_LEVEL_ALLOWLIST and entry.is_dir():
                _safe_copy_tree(entry, ws_path / name)
                copied.append(name + "/")
                continue
            # Everything else is silently dropped.
    except OSError as exc:
        # Best-effort cleanup of the half-built workspace.
        shutil.rmtree(ws_path, ignore_errors=True)
        return {"ok": False, "path": None, "copied": [],
                "error": f"failed to build workspace: {exc}"}

    return {"ok": True, "path": ws_path, "copied": copied, "error": None}


def overwrite_file_in_workspace(
    ws_path: Path,
    rel_path: str,
    content: str,
) -> Dict[str, Any]:
    """Overwrite ``rel_path`` (relative to ``ws_path``) with
    ``content``.

    The resolved path MUST stay strictly inside ``ws_path``. Returns
    a never-raising dict.
    """
    if not isinstance(ws_path, Path):
        return {"ok": False, "error": "ws_path must be a Path"}
    if not isinstance(rel_path, str) or not rel_path:
        return {"ok": False, "error": "rel_path must be a non-empty string"}
    if not isinstance(content, str):
        return {"ok": False, "error": "content must be a string"}
    if (
        os.path.isabs(rel_path)
        or PurePosixPath(rel_path).is_absolute()
        or PureWindowsPath(rel_path).is_absolute()
    ):
        return {"ok": False, "error": "rel_path must be relative"}
    if ".." in Path(rel_path).parts:
        return {"ok": False, "error": "rel_path must not contain '..'"}

    try:
        ws_abs = ws_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return {"ok": False, "error": f"ws_path does not exist: {exc}"}

    candidate = (ws_abs / rel_path).resolve()
    try:
        candidate.relative_to(ws_abs)
    except ValueError:
        return {"ok": False, "error": "resolved path escapes workspace"}

    try:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": f"write failed: {exc}"}
    return {"ok": True, "error": None, "path": candidate}


def cleanup_workspace(ws_path: Path) -> Dict[str, Any]:
    """Remove ``ws_path`` recursively. Refuses to touch anything that
    does not look like a workspace this module created.

    Returns a never-raising dict.
    """
    if not isinstance(ws_path, Path):
        return {"ok": False, "error": "ws_path must be a Path"}
    if not ws_path.exists():
        return {"ok": True, "error": None, "removed": False}
    try:
        ws_abs = ws_path.resolve()
    except (OSError, RuntimeError) as exc:
        return {"ok": False, "error": f"cannot resolve ws_path: {exc}"}

    # Refuse to remove anything whose basename doesn't start with our
    # prefix. This is a belt-and-suspenders check so a bug in the
    # caller (e.g. passing ``/`` by accident) never wipes the host.
    if not ws_abs.name.startswith(WORKSPACE_PREFIX):
        return {"ok": False, "error": (
            f"refusing to clean path without '{WORKSPACE_PREFIX}' prefix: "
            f"{ws_abs}")}

    # Refuse to remove anything that is not under a conventional
    # temporary parent. The most common case is /tmp; we also accept
    # anything strictly deeper than the system temp dir or an explicit
    # test tmp_path under pytest's tmp tree.
    try:
        tmp_root = Path(tempfile.gettempdir()).resolve()
    except (OSError, RuntimeError):
        tmp_root = Path("/tmp")
    try:
        ws_abs.relative_to(tmp_root)
    except ValueError:
        return {"ok": False, "error": (
            f"refusing to clean path not under tmp root {tmp_root}: "
            f"{ws_abs}")}

    try:
        shutil.rmtree(ws_abs)
    except OSError as exc:
        return {"ok": False, "error": f"rmtree failed: {exc}"}
    return {"ok": True, "error": None, "removed": True}
