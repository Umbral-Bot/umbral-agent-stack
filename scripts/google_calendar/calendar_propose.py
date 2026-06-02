"""Thin Python entrypoint for OpenClaw `calendar-propose`.

The canonical event logic is in `worker/tasks/google_calendar.py`.
This wrapper keeps ADR-16 policy clear: proposals are explicit and optional
whitelist checks are enforced before forwarding.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from client.worker_client import WorkerClient


PROPOSE_PREFIX = "[PROPUESTA]"


def _normalize_prefix(title: str) -> str:
    title = (title or "").strip()
    if not title:
        return title
    return title if title.startswith(PROPOSE_PREFIX) else f"{PROPOSE_PREFIX} {title}"


def _run(
    task: str,
    payload: Dict[str, Any],
    wc: Optional[WorkerClient] = None,
) -> Dict[str, Any]:
    if wc is None:
        wc = WorkerClient()
    return wc.run(task, payload)


def create_event_proposal(
    title: str,
    start: str,
    end: Optional[str] = None,
    calendar_id: str = "primary",
    timezone: str = "America/Santiago",
    description: str = "",
    attendees: Optional[List[str]] = None,
    allowed_calendar_ids: Optional[Set[str]] = None,
    wc: Optional[WorkerClient] = None,
) -> Dict[str, Any]:
    """Create a calendar proposal (`google.calendar.create_event`) with explicit prefix."""
    if not title:
        return {"ok": False, "error": "title is required"}
    if not start:
        return {"ok": False, "error": "start is required"}

    if allowed_calendar_ids is not None and calendar_id not in allowed_calendar_ids:
        return {
            "ok": False,
            "error": "calendar_id not in whitelist",
            "allowed_calendar_ids": sorted(allowed_calendar_ids),
        }

    payload: Dict[str, Any] = {
        "title": _normalize_prefix(title),
        "description": description or "",
        "start": start,
        "calendar_id": calendar_id,
        "timezone": timezone,
    }
    if end:
        payload["end"] = end
    if attendees:
        payload["attendees"] = attendees

    return _run("google.calendar.create_event", payload, wc=wc)


def list_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 10,
    allowed_calendar_ids: Optional[Set[str]] = None,
    wc: Optional[WorkerClient] = None,
) -> Dict[str, Any]:
    """List events (`google.calendar.list_events`) from a whitelist-limited calendar."""
    if allowed_calendar_ids is not None and calendar_id not in allowed_calendar_ids:
        return {
            "ok": False,
            "error": "calendar_id not in whitelist",
            "allowed_calendar_ids": sorted(allowed_calendar_ids),
        }

    payload: Dict[str, Any] = {
        "calendar_id": calendar_id,
        "max_results": max_results,
    }
    if time_min:
        payload["time_min"] = time_min
    if time_max:
        payload["time_max"] = time_max
    return _run("google.calendar.list_events", payload, wc=wc)


__all__ = ["create_event_proposal", "list_events", "PROPOSE_PREFIX"]
