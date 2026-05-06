"""Rick mention adapter (Ola 1b).

Detects @rick mentions in Notion comments authored by David and routes them
to the rick-orchestrator subagent via the dispatcher queue, bypassing the
legacy intent_classifier + smart_reply path. Each delegation is recorded in
the append-only trace log.

ADR: notion-governance/docs/adr/05-ola-1b-channel-adapters-and-traceability.md §2.1, §2.2.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from worker.tasks._trace import append_delegation
from dispatcher.queue import TaskQueue
from dispatcher.scheduler import TaskScheduler
from client.worker_client import WorkerClient

logger = logging.getLogger("dispatcher.rick_mention")

_RICK_MENTION_RE = re.compile(r"@rick(?:-orchestrator)?\b", re.IGNORECASE)
_MAX_TEXT_SNIPPET = 500


def is_rick_mention(text: str, author: Optional[str], allowlist: set[str]) -> bool:
    """Return True iff text contains @rick (or @rick-orchestrator) AND author is allowlisted."""
    if not text or not author:
        return False
    if author not in allowlist:
        return False
    return bool(_RICK_MENTION_RE.search(text))


def _david_allowlist() -> set[str]:
    raw = os.environ.get("DAVID_NOTION_USER_ID", "").strip()
    return {raw} if raw else set()


def handle_rick_mention(
    *,
    text: str,
    comment_id: str,
    page_id: Optional[str],
    page_kind: Optional[str],
    author: Optional[str],
    wc: WorkerClient,
    queue: TaskQueue,
    scheduler: TaskScheduler,
) -> None:
    """Enqueue rick-orchestrator triage and record the delegation trace."""
    trace_id = uuid.uuid4().hex
    snippet = (text or "")[:_MAX_TEXT_SNIPPET]
    task_id = uuid.uuid4().hex
    envelope = {
        "task_id": task_id,
        "task": "rick.orchestrator.triage",
        "team": "rick-orchestrator",
        "task_type": "triage",
        "trace_id": trace_id,
        "source": "notion-poller",
        "source_kind": "notion.comment.mention",
        "input": {
            "kind": "notion.comment.mention",
            "comment_id": comment_id,
            "page_id": page_id,
            "page_kind": page_kind,
            "author": author,
            "text": snippet,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
        },
    }
    queue.enqueue(envelope)
    append_delegation({
        "trace_id": trace_id,
        "from": "channel-adapter:notion-poller",
        "to": "rick-orchestrator",
        "intent": "triage",
        "ref": {"comment_id": comment_id, "page_id": page_id},
        "summary": f"@rick mention from author={author[:8] if author else '?'} on {page_kind or 'unknown'}",
    })
    logger.info(
        "Rick mention routed: comment=%s author=%s page=%s trace=%s",
        comment_id[:8], (author or "?")[:8], (page_id or "?")[:8], trace_id[:8],
    )
