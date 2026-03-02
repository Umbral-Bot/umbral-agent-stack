"""S5 — Windows filesystem tasks (no PAD).

Goal: allow simple file operations on the VM (e.g., Google Drive mounted as G:\\)
without requiring Power Automate Desktop.

Security model:
- Restricted by ToolPolicy allowlist of base paths.
- Blocks path traversal outside allowed bases.

Tasks:
- windows.fs.ensure_dirs: create directory tree
- windows.fs.list: list directory entries
- windows.fs.read_text: read a UTF-8 text file (size-limited)
- windows.fs.write_text: write a UTF-8 text file (size-limited)

"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from .. import tool_policy

logger = logging.getLogger("worker.tasks.windows_fs")


def _norm(p: str) -> str:
    # Normalize Windows paths; keep drive letters.
    return os.path.normpath(p).rstrip("\\/")


def _is_under_base(target: str, base: str) -> bool:
    """Return True if target path is inside base path (case-insensitive on Windows)."""
    t = _norm(target)
    b = _norm(base)
    try:
        # commonpath is reliable for path containment.
        cp = os.path.commonpath([t, b])
    except Exception:
        return False
    return cp.lower() == b.lower()


def _require_allowed_path(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("'path' (str) is required")
    p = _norm(path.strip())
    bases = tool_policy.get_fs_allowed_base_paths()
    if not bases:
        raise ValueError("FS tools disabled: no allowed base paths in tool_policy.yaml")
    for base in bases:
        if _is_under_base(p, base):
            return p
    raise ValueError(f"Path not allowed by policy. path={p}")


def handle_windows_fs_ensure_dirs(input_data: Dict[str, Any]) -> Dict[str, Any]:
    if sys.platform != "win32":
        return {"ok": False, "error": "Solo disponible en Windows."}
    path = _require_allowed_path(input_data.get("path", ""))
    try:
        os.makedirs(path, exist_ok=True)
        return {"ok": True, "path": path, "error": None}
    except Exception as e:
        logger.exception("ensure_dirs failed")
        return {"ok": False, "path": path, "error": str(e)}


def handle_windows_fs_list(input_data: Dict[str, Any]) -> Dict[str, Any]:
    if sys.platform != "win32":
        return {"ok": False, "error": "Solo disponible en Windows."}
    path = _require_allowed_path(input_data.get("path", ""))
    limit = int(input_data.get("limit", 200))
    try:
        entries: List[Dict[str, Any]] = []
        with os.scandir(path) as it:
            for i, ent in enumerate(it):
                if i >= limit:
                    break
                try:
                    st = ent.stat()
                    entries.append(
                        {
                            "name": ent.name,
                            "path": _norm(os.path.join(path, ent.name)),
                            "is_dir": ent.is_dir(),
                            "size": int(getattr(st, "st_size", 0)),
                            "mtime": float(getattr(st, "st_mtime", 0.0)),
                        }
                    )
                except Exception:
                    entries.append({"name": ent.name, "path": _norm(os.path.join(path, ent.name))})
        return {"ok": True, "path": path, "entries": entries, "error": None}
    except Exception as e:
        logger.exception("list failed")
        return {"ok": False, "path": path, "entries": [], "error": str(e)}


def handle_windows_fs_read_text(input_data: Dict[str, Any]) -> Dict[str, Any]:
    if sys.platform != "win32":
        return {"ok": False, "error": "Solo disponible en Windows."}
    path = _require_allowed_path(input_data.get("path", ""))
    max_chars = int(input_data.get("max_chars", 200_000))
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read(max_chars + 1)
        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars]
        return {"ok": True, "path": path, "text": text, "truncated": truncated, "error": None}
    except Exception as e:
        logger.exception("read_text failed")
        return {"ok": False, "path": path, "text": "", "truncated": False, "error": str(e)}


def handle_windows_fs_write_text(input_data: Dict[str, Any]) -> Dict[str, Any]:
    if sys.platform != "win32":
        return {"ok": False, "error": "Solo disponible en Windows."}
    path = _require_allowed_path(input_data.get("path", ""))
    text = input_data.get("text", "")
    if not isinstance(text, str):
        raise ValueError("'text' (str) is required")
    max_chars = int(input_data.get("max_chars", 500_000))
    if len(text) > max_chars:
        raise ValueError(f"text too large ({len(text)} chars), max {max_chars}")
    try:
        parent = _norm(str(Path(path).parent))
        _require_allowed_path(parent)
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return {"ok": True, "path": path, "chars": len(text), "error": None}
    except Exception as e:
        logger.exception("write_text failed")
        return {"ok": False, "path": path, "chars": 0, "error": str(e)}
