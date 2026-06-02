"""Thin Python entrypoint for OpenClaw `gmail-router`.

The canonical behavior stays in `worker/tasks/gmail.py` (`gmail.create_draft` and
`gmail.list_drafts`). This module only formats validation and forwards payloads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from client.worker_client import WorkerClient


def _run(
    task: str,
    payload: Dict[str, Any],
    wc: Optional[WorkerClient] = None,
) -> Dict[str, Any]:
    if wc is None:
        wc = WorkerClient()
    return wc.run(task, payload)


def create_draft(
    to: str,
    subject: str,
    body: str,
    body_type: str = "plain",
    cc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    wc: Optional[WorkerClient] = None,
) -> Dict[str, Any]:
    """Validate Gmail draft inputs and forward to `gmail.create_draft`."""
    if not to:
        return {"ok": False, "error": "to is required"}
    if not subject:
        return {"ok": False, "error": "subject is required"}
    if body is None:
        return {"ok": False, "error": "body is required"}
    if body_type not in {"plain", "html"}:
        return {"ok": False, "error": "body_type must be plain or html"}

    payload: Dict[str, Any] = {
        "to": to,
        "subject": subject,
        "body": body,
        "body_type": body_type,
    }
    if cc:
        payload["cc"] = cc
    if reply_to:
        payload["reply_to"] = reply_to

    return _run("gmail.create_draft", payload, wc=wc)


def list_drafts(
    max_results: int = 10,
    q: Optional[str] = None,
    wc: Optional[WorkerClient] = None,
) -> Dict[str, Any]:
    """Validate listing params and forward to `gmail.list_drafts`."""
    payload: Dict[str, Any] = {"max_results": max_results}
    if q:
        payload["q"] = q
    return _run("gmail.list_drafts", payload, wc=wc)


__all__ = ["create_draft", "list_drafts"]
