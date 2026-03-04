"""
Linear webhook ingress for Dispatcher.

Receives Linear Issue webhooks, validates signature, maps Issue -> TaskEnvelope,
and enqueues the task in Redis for Dispatcher workers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

import redis
from fastapi import FastAPI, Header, HTTPException, Request

from dispatcher.queue import TaskQueue

logger = logging.getLogger("dispatcher.linear_webhook")

DEFAULT_WEBHOOK_SECRET_ENV = "LINEAR_WEBHOOK_SECRET"
DEFAULT_RICK_IDENTIFIERS_ENV = "LINEAR_RICK_IDENTIFIERS"
DEFAULT_RICK_IDENTIFIERS = "rick"

DEFAULT_TASK = "llm.generate"
DEFAULT_TEAM = "system"
DEFAULT_TASK_TYPE = "general"

LINEAR_WEBHOOK_PATH = "/webhooks/linear"

TEAM_LABEL_MAP = {
    "marketing": "marketing",
    "advisory": "advisory",
    "improvement": "improvement",
    "lab": "lab",
    "system": "system",
    "infra": "system",
    "infrastructure": "system",
}

TASK_TYPE_LABEL_MAP = {
    "coding": "coding",
    "writing": "writing",
    "research": "research",
    "critical": "critical",
    "ms_stack": "ms_stack",
    "general": "general",
}

LINEAR_PRIORITY_MAP = {
    1: "high",    # urgent
    2: "high",    # high
    3: "medium",  # normal
    4: "low",     # low
    0: "medium",  # no priority
}

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis | None:
    """Lazy Redis client. Returns None when Redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable for Linear webhook: %s", exc)
        _redis_client = None
        return None


def _normalize_label(value: str) -> str:
    return value.strip().lower()


def parse_rick_identifiers(raw: str | None) -> set[str]:
    """
    Parse comma-separated Rick identifiers (name/email/id) into a normalized set.
    """
    if raw is None:
        raw = ""
    parts = [_normalize_label(part) for part in raw.split(",")]
    identifiers = {part for part in parts if part}
    if not identifiers:
        identifiers = {DEFAULT_RICK_IDENTIFIERS}
    return identifiers


def _extract_labels(issue_data: Mapping[str, Any]) -> list[str]:
    """
    Extract label names from possible Linear payload shapes.

    Supports:
    - labels: [{"name": "..."}]
    - labels: {"nodes": [{"name": "..."}]}
    - labels: ["..."]
    """
    labels_raw = issue_data.get("labels", [])
    if isinstance(labels_raw, Mapping):
        labels_raw = labels_raw.get("nodes") or labels_raw.get("data") or []

    labels: list[str] = []
    if not isinstance(labels_raw, Sequence) or isinstance(labels_raw, (str, bytes)):
        return labels

    for item in labels_raw:
        if isinstance(item, str):
            label_name = item.strip()
        elif isinstance(item, Mapping):
            label_name = str(item.get("name", "")).strip()
        else:
            label_name = ""

        if label_name and label_name not in labels:
            labels.append(label_name)
    return labels


def _extract_assignee_candidates(issue_data: Mapping[str, Any]) -> list[str]:
    assignee = issue_data.get("assignee")
    if assignee is None:
        return []

    candidates: list[str] = []
    if isinstance(assignee, str):
        cleaned = assignee.strip()
        if cleaned:
            candidates.append(cleaned)
        return candidates

    if not isinstance(assignee, Mapping):
        return candidates

    for key in ("id", "name", "displayName", "email"):
        value = str(assignee.get(key, "")).strip()
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def is_issue_assigned_to_rick(issue_data: Mapping[str, Any], rick_identifiers: set[str]) -> bool:
    """Return True when issue assignee matches one of Rick identifiers."""
    if not rick_identifiers:
        return False

    assignee_values = _extract_assignee_candidates(issue_data)
    if not assignee_values:
        return False

    normalized_ids = {_normalize_label(value) for value in rick_identifiers if value}
    for raw_assignee in assignee_values:
        assignee = _normalize_label(raw_assignee)
        for rid in normalized_ids:
            if assignee == rid:
                return True
            if re.search(rf"\b{re.escape(rid)}\b", assignee):
                return True
    return False


def validate_linear_signature(raw_body: bytes, signature_header: str, secret: str) -> bool:
    """
    Validate Linear-Signature header using HMAC SHA256.

    Accepts both:
    - <hex_digest>
    - sha256=<hex_digest>
    """
    if not signature_header or not secret:
        return False

    provided = signature_header.strip().lower()
    if provided.startswith("sha256="):
        provided = provided.split("=", 1)[1]

    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(provided, expected)


def _infer_team(issue_data: Mapping[str, Any], labels_lower: list[str]) -> str:
    for label in labels_lower:
        mapped = TEAM_LABEL_MAP.get(label)
        if mapped:
            return mapped

    team = issue_data.get("team")
    if isinstance(team, Mapping):
        team_candidates = [
            str(team.get("key", "")).strip().lower(),
            str(team.get("name", "")).strip().lower(),
        ]
        for value in team_candidates:
            if value in TEAM_LABEL_MAP:
                return TEAM_LABEL_MAP[value]
            if value in {"marketing", "advisory", "improvement", "lab", "system"}:
                return value

    return DEFAULT_TEAM


