"""Convert HTML (typically from RSS <content:encoded>) to Notion block children.

Pipeline: html → markdown (via ``markdownify``) → walk lines → Notion blocks.
Designed to satisfy the Notion REST API (version 2025-09-03):

- ``rich_text`` arrays are chunked at ``MAX_RICH_TEXT_LEN`` chars (Notion 2000-char hard limit).
- Block list is truncated to ``MAX_BLOCKS`` (default 90) plus a trailing "[contenido truncado]"
  paragraph.
- Supported block types: heading_1/2/3, paragraph, bulleted_list_item, numbered_list_item,
  image (external URL), divider.
- Inline annotations supported on rich_text: bold (``**x**`` / ``__x__``), italic
  (``*x*`` / ``_x_``), code (backtick-wrapped), strikethrough (``~~x~~``), and links
  (``[text](url)``). Inline tokens INSIDE link labels recurse up to depth 2, so
  ``[**OpenClaw**](url)`` emits a single span with both ``bold:true`` and
  ``link.url`` set. Backslash escapes for ``*``, ``_``, backtick, ``~`` produce
  literal characters with no annotation.
- Heading inference (013-H): a paragraph that consists of a single bold-only span
  ending in ``:`` (or followed by a list block) is promoted to ``heading_3``.
- Divider (013-H): a line of 3+ ``-``, ``*`` or ``_`` (optionally backslash-escaped)
  emits a Notion ``divider`` block.
- Image-in-link (013-H): the markdown pattern ``[![alt](src)](href)`` emits a
  Notion ``image`` block whose caption is a clickable link to ``href``.
- On any parser failure the line falls back to a single plain-text span.

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
    (?P<image_link>\[!\[(?P<il_alt>[^\]]*)\]\((?P<il_src>[^)\s]+)\)\]\((?P<il_href>[^)\s]+)\))  # [![alt](src)](href)
    | (?P<image>!\[(?P<image_alt>[^\]]*)\]\((?P<image_url>[^)\s]+)\))      # ![alt](url) - stripped
    | (?P<link>\[(?P<link_label>[^\]]+)\]\((?P<link_url>[^)\s]+)\))        # [label](url)
    | (?P<bold_star>\*\*(?P<bold_star_inner>[^\s*][^*]*?[^\s*]|[^\s*])\*\*)
    | (?P<bold_us>__(?P<bold_us_inner>[^\s_][^_]*?[^\s_]|[^\s_])__)
    | (?P<italic_star>\*(?P<italic_star_inner>[^\s*][^*]*?[^\s*]|[^\s*])\*)
    | (?P<italic_us>(?<![A-Za-z0-9_])_(?P<italic_us_inner>[^\s_][^_]*?[^\s_]|[^\s_])_(?![A-Za-z0-9_]))
    | (?P<code>`(?P<code_inner>[^`]+)`)
    | (?P<strike>~~(?P<strike_inner>[^~]+)~~)
    """,
    re.VERBOSE,
)

_MAX_INLINE_DEPTH = 2


def _unescape(text: str) -> str:
    """Convert backslash-escaped markdown punctuation to literal characters."""
    return re.sub(r"\\([\\*_`~\[\]()!#~-])", r"\1", text)


def _merge_ann(base: dict[str, Any] | None, extra: dict[str, Any]) -> dict[str, Any]:
    """Combine two annotation dicts (extra overrides base; OR-style for booleans)."""
    out: dict[str, Any] = {}
    if base:
        out.update(base)
    for k, v in extra.items():
        if isinstance(v, bool):
            out[k] = bool(out.get(k)) or v
        else:
            out[k] = v
    return out


