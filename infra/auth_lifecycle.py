"""
Auth Lifecycle Tracking — classify credential expiry and emit telemetry.

Pure functions for evaluating the lifecycle status of external credentials
(LinkedIn tokens, Ghost API keys, n8n encryption keys, etc.) without
touching secrets or real providers.

Status taxonomy:
  ok       — credential has >warning_days until expiry
  warning  — credential expires within warning_days
  critical — credential expires within critical_days
  expired  — credential has already expired
  unknown  — no expiry information available (e.g. API keys with no known TTL)

Security invariant: **no secret values are ever stored, logged, or returned**.
Only the ``credential_ref`` label (e.g. ``linkedin_company_access_token``)
and metadata about lifecycle are tracked.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Optional


class AuthLifecycleStatus(str, enum.Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


# Fields that must never appear in lifecycle records or OpsLogger events.
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

_DETAILS_MAX_LEN = 300


def parse_expiry(value: Any) -> Optional[datetime]:
    """Parse an expiry value into a timezone-aware datetime, or None.

    Accepts ISO 8601 strings and datetime objects. Naive datetimes are
    treated as UTC.  Returns None for anything unparseable.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def days_until_expiry(
    expires_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> Optional[int]:
    """Return integer days until expiry, or None if expires_at is unknown."""
    if expires_at is None:
        return None
    if now is None:
        now = datetime.now(timezone.utc)
    delta = expires_at - now
    return delta.days


def classify_auth_lifecycle(
    expires_at: Optional[datetime],
    now: Optional[datetime] = None,
    *,
    warning_days: int = 14,
    critical_days: int = 3,
) -> AuthLifecycleStatus:
    """Classify credential lifecycle status based on expiry distance.

    Returns ``unknown`` when ``expires_at`` is None — never assumes ``ok``
    without evidence.
    """
    if expires_at is None:
        return AuthLifecycleStatus.UNKNOWN
    if now is None:
        now = datetime.now(timezone.utc)
    remaining = days_until_expiry(expires_at, now)
    if remaining is None:
        return AuthLifecycleStatus.UNKNOWN
    if remaining < 0 or expires_at <= now:
        return AuthLifecycleStatus.EXPIRED
    if remaining <= critical_days:
        return AuthLifecycleStatus.CRITICAL
    if remaining <= warning_days:
        return AuthLifecycleStatus.WARNING
    return AuthLifecycleStatus.OK


def strip_sensitive_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* with sensitive fields removed."""
    return {
        k: v for k, v in data.items()
        if k.lower() not in _SENSITIVE_FIELD_NAMES
    }


def build_auth_lifecycle_record(
    *,
    provider: str,
    credential_ref: str,
    expires_at: Optional[datetime] = None,
    now: Optional[datetime] = None,
    warning_days: int = 14,
    critical_days: int = 3,
    source: Optional[str] = None,
    source_kind: Optional[str] = None,
    details: Optional[str] = None,
    trace_id: Optional[str] = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a lifecycle record dict suitable for OpsLogger persistence.

    Any sensitive fields accidentally passed via ``**extra`` are stripped.
    """
    status = classify_auth_lifecycle(
        expires_at, now, warning_days=warning_days, critical_days=critical_days,
    )
    remaining = days_until_expiry(expires_at, now)
    reauth_required = status in (
        AuthLifecycleStatus.EXPIRED,
        AuthLifecycleStatus.CRITICAL,
    )

    record: dict[str, Any] = {
        "provider": str(provider),
        "credential_ref": str(credential_ref),
        "status": status.value,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "days_until_expiry": remaining,
        "warning_days": warning_days,
        "critical_days": critical_days,
        "reauth_required": reauth_required,
    }
    if source:
        record["source"] = str(source)[:200]
    if source_kind:
        record["source_kind"] = str(source_kind)[:200]
    if details:
        record["details"] = str(details)[:_DETAILS_MAX_LEN]
    if trace_id:
        record["trace_id"] = str(trace_id)

    # Merge extra fields but strip anything sensitive
    safe_extra = strip_sensitive_fields(extra)
    record.update(safe_extra)

    return record
