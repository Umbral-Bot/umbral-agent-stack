"""
Tests for the Dispatcher module.

Uses fakeredis for Redis mocking — no real Redis required.

Run with:
    python -m pytest tests/test_dispatcher.py -v
"""

import json
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

# Must install fakeredis for these tests
try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False


# Skip all tests if fakeredis not available
pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")


from dispatcher.queue import TaskQueue
from dispatcher.health import HealthMonitor, SystemLevel
from dispatcher.router import TeamRouter, TEAM_CAPABILITIES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def redis_client():
    """Fake Redis client."""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def queue(redis_client):
    return TaskQueue(redis_client)


@pytest.fixture
def sample_envelope():
    return {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "marketing",
        "task_type": "writing",
        "task": "generate_post",
        "input": {"topic": "AI news"},
        "trace_id": str(uuid.uuid4()),
        "status": "queued",
    }


# ---------------------------------------------------------------------------
# TaskQueue tests
# ---------------------------------------------------------------------------


class TestTaskQueue:
    def test_enqueue_stores_task(self, queue, sample_envelope):
        task_id = queue.enqueue(sample_envelope)
        assert task_id == sample_envelope["task_id"]

        stored = queue.get_task(task_id)
        assert stored is not None
        assert stored["task_id"] == task_id
        assert stored["status"] == "queued"

    def test_enqueue_increments_pending(self, queue, sample_envelope):
        assert queue.pending_count() == 0
        queue.enqueue(sample_envelope)
        assert queue.pending_count() == 1

    def test_dequeue_returns_task(self, queue, sample_envelope):
        queue.enqueue(sample_envelope)
        result = queue.dequeue(timeout=1)
        assert result is not None
        assert result["task_id"] == sample_envelope["task_id"]
        assert result["status"] == "running"

    def test_dequeue_empty_returns_none(self, queue):
        result = queue.dequeue(timeout=1)
        assert result is None

    def test_complete_task(self, queue, sample_envelope):
        queue.enqueue(sample_envelope)
        task_id = sample_envelope["task_id"]
        queue.complete_task(task_id, {"output": "done"})

        stored = queue.get_task(task_id)
        assert stored["status"] == "done"
        assert stored["result"]["output"] == "done"

    def test_fail_task(self, queue, sample_envelope):
        queue.enqueue(sample_envelope)
        task_id = sample_envelope["task_id"]
        queue.fail_task(task_id, "timeout")

        stored = queue.get_task(task_id)
        assert stored["status"] == "failed"
        assert stored["error"] == "timeout"

    def test_block_task(self, queue, sample_envelope):
        queue.enqueue(sample_envelope)
        task_id = sample_envelope["task_id"]
        queue.block_task(task_id, "VM offline")

        stored = queue.get_task(task_id)
        assert stored["status"] == "blocked"
        assert stored["block_reason"] == "VM offline"
        assert queue.blocked_count() == 1

    def test_unblock_all(self, queue, sample_envelope):
        queue.enqueue(sample_envelope)
        task_id = sample_envelope["task_id"]
        queue.block_task(task_id, "VM offline")

        unblocked = queue.unblock_all()
        assert task_id in unblocked
        assert queue.blocked_count() == 0
        assert queue.pending_count() == 1

    def test_queue_stats(self, queue, sample_envelope):
        stats = queue.queue_stats()
        assert stats["pending"] == 0
        assert stats["blocked"] == 0

        queue.enqueue(sample_envelope)
        stats = queue.queue_stats()
        assert stats["pending"] == 1

    def test_enqueue_pending_meta_keeps_traceability_context(self, queue, sample_envelope, redis_client):
        sample_envelope["source"] = "openclaw_gateway"
        sample_envelope["source_kind"] = "tool_enqueue"
        sample_envelope["callback_url"] = "https://callback.example/hook"
        sample_envelope["notion_track"] = True
        sample_envelope["project_name"] = "Proyecto Embudo Ventas"
        sample_envelope["deliverable_name"] = "Benchmark Ruben Hassid - sistema contenido y funnel"

        queue.enqueue(sample_envelope)
        raw_meta = redis_client.lindex(TaskQueue.QUEUE_PENDING, 0)
        meta = json.loads(raw_meta)

        assert meta["trace_id"] == sample_envelope["trace_id"]
        assert meta["source"] == "openclaw_gateway"
        assert meta["source_kind"] == "tool_enqueue"
        assert meta["callback_url"] == "https://callback.example/hook"
        assert meta["notion_track"] is True
        assert meta["project_name"] == "Proyecto Embudo Ventas"
        assert meta["deliverable_name"] == "Benchmark Ruben Hassid - sistema contenido y funnel"

    def test_get_nonexistent_task(self, queue):
        result = queue.get_task("does-not-exist")
        assert result is None


# ---------------------------------------------------------------------------
# HealthMonitor tests
# ---------------------------------------------------------------------------


