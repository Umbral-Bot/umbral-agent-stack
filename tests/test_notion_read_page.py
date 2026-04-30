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


@patch("worker.notion_client.httpx.Client")
@patch("worker.notion_client.config.require_notion_core")
@patch("worker.notion_client.config.NOTION_API_KEY", "ntn_test_key")
def test_read_page_paginates_and_preserves_blank_lines(mock_require_notion_core, mock_client_cls):
    from worker.notion_client import read_page

    page_response = MagicMock()
    page_response.status_code = 200
    page_id = "1dbd6874-90a9-4ba2-9b19-f0daec70c68e"
    page_response.json.return_value = {
        "id": page_id,
        "url": "https://www.notion.so/Granola-1dbd687490a94ba29b19f0daec70c68e",
        "last_edited_time": "2026-03-08T16:23:00.000Z",
        "properties": {
            "title": {
                "type": "title",
                "title": [{"plain_text": "Granola"}],
            }
        },
    }
    blocks_response_1 = MagicMock()
    blocks_response_1.status_code = 200
    blocks_response_1.json.return_value = {
        "results": [
            {
                "id": "block-1",
                "type": "paragraph",
                "has_children": False,
                "last_edited_time": "2026-03-08T16:23:00.000Z",
                "paragraph": {"rich_text": [{"plain_text": "Meeting Title: ACI Autodesk"}]},
            },
            {
                "id": "block-2",
                "type": "paragraph",
                "has_children": False,
                "last_edited_time": "2026-03-08T16:23:00.000Z",
                "paragraph": {"rich_text": []},
            },
        ],
        "has_more": True,
        "next_cursor": "cursor-1",
    }
    blocks_response_2 = MagicMock()
    blocks_response_2.status_code = 200
    blocks_response_2.json.return_value = {
        "results": [
            {
                "id": "block-3",
                "type": "paragraph",
                "has_children": False,
                "last_edited_time": "2026-03-08T16:23:00.000Z",
                "paragraph": {"rich_text": [{"plain_text": "Transcript:"}]},
            },
        ],
        "has_more": False,
        "next_cursor": None,
    }

    mock_client = MagicMock()
    mock_client.get.side_effect = [page_response, blocks_response_1, blocks_response_2]
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = read_page(page_id, max_blocks=10)

    assert result["plain_text"] == "Meeting Title: ACI Autodesk\n\nTranscript:"
    assert result["has_more"] is False
    assert mock_client.get.call_count == 3


@patch("worker.notion_client.read_page")
@patch("worker.notion_client.get_page")
def test_get_page_snapshot_merges_properties_and_body(mock_get_page, mock_read_page):
    from worker.notion_client import get_page_snapshot

    mock_get_page.return_value = {
        "id": "page-123",
        "url": "https://notion.so/page-123",
        "last_edited_time": "2026-04-03T10:00:00.000Z",
        "icon": {"type": "emoji", "emoji": "📝"},
        "properties": {
            "Nombre": {"type": "title", "title": [{"plain_text": "Sesion A"}]},
            "Estado agente": {"type": "select", "select": {"name": "Pendiente"}},
            "Fecha": {"type": "date", "date": {"start": "2026-04-03"}},
        },
    }
    mock_read_page.return_value = {
        "page_id": "page-123",
        "url": "https://notion.so/page-123",
        "title": "Sesion A",
        "plain_text": "Transcript completo",
        "blocks": [{"type": "paragraph", "text": "Transcript completo"}],
        "has_more": False,
        "max_blocks": 10_000,
    }

    result = get_page_snapshot("page-123")

    assert result["page_id"] == "page-123"
    assert result["title"] == "Sesion A"
    assert result["properties"]["Estado agente"] == "Pendiente"
    assert result["properties"]["Fecha"] == {"start": "2026-04-03"}
    assert result["plain_text"] == "Transcript completo"
    assert result["properties_raw"]["Nombre"]["type"] == "title"
