"""
Publish Tracking — Structured records for publication attempts.

Pure functions for building, sanitizing, and classifying publication
events (attempt / success / failed) across channels (ghost, linkedin,
x, manual).  No side effects, no network calls, no secret handling.

This module provides the data layer that OpsLogger.publish_attempt,
OpsLogger.publish_success, and OpsLogger.publish_failed consume.
"""
from __future__ import annotations

import enum
import hashlib
import json
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Channel taxonomy
# ---------------------------------------------------------------------------

class PublishChannel(str, enum.Enum):
    GHOST = "ghost"
    LINKEDIN = "linkedin"
    X = "x"
    MANUAL = "manual"
    UNKNOWN = "unknown"


_CHANNEL_ALIASES: dict[str, str] = {
    "ghost": "ghost",
    "linkedin": "linkedin",
    "x": "x",
    "twitter": "x",
    "manual": "manual",
}


def normalize_publish_channel(value: Any) -> str:
    """Return a stable channel string; unknown inputs map to ``"unknown"``."""
    if value is None:
        return PublishChannel.UNKNOWN.value
    text = str(value).strip().lower()
    return _CHANNEL_ALIASES.get(text, PublishChannel.UNKNOWN.value)


# ---------------------------------------------------------------------------
# Event taxonomy
# ---------------------------------------------------------------------------

class PublishEvent(str, enum.Enum):
    ATTEMPT = "publish_attempt"
    SUCCESS = "publish_success"
    FAILED = "publish_failed"


# ---------------------------------------------------------------------------
# Content hashing (deterministic, no secrets)
# ---------------------------------------------------------------------------

def compute_content_hash(content: str | dict | None) -> str:
    """Return a deterministic SHA-256 hex digest (first 16 chars).

    - ``str``: hash the UTF-8 bytes directly.
    - ``dict``: serialize with ``sort_keys=True`` and ``ensure_ascii=False``.
    - ``None`` / empty: returns ``"empty"``.
    """
    if content is None:
        return "empty"
    if isinstance(content, dict):
        raw = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str)
    else:
        raw = str(content)
    if not raw.strip():
        return "empty"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Sensitive field stripping
# ---------------------------------------------------------------------------

_SENSITIVE_FIELD_NAMES: frozenset[str] = frozenset({
    "secret",
    "token",
    "api_key",
    "password",
    "credential_value",
    "access_token",
    "refresh_token",
    "private_key",
    "encryption_key",
    "key_value",
    "bearer",
    "authorization",
})


def sanitize_publish_metadata(metadata: dict | None) -> dict:
    """Return a copy of *metadata* with sensitive keys removed."""
    if not metadata or not isinstance(metadata, dict):
        return {}
    return {
        k: v for k, v in metadata.items()
        if k.lower() not in _SENSITIVE_FIELD_NAMES
    }


# ---------------------------------------------------------------------------
# Idempotency key
# ---------------------------------------------------------------------------

def _derive_idempotency_key(
    channel: str,
    content_hash: str,
    notion_page_id: str | None,
) -> str:
    """Derive a stable idempotency key from channel + content_hash + notion_page_id."""
    parts = [channel, content_hash, str(notion_page_id or "")]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

_MAX_FIELD_LEN = 300


def _truncate(value: Any, limit: int = _MAX_FIELD_LEN) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit] if len(text) > limit else text


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def build_publish_record(
    *,
    event: str,
    channel: str | None = None,
    publication_id: str | None = None,
    notion_page_id: str | None = None,
    content_hash: str | None = None,
    idempotency_key: str | None = None,
    platform_post_id: str | None = None,
    publication_url: str | None = None,
    attempt: int = 1,
    error_kind: str | None = None,
    error_code: str | None = None,
    retryable: bool | None = None,
    provider: str | None = None,
    metadata: dict | None = None,
    trace_id: str | None = None,
    source: str | None = None,
    source_kind: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a publish tracking record ready for OpsLogger.

    - Normalizes channel via ``normalize_publish_channel``.
    - Strips sensitive fields from ``metadata`` and ``**extra``.
    - Derives ``idempotency_key`` if not provided.
    - Truncates long string fields.
    - Never includes full post content.
    """
    norm_channel = normalize_publish_channel(channel)
    safe_hash = content_hash or "empty"

    if not idempotency_key:
        idempotency_key = _derive_idempotency_key(
            norm_channel, safe_hash, notion_page_id,
        )

    record: dict[str, Any] = {
        "event": str(event),
        "channel": norm_channel,
        "status": str(event).replace("publish_", ""),
        "content_hash": safe_hash,
        "idempotency_key": idempotency_key,
        "attempt": int(attempt),
    }

    # Optional fields — omit if None
    if publication_id is not None:
        record["publication_id"] = _truncate(publication_id, 200)
    if notion_page_id is not None:
        record["notion_page_id"] = _truncate(notion_page_id, 200)
    if platform_post_id is not None:
        record["platform_post_id"] = _truncate(platform_post_id, 200)
    if publication_url is not None:
        record["publication_url"] = _truncate(publication_url, 500)
    if error_kind is not None:
        record["error_kind"] = _truncate(error_kind, 120)
    if error_code is not None:
        record["error_code"] = _truncate(error_code, 60)
    if retryable is not None:
        record["retryable"] = bool(retryable)
    if provider is not None:
        record["provider"] = _truncate(provider, 120)
    if trace_id is not None:
        record["trace_id"] = _truncate(trace_id)
    if source is not None:
        record["source"] = _truncate(source, 200)
    if source_kind is not None:
        record["source_kind"] = _truncate(source_kind, 200)

    # Metadata — sanitized
    if metadata:
        safe_meta = sanitize_publish_metadata(metadata)
        if safe_meta:
            record["metadata"] = safe_meta

    # Extra kwargs — strip sensitive
    safe_extra = sanitize_publish_metadata(extra)
    for k, v in safe_extra.items():
        if k not in record:
            record[k] = _truncate(v) if isinstance(v, str) else v

    return record
