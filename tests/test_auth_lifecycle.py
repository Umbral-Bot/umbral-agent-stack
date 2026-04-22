"""
Tests for infra/auth_lifecycle.py — credential lifecycle classification.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from infra.auth_lifecycle import (
    AuthLifecycleStatus,
    build_auth_lifecycle_record,
    classify_auth_lifecycle,
    days_until_expiry,
    parse_expiry,
    strip_sensitive_fields,
)


NOW = datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# parse_expiry
# ---------------------------------------------------------------------------


class TestParseExpiry:
    def test_iso_string_with_tz(self):
        dt = parse_expiry("2026-06-15T00:00:00+00:00")
        assert dt is not None
        assert dt.tzinfo is not None
        assert dt.year == 2026

    def test_iso_string_without_tz_assumes_utc(self):
        dt = parse_expiry("2026-06-15T00:00:00")
        assert dt is not None
        assert dt.tzinfo == timezone.utc

    def test_datetime_passthrough(self):
        original = datetime(2026, 6, 15, tzinfo=timezone.utc)
        assert parse_expiry(original) is original

    def test_naive_datetime_gets_utc(self):
        naive = datetime(2026, 6, 15)
        result = parse_expiry(naive)
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_none_returns_none(self):
        assert parse_expiry(None) is None

    def test_empty_string_returns_none(self):
        assert parse_expiry("") is None
        assert parse_expiry("   ") is None

    def test_invalid_string_returns_none(self):
        assert parse_expiry("not-a-date") is None
        assert parse_expiry("12345") is None

    def test_non_string_non_datetime_returns_none(self):
        assert parse_expiry(12345) is None
        assert parse_expiry([]) is None


# ---------------------------------------------------------------------------
# days_until_expiry
# ---------------------------------------------------------------------------


class TestDaysUntilExpiry:
    def test_future_date(self):
        expires = NOW + timedelta(days=30)
        assert days_until_expiry(expires, NOW) == 30

    def test_past_date(self):
        expires = NOW - timedelta(days=5)
        assert days_until_expiry(expires, NOW) == -5

    def test_same_day(self):
        assert days_until_expiry(NOW, NOW) == 0

    def test_none_returns_none(self):
        assert days_until_expiry(None, NOW) is None


# ---------------------------------------------------------------------------
# classify_auth_lifecycle
# ---------------------------------------------------------------------------


class TestClassifyAuthLifecycle:
    def test_ok_far_future(self):
        expires = NOW + timedelta(days=60)
        assert classify_auth_lifecycle(expires, NOW) == AuthLifecycleStatus.OK

    def test_warning_within_window(self):
        expires = NOW + timedelta(days=10)
        assert classify_auth_lifecycle(expires, NOW, warning_days=14) == AuthLifecycleStatus.WARNING

    def test_critical_within_window(self):
        expires = NOW + timedelta(days=2)
        assert classify_auth_lifecycle(expires, NOW, critical_days=3) == AuthLifecycleStatus.CRITICAL

    def test_expired_past(self):
        expires = NOW - timedelta(days=1)
        assert classify_auth_lifecycle(expires, NOW) == AuthLifecycleStatus.EXPIRED

    def test_expired_exact_now(self):
        assert classify_auth_lifecycle(NOW, NOW) == AuthLifecycleStatus.EXPIRED

    def test_unknown_no_expiry(self):
        assert classify_auth_lifecycle(None, NOW) == AuthLifecycleStatus.UNKNOWN

    def test_custom_thresholds(self):
        expires = NOW + timedelta(days=5)
        assert classify_auth_lifecycle(
            expires, NOW, warning_days=7, critical_days=2,
        ) == AuthLifecycleStatus.WARNING

    def test_boundary_exactly_warning_days(self):
        expires = NOW + timedelta(days=14)
        assert classify_auth_lifecycle(expires, NOW, warning_days=14) == AuthLifecycleStatus.WARNING

    def test_boundary_exactly_critical_days(self):
        expires = NOW + timedelta(days=3)
        assert classify_auth_lifecycle(expires, NOW, critical_days=3) == AuthLifecycleStatus.CRITICAL


# ---------------------------------------------------------------------------
# strip_sensitive_fields
# ---------------------------------------------------------------------------


class TestStripSensitiveFields:
    def test_removes_known_sensitive(self):
        data = {"provider": "test", "token": "abc123", "secret": "xyz"}
        result = strip_sensitive_fields(data)
        assert "token" not in result
        assert "secret" not in result
        assert result["provider"] == "test"

    def test_case_insensitive(self):
        data = {"API_KEY": "val", "Password": "val", "provider": "test"}
        result = strip_sensitive_fields(data)
        assert "API_KEY" not in result
        assert "Password" not in result

    def test_keeps_safe_fields(self):
        data = {"provider": "x", "credential_ref": "y", "status": "ok"}
        result = strip_sensitive_fields(data)
        assert result == data


# ---------------------------------------------------------------------------
# build_auth_lifecycle_record
# ---------------------------------------------------------------------------


class TestBuildAuthLifecycleRecord:
    def test_basic_record_with_expiry(self):
        expires = NOW + timedelta(days=30)
        record = build_auth_lifecycle_record(
            provider="linkedin",
            credential_ref="linkedin_company_access_token",
            expires_at=expires,
            now=NOW,
        )
        assert record["provider"] == "linkedin"
        assert record["credential_ref"] == "linkedin_company_access_token"
        assert record["status"] == "ok"
        assert record["days_until_expiry"] == 30
        assert record["reauth_required"] is False

    def test_expired_record(self):
        expires = NOW - timedelta(days=5)
        record = build_auth_lifecycle_record(
            provider="linkedin",
            credential_ref="linkedin_company_access_token",
            expires_at=expires,
            now=NOW,
        )
        assert record["status"] == "expired"
        assert record["reauth_required"] is True

    def test_unknown_no_expiry(self):
        record = build_auth_lifecycle_record(
            provider="ghost",
            credential_ref="ghost_admin_api_key",
            now=NOW,
        )
        assert record["status"] == "unknown"
        assert record["expires_at"] is None
        assert record["days_until_expiry"] is None

    def test_strips_sensitive_extra_fields(self):
        record = build_auth_lifecycle_record(
            provider="linkedin",
            credential_ref="test_token",
            now=NOW,
            token="SHOULD_NOT_APPEAR",
            api_key="ALSO_HIDDEN",
            safe_field="visible",
        )
        assert "token" not in record
        assert "api_key" not in record
        assert record["safe_field"] == "visible"

    def test_details_truncated(self):
        long_details = "x" * 500
        record = build_auth_lifecycle_record(
            provider="test",
            credential_ref="test_ref",
            now=NOW,
            details=long_details,
        )
        assert len(record["details"]) == 300

    def test_includes_source_and_trace_id(self):
        record = build_auth_lifecycle_record(
            provider="test",
            credential_ref="test_ref",
            now=NOW,
            source="health_check",
            source_kind="cron",
            trace_id="trace-abc",
        )
        assert record["source"] == "health_check"
        assert record["source_kind"] == "cron"
        assert record["trace_id"] == "trace-abc"
