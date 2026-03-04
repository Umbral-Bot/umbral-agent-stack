#!/usr/bin/env python3
"""
Daily Activity Digest — Rick → David.

Escanea Redis por tareas completadas en las últimas 24h, genera un resumen
ejecutivo con LLM (vía Worker) y lo postea en Notion Control Room.

Uso:
    python scripts/daily_digest.py                 # imprime resumen sin publicar
    python scripts/daily_digest.py --notion        # genera con LLM y publica en Notion
    python scripts/daily_digest.py --dry-run       # genera sin publicar
    python scripts/daily_digest.py --hours 12      # ventana personalizada
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Repo root in sys.path
# ---------------------------------------------------------------------------
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from client.worker_client import WorkerClient  # noqa: E402

logger = logging.getLogger("daily_digest")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

TASK_KEY_PREFIX = "umbral:task:"
MAX_COMMENT_CHARS = 1900


# ======================================================================
# Worker Task History API
# ======================================================================

def fetch_task_history(
    worker_client: WorkerClient,
    hours: int = 24,
    team: Optional[str] = None,
    status: Optional[str] = None,
    page_size: int = 200,
    max_pages: int = 50,
) -> Dict[str, Any]:
    """Fetch task history from Worker API with pagination."""
    tasks: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {}
    offset = 0
    total = 0

    for _ in range(max_pages):
        page = worker_client.task_history(
            hours=hours,
            team=team,
            status=status,
            limit=page_size,
            offset=offset,
        )
        page_tasks = page.get("tasks", []) or []
        tasks.extend(page_tasks)
        total = int(page.get("total", total))
        if not stats:
            stats = page.get("stats", {}) or {}

        page_meta = page.get("page", {}) or {}
        if not bool(page_meta.get("has_more")):
            break
        offset += page_size

    return {"tasks": tasks, "total": total, "stats": stats}


# ======================================================================
# Redis scanning
# ======================================================================

def get_redis_client():
    """Connect to Redis. Returns None if unavailable."""
    try:
        import redis
    except ImportError:
        logger.warning("redis package not installed")
        return None

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:
        logger.warning("Cannot connect to Redis: %s", exc)
        return None


def scan_recent_tasks(
    redis_client,
    hours: int = 24,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Scan Redis for all umbral:task:* keys and return those completed/failed
    within the given window.
    """
    if redis_client is None:
        return []

    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=hours)).timestamp()

    tasks: List[Dict[str, Any]] = []
    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor, match=f"{TASK_KEY_PREFIX}*", count=200)
        for key in keys:
            raw = redis_client.get(key)
            if not raw:
                continue
            try:
                envelope = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            # Only include tasks with a terminal status
            status = envelope.get("status", "")
            if status not in ("done", "failed"):
                continue

            # Check timestamp within window
            ts = envelope.get("completed_at") or envelope.get("failed_at") or 0
            if isinstance(ts, (int, float)) and ts >= cutoff:
                tasks.append(envelope)

        if cursor == 0:
            break

    # Sort by completion time
    tasks.sort(key=lambda t: t.get("completed_at") or t.get("failed_at") or 0)
    return tasks


# ======================================================================
# Metrics extraction
# ======================================================================

