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
from typing import Any

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import httpx

from infra.ops_logger import OpsLogger, ops_log

WORKER_URL = os.environ.get("WORKER_URL", "http://127.0.0.1:8088").rstrip("/")
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
WORKER_URL_VM = os.environ.get("WORKER_URL_VM", "").strip() or None
WORKER_URL_VM_INTERACTIVE = os.environ.get("WORKER_URL_VM_INTERACTIVE", "").strip() or None
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "").strip()
NOTION_CONTROL_ROOM_PAGE_ID = os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID", "").strip()
NOTION_TASKS_DB_ID = os.environ.get("NOTION_TASKS_DB_ID", "").strip()
NOTION_DELIVERABLES_DB_ID = os.environ.get("NOTION_DELIVERABLES_DB_ID", "").strip()
NOTION_BRIDGE_DB_ID = os.environ.get("NOTION_BRIDGE_DB_ID", "").strip()
LEGACY_BRIDGE_DB_ID = "8496ee73-6c7d-43a3-89cf-b9c8825b5dfc"
CALLER_ID = "script.dashboard_report_vps"
_DASHBOARD_STATS: dict[str, int] = {
    "notion_reads": 0,
    "notion_writes": 0,
    "worker_calls": 0,
}


def _reset_dashboard_stats() -> None:
    _DASHBOARD_STATS["notion_reads"] = 0
    _DASHBOARD_STATS["notion_writes"] = 0
    _DASHBOARD_STATS["worker_calls"] = 0


def _record_dashboard_stats(*, notion_reads: int = 0, notion_writes: int = 0, worker_calls: int = 0) -> None:
    _DASHBOARD_STATS["notion_reads"] += notion_reads
    _DASHBOARD_STATS["notion_writes"] += notion_writes
    _DASHBOARD_STATS["worker_calls"] += worker_calls

TECHNICAL_TASK_PREFIXES = (
    "windows.fs.",
    "ping",
    "notion.poll_comments",
    "notion.read_page",
    "notion.read_database",
    "notion.search_databases",
)


def _vm_recovery_mode() -> dict[str, object] | None:
    """Detecta cuando la VM se expone via workaround local (tunel reverso)."""
    urls = [u for u in (WORKER_URL_VM, WORKER_URL_VM_INTERACTIVE) if u]
    if not urls:
        return {"enabled": False}
    if all("127.0.0.1:28" in u for u in urls):
        return {
            "enabled": True,
            "transport": "reverse_ssh_tunnel",
            "headless_url": WORKER_URL_VM,
            "interactive_url": WORKER_URL_VM_INTERACTIVE,
        }
    return {"enabled": False}


def _worker_health(url: str) -> dict:
    try:
        _record_dashboard_stats(worker_calls=1)
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


def _notion_query_rows(database_id: str) -> list[dict]:
    if not NOTION_API_KEY or not database_id:
        return []
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    rows: list[dict] = []
    next_cursor: str | None = None
    while True:
        body: dict[str, object] = {"page_size": 100}
        if next_cursor:
            body["start_cursor"] = next_cursor
        resp = httpx.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers,
            json=body,
            timeout=20,
        )
        _record_dashboard_stats(notion_reads=1)
        resp.raise_for_status()
        data = resp.json()
        rows.extend(data.get("results", []))
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
    return rows


def _notion_list_children(page_id: str) -> list[dict[str, Any]]:
    if not NOTION_API_KEY or not page_id:
        return []
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    rows: list[dict[str, Any]] = []
    next_cursor: str | None = None
    while True:
        params: dict[str, object] = {"page_size": 100}
        if next_cursor:
            params["start_cursor"] = next_cursor
        resp = httpx.get(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=headers,
            params=params,
            timeout=20,
        )
        _record_dashboard_stats(notion_reads=1)
        resp.raise_for_status()
        data = resp.json()
        rows.extend(data.get("results", []))
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
    return rows


def _find_child_database_id(page_id: str, title: str) -> str | None:
    wanted = title.strip().lower()
    try:
        children = _notion_list_children(page_id)
    except Exception:
        return None
    for block in children:
        if block.get("type") != "child_database":
            continue
        current = ((block.get("child_database") or {}).get("title") or "").strip().lower()
        if current == wanted:
            return block.get("id")
    return None


def _resolve_bridge_db_id() -> str:
    if NOTION_BRIDGE_DB_ID:
        return NOTION_BRIDGE_DB_ID
    if NOTION_CONTROL_ROOM_PAGE_ID:
        discovered = _find_child_database_id(NOTION_CONTROL_ROOM_PAGE_ID, "Bandeja Puente")
        if discovered:
            return discovered
    return LEGACY_BRIDGE_DB_ID


def _plain(prop: dict | None):
    if not isinstance(prop, dict):
        return None
    typ = prop.get("type")
    if typ == "title":
        return "".join(x.get("plain_text", "") for x in prop.get("title", []))
    if typ == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
    if typ == "select":
        return (prop.get("select") or {}).get("name")
    if typ == "status":
        return (prop.get("status") or {}).get("name")
    if typ == "relation":
        return [x.get("id") for x in prop.get("relation", [])]
    return None


