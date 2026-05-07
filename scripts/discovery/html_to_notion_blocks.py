"""Convert HTML (typically from RSS <content:encoded>) to Notion block children.

Pipeline: html → markdown (via ``markdownify``) → walk lines → Notion blocks.
Designed to satisfy the Notion REST API (version 2025-09-03):

- ``rich_text`` arrays are chunked at ``MAX_RICH_TEXT_LEN`` chars (Notion 2000-char hard limit).
- Block list is truncated to ``MAX_BLOCKS`` (default 90) plus a trailing "[contenido truncado]"
  paragraph.
- Supported block types: heading_1/2/3, paragraph, bulleted_list_item, numbered_list_item,
  image (external URL).
- Inline annotations supported on rich_text: bold (``**x**`` / ``__x__``), italic
  (``*x*`` / ``_x_``), code (backtick-wrapped), strikethrough (``~~x~~``), and links
  (``[text](url)``). Backslash escapes for ``*``, ``_``, backtick, ``~`` produce
  literal characters with no annotation.
- Limitation: nested annotations are NOT supported (e.g. ``**bold _italic_**`` will
  emit a single bold span keeping the inner ``_italic_`` markers literal). On any
  parser failure the line falls back to a single plain-text span.

If conversion fails entirely, callers should fall back to a single
``created_no_body`` paragraph (handled outside this module).
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

MAX_BLOCKS = 90
MAX_RICH_TEXT_LEN = 1900  # Notion limit is 2000; leave some headroom.
TRUNC_NOTICE = "[contenido truncado]"

DEFAULT_ANNOTATIONS = {
    "bold": False,
    "italic": False,
    "strikethrough": False,
    "underline": False,
    "code": False,
    "color": "default",
}


def _chunks(text: str, size: int = MAX_RICH_TEXT_LEN) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + size] for i in range(0, len(text), size)]


def _make_span(content: str, *, link: str | None = None,
               annotations: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Build one or more Notion text spans (chunked to MAX_RICH_TEXT_LEN)."""
    out: list[dict[str, Any]] = []
    for chunk in _chunks(content):
        text_obj: dict[str, Any] = {"content": chunk}
        if link:
            text_obj["link"] = {"url": link}
        span: dict[str, Any] = {"type": "text", "text": text_obj}
        if annotations:
            # Merge over defaults so Notion gets a complete annotations object.
            merged = {**DEFAULT_ANNOTATIONS, **annotations}
            span["annotations"] = merged
        out.append(span)
    return out


# ---------- Inline markdown parser ----------

# Order matters in the alternation: longer tokens first to avoid eating ``**`` as ``*``.
# Group names tell us which kind of span matched.
_INLINE_RE = re.compile(
    r"""
    (?P<image>!\[(?P<image_alt>[^\]]*)\]\((?P<image_url>[^)\s]+)\))      # ![alt](url) - stripped
    | (?P<link>\[(?P<link_label>[^\]]+)\]\((?P<link_url>[^)\s]+)\))      # [label](url)
    | (?P<bold_star>\*\*(?P<bold_star_inner>[^\s*][^*]*?[^\s*]|[^\s*])\*\*)
    | (?P<bold_us>__(?P<bold_us_inner>[^\s_][^_]*?[^\s_]|[^\s_])__)
    | (?P<italic_star>\*(?P<italic_star_inner>[^\s*][^*]*?[^\s*]|[^\s*])\*)
    | (?P<italic_us>(?<![A-Za-z0-9_])_(?P<italic_us_inner>[^\s_][^_]*?[^\s_]|[^\s_])_(?![A-Za-z0-9_]))
    | (?P<code>`(?P<code_inner>[^`]+)`)
    | (?P<strike>~~(?P<strike_inner>[^~]+)~~)
    """,
    re.VERBOSE,
)


def _unescape(text: str) -> str:
    """Convert backslash-escaped markdown punctuation to literal characters."""
    return re.sub(r"\\([\\*_`~\[\]()!#~])", r"\1", text)


def _parse_inline(text: str) -> list[dict[str, Any]]:
    """Parse markdown-flavored ``text`` into a list of Notion rich_text spans.

    Strategy: scan for the next inline token (regex alternation) and emit a plain
    span for the gap before it. Non-nesting; precedence is encoded in the regex
    alternation order. Backslash-escaped punctuation is preserved as literal.
    """
    spans: list[dict[str, Any]] = []
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            gap = _unescape(text[pos : m.start()])
            if gap:
                spans.extend(_make_span(gap))

        if m.group("image") is not None:
            # Inline images are emitted as separate image blocks elsewhere; drop here.
            pass
        elif m.group("link") is not None:
            label = _unescape(m.group("link_label"))
            url = m.group("link_url")
            spans.extend(_make_span(label, link=url))
        elif m.group("bold_star") is not None:
            spans.extend(_make_span(_unescape(m.group("bold_star_inner")),
                                    annotations={"bold": True}))
        elif m.group("bold_us") is not None:
            spans.extend(_make_span(_unescape(m.group("bold_us_inner")),
                                    annotations={"bold": True}))
        elif m.group("italic_star") is not None:
            spans.extend(_make_span(_unescape(m.group("italic_star_inner")),
                                    annotations={"italic": True}))
        elif m.group("italic_us") is not None:
            spans.extend(_make_span(_unescape(m.group("italic_us_inner")),
                                    annotations={"italic": True}))
        elif m.group("code") is not None:
            spans.extend(_make_span(m.group("code_inner"),
                                    annotations={"code": True}))
        elif m.group("strike") is not None:
            spans.extend(_make_span(_unescape(m.group("strike_inner")),
                                    annotations={"strikethrough": True}))
        pos = m.end()

    if pos < len(text):
        tail = _unescape(text[pos:])
        if tail:
            spans.extend(_make_span(tail))
    if not spans:
        spans = _make_span("")
    return spans


def _rich_text(text: str) -> list[dict[str, Any]]:
    """Public-ish helper: parse inline markdown, fall back to plain text on failure."""
    try:
        return _parse_inline(text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inline parser failed (%s); falling back to plain text", exc)
        return _make_span(text)


# ---------- Block builders ----------

def _paragraph(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rich_text(text)},
    }


def _heading(level: int, text: str) -> dict[str, Any]:
    level = max(1, min(3, level))
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": _rich_text(text)},
    }


def _list_item(numbered: bool, text: str) -> dict[str, Any]:
    key = "numbered_list_item" if numbered else "bulleted_list_item"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": _rich_text(text)},
    }


def _image(url: str, alt: str = "") -> dict[str, Any]:
    block: dict[str, Any] = {
        "object": "block",
        "type": "image",
        "image": {"type": "external", "external": {"url": url}},
    }
    if alt:
        block["image"]["caption"] = _make_span(alt[:MAX_RICH_TEXT_LEN])
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

