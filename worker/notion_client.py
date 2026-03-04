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


PROVIDER_LABELS = {
    "azure_foundry": "Azure Foundry (GPT-5.3 Codex)",
    "claude_pro": "Claude Sonnet 4.6",
    "claude_opus": "Claude Opus 4.6",
    "claude_haiku": "Claude Haiku 4.5",
    "gemini_pro": "Gemini Pro (customtools)",
    "gemini_flash": "Gemini Flash",
    "gemini_flash_lite": "Gemini Flash Lite",
    "gemini_vertex": "Gemini Vertex 3.1 Pro",
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
        logger.debug("Notion tasks DB not configured (NOTION_TASKS_DB_ID); skipping upsert_task")
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
            client.patch(
                f"{NOTION_BASE_URL}/pages/{page_id}",
                headers=_headers(),
                json={"properties": properties},
            )
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
