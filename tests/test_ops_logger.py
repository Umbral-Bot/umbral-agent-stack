"""
Tests for OpsLogger audit improvements (R13).

Covers:
  - trace_id inclusion in events when provided
  - input_summary inclusion and truncation
  - ops_log_rotate.py retention logic
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from infra.ops_logger import OpsLogger
from scripts.ops_log_rotate import rotate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ops_logger(tmp_path):
    return OpsLogger(log_dir=tmp_path)


@pytest.fixture
def log_path(ops_logger):
    return ops_logger.path


# ---------------------------------------------------------------------------
# trace_id tests
# ---------------------------------------------------------------------------


class TestTraceId:
    def test_task_completed_includes_trace_id_when_provided(self, ops_logger, log_path):
        tid = str(uuid.uuid4())
        ops_logger.task_completed("t1", "llm.generate", "eng", "gpt-4o", 120.0, trace_id=tid)
        events = ops_logger.read_events(event_filter="task_completed")
        assert len(events) == 1
        assert events[0]["trace_id"] == tid

    def test_task_completed_omits_trace_id_when_not_provided(self, ops_logger):
        ops_logger.task_completed("t1", "llm.generate", "eng", "gpt-4o", 120.0)
        events = ops_logger.read_events(event_filter="task_completed")
        assert "trace_id" not in events[0]

    def test_task_failed_includes_trace_id_when_provided(self, ops_logger):
        tid = str(uuid.uuid4())
        ops_logger.task_failed("t1", "llm.generate", "eng", "timeout", trace_id=tid)
        events = ops_logger.read_events(event_filter="task_failed")
        assert len(events) == 1
        assert events[0]["trace_id"] == tid

    def test_task_failed_omits_trace_id_when_not_provided(self, ops_logger):
        ops_logger.task_failed("t1", "llm.generate", "eng", "timeout")
        events = ops_logger.read_events(event_filter="task_failed")
        assert "trace_id" not in events[0]

    def test_task_queued_includes_trace_id(self, ops_logger):
        tid = str(uuid.uuid4())
        ops_logger.task_queued("t1", "ping", "system", trace_id=tid)
        events = ops_logger.read_events(event_filter="task_queued")
        assert events[0]["trace_id"] == tid

    def test_task_blocked_includes_trace_id(self, ops_logger):
        tid = str(uuid.uuid4())
        ops_logger.task_blocked("t1", "llm.generate", "eng", "quota", trace_id=tid)
        events = ops_logger.read_events(event_filter="task_blocked")
        assert events[0]["trace_id"] == tid

    def test_task_retried_includes_trace_id(self, ops_logger):
        tid = str(uuid.uuid4())
        ops_logger.task_retried("t1", "llm.generate", "eng", 1, trace_id=tid)
        events = ops_logger.read_events(event_filter="task_retried")
        assert events[0]["trace_id"] == tid

    def test_model_selected_includes_trace_id(self, ops_logger):
        tid = str(uuid.uuid4())
        ops_logger.model_selected("t1", "coding", "gpt-4o", trace_id=tid)
        events = ops_logger.read_events(event_filter="model_selected")
        assert events[0]["trace_id"] == tid


class TestTraceabilityContext:
    def test_task_completed_includes_source_source_kind_and_task_type(self, ops_logger):
        ops_logger.task_completed(
            "t1",
            "llm.generate",
            "eng",
            "gpt-4o",
            120.0,
            trace_id="trace-123",
            task_type="coding",
            source="openclaw_gateway",
            source_kind="tool_enqueue",
        )
        events = ops_logger.read_events(event_filter="task_completed")
        assert events[0]["task_type"] == "coding"
        assert events[0]["source"] == "openclaw_gateway"
        assert events[0]["source_kind"] == "tool_enqueue"

    def test_task_blocked_includes_source_context(self, ops_logger):
        ops_logger.task_blocked(
            "t1",
            "llm.generate",
            "eng",
            "quota",
            task_type="research",
            source="scheduler",
            source_kind="cron",
        )
        events = ops_logger.read_events(event_filter="task_blocked")
        assert events[0]["task_type"] == "research"
        assert events[0]["source"] == "scheduler"
        assert events[0]["source_kind"] == "cron"


# ---------------------------------------------------------------------------
# input_summary tests
# ---------------------------------------------------------------------------


class TestInputSummary:
    def test_task_completed_includes_input_summary_when_provided(self, ops_logger):
        summary = "{'topic': 'test', 'prompt': 'Hello world'}"
        ops_logger.task_completed(
            "t1", "llm.generate", "eng", "gpt-4o", 100.0,
            input_summary=summary,
        )
        events = ops_logger.read_events(event_filter="task_completed")
        assert events[0]["input_summary"] == summary

    def test_task_completed_omits_input_summary_when_not_provided(self, ops_logger):
        ops_logger.task_completed("t1", "llm.generate", "eng", "gpt-4o", 100.0)
        events = ops_logger.read_events(event_filter="task_completed")
        assert "input_summary" not in events[0]

    def test_task_failed_includes_input_summary_when_provided(self, ops_logger):
        summary = "{'key': 'value'}"
        ops_logger.task_failed(
            "t1", "llm.generate", "eng", "error",
            input_summary=summary,
        )
        events = ops_logger.read_events(event_filter="task_failed")
        assert events[0]["input_summary"] == summary

    def test_input_summary_truncated_to_200_chars(self, ops_logger):
        long_summary = "x" * 500
        ops_logger.task_completed(
            "t1", "llm.generate", "eng", "gpt-4o", 100.0,
            input_summary=long_summary,
        )
        events = ops_logger.read_events(event_filter="task_completed")
        assert len(events[0]["input_summary"]) == 200

    def test_task_failed_input_summary_truncated(self, ops_logger):
        long_summary = "y" * 300
        ops_logger.task_failed(
            "t1", "llm.generate", "eng", "error",
            input_summary=long_summary,
        )
        events = ops_logger.read_events(event_filter="task_failed")
        assert len(events[0]["input_summary"]) == 200

    def test_combined_trace_id_and_input_summary(self, ops_logger):
        tid = str(uuid.uuid4())
        ops_logger.task_completed(
            "t1", "llm.generate", "eng", "gpt-4o", 100.0,
            trace_id=tid,
            input_summary="some input",
        )
        events = ops_logger.read_events(event_filter="task_completed")
        assert events[0]["trace_id"] == tid
        assert events[0]["input_summary"] == "some input"


# ---------------------------------------------------------------------------
# ops_log_rotate tests
# ---------------------------------------------------------------------------


def _write_event(path, ts: datetime, event: str = "task_completed", extra: dict | None = None):
    ev = {"event": event, "task_id": "t1", "ts": ts.isoformat()}
    if extra:
        ev.update(extra)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev) + "\n")


class TestOpsLogRotate:
    def test_keeps_recent_events(self, tmp_path):
        log = tmp_path / "ops_log.jsonl"
        now = datetime.now(timezone.utc)
        _write_event(log, now - timedelta(days=10))
        _write_event(log, now - timedelta(days=5))
        _write_event(log, now - timedelta(days=1))
        stats = rotate(log, retention_days=90)
        assert stats["total"] == 3
        assert stats["kept"] == 3
        assert stats["removed"] == 0

    def test_removes_old_events(self, tmp_path):
        log = tmp_path / "ops_log.jsonl"
        now = datetime.now(timezone.utc)
        _write_event(log, now - timedelta(days=100))
        _write_event(log, now - timedelta(days=95))
        _write_event(log, now - timedelta(days=5))
        stats = rotate(log, retention_days=90)
        assert stats["total"] == 3
        assert stats["kept"] == 1
        assert stats["removed"] == 2

    def test_respects_retention_days(self, tmp_path):
        log = tmp_path / "ops_log.jsonl"
        now = datetime.now(timezone.utc)
        _write_event(log, now - timedelta(days=40))
        _write_event(log, now - timedelta(days=20))
        _write_event(log, now - timedelta(days=5))

        stats = rotate(log, retention_days=30)
        assert stats["kept"] == 2
        assert stats["removed"] == 1

    def test_empty_file(self, tmp_path):
        log = tmp_path / "ops_log.jsonl"
        log.touch()
        stats = rotate(log, retention_days=90)
        assert stats == {"total": 0, "kept": 0, "removed": 0}

    def test_missing_file(self, tmp_path):
        log = tmp_path / "ops_log.jsonl"
        stats = rotate(log, retention_days=90)
        assert stats == {"total": 0, "kept": 0, "removed": 0}

    def test_events_without_ts_are_kept(self, tmp_path):
        log = tmp_path / "ops_log.jsonl"
        with open(log, "w", encoding="utf-8") as f:
            f.write(json.dumps({"event": "legacy", "task_id": "old"}) + "\n")
        stats = rotate(log, retention_days=90)
        assert stats["kept"] == 1

    def test_file_rewritten_correctly(self, tmp_path):
        log = tmp_path / "ops_log.jsonl"
        now = datetime.now(timezone.utc)
        _write_event(log, now - timedelta(days=100), event="old_event")
        _write_event(log, now - timedelta(days=1), event="new_event")
        rotate(log, retention_days=90)

        with open(log, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["event"] == "new_event"
