#!/usr/bin/env python3
"""
SIM Daily Report.

Genera un resumen diario de ejecuciones SIM usando eventos de ops_log y,
opcionalmente, publica el reporte en Notion mediante `notion.add_comment`.

Uso:
  python scripts/sim_daily_report.py
  python scripts/sim_daily_report.py --dry-run
  python scripts/sim_daily_report.py --notion
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from client.worker_client import WorkerClient
from dispatcher.extractors.notion_comment_paginator import (
    SAFE_LIMIT,
    post_long_comment,
)
from infra.ops_logger import OpsLogger

SIM_TASKS = {"research.web", "llm.generate"}
SIM_EVENTS = {"task_completed", "task_failed"}
MAX_COMMENT_CHARS = SAFE_LIMIT  # kept for backwards-compat; use SAFE_LIMIT


def _parse_ts(raw_ts: str) -> datetime | None:
    if not raw_ts:
        return None
    try:
        dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _filter_recent_sim_events(events: list[dict[str, Any]], now: datetime, hours: int) -> list[dict[str, Any]]:
    cutoff = now - timedelta(hours=hours)
    filtered: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event") not in SIM_EVENTS:
            continue
        if ev.get("task") not in SIM_TASKS:
            continue
        ts = _parse_ts(ev.get("ts", ""))
        if ts and ts >= cutoff:
            filtered.append(ev)
    filtered.sort(key=lambda e: e.get("ts", ""))
    return filtered


def _load_task_details(task_ids: list[str]) -> dict[str, dict[str, Any]]:
    """
    Intenta enriquecer con task payload/result desde Redis.
    Si Redis no está disponible, regresa dict vacío sin fallar.
    """
    try:
        import redis
    except Exception:
        return {}

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    details: dict[str, dict[str, Any]] = {}
    try:
        client = redis.from_url(redis_url, decode_responses=True)
        for task_id in task_ids:
            raw = client.get(f"umbral:task:{task_id}")
            if not raw:
                continue
            try:
                details[task_id] = json.loads(raw)
            except json.JSONDecodeError:
                continue
    except Exception:
        return {}
    return details


def _extract_query(task_payload: dict[str, Any]) -> str:
    input_data = task_payload.get("input", {})
    query = input_data.get("query", "")
    return str(query).strip()


def _extract_llm_text(task_payload: dict[str, Any]) -> str:
    payload = _extract_result_payload(task_payload)
    text = payload.get("text", "")
    return str(text).strip()


def _extract_result_payload(task_payload: dict[str, Any]) -> dict[str, Any]:
    result = task_payload.get("result", {})
    if not isinstance(result, dict):
        return {}

    # WorkerClient.run devuelve {"ok": ..., "result": {...}}
    inner = result.get("result", result)
    if not isinstance(inner, dict):
        return {}
    return inner


def _extract_research_urls(task_payload: dict[str, Any], max_urls_per_task: int = 3) -> list[str]:
    payload = _extract_result_payload(task_payload)
    items = payload.get("results", [])
    if not isinstance(items, list):
        return []

    urls: list[str] = []
    seen_urls = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not url or url in seen_urls:
            continue
        urls.append(url)
        seen_urls.add(url)
        if len(urls) >= max_urls_per_task:
            break
    return urls


def _trim_for_comment(text: str, max_chars: int = MAX_COMMENT_CHARS) -> str:
    """DEPRECATED (Task 036b): silent truncator. Kept only for legacy callers.

    The SIM daily report writer now routes oversized payloads through
    :func:`dispatcher.extractors.notion_comment_paginator.post_long_comment`,
    which never silently drops content.
    """
    if len(text) <= max_chars:
        return text
    suffix = "\n\n[truncated]"
    return text[: max_chars - len(suffix)] + suffix


def build_report(
    events: list[dict[str, Any]],
    task_details: dict[str, dict[str, Any]],
    now: datetime,
    window_hours: int,
    max_topics: int = 12,
    max_urls: int = 12,
) -> str:
    research_events = [e for e in events if e.get("task") == "research.web"]
    llm_events = [e for e in events if e.get("task") == "llm.generate"]

    research_total = len(research_events)
    research_ok = sum(1 for e in research_events if e.get("event") == "task_completed")
    research_failed = research_total - research_ok

    llm_total = len(llm_events)
    llm_ok = sum(1 for e in llm_events if e.get("event") == "task_completed")
    llm_failed = llm_total - llm_ok

    team_counter = Counter(e.get("team", "unknown") for e in research_events)

    topics: list[str] = []
    seen = set()
    urls: list[str] = []
    seen_urls = set()
    for ev in research_events:
        detail = task_details.get(ev.get("task_id", ""))
        if not detail:
            continue
        query = _extract_query(detail)
        if query and query not in seen:
            topics.append(query)
            seen.add(query)
        for url in _extract_research_urls(detail):
            if url in seen_urls:
                continue
            urls.append(url)
            seen_urls.add(url)
            if len(urls) >= max_urls:
                break
        if len(topics) >= max_topics and len(urls) >= max_urls:
            break

    llm_summary = ""
    for ev in reversed(llm_events):
        if ev.get("event") != "task_completed":
            continue
        detail = task_details.get(ev.get("task_id", ""))
        if not detail:
            continue
        llm_summary = _extract_llm_text(detail)
        if llm_summary:
            break

    ts = now.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"SIM Daily Report ({ts})",
        f"Ventana: ultimas {window_hours}h",
        "",
        "Actividad:",
        f"- research.web: {research_total} total | {research_ok} exitosas | {research_failed} fallidas",
        f"- llm.generate: {llm_total} total | {llm_ok} exitosas | {llm_failed} fallidas",
    ]

    if team_counter:
        team_bits = [f"{team}:{count}" for team, count in sorted(team_counter.items())]
        lines.append(f"- equipos research: {', '.join(team_bits)}")

    lines += ["", "Temas cubiertos:"]
    if topics:
        for idx, topic in enumerate(topics, start=1):
            lines.append(f"{idx}. {topic}")
    else:
        lines.append("1. Sin temas recuperables desde task store (Redis no disponible o tareas expiradas).")

    lines += ["", "URLs encontradas (research.web):"]
    if urls:
        for idx, url in enumerate(urls, start=1):
            lines.append(f"{idx}. {url}")
    else:
        lines.append("1. Sin URLs recuperables desde task store (Redis no disponible o tareas expiradas).")

    lines += ["", "Resumen LLM:"]
    if llm_summary:
        lines.append(llm_summary[:900])
    else:
        lines.append("Sin resumen disponible en llm.generate para la ventana analizada.")

    # Task 036b: do NOT truncate here. The paginator handles oversized output.
    return "\n".join(lines)


class _SimNotionAdapter:
    """Adapter satisfying ``NotionLikeClient`` from the paginator helper.

    Wraps :mod:`worker.notion_client` so the paginator can call ``add_comment``
    and ``create_subpage`` without knowing about HTTP details. Requires
    ``NOTION_API_KEY`` in env (same precondition as the rest of the worker).
    """

    def add_comment(self, parent_id: str, text: str) -> dict[str, Any]:
        from worker import notion_client as nc  # lazy import: keep CLI fast
        return nc.add_comment(parent_id, text)

    def create_subpage(
        self, parent_page_id: str, title: str, blocks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        import httpx
        from worker import notion_client as nc

        payload: dict[str, Any] = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": [{"type": "text", "text": {"content": title[:200]}}]
            },
        }
        # Notion's POST /pages caps children at 100 blocks.
        first_chunk, rest = blocks[:100], blocks[100:]
        if first_chunk:
            payload["children"] = first_chunk
        with httpx.Client(timeout=nc.TIMEOUT) as http:
            resp = http.post(
                f"{nc.NOTION_BASE_URL}/pages",
                headers=nc._headers(),
                json=payload,
            )
        result = nc._check_response(resp, "sim.create_subpage")
        page_id = result["id"]
        if rest:
            nc.append_blocks_to_page(page_id, rest)
        return {"page_id": page_id, "url": result.get("url", "")}


def post_report_via_worker(report_text: str, page_id: str | None = None) -> dict[str, Any]:
    """Legacy direct-via-Worker comment path. Use :func:`post_report` instead."""
    worker_url = os.environ.get("WORKER_URL", "http://127.0.0.1:8088")
    worker_token = os.environ.get("WORKER_TOKEN", "")
    client = WorkerClient(base_url=worker_url, token=worker_token)
    return client.notion_add_comment(text=report_text, page_id=page_id)


def post_report(
    report_text: str,
    *,
    page_id: str | None = None,
    body_page_parent_id: str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Publish ``report_text`` through the paginator.

    Args:
        report_text: Full report (no pre-truncation).
        page_id: Notion page the comment is anchored to. ``None`` → uses the
            worker's default Control Room page.
        body_page_parent_id: When set, oversized reports get offloaded to a
            child page under this parent. When ``None`` and the report is
            oversized, the helper falls back to ``[i/N]`` numbered comments
            (and we log a WARNING).
        client: Override for tests; defaults to :class:`_SimNotionAdapter`.

    Returns:
        Dict from :func:`post_long_comment`.
    """
    if page_id is None:
        page_id = os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID")
    if page_id is None:
        raise RuntimeError(
            "post_report: page_id required (pass --page-id or set NOTION_CONTROL_ROOM_PAGE_ID)"
        )
    if body_page_parent_id is None and len(report_text) > SAFE_LIMIT:
        print(
            "WARN: report exceeds SAFE_LIMIT but no --sim-reports-parent-page-id / "
            "SIM_REPORTS_PARENT_PAGE configured. Falling back to numbered split comments.",
            file=sys.stderr,
        )
    adapter = client if client is not None else _SimNotionAdapter()
    return post_long_comment(
        adapter,
        page_id,
        report_text,
        body_page_parent_id=body_page_parent_id,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera reporte diario SIM y opcionalmente lo publica en Notion")
    parser.add_argument("--hours", type=int, default=24, help="Ventana de analisis en horas")
    parser.add_argument("--limit", type=int, default=50000, help="Maximo de eventos a leer del ops_log")
    parser.add_argument("--max-topics", type=int, default=12, help="Cantidad maxima de temas a listar")
    parser.add_argument("--max-urls", type=int, default=12, help="Cantidad maxima de URLs a listar")
    parser.add_argument("--notion", action="store_true", help="Publica el reporte en Notion Control Room")
    parser.add_argument("--page-id", default=None, help="Page ID override para Notion comment")
    parser.add_argument(
        "--sim-reports-parent-page-id",
        default=None,
        help=(
            "Notion page id under which oversized reports are offloaded as a "
            "child page (recommended). Falls back to ENV SIM_REPORTS_PARENT_PAGE. "
            "If both empty and the report > 1900 chars, the paginator splits "
            "into [i/N] numbered comments."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="No publica en Notion; imprime reporte")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    ops = OpsLogger()
    all_events = ops.read_events(limit=args.limit)
    recent_events = _filter_recent_sim_events(all_events, now=now, hours=args.hours)

    task_ids = [e.get("task_id", "") for e in recent_events if e.get("task_id")]
    task_details = _load_task_details(task_ids)
    report = build_report(
        recent_events,
        task_details=task_details,
        now=now,
        window_hours=args.hours,
        max_topics=args.max_topics,
        max_urls=args.max_urls,
    )

    print(report)

    if args.dry_run:
        print("\nDry-run: reporte no publicado.")
        return 0

    if not args.notion:
        print("\nReporte generado sin publicar. Usa --notion para postear en Control Room.")
        return 0

    body_page_parent = (
        args.sim_reports_parent_page_id
        or os.environ.get("SIM_REPORTS_PARENT_PAGE")
    )
    try:
        result = post_report(
            report,
            page_id=args.page_id,
            body_page_parent_id=body_page_parent,
        )
        msg = f"\nNotion comment posted: {result.get('comment_id', 'unknown')} (parts={result.get('parts', 1)})"
        if result.get("page_id"):
            msg += f" subpage={result['page_id']}"
        print(msg)
        return 0
    except Exception as e:
        print(f"\nFailed to post report: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