def _parse_inline(
    text: str,
    *,
    link: str | None = None,
    annotations: dict[str, Any] | None = None,
    depth: int = 0,
) -> list[dict[str, Any]]:
    """Parse markdown-flavored ``text`` into Notion rich_text spans.

    013-H: recurses inside link labels up to ``_MAX_INLINE_DEPTH`` so that
    annotations like ``[**OpenClaw**](url)`` produce a single span carrying
    both ``bold:true`` and ``link.url``. ``link`` and ``annotations`` are
    inherited contexts pushed by the caller (None on the top-level call).

    013-H: also collapses runs of 3+ ``*`` or ``_`` down to 2, as a defense
    against authors over-bolding via nested ``<strong><b>`` (markdownify
    emits ``****X****`` which would otherwise leak literal ``**`` to Notion).
    Block-level divider detection (``***`` / ``___`` / ``---`` alone on a
    line) runs BEFORE inline parsing, so this collapse only affects inline
    content where 3+ markers are unambiguously author noise.
    """
    # 013-H normalization: ****X**** → **X**, _____Y_____ → __Y__, etc.
    text = re.sub(r"\*{3,}", "**", text)
    text = re.sub(r"_{3,}", "__", text)

    spans: list[dict[str, Any]] = []
    pos = 0
    inherited = annotations or None

    def _emit(content: str, *, extra_ann: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        merged = _merge_ann(inherited, extra_ann) if extra_ann else (dict(inherited) if inherited else None)
        return _make_span(content, link=link, annotations=merged or None)

    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            gap = _unescape(text[pos : m.start()])
            if gap:
                spans.extend(_emit(gap))

        if m.group("image_link") is not None:
            # [![alt](src)](href) — when found *inside* inline (rare; usually
            # detected at block level). Emit the alt text as a link to href.
            alt = _unescape(m.group("il_alt") or "")
            href = m.group("il_href")
            spans.extend(_make_span(alt or "image", link=href,
                                    annotations=inherited or None))
        elif m.group("image") is not None:
            # Inline images are emitted as separate image blocks elsewhere; drop here.
            pass
        elif m.group("link") is not None:
            label = m.group("link_label")
            url = m.group("link_url")
            if depth < _MAX_INLINE_DEPTH:
                # Recurse so inner ``**bold**`` etc. become annotated spans
                # all carrying ``link.url=url``.
                try:
                    spans.extend(_parse_inline(
                        label,
                        link=url,
                        annotations=inherited,
                        depth=depth + 1,
                    ))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("inline link recursion failed (%s); plain fallback", exc)
                    spans.extend(_make_span(_unescape(label), link=url,
                                            annotations=inherited or None))
            else:
                spans.extend(_make_span(_unescape(label), link=url,
                                        annotations=inherited or None))
        elif m.group("bold_star") is not None:
            spans.extend(_emit(_unescape(m.group("bold_star_inner")),
                               extra_ann={"bold": True}))
        elif m.group("bold_us") is not None:
            spans.extend(_emit(_unescape(m.group("bold_us_inner")),
                               extra_ann={"bold": True}))
        elif m.group("italic_star") is not None:
            spans.extend(_emit(_unescape(m.group("italic_star_inner")),
                               extra_ann={"italic": True}))
        elif m.group("italic_us") is not None:
            spans.extend(_emit(_unescape(m.group("italic_us_inner")),
                               extra_ann={"italic": True}))
        elif m.group("code") is not None:
            spans.extend(_emit(m.group("code_inner"),
                               extra_ann={"code": True}))
        elif m.group("strike") is not None:
            spans.extend(_emit(_unescape(m.group("strike_inner")),
                               extra_ann={"strikethrough": True}))
        pos = m.end()

    if pos < len(text):
        tail = _unescape(text[pos:])
        if tail:
            spans.extend(_emit(tail))
    if not spans:
        spans = _make_span("", link=link, annotations=inherited or None)
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


def _image(url: str, alt: str = "", *, caption_link: str | None = None) -> dict[str, Any]:
    block: dict[str, Any] = {
        "object": "block",
        "type": "image",
        "image": {"type": "external", "external": {"url": url}},
    }
    if alt or caption_link:
        block["image"]["caption"] = _make_span(
            (alt or "image")[:MAX_RICH_TEXT_LEN],
            link=caption_link,
        )
    return block


def _divider() -> dict[str, Any]:
    return {"object": "block", "type": "divider", "divider": {}}


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
_NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.+?)\s*$")
_STANDALONE_IMG_RE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)\s]+)\)\s*$")
# 013-H: image wrapped in link, common for podcast/youtube embeds.
_IMAGE_IN_LINK_RE = re.compile(
    r"^\s*\\?\[!\[([^\]]*)\]\(([^)\s]+)\)\]\(([^)\s]+)\)\s*$"
)
# 013-H: divider (--- / *** / ___), optionally backslash-escaped by markdownify.
_DIVIDER_RE = re.compile(r"^\s*\\?(?:-{3,}|\*{3,}|_{3,})\s*$")
# 013-H: paragraph that is exactly one bold span (with optional trailing ":").
_BOLD_ONLY_LINE_RE = re.compile(
    r"^\s*(?:\*\*|__)(?P<inner>[^\s*_][^*_]*?[^\s*_]|[^\s*_])(?:\*\*|__)\s*$"
)


