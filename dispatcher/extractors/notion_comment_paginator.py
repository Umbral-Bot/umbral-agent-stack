"""Notion comment paginator.

Notion's `POST /comments` API accepts a single rich_text block whose
`content` field is hard-capped at 2000 characters. Reports longer than that
must be split or offloaded to a dedicated child page.

Task 036 (P1, 2026-05-07) — observed in Control Room: SIM Daily Report
writer (`scripts/sim_daily_report.py::_trim_for_comment`) silently truncates
to 1900 chars with a "[truncated]" suffix, dropping URLs past position ~17.

This module is a stateless helper. It does NOT persist deduplication state;
callers are responsible for not invoking it twice with the same payload.

Public API
----------

* :func:`post_long_comment` — primary entrypoint.
* :class:`NotionLikeClient` — :class:`typing.Protocol` describing the two
  methods the helper requires from its caller (`add_comment`,
  `create_subpage`). The real Notion HTTP wiring stays in
  ``worker.notion_client`` and ``scripts.discovery.stage4_push_notion``.
* :func:`render_text_to_blocks` — exposed for callers that want to pre-render
  plain-text payloads into Notion paragraph blocks.

Constants
---------

* :data:`SAFE_LIMIT` (1900) — soft budget for a single comment payload.
* :data:`ABSOLUTE_LIMIT` (2000) — Notion's hard API limit.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

__all__ = [
    "SAFE_LIMIT",
    "ABSOLUTE_LIMIT",
    "BLOCK_RICHTEXT_LIMIT",
    "NotionLikeClient",
    "post_long_comment",
    "render_text_to_blocks",
]


SAFE_LIMIT: int = 1900
ABSOLUTE_LIMIT: int = 2000
# Notion paragraph blocks also cap rich_text content at 2000 chars.
BLOCK_RICHTEXT_LIMIT: int = 1900

_FOOTER_TEMPLATE: str = "\n\n[Continúa en página dedicada → {url}]"
_PART_HEADER_TEMPLATE: str = "[{idx}/{total}] "

# Bare URL regex (good enough for daily reports — we only need to detect
# presence/order, not validate).
_URL_RE = re.compile(r"https?://\S+")


class NotionLikeClient(Protocol):
    """Minimal interface required by :func:`post_long_comment`.

    Implementations live outside this module (typically a thin wrapper around
    ``worker.notion_client``). The protocol is duck-typed; any object exposing
    these two methods is acceptable.
    """

    def add_comment(self, parent_id: str, text: str) -> dict[str, Any]:
        """POST a single Notion comment. Must return ``{"comment_id": str, ...}``."""
        ...

    def create_subpage(
        self, parent_page_id: str, title: str, blocks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Create a child page. Must return ``{"page_id": str, "url": str, ...}``."""
        ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_chars(text: str) -> int:
    """Return the character (NOT byte) length used by Notion's API."""
    return len(text)


def _first_line(text: str, max_chars: int = 60) -> str:
    """Return the first non-blank line, truncated."""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:max_chars]
    return text[:max_chars]


def render_text_to_blocks(text: str) -> list[dict[str, Any]]:
    """Render plain text as a list of Notion ``paragraph`` blocks.

    The input is split on blank lines (``\\n\\n``) into paragraphs. If any
    paragraph exceeds :data:`BLOCK_RICHTEXT_LIMIT`, it's further split on
    ``\\n`` then on hard chunks. Empty inputs return an empty list.
    """
    if not text:
        return []

    blocks: list[dict[str, Any]] = []
    for paragraph in text.split("\n\n"):
        if not paragraph.strip():
            continue
        chunks = _chunk_for_block(paragraph)
        for chunk in chunks:
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": chunk}}
                        ]
                    },
                }
            )
    return blocks