def _notion_ops_summary() -> dict | None:
    if not (NOTION_API_KEY and NOTION_TASKS_DB_ID and NOTION_DELIVERABLES_DB_ID):
        return None
    try:
        tasks = _notion_query_rows(NOTION_TASKS_DB_ID)
        deliverables = _notion_query_rows(NOTION_DELIVERABLES_DB_ID)
        bridge = _notion_query_rows(_resolve_bridge_db_id())
    except Exception:
        return None

    tasks_unlinked = 0
    for row in tasks:
        props = row.get("properties", {})
        if not (_plain(props.get("Proyecto")) or []) and not (_plain(props.get("Entregable")) or []):
            tasks_unlinked += 1

    deliverables_pending = 0
    deliverables_adjustments = 0
    for row in deliverables:
        review = (_plain(row.get("properties", {}).get("Estado revision")) or "").strip()
        if review == "Pendiente revision":
            deliverables_pending += 1
        elif review == "Aprobado con ajustes":
            deliverables_adjustments += 1

    bridge_live = 0
    for row in bridge:
        status = (_plain(row.get("properties", {}).get("Estado")) or "").strip()
        if status != "Resuelto":
            bridge_live += 1

    return {
        "tasks_total": len(tasks),
        "tasks_unlinked": tasks_unlinked,
        "deliverables_pending": deliverables_pending,
        "deliverables_adjustments": deliverables_adjustments,
        "bridge_live": bridge_live,
    }


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
                "source": t.get("source", ""),
                "project_name": t.get("project_name", "") or (t.get("input", {}) or {}).get("project_name", ""),
                "deliverable_name": t.get("deliverable_name", "") or (t.get("input", {}) or {}).get("deliverable_name", ""),
                "notion_track": bool(t.get("notion_track") or (t.get("input", {}) or {}).get("notion_track")),
            })
        return result
    except Exception:
        return []


def _is_recent_task_relevant(task: dict) -> bool:
    if task.get("project_name") or task.get("deliverable_name") or task.get("notion_track"):
        return True
    source = str(task.get("source", "")).strip().lower()
    if source in {"openclaw_gateway", "linear_webhook", "notion_poller", "smart_reply"}:
        return True
    task_name = str(task.get("task", "")).strip().lower()
    if any(task_name.startswith(prefix) for prefix in TECHNICAL_TASK_PREFIXES):
        return False
    return False


def _split_recent_tasks(tasks: list[dict], relevant_limit: int = 6, system_limit: int = 6) -> tuple[list[dict], list[dict]]:
    relevant: list[dict] = []
    system: list[dict] = []
    for task in tasks:
        if _is_recent_task_relevant(task):
            relevant.append(task)
        else:
            system.append(task)
    return relevant[:relevant_limit], system[:system_limit]


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


def _panel_activity_summary(hours: int = 24) -> list[dict[str, Any]]:
    try:
        logger = OpsLogger()
        events = logger.read_events(limit=5000, event_filter="system_activity")
    except Exception:
        return []

    cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
    buckets: dict[str, dict[str, Any]] = {}
    for event in events:
        component = str(event.get("component") or "").strip()
        if component not in {"dashboard_rick", "openclaw_panel"}:
            continue
        bucket = buckets.setdefault(
            component,
            {
                "component": component,
                "updated_24h": 0,
                "skipped_24h": 0,
                "failed_24h": 0,
                "notion_reads_24h": 0,
                "notion_writes_24h": 0,
                "worker_calls_24h": 0,
                "last_status": "",
                "last_trigger": "",
                "last_ts": "",
                "last_duration_ms": 0,
            },
        )
        ts_raw = str(event.get("ts") or "")
        ts_epoch = None
        if ts_raw:
            try:
                ts_epoch = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).timestamp()
            except ValueError:
                ts_epoch = None
        if not bucket["last_ts"] or ts_raw > bucket["last_ts"]:
            bucket["last_status"] = str(event.get("status") or "")
            bucket["last_trigger"] = str(event.get("trigger") or "")
            bucket["last_ts"] = ts_raw
            bucket["last_duration_ms"] = int(event.get("duration_ms") or 0)
        if ts_epoch is None or ts_epoch < cutoff:
            continue
        status = str(event.get("status") or "")
        if status == "updated":
            bucket["updated_24h"] += 1
        elif status == "skipped":
            bucket["skipped_24h"] += 1
        elif status == "failed":
            bucket["failed_24h"] += 1
        bucket["notion_reads_24h"] += int(event.get("notion_reads") or 0)
        bucket["notion_writes_24h"] += int(event.get("notion_writes") or 0)
        bucket["worker_calls_24h"] += int(event.get("worker_calls") or 0)

    ordered = []
    for component in ("dashboard_rick", "openclaw_panel"):
        if component in buckets:
            ordered.append(buckets[component])
    return ordered


