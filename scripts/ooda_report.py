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
    for provider in ("azure_foundry", "claude_pro", "claude_opus", "claude_haiku",
                      "gemini_pro", "gemini_flash", "gemini_flash_lite", "gemini_vertex"):
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


def _report_from_langfuse(start: datetime, end: datetime) -> Dict[str, Any]:
    """
    Obtener métricas desde Langfuse SDK para el período dado.

    Retorna traces por provider, tokens, latencia promedio, errores,
    top task_types, y costo estimado.

    Graceful: si LANGFUSE_PUBLIC_KEY no está configurado, retorna datos parciales.
    """
    import os

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").strip()

    if not public_key or not secret_key:
        return {
            "traces": 0,
            "generations": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "tokens_total": 0,
            "by_provider": {},
            "errors": 0,
            "error_details": [],
            "top_task_types": [],
            "avg_latency_ms": 0,
            "estimated_cost_usd": 0.0,
            "source": "langfuse_not_configured",
        }

    try:
        from langfuse import Langfuse

        lf = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

        # Fetch traces within the period
        traces = []
        page = 1
        while True:
            resp = lf.fetch_traces(
                limit=100,
                page=page,
                from_timestamp=start,
                to_timestamp=end,
            )
            batch = resp.data if hasattr(resp, "data") else []
            if not batch:
                break
            traces.extend(batch)
            page += 1
            if len(batch) < 100:
                break

        # Fetch generations (LLM calls) within the period
        generations: List[Any] = []
        page = 1
        while True:
            resp = lf.fetch_observations(
                limit=100,
                page=page,
                type="GENERATION",
                from_start_time=start,
                to_start_time=end,
            )
            batch = resp.data if hasattr(resp, "data") else []
            if not batch:
                break
            generations.extend(batch)
            page += 1
            if len(batch) < 100:
                break

        # Aggregate by provider (model family)
        by_provider: Dict[str, Dict[str, Any]] = {}
        total_input = 0
        total_output = 0
        total_latency_ms = 0
        latency_count = 0
        errors = 0
        error_details: List[str] = []
        task_type_counts: Dict[str, int] = {}

        for gen in generations:
            model = getattr(gen, "model", None) or "unknown"
            # Determine provider from model name
            provider = _model_to_provider(model)

            usage = getattr(gen, "usage", None) or {}
            inp_tokens = 0
            out_tokens = 0
            if isinstance(usage, dict):
                inp_tokens = usage.get("input", 0) or 0
                out_tokens = usage.get("output", 0) or 0
            elif hasattr(usage, "input"):
                inp_tokens = getattr(usage, "input", 0) or 0
                out_tokens = getattr(usage, "output", 0) or 0

            total_input += inp_tokens
            total_output += out_tokens

            # Latency (end_time - start_time)
            start_t = getattr(gen, "start_time", None)
            end_t = getattr(gen, "end_time", None)
            gen_latency_ms = 0
            if start_t and end_t:
                delta = (end_t - start_t).total_seconds() * 1000
                gen_latency_ms = delta
                total_latency_ms += delta
                latency_count += 1

            # Error detection
            level = getattr(gen, "level", "DEFAULT")
            status_msg = getattr(gen, "status_message", None)
            if level == "ERROR" or (status_msg and "error" in str(status_msg).lower()):
                errors += 1
                error_details.append(f"{provider}: {status_msg or level}")

            if provider not in by_provider:
                by_provider[provider] = {
                    "calls": 0,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "total_latency_ms": 0,
                    "latency_count": 0,
                    "errors": 0,
                }
            by_provider[provider]["calls"] += 1
            by_provider[provider]["tokens_input"] += inp_tokens
            by_provider[provider]["tokens_output"] += out_tokens
            by_provider[provider]["total_latency_ms"] += gen_latency_ms
            by_provider[provider]["latency_count"] += 1
            if level == "ERROR":
                by_provider[provider]["errors"] += 1

        # Task type counts from traces metadata
        for trace in traces:
            metadata = getattr(trace, "metadata", None) or {}
            if isinstance(metadata, dict):
                tt = metadata.get("task_type", "unknown")
            else:
                tt = "unknown"
            task_type_counts[tt] = task_type_counts.get(tt, 0) + 1

        top_task_types = sorted(task_type_counts.items(), key=lambda x: -x[1])[:5]

        # Compute avg latency per provider
        for prov, data in by_provider.items():
            cnt = data.pop("latency_count", 0)
            data["avg_latency_ms"] = round(data.pop("total_latency_ms", 0) / cnt, 1) if cnt > 0 else 0

        avg_latency = round(total_latency_ms / latency_count, 1) if latency_count > 0 else 0
        total_tokens = total_input + total_output

        # Estimated cost (rough rates per 1K tokens)
        cost = _estimate_cost(by_provider)

        lf.flush()

        return {
            "traces": len(traces),
            "generations": len(generations),
            "tokens_input": total_input,
            "tokens_output": total_output,
            "tokens_total": total_tokens,
            "by_provider": by_provider,
            "errors": errors,
            "error_details": error_details[:10],
            "top_task_types": top_task_types,
            "avg_latency_ms": avg_latency,
            "estimated_cost_usd": cost,
            "source": "langfuse",
        }
    except ImportError:
        return {
            "traces": 0,
            "generations": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "tokens_total": 0,
            "by_provider": {},
            "errors": 0,
            "error_details": [],
            "top_task_types": [],
            "avg_latency_ms": 0,
            "estimated_cost_usd": 0.0,
            "source": "langfuse_sdk_not_installed",
        }
    except Exception as e:
        return {
            "traces": 0,
            "generations": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "tokens_total": 0,
            "by_provider": {},
            "errors": 0,
            "error_details": [str(e)],
            "top_task_types": [],
            "avg_latency_ms": 0,
            "estimated_cost_usd": 0.0,
            "source": f"langfuse_error:{type(e).__name__}",
        }


