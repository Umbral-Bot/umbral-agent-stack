#!/usr/bin/env python3
"""
Verificación rápida del stack en la VPS.

Comprueba: env vars necesarias, Worker /health, Redis, tarea Dashboard en Worker,
opcionalmente Linear vía Worker. No imprime secretos.

Importante:
- Este script valida conectividad base y handlers disponibles.
- No valida en profundidad supervisor, reconciliación del Dispatcher, crons,
  rate limiting interno ni si la página de alertas de Notion sigue activa.
- Un "OK" aquí significa "plano base operativo", no "stack completamente sano".

Ejecutar EN LA VPS (o local con .env):
  cd ~/umbral-agent-stack && source .venv/bin/activate && export $(grep -v '^#' ~/.config/openclaw/env | xargs) && PYTHONPATH=. python3 scripts/verify_stack_vps.py

O desde repo local (lee .env):
  cd C:\\GitHub\\umbral-agent-stack && python scripts/verify_stack_vps.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Cargar env: ~/.config/openclaw/env (VPS) o .env. Última aparición de cada variable gana (igual que Worker y bash source).
def _load_env() -> None:
    env_files = []
    if os.name != "nt":
        env_files.append(Path(os.environ.get("HOME", "")) / ".config/openclaw/env")
    env_files.append(repo_root / ".env")
    for p in env_files:
        if p.exists():
            raw = p.read_text(encoding="utf-8", errors="ignore").replace("\x00", "")
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'").replace("\x00", "").replace("\r", "")
                if k.startswith("export "):
                    k = k[7:].strip()
                if k:
                    os.environ[k] = v
            break

_load_env()

from scripts.notion_alert_target import resolve_alert_target

# Requeridos para dashboard + Worker
REQUIRED = [
    "WORKER_URL",
    "WORKER_TOKEN",
    "REDIS_URL",
    "NOTION_DASHBOARD_PAGE_ID",
    "NOTION_API_KEY",
    "NOTION_CONTROL_ROOM_PAGE_ID",
]
OPTIONAL = [
    "WORKER_URL_VM",
    "LINEAR_API_KEY",
    "NOTION_TASKS_DB_ID",
    "NOTION_GRANOLA_DB_ID",
    "NOTION_SUPERVISOR_ALERT_PAGE_ID",
]


def _mask(s: str | None) -> str:
    if not s:
        return "(vacío)"
    if len(s) <= 8:
        return "***"
    return s[:4] + "..." + s[-2:]


def main() -> int:
    print("=== Verificación del stack (protocolos) ===\n")

    # 1) Env vars
    print("1) Variables de entorno")
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    for k in REQUIRED:
        val = os.environ.get(k)
        status = "OK" if val else "FALTA"
        print(f"   {k}: {status}" + (f" ({_mask(val)})" if val else ""))
    for k in OPTIONAL:
        val = os.environ.get(k)
        if val:
            print(f"   {k}: OK ({_mask(val)})")
        else:
            print(f"   {k}: (opcional, no definida)")
    if missing:
        print(f"   -> Faltan: {', '.join(missing)}. Definir en ~/.config/openclaw/env (VPS) o .env (local).")
    print()

    # 2) Worker health
    print("2) Worker (health)")
    worker_url = (os.environ.get("WORKER_URL") or "").rstrip("/")
    worker_token = os.environ.get("WORKER_TOKEN") or ""
    if not worker_url or not worker_token:
        print("   SKIP (falta WORKER_URL o WORKER_TOKEN)")
    else:
        try:
            import httpx
            r = httpx.get(f"{worker_url}/health", timeout=10)
            if r.status_code == 200:
                data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                tasks = data.get("tasks_registered") or []
                has_dashboard = "notion.update_dashboard" in tasks
                has_linear = "linear.list_teams" in tasks
                print(f"   OK (status 200, {len(tasks)} tareas)")
                print(f"   notion.update_dashboard: {'OK' if has_dashboard else 'NO registrada'}")
                print(f"   linear.list_teams: {'OK' if has_linear else 'NO registrada'}")
            else:
                print(f"   FAIL (status {r.status_code})")
        except Exception as e:
            print(f"   FAIL ({type(e).__name__}: {e})")
    print()

    # 3) Redis
    print("3) Redis")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
        pending = r.llen("umbral:tasks:pending")
        blocked = r.llen("umbral:tasks:blocked")
        print(f"   OK (conectado, cola: pending={pending}, blocked={blocked})")
    except Exception as e:
        print(f"   FAIL ({type(e).__name__}: {e})")
    print()

    # 4) Linear (vía Worker local; LINEAR_API_KEY en VPS; no usar WORKER_URL_VM aquí)
    print("4) Linear (vía Worker)")
    linear_worker = worker_url  # Usar Worker local (VPS) que tiene LINEAR_API_KEY
    if not linear_worker or not worker_token:
        print("   SKIP (sin Worker)")
    else:
        try:
            import httpx
            r = httpx.post(
                f"{linear_worker}/run",
                json={"task": "linear.list_teams", "input": {}},
                headers={"Authorization": f"Bearer {worker_token}", "Content-Type": "application/json"},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                result = data.get("result") or data
                if result.get("ok") and "teams" in result:
                    teams = result["teams"] or []
                    print(f"   OK ({len(teams)} equipos: {[t.get('key', t.get('name', '?')) for t in teams[:5]]}{'...' if len(teams) > 5 else ''})")
                else:
                    print(f"   FAIL (Worker respondió pero ok=False o sin teams: {result.get('error', 'unknown')})")
            else:
                print(f"   FAIL (HTTP {r.status_code})")
        except Exception as e:
            print(f"   FAIL ({type(e).__name__}: {e})")
    print()

    # 5) Notion alerting
    print("5) Notion alerting")
    alert_result = resolve_alert_target(dict(os.environ))
    checks = alert_result.get("checks", {})
    if alert_result.get("ok"):
        mode = alert_result.get("mode")
        target = _mask(alert_result.get("target_page_id"))
        if mode == "direct_supervisor":
            print(f"   OK (Supervisor -> dedicated alert page {target})")
        elif mode == "worker_alert_page":
            print(f"   WARN (Supervisor integration unavailable; Worker -> dedicated alert page {target})")
        else:
            print(f"   WARN (Dedicated alert page invalid; Worker -> Control Room {target})")
    else:
        print("   FAIL (no active Notion target available for supervisor alerts)")

    alert_supervisor = checks.get("alert_supervisor", {})
    control_worker = checks.get("control_worker", {})
    print(
        "   dedicated page via Supervisor: "
        f"{alert_supervisor.get('reason', 'unknown')}"
        + (
            f" (archived={alert_supervisor.get('archived')}, in_trash={alert_supervisor.get('in_trash')})"
            if "archived" in alert_supervisor
            else ""
        )
    )
    print(
        "   Control Room via Worker: "
        f"{control_worker.get('reason', 'unknown')}"
        + (
            f" (archived={control_worker.get('archived')}, in_trash={control_worker.get('in_trash')})"
            if "archived" in control_worker
            else ""
        )
    )
    print()

    # 6) Dashboard / Control Room (solo indicar cómo probar)
    print("6) Dashboard / Control Room")
    if missing:
        print("   SKIP (faltan variables de entorno)")
    else:
        print("   Env listado arriba. Para probar actualización real del Dashboard Rick:")
        print("   cd ~/umbral-agent-stack && source .venv/bin/activate && export $(grep -v '^#' ~/.config/openclaw/env | xargs) && PYTHONPATH=. python3 scripts/dashboard_report_vps.py")
        print("   Cron (cada 15 min): scripts/vps/install-cron.sh o crontab con dashboard-cron.sh")
    print()

    # 7) Alcance del chequeo
    print("7) Alcance del chequeo")
    print("   Verifica Worker, Redis y Linear mínimos.")
    print("   Incluye una validación operativa del target de alertas Notion.")
    print("   No reemplaza revisar supervisor, dispatcher-service.sh, logs /tmp/*.log")
    print("   ni probar manualmente un auto-restart real si quieres certidumbre completa.")
    print()

    # Resumen
    if missing:
        print(">>> Resumen: completar variables en ~/.config/openclaw/env (VPS) o .env (local) y volver a ejecutar.")
        return 1
    if not alert_result.get("ok"):
        print(">>> Resumen: plano base parcial. Worker/Redis/Linear OK, pero el canal de alertas Notion no tiene un destino activo.")
        return 1
    if alert_result.get("mode") != "direct_supervisor":
        print(">>> Resumen: plano base verificado con alerting degradado. Hay fallback efectivo vía Worker, pero la ruta dedicada del Supervisor requiere corrección.")
        return 0
    print(">>> Resumen: plano base verificado. Worker, Redis, Linear y alerting Notion dedicados están sanos; aún falta validar supervisor/Dispatcher/Dashboard en vivo si buscas certidumbre completa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
