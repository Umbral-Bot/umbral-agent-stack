#!/usr/bin/env python3
"""
Dashboard Report — Genera metricas completas y actualiza Dashboard Rick en Notion.

Ejecutar en la VPS (cron cada 15 min). Requiere:
  - Worker local en 8088 con NOTION_DASHBOARD_PAGE_ID y NOTION_* configurados.
  - REDIS_URL, WORKER_URL (default http://127.0.0.1:8088), WORKER_TOKEN.
  - Opcional: WORKER_URL_VM para comprobar estado de la VM.

Uso (VPS):
  source ~/.config/openclaw/env   # debe incluir WORKER_TOKEN, NOTION_API_KEY, NOTION_DASHBOARD_PAGE_ID, REDIS_URL
  cd ~/umbral-agent-stack && PYTHONPATH=. python3 scripts/dashboard_report_vps.py [--force]
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import httpx

WORKER_URL = os.environ.get("WORKER_URL", "http://127.0.0.1:8088").rstrip("/")
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
WORKER_URL_VM = os.environ.get("WORKER_URL_VM", "").strip() or None
WORKER_URL_VM_INTERACTIVE = os.environ.get("WORKER_URL_VM_INTERACTIVE", "").strip() or None


def _worker_health(url: str) -> dict:
    try:
        r = httpx.get(f"{url}/health", timeout=5)
        if r.status_code == 200:
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            return {"status": "OK", "tasks": data.get("tasks_registered", [])}
        return {"status": f"Error {r.status_code}", "tasks": []}
    except Exception as e:
        return {"status": f"Offline ({type(e).__name__})", "tasks": []}


def _redis_stats() -> dict:
    try:
        import redis as redis_lib
        r = redis_lib.from_url(REDIS_URL, decode_responses=True)
        pending = r.llen("umbral:tasks:pending")
        blocked = r.llen("umbral:tasks:blocked")
        return {"pending": pending, "blocked": blocked, "connected": True}
    except Exception:
        return {"pending": 0, "blocked": 0, "connected": False}


def _quota_stats() -> list[dict]:
    """Lee cuotas de cada proveedor desde Redis, incluyendo tiempo para reinicio."""
    try:
        import redis as redis_lib
        import yaml
        r = redis_lib.from_url(REDIS_URL, decode_responses=True)
        policy_path = repo_root / "config" / "quota_policy.yaml"
        if not policy_path.exists():
            return []
        with open(policy_path) as f:
            policy = yaml.safe_load(f)
        providers = policy.get("providers", {})
        result = []
        now = time.time()
        for name, cfg in providers.items():
            limit = int(cfg.get("limit_requests", 100))
            used = int(r.get(f"umbral:quota:{name}:used") or 0)
            pct = round((used / limit * 100) if limit > 0 else 0, 1)
            window_sec = int(cfg.get("window_seconds", 3600))
            window_h = round(window_sec / 3600, 1)
            window_end_raw = r.get(f"umbral:quota:{name}:window_end")
            resets_in_min = None
            if window_end_raw:
                secs_left = float(window_end_raw) - now
                if secs_left > 0:
                    resets_in_min = round(secs_left / 60)
            result.append({
                "provider": name,
                "used": used,
                "limit": limit,
                "pct": pct,
                "window_h": window_h,
                "resets_in_min": resets_in_min,
            })
        return result
    except Exception:
        return []


def _team_stats() -> list[dict]:
    """Lee equipos con estadisticas dinamicas de tareas."""
    try:
        import yaml
        import redis as redis_lib
        teams_path = repo_root / "config" / "teams.yaml"
        if not teams_path.exists():
            return []
        with open(teams_path) as f:
            data = yaml.safe_load(f)
        teams = data.get("teams", {})

        team_counts: dict[str, dict] = {name: {"completed": 0, "active": 0} for name in teams}
        try:
            r = redis_lib.from_url(REDIS_URL, decode_responses=True)
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor, match="umbral:task:*", count=200)
                for key in keys:
                    raw = r.get(key)
                    if not raw:
                        continue
                    try:
                        t = json.loads(raw)
                        tm = t.get("team", "system")
                        st = t.get("status", "")
                        if tm in team_counts:
                            if st == "done":
                                team_counts[tm]["completed"] += 1
                            elif st in ("running", "queued"):
                                team_counts[tm]["active"] += 1
                    except Exception:
                        continue
                if cursor == 0:
                    break
        except Exception:
            pass

        result = []
        for name, info in teams.items():
            tc = team_counts.get(name, {})
            result.append({
                "team": name,
                "supervisor": info.get("supervisor") or "—",
                "description": info.get("description", ""),
                "requires_vm": info.get("requires_vm", False),
                "completed": tc.get("completed", 0),
                "active": tc.get("active", 0),
            })
        return result
    except Exception:
        return []


def _recent_tasks(limit: int = 10) -> list[dict]:
    """Lee las ultimas tareas completadas/fallidas de Redis con timestamps."""
    try:
        import redis as redis_lib
        r = redis_lib.from_url(REDIS_URL, decode_responses=True)
        tasks = []
        cursor = 0
        while len(tasks) < limit * 3:
            cursor, keys = r.scan(cursor, match="umbral:task:*", count=100)
            for key in keys:
                raw = r.get(key)
                if not raw:
                    continue
                try:
                    t = json.loads(raw)
                    status = t.get("status", "")
                    if status in ("done", "failed"):
                        tasks.append(t)
                except Exception:
                    continue
            if cursor == 0:
                break
        tasks.sort(key=lambda x: x.get("completed_at") or x.get("failed_at") or 0, reverse=True)
        result = []
        for t in tasks[:limit]:
            started = t.get("started_at", 0)
            ended = t.get("completed_at") or t.get("failed_at") or 0
            duration = round(ended - started, 1) if (started and ended) else 0
            when = ""
            if ended:
                try:
                    when = datetime.fromtimestamp(ended, tz=timezone.utc).strftime("%H:%M %d/%m")
                except Exception:
                    pass
            result.append({
                "task": t.get("task", "?"),
                "team": t.get("team", "?"),
                "status": t.get("status", "?"),
                "duration_s": duration,
                "task_id": t.get("task_id", "?")[:8],
                "when": when,
            })
        return result
    except Exception:
        return []


def _running_tasks() -> list[dict]:
    """Tareas actualmente en ejecucion."""
    try:
        import redis as redis_lib
        r = redis_lib.from_url(REDIS_URL, decode_responses=True)
        tasks = []
        cursor = 0
        now = time.time()
        while True:
            cursor, keys = r.scan(cursor, match="umbral:task:*", count=200)
            for key in keys:
                raw = r.get(key)
                if not raw:
                    continue
                try:
                    t = json.loads(raw)
                    if t.get("status") == "running":
                        started = t.get("started_at", 0)
                        elapsed = f"{round(now - started)}s" if started else "?"
                        tasks.append({
                            "task": t.get("task", "?"),
                            "team": t.get("team", "?"),
                            "elapsed": elapsed,
                        })
                except Exception:
                    continue
            if cursor == 0:
                break
        return tasks
    except Exception:
        return []


def _last_error() -> str | None:
    """Ultimo error registrado en ops_log."""
    try:
        from infra.ops_logger import OpsLogger
        ol = OpsLogger()
        events = ol.read_events(limit=200, event_filter="task_failed")
        if events:
            last = events[-1]
            return f"{last.get('task', '?')} — {last.get('error', '?')[:150]}"
    except Exception:
        pass
    return None


def _active_alerts(quotas: list[dict], vps_health: dict, vm_health: dict | None) -> list[str]:
    """Alertas activas basadas en cuotas y estado de workers."""
    alerts = []
    for q in quotas:
        if q["pct"] >= 90:
            alerts.append(f"CUOTA CRITICA: {q['provider']} al {q['pct']}%")
        elif q["pct"] >= 70:
            alerts.append(f"Cuota alta: {q['provider']} al {q['pct']}%")
    if vps_health.get("status") != "OK":
        alerts.append(f"Worker VPS: {vps_health.get('status', '?')}")
    if vm_health and vm_health.get("status") != "OK":
        alerts.append(f"Worker VM: {vm_health.get('status', '?')}")
    return alerts


def _system_uptime() -> str | None:
    """Uptime estimado desde el primer evento en ops_log."""
    try:
        from infra.ops_logger import OpsLogger
        from datetime import datetime as dt
        ol = OpsLogger()
        events = ol.read_events(limit=5000)
        if events:
            first_ts = events[0].get("ts", "")
            if first_ts:
                start = dt.fromisoformat(first_ts.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                delta = now - start
                days = delta.days
                hours = delta.seconds // 3600
                if days > 0:
                    return f"{days}d {hours}h"
                return f"{hours}h {(delta.seconds % 3600) // 60}m"
    except Exception:
        pass
    return None


def _ops_log_summary() -> dict:
    """Resumen enriquecido del operations log con tendencia."""
    try:
        from infra.ops_logger import OpsLogger
        from datetime import timedelta
        ol = OpsLogger()
        events = ol.read_events(limit=5000)
        if not events:
            return {"total_events": 0}

        completed = sum(1 for e in events if e.get("event") == "task_completed")
        failed = sum(1 for e in events if e.get("event") == "task_failed")
        blocked = sum(1 for e in events if e.get("event") == "task_blocked")
        models_used: dict[str, int] = {}
        for e in events:
            if e.get("event") == "task_completed":
                m = e.get("model", "unknown")
                models_used[m] = models_used.get(m, 0) + 1

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        completed_today = sum(
            1 for e in events
            if e.get("event") == "task_completed" and e.get("ts", "").startswith(today_str)
        )
        completed_yesterday = sum(
            1 for e in events
            if e.get("event") == "task_completed" and e.get("ts", "").startswith(yesterday_str)
        )
        if completed_yesterday > 0 and completed_today > 0:
            diff_pct = round((completed_today - completed_yesterday) / completed_yesterday * 100)
            trend = f"+{diff_pct}% vs ayer" if diff_pct >= 0 else f"{diff_pct}% vs ayer"
        elif completed_today > 0:
            trend = f"{completed_today} hoy (sin datos de ayer)"
        else:
            trend = ""

        return {
            "total_events": len(events),
            "completed": completed,
            "failed": failed,
            "blocked": blocked,
            "completed_today": completed_today,
            "success_rate": round(completed / (completed + failed) * 100, 1) if (completed + failed) > 0 else 0,
            "models_used": models_used,
            "trend": trend,
        }
    except Exception:
        return {"total_events": 0}


def build_dashboard_payload() -> dict:
    """Construye el payload completo para el dashboard."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    vps_health = _worker_health(WORKER_URL)
    vm_health = _worker_health(WORKER_URL_VM) if WORKER_URL_VM else None
    vm_interactive_health = _worker_health(WORKER_URL_VM_INTERACTIVE) if WORKER_URL_VM_INTERACTIVE else None
    redis = _redis_stats()
    quotas = _quota_stats()
    teams = _team_stats()
    recent = _recent_tasks(8)
    running = _running_tasks()
    ops = _ops_log_summary()
    uptime = _system_uptime()
    last_err = _last_error()
    alerts = _active_alerts(quotas, vps_health, vm_health or vm_interactive_health)

    if vps_health["status"] == "OK" and redis["connected"]:
        overall = "Operativo"
    elif vps_health["status"] == "OK":
        overall = "Parcial (Redis offline)"
    else:
        overall = "Degradado"

    return {
        "dashboard_v2": True,
        "timestamp": now,
        "overall_status": overall,
        "vps_worker": vps_health,
        "vm_worker": vm_health,
        "vm_worker_interactive": vm_interactive_health,
        "redis": redis,
        "quotas": quotas,
        "teams": teams,
        "recent_tasks": recent,
        "running_tasks": running,
        "ops_summary": ops,
        "uptime": uptime,
        "last_error": last_err,
        "active_alerts": alerts,
    }


