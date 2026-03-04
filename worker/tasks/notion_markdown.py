"""
Notion Markdown Converter — converts simple markdown to Notion API blocks.

Supports: paragraphs, headers (# ## ###), bullets (- *), bold (**text**),
links [text](url), and dividers (---).

No external dependencies — stdlib only.
"""

import re
from typing import Any


def _rich_text(text: str, bold: bool = False) -> list[dict[str, Any]]:
    """Convert text with **bold** and [links](url) to Notion rich_text array."""
    parts: list[dict[str, Any]] = []
    # Pattern matches **bold**, [link text](url), or plain text
    pattern = re.compile(r'(\*\*(.+?)\*\*)|(\[([^\]]+)\]\(([^)]+)\))')

    pos = 0
    for match in pattern.finditer(text):
        # Add plain text before this match
        if match.start() > pos:
            plain = text[pos:match.start()]
            if plain:
                parts.append({"type": "text", "text": {"content": plain}})

        if match.group(2):  # **bold**
            parts.append({
                "type": "text",
                "text": {"content": match.group(2)},
                "annotations": {
                    "bold": True, "italic": False, "strikethrough": False,
                    "underline": False, "code": False, "color": "default",
                },
            })
        elif match.group(4):  # [text](url)
            parts.append({
                "type": "text",
                "text": {"content": match.group(4), "link": {"url": match.group(5)}},
            })

        pos = match.end()

    # Add remaining plain text
    remaining = text[pos:]
    if remaining:
        rt: dict[str, Any] = {"type": "text", "text": {"content": remaining}}
        if bold:
            rt["annotations"] = {
                "bold": True, "italic": False, "strikethrough": False,
                "underline": False, "code": False, "color": "default",
            }
        parts.append(rt)

    if not parts:
        parts.append({"type": "text", "text": {"content": text or ""}})

    return parts


def markdown_to_blocks(md: str) -> list[dict[str, Any]]:
    """
    Convert simple markdown text to a list of Notion API block objects.

    Supported syntax:
        # Heading 1
        ## Heading 2
        ### Heading 3
        - Bullet item  (or * Bullet item)
        **bold text**
        [link text](url)
        --- (horizontal rule)
        Regular paragraphs

    Returns:
        List of Notion block dicts ready for the pages API children field.
    """
    blocks: list[dict[str, Any]] = []
    lines = md.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Divider: --- or *** or ___
        if re.match(r'^[-*_]{3,}$', stripped):
            blocks.append({
                "object": "block", "type": "divider", "divider": {}
            })
            i += 1
            continue

        # Heading 3: ###
        if stripped.startswith("### "):
            text = stripped[4:].strip()
            blocks.append({
                "object": "block", "type": "heading_3",
                "heading_3": {"rich_text": _rich_text(text), "color": "default", "is_toggleable": False},
            })
            i += 1
            continue

        # Heading 2: ##
        if stripped.startswith("## "):
            text = stripped[3:].strip()
            blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": _rich_text(text), "color": "default", "is_toggleable": False},
            })
            i += 1
            continue

        # Heading 1: #
        if stripped.startswith("# "):
            text = stripped[2:].strip()
            blocks.append({
                "object": "block", "type": "heading_1",
                "heading_1": {"rich_text": _rich_text(text), "color": "default", "is_toggleable": False},
            })
            i += 1
            continue

        # Bullet: - or *
        if re.match(r'^[-*]\s+', stripped):
            text = re.sub(r'^[-*]\s+', '', stripped)
            blocks.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _rich_text(text), "color": "default"},
            })
            i += 1
            continue

        # Numbered list: 1. 2. etc
        if re.match(r'^\d+\.\s+', stripped):
            text = re.sub(r'^\d+\.\s+', '', stripped)
            blocks.append({
                "object": "block", "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": _rich_text(text), "color": "default"},
            })
            i += 1
            continue

        # Default: paragraph (accumulate adjacent non-special lines)
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            next_stripped = lines[i].strip()
            if (not next_stripped
                or next_stripped.startswith("#")
                or re.match(r'^[-*]\s+', next_stripped)
                or re.match(r'^\d+\.\s+', next_stripped)
                or re.match(r'^[-*_]{3,}$', next_stripped)):
                break
            para_lines.append(next_stripped)
            i += 1

        paragraph_text = " ".join(para_lines)
        # Notion rich_text content max is 2000 chars
        for chunk_start in range(0, len(paragraph_text), 2000):
            chunk = paragraph_text[chunk_start:chunk_start + 2000]
            blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": _rich_text(chunk), "color": "default"},
            })

    return blocks
