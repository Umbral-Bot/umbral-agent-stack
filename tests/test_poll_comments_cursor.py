"""Tests for ADR-010: Redis cursor checkpoint in poll_comments (O8i)."""
from unittest.mock import MagicMock, patch


def _make_response(status, body):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body
    r.text = str(body)
    return r


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_bootstrap_walks_to_tail_and_applies_since_filter(_req, mock_client_cls):
    """First poll with no Redis cursor should seek tail and collect only post-since comments."""
    from worker.notion_client import poll_comments, _cursor_key

    page_a = _make_response(200, {
        "results": [{"id": "old-a", "created_time": "2025-01-01T00:00:00.000Z",
                     "created_by": {"id": "u"}, "rich_text": []}],
        "has_more": True, "next_cursor": "cur-A",
    })
    page_b = _make_response(200, {
        "results": [{"id": "old-b", "created_time": "2025-02-01T00:00:00.000Z",
                     "created_by": {"id": "u"}, "rich_text": []}],
        "has_more": False,
    })
    mock_http = MagicMock()
    mock_http.get.side_effect = [page_a, page_b]
    mock_client_cls.return_value.__enter__.return_value = mock_http

    redis_mock = MagicMock()
    redis_mock.get.return_value = None  # no saved cursor

    result = poll_comments(
        page_id="P",
        limit=20,
        since="2025-01-15T00:00:00+00:00",
        redis_client=redis_mock,
    )

    assert result["bootstrap"] is True
    assert result["count"] == 1
    assert result["comments"][0]["id"] == "old-b"
    assert result["requests_count"] == 2
    # cursor saved (last next_cursor seen = "cur-A")
    redis_mock.set.assert_called_once()
    args, kwargs = redis_mock.set.call_args
    assert args[0] == _cursor_key("P")
    assert args[1] == "cur-A"
    assert kwargs.get("ex") == 30 * 24 * 3600


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_cursor_hit_starts_at_saved_cursor_and_returns_only_new(_req, mock_client_cls):
    from worker.notion_client import poll_comments

    resp = _make_response(200, {
        "results": [
            {"id": "new-1", "created_time": "2026-05-06T01:00:00.000Z",
             "created_by": {"id": "u"}, "rich_text": [{"plain_text": "hi"}]},
        ],
        "has_more": False,
    })
    mock_http = MagicMock()
    mock_http.get.return_value = resp
    mock_client_cls.return_value.__enter__.return_value = mock_http

    redis_mock = MagicMock()
    redis_mock.get.return_value = "cur-saved"

    result = poll_comments(page_id="P", limit=20, redis_client=redis_mock)

    assert result["cursor_used"] is True
    assert result["bootstrap"] is False
    assert result["requests_count"] == 1
    assert result["count"] == 1
    assert result["comments"][0]["id"] == "new-1"
    # First (and only) call used start_cursor="cur-saved"
    params = mock_http.get.call_args.kwargs["params"]
    assert params["start_cursor"] == "cur-saved"


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_cursor_invalidation_resets_and_returns_empty(_req, mock_client_cls):
    from worker.notion_client import poll_comments, _cursor_key

    bad = _make_response(400, {"object": "error", "code": "validation_error"})
    mock_http = MagicMock()
    mock_http.get.return_value = bad
    mock_client_cls.return_value.__enter__.return_value = mock_http

    redis_mock = MagicMock()
    redis_mock.get.return_value = "cur-stale"

    result = poll_comments(page_id="P", limit=20, redis_client=redis_mock)

    assert result["cursor_reset"] is True
    assert result["count"] == 0
    redis_mock.delete.assert_called_once_with(_cursor_key("P"))


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_no_redis_falls_back_to_legacy_since_filter(_req, mock_client_cls):
    """Without redis_client, behavior matches pre-ADR-010 semantics."""
    from worker.notion_client import poll_comments

    resp = _make_response(200, {
        "results": [
            {"id": "old", "created_time": "2025-01-01T00:00:00.000Z",
             "created_by": {"id": "u"}, "rich_text": []},
            {"id": "new", "created_time": "2026-05-06T01:00:00.000Z",
             "created_by": {"id": "u"}, "rich_text": [{"plain_text": "hi"}]},
        ],
        "has_more": False,
    })
    mock_http = MagicMock()
    mock_http.get.return_value = resp
    mock_client_cls.return_value.__enter__.return_value = mock_http

    result = poll_comments(
        page_id="P", limit=20, since="2026-01-01T00:00:00+00:00",
    )

    assert result["cursor_used"] is False
    assert result["bootstrap"] is False
    assert result["count"] == 1
    assert result["comments"][0]["id"] == "new"


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_tail_sentinel_triggers_rebootstrap(_req, mock_client_cls):
    """When saved cursor == sentinel, treat as bootstrap and collect post-since results."""
    from worker.notion_client import poll_comments, CURSOR_TAIL_SENTINEL

    resp = _make_response(200, {
        "results": [{"id": "x", "created_time": "2026-05-01T00:00:00.000Z",
                     "created_by": {"id": "u"}, "rich_text": []}],
        "has_more": False,
    })
    mock_http = MagicMock()
    mock_http.get.return_value = resp
    mock_client_cls.return_value.__enter__.return_value = mock_http

    redis_mock = MagicMock()
    redis_mock.get.return_value = CURSOR_TAIL_SENTINEL

    result = poll_comments(
        page_id="P",
        limit=20,
        since="2026-04-30T00:00:00+00:00",
        redis_client=redis_mock,
    )

    assert result["bootstrap"] is True
    assert result["count"] == 1
    assert result["comments"][0]["id"] == "x"
