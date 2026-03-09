from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.notion import (
    handle_notion_create_database_page,
    handle_notion_update_page_properties,
)


@patch("worker.tasks.notion.notion_client.create_database_page")
def test_handle_notion_create_database_page_success(mock_create_database_page):
    mock_create_database_page.return_value = {
        "page_id": "page-1",
        "url": "https://www.notion.so/page-1",
        "created": True,
    }

    result = handle_notion_create_database_page(
        {
            "database_id_or_url": "https://www.notion.so/3c1112c327cd445f848f041c4f8449c2",
            "properties": {"Nombre": {"title": [{"text": {"content": "Proyecto Embudo Ventas"}}]}},
        }
    )

    assert result["created"] is True
    mock_create_database_page.assert_called_once_with(
        database_id_or_url="https://www.notion.so/3c1112c327cd445f848f041c4f8449c2",
        properties={"Nombre": {"title": [{"text": {"content": "Proyecto Embudo Ventas"}}]}},
        children=None,
    )


def test_handle_notion_create_database_page_requires_inputs():
    with pytest.raises(ValueError, match="'database_id_or_url' is required"):
        handle_notion_create_database_page({"properties": {"foo": "bar"}})

    with pytest.raises(ValueError, match="'properties' must be a non-empty object"):
        handle_notion_create_database_page({"database_id_or_url": "db-1"})


@patch("worker.tasks.notion.notion_client.update_page_properties")
def test_handle_notion_update_page_properties_success(mock_update_page_properties):
    mock_update_page_properties.return_value = {
        "page_id": "page-1",
        "url": "https://www.notion.so/page-1",
        "updated": True,
    }

    result = handle_notion_update_page_properties(
        {
            "page_id_or_url": "https://www.notion.so/page-1",
            "properties": {"Estado": {"status": {"name": "En curso"}}},
        }
    )

    assert result["updated"] is True
    mock_update_page_properties.assert_called_once_with(
        page_id_or_url="https://www.notion.so/page-1",
        properties={"Estado": {"status": {"name": "En curso"}}},
    )


def test_handle_notion_update_page_properties_requires_inputs():
    with pytest.raises(ValueError, match="'page_id_or_url' is required"):
        handle_notion_update_page_properties({"properties": {"foo": "bar"}})

    with pytest.raises(ValueError, match="'properties' must be a non-empty object"):
        handle_notion_update_page_properties({"page_id_or_url": "page-1"})


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_create_database_page_posts_to_notion(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import create_database_page

    create_response = MagicMock()
    create_response.status_code = 200
    create_response.json.return_value = {
        "id": "page-1",
        "url": "https://www.notion.so/page-1",
    }

    mock_client = MagicMock()
    mock_client.post.return_value = create_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = create_database_page(
        "https://www.notion.so/3c1112c327cd445f848f041c4f8449c2",
        {"Nombre": {"title": [{"text": {"content": "Proyecto Embudo Ventas"}}]}},
    )

    assert result["created"] is True
    assert result["page_id"] == "page-1"
    mock_client.post.assert_called_once()


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_update_page_properties_patches_notion(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import update_page_properties

    update_response = MagicMock()
    update_response.status_code = 200
    update_response.json.return_value = {
        "id": "page-1",
        "url": "https://www.notion.so/page-1",
    }

    mock_client = MagicMock()
    mock_client.patch.return_value = update_response
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = update_page_properties(
        "https://www.notion.so/31e5f443fb5c81eb8949e8c59f497d42",
        {"Estado": {"status": {"name": "En curso"}}},
    )

    assert result["updated"] is True
    assert result["page_id"] == "page-1"
    mock_client.patch.assert_called_once()
