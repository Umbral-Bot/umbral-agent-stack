#!/usr/bin/env python3
"""
S6 — Reporte semanal OODA (Observe–Orient–Decide–Act).

Genera un resumen de la semana para Rick:
- Tareas completadas / fallidas
- Uso de modelos y cuotas
- Traces Langfuse (si están disponibles)

Uso:
  python scripts/ooda_report.py [--week-ago N]
  # N=0 (esta semana), N=1 (semana pasada), etc.

Salida: JSON o Markdown, apto para Notion o Telegram.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Genera reporte semanal OODA")
    p.add_argument("--week-ago", type=int, default=0, help="0=esta semana, 1=semana pasada")
    p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    return p.parse_args()


def _week_range(week_ago: int) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    end = now
    start = now - timedelta(weeks=week_ago + 1)
    return start, end


def _connect_redis():
    """Conectar a Redis usando REDIS_URL del entorno."""
    import os
    try:
        import redis
    except ImportError:
        return None
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.Redis.from_url(url, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None


def _report_from_redis() -> Dict[str, Any]:
    """Obtener métricas desde Redis (tareas completadas/fallidas/bloqueadas)."""
    r = _connect_redis()
    if r is None:
        return {"completed": 0, "failed": 0, "blocked": 0, "pending": 0, "source": "redis_unavailable"}

    completed, failed, blocked = 0, 0, 0
    pending = r.llen("umbral:tasks:pending")
    blocked_q = r.llen("umbral:tasks:blocked")

    prefix = "umbral:task:"
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor, match=f"{prefix}*", count=100)
        for key in keys:
            raw = r.get(key)
            if not raw:
                continue
            try:
                import json
                task = json.loads(raw)
                status = task.get("status", "")
                if status == "done":
                    completed += 1
                elif status == "failed":
                    failed += 1
                elif status == "blocked":
                    blocked += 1
            except Exception:
                continue
        if cursor == 0:
            break

    quota_states = {}
    for provider in ("claude_pro", "chatgpt_plus", "gemini_pro", "copilot_pro"):
        used = r.get(f"umbral:quota:{provider}:used")
        if used is not None:
            quota_states[provider] = int(used)

    return {
        "completed": completed,
        "failed": failed,
        "blocked": blocked,
        "pending": pending,
        "blocked_queue": blocked_q,
        "quota_usage": quota_states,
        "source": "redis",
    }


def _report_from_langfuse() -> Dict[str, Any]:
    """Obtener métricas desde Langfuse API (traces, cost, latencia)."""
    # TODO: LANGFUSE_API_KEY + API para traces del período
    return {
        "traces": 0,
        "generations": 0,
        "source": "langfuse_stub",
    }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    start, end = _week_range(args.week_ago)
    redis_stats = _report_from_redis()
    langfuse_stats = _report_from_langfuse()

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "tasks": redis_stats,
        "llm": langfuse_stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def to_markdown(report: Dict[str, Any]) -> str:
    p = report["period"]
    t = report["tasks"]
    llm = report["llm"]
    quota = t.get("quota_usage", {})
    pending = t.get("pending", 0)

    quota_lines = ""
    if quota:
        quota_lines = "\n## Cuotas (requests usados)\n"
        for provider, used in quota.items():
            quota_lines += f"- {provider}: {used}\n"

    return f"""# Reporte OODA — {p['start'][:10]} a {p['end'][:10]}

## Tareas
- Completadas: {t.get('completed', 0)}
- Fallidas: {t.get('failed', 0)}
- Bloqueadas: {t.get('blocked', 0)}
- Pendientes: {pending}
{quota_lines}
## LLM (Langfuse)
- Traces: {llm.get('traces', 0)}
- Generaciones: {llm.get('generations', 0)}

---
*Generado: {report['generated_at']}*
*Fuente tareas: {t.get('source', 'unknown')}*
"""


def main() -> None:
    args = _parse_args()
    report = build_report(args)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(to_markdown(report))


if __name__ == "__main__":
    main()
