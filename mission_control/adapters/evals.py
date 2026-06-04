"""Read-only adapter for Core Eval Harness reports."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_latest_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "available": False,
            "read_only": True,
            "path": str(path),
            "error": "eval report not found",
            "report": None,
        }
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact parser class is not important.
        return {
            "available": False,
            "read_only": True,
            "path": str(path),
            "error": f"{type(exc).__name__}: {exc}",
            "report": None,
        }
    return {
        "available": True,
        "read_only": True,
        "path": str(path),
        "error": None,
        "report": report,
    }
