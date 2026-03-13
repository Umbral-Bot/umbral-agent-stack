"""
Umbral Worker — Notion API Client

Thin wrapper around the Notion REST API (v2022-06-28).
Uses httpx for HTTP requests. All IDs come from environment variables
via worker.config — never hardcoded.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from . import config

logger = logging.getLogger("worker.notion")

NOTION_BASE_URL = "https://api.notion.com/v1"
TIMEOUT = 60.0


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


def _extract_notion_page_id(page_id_or_url: str) -> str:
    value = (page_id_or_url or "").strip()
    if not value:
        raise ValueError("page_id_or_url is required")

    direct = value.replace("-", "")
    if re.fullmatch(r"[0-9a-fA-F]{32}", direct):
        return value

    match = re.search(r"([0-9a-fA-F]{32})", value)
    if not match:
        raise ValueError(f"Could not extract Notion page id from: {value}")

    raw = match.group(1)
    return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"


def _plain_text_from_rich_text(rich_text: list[Any] | None) -> str:
    if not rich_text:
        return ""
    parts: list[str] = []
    for item in rich_text:
        if isinstance(item, dict):
            parts.append(item.get("plain_text", item.get("text", {}).get("content", "")))
        else:
            parts.append(str(item))
    return "".join(parts)


def _find_property_name(
    properties: dict[str, Any],
    candidates: list[str],
    expected_types: set[str] | None = None,
) -> str | None:
    """Return the first matching property name by exact name + optional type."""
    for candidate in candidates:
        meta = properties.get(candidate)
        if not isinstance(meta, dict):
            continue
        prop_type = str(meta.get("type", ""))
        if expected_types and prop_type not in expected_types:
            continue
        return candidate
    return None


def _extract_block_text(block: dict[str, Any]) -> str:
    block_type = block.get("type", "")
    container = block.get(block_type, {})
    if not isinstance(container, dict):
        return ""

    rich = container.get("rich_text")
    if isinstance(rich, list):
        return _plain_text_from_rich_text(rich)

    title = container.get("title")
    if isinstance(title, list):
        return _plain_text_from_rich_text(title)

    if block_type == "child_page":
        return str(container.get("title", ""))
    if block_type == "child_database":
        return str(container.get("title", ""))

    return ""


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

    logger.info("Creating transcript page: %s (db=%s)", title, db_id)
    with httpx.Client(timeout=TIMEOUT) as client:
        schema_resp = client.get(
            f"{NOTION_BASE_URL}/databases/{db_id}",
            headers=_headers(),
        )
        schema_data = _check_response(schema_resp, "create_transcript_page schema")
        db_properties = schema_data.get("properties") or {}

        title_prop = _find_property_name(
            db_properties,
            ["Name", "Nombre", "Título", "Title"],
            {"title"},
        )
        if not title_prop:
            raise RuntimeError("Notion transcript DB does not have a title property")

        date_prop = _find_property_name(
            db_properties,
            ["Date", "Fecha", "Fecha de transcripción", "Fecha de reunion", "Meeting Date"],
            {"date"},
        )
        status_prop = _find_property_name(
            db_properties,
            ["Estado", "Status"],
            {"select", "status"},
        )
        source_select_prop = _find_property_name(
            db_properties,
            ["Source", "Fuente"],
            {"select"},
        )
        tags_prop = _find_property_name(
            db_properties,
            ["Tags", "Etiquetas"],
            {"multi_select"},
        )
        passed_prop = _find_property_name(
            db_properties,
            ["Fecha que Rick pasó a Notion", "Fecha que Rick paso a Notion", "Imported At"],
            {"date"},
        )
        processed_prop = _find_property_name(
            db_properties,
            ["Fecha que el agente procesó", "Fecha que el agente proceso", "Processed At"],
            {"date"},
        )

        properties: dict[str, Any] = {
            title_prop: {"title": [{"text": {"content": title}}]},
        }

        if date_prop:
            properties[date_prop] = {"date": {"start": date}}

        if status_prop:
            status_type = db_properties[status_prop].get("type")
            if status_type == "status":
                properties[status_prop] = {"status": {"name": "Pendiente"}}
            else:
                properties[status_prop] = {"select": {"name": "Pendiente"}}

        if source_select_prop:
            properties[source_select_prop] = {"select": {"name": source}}
        elif tags_prop:
            properties[tags_prop] = {"multi_select": [{"name": source}]}

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if passed_prop:
            properties[passed_prop] = {"date": {"start": today}}
        if processed_prop:
            properties[processed_prop] = {"date": {"start": today}}

        payload = {
            "parent": {"database_id": db_id},
            "properties": properties,
            "children": blocks,
        }

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
    config.require_notion_core()
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
    config.require_notion_core()
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


def read_page(
    page_id_or_url: str,
    max_blocks: int = 50,
) -> dict[str, Any]:
    """
    Read a Notion page and return metadata plus a plain-text snapshot of its first blocks.

    Args:
        page_id_or_url: Notion page UUID or full URL.
        max_blocks: Maximum number of top-level child blocks to read.

    Returns:
        {
            "page_id": "...",
            "url": "...",
            "last_edited_time": "...",
            "title": "...",
            "blocks": [{"type": "paragraph", "text": "..."}],
            "plain_text": "joined text..."
        }
    """
    config.require_notion_core()
    page_id = _extract_notion_page_id(page_id_or_url)
    max_blocks = max(1, min(int(max_blocks), 100))

    with httpx.Client(timeout=TIMEOUT) as client:
        page_resp = client.get(
            f"{NOTION_BASE_URL}/pages/{page_id}",
            headers=_headers(),
        )
        page_data = _check_response(page_resp, "read_page metadata")

        blocks_resp = client.get(
            f"{NOTION_BASE_URL}/blocks/{page_id}/children",
            headers=_headers(),
            params={"page_size": max_blocks},
        )
        blocks_data = _check_response(blocks_resp, "read_page children")

    title = ""
    properties = page_data.get("properties", {})
    if isinstance(properties, dict):
        for prop in properties.values():
            if isinstance(prop, dict) and prop.get("type") == "title":
                title = _plain_text_from_rich_text(prop.get("title"))
                break

    blocks: list[dict[str, Any]] = []
    for block in blocks_data.get("results", []):
        if not isinstance(block, dict):
            continue
        blocks.append(
            {
                "id": block.get("id", ""),
                "type": block.get("type", ""),
                "text": _extract_block_text(block),
                "has_children": bool(block.get("has_children")),
                "last_edited_time": block.get("last_edited_time", ""),
            }
        )

    plain_text = "\n".join(item["text"] for item in blocks if item.get("text"))

    return {
        "page_id": page_data.get("id", page_id),
        "url": page_data.get("url", ""),
        "last_edited_time": page_data.get("last_edited_time", ""),
        "title": title,
        "blocks": blocks,
        "plain_text": plain_text,
        "has_more": bool(blocks_data.get("has_more")),
        "max_blocks": max_blocks,
    }


def _flatten_property_value(prop: dict[str, Any]) -> Any:
    prop_type = prop.get("type", "")

    if prop_type == "title":
        return _plain_text_from_rich_text(prop.get("title"))
    if prop_type == "rich_text":
        return _plain_text_from_rich_text(prop.get("rich_text"))
    if prop_type == "url":
        return prop.get("url")
    if prop_type == "select":
        return (prop.get("select") or {}).get("name")
    if prop_type == "multi_select":
        return [item.get("name", "") for item in prop.get("multi_select", [])]
    if prop_type == "status":
        return (prop.get("status") or {}).get("name")
    if prop_type == "number":
        return prop.get("number")
    if prop_type == "checkbox":
        return prop.get("checkbox")
    if prop_type == "email":
        return prop.get("email")
    if prop_type == "phone_number":
        return prop.get("phone_number")
    if prop_type == "date":
        return prop.get("date")
    if prop_type == "created_time":
        return prop.get("created_time")
    if prop_type == "last_edited_time":
        return prop.get("last_edited_time")
    if prop_type == "created_by":
        return (prop.get("created_by") or {}).get("id")
    if prop_type == "last_edited_by":
        return (prop.get("last_edited_by") or {}).get("id")
    if prop_type == "people":
        return [
            {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
            }
            for item in prop.get("people", [])
        ]
    if prop_type == "relation":
        return [item.get("id", "") for item in prop.get("relation", [])]
    if prop_type == "files":
        files = []
        for item in prop.get("files", []):
            if not isinstance(item, dict):
                continue
            files.append(
                {
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "url": (item.get("file") or {}).get("url")
                    or (item.get("external") or {}).get("url"),
                }
            )
        return files
    if prop_type == "formula":
        formula = prop.get("formula") or {}
        for key in ("string", "number", "boolean", "date"):
            if key in formula:
                return formula.get(key)
        return formula

    return prop.get(prop_type)


def read_database(
    database_id_or_url: str,
    max_items: int = 50,
    filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Read a Notion database and return schema metadata plus a flattened item snapshot.

    Args:
        database_id_or_url: Notion database UUID or full URL.
        max_items: Maximum number of rows to read.
        filter: Optional Notion database filter object.

    Returns:
        {
            "database_id": "...",
            "url": "...",
            "title": "...",
            "schema": {"Name": "title", ...},
            "items": [
                {
                    "page_id": "...",
                    "url": "...",
                    "title": "...",
                    "properties": {...}
                }
            ],
            "count": N,
            "has_more": bool
        }
    """
    config.require_notion_core()
    database_id = _extract_notion_page_id(database_id_or_url)
    max_items = max(1, min(int(max_items), 100))

    with httpx.Client(timeout=TIMEOUT) as client:
        db_resp = client.get(
            f"{NOTION_BASE_URL}/databases/{database_id}",
            headers=_headers(),
        )
        db_data = _check_response(db_resp, "read_database metadata")

        query_body: dict[str, Any] = {"page_size": max_items}
        if filter:
            query_body["filter"] = filter
        rows_resp = client.post(
            f"{NOTION_BASE_URL}/databases/{database_id}/query",
            headers=_headers(),
            json=query_body,
        )
        rows_data = _check_response(rows_resp, "read_database query")

    title = _plain_text_from_rich_text(db_data.get("title"))
    schema: dict[str, str] = {}
    for prop_name, prop_meta in (db_data.get("properties") or {}).items():
        if isinstance(prop_meta, dict):
            schema[prop_name] = str(prop_meta.get("type", ""))

    items: list[dict[str, Any]] = []
    for row in rows_data.get("results", []):
        if not isinstance(row, dict):
            continue

        flat_props: dict[str, Any] = {}
        row_title = ""
        properties = row.get("properties") or {}
        if isinstance(properties, dict):
            for prop_name, prop_value in properties.items():
                if not isinstance(prop_value, dict):
                    continue
                flat_value = _flatten_property_value(prop_value)
                flat_props[prop_name] = flat_value
                if prop_value.get("type") == "title" and not row_title:
                    row_title = str(flat_value or "")

        items.append(
            {
                "page_id": row.get("id", ""),
                "url": row.get("url", ""),
                "title": row_title,
                "properties": flat_props,
            }
        )

    return {
        "database_id": db_data.get("id", database_id),
        "url": db_data.get("url", ""),
        "title": title,
        "schema": schema,
        "items": items,
        "count": len(items),
        "has_more": bool(rows_data.get("has_more")),
        "max_items": max_items,
    }


