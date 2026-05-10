"""Append-only writer for publish_log.jsonl observability log.

Defined by ``docs/editorial-pipeline/publish-log-contract.md`` (#404-lite).

This module is intentionally permissive: it does NOT validate event keys
against the contract schema. Schema enforcement is the responsibility of
the caller (publish_guard, the future #402 publisher, the future #404
dashboard). A writer that rejects malformed events leaves no trace of
the event, which is the wrong default for an audit log.
"""

from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime, timezone

DEFAULT_PATH = pathlib.Path.home() / ".config" / "umbral" / "publish_log.jsonl"
ENV_VAR = "PUBLISH_LOG_PATH"


def _resolve_path(path: str | os.PathLike | None) -> pathlib.Path:
    if path is not None:
        return pathlib.Path(path)
    env = os.environ.get(ENV_VAR)
    if env:
        return pathlib.Path(env)
    return DEFAULT_PATH


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def write_event(
    event: dict,
    path: str | os.PathLike | None = None,
) -> pathlib.Path:
    """Append one JSON line to publish_log.jsonl.

    Resolution order for the destination path:
        1. ``path`` argument.
        2. ``PUBLISH_LOG_PATH`` env var.
        3. ``~/.config/umbral/publish_log.jsonl``.

    The parent directory is created if it does not exist
    (``mkdir -p`` semantics). The file is opened in append mode for each
    call so no buffering survives across invocations.

    If ``timestamp_utc`` is missing from ``event``, an ISO-8601 UTC
    timestamp (``YYYY-MM-DDTHH:MM:SSZ``) is auto-injected. Existing
    timestamps are preserved verbatim.

    Returns the resolved path that was written to (useful for tests).

    Raises ``TypeError`` only if ``event`` is not a dict.
    """
    if not isinstance(event, dict):
        raise TypeError("event must be a dict")
    target = _resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    record = dict(event)  # shallow copy, do not mutate caller dict
    record.setdefault("timestamp_utc", _utc_now_iso())
    line = json.dumps(record, ensure_ascii=False, sort_keys=False)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return target


def read_events(path: str | os.PathLike | None = None) -> list[dict]:
    """Read every event line from publish_log.jsonl.

    Helper for tests and ad-hoc inspection. Returns ``[]`` when the file
    does not exist. Skips blank lines silently. Malformed lines raise
    ``json.JSONDecodeError`` so that corruption is loud.
    """
    target = _resolve_path(path)
    if not target.exists():
        return []
    out: list[dict] = []
    for raw in target.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        out.append(json.loads(raw))
    return out
