"""Unit tests for ``scripts.discovery.html_to_notion_blocks``."""

from __future__ import annotations

import pytest

from scripts.discovery.html_to_notion_blocks import (
    MAX_BLOCKS,
    MAX_RICH_TEXT_LEN,
    TRUNC_NOTICE,
    fallback_no_body_block,
    html_to_notion_blocks,
)


def _block_text(block: dict) -> str:
    key = block["type"]
    rt = block[key].get("rich_text", [])
    return "".join(seg.get("text", {}).get("content", "") for seg in rt)


class TestHtmlToNotionBlocks:
    def test_empty_returns_empty_list(self):
        assert html_to_notion_blocks(None) == []
        assert html_to_notion_blocks("") == []
        assert html_to_notion_blocks("   ") == []

    def test_paragraph(self):
        out = html_to_notion_blocks("<p>Hola mundo</p>")
        assert len(out) == 1
        assert out[0]["type"] == "paragraph"
        assert _block_text(out[0]) == "Hola mundo"

    def test_headings(self):
        html = "<h1>Uno</h1><h2>Dos</h2><h3>Tres</h3><h4>Cuatro</h4>"
        out = html_to_notion_blocks(html)
        types = [b["type"] for b in out]
        assert "heading_1" in types
        assert "heading_2" in types
        assert "heading_3" in types
        # h4 falls back to heading_3 (cap).
        assert types.count("heading_3") >= 1

    def test_bulleted_list(self):
        out = html_to_notion_blocks("<ul><li>uno</li><li>dos</li></ul>")
        bullets = [b for b in out if b["type"] == "bulleted_list_item"]
        assert len(bullets) == 2

    def test_numbered_list(self):
        out = html_to_notion_blocks("<ol><li>a</li><li>b</li><li>c</li></ol>")
        nums = [b for b in out if b["type"] == "numbered_list_item"]
        assert len(nums) == 3

    def test_link_inside_paragraph(self):
        out = html_to_notion_blocks('<p>Mira <a href="https://x.test/y">acá</a> ahora.</p>')
        assert len(out) == 1
        rt = out[0]["paragraph"]["rich_text"]
        joined = "".join(s["text"]["content"] for s in rt)
        assert "Mira" in joined and "acá" in joined and "ahora" in joined
        link_segs = [s for s in rt if s["text"].get("link")]
        assert link_segs, "expected at least one link segment"
        assert link_segs[0]["text"]["link"]["url"] == "https://x.test/y"

    def test_standalone_image(self):
        out = html_to_notion_blocks('<p><img src="https://x.test/a.png" alt="foto"/></p>')
        imgs = [b for b in out if b["type"] == "image"]
        assert len(imgs) == 1
        assert imgs[0]["image"]["external"]["url"] == "https://x.test/a.png"

    def test_truncation(self):
        # Build an HTML that converts to MANY blocks (heading per line).
        html = "".join(f"<h2>Item {i}</h2>" for i in range(200))
        out = html_to_notion_blocks(html, max_blocks=MAX_BLOCKS)
        assert len(out) == MAX_BLOCKS + 1  # +1 truncation notice
        assert out[-1]["type"] == "paragraph"
        assert _block_text(out[-1]) == TRUNC_NOTICE

    def test_long_text_chunked(self):
        long_text = "x" * (MAX_RICH_TEXT_LEN * 2 + 100)
        out = html_to_notion_blocks(f"<p>{long_text}</p>")
        assert len(out) == 1
        rt = out[0]["paragraph"]["rich_text"]
        # Each chunk must be <= MAX_RICH_TEXT_LEN.
        assert all(len(s["text"]["content"]) <= MAX_RICH_TEXT_LEN for s in rt)
        joined = "".join(s["text"]["content"] for s in rt)
        assert joined == long_text

    def test_fallback_no_body_block(self):
        b = fallback_no_body_block()
        assert b["type"] == "paragraph"
        assert _block_text(b) == "created_no_body"

    def test_strips_script_and_style(self):
        html = "<p>visible</p><script>alert(1)</script><style>.x{}</style>"
        out = html_to_notion_blocks(html)
        joined = " ".join(_block_text(b) for b in out if b["type"] == "paragraph")
        assert "visible" in joined
        assert "alert" not in joined
        assert ".x" not in joined
