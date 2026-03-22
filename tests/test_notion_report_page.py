from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from worker import notion_client
from worker.tasks.notion import handle_notion_create_report_page
from worker.tasks.notion_markdown import markdown_to_blocks


def test_markdown_to_blocks_basic():
    md = """# Main Title
This is a paragraph with **bold** text and a [link](https://example.com).

## Subtitle
- Item 1
- Item 2

---
1. First
2. Second
"""
    blocks = markdown_to_blocks(md)
    assert len(blocks) == 8
    assert blocks[0]["type"] == "heading_1"
    assert blocks[0]["heading_1"]["rich_text"][0]["text"]["content"] == "Main Title"

    assert blocks[1]["type"] == "paragraph"
    assert len(blocks[1]["paragraph"]["rich_text"]) == 5
    assert blocks[1]["paragraph"]["rich_text"][0]["text"]["content"] == "This is a paragraph with "
    assert blocks[1]["paragraph"]["rich_text"][1]["annotations"]["bold"] is True
    assert blocks[1]["paragraph"]["rich_text"][3]["text"]["link"]["url"] == "https://example.com"

    assert blocks[2]["type"] == "heading_2"
    assert blocks[3]["type"] == "bulleted_list_item"
    assert blocks[5]["type"] == "divider"
    assert blocks[6]["type"] == "numbered_list_item"


def test_markdown_to_blocks_long_paragraph():
    md = "A" * 2500
    blocks = markdown_to_blocks(md)
    assert len(blocks) == 2
    assert len(blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]) == 2000
    assert len(blocks[1]["paragraph"]["rich_text"][0]["text"]["content"]) == 500


@patch("worker.tasks.notion.notion_client.create_report_page")
def test_handle_notion_create_report_page_success(mock_create):
    mock_create.return_value = {"page_id": "test_page_123", "page_url": "https://notion.so/test", "ok": True}

    input_data = {
        "title": "Test Report",
        "content": "# Hello\nWorld",
        "icon": "📝",
        "sources": [{"title": "Google", "url": "https://google.com"}],
        "queries": ["what is ai"],
        "metadata": {"team": "alpha"},
    }

    result = handle_notion_create_report_page(input_data)

    assert result["page_id"] == "test_page_123"
    assert result["page_url"] == "https://notion.so/test"
    assert result["ok"] is True

    mock_create.assert_called_once()
    kwargs = mock_create.call_args.kwargs
    assert kwargs["title"] == "Test Report"
    assert len(kwargs["content_blocks"]) == 2
    assert kwargs["sources"] == input_data["sources"]
    assert kwargs["queries"] == input_data["queries"]
    assert kwargs["metadata"]["team"] == "alpha"
    assert kwargs["icon"] == "📝"
    assert "generated_at" in kwargs["metadata"]


@patch("worker.tasks.notion.notion_client.create_report_page")
@patch("worker.tasks.notion._resolve_project_context")
def test_handle_notion_create_report_page_infers_project_icon(mock_resolve_project_context, mock_create):
    mock_resolve_project_context.return_value = {"page_id": "project-page-1", "icon": "🎯"}
    mock_create.return_value = {"page_id": "test_page_123", "page_url": "https://notion.so/test", "ok": True}

    handle_notion_create_report_page(
        {
            "title": "Embudo analysis",
            "content": "# Hello\nWorld",
            "metadata": {"project_name": "Proyecto Embudo Ventas"},
        }
    )

    kwargs = mock_create.call_args.kwargs
    assert kwargs["icon"] == "🎯"


def test_handle_notion_create_report_page_missing_inputs():
    with pytest.raises(ValueError, match="'title' is required"):
        handle_notion_create_report_page({"content": "hi"})

    with pytest.raises(ValueError, match="'content' is required"):
        handle_notion_create_report_page({"title": "hi"})


def test_resolve_report_parent_page_id_uses_archive_for_automation(monkeypatch):
    monkeypatch.setattr(notion_client.config, "NOTION_REPORTS_ARCHIVE_PAGE_ID", "archive-page")
    monkeypatch.setattr(notion_client.config, "NOTION_CONTROL_ROOM_PAGE_ID", "control-room")

    assert notion_client._resolve_report_parent_page_id({"source": "smart_reply"}) == "archive-page"
    assert notion_client._resolve_report_parent_page_id({"source": "workflow_engine"}) == "archive-page"
    assert notion_client._resolve_report_parent_page_id({"source": "manual"}) == "control-room"


def test_resolve_report_parent_page_id_falls_back_to_control_room(monkeypatch):
    monkeypatch.setattr(notion_client.config, "NOTION_REPORTS_ARCHIVE_PAGE_ID", None)
    monkeypatch.setattr(notion_client.config, "NOTION_CONTROL_ROOM_PAGE_ID", "control-room")

    assert notion_client._resolve_report_parent_page_id({"source": "smart_reply"}) == "control-room"