def build_dashboard_payload() -> dict:
    """Construye el payload completo para el dashboard."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    vps_health = _worker_health(WORKER_URL)
    vm_health = _worker_health(WORKER_URL_VM) if WORKER_URL_VM else None
    vm_interactive_health = _worker_health(WORKER_URL_VM_INTERACTIVE) if WORKER_URL_VM_INTERACTIVE else None
    redis = _redis_stats()
    quotas = _quota_stats()
    teams = _team_stats()
    recent_all = _recent_tasks(12)
    recent, recent_system = _split_recent_tasks(recent_all)
    running = _running_tasks()
    ops = _ops_log_summary()
    uptime = _system_uptime()
    last_err = _last_error()
    alerts = _active_alerts(quotas, vps_health, vm_health or vm_interactive_health)
    notion_ops = _notion_ops_summary()
    panel_tracking = _panel_activity_summary()

    vm_degraded = False
    if vm_health and vm_health.get("status") != "OK":
        vm_degraded = True
    if vm_interactive_health and vm_interactive_health.get("status") != "OK":
        vm_degraded = True

    if vps_health["status"] != "OK":
        overall = "Degradado"
    elif not redis["connected"]:
        overall = "Parcial (Redis offline)"
    elif vm_degraded:
        overall = "Degradado"
    else:
        overall = "Operativo"

    return {
        "dashboard_v2": True,
        "timestamp": now,
        "overall_status": overall,
        "vps_worker": vps_health,
        "vm_worker": vm_health,
        "vm_worker_interactive": vm_interactive_health,
        "vm_recovery_mode": _vm_recovery_mode(),
        "redis": redis,
        "quotas": quotas,
        "teams": teams,
        "recent_tasks": recent,
        "recent_system_tasks": recent_system,
        "running_tasks": running,
        "ops_summary": ops,
        "uptime": uptime,
        "last_error": last_err,
        "active_alerts": alerts,
        "notion_ops": notion_ops,
        "panel_tracking": panel_tracking,
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
    p.add_argument("--trigger", default="manual", help="Trigger label for ops_log tracking")
    args = p.parse_args()

    if not WORKER_TOKEN:
        print("WORKER_TOKEN no definido.", file=sys.stderr)
        return 1

    _reset_dashboard_stats()
    started_at = time.perf_counter()
    payload = build_dashboard_payload()
    fp = _payload_fingerprint(payload)

    if not args.force:
        try:
            prev = _FINGERPRINT_PATH.read_text().strip()
            if prev == fp:
                ops_log.system_activity(
                    "dashboard_rick",
                    "refresh",
                    "skipped",
                    (time.perf_counter() - started_at) * 1000,
                    trigger=args.trigger,
                    fingerprint=fp,
                    notion_reads=_DASHBOARD_STATS["notion_reads"],
                    notion_writes=_DASHBOARD_STATS["notion_writes"],
                    worker_calls=_DASHBOARD_STATS["worker_calls"],
                    details="fingerprint_unchanged",
                )
                print(f"Sin cambios (fingerprint={fp}). Skipping Notion update.")
                return 0
        except FileNotFoundError:
            pass

    request_body = {
        "task": "notion.update_dashboard",
        "input": {"metrics": payload},
    }
    try:
        _record_dashboard_stats(worker_calls=1, notion_writes=1)
        r = httpx.post(
            f"{WORKER_URL}/run",
            json=request_body,
            headers={
                "Authorization": f"Bearer {WORKER_TOKEN}",
                "Content-Type": "application/json",
                "X-Umbral-Caller": CALLER_ID,
            },
            timeout=90,
        )
        r.raise_for_status()
        data = r.json()
        _FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _FINGERPRINT_PATH.write_text(fp)
        ops_log.system_activity(
            "dashboard_rick",
            "refresh",
            "updated",
            (time.perf_counter() - started_at) * 1000,
            trigger=args.trigger,
            fingerprint=fp,
            notion_reads=_DASHBOARD_STATS["notion_reads"],
            notion_writes=_DASHBOARD_STATS["notion_writes"],
            worker_calls=_DASHBOARD_STATS["worker_calls"],
            details=f"overall={payload.get('overall_status', '?')}",
        )
        print(f"Dashboard actualizado (fp={fp}): {data.get('result', data)}")
        return 0
    except Exception as e:
        ops_log.system_activity(
            "dashboard_rick",
            "refresh",
            "failed",
            (time.perf_counter() - started_at) * 1000,
            trigger=args.trigger,
            fingerprint=fp,
            notion_reads=_DASHBOARD_STATS["notion_reads"],
            notion_writes=_DASHBOARD_STATS["notion_writes"],
            worker_calls=_DASHBOARD_STATS["worker_calls"],
            details=str(e),
        )
        print(f"Error al actualizar dashboard: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
