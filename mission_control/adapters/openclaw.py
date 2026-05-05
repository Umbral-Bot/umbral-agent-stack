"""Adapter: lee `openclaw.json` desde el filesystem.

ADR-009 D1: lectura best-effort. Si el file no existe o está mal formado,
devuelve un snapshot con `available=False` + `error` legible — NO levanta excepción.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import config


@dataclass(frozen=True)
class OpenclawSnapshot:
    source_path: Path
    available: bool
    error: str | None = None
    agents: list[dict[str, Any]] = field(default_factory=list)
    channels: list[dict[str, Any]] = field(default_factory=list)


def read_snapshot(path: Path | None = None) -> OpenclawSnapshot:
    target = path or config.OPENCLAW_JSON_PATH
    if not target.exists():
        return OpenclawSnapshot(
            source_path=target,
            available=False,
            error=f"file not found: {target}",
        )

    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return OpenclawSnapshot(
            source_path=target,
            available=False,
            error=f"{type(exc).__name__}: {exc}",
        )

    return OpenclawSnapshot(
        source_path=target,
        available=True,
        agents=_normalize_list(raw.get("agents")),
        channels=_normalize_list(raw.get("channels")),
    )


def _normalize_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        out: list[dict[str, Any]] = []
        for name, payload in value.items():
            entry = {"name": name}
            if isinstance(payload, dict):
                entry.update(payload)
            else:
                entry["value"] = payload
            out.append(entry)
        return out
    return []
