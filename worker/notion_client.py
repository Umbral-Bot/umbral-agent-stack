"""
Umbral Worker — Notion API Client

Thin wrapper around the Notion REST API (v2022-06-28).
Uses httpx for HTTP requests. All IDs come from environment variables
via worker.config — never hardcoded.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from . import config

logger = logging.getLogger("worker.notion")

NOTION_BASE_URL = "https://api.notion.com/v1"
TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _headers() -> dict[str, str]:
    """Build Notion API headers. Raises if NOTION_API_KEY is not set."""
    if not config.NOTION_API_KEY:
        raise RuntimeError("NOTION_API_KEY not configured")
    return {
        "Authorization": f"Bearer {config.NOTION_API_KEY}",
        "Notion-Version": config.NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def _check_response(resp: httpx.Response, context: str) -> dict[str, Any]:
    """Raise with clear message if Notion returns an error."""
    if resp.status_code >= 400:
        detail = resp.text[:500]
        logger.error("Notion %s failed (%d): %s", context, resp.status_code, detail)
        raise RuntimeError(
            f"Notion API error ({resp.status_code}) during {context}: {detail}"
        )
    return resp.json()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_transcript_page(
    title: str,
    content: str,
    source: str = "granola",
    date: str | None = None,
) -> dict[str, Any]:
    """
    Create a page in the Granola Inbox database.

    Args:
        title: Page title (e.g. meeting name).
        content: Transcript text (plain text, will be split into blocks).
        source: Source identifier (default: "granola").
        date: ISO date string. Defaults to now (UTC).

    Returns:
        Notion page object (dict).
    """
    config.require_notion()
    db_id = config.NOTION_GRANOLA_DB_ID

    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Split content into Notion paragraph blocks (max 2000 chars each)
    blocks = []
    for i in range(0, len(content), 2000):
        chunk = content[i : i + 2000]
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                },
            }
        )

    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Source": {"select": {"name": source}},
            "Date": {"date": {"start": date}},
        },
        "children": blocks,
    }

    logger.info("Creating transcript page: %s (db=%s)", title, db_id)
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{NOTION_BASE_URL}/pages",
            headers=_headers(),
            json=payload,
        )
    result = _check_response(resp, "create_transcript_page")
    logger.info("Created page: %s", result.get("id"))
    return {"page_id": result["id"], "url": result.get("url", "")}


def add_comment(page_id: str | None, text: str) -> dict[str, Any]:
    """
    Add a discussion comment to a Notion page.

    Args:
        page_id: The page to comment on. Defaults to NOTION_CONTROL_ROOM_PAGE_ID.
        text: Comment body.

    Returns:
        Notion comment object (dict).
    """
    config.require_notion()
    if page_id is None:
        page_id = config.NOTION_CONTROL_ROOM_PAGE_ID

    payload = {
        "parent": {"page_id": page_id},
        "rich_text": [{"type": "text", "text": {"content": text}}],
    }

    logger.info("Adding comment to page %s: %.60s...", page_id, text)
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{NOTION_BASE_URL}/comments",
            headers=_headers(),
            json=payload,
        )
    result = _check_response(resp, "add_comment")
    return {"comment_id": result["id"]}


def poll_comments(
    page_id: str | None = None,
    since: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Read recent comments from a Notion page.

    Args:
        page_id: The page to poll. Defaults to NOTION_CONTROL_ROOM_PAGE_ID.
        since: ISO datetime string — only return comments created after this time.
               If None, returns the most recent `limit` comments.
        limit: Max comments to return (Notion API max is 100).

    Returns:
        Dict with "comments" list and "count".
    """
    config.require_notion()
    if page_id is None:
        page_id = config.NOTION_CONTROL_ROOM_PAGE_ID

    params: dict[str, Any] = {"block_id": page_id, "page_size": min(limit, 100)}

    logger.info("Polling comments from page %s (since=%s)", page_id, since)
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(
            f"{NOTION_BASE_URL}/comments",
            headers=_headers(),
            params=params,
        )
    data = _check_response(resp, "poll_comments")

    comments = []
    for c in data.get("results", []):
        created = c.get("created_time", "")

        # Filter by since if provided
        if since and created < since:
            continue

        # Extract plain text from rich_text
        text_parts = []
        for rt in c.get("rich_text", []):
            text_parts.append(rt.get("plain_text", rt.get("text", {}).get("content", "")))

        comments.append(
            {
                "id": c["id"],
                "created_time": created,
                "created_by": c.get("created_by", {}).get("id", "unknown"),
                "text": "".join(text_parts),
            }
        )

    return {"comments": comments, "count": len(comments)}
