"""Tests for notion.enrich_bitacora_page handler."""

import pytest
from unittest.mock import patch

try:
    from worker.tasks.notion import (
        handle_notion_enrich_bitacora_page,
        _sections_to_blocks,
        _raw_blocks_to_notion,
    )
except ImportError:
    pytest.skip(
        "notion.enrich_bitacora_page handler is not available in this branch",
        allow_module_level=True,
    )


class TestSectionsToBlocks:
    def test_basic_section_with_content(self):
        sections = [{"title": "Resumen", "content": "Párrafo uno.\n\nPárrafo dos."}]
        blocks = _sections_to_blocks(sections)
        types = [b["type"] for b in blocks]
        assert "heading_2" in types
        assert types.count("paragraph") == 2
        assert blocks[0]["heading_2"]["rich_text"][0]["text"]["content"] == "Resumen"

    def test_section_with_mermaid(self):
        sections = [{"title": "Diagrama", "mermaid": "graph TD\n  A-->B"}]
        blocks = _sections_to_blocks(sections)
        code_blocks = [b for b in blocks if b["type"] == "code"]
        assert len(code_blocks) == 1
        assert code_blocks[0]["code"]["language"] == "mermaid"
        assert "A-->B" in code_blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_section_with_items(self):
        sections = [{"title": "Archivos", "items": ["file1.py", "file2.md"]}]
        blocks = _sections_to_blocks(sections)
        bullets = [b for b in blocks if b["type"] == "bulleted_list_item"]
        assert len(bullets) == 2

    def test_section_with_table(self):
        sections = [{"title": "Datos", "table": {"headers": ["A", "B"], "rows": [["1", "2"]]}}]
        blocks = _sections_to_blocks(sections)
        tables = [b for b in blocks if b["type"] == "table"]
        assert len(tables) == 1

    def test_empty_title(self):
        sections = [{"content": "Solo contenido sin título."}]
        blocks = _sections_to_blocks(sections)
        headings = [b for b in blocks if b["type"] == "heading_2"]
        assert len(headings) == 0

    def test_divider_after_each_section(self):
        sections = [{"title": "A", "content": "x"}, {"title": "B", "content": "y"}]
        blocks = _sections_to_blocks(sections)
        dividers = [b for b in blocks if b["type"] == "divider"]
        assert len(dividers) == 2


class TestRawBlocksToNotion:
    def test_heading_types(self):
        raw = [
            {"type": "heading_1", "text": "H1"},
            {"type": "heading_2", "text": "H2"},
            {"type": "heading_3", "text": "H3"},
        ]
        blocks = _raw_blocks_to_notion(raw)
        assert blocks[0]["type"] == "heading_1"
        assert blocks[1]["type"] == "heading_2"
        assert blocks[2]["type"] == "heading_3"

    def test_code_block(self):
        raw = [{"type": "code", "language": "mermaid", "text": "graph TD\n  A-->B"}]
        blocks = _raw_blocks_to_notion(raw)
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "mermaid"

    def test_paragraph(self):
        raw = [{"type": "paragraph", "text": "Hola mundo"}]
        blocks = _raw_blocks_to_notion(raw)
        assert blocks[0]["type"] == "paragraph"
        assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == "Hola mundo"

    def test_bulleted_list(self):
        raw = [{"type": "bulleted_list_item", "text": "Item 1"}]
        blocks = _raw_blocks_to_notion(raw)
        assert blocks[0]["type"] == "bulleted_list_item"

    def test_divider(self):
        raw = [{"type": "divider"}]
        blocks = _raw_blocks_to_notion(raw)
        assert blocks[0]["type"] == "divider"

    def test_callout(self):
        raw = [{"type": "callout", "text": "Nota", "emoji": "⚠️"}]
        blocks = _raw_blocks_to_notion(raw)
        assert blocks[0]["type"] == "callout"

    def test_quote(self):
        raw = [{"type": "quote", "text": "Cita textual"}]
        blocks = _raw_blocks_to_notion(raw)
        assert blocks[0]["type"] == "quote"

    def test_table(self):
        raw = [{"type": "table", "rows": [["Col1", "Col2"], ["a", "b"]]}]
        blocks = _raw_blocks_to_notion(raw)
        assert blocks[0]["type"] == "table"

    def test_unknown_type_defaults_to_paragraph(self):
        raw = [{"type": "unknown_block", "text": "Fallback"}]
        blocks = _raw_blocks_to_notion(raw)
        assert blocks[0]["type"] == "paragraph"


