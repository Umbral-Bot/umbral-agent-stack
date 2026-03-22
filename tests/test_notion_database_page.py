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
            "icon": "📁",
        }
    )

    assert result["created"] is True
    mock_create_database_page.assert_called_once_with(
        database_id_or_url="https://www.notion.so/3c1112c327cd445f848f041c4f8449c2",
        properties={"Nombre": {"title": [{"text": {"content": "Proyecto Embudo Ventas"}}]}},
        children=None,
        icon="📁",
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
            "icon": "📝",
        }
    )

    assert result["updated"] is True
    mock_update_page_properties.assert_called_once_with(
        page_id_or_url="https://www.notion.so/page-1",
        properties={"Estado": {"status": {"name": "En curso"}}},
        icon="📝",
        archived=None,
    )


def test_handle_notion_update_page_properties_requires_inputs():
    with pytest.raises(ValueError, match="'page_id_or_url' is required"):
        handle_notion_update_page_properties({"properties": {"foo": "bar"}})

    with pytest.raises(ValueError, match="'properties', 'icon' or 'archived' must be provided"):
        handle_notion_update_page_properties({"page_id_or_url": "page-1"})


@patch("worker.tasks.notion.notion_client.update_page_properties")
def test_handle_notion_update_page_properties_allows_archived_only(mock_update_page_properties):
    mock_update_page_properties.return_value = {
        "page_id": "page-1",
        "url": "https://www.notion.so/page-1",
        "updated": True,
    }

    result = handle_notion_update_page_properties(
        {
            "page_id_or_url": "https://www.notion.so/page-1",
            "archived": True,
        }
    )

    assert result["updated"] is True
    mock_update_page_properties.assert_called_once_with(
        page_id_or_url="https://www.notion.so/page-1",
        properties={},
        icon=None,
        archived=True,
    )


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
        icon="📁",
    )

    assert result["created"] is True
    assert result["page_id"] == "page-1"
    mock_client.post.assert_called_once()
    assert mock_client.post.call_args.kwargs["json"]["icon"] == {"type": "emoji", "emoji": "📁"}


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
        icon="📝",
    )

    assert result["updated"] is True
    assert result["page_id"] == "page-1"
    mock_client.patch.assert_called_once()
    assert mock_client.patch.call_args.kwargs["json"]["icon"] == {"type": "emoji", "emoji": "📝"}


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_update_page_properties_allows_icon_only(mock_require_notion_core, mock_client_cls):
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
        {},
        icon="🧭",
    )

    assert result["updated"] is True
    assert mock_client.patch.call_args.kwargs["json"] == {
        "icon": {"type": "emoji", "emoji": "🧭"}
    }


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_update_page_properties_allows_archive_only(mock_require_notion_core, mock_client_cls):
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
        {},
        archived=True,
    )

    assert result["updated"] is True
    assert mock_client.patch.call_args.kwargs["json"] == {"archived": True}


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_create_database_page_retries_without_invalid_icon(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import create_database_page

    invalid_response = MagicMock()
    invalid_response.status_code = 400
    invalid_response.text = "{\"object\":\"error\",\"status\":400,\"code\":\"validation_error\",\"message\":\"body.icon.emoji should be valid\"}"
    invalid_response.json.return_value = {
        "object": "error",
        "status": 400,
        "code": "validation_error",
        "message": "body.icon.emoji should be valid",
    }

    create_response = MagicMock()
    create_response.status_code = 200
    create_response.json.return_value = {
        "id": "page-1",
        "url": "https://www.notion.so/page-1",
    }

    mock_client = MagicMock()
    mock_client.post.side_effect = [invalid_response, create_response]
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = create_database_page(
        "https://www.notion.so/3c1112c327cd445f848f041c4f8449c2",
        {"Nombre": {"title": [{"text": {"content": "Proyecto Embudo Ventas"}}]}},
        icon="📮",
    )

    assert result["created"] is True
    assert mock_client.post.call_count == 2
    assert "icon" not in mock_client.post.call_args_list[1].kwargs["json"]


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_update_page_properties_retries_without_invalid_icon(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import update_page_properties

    invalid_response = MagicMock()
    invalid_response.status_code = 400
    invalid_response.text = "{\"object\":\"error\",\"status\":400,\"code\":\"validation_error\",\"message\":\"body.icon.emoji should be valid\"}"
    invalid_response.json.return_value = {
        "object": "error",
        "status": 400,
        "code": "validation_error",
        "message": "body.icon.emoji should be valid",
    }

    update_response = MagicMock()
    update_response.status_code = 200
    update_response.json.return_value = {
        "id": "page-1",
        "url": "https://www.notion.so/page-1",
    }

    mock_client = MagicMock()
    mock_client.patch.side_effect = [invalid_response, update_response]
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = update_page_properties(
        "https://www.notion.so/31e5f443fb5c81eb8949e8c59f497d42",
        {"Estado": {"status": {"name": "En curso"}}},
        icon="📮",
    )

    assert result["updated"] is True
    assert mock_client.patch.call_count == 2
    assert "icon" not in mock_client.patch.call_args_list[1].kwargs["json"]