class TestHealthMonitor:
    def test_initial_state(self):
        hm = HealthMonitor(
            worker_url="http://localhost:8088",
            worker_token="test",
        )
        assert hm.level == SystemLevel.NORMAL
        assert hm.vm_online is False

    @patch("dispatcher.health.httpx.get")
    def test_successful_check(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "version": "0.3.0"}
        mock_get.return_value = mock_resp

        hm = HealthMonitor(
            worker_url="http://localhost:8088",
            worker_token="test",
        )
        result = hm.check_once()
        assert result is True
        assert hm.vm_online is True
        assert hm.level == SystemLevel.NORMAL

    @patch("dispatcher.health.httpx.get")
    def test_failure_threshold(self, mock_get):
        mock_get.side_effect = Exception("connection refused")

        hm = HealthMonitor(
            worker_url="http://localhost:8088",
            worker_token="test",
            failure_threshold=3,
        )

        # 1st and 2nd failure — still online
        hm.check_once()
        assert hm.vm_online is False
        hm.check_once()
        assert hm.vm_online is False

        # 3rd failure — now offline
        hm.check_once()
        assert hm.vm_online is False
        assert hm.level == SystemLevel.PARTIAL

    @patch("dispatcher.health.httpx.get")
    def test_recovery(self, mock_get):
        # First fail 3 times
        mock_get.side_effect = Exception("timeout")
        hm = HealthMonitor(
            worker_url="http://localhost:8088",
            worker_token="test",
            failure_threshold=3,
        )
        for _ in range(3):
            hm.check_once()
        assert hm.vm_online is False

        # Then succeed
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "version": "0.3.0"}
        mock_get.side_effect = None
        mock_get.return_value = mock_resp

        hm.check_once()
        assert hm.vm_online is True
        assert hm.level == SystemLevel.NORMAL

    @patch("dispatcher.health.httpx.get")
    def test_on_vm_back_callback(self, mock_get):
        callback = MagicMock()
        mock_get.side_effect = Exception("timeout")
        hm = HealthMonitor(
            worker_url="http://localhost:8088",
            worker_token="test",
            failure_threshold=1,
            on_vm_back=callback,
        )
        hm.check_once()  # VM goes offline

        # Recover
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_get.side_effect = None
        mock_get.return_value = mock_resp
        hm.check_once()

        callback.assert_called_once()

    def test_status_dict(self):
        hm = HealthMonitor(
            worker_url="http://localhost:8088",
            worker_token="test",
        )
        status = hm.status
        assert "level" in status
        assert "vm_online" in status
        assert status["level"] == "normal"


# ---------------------------------------------------------------------------
# TeamRouter tests
# ---------------------------------------------------------------------------


class TestTeamRouter:
    def test_dispatch_normal(self, redis_client, sample_envelope):
        queue = TaskQueue(redis_client)
        health = MagicMock()
        health.vm_online = True
        health.level = SystemLevel.NORMAL

        router = TeamRouter(queue=queue, health=health)
        result = router.dispatch(sample_envelope)

        assert result["action"] == "enqueued"
        assert result["team"] == "marketing"
        assert queue.pending_count() == 1

    def test_dispatch_blocks_when_vm_offline(self, redis_client):
        queue = TaskQueue(redis_client)
        health = MagicMock()
        health.vm_online = False
        health.level = SystemLevel.PARTIAL

        router = TeamRouter(queue=queue, health=health)

        # improvement team requires VM
        envelope = {
            "task_id": str(uuid.uuid4()),
            "team": "improvement",
            "task_type": "research",
            "task": "sota_scan",
            "input": {},
        }
        result = router.dispatch(envelope)

        assert result["action"] == "blocked"
        assert queue.blocked_count() == 1

    def test_dispatch_allows_llm_only_when_vm_offline(self, redis_client):
        queue = TaskQueue(redis_client)
        health = MagicMock()
        health.vm_online = False
        health.level = SystemLevel.PARTIAL

        router = TeamRouter(queue=queue, health=health)

        # marketing team does NOT require VM
        envelope = {
            "task_id": str(uuid.uuid4()),
            "team": "marketing",
            "task_type": "writing",
            "task": "write_post",
            "input": {},
        }
        result = router.dispatch(envelope)

        assert result["action"] == "enqueued"
        assert queue.pending_count() == 1


    def test_dispatch_allows_improvement_research_locally_when_vm_offline(self, redis_client):
        queue = TaskQueue(redis_client)
        health = MagicMock()
        health.vm_online = False
        health.level = SystemLevel.PARTIAL

        router = TeamRouter(queue=queue, health=health)

        envelope = {
            "task_id": str(uuid.uuid4()),
            "team": "improvement",
            "task_type": "research",
            "task": "research.web",
            "input": {"query": "test"},
        }
        result = router.dispatch(envelope)

        assert result["action"] == "enqueued"
        assert queue.pending_count() == 1
    def test_dispatch_unknown_team(self, redis_client, sample_envelope):
        queue = TaskQueue(redis_client)
        health = MagicMock()
        health.vm_online = True
        health.level = SystemLevel.NORMAL

        router = TeamRouter(queue=queue, health=health)
        sample_envelope["team"] = "nonexistent"
        result = router.dispatch(sample_envelope)

        assert result["action"] == "rejected"

    def test_on_vm_back_unblocks(self, redis_client):
        queue = TaskQueue(redis_client)
        health = MagicMock()
        health.vm_online = True
        health.level = SystemLevel.NORMAL

        router = TeamRouter(queue=queue, health=health)

        # Block a task
        task_id = str(uuid.uuid4())
        envelope = {
            "task_id": task_id,
            "team": "improvement",
            "task": "eval",
            "input": {},
        }
        queue.enqueue(envelope)
        queue.block_task(task_id, "VM offline")

        # VM comes back
        result = router.on_vm_back()
        assert task_id in result["unblocked"]
        assert queue.pending_count() == 1
        assert queue.blocked_count() == 0

    def test_list_teams(self, redis_client):
        queue = TaskQueue(redis_client)
        health = MagicMock()
        health.vm_online = True

        router = TeamRouter(queue=queue, health=health)
        teams = router.list_teams()
        assert "marketing" in teams
        assert "improvement" in teams
        assert teams["marketing"]["available"] is True

    def test_list_teams_vm_offline(self, redis_client):
        queue = TaskQueue(redis_client)
        health = MagicMock()
        health.vm_online = False

        router = TeamRouter(queue=queue, health=health)
        teams = router.list_teams()
        assert teams["marketing"]["available"] is True
        assert teams["improvement"]["available"] is False


