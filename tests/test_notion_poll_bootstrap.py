from unittest.mock import MagicMock, patch

import fakeredis


PAGE_ID = "page-035"


def _comment(comment_id: str, created_time: str, text: str = "hello") -> dict:
    return {
        "id": comment_id,
        "created_time": created_time,
        "created_by": {"id": "user-1"},
        "rich_text": [{"plain_text": text}],
    }


def _response(
    results: list[dict],
    *,
    has_more: bool = False,
    next_cursor: str | None = None,
) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "results": results,
        "has_more": has_more,
        "next_cursor": next_cursor,
    }
    return response


def _mock_client_gets(mock_client_cls: MagicMock, *responses: MagicMock) -> MagicMock:
    mock_client = MagicMock()
    mock_client.get.side_effect = list(responses)
    mock_client_cls.return_value.__enter__.return_value = mock_client
    return mock_client


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_poll_comments_bootstrap_single_page_collects_comments(
    mock_require_notion_core,
    mock_client_cls,
):
    from worker.notion_client import CURSOR_TAIL_SENTINEL, _cursor_key, poll_comments

    redis_client = fakeredis.FakeRedis(decode_responses=True)
    redis_client.set(_cursor_key(PAGE_ID), CURSOR_TAIL_SENTINEL)
    mock_client = _mock_client_gets(
        mock_client_cls,
        _response(
            [
                _comment(
                    "c-new",
                    "2026-05-07T18:44:00.000Z",
                    "@Rick ping worker /health",
                )
            ],
            has_more=False,
            next_cursor=None,
        ),
    )

    result = poll_comments(
        page_id=PAGE_ID,
        since="2026-05-07T18:40:00+00:00",
        limit=20,
        redis_client=redis_client,
    )

    assert result["count"] == 1
    assert result["comments"][0]["id"] == "c-new"
    assert result["comments"][0]["text"] == "@Rick ping worker /health"
    assert result["bootstrap"] is True
    assert result["cursor_used"] is False
    assert result["requests_count"] == 1
    assert mock_client.get.call_args.kwargs["params"] == {
        "block_id": PAGE_ID,
        "page_size": 20,
    }


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_poll_comments_bootstrap_multi_page_tail_skip_filters_old_pages(
    mock_require_notion_core,
    mock_client_cls,
):
    from worker.notion_client import _cursor_key, poll_comments

    redis_client = fakeredis.FakeRedis(decode_responses=True)
    mock_client = _mock_client_gets(
        mock_client_cls,
        _response(
            [_comment("c-old", "2026-05-07T17:00:00.000Z", "old")],
            has_more=True,
            next_cursor="cursor-2",
        ),
        _response(
            [_comment("c-new", "2026-05-07T18:44:00.000Z", "new")],
            has_more=False,
            next_cursor=None,
        ),
    )

    result = poll_comments(
        page_id=PAGE_ID,
        since="2026-05-07T18:00:00+00:00",
        limit=20,
        redis_client=redis_client,
    )

    assert result["count"] == 1
    assert [comment["id"] for comment in result["comments"]] == ["c-new"]
    assert result["bootstrap"] is True
    assert result["requests_count"] == 2
    assert [call.kwargs["params"] for call in mock_client.get.call_args_list] == [
        {"block_id": PAGE_ID, "page_size": 20},
        {"block_id": PAGE_ID, "page_size": 20, "start_cursor": "cursor-2"},
    ]
    assert redis_client.get(_cursor_key(PAGE_ID)) == "cursor-2"


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_poll_comments_bootstrap_no_perpetual_sentinel_zero_delivery(
    mock_require_notion_core,
    mock_client_cls,
):
    from worker.notion_client import CURSOR_TAIL_SENTINEL, _cursor_key, poll_comments

    redis_client = fakeredis.FakeRedis(decode_responses=True)
    redis_client.set(_cursor_key(PAGE_ID), CURSOR_TAIL_SENTINEL)
    _mock_client_gets(
        mock_client_cls,
        _response(
            [_comment("c-first", "2026-05-07T18:44:00.000Z", "first")],
            has_more=False,
            next_cursor=None,
        ),
        _response(
            [
                _comment("c-first", "2026-05-07T18:44:00.000Z", "first"),
                _comment("c-second", "2026-05-07T18:50:00.000Z", "second"),
            ],
            has_more=False,
            next_cursor=None,
        ),
    )

    first = poll_comments(
        page_id=PAGE_ID,
        since="2026-05-07T18:40:00+00:00",
        limit=20,
        redis_client=redis_client,
    )
    second = poll_comments(
        page_id=PAGE_ID,
        since="2026-05-07T18:44:00+00:00",
        limit=20,
        redis_client=redis_client,
    )

    assert first["count"] == 1
    assert first["comments"][0]["id"] == "c-first"
    assert redis_client.get(_cursor_key(PAGE_ID)) == CURSOR_TAIL_SENTINEL
    assert second["count"] == 1
    assert second["comments"][0]["id"] == "c-second"
    assert second["bootstrap"] is True
