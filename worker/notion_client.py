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


def update_dashboard_page(page_id: str | None, metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Reemplaza el contenido de la página Dashboard con un snapshot de métricas.
    Archiva los bloques hijos existentes y añade nuevos (doc 22).

    Args:
        page_id: ID de la página Dashboard. Default: NOTION_DASHBOARD_PAGE_ID.
        metrics: Dict nombre_metric -> valor (str o número). Ej: {"Estado general": "Operativo", "Worker VPS": "OK"}.

    Returns:
        {"updated": True, "blocks_appended": N}.
    """
    if not config.NOTION_API_KEY:
        raise RuntimeError("NOTION_API_KEY not configured")
    if page_id is None:
        page_id = config.NOTION_DASHBOARD_PAGE_ID
    if not page_id:
        raise ValueError("NOTION_DASHBOARD_PAGE_ID not set and page_id not provided")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    blocks: list[dict[str, Any]] = []

    # Título de sección + última actualización
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Dashboard Rick — Estado del proyecto"}}]},
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Última actualización: {now}"}}]},
    })

    for name, value in metrics.items():
        text = str(value)[:2000]
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": name[:2000]}}]},
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        })

    with httpx.Client(timeout=TIMEOUT) as client:
        # 1. Listar hijos y archivar (paginated)
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
            for block in data.get("results", []):
                bid = block.get("id")
                if bid and block.get("type") != "child_page":
                    client.patch(
                        f"{NOTION_BASE_URL}/blocks/{bid}",
                        headers=_headers(),
                        json={"archived": True},
                    )
            next_cursor = data.get("next_cursor")
            if not next_cursor:
                break

        # 2. Añadir nuevos bloques (máx 100 por request)
        for i in range(0, len(blocks), 100):
            chunk = blocks[i : i + 100]
            resp = client.patch(
                f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=_headers(),
                json={"children": chunk},
            )
            _check_response(resp, "append dashboard blocks")

    logger.info("Dashboard page %s updated with %d metrics", page_id[:8], len(metrics))
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
        logger.debug("Notion tasks DB not configured (NOTION_TASKS_DB_ID); skipping upsert_task")
        return {"skipped": True, "reason": "NOTION_TASKS_DB_ID not set"}

    db_id = config.NOTION_TASKS_DB_ID
    status_map = {
        "queued": "En cola",
        "running": "En curso",
        "done": "Hecho",
        "failed": "Fallido",
        "blocked": "Bloqueado",
    }
    notion_status = status_map.get(status, status)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    title_text = task[:2000] if task else f"Task {task_id[:8]}"
    input_preview = (input_summary or "")[:200] if input_summary else "—"
    error_preview = (error or "")[:200] if error else ""
    result_preview = (result_summary or "")[:200] if result_summary else ""
    resumen = result_preview if result_preview else (error_preview if error_preview else input_preview)

    properties: dict[str, Any] = {
        "Tarea": {"title": [{"text": {"content": title_text}}]},
        "Estado": {"select": {"name": notion_status}},
        "Agente": {"select": {"name": team}},
        "Task ID": {"rich_text": [{"text": {"content": task_id[:2000]}}]},
        "Actualizada": {"date": {"start": now}},
        "Resumen": {"rich_text": [{"text": {"content": resumen[:2000] or "—"}}]},
    }

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
            client.patch(
                f"{NOTION_BASE_URL}/pages/{page_id}",
                headers=_headers(),
                json={"properties": properties},
            )
            logger.info("Updated task %s in Notion (status=%s)", task_id[:8], notion_status)
            return {"page_id": page_id, "updated": True}
        else:
            properties["Creada"] = {"date": {"start": now}}
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