def compute_metrics(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate metrics from task list."""
    total = len(tasks)
    status_counter: Dict[str, int] = Counter(str(t.get("status", "unknown")) for t in tasks)
    done = int(status_counter.get("done", 0))
    failed = int(status_counter.get("failed", 0))

    # Group by team
    by_team: Dict[str, int] = Counter(t.get("team", "unknown") for t in tasks)

    # Group by task type
    by_task_type: Dict[str, int] = Counter(t.get("task_type", "general") for t in tasks)

    # Group by task name
    by_task: Dict[str, Dict[str, int]] = defaultdict(lambda: {"done": 0, "failed": 0})
    for t in tasks:
        name = t.get("task", "unknown")
        by_task[name][t.get("status", "unknown")] += 1

    # Average execution time (for done tasks with both timestamps)
    durations: List[float] = []
    for t in tasks:
        started = t.get("started_at") or t.get("queued_at")
        completed = t.get("completed_at")
        if started and completed and t.get("status") == "done":
            dur = float(completed) - float(started)
            if dur >= 0:
                durations.append(dur)
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    # Collect research topics
    research_topics: List[str] = []
    for t in tasks:
        if t.get("task") == "research.web" and t.get("status") == "done":
            query = (t.get("input") or {}).get("query", "")
            if query:
                research_topics.append(str(query).strip())

    # Collect pending/queued tasks
    # (not in this scan, but we can flag blocked)
    errors: List[str] = []
    for t in tasks:
        if t.get("status") == "failed":
            err = t.get("error", "unknown error")
            errors.append(f"{t.get('task', '?')}: {err}")

    return {
        "total": total,
        "done": done,
        "failed": failed,
        "status_counts": dict(status_counter),
        "by_team": dict(by_team),
        "by_task_type": dict(by_task_type),
        "by_task": {k: dict(v) for k, v in by_task.items()},
        "avg_duration_s": round(avg_duration, 1),
        "research_topics": research_topics[:20],
        "errors": errors[:10],
    }


def count_pending(redis_client) -> int:
    """Count tasks still in pending queue."""
    if redis_client is None:
        return 0
    try:
        return redis_client.llen("umbral:tasks:pending") or 0
    except Exception:
        return 0


# ======================================================================
# Report building (plain text)
# ======================================================================

def build_plain_report(
    metrics: Dict[str, Any],
    pending: int,
    now: datetime,
    hours: int,
) -> str:
    """Build the plain-text digest (used as fallback or standalone)."""
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")

    lines = [
        f"Rick: Resumen diario — {date_str}",
        f"Generado: {time_str} | Ventana: últimas {hours}h",
        "",
        "📊 Actividad:",
        f"- {metrics['total']} tareas ejecutadas ({metrics['done']} exitosas, {metrics['failed']} fallidas)",
        f"- Tiempo promedio: {metrics['avg_duration_s']}s",
    ]

    if metrics["by_team"]:
        teams = ", ".join(f"{k}:{v}" for k, v in sorted(metrics["by_team"].items()))
        lines.append(f"- Equipos activos: {teams}")

    if metrics["by_task"]:
        lines.append("- Desglose por tarea:")
        for task_name, counts in sorted(metrics["by_task"].items()):
            ok = counts.get("done", 0)
            fail = counts.get("failed", 0)
            lines.append(f"  • {task_name}: {ok} ok / {fail} fail")

    if metrics["research_topics"]:
        lines += ["", "🔍 Investigaciones:"]
        for i, topic in enumerate(metrics["research_topics"], 1):
            lines.append(f"  {i}. {topic}")

    if metrics["failed"] > 0:
        lines += [
            "",
            "Alertas:",
            f"- {metrics['failed']} tareas fallidas detectadas en la ventana.",
        ]

    if metrics["errors"]:
        lines += ["", "⚠️ Errores:"]
        for err in metrics["errors"]:
            lines.append(f"  - {err}")

    if pending > 0:
        lines += ["", f"📋 Pendientes: {pending} tareas en cola"]

    return "\n".join(lines)


# ======================================================================
# LLM-enhanced summary
# ======================================================================

DIGEST_SYSTEM_PROMPT = (
    "Eres Rick, asistente de David. Genera un resumen ejecutivo breve y "
    "accionable del reporte de actividad diaria. Mantén el formato con "
    "emojis. Responde en español. Máximo 800 caracteres."
)


def generate_llm_summary(
    plain_report: str,
    worker_client: WorkerClient,
) -> Optional[str]:
    """
    Call llm.generate via Worker to produce an executive summary.
    Returns None on failure.
    """
    prompt = (
        "Basándote en este reporte de actividad del sistema Umbral, genera un "
        "resumen ejecutivo para David. Incluye highlights, problemas detectados "
        "y recomendaciones. Formato con emojis.\n\n"
        f"--- REPORTE ---\n{plain_report}\n--- FIN ---"
    )

    try:
        resp = worker_client.run("llm.generate", {
            "prompt": prompt,
            "system": DIGEST_SYSTEM_PROMPT,
            "max_tokens": 512,
            "temperature": 0.5,
        })
        text = (resp.get("result") or {}).get("text", "")
        if not text:
            logger.warning("LLM returned empty text")
            return None
        return text.strip()
    except Exception as exc:
        logger.warning("LLM summary generation failed: %s", exc)
        return None


# ======================================================================
# Notion posting
# ======================================================================

def post_to_notion(
    text: str,
    worker_client: WorkerClient,
    page_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Post digest to Notion Control Room via Worker."""
    # Trim if too long for Notion comment
    if len(text) > MAX_COMMENT_CHARS:
        text = text[: MAX_COMMENT_CHARS - 15] + "\n\n[truncated]"
    return worker_client.notion_add_comment(text=text, page_id=page_id)


# ======================================================================
# Build final digest
# ======================================================================

def build_digest(
    tasks: List[Dict[str, Any]],
    pending: int,
    now: datetime,
    hours: int,
    worker_client: Optional[WorkerClient] = None,
    use_llm: bool = True,
) -> str:
    """
    Build the full digest: plain report + optional LLM summary.
    Falls back to plain report if LLM is unavailable.
    """
    metrics = compute_metrics(tasks)
    plain = build_plain_report(metrics, pending, now, hours)

    if not use_llm or worker_client is None or metrics["total"] == 0:
        return plain

    llm_summary = generate_llm_summary(plain, worker_client)
    if llm_summary:
        return (
            f"Rick: Resumen diario — {now.strftime('%Y-%m-%d')}\n"
            f"(Generado con IA a las {now.strftime('%H:%M UTC')})\n\n"
            f"{llm_summary}\n\n"
            "--- Datos crudos ---\n"
            f"{plain}"
        )

    # Fallback: plain report only
    return plain


# ======================================================================
# CLI
# ======================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Daily Activity Digest — escanea Redis, genera resumen, publica en Notion."
    )
    parser.add_argument("--hours", type=int, default=24, help="Ventana de análisis en horas (default: 24)")
    parser.add_argument("--notion", action="store_true", help="Publica el digest en Notion Control Room")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM summary (solo datos crudos)")
    parser.add_argument("--page-id", default=None, help="Page ID override para Notion")
    parser.add_argument("--dry-run", action="store_true", help="Genera pero no publica en Notion")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)

    # --- Worker API client ---
    try:
        wc = WorkerClient()
    except ValueError as exc:
        logger.error("WorkerClient not available: %s", exc)
        print("ERROR: WORKER_URL/WORKER_TOKEN no configurados.", file=sys.stderr)
        return 1

    # --- Query /task/history ---
    try:
        history = fetch_task_history(wc, hours=args.hours)
    except Exception as exc:
        logger.error("Failed to query /task/history: %s", exc)
        print(f"ERROR: No se pudo consultar /task/history: {exc}", file=sys.stderr)
        return 1

    all_tasks = history.get("tasks", []) or []
    tasks = [t for t in all_tasks if t.get("status") in ("done", "failed")]
    stats = history.get("stats", {}) or {}
    pending = int(stats.get("queued", 0)) + int(stats.get("running", 0))
    logger.info(
        "History API returned %d tasks (done/failed=%d), pending=%d",
        len(all_tasks),
        len(tasks),
        pending,
    )

    if not tasks:
        print(f"Sin tareas completadas/fallidas en las últimas {args.hours}h.")
        if args.notion and not args.dry_run:
            try:
                post_to_notion(
                    f"Rick: Sin actividad en las últimas {args.hours}h — {now.strftime('%Y-%m-%d %H:%M UTC')}",
                    wc,
                    page_id=args.page_id,
                )
                print("Nota 'sin actividad' publicada en Notion.")
            except Exception as exc:
                logger.error("Failed to post empty digest: %s", exc)
        return 0

    # --- Build digest ---
    use_llm = not args.no_llm
    digest = build_digest(tasks, pending, now, args.hours, worker_client=wc, use_llm=use_llm)
    
    # --- Append quota ---
    try:
        quota_data = wc.quota_status()
        from scripts.quota_report import build_visual_report
        quota_visual = build_visual_report(quota_data)
        if quota_visual:
            digest += f"\n\n---\n{quota_visual}"
    except Exception as exc:
        logger.warning("Failed to fetch/append quota status: %s", exc)

    print(digest)

    # --- Post to Notion ---
    if args.dry_run:
        print("\nDry-run: digest no publicado.")
        return 0

    if not args.notion:
        print("\nDigest generado. Usa --notion para publicar en Notion Control Room.")
        return 0

    try:
        result = post_to_notion(digest, wc, page_id=args.page_id)
        print(f"\nNotion comment posted: {result}")
        return 0
    except Exception as exc:
        logger.error("Failed to post digest to Notion: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
