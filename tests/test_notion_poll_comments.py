from unittest.mock import MagicMock, patch


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_poll_comments_paginates_until_it_finds_unseen_comments(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import poll_comments

    page_1 = MagicMock()
    page_1.status_code = 200
    page_1.json.return_value = {
        "results": [
            {
                "id": "c-old-1",
                "created_time": "2026-03-04T06:00:00.000Z",
                "created_by": {"id": "u-old"},
                "rich_text": [{"plain_text": "old 1"}],
            },
            {
                "id": "c-old-2",
                "created_time": "2026-03-04T06:30:00.000Z",
                "created_by": {"id": "u-old"},
                "rich_text": [{"plain_text": "old 2"}],
            },
        ],
        "has_more": True,
        "next_cursor": "cursor-2",
    }
    page_2 = MagicMock()
    page_2.status_code = 200
    page_2.json.return_value = {
        "results": [
            {
                "id": "c-new-1",
                "created_time": "2026-03-16T22:48:00.000Z",
                "created_by": {"id": "u-new"},
                "rich_text": [{"plain_text": "new 1"}],
            },
            {
                "id": "c-new-2",
                "created_time": "2026-03-16T22:49:00.000Z",
                "created_by": {"id": "u-new"},
                "rich_text": [{"plain_text": "new 2"}],
            },
        ],
        "has_more": False,
    }

    mock_client = MagicMock()
    mock_client.get.side_effect = [page_1, page_2]
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = poll_comments(
        page_id="page-123",
        since="2026-03-04T06:37:55.219422+00:00",
        limit=20,
    )

    assert result["count"] == 2
    assert [c["id"] for c in result["comments"]] == ["c-new-1", "c-new-2"]
    assert mock_client.get.call_count == 2
    first_params = mock_client.get.call_args_list[0].kwargs["params"]
    second_params = mock_client.get.call_args_list[1].kwargs["params"]
    assert first_params == {"block_id": "page-123", "page_size": 20}
    assert second_params == {
        "block_id": "page-123",
        "page_size": 20,
        "start_cursor": "cursor-2",
    }


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_poll_comments_compares_iso_datetimes_by_value_not_string(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import poll_comments

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "results": [
            {
                "id": "equal",
                "created_time": "2026-03-05T10:00:00.000Z",
                "created_by": {"id": "u-1"},
                "rich_text": [{"plain_text": "equal"}],
            },
            {
                "id": "later",
                "created_time": "2026-03-05T10:00:01.000Z",
                "created_by": {"id": "u-2"},
                "rich_text": [{"plain_text": "later"}],
            },
        ],
        "has_more": False,
    }

    mock_client = MagicMock()
    mock_client.get.return_value = response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = poll_comments(
        page_id="page-123",
        since="2026-03-05T10:00:00+00:00",
        limit=20,
    )

    assert result["count"] == 1
    assert result["comments"][0]["id"] == "later"


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_poll_comments_returns_oldest_unseen_first_when_limited(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import poll_comments

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "results": [
            {
                "id": "c-3",
                "created_time": "2026-03-06T10:00:03.000Z",
                "created_by": {"id": "u"},
                "rich_text": [{"plain_text": "3"}],
            },
            {
                "id": "c-1",
                "created_time": "2026-03-06T10:00:01.000Z",
                "created_by": {"id": "u"},
                "rich_text": [{"plain_text": "1"}],
            },
            {
                "id": "c-2",
                "created_time": "2026-03-06T10:00:02.000Z",
                "created_by": {"id": "u"},
                "rich_text": [{"plain_text": "2"}],
            },
        ],
        "has_more": False,
    }

    mock_client = MagicMock()
    mock_client.get.return_value = response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = poll_comments(
        page_id="page-123",
        since="2026-03-06T10:00:00+00:00",
        limit=2,
    )

    assert [c["id"] for c in result["comments"]] == ["c-1", "c-2"]
