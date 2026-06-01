---
id: 2026-06-01-009-copilot-vps-o15-delegation-smoke
title: "O15 — delegation smoke orchestrator → rick-ops + delegations.jsonl"
status: assigned
assigned_to: copilot-vps
created_by: cursor
created: 2026-06-01
---

# O15 delegation smoke

## Objetivo

Validar cadena **rick-orchestrator → rick-ops** con traza en `~/.openclaw/trace/delegations.jsonl`. Read-only en runtime (health checks); no torneo, no openclaw.json writes.

## Preflight repo

```bash
cd ~/umbral-agent-stack
git pull --ff-only origin main
git log -1 --oneline
test -f .agents/tasks/2026-06-01-009-copilot-vps-o15-delegation-smoke.md && echo TASK_FILE_OK
```

## Pasos

1. Evidencia: `~/.coord-ag-evidence/O15-DELEG-SMOKE/`
2. Asegurar trace dir: `mkdir -p ~/.openclaw/trace`
3. Snapshot pre: `wc -l ~/.openclaw/trace/delegations.jsonl 2>/dev/null || echo 0`
4. Invocar **rick-orchestrator** (CLI o sesión) con tarea acotada:
   - "Delega a rick-ops: read-only health — gateway :18789, worker :8088, list crons activos. Devuelve tabla PASS/FAIL. Registra delegación en delegations.jsonl."
5. Verificar post: nueva línea JSON con `requested_by: agent:rick-orchestrator`, `assigned_to: agent:rick-ops`
6. Capturar output rick-ops (health 200, worker ping si aplica)
7. Si spawn falla retry-limit (histórico orchestrator→tracker): documentar y escalar en Log — no marcar OK

## Criterios

- [ ] delegations.jsonl append con task_id uuid
- [ ] rick-ops respondió con evidencia (curl health, no narrativa vacía)
- [ ] Sin writes a openclaw.json / gateway restart

## Prompt para Copilot-VPS (pegar en hilo)

Ver `docs/ops/copilot-handoff-prompts.md` § Thread B.

## Log

### 2026-06-01 — Cursor

Task creada; ejecutar en hilo VPS **separado** del D3.1 si main está en torneo.

## VEREDICTO

_Pendiente → **O15_DELEGATION_SMOKE_OK**_
