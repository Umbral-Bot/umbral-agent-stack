#!/usr/bin/env python3
"""
S6 — Self-Evaluation: evalúa calidad de outputs del sistema.

Revisa tareas completadas en Redis y genera scores de calidad.
Puede enviar resultados a Langfuse (si configurado) o a Notion.

Uso:
  python scripts/evals_self_check.py [--limit N] [--format json|markdown]
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any, Dict, List


def _connect_redis():
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


def _get_completed_tasks(r, limit: int = 20) -> List[Dict[str, Any]]:
    """Busca tareas con status=done en Redis."""
    tasks = []
    cursor = 0
    while len(tasks) < limit:
        cursor, keys = r.scan(cursor, match="umbral:task:*", count=100)
        for key in keys:
            raw = r.get(key)
            if not raw:
                continue
            try:
                task = json.loads(raw)
                if task.get("status") == "done":
                    tasks.append(task)
                    if len(tasks) >= limit:
                        break
            except Exception:
                continue
        if cursor == 0:
            break
    return tasks


def evaluate_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evalúa una tarea completada con heurísticas básicas.
    Scores: 0.0 (malo) a 1.0 (bueno).
    """
    result = task.get("result", {})
    task_name = task.get("task", "unknown")
    task_id = task.get("task_id", "?")

    scores = {}

    has_result = bool(result)
    scores["has_result"] = 1.0 if has_result else 0.0

    ok = result.get("ok", False) if isinstance(result, dict) else False
    scores["ok_flag"] = 1.0 if ok else 0.0

    started = task.get("started_at", 0)
    completed = task.get("completed_at", 0)
    duration = completed - started if (started and completed) else 0
    if duration > 0:
        scores["latency"] = 1.0 if duration < 30 else (0.5 if duration < 120 else 0.2)
    else:
        scores["latency"] = 0.5

    if isinstance(result, dict):
        result_str = json.dumps(result)
        scores["result_richness"] = min(1.0, len(result_str) / 200)
    else:
        scores["result_richness"] = 0.0

    avg = sum(scores.values()) / len(scores) if scores else 0.0

    return {
        "task_id": task_id,
        "task": task_name,
        "team": task.get("team", "system"),
        "scores": scores,
        "overall": round(avg, 2),
        "duration_sec": round(duration, 1),
    }


def run_evals(limit: int = 20) -> List[Dict[str, Any]]:
    r = _connect_redis()
    if r is None:
        return [{"error": "Redis not available"}]

    tasks = _get_completed_tasks(r, limit)
    if not tasks:
        return [{"info": "No completed tasks found in Redis"}]

    return [evaluate_task(t) for t in tasks]


def to_markdown(evals: List[Dict[str, Any]]) -> str:
    lines = ["# Self-Evaluation Report", ""]
    if not evals or "error" in evals[0] or "info" in evals[0]:
        msg = evals[0].get("error") or evals[0].get("info", "No data")
        return f"# Self-Evaluation Report\n\n{msg}\n"

    lines.append(f"| Task | Team | Overall | Latency | OK | Richness |")
    lines.append(f"|------|------|---------|---------|----|----------|")
    for e in evals:
        s = e["scores"]
        lines.append(
            f"| {e['task']} | {e['team']} | {e['overall']} | {s.get('latency', '-')} | {s.get('ok_flag', '-')} | {s.get('result_richness', '-')} |"
        )

    avg_overall = sum(e.get("overall", 0) for e in evals) / len(evals)
    lines.append("")
    lines.append(f"**Promedio global: {avg_overall:.2f}**")
    lines.append(f"*Evaluadas: {len(evals)} tareas*")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Self-evaluation de tareas completadas")
    p.add_argument("--limit", type=int, default=20, help="Máximo de tareas a evaluar")
    p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = p.parse_args()

    evals = run_evals(args.limit)
    if args.format == "json":
        print(json.dumps(evals, indent=2))
    else:
        print(to_markdown(evals))


if __name__ == "__main__":
    main()
