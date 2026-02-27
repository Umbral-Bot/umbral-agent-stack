#!/usr/bin/env python3
"""
Reporta estado del proyecto al Dashboard de Notion (doc 22).

Ejecutar en la VPS (cron cada 15–30 min). Requiere:
  - Worker local en 8088 con NOTION_DASHBOARD_PAGE_ID y NOTION_* configurados.
  - REDIS_URL, WORKER_URL (default http://127.0.0.1:8088), WORKER_TOKEN.
  - Opcional: WORKER_URL_VM para comprobar estado de la VM.

Uso:
  cd ~/umbral-agent-stack && source .venv/bin/activate && PYTHONPATH=. python scripts/dashboard_report_vps.py
"""

import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import httpx

WORKER_URL = os.environ.get("WORKER_URL", "http://127.0.0.1:8088").rstrip("/")
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
WORKER_URL_VM = os.environ.get("WORKER_URL_VM", "").strip() or None


def _worker_health(url: str) -> str:
    try:
        r = httpx.get(f"{url}/health", timeout=5)
        if r.status_code == 200:
            return "OK"
        return f"Error {r.status_code}"
    except Exception as e:
        return f"No disponible ({type(e).__name__})"


def _redis_pending() -> str:
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=True)
        n = r.llen("umbral:tasks:pending")
        return str(n) if n is not None else "—"
    except Exception:
        return "—"


def _sprint_summary() -> str:
    readme = repo_root / "README.md"
    if not readme.exists():
        return "—"
    text = readme.read_text(encoding="utf-8", errors="replace")
    done = text.count("✅ Hecho")
    pending = max(0, text.count("📋") + (1 if "En progreso" in text else 0))
    return f"{done} hechos, resto pendientes (ver README)"


def main() -> int:
    if not WORKER_TOKEN:
        print("WORKER_TOKEN no definido.", file=sys.stderr)
        return 1

    metrics = {
        "Estado general": "Operativo" if WORKER_URL else "—",
        "Worker VPS": _worker_health(WORKER_URL),
        "Cola (Redis) pendientes": _redis_pending(),
        "Resumen sprints": _sprint_summary(),
    }
    if WORKER_URL_VM:
        metrics["Worker VM"] = _worker_health(WORKER_URL_VM)

    payload = {
        "task": "notion.update_dashboard",
        "input": {"metrics": metrics},
    }
    try:
        r = httpx.post(
            f"{WORKER_URL}/run",
            json=payload,
            headers={"Authorization": f"Bearer {WORKER_TOKEN}", "Content-Type": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        print("Dashboard actualizado:", data.get("result", data))
        return 0
    except Exception as e:
        print(f"Error al actualizar dashboard: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
