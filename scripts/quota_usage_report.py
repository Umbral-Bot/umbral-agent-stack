#!/usr/bin/env python3
"""
Quota Usage Report — Métricas de aprovechamiento de cuotas LLM.

Lee el estado de cuotas de Redis (o fakeredis para pruebas) y el ops_log
para generar un reporte de utilización por proveedor.

Uso:
    python scripts/quota_usage_report.py              # stdout (para cron)
    python scripts/quota_usage_report.py --json       # salida JSON
    python scripts/quota_usage_report.py --json -o report.json  # archivo

Requiere:
    - Redis accesible (REDIS_URL env) o --fake para pruebas sin Redis
    - config/quota_policy.yaml
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load .env if available
try:
    from scripts import env_loader
    env_loader.load()
except Exception:
    pass

logger = logging.getLogger("scripts.quota_usage_report")

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_quota_policy() -> Dict[str, Dict[str, Any]]:
    """Load providers config from config/quota_policy.yaml."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed; using hardcoded defaults")
        return _default_providers()

    path = REPO_ROOT / "config" / "quota_policy.yaml"
    if not path.is_file():
        logger.warning("quota_policy.yaml not found; using defaults")
        return _default_providers()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    providers = {}
    for pid, cfg in (data.get("providers") or {}).items():
        if isinstance(cfg, dict):
            providers[pid] = {
                "limit_requests": int(cfg.get("limit_requests", 100)),
                "window_seconds": int(cfg.get("window_seconds", 3600)),
                "warn": float(cfg.get("warn", 0.8)),
                "restrict": float(cfg.get("restrict", 0.9)),
            }
    return providers


def _default_providers() -> Dict[str, Dict[str, Any]]:
    """Fallback hardcoded from quota_policy.yaml."""
    return {
        "claude_pro": {"limit_requests": 200, "window_seconds": 18000, "warn": 0.80, "restrict": 0.90},
        "chatgpt_plus": {"limit_requests": 300, "window_seconds": 10800, "warn": 0.70, "restrict": 0.90},
        "gemini_pro": {"limit_requests": 500, "window_seconds": 86400, "warn": 0.80, "restrict": 0.95},
        "copilot_pro": {"limit_requests": 400, "window_seconds": 2592000, "warn": 0.70, "restrict": 0.85},
    }


# ---------------------------------------------------------------------------
# Redis quota state
# ---------------------------------------------------------------------------

REDIS_KEY_USED = "umbral:quota:{provider}:used"
REDIS_KEY_WINDOW_END = "umbral:quota:{provider}:window_end"


def get_redis_client(fake: bool = False):
    """Get Redis or fakeredis client."""
    if fake:
        try:
            import fakeredis
            return fakeredis.FakeRedis(decode_responses=True)
        except ImportError:
            raise RuntimeError("fakeredis not installed (pip install fakeredis)")

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis as redis_lib
        client = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        raise RuntimeError(f"Cannot connect to Redis at {redis_url}: {e}")


def read_quota_state(redis_client, providers: Dict[str, Dict]) -> Dict[str, Dict[str, Any]]:
    """Read current quota state from Redis for all providers."""
    now = time.time()
    result = {}

    for provider, cfg in providers.items():
        key_used = REDIS_KEY_USED.format(provider=provider)
        key_end = REDIS_KEY_WINDOW_END.format(provider=provider)

        used_raw = redis_client.get(key_used)
        end_raw = redis_client.get(key_end)

        used = int(used_raw) if used_raw else 0
        window_end = float(end_raw) if end_raw else 0.0
        limit = cfg["limit_requests"]
        window_secs = cfg["window_seconds"]

        # Window status
        if window_end == 0.0:
            window_status = "never_started"
            remaining_secs = window_secs
        elif now >= window_end:
            window_status = "expired"
            remaining_secs = 0
        else:
            window_status = "active"
            remaining_secs = int(window_end - now)

        pct = (used / limit * 100) if limit > 0 else 0.0
        warn_pct = cfg["warn"] * 100
        restrict_pct = cfg["restrict"] * 100

        if pct >= restrict_pct:
            health = "RESTRICTED"
        elif pct >= warn_pct:
            health = "WARNING"
        else:
            health = "OK"

        result[provider] = {
            "used": used,
            "limit": limit,
            "pct": round(pct, 1),
            "health": health,
            "window_seconds": window_secs,
            "window_status": window_status,
            "remaining_seconds": remaining_secs,
            "warn_threshold": cfg["warn"],
            "restrict_threshold": cfg["restrict"],
        }

    return result


