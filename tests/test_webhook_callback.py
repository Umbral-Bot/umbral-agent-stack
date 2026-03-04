"""
Tests for webhook callback flow (R3 task 014).

Run with:
    python -m pytest tests/test_webhook_callback.py -v
"""

import json
import os
import uuid
from unittest.mock import MagicMock, patch

import httpx
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
from dispatcher.service import _run_worker  # noqa: E402
from worker.app import app  # noqa: E402

AUTH = {"Authorization": "Bearer test-token-12345"}
TASK_KEY_PREFIX = "umbral:task:"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


class _ImmediateThread:
    """Thread stub that executes target synchronously on start()."""

    def __init__(self, target=None, args=(), kwargs=None, daemon=None):  # noqa: ARG002
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


def _run_one_worker_iteration(
    redis_client,
    envelope,
    callback_post_side_effect=None,
):
    """
    Enqueue one task and execute exactly one _run_worker loop iteration.

    Returns the stored task envelope and callback HTTP client mock.
    """
    queue = TaskQueue(redis_client)
    queue.enqueue(dict(envelope))

    dequeue_calls = [0]
    original_dequeue = TaskQueue.dequeue

    def patched_dequeue(self, timeout=2):
        dequeue_calls[0] += 1
        if dequeue_calls[0] > 1:
            raise KeyboardInterrupt("stop after one iteration")
        return original_dequeue(self, timeout=timeout)

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
    wc_mock.run.return_value = {"ok": True, "result": {"message": "done"}}

    request = httpx.Request("POST", "https://callback.example/hook")
    ok_response = httpx.Response(200, request=request, text="ok")
    callback_side_effect = callback_post_side_effect or [ok_response]

    with (
        patch("dispatcher.service.redis.Redis", return_value=redis_client),
        patch("dispatcher.service.WorkerClient", return_value=wc_mock),
        patch("dispatcher.service.get_team_capabilities", return_value={"marketing": {"requires_vm": False}}),
        patch.object(TaskQueue, "dequeue", patched_dequeue),
        patch("dispatcher.service.ops_log"),
        patch("dispatcher.service._notion_upsert"),
        patch("dispatcher.service._notify_linear_completion"),
        patch("dispatcher.service.threading.Thread", side_effect=lambda *a, **k: _ImmediateThread(*a, **k)),
        patch("dispatcher.service.time") as mock_time,
        patch("dispatcher.service.httpx.Client") as mock_client_cls,
    ):
        callback_client = MagicMock()
        callback_client.post.side_effect = callback_side_effect
        mock_client_cls.return_value.__enter__.return_value = callback_client
        mock_time.time.return_value = 1741086000.0

        try:
            _run_worker(
                MagicMock(),  # pool is unused because redis.Redis is patched
                "http://127.0.0.1:8088",
                "token",
                None,
                hm,
                model_router,
                1,
            )
        except KeyboardInterrupt:
            pass

    stored = queue.get_task(envelope["task_id"])
    return stored, callback_client, mock_time


def test_enqueue_with_callback_url_stores_it_in_envelope(client, redis_client):
    with patch("worker.app._get_redis", return_value=redis_client):
        resp = client.post(
            "/enqueue",
            json={
                "task": "ping",
                "team": "system",
                "input": {"msg": "hello"},
                "callback_url": "https://callback.example/hook",
            },
            headers=AUTH,
        )

    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    raw = redis_client.get(f"{TASK_KEY_PREFIX}{task_id}")
    assert raw is not None
    stored = json.loads(raw)
    assert stored["callback_url"] == "https://callback.example/hook"


def test_complete_task_with_callback_posts_result(redis_client):
    envelope = {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "marketing",
        "task_type": "writing",
        "task": "ping",
        "input": {"msg": "hello"},
        "trace_id": str(uuid.uuid4()),
        "callback_url": "https://callback.example/hook",
    }

    stored, callback_client, _ = _run_one_worker_iteration(redis_client, envelope)

    assert stored is not None
    assert stored["status"] == "done"
    callback_client.post.assert_called_once()
    url = callback_client.post.call_args.args[0]
    payload = callback_client.post.call_args.kwargs["json"]
    assert url == "https://callback.example/hook"
    assert payload["task_id"] == envelope["task_id"]
    assert payload["status"] == "done"
    assert payload["task"] == "ping"
    assert "result" in payload
    assert "completed_at" in payload


def test_callback_failure_does_not_crash_dispatcher(redis_client):
    envelope = {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "marketing",
        "task_type": "writing",
        "task": "ping",
        "input": {"msg": "hello"},
        "trace_id": str(uuid.uuid4()),
        "callback_url": "https://callback.example/hook",
    }

    timeout_exc = httpx.ReadTimeout("callback timeout")
    stored, callback_client, _ = _run_one_worker_iteration(
        redis_client,
        envelope,
        callback_post_side_effect=[timeout_exc, timeout_exc],
    )

    assert stored is not None
    assert stored["status"] == "done"
    assert callback_client.post.call_count == 2


def test_callback_retries_once_on_5xx(redis_client):
    envelope = {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "marketing",
        "task_type": "writing",
        "task": "ping",
        "input": {"msg": "hello"},
        "trace_id": str(uuid.uuid4()),
        "callback_url": "https://callback.example/hook",
    }

    req = httpx.Request("POST", "https://callback.example/hook")
    first = httpx.Response(503, request=req, text="unavailable")
    second = httpx.Response(200, request=req, text="ok")

    stored, callback_client, mock_time = _run_one_worker_iteration(
        redis_client,
        envelope,
        callback_post_side_effect=[first, second],
    )

    assert stored is not None
    assert stored["status"] == "done"
    assert callback_client.post.call_count == 2
    mock_time.sleep.assert_called_once_with(5)


def test_without_callback_url_does_not_post(redis_client):
    envelope = {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "marketing",
        "task_type": "writing",
        "task": "ping",
        "input": {"msg": "hello"},
        "trace_id": str(uuid.uuid4()),
    }

    stored, callback_client, _ = _run_one_worker_iteration(redis_client, envelope)

    assert stored is not None
    assert stored["status"] == "done"
    callback_client.post.assert_not_called()
