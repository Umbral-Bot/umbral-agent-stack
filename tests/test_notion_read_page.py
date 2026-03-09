import os
from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.notion import handle_notion_read_page


@patch("worker.tasks.notion.notion_client.read_page")
def test_handle_notion_read_page_success(mock_read_page):
    mock_read_page.return_value = {
        "page_id": "1dbd6874-90a9-4ba2-9b19-f0daec70c68e",
        "title": "Perfil David Moreira",
        "blocks": [{"type": "paragraph", "text": "Resumen"}],
        "plain_text": "Resumen",
    }

    result = handle_notion_read_page(
        {
            "page_id_or_url": "https://www.notion.so/Perfil-David-Moreira-1dbd687490a94ba29b19f0daec70c68e",
            "max_blocks": 25,
        }
    )

    assert result["title"] == "Perfil David Moreira"
    mock_read_page.assert_called_once_with(
        page_id_or_url="https://www.notion.so/Perfil-David-Moreira-1dbd687490a94ba29b19f0daec70c68e",
        max_blocks=25,
    )


def test_handle_notion_read_page_requires_page():
    with pytest.raises(ValueError, match="'page_id_or_url' is required"):
        handle_notion_read_page({})


def test_extract_notion_page_id_from_url():
    from worker.notion_client import _extract_notion_page_id

    result = _extract_notion_page_id(
        "https://www.notion.so/Perfil-David-Moreira-1dbd687490a94ba29b19f0daec70c68e"
    )

    assert result == "1dbd6874-90a9-4ba2-9b19-f0daec70c68e"


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_read_page_returns_metadata_and_plain_text(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import read_page

    page_response = MagicMock()
    page_response.status_code = 200
    page_response.json.return_value = {
        "id": "1dbd6874-90a9-4ba2-9b19-f0daec70c68e",
        "url": "https://www.notion.so/Perfil-David-Moreira-1dbd687490a94ba29b19f0daec70c68e",
        "last_edited_time": "2026-03-08T16:23:00.000Z",
        "properties": {
            "title": {
                "type": "title",
                "title": [{"plain_text": "Perfil David Moreira"}],
            }
        },
    }
    blocks_response = MagicMock()
    blocks_response.status_code = 200
    blocks_response.json.return_value = {
        "results": [
            {
                "id": "block-1",
                "type": "heading_2",
                "has_children": False,
                "last_edited_time": "2026-03-08T16:23:00.000Z",
                "heading_2": {"rich_text": [{"plain_text": "Resumen Ejecutivo"}]},
            },
            {
                "id": "block-2",
                "type": "paragraph",
                "has_children": False,
                "last_edited_time": "2026-03-08T16:23:00.000Z",
                "paragraph": {"rich_text": [{"plain_text": "David es arquitecto UTFSM"}]},
            },
        ],
        "has_more": False,
    }

    mock_client = MagicMock()
    mock_client.get.side_effect = [page_response, blocks_response]
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = read_page(
        "https://www.notion.so/Perfil-David-Moreira-1dbd687490a94ba29b19f0daec70c68e",
        max_blocks=20,
    )

    assert result["title"] == "Perfil David Moreira"
    assert result["page_id"] == "1dbd6874-90a9-4ba2-9b19-f0daec70c68e"
    assert "Resumen Ejecutivo" in result["plain_text"]
    assert "David es arquitecto UTFSM" in result["plain_text"]
    assert len(result["blocks"]) == 2
