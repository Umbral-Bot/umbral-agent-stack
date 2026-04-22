"""Structured error classification for operational telemetry.

The classifier intentionally stays conservative: it labels failures with a
small stable taxonomy so dashboards and alerts can aggregate incidents without
depending on free-form exception text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ERROR_KINDS: frozenset[str] = frozenset(
    {
        "timeout",
        "auth",
        "quota",
        "upstream",
        "data",
        "config",
        "validation",
        "unknown",
    }
)


@dataclass(frozen=True)
class ErrorClassification:
    error_kind: str
    error_code: str
    retryable: bool


def normalize_error_kind(value: Any) -> str:
    """Return a stable error kind, falling back to ``unknown``."""
    try:
        text = str(value).strip().lower()
    except Exception:
        return "unknown"
    return text if text in ERROR_KINDS else "unknown"


def classify_error(error: BaseException | str | None) -> ErrorClassification:
    """Classify an exception or message into the stable telemetry taxonomy."""
    if error is None:
        return _classification("unknown", retryable=False)

    name = ""
    if isinstance(error, BaseException):
        name = error.__class__.__name__.lower()
        message = str(error)
    else:
        message = str(error)
    text = f"{name} {message}".strip().lower()

    if any(token in text for token in ("timeout", "timed out", "readtimeout", "writetimeout", "connecttimeout")):
        return _classification("timeout", retryable=True)

    if any(token in text for token in ("quota", "rate limit", "rate-limit", "429", "too many requests", "exceeded")):
        return _classification("quota", retryable=False)

    if any(token in text for token in ("not configured", "missing env", "environment variable", "no_configured_provider", "config")):
        return _classification("config", retryable=False)

    if any(token in text for token in ("unauthorized", "forbidden", "401", "403", "bearer", "token", "credential", "permission")):
        return _classification("auth", retryable=False)

    if any(token in text for token in ("valueerror", "validation", "invalid", "unsupported", "required", "unknown task")):
        return _classification("validation", retryable=False)

    if any(token in text for token in ("jsondecodeerror", "decode", "malformed", "parse", "schema")):
        return _classification("data", retryable=False)

    if any(
        token in text
        for token in (
            "httpstatuserror",
            "connecterror",
            "connection error",
            "connection refused",
            "unreachable",
            "upstream",
            "502",
            "503",
            "504",
            "server error",
            "service unavailable",
        )
    ):
        return _classification("upstream", retryable=True)

    return _classification("unknown", retryable=False)


def _classification(kind: str, *, retryable: bool) -> ErrorClassification:
    normalized = normalize_error_kind(kind)
    return ErrorClassification(
        error_kind=normalized,
        error_code=f"task_failed_{normalized}",
        retryable=retryable,
    )
