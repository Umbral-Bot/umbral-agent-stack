"""
Tests for infra/publish_tracking.py and OpsLogger publish events.
"""
from __future__ import annotations

import json

import pytest

from infra.publish_tracking import (
    PublishChannel,
    PublishEvent,
    build_publish_record,
    compute_content_hash,
    normalize_publish_channel,
    sanitize_publish_metadata,
    _derive_idempotency_key,
)
from infra.ops_logger import OpsLogger


# ---------------------------------------------------------------------------
# normalize_publish_channel
# ---------------------------------------------------------------------------


class TestNormalizePublishChannel:
    def test_known_channels(self):
        assert normalize_publish_channel("ghost") == "ghost"
        assert normalize_publish_channel("linkedin") == "linkedin"
        assert normalize_publish_channel("x") == "x"
        assert normalize_publish_channel("manual") == "manual"

    def test_twitter_alias(self):
        assert normalize_publish_channel("twitter") == "x"

    def test_case_insensitive(self):
        assert normalize_publish_channel("GHOST") == "ghost"
        assert normalize_publish_channel("LinkedIn") == "linkedin"

    def test_unknown_channel(self):
        assert normalize_publish_channel("tiktok") == "unknown"
        assert normalize_publish_channel("") == "unknown"

    def test_none_returns_unknown(self):
        assert normalize_publish_channel(None) == "unknown"

    def test_whitespace_stripped(self):
        assert normalize_publish_channel("  ghost  ") == "ghost"


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


