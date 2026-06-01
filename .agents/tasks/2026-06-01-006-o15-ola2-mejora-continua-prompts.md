---
id: 2026-06-01-006-o15-ola2-mejora-continua-prompts
title: "O15 Ola 2 — Mejora Continua prompts + sync IDENTITY/ROLE"
status: in_progress
assigned_to: cursor
created: 2026-06-01
gates:
  - repo-side prompts canonical (main + orchestrator IDENTITY)
  - VPS sync post-push
---

# O15 Ola 2 — Mejora Continua (prompts)

## Goal

Segunda capa del modelo Rick CEO: formalizar gerencia Mejora Continua en repo y propagar a VPS vía `sync_openclaw_workspace_governance.py`.

## Entregables repo

- [x] `openclaw/workspace-agent-overrides/main/IDENTITY.md` (O15.1 + excepción torneo)
- [x] `openclaw/workspace-agent-overrides/rick-orchestrator/IDENTITY.md`
- [x] `openclaw/workspace-agent-overrides/rick-qa/ROLE.md` — bloque gerencia
- [x] `openclaw/workspace-agent-overrides/rick-tracker/ROLE.md` — charter operativo
- [x] `docs/ops/o15-ola2-mejora-continua-charter.md`
- [x] `scripts/sync_openclaw_workspace_governance.py` — sync `IDENTITY.md` / `ROLE.md` (override-only)

## VPS (post-push)

```bash
cd ~/umbral-agent-stack && git pull --ff-only origin main
python3 scripts/sync_openclaw_workspace_governance.py --dry-run
python3 scripts/sync_openclaw_workspace_governance.py --execute
```

Verificar presencia de bloques O15 en:
- `~/.openclaw/workspace/IDENTITY.md`
- `~/.openclaw/workspaces/rick-orchestrator/IDENTITY.md`
- `~/.openclaw/workspaces/rick-qa/ROLE.md`
- `~/.openclaw/workspaces/rick-tracker/ROLE.md`

## Log

### 2026-06-01 — Cursor

Repo-side prompts + charter + sync script extendido. Pendiente: pull + execute en VPS.

## VEREDICTO

_Pendiente VPS sync → **O15_OLA2_REPO_OK**_
