#!/usr/bin/env python3
"""
Effectiveness Report — Analisis de efectividad del sistema Umbral.

Lee ops_log.jsonl y genera metricas de rendimiento para medicion y replica.

Uso:
  python scripts/effectiveness_report.py [--days N] [--format json|markdown]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_events(days: int = 7) -> List[Dict[str, Any]]:
    from infra.ops_logger import OpsLogger
    ol = OpsLogger()
    events = ol.read_events(limit=50000)
    if days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        events = [e for e in events if e.get("ts", "") >= cutoff]
    return events


def analyze(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    completed = [e for e in events if e.get("event") == "task_completed"]
    failed = [e for e in events if e.get("event") == "task_failed"]
    blocked = [e for e in events if e.get("event") == "task_blocked"]
    model_selected = [e for e in events if e.get("event") == "model_selected"]

    # Tasks per day
    tasks_per_day: Dict[str, int] = defaultdict(int)
    for e in completed + failed:
        day = e.get("ts", "")[:10]
        if day:
            tasks_per_day[day] += 1

    # Success rate
    total_exec = len(completed) + len(failed)
    success_rate = round(len(completed) / total_exec * 100, 1) if total_exec > 0 else 0

    # By model
    model_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"completed": 0, "failed": 0, "total_duration_ms": 0})
    for e in completed:
        m = e.get("model", "unknown")
        model_stats[m]["completed"] += 1
        model_stats[m]["total_duration_ms"] += e.get("duration_ms", 0)
    for e in failed:
        m = e.get("model", "unknown")
        model_stats[m]["failed"] += 1

    model_report = {}
    for m, s in model_stats.items():
        total = s["completed"] + s["failed"]
        avg_ms = round(s["total_duration_ms"] / s["completed"]) if s["completed"] > 0 else 0
        model_report[m] = {
            "requests": total,
            "completed": s["completed"],
            "failed": s["failed"],
            "success_rate": round(s["completed"] / total * 100, 1) if total > 0 else 0,
            "avg_duration_ms": avg_ms,
        }

    # By team
    team_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"completed": 0, "failed": 0, "blocked": 0})
    for e in completed:
        team_stats[e.get("team", "unknown")]["completed"] += 1
    for e in failed:
        team_stats[e.get("team", "unknown")]["failed"] += 1
    for e in blocked:
        team_stats[e.get("team", "unknown")]["blocked"] += 1

    # By task type
    task_type_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_duration_ms": 0})
    for e in completed:
        t = e.get("task", "unknown")
        task_type_stats[t]["count"] += 1
        task_type_stats[t]["total_duration_ms"] += e.get("duration_ms", 0)
    task_type_report = {}
    for t, s in task_type_stats.items():
        task_type_report[t] = {
            "count": s["count"],
            "avg_duration_ms": round(s["total_duration_ms"] / s["count"]) if s["count"] > 0 else 0,
        }

    # Worker distribution
    worker_dist: Dict[str, int] = defaultdict(int)
    for e in completed:
        worker_dist[e.get("worker", "unknown")] += 1

    # Quota events
    quota_warnings = len([e for e in events if e.get("event") == "quota_warning"])
    quota_restricted = len([e for e in events if e.get("event") == "quota_restricted"])

    return {
        "period_days": max(1, len(tasks_per_day)),
        "total_events": len(events),
        "tasks_completed": len(completed),
        "tasks_failed": len(failed),
        "tasks_blocked": len(blocked),
        "success_rate": success_rate,
        "tasks_per_day": dict(sorted(tasks_per_day.items())),
        "avg_tasks_per_day": round(sum(tasks_per_day.values()) / max(1, len(tasks_per_day)), 1),
        "by_model": model_report,
        "by_team": dict(team_stats),
        "by_task_type": task_type_report,
        "worker_distribution": dict(worker_dist),
        "quota_warnings": quota_warnings,
        "quota_restricted": quota_restricted,
    }


def to_markdown(report: Dict[str, Any]) -> str:
    lines = [
        f"# Reporte de Efectividad — Umbral Agent Stack",
        f"",
        f"## Resumen ({report['period_days']} dias)",
        f"- Tareas completadas: {report['tasks_completed']}",
        f"- Tareas fallidas: {report['tasks_failed']}",
        f"- Tareas bloqueadas: {report['tasks_blocked']}",
        f"- Tasa de exito: {report['success_rate']}%",
        f"- Promedio tareas/dia: {report['avg_tasks_per_day']}",
        f"- Alertas cuota: {report['quota_warnings']} warnings, {report['quota_restricted']} restricciones",
        "",
    ]

    if report.get("by_model"):
        lines.append("## Uso por Modelo")
        lines.append("| Modelo | Requests | Completadas | Fallidas | Exito % | Avg ms |")
        lines.append("|--------|----------|-------------|----------|---------|--------|")
        for m, s in sorted(report["by_model"].items(), key=lambda x: -x[1]["requests"]):
            lines.append(f"| {m} | {s['requests']} | {s['completed']} | {s['failed']} | {s['success_rate']}% | {s['avg_duration_ms']} |")
        lines.append("")

    if report.get("by_team"):
        lines.append("## Rendimiento por Equipo")
        lines.append("| Equipo | Completadas | Fallidas | Bloqueadas |")
        lines.append("|--------|-------------|----------|------------|")
        for t, s in sorted(report["by_team"].items()):
            lines.append(f"| {t} | {s['completed']} | {s['failed']} | {s['blocked']} |")
        lines.append("")

    if report.get("by_task_type"):
        lines.append("## Rendimiento por Tipo de Tarea")
        lines.append("| Tarea | Ejecuciones | Avg ms |")
        lines.append("|-------|-------------|--------|")
        for t, s in sorted(report["by_task_type"].items(), key=lambda x: -x[1]["count"]):
            lines.append(f"| {t} | {s['count']} | {s['avg_duration_ms']} |")
        lines.append("")

    if report.get("worker_distribution"):
        lines.append("## Distribucion Worker")
        for w, c in report["worker_distribution"].items():
            lines.append(f"- {w}: {c} tareas")
        lines.append("")

    if report.get("tasks_per_day"):
        lines.append("## Tareas por Dia")
        for day, count in report["tasks_per_day"].items():
            bar = "█" * min(count, 50)
            lines.append(f"  {day}: {bar} {count}")
        lines.append("")

    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Reporte de efectividad Umbral")
    p.add_argument("--days", type=int, default=7, help="Dias a analizar (0=todo)")
    p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = p.parse_args()

    events = load_events(args.days)
    if not events:
        print("Sin eventos en ops_log. Ejecuta tareas primero.")
        return

    report = analyze(events)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(to_markdown(report))


if __name__ == "__main__":
    main()
