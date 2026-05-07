"""Convert HTML (typically from RSS <content:encoded>) to Notion block children.

Pipeline: html → markdown (via ``markdownify``) → walk lines → Notion blocks.
Designed to satisfy the Notion REST API (version 2025-09-03):

- ``rich_text`` arrays are chunked at ``MAX_RICH_TEXT_LEN`` chars (Notion 2000-char hard limit).
- Block list is truncated to ``MAX_BLOCKS`` (default 90) plus a trailing "[contenido truncado]"
  paragraph.
- Supported block types: heading_1/2/3, paragraph, bulleted_list_item, numbered_list_item,
  image (external URL).
- Links inside paragraphs preserve href via ``rich_text[].text.link.url``.

If conversion fails for any reason, callers should fall back to a single
``created_no_body`` paragraph (handled outside this module).
"""

from __future__ import annotations

import re
from typing import Any

MAX_BLOCKS = 90
MAX_RICH_TEXT_LEN = 1900  # Notion limit is 2000; leave some headroom.
TRUNC_NOTICE = "[contenido truncado]"


def _chunks(text: str, size: int = MAX_RICH_TEXT_LEN) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + size] for i in range(0, len(text), size)]


def _rich_text_plain(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": chunk}} for chunk in _chunks(text)]


_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def _rich_text_with_links(text: str) -> list[dict[str, Any]]:
    """Parse inline markdown links into Notion rich_text segments.

    Strips inline images first (they become standalone image blocks elsewhere).
    Bold/italic are flattened to plain text — keeps converter simple and avoids
    misparsing edge cases.
    """
    text = _IMG_RE.sub("", text)
    out: list[dict[str, Any]] = []
    pos = 0
    for m in _LINK_RE.finditer(text):
        before = text[pos : m.start()]
        if before:
            out.extend(_rich_text_plain(before))
        label, url = m.group(1), m.group(2)
        for chunk in _chunks(label):
            out.append({
                "type": "text",
                "text": {"content": chunk, "link": {"url": url}},
            })
        pos = m.end()
    tail = text[pos:]
    if tail:
        out.extend(_rich_text_plain(tail))
    if not out:
        out = [{"type": "text", "text": {"content": ""}}]
    return out


def _paragraph(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rich_text_with_links(text)},
    }


def _heading(level: int, text: str) -> dict[str, Any]:
    level = max(1, min(3, level))
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": _rich_text_with_links(text)},
    }


def _list_item(numbered: bool, text: str) -> dict[str, Any]:
    key = "numbered_list_item" if numbered else "bulleted_list_item"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": _rich_text_with_links(text)},
    }


def _image(url: str, alt: str = "") -> dict[str, Any]:
    block: dict[str, Any] = {
        "object": "block",
        "type": "image",
        "image": {"type": "external", "external": {"url": url}},
    }
    if alt:
        block["image"]["caption"] = _rich_text_plain(alt[:MAX_RICH_TEXT_LEN])
    return block


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
_NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.+?)\s*$")
_STANDALONE_IMG_RE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)\s]+)\)\s*$")


def _md_lines_to_blocks(md: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    paragraph_buf: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph_buf:
            return
        text = " ".join(s.strip() for s in paragraph_buf if s.strip())
        paragraph_buf.clear()
        if text:
            blocks.append(_paragraph(text))

    for raw_line in md.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            flush_paragraph()
            continue
        m = _STANDALONE_IMG_RE.match(line)
        if m:
            flush_paragraph()
            alt, url = m.group(1), m.group(2)
            blocks.append(_image(url, alt=alt))
            continue
        m = _HEADING_RE.match(line)
        if m:
            flush_paragraph()
            level = min(3, len(m.group(1)))
            blocks.append(_heading(level, m.group(2)))
            continue
        m = _BULLET_RE.match(line)
        if m:
            flush_paragraph()
            blocks.append(_list_item(False, m.group(1)))
            continue
        m = _NUMBERED_RE.match(line)
        if m:
            flush_paragraph()
            blocks.append(_list_item(True, m.group(1)))
            continue
        paragraph_buf.append(line)

    flush_paragraph()
    return blocks


def html_to_notion_blocks(html: str | None, *, max_blocks: int = MAX_BLOCKS) -> list[dict[str, Any]]:
    """Convert HTML to a list of Notion block children.

    Returns an empty list if input is empty/None. Raises only if a real conversion
    failure occurs (caller should catch and emit a fallback ``created_no_body``
    paragraph).
    """
    if not html or not html.strip():
        return []
    # markdownify is the only third-party dep we add for 013-F.
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md_convert

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    md = md_convert(str(soup), heading_style="ATX")
    blocks = _md_lines_to_blocks(md)
    if len(blocks) > max_blocks:
        blocks = blocks[:max_blocks]
        blocks.append(_paragraph(TRUNC_NOTICE))
    return blocks


def fallback_no_body_block() -> dict[str, Any]:
    """Single paragraph block used when html conversion fails or content is empty."""
    return _paragraph("created_no_body")