class TestHandlerEnrichBitacora:
    @patch("worker.tasks.notion.notion_client.append_blocks_to_page")
    def test_with_sections(self, mock_append):
        mock_append.return_value = {"blocks_appended": 5, "page_id": "page-123"}

        input_data = {
            "page_id": "page-123",
            "sections": [
                {"title": "Resumen", "content": "Contenido de prueba."},
                {"title": "Diagrama", "mermaid": "graph TD\n  A-->B"},
            ],
        }
        result = handle_notion_enrich_bitacora_page(input_data)

        assert result["page_id"] == "page-123"
        assert result["blocks_appended"] == 5
        mock_append.assert_called_once()
        blocks = mock_append.call_args.kwargs.get("blocks") or mock_append.call_args[1].get("blocks") or mock_append.call_args[0][1]
        assert len(blocks) > 0

    @patch("worker.tasks.notion.notion_client.append_blocks_to_page")
    def test_with_blocks(self, mock_append):
        mock_append.return_value = {"blocks_appended": 3, "page_id": "page-456"}

        input_data = {
            "page_id": "page-456",
            "blocks": [
                {"type": "heading_2", "text": "Resumen"},
                {"type": "paragraph", "text": "Descripción."},
                {"type": "code", "language": "mermaid", "text": "graph TD\n  A-->B"},
            ],
        }
        result = handle_notion_enrich_bitacora_page(input_data)

        assert result["page_id"] == "page-456"
        mock_append.assert_called_once()

    def test_missing_page_id(self):
        with pytest.raises(ValueError, match="page_id"):
            handle_notion_enrich_bitacora_page({"sections": []})

    def test_missing_blocks_and_sections(self):
        with pytest.raises(ValueError, match="blocks.*sections"):
            handle_notion_enrich_bitacora_page({"page_id": "page-789"})


class TestNotionClientBlockCode:
    def test_block_code_mermaid(self):
        from worker.notion_client import _block_code
        block = _block_code("graph TD\n  A-->B", "mermaid")
        assert block["type"] == "code"
        assert block["code"]["language"] == "mermaid"
        assert block["code"]["rich_text"][0]["text"]["content"] == "graph TD\n  A-->B"

    def test_block_code_default_language(self):
        from worker.notion_client import _block_code
        block = _block_code("print('hello')")
        assert block["code"]["language"] == "plain text"

    def test_block_code_truncation(self):
        from worker.notion_client import _block_code
        block = _block_code("x" * 3000, "python")
        assert len(block["code"]["rich_text"][0]["text"]["content"]) == 2000


class TestNotionClientQueryDatabase:
    @patch("worker.notion_client.httpx.Client")
    def test_query_database_basic(self, mock_client_cls):
        import worker.config as cfg
        original = cfg.NOTION_API_KEY
        cfg.NOTION_API_KEY = "test-key"

        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_resp = type("Resp", (), {
            "status_code": 200,
            "json": lambda self: {"results": [{"id": "p1"}, {"id": "p2"}], "next_cursor": None},
            "text": "",
        })()
        mock_client.post.return_value = mock_resp

        from worker.notion_client import query_database
        results = query_database("db-123")
        assert len(results) == 2
        assert results[0]["id"] == "p1"

        cfg.NOTION_API_KEY = original

    @patch("worker.notion_client.httpx.Client")
    def test_query_database_pagination(self, mock_client_cls):
        import worker.config as cfg
        original = cfg.NOTION_API_KEY
        cfg.NOTION_API_KEY = "test-key"

        mock_client = mock_client_cls.return_value.__enter__.return_value
        page1 = type("Resp", (), {
            "status_code": 200,
            "json": lambda self: {"results": [{"id": "p1"}], "next_cursor": "cur1"},
            "text": "",
        })()
        page2 = type("Resp", (), {
            "status_code": 200,
            "json": lambda self: {"results": [{"id": "p2"}], "next_cursor": None},
            "text": "",
        })()
        mock_client.post.side_effect = [page1, page2]

        from worker.notion_client import query_database
        results = query_database("db-456")
        assert len(results) == 2
        assert mock_client.post.call_count == 2

        cfg.NOTION_API_KEY = original

    def test_query_database_no_api_key(self):
        import worker.config as cfg
        original = cfg.NOTION_API_KEY
        cfg.NOTION_API_KEY = None

        from worker.notion_client import query_database
        with pytest.raises(RuntimeError, match="NOTION_API_KEY"):
            query_database("db-789")

        cfg.NOTION_API_KEY = original


