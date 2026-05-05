"""Adapter: estado de quota Claude Pro (lectura, sin bloqueo).

Espera un JSON producido por `scripts/openclaw-claude-quota.py` (no parte del
MVP de Mission Control). Si el file no existe, devuelve `available=False`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import config


def read_state(path: Path | None = None) -> dict[str, Any]:
    target = path or config.QUOTA_STATE_PATH
    if not target.exists():
        return {
            "available": False,
            "error": f"quota state file not found: {target}",
            "source": str(target),
        }

    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "source": str(target),
        }

    return {
        "available": True,
        "source": str(target),
        "state": raw,
    }