def _chunk_for_block(paragraph: str) -> list[str]:
    """Split a paragraph so each chunk fits in BLOCK_RICHTEXT_LIMIT."""
    if len(paragraph) <= BLOCK_RICHTEXT_LIMIT:
        return [paragraph]
    out: list[str] = []
    # First try splitting on single newlines.
    buf = ""
    for line in paragraph.split("\n"):
        candidate = (buf + "\n" + line) if buf else line
        if len(candidate) > BLOCK_RICHTEXT_LIMIT and buf:
            out.append(buf)
            buf = line
        else:
            buf = candidate
    if buf:
        out.append(buf)
    # Hard-chunk anything that's still too long (very long single line).
    final: list[str] = []
    for chunk in out:
        while len(chunk) > BLOCK_RICHTEXT_LIMIT:
            final.append(chunk[:BLOCK_RICHTEXT_LIMIT])
            chunk = chunk[BLOCK_RICHTEXT_LIMIT:]
        if chunk:
            final.append(chunk)
    return final


def _build_header_with_footer(text: str, footer: str) -> str:
    """Take leading lines of ``text`` until adding the next would exceed
    ``SAFE_LIMIT - len(footer)``. Append ``footer`` at the end.

    Always preserves at least the first non-empty line (even if that means
    truncating it inside the budget).
    """
    budget = SAFE_LIMIT - len(footer)
    if budget <= 0:
        # Pathological footer; just send footer alone, hard-truncated.
        return footer[:SAFE_LIMIT]

    lines = text.split("\n")
    out_lines: list[str] = []
    used = 0
    for line in lines:
        # +1 accounts for the joining "\n" if there's already content.
        cost = len(line) + (1 if out_lines else 0)
        if used + cost > budget:
            break
        out_lines.append(line)
        used += cost

    if not out_lines:
        # Force-include the first line, hard-truncated to budget.
        first = lines[0] if lines else ""
        out_lines = [first[:budget]]

    return "\n".join(out_lines) + footer


def _split_into_numbered_parts(text: str) -> list[str]:
    """Split ``text`` into N parts, each prefixed ``[i/N] `` and ≤ SAFE_LIMIT.

    The split prefers paragraph boundaries (``\\n\\n``) then line boundaries
    (``\\n``); only falls back to a hard char split if a single line exceeds
    the per-part budget. The header prefix is computed from the *final* part
    count (``N``) so numbering is consistent.
    """
    # First pass: estimate parts by chunking with a worst-case header width.
    # We assume N ≤ 99 → header ≤ "[99/99] " = 8 chars.
    worst_header = 8
    raw_chunks = _chunk_text(text, SAFE_LIMIT - worst_header)
    total = len(raw_chunks)
    if total == 0:
        return []
    if total == 1:
        # Even with worst-case header it fits — but we still tag it [1/1] so
        # the numbering invariant holds for callers.
        header = _PART_HEADER_TEMPLATE.format(idx=1, total=1)
        return [header + raw_chunks[0]]

    # Recompute with the actual header width for the chosen total.
    header_width = len(_PART_HEADER_TEMPLATE.format(idx=total, total=total))
    final_chunks = _chunk_text(text, SAFE_LIMIT - header_width)
    # In the unlikely case the recompute changes total, redo once more.
    if len(final_chunks) != total:
        total = len(final_chunks)
        header_width = len(_PART_HEADER_TEMPLATE.format(idx=total, total=total))
        final_chunks = _chunk_text(text, SAFE_LIMIT - header_width)
        total = len(final_chunks)

    return [
        _PART_HEADER_TEMPLATE.format(idx=i + 1, total=total) + chunk
        for i, chunk in enumerate(final_chunks)
    ]


