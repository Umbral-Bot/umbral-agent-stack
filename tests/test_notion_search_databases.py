from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.notion import handle_notion_search_databases


@patch("worker.tasks.notion.notion_client.search_databases")
def test_handle_notion_search_databases_success(mock_search_databases):
    mock_search_databases.return_value = {
        "query": "Fuentes confiables",
        "results": [{"database_id": "db-1", "title": "Fuentes confiables"}],
        "count": 1,
    }

    result = handle_notion_search_databases({"query": "Fuentes confiables", "max_results": 5})

    assert result["count"] == 1
    mock_search_databases.assert_called_once_with(query="Fuentes confiables", max_results=5)


def test_handle_notion_search_databases_requires_query():
    with pytest.raises(ValueError, match="'query' is required"):
        handle_notion_search_databases({})


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_search_databases_returns_matches(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import search_databases

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "results": [
            {
                "id": "db-1",
                "url": "https://www.notion.so/db-1",
                "last_edited_time": "2026-03-09T08:00:00.000Z",
                "title": [{"plain_text": "Fuentes confiables"}],
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.post.return_value = response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = search_databases("Fuentes confiables", max_results=5)

    assert result["query"] == "Fuentes confiables"
    assert result["count"] == 1
    assert result["results"][0]["database_id"] == "db-1"
    assert result["results"][0]["title"] == "Fuentes confiables"
