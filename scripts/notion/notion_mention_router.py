"""Skill: notion-mention-router (entrypoint module per task 025).

This is the canonical, name-aligned skill module for "Rick Notion mention
routing". It is a **thin wrapper** that delegates to
`dispatcher.rick_mention`, which contains the real implementation already
in production since Ola 1b (2026-04). See `tests/test_rick_mention.py` for
the live behavior contract.

Why a wrapper instead of duplicating the logic:
- The detect → filter → dispatch path lives in `dispatcher/rick_mention.py`
  with passing tests (7/7) and is integrated with the running notion-poller
  daemon (`scripts/vps/notion-poller-daemon.py`).
- Per `<implementationDiscipline>` we must NOT duplicate working code or
  refactor unrelated modules. Task 025 only requires the **named skill**
  to exist as an importable surface for Rick channels.

What this module exposes:

- `is_rick_mention(text, author, allowlist)` — re-export.
- `handle_rick_mention(...)` — re-export.
- `route_one_mention(comment_payload, *, deps)` — convenience wrapper that
  takes a Notion comment dict (as returned by `notion.poll_comments`) and
  feeds it into the existing handler. Useful for ad-hoc CLI dispatch and
  for the future webhook handler (B4 future migration).

Identity gap (ADR D2):
- Detection + dispatch run as the **integration bot** identity
  (`NOTION_API_KEY`, David's integration). That is OK because polling is
  read-only.
- The reply path (posting Rick's comment back to Notion) MUST run with
  `NOTION_RICK_INTEGRATION_TOKEN` (separate identity scoped to
  `rick.asistente@gmail.com`). That reply path is NOT activated in this
  task — it is enabled after David completes B2 OAuth setup. Until then,
  the legacy `notion.add_comment` worker task posts as integration bot
  (documented gap, runbook references it).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from dispatcher.rick_mention import (  # noqa: F401  (re-export)
    is_rick_mention,
    handle_rick_mention,
)


def route_one_mention(
    comment: Dict[str, Any],
    *,
    allowlist: set[str],
    wc: Any,
    queue: Any,
    scheduler: Any,
    page_kind: Optional[str] = None,
) -> bool:
    """Route a single Notion comment payload through `handle_rick_mention`.

    Parameters
    ----------
    comment : dict
        Notion comment object. Expected keys: `id`, `parent` (page or block),
        `created_by.id`, plain-text representation in `rich_text` or
        precomputed `text`.
    allowlist : set[str]
        Allowed author user_ids (typically `{DAVID_NOTION_USER_ID}`).
    wc, queue, scheduler
        Same dependencies the legacy poller passes; injected for
        testability.
    page_kind : str, optional
        Logical kind tag (e.g. ``"control_room"``).

    Returns
    -------
    bool
        True if a mention was detected AND routed; False otherwise.
    """
    text = (
        comment.get("text")
        or "".join(rt.get("plain_text", "") for rt in comment.get("rich_text", []))
        or ""
    )
    author = (comment.get("created_by") or {}).get("id")
    parent = comment.get("parent") or {}
    page_id = parent.get("page_id") or parent.get("block_id")
    comment_id = comment.get("id") or ""

    if not is_rick_mention(text, author, allowlist):
        return False

    handle_rick_mention(
        text=text,
        comment_id=comment_id,
        page_id=page_id,
        page_kind=page_kind,
        author=author,
        wc=wc,
        queue=queue,
        scheduler=scheduler,
    )
    return True
