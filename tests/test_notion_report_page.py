import pytest
from worker.tasks.notion import handle_notion_create_report_page
from worker.tasks.notion_markdown import markdown_to_blocks
from datetime import datetime, timezone

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


from unittest.mock import patch

@patch("worker.tasks.notion.notion_client.create_report_page")
def test_handle_notion_create_report_page_success(mock_create):
    mock_create.return_value = {"page_id": "test_page_123", "page_url": "https://notion.so/test", "ok": True}

    input_data = {
        "title": "Test Report",
        "content": "# Hello\nWorld",
        "sources": [{"title": "Google", "url": "https://google.com"}],
        "queries": ["what is ai"],
        "metadata": {"team": "alpha"}
    }

    result = handle_notion_create_report_page(input_data)
    
    assert result["page_id"] == "test_page_123"
    assert result["page_url"] == "https://notion.so/test"
    assert result["ok"] is True
    
    # Check that create_report_page was called correctly
    mock_create.assert_called_once()
    kwargs = mock_create.call_args.kwargs
    assert kwargs["title"] == "Test Report"
    assert len(kwargs["content_blocks"]) == 2
    assert kwargs["sources"] == input_data["sources"]
    assert kwargs["queries"] == input_data["queries"]
    assert kwargs["metadata"]["team"] == "alpha"
    assert "generated_at" in kwargs["metadata"]

def test_handle_notion_create_report_page_missing_inputs():
    with pytest.raises(ValueError, match="'title' is required"):
        handle_notion_create_report_page({"content": "hi"})
        
    with pytest.raises(ValueError, match="'content' is required"):
        handle_notion_create_report_page({"title": "hi"})
