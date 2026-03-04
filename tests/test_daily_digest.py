"""
Tests for scripts/daily_digest.py

Uses fakeredis to mock Redis. Run:
    WORKER_TOKEN=test python -m pytest tests/test_daily_digest.py -v
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

# Ensure repo root is in path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")
os.environ.setdefault("WORKER_URL", "http://localhost:8088")

from scripts.daily_digest import (  # noqa: E402
    TASK_KEY_PREFIX,
    build_digest,
    build_plain_report,
    compute_metrics,
    count_pending,
    fetch_task_history,
    generate_llm_summary,
    scan_recent_tasks,
)


# ======================================================================
# Helpers
# ======================================================================

NOW = datetime(2026, 3, 4, 22, 0, 0, tzinfo=timezone.utc)
NOW_TS = NOW.timestamp()


def _make_task(
    task: str = "ping",
    team: str = "system",
    task_type: str = "general",
    status: str = "done",
    hours_ago: float = 2.0,
    input_data: dict | None = None,
    result: dict | None = None,
    error: str | None = None,
) -> dict:
    """Build a task envelope dict."""
    task_id = str(uuid.uuid4())
    completed_ts = NOW_TS - (hours_ago * 3600)
    envelope = {
        "task_id": task_id,
        "task": task,
        "team": team,
        "task_type": task_type,
        "status": status,
        "queued_at": completed_ts - 10,
        "started_at": completed_ts - 5,
        "input": input_data or {},
    }
    if status == "done":
        envelope["completed_at"] = completed_ts
        envelope["result"] = result or {"ok": True}
    elif status == "failed":
        envelope["failed_at"] = completed_ts
        envelope["error"] = error or "test error"
    return envelope


def _populate_redis(redis_client, tasks: list[dict]) -> None:
    """Store task envelopes in fakeredis."""
    for t in tasks:
        key = f"{TASK_KEY_PREFIX}{t['task_id']}"
        redis_client.set(key, json.dumps(t))


@pytest.fixture
def fake_redis():
    if not HAS_FAKEREDIS:
        pytest.skip("fakeredis not installed")
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def sample_tasks() -> list[dict]:
    """A mix of tasks from last 24h."""
    return [
        _make_task(task="ping", team="system", hours_ago=1),
        _make_task(task="research.web", team="marketing", task_type="research",
                   hours_ago=3, input_data={"query": "AI trends 2026"},
                   result={"results": [{"url": "https://example.com"}]}),
        _make_task(task="research.web", team="marketing", task_type="research",
                   hours_ago=5, input_data={"query": "SaaS pricing models"},
                   result={"results": []}),
        _make_task(task="llm.generate", team="lab", task_type="coding",
                   hours_ago=2, result={"text": "Generated code sample"}),
        _make_task(task="notion.add_comment", team="system", hours_ago=4),
        _make_task(task="research.web", team="advisory", task_type="research",
                   status="failed", hours_ago=6, error="Tavily timeout"),
    ]


# ======================================================================
# scan_recent_tasks
# ======================================================================


class TestScanRecentTasks:
    def test_returns_empty_when_redis_is_none(self):
        result = scan_recent_tasks(None, hours=24, now=NOW)
        assert result == []

    def test_returns_empty_when_no_tasks(self, fake_redis):
        result = scan_recent_tasks(fake_redis, hours=24, now=NOW)
        assert result == []

    def test_finds_tasks_within_window(self, fake_redis, sample_tasks):
        _populate_redis(fake_redis, sample_tasks)
        result = scan_recent_tasks(fake_redis, hours=24, now=NOW)
        assert len(result) == 6

    def test_excludes_old_tasks(self, fake_redis):
        old_task = _make_task(task="ping", hours_ago=30)  # 30h ago — outside 24h window
        _populate_redis(fake_redis, [old_task])
        result = scan_recent_tasks(fake_redis, hours=24, now=NOW)
        assert len(result) == 0

    def test_excludes_queued_tasks(self, fake_redis):
        queued = _make_task(task="ping", hours_ago=1)
        queued["status"] = "queued"
        queued.pop("completed_at", None)
        _populate_redis(fake_redis, [queued])
        result = scan_recent_tasks(fake_redis, hours=24, now=NOW)
        assert len(result) == 0

    def test_includes_failed_tasks(self, fake_redis):
        failed = _make_task(task="llm.generate", status="failed", hours_ago=2, error="timeout")
        _populate_redis(fake_redis, [failed])
        result = scan_recent_tasks(fake_redis, hours=24, now=NOW)
        assert len(result) == 1
        assert result[0]["status"] == "failed"

    def test_sorted_by_time(self, fake_redis, sample_tasks):
        _populate_redis(fake_redis, sample_tasks)
        result = scan_recent_tasks(fake_redis, hours=24, now=NOW)
        timestamps = [
            t.get("completed_at") or t.get("failed_at") or 0
            for t in result
        ]
        assert timestamps == sorted(timestamps)


# ======================================================================
# compute_metrics
# ======================================================================


class TestComputeMetrics:
    def test_empty_tasks(self):
        m = compute_metrics([])
        assert m["total"] == 0
        assert m["done"] == 0
        assert m["failed"] == 0
        assert m["avg_duration_s"] == 0.0

    def test_counts_done_and_failed(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        assert m["total"] == 6
        assert m["done"] == 5
        assert m["failed"] == 1

    def test_groups_by_team(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        assert "system" in m["by_team"]
        assert "marketing" in m["by_team"]
        assert m["by_team"]["marketing"] == 2

    def test_groups_by_task_name(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        assert "research.web" in m["by_task"]
        assert m["by_task"]["research.web"]["done"] == 2
        assert m["by_task"]["research.web"]["failed"] == 1

    def test_extracts_research_topics(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        assert "AI trends 2026" in m["research_topics"]
        assert "SaaS pricing models" in m["research_topics"]

    def test_captures_errors(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        assert len(m["errors"]) == 1
        assert "Tavily timeout" in m["errors"][0]

    def test_avg_duration(self):
        t1 = _make_task(hours_ago=1)
        t1["started_at"] = t1["completed_at"] - 10.0  # 10 seconds
        t2 = _make_task(hours_ago=2)
        t2["started_at"] = t2["completed_at"] - 20.0  # 20 seconds
        m = compute_metrics([t1, t2])
        assert m["avg_duration_s"] == 15.0  # avg of 10 and 20


# ======================================================================
# build_plain_report
# ======================================================================


class TestBuildPlainReport:
    def test_contains_date(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        report = build_plain_report(m, pending=0, now=NOW, hours=24)
        assert "2026-03-04" in report

    def test_contains_activity_counts(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        report = build_plain_report(m, pending=0, now=NOW, hours=24)
        assert "6 tareas ejecutadas" in report
        assert "5 exitosas" in report
        assert "1 fallidas" in report

    def test_shows_pending(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        report = build_plain_report(m, pending=3, now=NOW, hours=24)
        assert "3 tareas en cola" in report

    def test_shows_research_topics(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        report = build_plain_report(m, pending=0, now=NOW, hours=24)
        assert "AI trends 2026" in report

    def test_shows_errors(self, sample_tasks):
        m = compute_metrics(sample_tasks)
        report = build_plain_report(m, pending=0, now=NOW, hours=24)
        assert "Alertas:" in report
        assert "Tavily timeout" in report

    def test_empty_tasks_report(self):
        m = compute_metrics([])
        report = build_plain_report(m, pending=0, now=NOW, hours=24)
        assert "0 tareas ejecutadas" in report
        assert "Alertas:" not in report


# ======================================================================
# count_pending
# ======================================================================


class TestCountPending:
    def test_returns_zero_for_none(self):
        assert count_pending(None) == 0

    def test_returns_pending_count(self, fake_redis):
        fake_redis.lpush("umbral:tasks:pending", "task1", "task2")
        assert count_pending(fake_redis) == 2


# ======================================================================
# generate_llm_summary
# ======================================================================


class TestGenerateLlmSummary:
    def test_returns_text_on_success(self):
        mock_wc = MagicMock()
        mock_wc.run.return_value = {"result": {"text": "Resumen ejecutivo de prueba"}}
        result = generate_llm_summary("plain report text", mock_wc)
        assert result == "Resumen ejecutivo de prueba"
        mock_wc.run.assert_called_once()

    def test_returns_none_on_empty_response(self):
        mock_wc = MagicMock()
        mock_wc.run.return_value = {"result": {"text": ""}}
        result = generate_llm_summary("plain report", mock_wc)
        assert result is None

    def test_returns_none_on_exception(self):
        mock_wc = MagicMock()
        mock_wc.run.side_effect = Exception("Connection refused")
        result = generate_llm_summary("plain report", mock_wc)
        assert result is None

    def test_calls_llm_generate(self):
        mock_wc = MagicMock()
        mock_wc.run.return_value = {"result": {"text": "summary"}}
        generate_llm_summary("test report", mock_wc)
        args = mock_wc.run.call_args
        assert args[0][0] == "llm.generate"
        assert "prompt" in args[0][1]
        assert "test report" in args[0][1]["prompt"]


# ======================================================================
# fetch_task_history (Worker API)
# ======================================================================


class TestFetchTaskHistory:
    def test_single_page(self):
        mock_wc = MagicMock()
        mock_wc.task_history.return_value = {
            "tasks": [{"task_id": "t1", "status": "done"}],
            "total": 1,
            "page": {"offset": 0, "limit": 200, "has_more": False},
            "stats": {"done": 1, "failed": 0, "queued": 0, "running": 0, "teams": {"system": 1}},
        }

        out = fetch_task_history(mock_wc, hours=24)
        assert out["total"] == 1
        assert len(out["tasks"]) == 1
        assert out["stats"]["done"] == 1
        mock_wc.task_history.assert_called_once()

    def test_paginates_until_has_more_false(self):
        mock_wc = MagicMock()
        mock_wc.task_history.side_effect = [
            {
                "tasks": [{"task_id": "t1"}],
                "total": 3,
                "page": {"offset": 0, "limit": 2, "has_more": True},
                "stats": {"done": 2, "failed": 1, "queued": 0, "running": 0, "teams": {"system": 3}},
            },
            {
                "tasks": [{"task_id": "t2"}, {"task_id": "t3"}],
                "total": 3,
                "page": {"offset": 2, "limit": 2, "has_more": False},
                "stats": {"done": 2, "failed": 1, "queued": 0, "running": 0, "teams": {"system": 3}},
            },
        ]

        out = fetch_task_history(mock_wc, hours=24, page_size=2)
        assert out["total"] == 3
        assert [t["task_id"] for t in out["tasks"]] == ["t1", "t2", "t3"]
        assert mock_wc.task_history.call_count == 2


# ======================================================================
# build_digest (integration)
# ======================================================================


class TestBuildDigest:
    def test_plain_only_when_no_llm(self, sample_tasks):
        digest = build_digest(sample_tasks, pending=0, now=NOW, hours=24, use_llm=False)
        assert "Rick: Resumen diario" in digest
        assert "6 tareas ejecutadas" in digest

    def test_plain_when_no_worker_client(self, sample_tasks):
        digest = build_digest(sample_tasks, pending=0, now=NOW, hours=24,
                              worker_client=None, use_llm=True)
        assert "6 tareas ejecutadas" in digest

    def test_plain_when_no_tasks(self):
        digest = build_digest([], pending=0, now=NOW, hours=24, use_llm=True)
        assert "0 tareas ejecutadas" in digest

    def test_includes_llm_summary_when_available(self, sample_tasks):
        mock_wc = MagicMock()
        mock_wc.run.return_value = {"result": {"text": "IA: Todo bien hoy."}}
        digest = build_digest(sample_tasks, pending=0, now=NOW, hours=24,
                              worker_client=mock_wc, use_llm=True)
        assert "IA: Todo bien hoy." in digest
        assert "Generado con IA" in digest
        # Also contains raw data
        assert "Datos crudos" in digest

    def test_fallback_to_plain_on_llm_failure(self, sample_tasks):
        mock_wc = MagicMock()
        mock_wc.run.side_effect = Exception("LLM down")
        digest = build_digest(sample_tasks, pending=0, now=NOW, hours=24,
                              worker_client=mock_wc, use_llm=True)
        # Should still have the plain report
        assert "6 tareas ejecutadas" in digest
        # Should not have the IA header
        assert "Generado con IA" not in digest


# ======================================================================
# Full pipeline: scan → metrics → digest
# ======================================================================


class TestFullPipeline:
    def test_end_to_end_with_fakeredis(self, fake_redis, sample_tasks):
        _populate_redis(fake_redis, sample_tasks)
        tasks = scan_recent_tasks(fake_redis, hours=24, now=NOW)
        pending = count_pending(fake_redis)
        digest = build_digest(tasks, pending, now=NOW, hours=24, use_llm=False)

        assert "Rick: Resumen diario — 2026-03-04" in digest
        assert "6 tareas ejecutadas" in digest
        assert "AI trends 2026" in digest

    def test_empty_redis(self, fake_redis):
        tasks = scan_recent_tasks(fake_redis, hours=24, now=NOW)
        digest = build_digest(tasks, pending=0, now=NOW, hours=24, use_llm=False)
        assert "0 tareas ejecutadas" in digest
