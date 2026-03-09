from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.notion import handle_notion_read_database


@patch("worker.tasks.notion.notion_client.read_database")
def test_handle_notion_read_database_success(mock_read_database):
    mock_read_database.return_value = {
        "database_id": "2b45f443-fb5c-8154-8f22-de9978f2a039",
        "title": "Fuentes",
        "schema": {"Name": "title", "URL": "url"},
        "items": [{"title": "Gartner", "properties": {"URL": "https://www.gartner.com/"}}],
    }

    result = handle_notion_read_database(
        {
            "database_id_or_url": "https://www.notion.so/umbralbim/Fuentes-2b45f443fb5c81548f22de9978f2a039",
            "max_items": 25,
        }
    )

    assert result["title"] == "Fuentes"
    mock_read_database.assert_called_once_with(
        database_id_or_url="https://www.notion.so/umbralbim/Fuentes-2b45f443fb5c81548f22de9978f2a039",
        max_items=25,
        filter=None,
    )


def test_handle_notion_read_database_requires_database():
    with pytest.raises(ValueError, match="'database_id_or_url' is required"):
        handle_notion_read_database({})


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_read_database_returns_schema_and_items(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import read_database

    db_response = MagicMock()
    db_response.status_code = 200
    db_response.json.return_value = {
        "id": "2b45f443-fb5c-8154-8f22-de9978f2a039",
        "url": "https://www.notion.so/umbralbim/Fuentes-2b45f443fb5c81548f22de9978f2a039",
        "title": [{"plain_text": "Fuentes"}],
        "properties": {
            "Name": {"type": "title"},
            "URL": {"type": "url"},
            "Prioridad": {"type": "select"},
        },
    }
    query_response = MagicMock()
    query_response.status_code = 200
    query_response.json.return_value = {
        "results": [
            {
                "id": "page-1",
                "url": "https://www.notion.so/item-1",
                "properties": {
                    "Name": {"type": "title", "title": [{"plain_text": "Gartner"}]},
                    "URL": {"type": "url", "url": "https://www.gartner.com/"},
                    "Prioridad": {"type": "select", "select": {"name": "Alta"}},
                },
            }
        ],
        "has_more": False,
    }

    mock_client = MagicMock()
    mock_client.get.return_value = db_response
    mock_client.post.return_value = query_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = read_database(
        "https://www.notion.so/umbralbim/Fuentes-2b45f443fb5c81548f22de9978f2a039",
        max_items=20,
    )

    assert result["title"] == "Fuentes"
    assert result["database_id"] == "2b45f443-fb5c-8154-8f22-de9978f2a039"
    assert result["schema"] == {"Name": "title", "URL": "url", "Prioridad": "select"}
    assert result["count"] == 1
    assert result["items"][0]["title"] == "Gartner"
    assert result["items"][0]["properties"]["URL"] == "https://www.gartner.com/"
    assert result["items"][0]["properties"]["Prioridad"] == "Alta"
