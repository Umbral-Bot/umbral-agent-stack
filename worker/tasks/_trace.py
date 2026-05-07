"""Append-only delegation trace log (Ola 1b, ADR 05 §2.3).

Single public helper: ``append_delegation(record)``.

Uses ``fcntl.flock`` on the VPS Linux runtime. Local non-POSIX test runs
fall back to process-local locking around append-only writes.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows local runs
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)
_FALLBACK_LOCK = threading.Lock()

DEFAULT_LOG_PATH = Path(
    os.environ.get("UMBRAL_DELEGATIONS_LOG", "~/.local/state/umbral/delegations.jsonl")
).expanduser()

_REQUIRED_FIELDS = ("from", "to", "intent")
_FORBIDDEN_KEYS = frozenset({"text", "secret", "token", "api_key", "password"})
_SUMMARY_MAX_LEN = 200
_FILE_MODE = 0o600


def _check_forbidden(record: dict) -> None:
    """Reject sensitive keys at any nesting level."""
    stack: list = [record]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, str) and k.lower() in _FORBIDDEN_KEYS:
                    raise ValueError(f"forbidden key in delegation record: {k!r}")
                stack.append(v)
        elif isinstance(node, list):
            stack.extend(node)


def append_delegation(record: dict) -> None:
    """Append a delegation record to the JSONL log (atomic, 0o600).

    Required keys: ``from``, ``to``, ``intent``.
    Auto-injects ``ts`` (UTC ISO 8601) and ``trace_id`` (uuid4 hex) if absent.
    Truncates ``summary`` to 200 chars. Rejects keys ``text``, ``secret``,
    ``token``, ``api_key``, ``password``.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    for field in _REQUIRED_FIELDS:
        if not record.get(field):
            raise ValueError(f"missing required field: {field!r}")
    _check_forbidden(record)

    record = dict(record)
    record.setdefault("ts", datetime.now(timezone.utc).isoformat())
    record.setdefault("trace_id", uuid.uuid4().hex)

    summary = record.get("summary")
    if isinstance(summary, str) and len(summary) > _SUMMARY_MAX_LEN:
        logger.warning("delegation summary truncated from %d to %d chars",
                       len(summary), _SUMMARY_MAX_LEN)
        record["summary"] = summary[:_SUMMARY_MAX_LEN]

    log_path = Path(
        os.environ.get("UMBRAL_DELEGATIONS_LOG") or str(DEFAULT_LOG_PATH)
    ).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    lock_context = _FALLBACK_LOCK if fcntl is None else nullcontext()
    with lock_context:
        existed = log_path.exists()
        fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, _FILE_MODE)
        try:
            if existed:
                current_mode = log_path.stat().st_mode & 0o777
                if current_mode != _FILE_MODE:
                    logger.warning("delegations log mode was %o, forcing %o",
                                   current_mode, _FILE_MODE)
                    os.chmod(log_path, _FILE_MODE)
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                os.write(fd, line.encode("utf-8"))
            finally:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