def _is_bold_only_line(text: str) -> tuple[bool, bool]:
    """Return (is_bold_only, ends_with_colon)."""
    m = _BOLD_ONLY_LINE_RE.match(text or "")
    if not m:
        return (False, False)
    inner = m.group("inner").rstrip()
    return (True, inner.endswith(":"))


def _md_lines_to_blocks(md: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    paragraph_buf: list[str] = []
    lines = md.splitlines()

    def flush_paragraph(*, lookahead_idx: int | None = None) -> None:
        if not paragraph_buf:
            return
        text = " ".join(s.strip() for s in paragraph_buf if s.strip())
        paragraph_buf.clear()
        if not text:
            return
        # 013-H: heading-from-bold inference. Conservative: only when the
        # whole flushed paragraph is a single bold span AND either ends with
        # ``:`` OR the next non-empty line is a list item.
        is_bold_only, ends_colon = _is_bold_only_line(text)
        if is_bold_only:
            promote = ends_colon
            if not promote and lookahead_idx is not None:
                for j in range(lookahead_idx, len(lines)):
                    nxt = lines[j].rstrip()
                    if not nxt.strip():
                        continue
                    if _BULLET_RE.match(nxt) or _NUMBERED_RE.match(nxt):
                        promote = True
                    break
            if promote:
                m = _BOLD_ONLY_LINE_RE.match(text)
                inner = m.group("inner") if m else text  # type: ignore[union-attr]
                blocks.append(_heading(3, inner))
                return
        blocks.append(_paragraph(text))

    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        if not line.strip():
            flush_paragraph(lookahead_idx=idx + 1)
            continue
        if _DIVIDER_RE.match(line):
            flush_paragraph(lookahead_idx=idx + 1)
            blocks.append(_divider())
            continue
        m = _IMAGE_IN_LINK_RE.match(line)
        if m:
            flush_paragraph(lookahead_idx=idx + 1)
            alt, src, href = m.group(1), m.group(2), m.group(3)
            blocks.append(_image(src, alt=alt, caption_link=href))
            continue
        m = _STANDALONE_IMG_RE.match(line)
        if m:
            flush_paragraph(lookahead_idx=idx + 1)
            alt, url = m.group(1), m.group(2)
            blocks.append(_image(url, alt=alt))
            continue
        m = _HEADING_RE.match(line)
        if m:
            flush_paragraph(lookahead_idx=idx + 1)
            level = min(3, len(m.group(1)))
            blocks.append(_heading(level, m.group(2)))
            continue
        m = _BULLET_RE.match(line)
        if m:
            flush_paragraph(lookahead_idx=idx + 1)
            blocks.append(_list_item(False, m.group(1)))
            continue
        m = _NUMBERED_RE.match(line)
        if m:
            flush_paragraph(lookahead_idx=idx + 1)
            blocks.append(_list_item(True, m.group(1)))
            continue
        paragraph_buf.append(line)

    flush_paragraph(lookahead_idx=len(lines))
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
    # 013-H Phase E (option 1): disable markdownify's aggressive escaping of
    # ``*`` and ``_`` in plain text. Our inline parser handles literal vs syntax
    # via regex precedence + backslash unescape; markdownify-injected ``\*``
    # noise polluted link labels (Comet QA finding).
    md = md_convert(
        str(soup),
        heading_style="ATX",
        escape_asterisks=False,
        escape_underscores=False,
    )
    blocks = _md_lines_to_blocks(md)
    if len(blocks) > max_blocks:
        blocks = blocks[:max_blocks]
        blocks.append(_paragraph(TRUNC_NOTICE))
    return blocks


def fallback_no_body_block() -> dict[str, Any]:
    """Single paragraph block used when html conversion fails or content is empty."""
    return _paragraph("created_no_body")

