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


# --- 013-G: inline annotations + heading inline parsing ---


def _spans(block: dict) -> list[dict]:
    key = block["type"]
    return block[key]["rich_text"]


class TestInlineAnnotations:
    def test_bold_inline_produces_annotation(self):
        # Both ** and __ should produce bold annotation.
        out = html_to_notion_blocks("<p>Esto es <strong>negrita</strong> ya.</p>")
        spans = _spans(out[0])
        bolds = [s for s in spans if s.get("annotations", {}).get("bold")]
        assert bolds, "expected at least one bold span"
        assert any("negrita" in s["text"]["content"] for s in bolds)
        # Plain spans must NOT carry an annotations dict (or carry default-only).
        plain = [s for s in spans if s["text"]["content"].strip() == "Esto es"]
        assert plain
        assert not plain[0].get("annotations", {}).get("bold")

    def test_italic_inline_produces_annotation(self):
        out = html_to_notion_blocks("<p>Esto es <em>itálica</em> ahora.</p>")
        spans = _spans(out[0])
        italics = [s for s in spans if s.get("annotations", {}).get("italic")]
        assert italics
        assert any("itálica" in s["text"]["content"] for s in italics)

    def test_link_inline_produces_text_link(self):
        out = html_to_notion_blocks('<p>Ver <a href="https://x.test/y">acá</a>.</p>')
        spans = _spans(out[0])
        links = [s for s in spans if s["text"].get("link")]
        assert links and links[0]["text"]["link"]["url"] == "https://x.test/y"
        assert links[0]["text"]["content"] == "acá"
        # Link spans should NOT carry bold/italic by default.
        assert not links[0].get("annotations", {}).get("bold")
        assert not links[0].get("annotations", {}).get("italic")

    def test_heading_h1_h2_h3_block_types(self):
        out = html_to_notion_blocks(
            "<h1>uno</h1><h2>dos</h2><h3>tres</h3><h4>cuatro</h4>"
        )
        types = [b["type"] for b in out]
        assert types[0] == "heading_1"
        assert types[1] == "heading_2"
        assert types[2] == "heading_3"
        # h4 must collapse to heading_3.
        assert types[3] == "heading_3"
        # Heading content should be plain text — no literal ``#`` in rich_text.
        for b in out:
            joined = "".join(s["text"]["content"] for s in _spans(b))
            assert not joined.startswith("#"), f"heading leaked literal hash: {joined!r}"

    def test_mixed_inline_in_bullet(self):
        # Bulleted list item should also pass through the inline parser.
        out = html_to_notion_blocks(
            "<ul><li>Mira <strong>esto</strong> en <a href='https://x.test'>link</a></li></ul>"
        )
        bullets = [b for b in out if b["type"] == "bulleted_list_item"]
        assert bullets
        spans = _spans(bullets[0])
        assert any(s.get("annotations", {}).get("bold") for s in spans)
        assert any(s["text"].get("link") for s in spans)

    def test_inline_parser_fallback_on_exception(self, monkeypatch):
        # Force _parse_inline to raise; helper must fall back to plain text.
        from scripts.discovery import html_to_notion_blocks as mod

        def boom(_text):
            raise RuntimeError("synthetic")

        monkeypatch.setattr(mod, "_parse_inline", boom)
        out = mod.html_to_notion_blocks("<p>contenido importante</p>")
        assert len(out) == 1
        spans = _spans(out[0])
        joined = "".join(s["text"]["content"] for s in spans)
        assert "contenido importante" in joined
        # Fallback must NOT have annotations applied.
        assert not any(s.get("annotations", {}).get("bold") for s in spans)

    def test_no_double_processing_when_no_markdown(self):
        out = html_to_notion_blocks("<p>texto plano sin marcas.</p>")
        spans = _spans(out[0])
        # Single plain span, no annotations.
        assert len(spans) == 1
        assert spans[0]["text"]["content"] == "texto plano sin marcas."
        assert "annotations" not in spans[0] or not any(
            spans[0]["annotations"].get(k) for k in ("bold", "italic", "code", "strikethrough")
        )