def search_databases(
    query: str,
    max_results: int = 10,
) -> dict[str, Any]:
    """
    Search Notion databases by title.

    Args:
        query: Search query string.
        max_results: Maximum number of databases to return.

    Returns:
        {
            "query": "...",
            "results": [
                {"database_id": "...", "title": "...", "url": "...", "last_edited_time": "..."}
            ],
            "count": N
        }
    """
    config.require_notion_core()
    query = (query or "").strip()
    if not query:
        raise ValueError("query is required")
    max_results = max(1, min(int(max_results), 20))

    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{NOTION_BASE_URL}/search",
            headers=_headers(),
            json={
                "query": query,
                "page_size": max_results,
                "filter": {"value": "database", "property": "object"},
            },
        )
        data = _check_response(resp, "search_databases")

    results: list[dict[str, Any]] = []
    for item in data.get("results", []):
        if not isinstance(item, dict):
            continue
        title = _plain_text_from_rich_text(item.get("title"))
        results.append(
            {
                "database_id": item.get("id", ""),
                "title": title,
                "url": item.get("url", ""),
                "last_edited_time": item.get("last_edited_time", ""),
            }
        )

    return {
        "query": query,
        "results": results,
        "count": len(results),
    }


def create_database_page(
    database_id_or_url: str,
    properties: dict[str, Any],
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Create a page inside an existing Notion database using raw Notion API properties.

    Args:
        database_id_or_url: Notion database UUID or full URL.
        properties: Raw Notion page properties payload.
        children: Optional list of child blocks to append.

    Returns:
        {"page_id": "...", "url": "...", "created": True}
    """
    config.require_notion_core()
    database_id = _extract_notion_page_id(database_id_or_url)
    if not isinstance(properties, dict) or not properties:
        raise ValueError("properties must be a non-empty dict")

    payload: dict[str, Any] = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    if children:
        payload["children"] = children[:100]

    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{NOTION_BASE_URL}/pages",
            headers=_headers(),
            json=payload,
        )
        result = _check_response(resp, "create_database_page")
        page_id = result["id"]

        if children and len(children) > 100:
            for i in range(100, len(children), 100):
                batch = children[i : i + 100]
                resp = client.patch(
                    f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                    headers=_headers(),
                    json={"children": batch},
                )
                _check_response(resp, "append create_database_page blocks")

    return {"page_id": page_id, "url": result.get("url", ""), "created": True}


def update_page_properties(
    page_id_or_url: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    """
    Update raw Notion page properties for an existing page.

    Args:
        page_id_or_url: Notion page UUID or full URL.
        properties: Raw Notion properties payload to PATCH.

    Returns:
        {"page_id": "...", "url": "...", "updated": True}
    """
    config.require_notion_core()
    page_id = _extract_notion_page_id(page_id_or_url)
    if not isinstance(properties, dict) or not properties:
        raise ValueError("properties must be a non-empty dict")

    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.patch(
            f"{NOTION_BASE_URL}/pages/{page_id}",
            headers=_headers(),
            json={"properties": properties},
        )
        result = _check_response(resp, "update_page_properties")

    return {"page_id": result.get("id", page_id), "url": result.get("url", ""), "updated": True}


PROVIDER_LABELS = {
    "azure_foundry": "Azure Foundry (GPT-5.2 Chat)",
    "claude_pro": "Claude Sonnet 4.6",
    "claude_opus": "Claude Opus 4.6",
    "claude_haiku": "Claude Haiku 4.5",
    "gemini_pro": "Gemini 2.5 Pro",
    "gemini_flash": "Gemini 2.5 Flash",
    "gemini_flash_lite": "Gemini 2.5 Flash Lite",
    "gemini_vertex": "Gemini Vertex 2.5 Flash",
}


def _rich(text: str, bold: bool = False, color: str = "default") -> dict[str, Any]:
    rt: dict[str, Any] = {"type": "text", "text": {"content": text[:2000]}}
    if bold or color != "default":
        rt["annotations"] = {"bold": bold, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": color}
    return rt


def _block_heading1(text: str, toggleable: bool = False) -> dict[str, Any]:
    return {"object": "block", "type": "heading_1", "heading_1": {"rich_text": [_rich(text)], "color": "default", "is_toggleable": toggleable}}

def _block_heading2(text: str, toggleable: bool = False) -> dict[str, Any]:
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [_rich(text)], "color": "default", "is_toggleable": toggleable}}

def _block_heading3(text: str, toggleable: bool = False) -> dict[str, Any]:
    return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [_rich(text)], "color": "default", "is_toggleable": toggleable}}

def _block_paragraph(text: str, color: str = "default") -> dict[str, Any]:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [_rich(text)], "color": color}}

def _block_paragraph_rich(parts: list[dict[str, Any]], color: str = "default") -> dict[str, Any]:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": parts, "color": color}}

def _block_callout(text: str, emoji: str = "🟢", color: str = "default") -> dict[str, Any]:
    return {"object": "block", "type": "callout", "callout": {"rich_text": [_rich(text)], "icon": {"type": "emoji", "emoji": emoji}, "color": color}}

def _block_divider() -> dict[str, Any]:
    return {"object": "block", "type": "divider", "divider": {}}

def _block_table(headers: list[str], rows: list[list[str]], bold_header: bool = True) -> dict[str, Any]:
    width = len(headers)
    table_rows = []
    if bold_header:
        header_cells = [[_rich(h[:200], bold=True)] for h in headers]
    else:
        header_cells = [[_rich(h[:200])] for h in headers]
    table_rows.append({"type": "table_row", "table_row": {"cells": header_cells}})
    for row in rows:
        cells = [[_rich(str(c)[:200])] for c in row]
        while len(cells) < width:
            cells.append([_rich("—")])
        table_rows.append({"type": "table_row", "table_row": {"cells": cells[:width]}})
    return {
        "object": "block",
        "type": "table",
        "table": {"table_width": width, "has_column_header": True, "has_row_header": False, "children": table_rows},
    }

def _block_toggle(text: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    return {"object": "block", "type": "toggle", "toggle": {"rich_text": [_rich(text)], "children": children}}

def _block_column_list(columns: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Creates a column_list with N columns. Each column is a list of child blocks."""
    col_blocks = []
    n = len(columns)
    for col_children in columns:
        col_blocks.append({
            "object": "block",
            "type": "column",
            "column": {"width_ratio": round(1.0 / n, 2), "children": col_children},
        })
    return {"object": "block", "type": "column_list", "column_list": {"children": col_blocks}}

def _block_bulleted(text: str, color: str = "default") -> dict[str, Any]:
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [_rich(text)], "color": color}}

