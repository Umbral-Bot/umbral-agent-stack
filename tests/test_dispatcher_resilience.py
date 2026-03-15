"""
Tests for Dispatcher resilience features (UMB-18).

Verifies:
  1. Fire-and-forget: _notion_upsert / _notify_linear_completion don't block
  2. Retry: httpx timeouts re-enqueue with retry_count
  3. Graceful errors: ConnectError doesn't crash, retries with 30s backoff
  4. OpsLogger.task_retried event

Run with:
    python -m pytest tests/test_dispatcher_resilience.py -v
"""

import inspect
import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest

try:
    import fakeredis

    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")

from dispatcher.queue import TaskQueue
from dispatcher.service import _notion_upsert, _notify_linear_completion, _run_worker
from infra.ops_logger import OpsLogger


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def queue(redis_client):
    return TaskQueue(redis_client)


@pytest.fixture
def mock_wc():
    wc = MagicMock()
    wc.run.return_value = {"ok": True, "result": "done"}
    return wc


@pytest.fixture
def sample_envelope():
    return {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "marketing",
        "task_type": "writing",
        "task": "generate_post",
        "input": {"topic": "test", "project_name": "Proyecto Embudo Ventas"},
        "trace_id": str(uuid.uuid4()),
        "status": "queued",
    }


@pytest.fixture
def ops_logger(tmp_path):
    return OpsLogger(log_dir=tmp_path)


# ---------------------------------------------------------------------------
# Helper: run a single iteration of _run_worker
# ---------------------------------------------------------------------------


def _run_one_iteration(redis_client, envelope, wc_side_effect=None):
    """Enqueue one task, run _run_worker for exactly one iteration, return mocks.

    _run_worker creates its own Redis/Queue/WorkerClient internally, so we
    must patch at the class/module level.
    """
    queue = TaskQueue(redis_client)
    queue.enqueue(envelope)

    # After the first dequeue returns a task, the second must return None
    # so we can break the loop via a controlled exception.
    dequeue_calls = [0]
    original_dequeue = TaskQueue.dequeue

    def patched_dequeue(self, timeout=2):
        dequeue_calls[0] += 1
        if dequeue_calls[0] > 1:
            raise KeyboardInterrupt("stop after 1 iteration")
        return original_dequeue(self, timeout=timeout)

    # Build mocks
    model_decision = MagicMock()
    model_decision.model = "gpt-4o-mini"
    model_decision.requires_approval = False
    model_decision.reason = "default"

    model_router = MagicMock()
    model_router.select_model.return_value = model_decision
    model_router.quota = MagicMock()

    hm = MagicMock()
    hm.vm_online = False

    wc_mock = MagicMock()
    if wc_side_effect:
        wc_mock.run.side_effect = wc_side_effect
    else:
        wc_mock.run.return_value = {"ok": True, "result": "done"}

    with (
        patch("dispatcher.service.redis.Redis", return_value=redis_client),
        patch("dispatcher.service.WorkerClient", return_value=wc_mock),
        patch("dispatcher.service.get_team_capabilities", return_value={"marketing": {"requires_vm": False}}),
        patch.object(TaskQueue, "dequeue", patched_dequeue),
        patch("dispatcher.service.ops_log") as mock_ops,
        patch("dispatcher.service.time") as mock_time,
        patch("dispatcher.service.threading") as mock_threading,
    ):
        # Make mock_time.time() return increasing values
        mock_time.time.side_effect = [1000.0, 1001.0, 1002.0, 1003.0]
        # Make threading.Thread return a mock with .start()
        thread_mock = MagicMock()
        mock_threading.Thread.return_value = thread_mock

        try:
            _run_worker(
                MagicMock(),  # pool (unused since redis.Redis is patched)
                "http://fake:8088",
                "token",
                None,
                hm,
                model_router,
                None,
                1,
            )
        except KeyboardInterrupt:
            pass

    return {
        "ops": mock_ops,
        "wc": wc_mock,
        "queue": queue,
        "time": mock_time,
        "threading": mock_threading,
        "thread": thread_mock,
    }


# ---------------------------------------------------------------------------
# 1. Fire-and-forget tests
# ---------------------------------------------------------------------------


