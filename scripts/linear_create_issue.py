#!/usr/bin/env python3
"""
Script para crear issues en Linear (para Rick o uso manual).

Uso básico:
  python scripts/linear_create_issue.py "Título del issue" [--team-key UMB] [--description "Descripción"]

Modo estandarizado (recomendado):
  python scripts/linear_create_issue.py "[marketing] Diseñar secuencia de outreach" \
    --team-key UMB \
    --umbral-team marketing \
    --owner-agent rick-delivery \
    --objective "Generar secuencia para primer contacto" \
    --dod "Secuencia de 5 mensajes validada" \
    --dod "Checklist QA completo" \
    --artifacts-path "proyectos/venta-servicios-embudo/runs/2026-03-06_xxx"

También puede encolarse vía Redis/Dispatcher con --enqueue.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import List

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def _build_description(
    base_description: str,
    trace_id: str,
    umbral_team: str | None,
    owner_agent: str | None,
    objective: str | None,
    dod_items: List[str],
    artifacts_path: str | None,
) -> str:
    lines: List[str] = []

    if base_description:
        lines.append(base_description.strip())
        lines.append("")

    lines.append("## Operative Metadata")
    lines.append(f"- trace_id: `{trace_id}`")
    lines.append(f"- umbral_team: `{umbral_team or 'system'}`")
    lines.append(f"- owner_agent: `{owner_agent or 'rick'}`")

    if objective:
        lines.append("")
        lines.append("## Objective")
        lines.append(objective.strip())

    if dod_items:
        lines.append("")
        lines.append("## Definition of Done")
        for item in dod_items:
            lines.append(f"- [ ] {item.strip()}")

    if artifacts_path:
        lines.append("")
        lines.append("## Artifacts")
        lines.append(f"- path: `{artifacts_path.strip()}`")

    return "\n".join(lines).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="Crear issue en Linear")
    p.add_argument("title", help="Título del issue")
    p.add_argument("--team-key", default="UMB", help="Clave del equipo Linear (default: UMB)")
    p.add_argument("--description", "-d", default="", help="Descripción opcional")
    p.add_argument("--enqueue", action="store_true", help="Encolar vía Redis en lugar de llamar API directa")

    # Campos operativos recomendados
    p.add_argument("--trace-id", default="", help="ID de trazabilidad. Si no se pasa, se autogenera")
    p.add_argument("--umbral-team", default="", help="Equipo lógico: marketing|advisory|improvement|system|lab")
    p.add_argument("--owner-agent", default="", help="Agente owner de la tarea")
    p.add_argument("--objective", default="", help="Objetivo de la tarea")
    p.add_argument("--dod", action="append", default=[], help="Item de Definition of Done (repetible)")
    p.add_argument("--artifacts-path", default="", help="Ruta de artefactos/output")

    args = p.parse_args()

    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        print("LINEAR_API_KEY no definido.", file=sys.stderr)
        return 1

    trace_id = args.trace_id.strip() or f"trace-{uuid.uuid4().hex[:12]}"
    description = _build_description(
        base_description=args.description,
        trace_id=trace_id,
        umbral_team=args.umbral_team.strip() or None,
        owner_agent=args.owner_agent.strip() or None,
        objective=args.objective.strip() or None,
        dod_items=args.dod,
        artifacts_path=args.artifacts_path.strip() or None,
    )

    payload = {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "system",
        "task_type": "general",
        "task": "linear.create_issue",
        "input": {
            "title": args.title,
            "team_key": args.team_key,
            "description": description or None,
        },
    }

    if args.enqueue:
        try:
            import redis
            from dispatcher.queue import TaskQueue

            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url, decode_responses=True)
            q = TaskQueue(r)
            
            q.enqueue(payload)
            print(json.dumps({
                "ok": True, 
                "task_id": payload["task_id"], 
                "trace_id": trace_id,
                "message": "Task encolada; Dispatcher la procesará"
            }))
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
            description=description or None,
        )
        print(json.dumps({"ok": True, "trace_id": trace_id, **issue}, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
