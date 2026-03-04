#!/usr/bin/env python3
"""
Script para crear issues en Linear (para Rick o uso manual).

Uso:
  python scripts/linear_create_issue.py "Título del issue" [--team-key UMB] [--description "Descripción"]
  # O encolar vía Worker (requiere Redis, Dispatcher, Worker):
  python scripts/linear_create_issue.py "Título" --enqueue

Ejecutar en VPS con LINEAR_API_KEY en env.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def main() -> int:
    p = argparse.ArgumentParser(description="Crear issue en Linear")
    p.add_argument("title", help="Título del issue")
    p.add_argument("--team-key", default="UMB", help="Clave del equipo (default: UMB)")
    p.add_argument("--description", "-d", default="", help="Descripción opcional")
    p.add_argument("--enqueue", action="store_true", help="Encolar vía Redis en lugar de llamar API directa")
    args = p.parse_args()

    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        print("LINEAR_API_KEY no definido.", file=sys.stderr)
        return 1

    if args.enqueue:
        try:
            import uuid
            import redis
            from dispatcher.queue import TaskQueue

            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url, decode_responses=True)
            q = TaskQueue(r)
            task_id = str(uuid.uuid4())
            envelope = {
                "schema_version": "0.1",
                "task_id": task_id,
                "team": "system",
                "task_type": "general",
                "task": "linear.create_issue",
                "input": {
                    "title": args.title,
                    "team_key": args.team_key,
                    "description": args.description or None,
                },
            }
            q.enqueue(envelope)
            print(json.dumps({"ok": True, "task_id": task_id, "message": "Task encolada; Dispatcher la procesará"}))
            return 0
        except Exception as e:
            print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
            return 2

    # Llamada directa a API
    from worker.linear_client import create_issue, get_team_by_key

    team = get_team_by_key(api_key, args.team_key)
    if not team:
        print(json.dumps({"ok": False, "error": f"Team '{args.team_key}' no encontrado"}), file=sys.stderr)
        return 2

    try:
        issue = create_issue(
            api_key=api_key,
            team_id=team["id"],
            title=args.title,
            description=args.description or None,
        )
        print(json.dumps({"ok": True, **issue}, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