def _block_quote(text: str, color: str = "default") -> dict[str, Any]:
    return {"object": "block", "type": "quote", "quote": {"rich_text": [_rich(text)], "color": color}}

def _block_code(text: str, language: str = "plain text") -> dict[str, Any]:
    return {"object": "block", "type": "code", "code": {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}], "language": language}}


def _quota_zone(pct: float) -> str:
    if pct >= 90:
        return "CRITICO"
    if pct >= 70:
        return "ALERTA"
    return "OK"


def _build_dashboard_v2_blocks(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Construye bloques ricos para dashboard v2 con layout avanzado."""
    blocks: list[dict[str, Any]] = []
    ts = data.get("timestamp", "?")
    overall = data.get("overall_status", "?")

    emoji_map = {"Operativo": "🟢", "Parcial (Redis offline)": "🟡", "Degradado": "🔴"}
    color_map = {"Operativo": "green_background", "Parcial (Redis offline)": "yellow_background", "Degradado": "red_background"}
    status_emoji = emoji_map.get(overall, "⚪")
    status_color = color_map.get(overall, "default")

    blocks.append(_block_heading1("Dashboard Rick"))
    blocks.append(_block_callout(f"Estado: {overall}  —  {ts}", status_emoji, status_color))

    # KPI summary row
    ops = data.get("ops_summary", {})
    rd = data.get("redis", {})
    alerts = data.get("active_alerts", [])
    kpi_parts = [
        _rich("Tareas hoy: ", bold=True),
        _rich(str(ops.get("completed_today", ops.get("completed", 0)))),
        _rich("  |  Exito: ", bold=True),
        _rich(f"{ops.get('success_rate', 0)}%"),
        _rich("  |  Cola: ", bold=True),
        _rich(str(rd.get("pending", 0))),
        _rich("  |  Alertas: ", bold=True),
        _rich(str(len(alerts)), color="red" if alerts else "default"),
    ]
    blocks.append(_block_paragraph_rich(kpi_parts))
    blocks.append(_block_divider())

    # Release tracking snapshot (R16/R17)
    tracking = data.get("release_tracking") or {}
    if tracking:
        r16 = tracking.get("r16", {})
        r17 = tracking.get("r17", {})
        tests_passed = tracking.get("tests_passed", "—")
        tracking_rows = [
            [
                "R16",
                str(r16.get("status", "Cerrada")),
                str(r16.get("prs", "PRs #85-#90 mergeados")),
            ],
            [
                "R17",
                str(r17.get("status", "Cerrada")),
                str(r17.get("prs", "PRs #91-#96 mergeados")),
            ],
            ["Tests", f"{tests_passed} passed", "pytest tests/ -q"],
            ["Ultima actualizacion", str(ts), "Timestamp del run"],
        ]
        blocks.append(_block_heading2("Seguimiento R16/R17"))
        blocks.append(_block_table(["Bloque", "Estado", "Detalle"], tracking_rows))
        blocks.append(_block_divider())

    # Active alerts
    if alerts:
        blocks.append(_block_callout("  ".join(alerts), "🚨", "red_background"))

    # Infrastructure: Workers + Redis in columns
    blocks.append(_block_heading2("Infraestructura"))
    vps = data.get("vps_worker", {})
    vm = data.get("vm_worker")
    vm_int = data.get("vm_worker_interactive")
    vps_icon = "🟢" if vps.get("status") == "OK" else "🔴"
    vm_icon = "🟢" if vm and vm.get("status") == "OK" else ("🔴" if vm else "⚫")
    vm_int_icon = "🟢" if vm_int and vm_int.get("status") == "OK" else ("🔴" if vm_int else "⚫")
    redis_icon = "🟢" if rd.get("connected") else "🔴"

    infra_rows = [
        [f"{vps_icon} Worker VPS", vps.get("status", "?"), f'{len(vps.get("tasks", []))} tareas'],
    ]
    if vm:
        infra_rows.append([f"{vm_icon} Worker VM (8088)", vm.get("status", "?"), f'{len(vm.get("tasks", []))} tareas'])
    if vm_int is not None:
        infra_rows.append([f"{vm_int_icon} Worker VM interactivo (8089)", vm_int.get("status", "?"), f'{len(vm_int.get("tasks", []))} tareas'])
    infra_rows.append([f"{redis_icon} Redis", "Conectado" if rd.get("connected") else "Offline", f'Cola: {rd.get("pending", 0)} | Bloq: {rd.get("blocked", 0)}'])

    uptime = data.get("uptime")
    if uptime:
        infra_rows.append(["⏱ Uptime", uptime, ""])

    blocks.append(_block_table(["Componente", "Estado", "Detalle"], infra_rows))
    blocks.append(_block_divider())

    # Quotas
    quotas = data.get("quotas", [])
    if quotas:
        blocks.append(_block_heading2("Cuotas por Modelo"))
        quota_rows = []
        for q in quotas:
            label = PROVIDER_LABELS.get(q["provider"], q["provider"])
            pct = q["pct"]
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            zone = _quota_zone(pct)
            zone_icon = {"OK": "🟢", "ALERTA": "🟡", "CRITICO": "🔴"}.get(zone, "⚪")
            remaining = q["limit"] - q["used"]
            resets_in = q.get("resets_in_min")
            reset_str = f"{resets_in} min" if resets_in else f"{q['window_h']}h ventana"
            quota_rows.append([
                f"{zone_icon} {label}",
                f"{q['used']}/{q['limit']}",
                f"{pct}% {bar}",
                f"{remaining} restantes",
                reset_str,
            ])
        blocks.append(_block_table(["Proveedor", "Usado/Limite", "Uso", "Restante", "Reinicio"], quota_rows))
        blocks.append(_block_divider())

    # Teams with dynamic stats
    teams = data.get("teams", [])
    if teams:
        blocks.append(_block_heading2("Equipos"))
        team_rows = []
        for t in teams:
            vm_flag = "VM" if t.get("requires_vm") else "VPS"
            completed = t.get("completed", 0)
            active = t.get("active", 0)
            status_str = f"{active} activas, {completed} completadas" if (active or completed) else "Sin actividad"
            team_rows.append([t["team"].capitalize(), t.get("supervisor", "—"), vm_flag, status_str])
        blocks.append(_block_table(["Equipo", "Supervisor", "Plano", "Actividad"], team_rows))
        blocks.append(_block_divider())

    # Recent tasks with timestamps
    recent = data.get("recent_tasks", [])
    if recent:
        blocks.append(_block_heading2("Tareas Recientes"))
        task_rows = []
        for t in recent:
            status_icon = "✅" if t["status"] == "done" else "❌"
            when = t.get("when", "")
            task_rows.append([f"{status_icon} {t['task']}", t["team"], f"{t['duration_s']}s", when, t["task_id"]])
        blocks.append(_block_table(["Tarea", "Equipo", "Duracion", "Cuando", "ID"], task_rows))

        # Last error if any failures
        last_error = data.get("last_error")
        if last_error:
            blocks.append(_block_callout(f"Ultimo error: {last_error}", "⚠️", "red_background"))
        blocks.append(_block_divider())

    # Running tasks
    running = data.get("running_tasks", [])
    if running:
        blocks.append(_block_heading3("En ejecucion ahora"))
        run_rows = [[t["task"], t["team"], t.get("elapsed", "?")] for t in running]
        blocks.append(_block_table(["Tarea", "Equipo", "Tiempo"], run_rows))
        blocks.append(_block_divider())

    # Operations summary
    if ops.get("total_events", 0) > 0:
        blocks.append(_block_heading2("Operaciones"))
        trend = ops.get("trend", "")
        trend_text = f"  ({trend})" if trend else ""

        ops_parts = [
            _rich("Completadas: ", bold=True), _rich(str(ops.get("completed", 0))),
            _rich("  |  Fallidas: ", bold=True), _rich(str(ops.get("failed", 0)), color="red" if ops.get("failed", 0) > 0 else "default"),
            _rich("  |  Tasa exito: ", bold=True), _rich(f"{ops.get('success_rate', 0)}%{trend_text}"),
        ]
        blocks.append(_block_paragraph_rich(ops_parts))

        models = ops.get("models_used", {})
        if models:
            model_rows = [[PROVIDER_LABELS.get(m, m), str(c)] for m, c in sorted(models.items(), key=lambda x: -x[1])]
            blocks.append(_block_table(["Modelo", "Requests"], model_rows))

    return blocks


def update_dashboard_page(page_id: str | None, metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Reemplaza el contenido de la página Dashboard con un snapshot de métricas.
    Soporta v2 (bloques ricos) y v1 (simple heading+paragraph).

    Args:
        page_id: ID de la página Dashboard. Default: NOTION_DASHBOARD_PAGE_ID.
        metrics: Dict con datos del dashboard (v2 si tiene "dashboard_v2": True).

    Returns:
        {"updated": True, "blocks_appended": N}.
    """
    if not config.NOTION_API_KEY:
        raise RuntimeError("NOTION_API_KEY not configured")
    if page_id is None:
        page_id = config.NOTION_DASHBOARD_PAGE_ID
    if not page_id:
        raise ValueError("NOTION_DASHBOARD_PAGE_ID not set and page_id not provided")

    if metrics.get("dashboard_v2"):
        blocks = _build_dashboard_v2_blocks(metrics)
    else:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        blocks = [_block_heading2("Dashboard Rick — Estado del proyecto"), _block_paragraph(f"Última actualización: {now}")]
        for name, value in metrics.items():
            blocks.append(_block_heading3(str(name)))
            blocks.append(_block_paragraph(str(value)[:2000]))

    with httpx.Client(timeout=TIMEOUT) as client:
        next_cursor = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if next_cursor:
                params["start_cursor"] = next_cursor
            resp = client.get(
                f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=_headers(),
                params=params,
            )
            data = _check_response(resp, "list block children")
            block_ids = [b["id"] for b in data.get("results", []) if b.get("id") and b.get("type") != "child_page"]
            for bid in block_ids:
                client.patch(
                    f"{NOTION_BASE_URL}/blocks/{bid}",
                    headers=_headers(),
                    json={"in_trash": True},
                )
            next_cursor = data.get("next_cursor")
            if not next_cursor:
                break

        for i in range(0, len(blocks), 100):
            chunk = blocks[i : i + 100]
            resp = client.patch(
                f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=_headers(),
                json={"children": chunk},
            )
            _check_response(resp, "append dashboard blocks")

    logger.info("Dashboard page %s updated with %d blocks", page_id[:8], len(blocks))
    return {"updated": True, "blocks_appended": len(blocks)}


def upsert_task(
    task_id: str,
    status: str,
    team: str,
    task: str,
    input_summary: str | None = None,
    error: str | None = None,
    result_summary: str | None = None,
) -> dict[str, Any]:
    """
    Crea o actualiza una página en la DB "Tareas Umbral" (Kanban tracking).
    Busca por Task ID; si existe actualiza; si no existe crea.

    Estados: En cola, En curso, Hecho, Bloqueado, Fallido
    """
    if not config.NOTION_API_KEY or not config.NOTION_TASKS_DB_ID:
        logger.warning("Notion tasks DB not configured (NOTION_TASKS_DB_ID); skipping upsert_task")
        return {"skipped": True, "reason": "NOTION_TASKS_DB_ID not set"}

    db_id = config.NOTION_TASKS_DB_ID
    notion_status = status if status in ("queued", "running", "done", "failed", "blocked") else "queued"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    title_text = task[:2000] if task else f"Task {task_id[:8]}"
    input_preview = (input_summary or "")[:200] if input_summary else "—"
    error_preview = (error or "")[:200] if error else ""
    result_preview = (result_summary or "")[:200] if result_summary else ""
    summary = result_preview if result_preview else (error_preview if error_preview else input_preview)

    properties: dict[str, Any] = {
        "Task": {"title": [{"text": {"content": title_text}}]},
        "Status": {"select": {"name": notion_status}},
        "Team": {"select": {"name": team}},
        "Task ID": {"rich_text": [{"text": {"content": task_id[:2000]}}]},
        "Result Summary": {"rich_text": [{"text": {"content": summary[:2000] or "—"}}]},
    }
    if error_preview:
        properties["Error"] = {"rich_text": [{"text": {"content": error_preview[:2000]}}]}
    if input_preview and input_preview != "—":
        properties["Input Summary"] = {"rich_text": [{"text": {"content": input_preview[:2000]}}]}
    if team:
        properties["Model"] = {"rich_text": [{"text": {"content": team}}]}

    with httpx.Client(timeout=TIMEOUT) as client:
        # Query by Task ID
        resp = client.post(
            f"{NOTION_BASE_URL}/databases/{db_id}/query",
            headers=_headers(),
            json={"filter": {"property": "Task ID", "rich_text": {"equals": task_id}}},
        )
        data = _check_response(resp, "query tasks")
        results = data.get("results", [])

        if results:
            page_id = results[0]["id"]
            resp = client.patch(
                f"{NOTION_BASE_URL}/pages/{page_id}",
                headers=_headers(),
                json={"properties": properties},
            )
            _check_response(resp, "update task")
            logger.info("Updated task %s in Notion (status=%s)", task_id[:8], notion_status)
            return {"page_id": page_id, "updated": True}
        else:
            properties["Created"] = {"date": {"start": now}}
            resp = client.post(
                f"{NOTION_BASE_URL}/pages",
                headers=_headers(),
                json={
                    "parent": {"database_id": db_id},
                    "properties": properties,
                },
            )
            result = _check_response(resp, "create task")
            logger.info("Created task %s in Notion (status=%s)", task_id[:8], notion_status)
            return {"page_id": result["id"], "url": result.get("url", ""), "created": True}


def create_report_page(
    parent_page_id: str | None,
    title: str,
    content_blocks: list[dict[str, Any]],
    sources: list[dict[str, Any]] | None = None,
    queries: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a child page under a Notion page with a structured report.

    Args:
        parent_page_id: Parent page ID. Defaults to NOTION_CONTROL_ROOM_PAGE_ID.
        title: Page title (e.g. "SIM Report: AI trends — 2026-03-04").
        content_blocks: List of Notion block dicts (from notion_markdown.markdown_to_blocks).
        sources: Optional list of source dicts (title, url).
        queries: Optional list of search queries used.
        metadata: Optional dict with extra metadata (team, topic, etc).

    Returns:
        {"page_id": "...", "page_url": "...", "ok": True}
    """
    config.require_notion_core()
    if parent_page_id is None:
        parent_page_id = config.NOTION_CONTROL_ROOM_PAGE_ID

    # Build children blocks: content + sources + queries
    children: list[dict[str, Any]] = []

    # Main content
    children.extend(content_blocks[:95])  # Leave room for sources/queries (max 100 children)

    # Sources section
    if sources:
        children.append(_block_divider())
        children.append(_block_heading2("Fuentes"))
        for src in sources[:20]:
            src_title = src.get("title", "Sin título")
            src_url = src.get("url", "")
            if src_url:
                children.append(_block_bulleted(f"{src_title} — {src_url}"))
            else:
                children.append(_block_bulleted(src_title))

    # Queries section
    if queries:
        children.append(_block_divider())
        children.append(_block_heading3("Queries utilizadas"))
        for q in queries[:15]:
            children.append(_block_bulleted(q))

    # Metadata callout
    if metadata:
        meta_parts = []
        for k, v in metadata.items():
            meta_parts.append(f"{k}: {v}")
        children.append(_block_divider())
        children.append(_block_callout(" | ".join(meta_parts), "📋", "gray_background"))

    # Notion API max 100 children per request
    payload = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": {"title": [{"text": {"content": title[:2000]}}]},
        },
        "children": children[:100],
    }

    logger.info("Creating report page: %s under %s", title[:60], parent_page_id[:8])
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{NOTION_BASE_URL}/pages",
            headers=_headers(),
            json=payload,
        )
    result = _check_response(resp, "create_report_page")
    page_id = result["id"]
    page_url = result.get("url", "")

    # If more than 100 children, append the rest in batches
    if len(children) > 100:
        with httpx.Client(timeout=TIMEOUT) as client:
            for i in range(100, len(children), 100):
                batch = children[i:i + 100]
                resp = client.patch(
                    f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                    headers=_headers(),
                    json={"children": batch},
                )
                _check_response(resp, "append report blocks")

    logger.info("Created report page: %s (%s)", page_id, page_url)
    return {"page_id": page_id, "page_url": page_url, "ok": True}


# ---------------------------------------------------------------------------
# Bitácora helpers
# ---------------------------------------------------------------------------


def query_database(
    database_id: str,
    filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Query a Notion database with automatic pagination.

    Args:
        database_id: The Notion database ID.
        filter: Optional Notion filter object.

    Returns:
        List of page objects from the database.
    """
    if not config.NOTION_API_KEY:
        raise RuntimeError("NOTION_API_KEY not configured")

    results: list[dict[str, Any]] = []

    with httpx.Client(timeout=TIMEOUT) as client:
        next_cursor: str | None = None
        while True:
            body: dict[str, Any] = {}
            if filter:
                body["filter"] = filter
            if next_cursor:
                body["start_cursor"] = next_cursor

            resp = client.post(
                f"{NOTION_BASE_URL}/databases/{database_id}/query",
                headers=_headers(),
                json=body,
            )
            data = _check_response(resp, "query_database")
            results.extend(data.get("results", []))
            next_cursor = data.get("next_cursor")
            if not next_cursor:
                break

    logger.info("Queried database %s: %d results", database_id[:8], len(results))
    return results


def append_blocks_to_page(
    page_id: str,
    blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Append blocks as children of a Notion page.

    Args:
        page_id: The page to append blocks to.
        blocks: List of Notion block dicts.

    Returns:
        {"blocks_appended": N, "page_id": "..."}
    """
    if not config.NOTION_API_KEY:
        raise RuntimeError("NOTION_API_KEY not configured")

    with httpx.Client(timeout=TIMEOUT) as client:
        for i in range(0, len(blocks), 100):
            chunk = blocks[i : i + 100]
            resp = client.patch(
                f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=_headers(),
                json={"children": chunk},
            )
            _check_response(resp, "append_blocks_to_page")

    logger.info("Appended %d blocks to page %s", len(blocks), page_id[:8])
    return {"blocks_appended": len(blocks), "page_id": page_id}


_WRITABLE_BLOCK_TYPES = {
    "paragraph", "heading_1", "heading_2", "heading_3",
    "bulleted_list_item", "numbered_list_item",
    "code", "quote", "callout", "divider", "table",
    "toggle", "to_do", "embed", "bookmark", "image",
}


def _convert_block_for_write(
    block: dict[str, Any],
    client: Any,
) -> dict[str, Any] | None:
    """
    Convert a Notion API read-format block to write-format.

    Strips read-only fields (id, has_children, created_time, etc.)
    and returns only the type + type-specific payload.
    Returns None for unsupported block types (child_database, child_page, etc.).
    """
    block_type = block.get("type", "")

    if block_type not in _WRITABLE_BLOCK_TYPES:
        return None

    result: dict[str, Any] = {"type": block_type}
    type_data = block.get(block_type)
    if type_data is not None:
        result[block_type] = type_data
    else:
        result[block_type] = {}

    return result


def prepend_blocks_to_page(
    page_id: str,
    blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Prepend blocks to a Notion page by deleting existing blocks and
    re-appending with new blocks first, then the old blocks.

    Args:
        page_id: The page to prepend blocks to.
        blocks: New blocks to place at the beginning.

    Returns:
        {"blocks_prepended": N, "blocks_preserved": M, "page_id": "..."}
    """
    if not config.NOTION_API_KEY:
        raise RuntimeError("NOTION_API_KEY not configured")

    with httpx.Client(timeout=TIMEOUT) as client:
        # 1. Read existing blocks
        existing_blocks: list[dict[str, Any]] = []
        next_cursor: str | None = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if next_cursor:
                params["start_cursor"] = next_cursor
            resp = client.get(
                f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=_headers(),
                params=params,
            )
            data = _check_response(resp, "list blocks for prepend")
            existing_blocks.extend(data.get("results", []))
            next_cursor = data.get("next_cursor")
            if not next_cursor:
                break

        # 2. Delete existing blocks
        for eb in existing_blocks:
            bid = eb.get("id")
            if bid:
                client.patch(
                    f"{NOTION_BASE_URL}/blocks/{bid}",
                    headers=_headers(),
                    json={"in_trash": True},
                )

        # 3. Convert old blocks for re-writing
        old_write_blocks: list[dict[str, Any]] = []
        for eb in existing_blocks:
            converted = _convert_block_for_write(eb, client)
            if converted is not None:
                old_write_blocks.append(converted)

        # 4. Append new blocks first, then old blocks
        all_blocks = list(blocks) + old_write_blocks
        for i in range(0, len(all_blocks), 100):
            chunk = all_blocks[i : i + 100]
            resp = client.patch(
                f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=_headers(),
                json={"children": chunk},
            )
            _check_response(resp, "prepend blocks")

    logger.info(
        "Prepended %d blocks, preserved %d in page %s",
        len(blocks), len(old_write_blocks), page_id[:8],
    )
    return {
        "blocks_prepended": len(blocks),
        "blocks_preserved": len(old_write_blocks),
        "page_id": page_id,
    }
