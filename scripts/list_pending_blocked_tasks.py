#!/usr/bin/env python3
"""
Lista tareas pendientes y bloqueadas en Redis (umbral:tasks:pending, umbral:tasks:blocked).
Para que Rick (o un script) pueda vaciarlas a Linear como issues.

Uso en VPS (no hay python global; usar .venv; git pull si el script no existe):
  cd ~/umbral-agent-stack && git pull origin main
  source .venv/bin/activate && export $(grep -v '^#' ~/.config/openclaw/env | xargs)
  PYTHONPATH=. python scripts/list_pending_blocked_tasks.py

Salida: JSON con listas "pending" y "blocked", cada ítem con task_id, task, team, etc.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
PENDING_KEY = "umbral:tasks:pending"
BLOCKED_KEY = "umbral:tasks:blocked"
TASK_PREFIX = "umbral:task:"


def main() -> int:
    try:
        import redis
    except ImportError:
        print('{"error": "redis package required"}', file=sys.stderr)
        return 1

    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
    except Exception as e:
        print(json.dumps({"error": str(e), "pending": [], "blocked": []}))
        return 1

    def get_envelope(task_id: str) -> dict | None:
        raw = r.get(f"{TASK_PREFIX}{task_id}")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    pending_items = r.lrange(PENDING_KEY, 0, -1) or []
    blocked_items = r.lrange(BLOCKED_KEY, 0, -1) or []

    pending = []
    for raw in pending_items:
        try:
            meta = json.loads(raw)
            task_id = meta.get("task_id")
            env = get_envelope(task_id) if task_id else None
            pending.append({
                "task_id": task_id,
                "task": meta.get("task", env.get("task") if env else "?"),
                "team": meta.get("team", env.get("team") if env else "system"),
                "queued_at": meta.get("queued_at"),
                "envelope": env,
            })
        except (json.JSONDecodeError, TypeError):
            pending.append({"raw": raw, "task_id": None})

    blocked = []
    for raw in blocked_items:
        try:
            meta = json.loads(raw)
            task_id = meta.get("task_id")
            env = get_envelope(task_id) if task_id else None
            blocked.append({
                "task_id": task_id,
                "reason": meta.get("reason"),
                "blocked_at": meta.get("blocked_at"),
                "task": env.get("task") if env else "?",
                "team": env.get("team") if env else "system",
                "envelope": env,
            })
        except (json.JSONDecodeError, TypeError):
            blocked.append({"raw": raw, "task_id": None})

    out = {"pending": pending, "blocked": blocked}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
