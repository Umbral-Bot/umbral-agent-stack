#!/usr/bin/env python3
"""
Governance Metrics Report — Métricas agregadas de gobernanza del sistema Umbral.

Lee ops_log.jsonl y genera un reporte estructurado con:
  tasks por día/team/tipo, success rate, uso de modelos,
  duración media, distribución de workers, y estado de cuotas.

Uso:
  python scripts/governance_metrics_report.py                         # markdown a stdout
  python scripts/governance_metrics_report.py --days 30               # últimos 30 días
  python scripts/governance_metrics_report.py --format json           # salida JSON
  python scripts/governance_metrics_report.py --format markdown -o report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_events(
    days: int = 7,
    log_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Lee eventos del ops_log filtrados por ventana de tiempo."""
    from infra.ops_logger import OpsLogger

    if log_path:
        ol = OpsLogger(log_dir=log_path.parent)
    else:
        ol = OpsLogger()

    events = ol.read_events(limit=100_000)
    if days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        events = [e for e in events if e.get("ts", "") >= cutoff]
    return events


def load_quota_policy() -> Dict[str, Dict[str, Any]]:
    """Carga la configuración de cuotas desde quota_policy.yaml."""
    try:
        import yaml
    except ImportError:
        return {}

    path = REPO_ROOT / "config" / "quota_policy.yaml"
    if not path.is_file():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    providers: Dict[str, Dict[str, Any]] = {}
    for pid, cfg in (data.get("providers") or {}).items():
        if isinstance(cfg, dict):
            providers[pid] = {
                "limit_requests": int(cfg.get("limit_requests", 100)),
                "window_seconds": int(cfg.get("window_seconds", 3600)),
            }
    return providers


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula todas las métricas de gobernanza a partir de eventos ops_log."""
    completed = [e for e in events if e.get("event") == "task_completed"]
    failed = [e for e in events if e.get("event") == "task_failed"]
    blocked = [e for e in events if e.get("event") == "task_blocked"]
    model_events = [e for e in events if e.get("event") == "model_selected"]

    tasks_total = len(completed) + len(failed) + len(blocked)
    total_exec = len(completed) + len(failed)
    success_rate = round(len(completed) / total_exec * 100, 1) if total_exec > 0 else 0.0

    # --- tasks_by_day ---
    tasks_by_day: Dict[str, int] = defaultdict(int)
    for e in completed + failed + blocked:
        day = e.get("ts", "")[:10]
        if day:
            tasks_by_day[day] += 1

    # --- tasks_by_team ---
    team_stats: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"completed": 0, "failed": 0, "blocked": 0}
    )
    for e in completed:
        team_stats[e.get("team", "unknown")]["completed"] += 1
    for e in failed:
        team_stats[e.get("team", "unknown")]["failed"] += 1
    for e in blocked:
        team_stats[e.get("team", "unknown")]["blocked"] += 1

    tasks_by_team: Dict[str, Dict[str, Any]] = {}
    for team, s in team_stats.items():
        t = s["completed"] + s["failed"]
        tasks_by_team[team] = {
            **s,
            "success_rate": round(s["completed"] / t * 100, 1) if t > 0 else 0.0,
        }

    # --- tasks_by_task_type ---
    type_stats: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"completed": 0, "failed": 0}
    )
    for e in completed:
        type_stats[e.get("task", "unknown")]["completed"] += 1
    for e in failed:
        type_stats[e.get("task", "unknown")]["failed"] += 1

    tasks_by_task_type: Dict[str, Dict[str, Any]] = {}
    for task, s in type_stats.items():
        t = s["completed"] + s["failed"]
        tasks_by_task_type[task] = {
            **s,
            "success_rate": round(s["completed"] / t * 100, 1) if t > 0 else 0.0,
        }

    # --- model_usage ---
    model_usage: Dict[str, int] = defaultdict(int)
    for e in model_events:
        model_usage[e.get("model", "unknown")] += 1
    for e in completed:
        m = e.get("model")
        if m:
            model_usage[m] += 1

    # --- avg_duration_ms ---
    durations = [e.get("duration_ms", 0) for e in completed if e.get("duration_ms")]
    avg_duration_ms = round(sum(durations) / len(durations)) if durations else 0

    # --- duration_by_task_type ---
    dur_by_type: Dict[str, List[float]] = defaultdict(list)
    for e in completed:
        d = e.get("duration_ms")
        if d:
            dur_by_type[e.get("task", "unknown")].append(d)
    avg_duration_by_type = {
        t: round(sum(ds) / len(ds)) for t, ds in dur_by_type.items()
    }

    # --- worker_distribution ---
    worker_dist: Dict[str, int] = defaultdict(int)
    for e in completed:
        worker_dist[e.get("worker", "unknown")] += 1

    return {
        "tasks_total": tasks_total,
        "tasks_completed": len(completed),
        "tasks_failed": len(failed),
        "tasks_blocked": len(blocked),
        "success_rate": success_rate,
        "tasks_by_day": dict(sorted(tasks_by_day.items())),
        "tasks_by_team": dict(sorted(tasks_by_team.items())),
        "tasks_by_task_type": dict(
            sorted(tasks_by_task_type.items(), key=lambda x: -(x[1]["completed"] + x[1]["failed"]))
        ),
        "model_usage": dict(sorted(model_usage.items(), key=lambda x: -x[1])),
        "avg_duration_ms": avg_duration_ms,
        "avg_duration_by_type": avg_duration_by_type,
        "worker_distribution": dict(worker_dist),
    }


# ---------------------------------------------------------------------------
# Quota usage (from Redis, optional)
# ---------------------------------------------------------------------------

def get_quota_usage() -> Dict[str, Dict[str, Any]]:
    """Intenta leer el estado de cuotas de Redis. Retorna {} si no disponible."""
    providers = load_quota_policy()
    if not providers:
        return {}

    try:
        from scripts.quota_usage_report import get_redis_client, read_quota_state
        client = get_redis_client(fake=False)
        state = read_quota_state(client, providers)
        return {
            p: {"used": s["used"], "limit": s["limit"], "pct": s["pct"], "health": s["health"]}
            for p, s in state.items()
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def to_json(report: Dict[str, Any], days: int) -> str:
    """Serializa el reporte a JSON."""
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        **report,
    }
    return json.dumps(output, indent=2, ensure_ascii=False, default=str)


def to_markdown(report: Dict[str, Any], days: int) -> str:
    """Genera reporte Markdown de gobernanza."""
    sr = report["success_rate"]
    lines = [
        f"# Métricas de gobernanza — Últimos {days} días",
        "",
        "## Resumen",
        f"- Tasks totales: {report['tasks_total']}",
        f"- Completadas: {report['tasks_completed']} ({sr}%)",
        f"- Fallidas: {report['tasks_failed']}",
        f"- Bloqueadas: {report['tasks_blocked']}",
        f"- Duración media: {report['avg_duration_ms']} ms",
        "",
    ]

    # --- Por team ---
    if report.get("tasks_by_team"):
        lines.append("## Por team")
        lines.append("| Team | Completadas | Fallidas | Bloqueadas | Success rate |")
        lines.append("|------|-------------|----------|------------|--------------|")
        for team, s in report["tasks_by_team"].items():
            lines.append(
                f"| {team} | {s['completed']} | {s['failed']} | {s['blocked']} | {s['success_rate']}% |"
            )
        lines.append("")

    # --- Por task type ---
    if report.get("tasks_by_task_type"):
        lines.append("## Por task type")
        lines.append("| Task | Completadas | Fallidas | Success rate |")
        lines.append("|------|-------------|----------|--------------|")
        for task, s in report["tasks_by_task_type"].items():
            lines.append(
                f"| {task} | {s['completed']} | {s['failed']} | {s['success_rate']}% |"
            )
        lines.append("")

    # --- Uso de modelos ---
    if report.get("model_usage"):
        lines.append("## Uso de modelos")
        lines.append("| Modelo | Selecciones |")
        lines.append("|--------|-------------|")
        for model, count in report["model_usage"].items():
            lines.append(f"| {model} | {count} |")
        lines.append("")

    # --- Duración media por tipo ---
    if report.get("avg_duration_by_type"):
        lines.append("## Duración media por tipo (ms)")
        lines.append("| Task | Avg ms |")
        lines.append("|------|--------|")
        for task, avg in sorted(report["avg_duration_by_type"].items(), key=lambda x: -x[1]):
            lines.append(f"| {task} | {avg} |")
        lines.append("")

    # --- Worker distribution ---
    if report.get("worker_distribution"):
        lines.append("## Distribución de workers")
        for w, c in report["worker_distribution"].items():
            lines.append(f"- {w}: {c} tareas")
        lines.append("")

    # --- Tasks por día ---
    if report.get("tasks_by_day"):
        lines.append("## Tasks por día")
        for day, count in report["tasks_by_day"].items():
            bar = "█" * min(count, 50)
            lines.append(f"  {day}: {bar} {count}")
        lines.append("")

    # --- Quota usage ---
    if report.get("quota_usage"):
        lines.append("## Uso de cuotas")
        lines.append("| Provider | Usado | Límite | Uso % | Estado |")
        lines.append("|----------|-------|--------|-------|--------|")
        for p, s in report["quota_usage"].items():
            lines.append(f"| {p} | {s['used']} | {s['limit']} | {s['pct']}% | {s['health']} |")
        lines.append("")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"---\n_Generado: {ts}_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_report(days: int = 7, log_path: Optional[Path] = None) -> Dict[str, Any]:
    """Construye el reporte completo de gobernanza."""
    events = load_events(days=days, log_path=log_path)
    report = analyze(events)
    report["quota_usage"] = get_quota_usage()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reporte de métricas de gobernanza — Umbral Agent Stack"
    )
    parser.add_argument("--days", type=int, default=7, help="Días a analizar (default: 7)")
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "notion"],
        default="markdown",
        help="Formato de salida",
    )
    parser.add_argument("-o", "--output", type=str, help="Escribir a archivo")
    args = parser.parse_args()

    report = build_report(days=args.days)

    if not report["tasks_total"] and not report.get("quota_usage"):
        print("Sin datos en ops_log para el período solicitado.", file=sys.stderr)

    fmt = args.format if args.format != "notion" else "markdown"
    if fmt == "json":
        output = to_json(report, args.days)
    else:
        output = to_markdown(report, args.days)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Reporte escrito en {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
