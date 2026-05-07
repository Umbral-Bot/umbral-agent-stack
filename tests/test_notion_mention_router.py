"""Tests for skill `notion-mention-router` (scripts/notion/notion_mention_router).

The skill is a thin wrapper around `dispatcher.rick_mention`; we test the
wrapper-only behavior here. The handler internals are covered by
`tests/test_rick_mention.py` (7 tests, all passing).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def deps():
    """Fake injected dependencies."""
    return dict(
        wc=MagicMock(name="WorkerClient"),
        queue=MagicMock(name="TaskQueue"),
        scheduler=MagicMock(name="TaskScheduler"),
    )


def test_route_one_mention_returns_true_and_calls_handler_when_rick_mentioned(deps):
    """Mention from allowlisted author triggers handle_rick_mention."""
    from scripts.notion import notion_mention_router as router

    comment = {
        "id": "comment-1",
        "rich_text": [{"plain_text": "hey @rick can you check this?"}],
        "created_by": {"id": "david-uuid"},
        "parent": {"page_id": "page-xyz"},
    }
    with patch.object(router, "handle_rick_mention") as mock_handler:
        result = router.route_one_mention(
            comment, allowlist={"david-uuid"}, page_kind="control_room", **deps
        )

    assert result is True
    mock_handler.assert_called_once()
    kwargs = mock_handler.call_args.kwargs
    assert kwargs["comment_id"] == "comment-1"
    assert kwargs["page_id"] == "page-xyz"
    assert kwargs["page_kind"] == "control_room"
    assert kwargs["author"] == "david-uuid"
    assert "@rick" in kwargs["text"]


def test_route_one_mention_returns_false_when_no_mention(deps):
    """No @rick → not routed."""
    from scripts.notion import notion_mention_router as router

    comment = {
        "id": "comment-2",
        "rich_text": [{"plain_text": "just an ordinary comment"}],
        "created_by": {"id": "david-uuid"},
        "parent": {"page_id": "page-xyz"},
    }
    with patch.object(router, "handle_rick_mention") as mock_handler:
        result = router.route_one_mention(comment, allowlist={"david-uuid"}, **deps)

    assert result is False
    mock_handler.assert_not_called()


def test_route_one_mention_rejects_non_allowlisted_author(deps):
    """@rick from non-allowlisted author → ignored (per ADR D6 whitelist)."""
    from scripts.notion import notion_mention_router as router

    comment = {
        "id": "comment-3",
        "rich_text": [{"plain_text": "@rick please reply"}],
        "created_by": {"id": "stranger-uuid"},
        "parent": {"page_id": "page-xyz"},
    }
    with patch.object(router, "handle_rick_mention") as mock_handler:
        result = router.route_one_mention(comment, allowlist={"david-uuid"}, **deps)

    assert result is False
    mock_handler.assert_not_called()


def test_route_one_mention_handles_block_parent(deps):
    """Comment whose parent is block_id (not page_id) still resolves."""
    from scripts.notion import notion_mention_router as router

    comment = {
        "id": "comment-4",
        "rich_text": [{"plain_text": "@rick-orchestrator do the thing"}],
        "created_by": {"id": "david-uuid"},
        "parent": {"block_id": "block-abc"},
    }
    with patch.object(router, "handle_rick_mention") as mock_handler:
        result = router.route_one_mention(comment, allowlist={"david-uuid"}, **deps)

    assert result is True
    assert mock_handler.call_args.kwargs["page_id"] == "block-abc"


def test_route_one_mention_uses_text_field_when_present(deps):
    """If comment has precomputed `text`, it is preferred over rich_text."""
    from scripts.notion import notion_mention_router as router

    comment = {
        "id": "comment-5",
        "text": "@rick respond plz",
        "rich_text": [{"plain_text": "ignored"}],
        "created_by": {"id": "david-uuid"},
        "parent": {"page_id": "page-xyz"},
    }
    with patch.object(router, "handle_rick_mention") as mock_handler:
        result = router.route_one_mention(comment, allowlist={"david-uuid"}, **deps)

    assert result is True
    assert mock_handler.call_args.kwargs["text"] == "@rick respond plz"


def test_reexports_match_dispatcher_rick_mention():
    """The wrapper re-exports the canonical handler symbols."""
    from scripts.notion import notion_mention_router as router
    from dispatcher import rick_mention

    assert router.is_rick_mention is rick_mention.is_rick_mention
    assert router.handle_rick_mention is rick_mention.handle_rick_mention