class TestFireAndForget:
    """_notion_upsert and _notify_linear_completion must not block the caller."""

    def test_notion_upsert_success(self, mock_wc):
        _notion_upsert(
            mock_wc,
            "t1",
            "running",
            "marketing",
            "task",
            envelope={"input": {"project_name": "Proyecto Embudo Ventas"}},
        )
        mock_wc.run.assert_called_once()

    def test_notion_upsert_swallows_404(self, mock_wc):
        mock_wc.run.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        _notion_upsert(
            mock_wc,
            "t1",
            "running",
            "marketing",
            "task",
            envelope={"input": {"project_name": "Proyecto Embudo Ventas"}},
        )
        # No exception raised

    def test_notion_upsert_swallows_connect_error(self, mock_wc):
        mock_wc.run.side_effect = httpx.ConnectError("refused")
        _notion_upsert(
            mock_wc,
            "t1",
            "running",
            "marketing",
            "task",
            envelope={"input": {"project_name": "Proyecto Embudo Ventas"}},
        )

    def test_notion_upsert_skips_noise_without_context(self, mock_wc):
        _notion_upsert(mock_wc, "t1", "running", "marketing", "task")
        mock_wc.run.assert_not_called()

    def test_linear_skip_without_issue_id(self, mock_wc):
        _notify_linear_completion(mock_wc, {"task": "t"}, True)
        mock_wc.run.assert_not_called()

    def test_linear_calls_with_issue_id(self, mock_wc):
        _notify_linear_completion(mock_wc, {"task": "t", "linear_issue_id": "L-1"}, True)
        assert mock_wc.run.call_args[0][0] == "linear.update_issue_status"

    def test_linear_swallows_errors(self, mock_wc):
        mock_wc.run.side_effect = Exception("Linear down")
        _notify_linear_completion(mock_wc, {"task": "t", "linear_issue_id": "L-1"}, False, error="x")

    def test_daemon_threads_in_source(self):
        """All threading.Thread calls in _run_worker use daemon=True."""
        source = inspect.getsource(_run_worker)
        assert "daemon=True" in source
        assert "threading.Thread(target=_notion_upsert" in source
        assert "threading.Thread(target=_notify_linear_completion" in source

    def test_notion_upsert_runs_as_thread(self, redis_client, sample_envelope):
        """In _run_worker, _notion_upsert is called via threading.Thread."""
        mocks = _run_one_iteration(redis_client, sample_envelope)
        # threading.Thread should have been called with target=_notion_upsert
        thread_calls = mocks["threading"].Thread.call_args_list
        targets = [c.kwargs.get("target") or (c.args[0] if c.args else None) for c in thread_calls]
        # At least one call should target _notion_upsert
        has_notion = any(
            "target" in c.kwargs and c.kwargs["target"] is _notion_upsert
            for c in thread_calls
        )
        assert has_notion, f"Expected _notion_upsert as thread target, got: {thread_calls}"


# ---------------------------------------------------------------------------
# 2. Retry for timeouts
# ---------------------------------------------------------------------------


class TestRetryOnTimeout:
    """Tasks with httpx.ReadTimeout/WriteTimeout are re-enqueued up to 2 times."""

    def test_read_timeout_retries(self, redis_client, sample_envelope):
        sample_envelope["retry_count"] = 0
        mocks = _run_one_iteration(redis_client, sample_envelope, httpx.ReadTimeout("timeout"))
        mocks["ops"].task_retried.assert_called_once()

    def test_write_timeout_retries(self, redis_client, sample_envelope):
        sample_envelope["retry_count"] = 0
        mocks = _run_one_iteration(redis_client, sample_envelope, httpx.WriteTimeout("timeout"))
        mocks["ops"].task_retried.assert_called_once()

    def test_retry_emits_task_queued_with_envelope_fields(self, redis_client, sample_envelope):
        sample_envelope["retry_count"] = 0
        mocks = _run_one_iteration(redis_client, sample_envelope, httpx.ReadTimeout("timeout"))
        mocks["ops"].task_queued.assert_called_once_with(
            sample_envelope["task_id"],
            sample_envelope["task"],
            sample_envelope["team"],
            sample_envelope["task_type"],
            trace_id=sample_envelope["trace_id"],
        )

    def test_retry_count_increments_to_1(self, redis_client, sample_envelope):
        sample_envelope["retry_count"] = 0
        mocks = _run_one_iteration(redis_client, sample_envelope, httpx.ReadTimeout("timeout"))
        # Fourth positional arg is retry_count = 1
        assert mocks["ops"].task_retried.call_args[0][3] == 1

    def test_no_retry_at_max(self, redis_client, sample_envelope):
        """After 2 retries (retry_count=2), task fails instead of retrying."""
        sample_envelope["retry_count"] = 2
        mocks = _run_one_iteration(redis_client, sample_envelope, httpx.ReadTimeout("timeout"))
        mocks["ops"].task_retried.assert_not_called()
        mocks["ops"].task_failed.assert_called_once()

    def test_retry_count_field_in_source(self):
        source = inspect.getsource(_run_worker)
        assert 'envelope.get("retry_count", 0)' in source


# ---------------------------------------------------------------------------
# 3. Graceful connection errors
# ---------------------------------------------------------------------------


class TestGracefulConnectionErrors:
    """ConnectError retries with 30s backoff before failing."""

    def test_connect_error_sleeps_30s(self, redis_client, sample_envelope):
        mocks = _run_one_iteration(redis_client, sample_envelope, httpx.ConnectError("refused"))
        mocks["time"].sleep.assert_called_with(30)

    def test_connect_error_logs_retry(self, redis_client, sample_envelope):
        mocks = _run_one_iteration(redis_client, sample_envelope, httpx.ConnectError("refused"))
        mocks["ops"].task_failed.assert_not_called()
        mocks["ops"].task_retried.assert_called_once()

    def test_connect_error_handling_in_source(self):
        source = inspect.getsource(_run_worker)
        assert "httpx.ConnectError" in source
        assert "time.sleep(30)" in source


# ---------------------------------------------------------------------------
# 4. OpsLogger.task_retried
# ---------------------------------------------------------------------------


class TestOpsLoggerTaskRetried:
    def test_method_exists(self):
        assert hasattr(OpsLogger, "task_retried")

    def test_writes_event(self, ops_logger):
        ops_logger.task_retried("t1", "generate_post", "marketing", 1)
        events = ops_logger.read_events(event_filter="task_retried")
        assert len(events) == 1
        assert events[0]["task_id"] == "t1"
        assert events[0]["retry_count"] == 1

    def test_multiple_retries(self, ops_logger):
        ops_logger.task_retried("t1", "task", "marketing", 1)
        ops_logger.task_retried("t1", "task", "marketing", 2)
        events = ops_logger.read_events(event_filter="task_retried")
        assert len(events) == 2
        assert events[1]["retry_count"] == 2
