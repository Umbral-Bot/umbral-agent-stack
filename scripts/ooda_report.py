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


def _report_from_redis() -> Dict[str, Any]:
    """Obtener métricas desde Redis (queue, completions, failures)."""
    # TODO: conectar a Redis y agregar tareas completadas/fallidas por semana
    return {
        "completed": 0,
        "failed": 0,
        "blocked": 0,
        "source": "redis_stub",
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
    return f"""# Reporte OODA — {p['start'][:10]} a {p['end'][:10]}

## Tareas
- Completadas: {t.get('completed', 0)}
- Fallidas: {t.get('failed', 0)}
- Bloqueadas: {t.get('blocked', 0)}

## LLM (Langfuse)
- Traces: {llm.get('traces', 0)}
- Generaciones: {llm.get('generations', 0)}

---
*Generado: {report['generated_at']}*
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
