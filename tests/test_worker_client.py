from unittest.mock import MagicMock, patch

from client.worker_client import WorkerClient


def test_run_sends_canonical_envelope_fields():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"ok": True}

    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.post.return_value = response

    envelope = {
        "task_id": "task-123",
        "team": "improvement",
        "task_type": "coding",
        "trace_id": "trace-123",
        "source": "openclaw_gateway",
        "source_kind": "tool_enqueue",
        "project_name": "Mejora Continua Agent Stack",
        "notion_track": True,
        "callback_url": "https://callback.example/hook",
    }

    with patch("client.worker_client.httpx.Client", return_value=http_client):
        wc = WorkerClient(base_url="http://worker.local", token="test-token")
        wc.run("ping", {"hello": "world"}, envelope=envelope)

    payload = http_client.post.call_args.kwargs["json"]
    assert payload["schema_version"] == "0.1"
    assert payload["task"] == "ping"
    assert payload["input"] == {"hello": "world"}
    assert payload["task_id"] == "task-123"
    assert payload["team"] == "improvement"
    assert payload["task_type"] == "coding"
    assert payload["trace_id"] == "trace-123"
    assert payload["source"] == "openclaw_gateway"
    assert payload["source_kind"] == "tool_enqueue"
    assert payload["project_name"] == "Mejora Continua Agent Stack"
    assert payload["notion_track"] is True
    assert payload["callback_url"] == "https://callback.example/hook"


def test_run_sends_optional_internal_caller_header():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"ok": True}

    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.post.return_value = response

    with patch("client.worker_client.httpx.Client", return_value=http_client):
        wc = WorkerClient(
            base_url="http://worker.local",
            token="test-token",
            caller_id="script.verify_stack_vps",
        )
        wc.run("ping", {"hello": "world"})

    headers = http_client.post.call_args.kwargs["headers"]
    assert headers["X-Umbral-Caller"] == "script.verify_stack_vps"
