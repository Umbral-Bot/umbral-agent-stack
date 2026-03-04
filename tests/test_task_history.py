"""
Tests for dispatcher.task_history and GET /task/history endpoint.

Run with:
    WORKER_TOKEN=test python -m pytest tests/test_task_history.py -v
"""

import json
import os
import time
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

try:
    import fakeredis

    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")

os.environ["WORKER_TOKEN"] = "test-token-12345"

from dispatcher.queue import TaskQueue  # noqa: E402
from dispatcher.task_history import TaskHistory  # noqa: E402
from worker.app import app  # noqa: E402

AUTH = {"Authorization": "Bearer test-token-12345"}
TASK_KEY_PREFIX = TaskQueue.TASK_KEY_PREFIX


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def client():
    return TestClient(app)


def _store_task(redis_client, **kwargs):
    task_id = kwargs.get("task_id", str(uuid.uuid4()))
    envelope = {
        "task_id": task_id,
        "task": kwargs.get("task", "ping"),
        "team": kwargs.get("team", "system"),
        "task_type": kwargs.get("task_type", "general"),
        "status": kwargs.get("status", "done"),
        "queued_at": kwargs.get("queued_at", time.time()),
    }
    for key in ("started_at", "completed_at", "failed_at", "created_at", "input", "error", "result"):
        if key in kwargs:
            envelope[key] = kwargs[key]

    redis_client.set(f"{TASK_KEY_PREFIX}{task_id}", json.dumps(envelope))
    return envelope


def test_query_without_filters_returns_all(fake_redis):
    now = 1_741_086_000.0
    _store_task(fake_redis, team="system", status="done", queued_at=now - 100)
    _store_task(fake_redis, team="marketing", status="failed", queued_at=now - 200)

    with patch("dispatcher.task_history.time.time", return_value=now):
        history = TaskHistory(fake_redis)
        result = history.query(hours=24, limit=100, offset=0)

    assert result["total"] == 2
    assert len(result["tasks"]) == 2


def test_query_filter_by_team(fake_redis):
    now = 1_741_086_000.0
    _store_task(fake_redis, team="marketing", status="done", queued_at=now - 100)
    _store_task(fake_redis, team="system", status="done", queued_at=now - 200)

    with patch("dispatcher.task_history.time.time", return_value=now):
        result = TaskHistory(fake_redis).query(hours=24, team="marketing", limit=100, offset=0)

    assert result["total"] == 1
    assert result["tasks"][0]["team"] == "marketing"


def test_query_filter_by_status(fake_redis):
    now = 1_741_086_000.0
    _store_task(fake_redis, status="done", queued_at=now - 100)
    _store_task(fake_redis, status="failed", queued_at=now - 100)

    with patch("dispatcher.task_history.time.time", return_value=now):
        result = TaskHistory(fake_redis).query(hours=24, status="failed", limit=100, offset=0)

    assert result["total"] == 1
    assert result["tasks"][0]["status"] == "failed"


def test_query_hours_excludes_old_tasks(fake_redis):
    now = 1_741_086_000.0
    _store_task(fake_redis, status="done", queued_at=now - 3600)  # 1h
    _store_task(fake_redis, status="done", queued_at=now - (30 * 3600))  # 30h

    with patch("dispatcher.task_history.time.time", return_value=now):
        result = TaskHistory(fake_redis).query(hours=24, limit=100, offset=0)

    assert result["total"] == 1


def test_query_pagination_limit_offset(fake_redis):
    now = 1_741_086_000.0
    _store_task(fake_redis, queued_at=now - 10)
    _store_task(fake_redis, queued_at=now - 20)
    _store_task(fake_redis, queued_at=now - 30)

    with patch("dispatcher.task_history.time.time", return_value=now):
        result = TaskHistory(fake_redis).query(hours=24, limit=2, offset=1)

    assert result["total"] == 3
    assert len(result["tasks"]) == 2
    assert result["page"]["has_more"] is False
    assert result["page"]["offset"] == 1
    assert result["page"]["limit"] == 2


def test_stats_aggregates_correctly(fake_redis):
    now = 1_741_086_000.0
    _store_task(fake_redis, team="marketing", status="done", queued_at=now - 10)
    _store_task(fake_redis, team="marketing", status="failed", queued_at=now - 20)
    _store_task(fake_redis, team="system", status="queued", queued_at=now - 30)

    with patch("dispatcher.task_history.time.time", return_value=now):
        stats = TaskHistory(fake_redis).stats(hours=24)

    assert stats["done"] == 1
    assert stats["failed"] == 1
    assert stats["queued"] == 1
    assert stats["teams"]["marketing"] == 2
    assert stats["teams"]["system"] == 1


def test_empty_redis_returns_empty_without_error(fake_redis):
    now = 1_741_086_000.0
    with patch("dispatcher.task_history.time.time", return_value=now):
        history = TaskHistory(fake_redis)
        query = history.query(hours=24, limit=100, offset=0)
        stats = history.stats(hours=24)

    assert query["tasks"] == []
    assert query["total"] == 0
    assert stats["done"] == 0
    assert stats["failed"] == 0
    assert stats["teams"] == {}


def test_worker_task_history_endpoint(fake_redis, client):
    now = 1_741_086_000.0
    _store_task(fake_redis, team="marketing", status="done", queued_at=now - 10)
    _store_task(fake_redis, team="system", status="failed", queued_at=now - 20)

    with (
        patch("worker.app._get_redis", return_value=fake_redis),
        patch("dispatcher.task_history.time.time", return_value=now),
    ):
        resp = client.get("/task/history?hours=24&limit=1&offset=0", headers=AUTH)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["tasks"]) == 1
    assert data["page"]["has_more"] is True
    assert "stats" in data