class TestAppendBlocksToPage:
    @patch("worker.notion_client.httpx.Client")
    def test_append_blocks_basic(self, mock_client_cls):
        import worker.config as cfg
        original = cfg.NOTION_API_KEY
        cfg.NOTION_API_KEY = "test-key"

        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_resp = type("Resp", (), {
            "status_code": 200,
            "json": lambda self: {"results": []},
            "text": "",
        })()
        mock_client.patch.return_value = mock_resp

        from worker.notion_client import append_blocks_to_page, _block_paragraph
        blocks = [_block_paragraph("Test")]
        result = append_blocks_to_page("page-123", blocks)
        assert result["blocks_appended"] == 1
        assert result["page_id"] == "page-123"

        cfg.NOTION_API_KEY = original

    def test_append_blocks_no_api_key(self):
        import worker.config as cfg
        original = cfg.NOTION_API_KEY
        cfg.NOTION_API_KEY = None

        from worker.notion_client import append_blocks_to_page
        with pytest.raises(RuntimeError, match="NOTION_API_KEY"):
            append_blocks_to_page("page-123", [])

        cfg.NOTION_API_KEY = original


class TestPrependBlocksToPage:
    @patch("worker.notion_client.httpx.Client")
    def test_prepend_deletes_old_and_writes_new_first(self, mock_client_cls):
        import worker.config as cfg
        original = cfg.NOTION_API_KEY
        cfg.NOTION_API_KEY = "test-key"

        mock_client = mock_client_cls.return_value.__enter__.return_value

        existing_blocks = [
            {"id": "old-1", "type": "paragraph", "has_children": False,
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Old"}, "plain_text": "Old"}], "color": "default"}},
            {"id": "old-2", "type": "divider", "has_children": False, "divider": {}},
        ]

        get_resp = type("Resp", (), {
            "status_code": 200,
            "json": lambda self: {"results": existing_blocks, "next_cursor": None},
            "text": "",
        })()
        ok_resp = type("Resp", (), {
            "status_code": 200,
            "json": lambda self: {"results": []},
            "text": "",
        })()

        mock_client.get.return_value = get_resp
        mock_client.patch.return_value = ok_resp

        from worker.notion_client import prepend_blocks_to_page, _block_heading2
        new_blocks = [_block_heading2("En pocas palabras")]
        result = prepend_blocks_to_page("page-abc", new_blocks)

        assert result["blocks_prepended"] == 1
        assert result["blocks_preserved"] == 2
        assert result["page_id"] == "page-abc"

        patch_calls = mock_client.patch.call_args_list
        delete_calls = [c for c in patch_calls if "in_trash" in str(c)]
        assert len(delete_calls) == 2

        append_call = patch_calls[-1]
        children = append_call.kwargs.get("json", {}).get("children", [])
        assert len(children) == 3
        assert children[0]["type"] == "heading_2"
        assert children[1]["type"] == "paragraph"
        assert children[2]["type"] == "divider"

        cfg.NOTION_API_KEY = original

    def test_prepend_no_api_key(self):
        import worker.config as cfg
        original = cfg.NOTION_API_KEY
        cfg.NOTION_API_KEY = None

        from worker.notion_client import prepend_blocks_to_page
        with pytest.raises(RuntimeError, match="NOTION_API_KEY"):
            prepend_blocks_to_page("page-123", [])

        cfg.NOTION_API_KEY = original


class TestConvertBlockForWrite:
    def test_simple_paragraph(self):
        from worker.notion_client import _convert_block_for_write
        block = {
            "id": "x", "type": "paragraph", "has_children": False,
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Hello"}}], "color": "default"},
        }
        result = _convert_block_for_write(block, None)
        assert result["type"] == "paragraph"
        assert "id" not in result
        assert result["paragraph"]["rich_text"][0]["text"]["content"] == "Hello"

    def test_divider(self):
        from worker.notion_client import _convert_block_for_write
        block = {"id": "x", "type": "divider", "has_children": False, "divider": {}}
        result = _convert_block_for_write(block, None)
        assert result["type"] == "divider"
        assert result["divider"] == {}

    def test_code_block(self):
        from worker.notion_client import _convert_block_for_write
        block = {
            "id": "x", "type": "code", "has_children": False,
            "code": {"rich_text": [{"type": "text", "text": {"content": "graph TD"}}], "language": "mermaid"},
        }
        result = _convert_block_for_write(block, None)
        assert result["type"] == "code"
        assert result["code"]["language"] == "mermaid"

    def test_callout(self):
        from worker.notion_client import _convert_block_for_write
        block = {
            "id": "x", "type": "callout", "has_children": False,
            "callout": {"rich_text": [{"type": "text", "text": {"content": "Note"}}], "icon": {"type": "emoji", "emoji": "💡"}, "color": "default"},
        }
        result = _convert_block_for_write(block, None)
        assert result["type"] == "callout"
        assert result["callout"]["icon"]["emoji"] == "💡"

    def test_unsupported_type_returns_none(self):
        from worker.notion_client import _convert_block_for_write
        block = {"id": "x", "type": "child_database", "has_children": False}
        result = _convert_block_for_write(block, None)
        assert result is None
