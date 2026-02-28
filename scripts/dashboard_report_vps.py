#!/usr/bin/env python3
"""
Dashboard Report — Genera metricas completas y actualiza Dashboard Rick en Notion.

Ejecutar en la VPS (cron cada 15 min). Requiere:
  - Worker local en 8088 con NOTION_DASHBOARD_PAGE_ID y NOTION_* configurados.
  - REDIS_URL, WORKER_URL (default http://127.0.0.1:8088), WORKER_TOKEN.
  - Opcional: WORKER_URL_VM para comprobar estado de la VM.

Uso:
  cd ~/umbral-agent-stack && source .venv/bin/activate && PYTHONPATH=. python scripts/dashboard_report_vps.py
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
    """Lee cuotas de cada proveedor desde Redis."""
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
        for name, cfg in providers.items():
            limit = int(cfg.get("limit_requests", 100))
            used = int(r.get(f"umbral:quota:{name}:used") or 0)
            pct = round((used / limit * 100) if limit > 0 else 0, 1)
            window_h = round(int(cfg.get("window_seconds", 3600)) / 3600, 1)
            result.append({
                "provider": name,
                "used": used,
                "limit": limit,
                "pct": pct,
                "window_h": window_h,
            })
        return result
    except Exception:
        return []


def _team_stats() -> list[dict]:
    """Lee equipos y su estado actual."""
    try:
        import yaml
        teams_path = repo_root / "config" / "teams.yaml"
        if not teams_path.exists():
            return []
        with open(teams_path) as f:
            data = yaml.safe_load(f)
        teams = data.get("teams", {})
        result = []
        for name, info in teams.items():
            result.append({
                "team": name,
                "supervisor": info.get("supervisor") or "—",
                "description": info.get("description", ""),
                "requires_vm": info.get("requires_vm", False),
            })
        return result
    except Exception:
        return []


def _recent_tasks(limit: int = 10) -> list[dict]:
    """Lee las ultimas tareas completadas/fallidas de Redis."""
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
            result.append({
                "task": t.get("task", "?"),
                "team": t.get("team", "?"),
                "status": t.get("status", "?"),
                "duration_s": duration,
                "task_id": t.get("task_id", "?")[:8],
            })
        return result
    except Exception:
        return []


def _ops_log_summary() -> dict:
    """Resumen del operations log."""
    try:
        from infra.ops_logger import OpsLogger
        ol = OpsLogger()
        events = ol.read_events(limit=500)
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

        return {
            "total_events": len(events),
            "completed": completed,
            "failed": failed,
            "blocked": blocked,
            "success_rate": round(completed / (completed + failed) * 100, 1) if (completed + failed) > 0 else 0,
            "models_used": models_used,
        }
    except Exception:
        return {"total_events": 0}


def build_dashboard_payload() -> dict:
    """Construye el payload completo para el dashboard."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    vps_health = _worker_health(WORKER_URL)
    vm_health = _worker_health(WORKER_URL_VM) if WORKER_URL_VM else None
    redis = _redis_stats()
    quotas = _quota_stats()
    teams = _team_stats()
    recent = _recent_tasks(8)
    ops = _ops_log_summary()

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
        "redis": redis,
        "quotas": quotas,
        "teams": teams,
        "recent_tasks": recent,
        "ops_summary": ops,
    }


def main() -> int:
    if not WORKER_TOKEN:
        print("WORKER_TOKEN no definido.", file=sys.stderr)
        return 1

    payload = build_dashboard_payload()

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
        print(f"Dashboard actualizado: {data.get('result', data)}")
        return 0
    except Exception as e:
        print(f"Error al actualizar dashboard: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