# ---------------------------------------------------------------------------
# Ops log analysis
# ---------------------------------------------------------------------------

OPS_LOG_DEFAULT = Path.home() / ".config" / "umbral" / "ops_log.jsonl"


def read_ops_log(log_path: Optional[Path] = None, hours: int = 24) -> List[Dict[str, Any]]:
    """Read ops_log events from the last N hours."""
    path = log_path or Path(os.environ.get("UMBRAL_OPS_LOG_DIR", str(OPS_LOG_DEFAULT.parent))) / "ops_log.jsonl"

    if not path.exists():
        logger.info("No ops_log found at %s", path)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    events = []

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue

        ts_str = ev.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

        if ts >= cutoff:
            events.append(ev)

    return events


def analyze_ops_log(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze ops_log events for model usage stats."""
    model_requests: Dict[str, int] = {}
    model_completions: Dict[str, int] = {}
    model_failures: Dict[str, int] = {}
    task_types: Dict[str, int] = {}
    total_tasks_completed = 0
    total_tasks_failed = 0

    for ev in events:
        event_type = ev.get("event", "")
        model = ev.get("model", "unknown")

        if event_type == "task_completed":
            total_tasks_completed += 1
            model_completions[model] = model_completions.get(model, 0) + 1

        elif event_type == "task_failed":
            total_tasks_failed += 1
            model_failures[model] = model_failures.get(model, 0) + 1

        elif event_type == "model_selected":
            model_requests[model] = model_requests.get(model, 0) + 1
            tt = ev.get("task_type", "general")
            task_types[tt] = task_types.get(tt, 0) + 1

        elif event_type == "task_queued":
            tt = ev.get("task_type", "general")
            task_types[tt] = task_types.get(tt, 0) + 1

    return {
        "total_events": len(events),
        "tasks_completed": total_tasks_completed,
        "tasks_failed": total_tasks_failed,
        "model_selections": model_requests,
        "model_completions": model_completions,
        "model_failures": model_failures,
        "task_type_distribution": task_types,
    }


# ---------------------------------------------------------------------------
# Underutilization detection
# ---------------------------------------------------------------------------

def detect_underutilized(
    quota_state: Dict[str, Dict],
    ops_analysis: Dict[str, Any],
    hours: int = 24,
) -> List[Dict[str, Any]]:
    """Identify providers with zero or near-zero usage in the observed period."""
    underutilized = []
    completions = ops_analysis.get("model_completions", {})
    selections = ops_analysis.get("model_selections", {})

    for provider, state in quota_state.items():
        uses_in_period = completions.get(provider, 0) + selections.get(provider, 0)
        if uses_in_period == 0 and state["used"] == 0:
            underutilized.append({
                "provider": provider,
                "limit": state["limit"],
                "window_hours": round(state["window_seconds"] / 3600, 1),
                "reason": f"0 requests in last {hours}h and 0 in current quota window",
            })
        elif state["pct"] < 5.0 and uses_in_period < 3:
            underutilized.append({
                "provider": provider,
                "limit": state["limit"],
                "used": state["used"],
                "pct": state["pct"],
                "reason": f"Under 5% utilization ({state['used']}/{state['limit']})",
            })

    return underutilized


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def format_window(seconds: int) -> str:
    """Human readable window duration."""
    if seconds <= 0:
        return "expired"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        h = seconds / 3600
        return f"{h:.1f}h"
    d = seconds / 86400
    return f"{d:.1f}d"


def format_report_stdout(
    quota_state: Dict[str, Dict],
    ops_analysis: Dict[str, Any],
    underutilized: List[Dict],
) -> str:
    """Format a human-readable report for stdout/cron."""
    lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"=== Umbral Quota Usage Report — {now} ===")
    lines.append("")

    # Quota state table
    lines.append("Provider          | Used/Limit | Usage  | Health     | Window")
    lines.append("------------------|------------|--------|------------|--------")
    for provider, s in sorted(quota_state.items()):
        name = provider.ljust(17)
        usage = f"{s['used']}/{s['limit']}".ljust(10)
        pct = f"{s['pct']:5.1f}%".ljust(6)
        health = s["health"].ljust(10)
        window = f"{s['window_status']} ({format_window(s['remaining_seconds'])})"
        lines.append(f"{name} | {usage} | {pct} | {health} | {window}")

    lines.append("")

    # Ops log stats
    lines.append(f"Ops Log (last 24h): {ops_analysis['total_events']} events")
    lines.append(f"  Tasks completed: {ops_analysis['tasks_completed']}")
    lines.append(f"  Tasks failed:    {ops_analysis['tasks_failed']}")

    if ops_analysis["model_completions"]:
        lines.append("  Model completions:")
        for model, count in sorted(ops_analysis["model_completions"].items()):
            lines.append(f"    {model}: {count}")

    if ops_analysis["task_type_distribution"]:
        lines.append("  Task types:")
        for tt, count in sorted(ops_analysis["task_type_distribution"].items()):
            lines.append(f"    {tt}: {count}")

    lines.append("")

    # Underutilized
    if underutilized:
        lines.append("⚠ Underutilized subscriptions:")
        for u in underutilized:
            lines.append(f"  - {u['provider']}: {u['reason']}")
    else:
        lines.append("✓ All subscriptions showing activity")

    lines.append("")
    return "\n".join(lines)


def build_json_report(
    quota_state: Dict[str, Dict],
    ops_analysis: Dict[str, Any],
    underutilized: List[Dict],
) -> Dict[str, Any]:
    """Build structured JSON report for dashboard integration."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quota_state": quota_state,
        "ops_log_24h": ops_analysis,
        "underutilized": underutilized,
        "summary": {
            "total_providers": len(quota_state),
            "providers_ok": sum(1 for s in quota_state.values() if s["health"] == "OK"),
            "providers_warning": sum(1 for s in quota_state.values() if s["health"] == "WARNING"),
            "providers_restricted": sum(1 for s in quota_state.values() if s["health"] == "RESTRICTED"),
            "underutilized_count": len(underutilized),
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Umbral Quota Usage Report")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    parser.add_argument("-o", "--output", type=str, help="Write output to file")
    parser.add_argument("--fake", action="store_true", help="Use fakeredis (for testing without Redis)")
    parser.add_argument("--hours", type=int, default=24, help="Ops log lookback hours (default: 24)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # Load config
    providers = load_quota_policy()
    if not providers:
        print("ERROR: No providers configured in quota_policy.yaml", file=sys.stderr)
        sys.exit(1)

    # Read Redis quota state
    try:
        redis_client = get_redis_client(fake=args.fake)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Hint: Use --fake to run without Redis, or set REDIS_URL", file=sys.stderr)
        sys.exit(1)

    quota_state = read_quota_state(redis_client, providers)

    # Read ops log
    ops_events = read_ops_log(hours=args.hours)
    ops_analysis = analyze_ops_log(ops_events)

    # Detect underutilized
    underutilized = detect_underutilized(quota_state, ops_analysis, hours=args.hours)

    # Generate report
    if args.json:
        report = build_json_report(quota_state, ops_analysis, underutilized)
        output = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    else:
        output = format_report_stdout(quota_state, ops_analysis, underutilized)

    # Output
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