class TestComputeContentHash:
    def test_deterministic_for_string(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        assert h1 == h2
        assert len(h1) == 16

    def test_deterministic_for_dict(self):
        d1 = {"title": "Post", "body": "Content"}
        d2 = {"body": "Content", "title": "Post"}
        assert compute_content_hash(d1) == compute_content_hash(d2)

    def test_different_content_different_hash(self):
        assert compute_content_hash("hello") != compute_content_hash("world")

    def test_none_returns_empty(self):
        assert compute_content_hash(None) == "empty"

    def test_empty_string_returns_empty(self):
        assert compute_content_hash("") == "empty"
        assert compute_content_hash("   ") == "empty"

    def test_dict_with_nested_values(self):
        d = {"a": 1, "b": {"c": 2}}
        h = compute_content_hash(d)
        assert len(h) == 16
        assert h == compute_content_hash(d)


# ---------------------------------------------------------------------------
# sanitize_publish_metadata
# ---------------------------------------------------------------------------


class TestSanitizePublishMetadata:
    def test_removes_sensitive_fields(self):
        meta = {
            "provider": "ghost",
            "token": "secret123",
            "access_token": "abc",
            "refresh_token": "xyz",
            "api_key": "key",
            "secret": "hidden",
            "password": "pass",
            "authorization": "Bearer xxx",
        }
        result = sanitize_publish_metadata(meta)
        assert "token" not in result
        assert "access_token" not in result
        assert "refresh_token" not in result
        assert "api_key" not in result
        assert "secret" not in result
        assert "password" not in result
        assert "authorization" not in result
        assert result["provider"] == "ghost"

    def test_case_insensitive_stripping(self):
        meta = {"TOKEN": "val", "Api_Key": "val", "safe": "ok"}
        result = sanitize_publish_metadata(meta)
        assert "TOKEN" not in result
        assert "Api_Key" not in result
        assert result["safe"] == "ok"

    def test_none_returns_empty(self):
        assert sanitize_publish_metadata(None) == {}

    def test_empty_dict(self):
        assert sanitize_publish_metadata({}) == {}

    def test_keeps_safe_fields(self):
        meta = {"provider": "ghost", "channel": "linkedin", "attempt": 1}
        assert sanitize_publish_metadata(meta) == meta


# ---------------------------------------------------------------------------
# idempotency_key
# ---------------------------------------------------------------------------


class TestIdempotencyKey:
    def test_deterministic(self):
        k1 = _derive_idempotency_key("ghost", "abc123", "page-001")
        k2 = _derive_idempotency_key("ghost", "abc123", "page-001")
        assert k1 == k2
        assert len(k1) == 20

    def test_different_inputs_different_key(self):
        k1 = _derive_idempotency_key("ghost", "abc", "page-001")
        k2 = _derive_idempotency_key("linkedin", "abc", "page-001")
        assert k1 != k2

    def test_none_page_id(self):
        k = _derive_idempotency_key("ghost", "abc123", None)
        assert len(k) == 20


# ---------------------------------------------------------------------------
# build_publish_record
# ---------------------------------------------------------------------------


class TestBuildPublishRecord:
    def test_basic_attempt_record(self):
        record = build_publish_record(
            event="publish_attempt",
            channel="ghost",
            content_hash="abc123def456",
            notion_page_id="page-001",
        )
        assert record["event"] == "publish_attempt"
        assert record["channel"] == "ghost"
        assert record["status"] == "attempt"
        assert record["content_hash"] == "abc123def456"
        assert "idempotency_key" in record
        assert record["attempt"] == 1

    def test_success_with_platform_fields(self):
        record = build_publish_record(
            event="publish_success",
            channel="ghost",
            content_hash="abc123",
            platform_post_id="ghost-post-123",
            publication_url="https://example.com/post",
        )
        assert record["platform_post_id"] == "ghost-post-123"
        assert record["publication_url"] == "https://example.com/post"

    def test_failed_with_error_fields(self):
        record = build_publish_record(
            event="publish_failed",
            channel="linkedin",
            error_kind="auth_expired",
            error_code="401",
            retryable=False,
        )
        assert record["error_kind"] == "auth_expired"
        assert record["error_code"] == "401"
        assert record["retryable"] is False

    def test_normalizes_channel(self):
        record = build_publish_record(
            event="publish_attempt",
            channel="Twitter",
        )
        assert record["channel"] == "x"

    def test_strips_sensitive_from_metadata(self):
        record = build_publish_record(
            event="publish_attempt",
            channel="ghost",
            metadata={"version": "1.0", "token": "SECRET"},
        )
        assert "token" not in record.get("metadata", {})
        assert record["metadata"]["version"] == "1.0"

    def test_strips_sensitive_from_extra(self):
        record = build_publish_record(
            event="publish_attempt",
            channel="ghost",
            api_key="SHOULD_NOT_APPEAR",
            safe_field="visible",
        )
        assert "api_key" not in record
        assert record["safe_field"] == "visible"

    def test_does_not_include_content_body(self):
        record = build_publish_record(
            event="publish_attempt",
            channel="ghost",
            content_hash="abc123",
        )
        assert "body" not in record
        assert "content" not in record

    def test_idempotency_key_deterministic(self):
        kwargs = dict(
            event="publish_attempt",
            channel="ghost",
            content_hash="abc123",
            notion_page_id="page-001",
        )
        r1 = build_publish_record(**kwargs)
        r2 = build_publish_record(**kwargs)
        assert r1["idempotency_key"] == r2["idempotency_key"]

    def test_explicit_idempotency_key_preserved(self):
        record = build_publish_record(
            event="publish_attempt",
            channel="ghost",
            idempotency_key="my-custom-key",
        )
        assert record["idempotency_key"] == "my-custom-key"

    def test_long_fields_truncated(self):
        record = build_publish_record(
            event="publish_attempt",
            channel="ghost",
            publication_url="x" * 1000,
            error_kind="y" * 500,
        )
        assert len(record["publication_url"]) == 500
        assert len(record["error_kind"]) == 120

    def test_optional_fields_omitted_when_none(self):
        record = build_publish_record(
            event="publish_attempt",
            channel="ghost",
        )
        assert "publication_id" not in record
        assert "notion_page_id" not in record
        assert "platform_post_id" not in record
        assert "publication_url" not in record
        assert "error_kind" not in record
        assert "trace_id" not in record


# ---------------------------------------------------------------------------
# OpsLogger.publish_attempt / publish_success / publish_failed
# ---------------------------------------------------------------------------


class TestOpsLoggerPublishEvents:
    @pytest.fixture
    def ops_logger(self, tmp_path):
        return OpsLogger(log_dir=tmp_path)

    def test_publish_attempt_writes_event(self, ops_logger):
        ops_logger.publish_attempt(
            channel="ghost",
            content_hash="abc123",
            notion_page_id="page-001",
            attempt=1,
            source="test",
        )
        events = ops_logger.read_events(event_filter="publish_attempt")
        assert len(events) == 1
        ev = events[0]
        assert ev["event"] == "publish_attempt"
        assert ev["channel"] == "ghost"
        assert ev["content_hash"] == "abc123"
        assert ev["attempt"] == 1
        assert "ts" in ev

    def test_publish_success_writes_platform_fields(self, ops_logger):
        ops_logger.publish_success(
            channel="ghost",
            content_hash="abc123",
            platform_post_id="ghost-post-xyz",
            publication_url="https://example.ghost.io/post/",
        )
        events = ops_logger.read_events(event_filter="publish_success")
        assert len(events) == 1
        ev = events[0]
        assert ev["event"] == "publish_success"
        assert ev["platform_post_id"] == "ghost-post-xyz"
        assert ev["publication_url"] == "https://example.ghost.io/post/"

    def test_publish_failed_writes_error_fields(self, ops_logger):
        ops_logger.publish_failed(
            channel="linkedin",
            content_hash="def456",
            error_kind="auth_expired",
            error_code="401",
            retryable=False,
        )
        events = ops_logger.read_events(event_filter="publish_failed")
        assert len(events) == 1
        ev = events[0]
        assert ev["event"] == "publish_failed"
        assert ev["error_kind"] == "auth_expired"
        assert ev["error_code"] == "401"
        assert ev["retryable"] is False

    def test_strips_sensitive_extra_fields(self, ops_logger):
        ops_logger.publish_attempt(
            channel="ghost",
            token="SHOULD_NOT_APPEAR",
            secret="ALSO_HIDDEN",
            api_key="NOPE",
        )
        events = ops_logger.read_events(event_filter="publish_attempt")
        assert len(events) == 1
        ev = events[0]
        assert "token" not in ev
        assert "secret" not in ev
        assert "api_key" not in ev

    def test_strips_sensitive_from_metadata(self, ops_logger):
        ops_logger.publish_attempt(
            channel="ghost",
            metadata={"version": "1.0", "password": "hidden"},
        )
        events = ops_logger.read_events(event_filter="publish_attempt")
        ev = events[0]
        assert "password" not in ev.get("metadata", {})
        assert ev["metadata"]["version"] == "1.0"

    def test_compatible_with_existing_events(self, ops_logger):
        ops_logger.task_completed("t1", "ping", "system", "none", 10.0)
        ops_logger.publish_attempt(channel="ghost", content_hash="abc")
        ops_logger.publish_success(channel="ghost", content_hash="abc")
        all_events = ops_logger.read_events()
        assert len(all_events) == 3
        publish_events = [e for e in all_events if e["event"].startswith("publish_")]
        assert len(publish_events) == 2

    def test_idempotency_key_present(self, ops_logger):
        ops_logger.publish_attempt(
            channel="ghost",
            content_hash="hash1",
            notion_page_id="page-1",
        )
        events = ops_logger.read_events(event_filter="publish_attempt")
        assert "idempotency_key" in events[0]
        assert len(events[0]["idempotency_key"]) > 0


# ---------------------------------------------------------------------------
# Demo script tests
# ---------------------------------------------------------------------------


class TestPublishTrackingDemoScript:
    def test_dry_run_succeeds(self):
        from scripts.publish_tracking_demo import main
        ret = main([])
        assert ret == 0

    def test_json_output(self, capsys):
        from scripts.publish_tracking_demo import main
        ret = main(["--json"])
        assert ret == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) >= 5
        events = {r["event"] for r in data}
        assert "publish_attempt" in events
        assert "publish_success" in events
        assert "publish_failed" in events

    def test_write_mode_creates_events(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMBRAL_OPS_LOG_DIR", str(tmp_path))
        from scripts.publish_tracking_demo import main
        ret = main(["--write-ops-log"])
        assert ret == 0
        ops = OpsLogger(log_dir=tmp_path)
        all_events = ops.read_events()
        publish_events = [e for e in all_events if e["event"].startswith("publish_")]
        assert len(publish_events) >= 5
