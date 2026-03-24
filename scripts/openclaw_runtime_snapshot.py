#!/usr/bin/env python3
"""
Snapshot repo-side del tracking operativo y de uso OpenClaw.

Lee `ops_log.jsonl` y consolida:
- actividad de paneles (Dashboard Rick + OpenClaw)
- uso OpenClaw atribuido a `source=openclaw_gateway`
- uso LLM trazado por provider/model/componente
- costo proxy aproximado basado en rates rough del repo

No es facturacion oficial. Si el backend no expone tokens, el reporte lo deja
explicito como limitacion.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infra.ops_logger import OpsLogger

PANEL_COMPONENTS = ("dashboard_rick", "openclaw_panel")
OPENCLAW_SOURCE = "openclaw_gateway"
DEFAULT_LIMITATIONS = [
    "El snapshot cubre actividad de paneles y eventos LLM trazados en ops_log; no es facturacion exacta.",
    "research.web via Gemini grounded search no expone tokens en ops_log hoy, asi que su costo fino queda fuera del corte.",
    "La estimacion monetaria usa rates rough versionados en el repo y debe leerse como costo proxy, no como facturacion oficial.",
]
_COST_PROXY_RATES = {
    "gemini": {"input": 0.00035, "output": 0.00105},
    "google": {"input": 0.00035, "output": 0.00105},
    "google-vertex": {"input": 0.00035, "output": 0.00105},
    "vertex": {"input": 0.00035, "output": 0.00105},
    "openai": {"input": 0.00015, "output": 0.0006},
    "azure_foundry": {"input": 0.00015, "output": 0.0006},
    "anthropic": {"input": 0.003, "output": 0.015},
    "openclaw_proxy": {"input": 0.003, "output": 0.015},
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Snapshot OpenClaw desde ops_log")
    parser.add_argument("--days", type=int, default=7, help="Ventana en dias (0=todo)")
    parser.add_argument("--ops-log-path", default="", help="Ruta alternativa a ops_log.jsonl")
    parser.add_argument(
        "--sessions-root",
        default="",
        help="Raiz alternativa de sesiones OpenClaw (ej. ~/.openclaw/agents)",
    )
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    return parser.parse_args()


def _load_events_from_path(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
    return events


def load_events(days: int = 7, ops_log_path: str = "") -> list[dict[str, Any]]:
    if ops_log_path:
        events = _load_events_from_path(Path(ops_log_path))
    else:
        events = OpsLogger().read_events(limit=50000)

    if days <= 0:
        return events

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered: list[dict[str, Any]] = []
    for event in events:
        raw_ts = str(event.get("ts", "") or "").strip()
        if not raw_ts:
            continue
        try:
            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts >= cutoff:
            filtered.append(event)
    return filtered


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _estimate_cost_proxy_usd(provider: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _COST_PROXY_RATES.get(provider, {"input": 0.001, "output": 0.002})
    return round((prompt_tokens / 1000) * rates["input"] + (completion_tokens / 1000) * rates["output"], 6)


def _normalize_provider(provider: str) -> str:
    value = (provider or "").strip().lower()
    if not value:
        return "unknown"
    if value in _COST_PROXY_RATES:
        return value
    if value.startswith("openai") or "codex" in value:
        return "openai"
    if value.startswith("azure-openai") or value.startswith("azure_openai") or value.startswith("azure"):
        return "azure_foundry"
    if value.startswith("google-vertex") or "vertex" in value:
        return "google-vertex"
    if value.startswith("google") or value.startswith("gemini"):
        return "google"
    if value.startswith("anthropic") or "claude" in value:
        return "anthropic"
    return value


def _sort_rows(rows: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda item: (-_safe_int(item.get(key)), str(item.get("name", item.get("component", "")))))


def _format_session_ts(value: Any) -> str | None:
    raw = _safe_int(value)
    if raw <= 0:
        return None
    if raw > 10_000_000_000:
        raw = raw / 1000
    return datetime.fromtimestamp(raw, timezone.utc).isoformat()


def _load_sessions_usage(sessions_root: str = "") -> dict[str, Any]:
    if not sessions_root:
        return {"tracked": False, "root": "", "agents": [], "by_model": [], "recent_sessions": []}

    root = Path(sessions_root)
    if not root.exists():
        return {"tracked": False, "root": str(root), "agents": [], "by_model": [], "recent_sessions": []}

    by_agent: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "agent": "",
            "sessions": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cache_read": 0,
            "cache_write": 0,
            "estimated_cost_proxy_usd": 0.0,
        }
    )
    by_model: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "model": "",
            "provider": "",
            "sessions": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cache_read": 0,
            "estimated_cost_proxy_usd": 0.0,
        }
    )
    recent_sessions: list[dict[str, Any]] = []

    for agent_dir in sorted(root.iterdir()):
        sessions_path = agent_dir / "sessions" / "sessions.json"
        if not sessions_path.exists():
            continue
        try:
            payload = json.loads(sessions_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue

        for session_key, item in payload.items():
            if not isinstance(item, dict):
                continue
            agent = agent_dir.name
            model = str(item.get("model") or "unknown")
            provider_raw = str(item.get("modelProvider") or "unknown")
            provider = _normalize_provider(provider_raw)
            input_tokens = _safe_int(item.get("inputTokens"))
            output_tokens = _safe_int(item.get("outputTokens"))
            total_tokens = _safe_int(item.get("totalTokens"))
            cache_read = _safe_int(item.get("cacheRead"))
            cache_write = _safe_int(item.get("cacheWrite"))
            cost_proxy = _estimate_cost_proxy_usd(provider, input_tokens, output_tokens)
            updated_at = _format_session_ts(item.get("updatedAt"))
            origin = item.get("origin") or {}

            agent_bucket = by_agent[agent]
            agent_bucket["agent"] = agent
            agent_bucket["sessions"] += 1
            agent_bucket["input_tokens"] += input_tokens
            agent_bucket["output_tokens"] += output_tokens
            agent_bucket["total_tokens"] += total_tokens
            agent_bucket["cache_read"] += cache_read
            agent_bucket["cache_write"] += cache_write
            agent_bucket["estimated_cost_proxy_usd"] = round(agent_bucket["estimated_cost_proxy_usd"] + cost_proxy, 6)

            model_bucket = by_model[f"{provider_raw}:{model}"]
            model_bucket["model"] = model
            model_bucket["provider"] = provider_raw
            model_bucket["sessions"] += 1
            model_bucket["input_tokens"] += input_tokens
            model_bucket["output_tokens"] += output_tokens
            model_bucket["total_tokens"] += total_tokens
            model_bucket["cache_read"] += cache_read
            model_bucket["estimated_cost_proxy_usd"] = round(model_bucket["estimated_cost_proxy_usd"] + cost_proxy, 6)

            recent_sessions.append(
                {
                    "agent": agent,
                    "session_key": str(session_key),
                    "model": model,
                    "provider": provider_raw,
                    "updated_at": updated_at,
                    "total_tokens": total_tokens,
                    "origin_provider": str(origin.get("provider") or ""),
                    "origin_surface": str(origin.get("surface") or ""),
                }
            )

    recent_sessions = sorted(
        recent_sessions,
        key=lambda item: str(item.get("updated_at") or ""),
        reverse=True,
    )[:10]

    return {
        "tracked": bool(by_agent),
        "root": str(root),
        "agents": _sort_rows(
            [
                {
                    "name": stats["agent"],
                    "sessions": stats["sessions"],
                    "input_tokens": stats["input_tokens"],
                    "output_tokens": stats["output_tokens"],
                    "total_tokens": stats["total_tokens"],
                    "cache_read": stats["cache_read"],
                    "cache_write": stats["cache_write"],
                    "estimated_cost_proxy_usd": round(stats["estimated_cost_proxy_usd"], 6),
                }
                for stats in by_agent.values()
            ],
            "total_tokens",
        ),
        "by_model": _sort_rows(
            [
                {
                    "name": stats["model"],
                    "provider": stats["provider"],
                    "sessions": stats["sessions"],
                    "input_tokens": stats["input_tokens"],
                    "output_tokens": stats["output_tokens"],
                    "total_tokens": stats["total_tokens"],
                    "cache_read": stats["cache_read"],
                    "estimated_cost_proxy_usd": round(stats["estimated_cost_proxy_usd"], 6),
                }
                for stats in by_model.values()
            ],
            "total_tokens",
        )[:10],
        "recent_sessions": recent_sessions,
    }


def build_snapshot(events: list[dict[str, Any]], *, days: int = 7, sessions_root: str = "") -> dict[str, Any]:
    panel_events = [
        event for event in events
        if event.get("event") == "system_activity" and event.get("component") in PANEL_COMPONENTS
    ]
    openclaw_task_events = [
        event for event in events
        if event.get("source") == OPENCLAW_SOURCE and event.get("event") in {"task_completed", "task_failed", "task_blocked"}
    ]
    llm_usage_events = [
        event for event in events
        if event.get("event") == "llm_usage" and event.get("source") == OPENCLAW_SOURCE
    ]

    panel_summary: dict[str, dict[str, Any]] = {}
    for component in PANEL_COMPONENTS:
        current = [event for event in panel_events if event.get("component") == component]
        current_sorted = sorted(current, key=lambda item: str(item.get("ts", "")))
        last = current_sorted[-1] if current_sorted else {}
        panel_summary[component] = {
            "component": component,
            "updated": sum(1 for event in current if event.get("status") == "updated"),
            "skipped": sum(1 for event in current if event.get("status") == "skipped"),
            "failed": sum(1 for event in current if event.get("status") == "failed"),
            "notion_reads": sum(_safe_int(event.get("notion_reads")) for event in current),
            "notion_writes": sum(_safe_int(event.get("notion_writes")) for event in current),
            "worker_calls": sum(_safe_int(event.get("worker_calls")) for event in current),
            "db_rows_read": sum(_safe_int(event.get("db_rows_read")) for event in current),
            "last_status": last.get("status"),
            "last_trigger": last.get("trigger"),
            "last_ts": last.get("ts"),
            "last_duration_ms": _safe_int(last.get("duration_ms")),
            "last_details": last.get("details"),
        }

    by_task: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"name": "", "completed": 0, "failed": 0, "blocked": 0, "duration_ms_total": 0}
    )
    recent_failures: list[dict[str, Any]] = []
    for event in openclaw_task_events:
        task_name = str(event.get("task", "unknown"))
        bucket = by_task[task_name]
        bucket["name"] = task_name
        if event.get("event") == "task_completed":
            bucket["completed"] += 1
            bucket["duration_ms_total"] += _safe_int(event.get("duration_ms"))
        elif event.get("event") == "task_failed":
            bucket["failed"] += 1
            if len(recent_failures) < 10:
                recent_failures.append(
                    {
                        "ts": event.get("ts"),
                        "task": task_name,
                        "error": event.get("error"),
                        "task_type": event.get("task_type"),
                        "source_kind": event.get("source_kind"),
                    }
                )
        elif event.get("event") == "task_blocked":
            bucket["blocked"] += 1

    task_rows: list[dict[str, Any]] = []
    for task_name, stats in by_task.items():
        completed = stats["completed"]
        duration_total = stats["duration_ms_total"]
        task_rows.append(
            {
                "name": task_name,
                "completed": completed,
                "failed": stats["failed"],
                "blocked": stats["blocked"],
                "avg_duration_ms": round(duration_total / completed) if completed else 0,
            }
        )

    by_provider: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "provider": "",
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "duration_ms_total": 0,
            "estimated_cost_proxy_usd": 0.0,
        }
    )
    by_model: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "model": "",
            "provider": "",
            "calls": 0,
            "total_tokens": 0,
            "estimated_cost_proxy_usd": 0.0,
        }
    )
    by_component: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "usage_component": "",
            "calls": 0,
            "total_tokens": 0,
            "estimated_cost_proxy_usd": 0.0,
        }
    )

    for event in llm_usage_events:
        provider = str(event.get("provider", "unknown"))
        model = str(event.get("model", "unknown"))
        usage_component = str(event.get("usage_component", "llm.generate"))
        prompt_tokens = _safe_int(event.get("prompt_tokens"))
        completion_tokens = _safe_int(event.get("completion_tokens"))
        total_tokens = _safe_int(event.get("total_tokens"))
        duration_ms = _safe_int(event.get("duration_ms"))
        cost_proxy = _estimate_cost_proxy_usd(provider, prompt_tokens, completion_tokens)

        provider_bucket = by_provider[provider]
        provider_bucket["provider"] = provider
        provider_bucket["calls"] += 1
        provider_bucket["prompt_tokens"] += prompt_tokens
        provider_bucket["completion_tokens"] += completion_tokens
        provider_bucket["total_tokens"] += total_tokens
        provider_bucket["duration_ms_total"] += duration_ms
        provider_bucket["estimated_cost_proxy_usd"] = round(provider_bucket["estimated_cost_proxy_usd"] + cost_proxy, 6)

        model_bucket = by_model[model]
        model_bucket["model"] = model
        model_bucket["provider"] = provider
        model_bucket["calls"] += 1
        model_bucket["total_tokens"] += total_tokens
        model_bucket["estimated_cost_proxy_usd"] = round(model_bucket["estimated_cost_proxy_usd"] + cost_proxy, 6)

        component_bucket = by_component[usage_component]
        component_bucket["usage_component"] = usage_component
        component_bucket["calls"] += 1
        component_bucket["total_tokens"] += total_tokens
        component_bucket["estimated_cost_proxy_usd"] = round(component_bucket["estimated_cost_proxy_usd"] + cost_proxy, 6)

    provider_rows: list[dict[str, Any]] = []
    for provider, stats in by_provider.items():
        calls = stats["calls"]
        provider_rows.append(
            {
                "name": provider,
                "calls": calls,
                "prompt_tokens": stats["prompt_tokens"],
                "completion_tokens": stats["completion_tokens"],
                "total_tokens": stats["total_tokens"],
                "avg_duration_ms": round(stats["duration_ms_total"] / calls) if calls else 0,
                "estimated_cost_proxy_usd": round(stats["estimated_cost_proxy_usd"], 6),
            }
        )

    panels_total_reads = sum(item["notion_reads"] for item in panel_summary.values())
    panels_total_writes = sum(item["notion_writes"] for item in panel_summary.values())
    panels_total_worker_calls = sum(item["worker_calls"] for item in panel_summary.values())

    total_task_events = len(openclaw_task_events)
    completed = sum(1 for event in openclaw_task_events if event.get("event") == "task_completed")
    failed = sum(1 for event in openclaw_task_events if event.get("event") == "task_failed")
    blocked = sum(1 for event in openclaw_task_events if event.get("event") == "task_blocked")

    tracked_sources = sorted(
        {
            str(event.get("source") or "")
            for event in events
            if str(event.get("source") or "").strip()
        }
    )
    sessions_usage = _load_sessions_usage(sessions_root)

    limitations = list(DEFAULT_LIMITATIONS)
    if sessions_usage["tracked"]:
        limitations.append(
            "La vista de sesiones usa snapshots `sessions.json` de OpenClaw; refleja tokens acumulados por sesion y no reemplaza billing oficial por request."
        )
        limitations.append(
            "El costo proxy de sesiones usa solo input/output tokens; `cacheRead` y `cacheWrite` quedan fuera porque su billing depende del provider."
        )
    else:
        limitations.append(
            "No se cargo `sessions_root`, asi que el snapshot no incluye uso por sesion/agente del runtime nativo de OpenClaw."
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": days,
        "total_events": len(events),
        "tracked_sources": tracked_sources,
        "panels": {
            "components": panel_summary,
            "totals": {
                "notion_reads": panels_total_reads,
                "notion_writes": panels_total_writes,
                "worker_calls": panels_total_worker_calls,
            },
        },
        "openclaw_runtime": {
            "source": OPENCLAW_SOURCE,
            "task_events_total": total_task_events,
            "completed": completed,
            "failed": failed,
            "blocked": blocked,
            "top_tasks": _sort_rows(task_rows, "completed")[:10],
            "recent_failures": recent_failures,
        },
        "llm_usage": {
            "tracked_events": len(llm_usage_events),
            "tracked": len(llm_usage_events) > 0,
            "by_provider": _sort_rows(provider_rows, "total_tokens"),
            "by_model": _sort_rows(
                [
                    {
                        "name": stats["model"],
                        "provider": stats["provider"],
                        "calls": stats["calls"],
                        "total_tokens": stats["total_tokens"],
                        "estimated_cost_proxy_usd": round(stats["estimated_cost_proxy_usd"], 6),
                    }
                    for stats in by_model.values()
                ],
                "total_tokens",
            )[:10],
            "by_usage_component": _sort_rows(
                [
                    {
                        "name": stats["usage_component"],
                        "calls": stats["calls"],
                        "total_tokens": stats["total_tokens"],
                        "estimated_cost_proxy_usd": round(stats["estimated_cost_proxy_usd"], 6),
                    }
                    for stats in by_component.values()
                ],
                "total_tokens",
            )[:10],
            "tokens_total": sum(item["total_tokens"] for item in provider_rows),
            "estimated_cost_proxy_usd": round(sum(item["estimated_cost_proxy_usd"] for item in provider_rows), 6),
        },
        "sessions_usage": sessions_usage,
        "limitations": limitations,
    }


def to_markdown(report: dict[str, Any]) -> str:
    panel_components = report["panels"]["components"]
    llm_usage = report["llm_usage"]
    runtime = report["openclaw_runtime"]
    sessions_usage = report.get("sessions_usage") or {"tracked": False}

    lines = [
        "# OpenClaw Runtime Snapshot",
        "",
        f"- Generado: {report['generated_at']}",
        f"- Ventana: {report['window_days']} dias",
        f"- Eventos leidos: {report['total_events']}",
        f"- Fuente OpenClaw: `{runtime['source']}`",
        "",
        "## Resumen",
        f"- Eventos operativos OpenClaw: {runtime['task_events_total']} ({runtime['completed']} completados, {runtime['failed']} fallidos, {runtime['blocked']} bloqueados)",
        f"- Eventos LLM trazados: {llm_usage['tracked_events']}",
        f"- Tokens LLM trazados: {llm_usage['tokens_total']}",
        f"- Costo proxy total: {llm_usage['estimated_cost_proxy_usd']:.6f} USD",
        f"- Lecturas Notion de paneles: {report['panels']['totals']['notion_reads']}",
        f"- Escrituras Notion de paneles: {report['panels']['totals']['notion_writes']}",
        f"- Snapshot de sesiones OpenClaw: {'si' if sessions_usage.get('tracked') else 'no'}",
        "",
        "## Paneles",
    ]

    for component in PANEL_COMPONENTS:
        current = panel_components.get(component, {})
        lines.extend(
            [
                f"### {component}",
                f"- updated/skipped/failed: {current.get('updated', 0)}/{current.get('skipped', 0)}/{current.get('failed', 0)}",
                f"- Notion reads/writes: {current.get('notion_reads', 0)}/{current.get('notion_writes', 0)}",
                f"- Worker calls: {current.get('worker_calls', 0)}",
                f"- Ultimo estado: {current.get('last_status') or 'n/a'}",
                f"- Ultimo trigger: {current.get('last_trigger') or 'n/a'}",
                f"- Ultimo ts: {current.get('last_ts') or 'n/a'}",
                "",
            ]
        )

    lines.append("## OpenClaw runtime")
    if runtime["top_tasks"]:
        lines.append("| Task | Completed | Failed | Blocked | Avg ms |")
        lines.append("|------|-----------|--------|---------|--------|")
        for item in runtime["top_tasks"]:
            lines.append(
                f"| {item['name']} | {item['completed']} | {item['failed']} | {item['blocked']} | {item['avg_duration_ms']} |"
            )
    else:
        lines.append("- Sin eventos de tareas con source `openclaw_gateway` en la ventana.")
    lines.append("")

    lines.append("## LLM usage")
    if llm_usage["tracked"]:
        lines.append("| Provider | Calls | Prompt | Completion | Total | Avg ms | Cost proxy USD |")
        lines.append("|----------|-------|--------|------------|-------|--------|----------------|")
        for item in llm_usage["by_provider"]:
            lines.append(
                f"| {item['name']} | {item['calls']} | {item['prompt_tokens']} | {item['completion_tokens']} | {item['total_tokens']} | {item['avg_duration_ms']} | {item['estimated_cost_proxy_usd']:.6f} |"
            )
        lines.append("")
        lines.append("### By usage component")
        lines.append("| Component | Calls | Tokens | Cost proxy USD |")
        lines.append("|-----------|-------|--------|----------------|")
        for item in llm_usage["by_usage_component"]:
            lines.append(
                f"| {item['name']} | {item['calls']} | {item['total_tokens']} | {item['estimated_cost_proxy_usd']:.6f} |"
            )
    else:
        lines.append("- No hay eventos `llm_usage` suficientes en la ventana.")
    lines.append("")

    lines.append("## Session usage")
    if sessions_usage.get("tracked"):
        lines.append(f"- Sessions root: `{sessions_usage.get('root')}`")
        lines.append("| Agent | Sessions | Input | Output | Total | Cache read | Cost proxy USD |")
        lines.append("|-------|----------|-------|--------|-------|------------|----------------|")
        for item in sessions_usage.get("agents", []):
            lines.append(
                f"| {item['name']} | {item['sessions']} | {item['input_tokens']} | {item['output_tokens']} | {item['total_tokens']} | {item['cache_read']} | {item['estimated_cost_proxy_usd']:.6f} |"
            )
        lines.append("")
        lines.append("### By model")
        lines.append("| Model | Provider | Sessions | Total | Cost proxy USD |")
        lines.append("|-------|----------|----------|-------|----------------|")
        for item in sessions_usage.get("by_model", []):
            lines.append(
                f"| {item['name']} | {item['provider']} | {item['sessions']} | {item['total_tokens']} | {item['estimated_cost_proxy_usd']:.6f} |"
            )
    else:
        lines.append("- No se cargaron snapshots `sessions.json` en esta ejecucion.")
    lines.append("")

    if runtime["recent_failures"]:
        lines.append("## Recent failures")
        for item in runtime["recent_failures"]:
            lines.append(
                f"- {item.get('ts')}: `{item.get('task')}` -> {item.get('error')}"
            )
        lines.append("")

    lines.append("## Limitations")
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    events = load_events(days=args.days, ops_log_path=args.ops_log_path)
    report = build_snapshot(events, days=args.days, sessions_root=args.sessions_root)
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(to_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
