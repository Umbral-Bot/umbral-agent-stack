"""Tests for dispatcher.extractors.notion_comment_paginator (Task 036)."""

from __future__ import annotations

from typing import Any

import pytest

from dispatcher.extractors.notion_comment_paginator import (
    ABSOLUTE_LIMIT,
    SAFE_LIMIT,
    BLOCK_RICHTEXT_LIMIT,
    post_long_comment,
    render_text_to_blocks,
)


# ---------------------------------------------------------------------------
# Test double
# ---------------------------------------------------------------------------


class FakeNotionClient:
    """Records every call to add_comment / create_subpage."""

    def __init__(self) -> None:
        self.comments: list[tuple[str, str]] = []
        self.pages: list[tuple[str, str, list[dict[str, Any]]]] = []
        self._comment_seq = 0
        self._page_seq = 0

    def add_comment(self, parent_id: str, text: str) -> dict[str, Any]:
        # Enforce Notion's hard limit so tests fail loudly if helper regresses.
        assert len(text) <= ABSOLUTE_LIMIT, (
            f"add_comment payload {len(text)} chars exceeds Notion limit"
        )
        self._comment_seq += 1
        cid = f"comment-{self._comment_seq:03d}"
        self.comments.append((parent_id, text))
        return {"comment_id": cid}

    def create_subpage(
        self, parent_page_id: str, title: str, blocks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self._page_seq += 1
        pid = f"page-{self._page_seq:03d}"
        self.pages.append((parent_page_id, title, blocks))
        return {"page_id": pid, "url": f"https://www.notion.so/{pid}"}


# ---------------------------------------------------------------------------
# 1. Default behaviour preserved (text within budget → 1 POST)
# ---------------------------------------------------------------------------


class TestSinglePost:
    def test_short_text_one_comment_no_page(self) -> None:
        client = FakeNotionClient()
        result = post_long_comment(client, "parent-1", "Hola David")
        assert len(client.comments) == 1
        assert client.pages == []
        assert client.comments[0] == ("parent-1", "Hola David")
        assert result == {
            "comment_id": "comment-001",
            "page_id": None,
            "truncated": False,
            "parts": 1,
        }

    def test_text_exactly_at_safe_limit(self) -> None:
        client = FakeNotionClient()
        text = "x" * SAFE_LIMIT
        result = post_long_comment(client, "parent-1", text)
        assert len(client.comments) == 1
        assert client.comments[0][1] == text
        assert result["parts"] == 1
        assert result["page_id"] is None


# ---------------------------------------------------------------------------
# 2. Long text with body_page_parent_id → page + lead comment
# ---------------------------------------------------------------------------


class TestPageOffloadMode:
    def _long_text(self) -> str:
        # 50 URLs in a numbered list, plus header — ~3.5 KB, definitely > 1900.
        lines = ["SIM Daily Report (2026-05-07 18:30 UTC)", "Ventana: ultimas 24h", ""]
        lines.append("URLs encontradas:")
        for i in range(50):
            lines.append(f"{i + 1}. https://example.com/article-{i:03d}-with-long-slug-text")
        return "\n".join(lines)

    def test_creates_page_then_posts_lead_comment(self) -> None:
        client = FakeNotionClient()
        text = self._long_text()
        assert len(text) > SAFE_LIMIT  # sanity

        result = post_long_comment(
            client, "parent-1", text, body_page_parent_id="container-page-99"
        )

        # Exactly one page + one comment.
        assert len(client.pages) == 1
        assert len(client.comments) == 1

        page_parent, page_title, page_blocks = client.pages[0]
        assert page_parent == "container-page-99"
        assert page_title.startswith("[Long content] ")
        assert "SIM Daily Report" in page_title
        # Page body holds the FULL text reconstructed.
        rendered = "\n\n".join(
            block["paragraph"]["rich_text"][0]["text"]["content"]
            for block in page_blocks
        )
        # Each input paragraph should be present (we split on \n\n).
        assert "https://example.com/article-049" in rendered
        assert "https://example.com/article-000" in rendered

        comment_parent, comment_text = client.comments[0]
        assert comment_parent == "parent-1"
        assert "[Continúa en página dedicada" in comment_text
        assert "page-001" in comment_text
        assert len(comment_text) <= ABSOLUTE_LIMIT

        assert result["comment_id"] == "comment-001"
        assert result["page_id"] == "page-001"
        assert result["truncated"] is False
        assert result["parts"] == 1

    def test_first_17_urls_preserved_in_lead_comment(self) -> None:
        """Header invariant: even after page offload, the first 17 URLs from
        the input must appear verbatim in the lead comment so David sees
        them in Control Room without clicking through."""
        client = FakeNotionClient()
        text = self._long_text()
        post_long_comment(
            client, "parent-1", text, body_page_parent_id="container-page-99"
        )
        comment_text = client.comments[0][1]
        for i in range(17):
            assert f"https://example.com/article-{i:03d}" in comment_text, (
                f"URL #{i} missing from lead comment"
            )


# ---------------------------------------------------------------------------
# 3. Long text without body_page_parent_id → numbered fragmentation
# ---------------------------------------------------------------------------


class TestNumberedFallback:
    def test_long_text_split_into_numbered_parts_in_order(self) -> None:
        client = FakeNotionClient()
        # ~5500 chars → ≥ 3 parts at SAFE_LIMIT.
        paragraphs = [f"Paragraph {i}: " + ("data " * 80) for i in range(20)]
        text = "\n\n".join(paragraphs)
        assert len(text) > SAFE_LIMIT * 2

        result = post_long_comment(client, "parent-1", text)

        n = result["parts"]
        assert n >= 3
        assert isinstance(result["comment_id"], list)
        assert len(result["comment_id"]) == n
        assert result["page_id"] is None
        assert result["truncated"] is False

        for idx, (parent, body) in enumerate(client.comments, start=1):
            assert parent == "parent-1"
            assert body.startswith(f"[{idx}/{n}] ")
            assert len(body) <= ABSOLUTE_LIMIT

        # Chronological order: ids assigned in order.
        assert result["comment_id"] == [f"comment-{i:03d}" for i in range(1, n + 1)]


# ---------------------------------------------------------------------------
# 4-9. Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_text_raises(self) -> None:
        client = FakeNotionClient()
        with pytest.raises(ValueError, match="non-empty"):
            post_long_comment(client, "parent-1", "")
        assert client.comments == []
        assert client.pages == []

    def test_unicode_uses_char_count_not_bytes(self) -> None:
        """Multi-byte chars: 1900 emoji + ASCII < SAFE_LIMIT in chars but
        would exceed any byte-based check. Helper must measure chars."""
        client = FakeNotionClient()
        # 1900 chars where many are 4-byte emoji.
        text = "🚀" * 1800 + "tail"  # 1804 chars, ~7216 bytes
        assert len(text) <= SAFE_LIMIT
        result = post_long_comment(client, "parent-1", text)
        assert len(client.comments) == 1
        assert client.comments[0][1] == text
        assert result["parts"] == 1

    def test_newlines_preserved_in_page_body(self) -> None:
        client = FakeNotionClient()
        # Three paragraphs separated by blank lines, intentionally over budget.
        para1 = "First paragraph: " + ("a " * 600)
        para2 = "Second paragraph: " + ("b " * 600)
        para3 = "Third paragraph: " + ("c " * 600)
        text = f"{para1}\n\n{para2}\n\n{para3}"
        assert len(text) > SAFE_LIMIT

        post_long_comment(
            client, "parent-1", text, body_page_parent_id="container-99"
        )

        _, _, blocks = client.pages[0]
        # Each paragraph maps to at least one block; structure preserved.
        contents = [
            b["paragraph"]["rich_text"][0]["text"]["content"] for b in blocks
        ]
        assert any("First paragraph" in c for c in contents)
        assert any("Second paragraph" in c for c in contents)
        assert any("Third paragraph" in c for c in contents)

    def test_payload_shape_matches_notion_schema(self) -> None:
        """Verify the page-blocks payload uses the exact Notion paragraph schema."""
        client = FakeNotionClient()
        text = "Header line\n\n" + ("payload " * 400)  # > SAFE_LIMIT
        post_long_comment(
            client, "parent-1", text, body_page_parent_id="container-99"
        )
        _, _, blocks = client.pages[0]
        for b in blocks:
            assert b["object"] == "block"
            assert b["type"] == "paragraph"
            rt = b["paragraph"]["rich_text"]
            assert isinstance(rt, list) and len(rt) == 1
            assert rt[0]["type"] == "text"
            content = rt[0]["text"]["content"]
            assert isinstance(content, str)
            assert len(content) <= BLOCK_RICHTEXT_LIMIT

    def test_idempotency_is_caller_responsibility(self) -> None:
        """Documented contract: helper does NOT dedupe. Two identical calls
        produce two comments. Callers must enforce idempotency upstream."""
        client = FakeNotionClient()
        post_long_comment(client, "parent-1", "Same text")
        post_long_comment(client, "parent-1", "Same text")
        assert len(client.comments) == 2
        assert client.comments[0] == client.comments[1]


# ---------------------------------------------------------------------------
# 10. render_text_to_blocks unit
# ---------------------------------------------------------------------------


class TestRenderBlocks:
    def test_empty_returns_empty(self) -> None:
        assert render_text_to_blocks("") == []

    def test_oversized_paragraph_is_chunked(self) -> None:
        big = "x" * (BLOCK_RICHTEXT_LIMIT * 2 + 100)
        blocks = render_text_to_blocks(big)
        assert len(blocks) >= 3
        for b in blocks:
            content = b["paragraph"]["rich_text"][0]["text"]["content"]
            assert len(content) <= BLOCK_RICHTEXT_LIMIT
        # Round-trip: concatenated chunks recover the input.
        rendered = "".join(
            b["paragraph"]["rich_text"][0]["text"]["content"] for b in blocks
        )
        assert rendered == big