_FINGERPRINT_PATH = Path.home() / ".config" / "umbral" / "dashboard_fingerprint"


def _payload_fingerprint(payload: dict) -> str:
    """Hash estable del payload, excluyendo timestamp (cambia cada vez)."""
    import hashlib
    stable = {k: v for k, v in payload.items() if k != "timestamp"}
    raw = json.dumps(stable, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Dashboard report -> Notion")
    p.add_argument("--force", action="store_true", help="Forzar update aunque no haya cambios")
    args = p.parse_args()

    if not WORKER_TOKEN:
        print("WORKER_TOKEN no definido.", file=sys.stderr)
        return 1

    payload = build_dashboard_payload()
    fp = _payload_fingerprint(payload)

    if not args.force:
        try:
            prev = _FINGERPRINT_PATH.read_text().strip()
            if prev == fp:
                print(f"Sin cambios (fingerprint={fp}). Skipping Notion update.")
                return 0
        except FileNotFoundError:
            pass

    request_body = {
        "task": "notion.update_dashboard",
        "input": {"metrics": payload},
    }
    try:
        r = httpx.post(
            f"{WORKER_URL}/run",
            json=request_body,
            headers={"Authorization": f"Bearer {WORKER_TOKEN}", "Content-Type": "application/json"},
            timeout=90,
        )
        r.raise_for_status()
        data = r.json()
        _FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _FINGERPRINT_PATH.write_text(fp)
        print(f"Dashboard actualizado (fp={fp}): {data.get('result', data)}")
        return 0
    except Exception as e:
        print(f"Error al actualizar dashboard: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