def _chunk_text(text: str, budget: int) -> list[str]:
    """Greedy split preferring \\n\\n then \\n then hard char boundaries."""
    if budget <= 0:
        raise ValueError(f"chunk budget must be > 0, got {budget}")
    if len(text) <= budget:
        return [text] if text else []

    out: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf:
            out.append(buf)
            buf = ""

    paragraphs = text.split("\n\n")
    for p_idx, paragraph in enumerate(paragraphs):
        # The separator we'd glue with: \n\n between paragraphs, nothing for first.
        sep = "\n\n" if buf else ""
        candidate = buf + sep + paragraph
        if len(candidate) <= budget:
            buf = candidate
            continue
        # Paragraph doesn't fit. Flush current buffer first.
        flush()
        if len(paragraph) <= budget:
            buf = paragraph
            continue
        # Single paragraph itself too big — split on \n.
        line_buf = ""
        for line in paragraph.split("\n"):
            sep_l = "\n" if line_buf else ""
            cand = line_buf + sep_l + line
            if len(cand) <= budget:
                line_buf = cand
                continue
            if line_buf:
                out.append(line_buf)
                line_buf = ""
            # Still too big? Hard-chunk this line.
            while len(line) > budget:
                out.append(line[:budget])
                line = line[budget:]
            line_buf = line
        if line_buf:
            buf = line_buf
    flush()
    return out


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def post_long_comment(
    client: NotionLikeClient,
    parent_id: str,
    text: str,
    *,
    body_page_parent_id: str | None = None,
) -> dict[str, Any]:
    """Post ``text`` as a Notion comment, paginating safely past the 2000-char limit.

    Behaviour matrix:

    +------------------------------+----------------------------------------+
    | ``len(text) <= SAFE_LIMIT``  | One ``add_comment`` call (legacy path) |
    +------------------------------+----------------------------------------+
    | text too long, page parent   | Create child page with full body, then |
    | provided                     | post a single comment whose body is    |
    |                              | the leading lines + footer link to     |
    |                              | the new page.                          |
    +------------------------------+----------------------------------------+
    | text too long, no page       | Split into N comments numbered         |
    | parent                       | ``[1/N]``…``[N/N]`` posted in order.   |
    +------------------------------+----------------------------------------+

    Args:
        client: Anything implementing :class:`NotionLikeClient`.
        parent_id: Notion page id (or thread id) the comment is anchored to.
        text: Comment body. Must be non-empty.
        body_page_parent_id: When provided, oversized payloads are offloaded
            to a child page under this parent (recommended). When ``None``,
            the helper falls back to numbered comment fragmentation.

    Returns:
        ``{"comment_id": str | list[str], "page_id": str | None,``
        ``"truncated": False, "parts": int}``. ``truncated`` is always
        ``False`` because the helper is the anti-truncation primitive; the
        field is included so callers can assert on it.

    Raises:
        ValueError: If ``text`` is empty.

    Note:
        This helper is stateless. Callers must deduplicate at their own
        layer (e.g. by stamping an idempotency key on the source ops_log
        entry) — calling ``post_long_comment`` twice with the same ``text``
        will create two comments (and two pages, in mode 2).
    """
    if not text:
        raise ValueError("post_long_comment: text must be non-empty")

    if _count_chars(text) <= SAFE_LIMIT:
        result = client.add_comment(parent_id, text)
        return {
            "comment_id": result["comment_id"],
            "page_id": None,
            "truncated": False,
            "parts": 1,
        }

    if body_page_parent_id:
        title = "[Long content] " + _first_line(text)
        blocks = render_text_to_blocks(text)
        page = client.create_subpage(body_page_parent_id, title, blocks)
        page_id = page["page_id"]
        page_url = page.get("url") or f"https://www.notion.so/{page_id.replace('-', '')}"
        footer = _FOOTER_TEMPLATE.format(url=page_url)
        comment_text = _build_header_with_footer(text, footer)
        result = client.add_comment(parent_id, comment_text)
        return {
            "comment_id": result["comment_id"],
            "page_id": page_id,
            "truncated": False,
            "parts": 1,
        }

    # Fallback: numbered-parts fragmentation.
    parts = _split_into_numbered_parts(text)
    comment_ids: list[str] = []
    for part in parts:
        result = client.add_comment(parent_id, part)
        comment_ids.append(result["comment_id"])
    return {
        "comment_id": comment_ids,
        "page_id": None,
        "truncated": False,
        "parts": len(parts),
    }