def _infer_task_type(labels_lower: list[str]) -> str:
    for label in labels_lower:
        mapped = TASK_TYPE_LABEL_MAP.get(label)
        if mapped:
            return mapped
    return DEFAULT_TASK_TYPE


def _infer_task_name(labels_lower: list[str]) -> str:
    for label in labels_lower:
        if not label.startswith("task:"):
            continue
        task_name = label.split(":", 1)[1].strip()
        if task_name:
            return task_name
    return DEFAULT_TASK


def _map_priority(raw_priority: Any) -> str:
    try:
        numeric = int(raw_priority)
    except (TypeError, ValueError):
        numeric = 0
    return LINEAR_PRIORITY_MAP.get(numeric, "medium")


def linear_issue_to_envelope(issue_data: Mapping[str, Any], action: str = "create") -> dict[str, Any]:
    """
    Map Linear Issue payload to the TaskEnvelope shape used by TaskQueue.
    """
    issue_id = str(issue_data.get("id", "")).strip()
    if not issue_id:
        raise ValueError("Linear issue payload missing 'id'")

    title = str(issue_data.get("title", "")).strip()
    description = str(issue_data.get("description", "")).strip()
    identifier = str(issue_data.get("identifier", "")).strip()
    issue_url = str(issue_data.get("url", "")).strip()
    labels = _extract_labels(issue_data)
    labels_lower = [_normalize_label(label) for label in labels]

    team = _infer_team(issue_data, labels_lower)
    task_type = _infer_task_type(labels_lower)
    task_name = _infer_task_name(labels_lower)
    priority = _map_priority(issue_data.get("priority"))
    prompt = description or title or f"Linear issue {issue_id}"

    now_iso = datetime.now(timezone.utc).isoformat()
    task_id = f"lin-{issue_id[:8]}-{uuid.uuid4().hex[:6]}"

    envelope: dict[str, Any] = {
        "schema_version": "0.1",
        "task_id": task_id,
        "team": team,
        "task_type": task_type,
        "task": task_name,
        "priority": priority,
        "input": {
            "prompt": prompt,
            "title": title,
            "description": description,
            "labels": labels,
            "priority": priority,
            "linear_issue_id": issue_id,
            "linear_identifier": identifier,
            "linear_url": issue_url,
        },
        "status": "queued",
        "trace_id": str(uuid.uuid4()),
        "created_at": now_iso,
        "queued_at": time.time(),
        "source": "linear_webhook",
        "linear_issue_id": issue_id,
        "linear_event_action": action,
    }
    return envelope


def should_enqueue_linear_issue(payload: Mapping[str, Any], rick_identifiers: set[str]) -> tuple[bool, str]:
    """
    Decide if webhook payload should be converted to a task and enqueued.
    """
    event_type = str(payload.get("type", "")).strip().lower()
    if event_type != "issue":
        return False, "unsupported_type"

    action = str(payload.get("action", "")).strip().lower()
    if action not in {"create", "update"}:
        return False, "unsupported_action"

    issue_data = payload.get("data")
    if not isinstance(issue_data, Mapping):
        return False, "invalid_issue_payload"

    labels = _extract_labels(issue_data)
    labels_lower = {_normalize_label(label) for label in labels}
    if "no-auto" in labels_lower:
        return False, "label_no_auto"

    if not is_issue_assigned_to_rick(issue_data, rick_identifiers):
        return False, "not_assigned_to_rick"

    return True, "enqueue"


app = FastAPI(
    title="Umbral Dispatcher - Linear Webhook",
    description="Receives Linear webhooks and enqueues TaskEnvelopes in Redis.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "service": "dispatcher.linear_webhook"}


@app.post(LINEAR_WEBHOOK_PATH)
async def linear_webhook(
    request: Request,
    linear_signature: str | None = Header(default=None, alias="Linear-Signature"),
) -> dict[str, Any]:
    raw_body = await request.body()
    webhook_secret = os.environ.get(DEFAULT_WEBHOOK_SECRET_ENV, "").strip()
    if not webhook_secret:
        raise HTTPException(
            status_code=503,
            detail=f"{DEFAULT_WEBHOOK_SECRET_ENV} not configured",
        )

    if not validate_linear_signature(raw_body, linear_signature or "", webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid Linear signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    rick_identifiers = parse_rick_identifiers(
        os.environ.get(DEFAULT_RICK_IDENTIFIERS_ENV, DEFAULT_RICK_IDENTIFIERS)
    )

    should_enqueue, reason = should_enqueue_linear_issue(payload, rick_identifiers)
    if not should_enqueue:
        return {"ok": True, "enqueued": False, "ignored_reason": reason}

    issue_data = payload["data"]
    action = str(payload.get("action", "create")).lower()
    envelope = linear_issue_to_envelope(issue_data, action=action)

    redis_client = _get_redis()
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not available")

    queue = TaskQueue(redis_client)
    queue.enqueue(envelope)

    logger.info(
        "Linear issue enqueued: issue_id=%s task_id=%s action=%s",
        issue_data.get("id"),
        envelope["task_id"],
        action,
    )
    return {
        "ok": True,
        "enqueued": True,
        "task_id": envelope["task_id"],
        "linear_issue_id": issue_data.get("id"),
    }

