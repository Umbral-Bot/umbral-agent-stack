#!/usr/bin/env python3
"""
Verificación del stack en la VPS (antes de configurar n8n u otros cambios).

Comprueba: env vars necesarias, Worker /health, Redis, tarea Dashboard en Worker,
opcionalmente Linear vía Worker. No imprime secretos.

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

# Requeridos para dashboard + Worker
REQUIRED = [
    "WORKER_URL",
    "WORKER_TOKEN",
    "REDIS_URL",
    "NOTION_DASHBOARD_PAGE_ID",
    "NOTION_API_KEY",
    "NOTION_CONTROL_ROOM_PAGE_ID",
]
OPTIONAL = ["WORKER_URL_VM", "LINEAR_API_KEY", "NOTION_TASKS_DB_ID", "NOTION_GRANOLA_DB_ID"]


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

    # 5) Dashboard (solo indicar cómo probar)
    print("5) Dashboard Notion")
    if missing:
        print("   SKIP (faltan variables de entorno)")
    else:
        print("   Env listado arriba. Para probar actualización real del Dashboard Rick:")
        print("   cd ~/umbral-agent-stack && source .venv/bin/activate && export $(grep -v '^#' ~/.config/openclaw/env | xargs) && PYTHONPATH=. python3 scripts/dashboard_report_vps.py")
        print("   Cron (cada 15 min): scripts/vps/install-cron.sh o crontab con dashboard-cron.sh")
    print()

    # Resumen
    if missing:
        print(">>> Resumen: completar variables en ~/.config/openclaw/env (VPS) o .env (local) y volver a ejecutar.")
        return 1
    print(">>> Resumen: env listado. Si Worker, Redis y Linear OK, el stack está listo. Probar dashboard con el comando de la sección 5.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
