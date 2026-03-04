"""
Tests for Linear -> Dispatcher webhook ingestion.
"""

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

try:
    import fakeredis

    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")

from dispatcher.linear_webhook import (  # noqa: E402
    app,
    linear_issue_to_envelope,
    should_enqueue_linear_issue,
    validate_linear_signature,
)


def _sample_issue(
    *,
    assignee_name: str = "Rick",
    labels: list[dict[str, str]] | None = None,
) -> dict:
    if labels is None:
        labels = [{"name": "coding"}, {"name": "Marketing"}]

    return {
        "id": "7c9f0d3a-1234-4567-89ab-abcdef012345",
        "identifier": "UMB-42",
        "title": "Fix webhook ingestion",
        "description": "Implement Linear webhook to enqueue tasks.",
        "priority": 1,
        "team": {"name": "Advisory", "key": "advisory"},
        "assignee": {"name": assignee_name, "email": f"{assignee_name.lower()}@example.com"},
        "labels": labels,
        "url": "https://linear.app/umbral/issue/UMB-42/fix-webhook-ingestion",
    }


def _sample_payload(*, action: str = "create", issue: dict | None = None) -> dict:
    return {
        "action": action,
        "type": "Issue",
        "data": issue or _sample_issue(),
    }


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


def test_validate_linear_signature_accepts_hex_and_prefixed():
    secret = "linear-secret"
    payload = _sample_payload()
    body = json.dumps(payload).encode("utf-8")
    signature = _sign(secret, body)

    assert validate_linear_signature(body, signature, secret) is True
    assert validate_linear_signature(body, f"sha256={signature}", secret) is True
    assert validate_linear_signature(body, "bad-signature", secret) is False


def test_linear_issue_to_envelope_mapping():
    issue = _sample_issue(
        labels=[
            {"name": "coding"},
            {"name": "Marketing"},
            {"name": "task:research.web"},
        ]
    )
    envelope = linear_issue_to_envelope(issue, action="create")

    assert envelope["schema_version"] == "0.1"
    assert envelope["task_id"].startswith("lin-7c9f0d3a")
    assert envelope["task"] == "research.web"
    assert envelope["team"] == "marketing"
    assert envelope["task_type"] == "coding"
    assert envelope["priority"] == "high"
    assert envelope["linear_issue_id"] == issue["id"]
    assert envelope["input"]["prompt"] == issue["description"]
    assert envelope["input"]["labels"] == ["coding", "Marketing", "task:research.web"]


def test_filtering_only_assigned_to_rick():
    rick_ids = {"rick"}

    ok_payload = _sample_payload(issue=_sample_issue(assignee_name="Rick Sanchez"))
    should_enqueue, reason = should_enqueue_linear_issue(ok_payload, rick_ids)
    assert should_enqueue is True
    assert reason == "enqueue"

    other_payload = _sample_payload(issue=_sample_issue(assignee_name="Alice"))
    should_enqueue, reason = should_enqueue_linear_issue(other_payload, rick_ids)
    assert should_enqueue is False
    assert reason == "not_assigned_to_rick"


def test_no_auto_label_is_ignored():
    payload = _sample_payload(
        issue=_sample_issue(labels=[{"name": "coding"}, {"name": "no-auto"}])
    )
    should_enqueue, reason = should_enqueue_linear_issue(payload, {"rick"})
    assert should_enqueue is False
    assert reason == "label_no_auto"


def test_webhook_enqueues_issue_for_rick(client, fake_redis, monkeypatch):
    secret = "linear-secret"
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("LINEAR_RICK_IDENTIFIERS", "rick,rick@example.com")

    payload = _sample_payload(action="create")
    body = json.dumps(payload).encode("utf-8")
    signature = _sign(secret, body)

    with patch("dispatcher.linear_webhook._get_redis", return_value=fake_redis):
        resp = client.post(
            "/webhooks/linear",
            content=body,
            headers={"Linear-Signature": signature, "Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["enqueued"] is True

    task_id = data["task_id"]
    stored_raw = fake_redis.get(f"umbral:task:{task_id}")
    assert stored_raw is not None
    stored = json.loads(stored_raw)
    assert stored["linear_issue_id"] == payload["data"]["id"]
    assert stored["task_type"] == "coding"
    assert stored["team"] == "marketing"


def test_webhook_ignores_issue_not_assigned_to_rick(client, fake_redis, monkeypatch):
    secret = "linear-secret"
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("LINEAR_RICK_IDENTIFIERS", "rick")

    payload = _sample_payload(issue=_sample_issue(assignee_name="Alice"))
    body = json.dumps(payload).encode("utf-8")
    signature = _sign(secret, body)

    with patch("dispatcher.linear_webhook._get_redis", return_value=fake_redis):
        resp = client.post(
            "/webhooks/linear",
            content=body,
            headers={"Linear-Signature": signature, "Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["enqueued"] is False
    assert data["ignored_reason"] == "not_assigned_to_rick"
    assert fake_redis.llen("umbral:tasks:pending") == 0