def _model_to_provider(model: str) -> str:
    """Map a model string to a provider name for aggregation."""
    m = model.lower()
    if "gemini" in m:
        return "gemini"
    if "copilot" in m:
        return "copilot"
    if "gpt" in m or "openai" in m:
        return "openai"
    if "claude" in m or "anthropic" in m:
        return "anthropic"
    return model


# Rough cost per 1K tokens (USD) for estimation
_COST_RATES = {
    "gemini": {"input": 0.00035, "output": 0.00105},
    "openai": {"input": 0.00015, "output": 0.0006},
    "anthropic": {"input": 0.003, "output": 0.015},
    "copilot": {"input": 0.00015, "output": 0.0006},
}


def _estimate_cost(by_provider: Dict[str, Dict[str, Any]]) -> float:
    """Estimate total cost in USD from per-provider token counts."""
    total = 0.0
    for provider, data in by_provider.items():
        rates = _COST_RATES.get(provider, {"input": 0.001, "output": 0.002})
        inp = data.get("tokens_input", 0)
        out = data.get("tokens_output", 0)
        total += (inp / 1000) * rates["input"] + (out / 1000) * rates["output"]
    return round(total, 4)


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    start, end = _week_range(args.week_ago)
    redis_stats = _report_from_redis()
    langfuse_stats = _report_from_langfuse(start, end)

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
    by_provider = llm.get("by_provider", {})
    source = llm.get("source", "unknown")

    start_str = p["start"][:10]
    end_str = p["end"][:10]

    # Header
    lines = [f"📊 OODA Weekly Report — Semana del {start_str} al {end_str}", ""]

    # == Observe ==
    lines.append("== Observe ==")
    total_tasks = t.get("completed", 0) + t.get("failed", 0) + t.get("blocked", 0)
    lines.append(f"- Total tareas procesadas: {total_tasks}")
    lines.append(f"  - Completadas: {t.get('completed', 0)}")
    lines.append(f"  - Fallidas: {t.get('failed', 0)}")
    lines.append(f"  - Bloqueadas: {t.get('blocked', 0)}")
    lines.append(f"  - Pendientes: {pending}")

    total_llm_calls = llm.get("generations", 0)
    if total_llm_calls > 0:
        lines.append(f"- Total LLM calls: {total_llm_calls}")
        if by_provider:
            provider_summary = ", ".join(
                f"{prov} ({data.get('calls', 0)})" for prov, data in by_provider.items()
            )
            lines.append(f"- Providers: {provider_summary}")
        tokens_total = llm.get("tokens_total", 0)
        tokens_in = llm.get("tokens_input", 0)
        tokens_out = llm.get("tokens_output", 0)
        lines.append(f"- Tokens totales: {_fmt_tokens(tokens_total)} (input: {_fmt_tokens(tokens_in)}, output: {_fmt_tokens(tokens_out)})")
    elif source in ("langfuse_not_configured", "langfuse_sdk_not_installed"):
        lines.append(f"- LLM metrics: ⚠️ Langfuse no configurado — datos parciales desde Redis")
    else:
        lines.append(f"- LLM calls: 0 (source: {source})")

    if quota:
        lines.append("- Cuotas Redis (requests usados):")
        for provider, used in quota.items():
            lines.append(f"  - {provider}: {used}")

    lines.append("")

    # == Orient ==
    lines.append("== Orient ==")
    if by_provider and total_llm_calls > 0:
        for prov, data in sorted(by_provider.items(), key=lambda x: -x[1].get("calls", 0)):
            calls = data.get("calls", 0)
            pct = round(calls / total_llm_calls * 100, 1) if total_llm_calls > 0 else 0
            avg_lat = data.get("avg_latency_ms", 0)
            prov_errors = data.get("errors", 0)
            lines.append(f"- {prov}: {pct}% del volumen, latencia promedio {avg_lat}ms, {prov_errors} errores")
    else:
        lines.append("- Sin datos LLM detallados disponibles")

    error_count = llm.get("errors", 0)
    if error_count > 0:
        error_rate = round(error_count / total_llm_calls * 100, 1) if total_llm_calls > 0 else 0
        lines.append(f"- Errores totales: {error_count} ({error_rate}%)")
        for detail in llm.get("error_details", [])[:5]:
            lines.append(f"  - {detail}")

    top_tasks = llm.get("top_task_types", [])
    if top_tasks:
        lines.append("- Top task_types por volumen:")
        for tt, count in top_tasks:
            lines.append(f"  - {tt}: {count}")

    lines.append("")

    # == Decide ==
    lines.append("== Decide ==")
    recommendations = _generate_recommendations(t, llm)
    if recommendations:
        for rec in recommendations:
            lines.append(f"- {rec}")
    else:
        lines.append("- Sin recomendaciones especiales esta semana")

    lines.append("")

    # == Act ==
    lines.append("== Act ==")
    actions = _generate_actions(t, llm)
    if actions:
        lines.append("- Acciones sugeridas:")
        for i, action in enumerate(actions, 1):
            lines.append(f"  {i}. {action}")
    else:
        lines.append("- No se requieren acciones inmediatas")

    lines.append("")
    lines.append("---")
    lines.append(f"*Generado: {report['generated_at']}*")
    lines.append(f"*Fuente tareas: {t.get('source', 'unknown')} | Fuente LLM: {source}*")

    return "\n".join(lines) + "\n"


def _fmt_tokens(n: int) -> str:
    """Format token count with K/M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _generate_recommendations(tasks: Dict, llm: Dict) -> List[str]:
    """Generate Orient→Decide recommendations from the data."""
    recs = []
    by_prov = llm.get("by_provider", {})
    total_calls = llm.get("generations", 0)

    # High error rate
    error_count = llm.get("errors", 0)
    if total_calls > 0 and error_count / total_calls > 0.05:
        recs.append(f"Tasa de error elevada: {error_count}/{total_calls} ({round(error_count/total_calls*100,1)}%) — investigar")

    # Provider concentration
    for prov, data in by_prov.items():
        calls = data.get("calls", 0)
        if total_calls > 0 and calls / total_calls > 0.8:
            recs.append(f"{prov} concentra {round(calls/total_calls*100)}% del tráfico — considerar distribuir carga")

    # High failure rate in tasks
    completed = tasks.get("completed", 0)
    failed = tasks.get("failed", 0)
    total_tasks = completed + failed
    if total_tasks > 0 and failed / total_tasks > 0.1:
        recs.append(f"Tasa de fallos en tareas: {failed}/{total_tasks} ({round(failed/total_tasks*100,1)}%)")

    # High pending queue
    pending = tasks.get("pending", 0)
    if pending > 20:
        recs.append(f"Cola pendiente alta: {pending} tareas — considerar escalar workers")

    return recs


def _generate_actions(tasks: Dict, llm: Dict) -> List[str]:
    """Generate Decide→Act suggested actions."""
    actions = []
    by_prov = llm.get("by_provider", {})

    # Provider-specific errors
    for prov, data in by_prov.items():
        if data.get("errors", 0) > 3:
            actions.append(f"Revisar errores de {prov} ({data['errors']} esta semana)")

    # Latency issues
    for prov, data in by_prov.items():
        avg_lat = data.get("avg_latency_ms", 0)
        if avg_lat > 5000:
            actions.append(f"Investigar latencia de {prov}: {avg_lat}ms promedio (>5s)")

    # Cost optimization hints
    cost = llm.get("estimated_cost_usd", 0)
    if cost > 10:
        actions.append(f"Costo estimado ${cost:.2f} — evaluar optimización de prompts o modelos más baratos")

    # High blocked tasks
    blocked = tasks.get("blocked", 0)
    if blocked > 5:
        actions.append(f"Desbloquear {blocked} tareas bloqueadas en cola")

    if not actions:
        actions.append("Mantener configuración actual — métricas dentro de parámetros normales")

    return actions


def main() -> None:
    args = _parse_args()
    report = build_report(args)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(to_markdown(report))


if __name__ == "__main__":
    main()
