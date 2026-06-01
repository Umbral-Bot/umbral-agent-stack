---
id: 2026-06-01-013-copilot-vps-d31-worktree-cleanup
title: "D3.1 — cleanup stale lane worktree (read-only inventory + remove if authorized)"
status: assigned
assigned_to: copilot-vps
created_by: cursor
created: 2026-06-01
---

# D3.1 worktree cleanup

## Objetivo

Inventariar y, **solo si David autoriza en el prompt**, remover worktree huérfano `~/umbral-agent-stack-lane-sqlite-impl` (0 commits, nunca pusheado).

## Preflight

```bash
cd ~/umbral-agent-stack && git pull --ff-only origin main
test -f .agents/tasks/2026-06-01-013-copilot-vps-d31-worktree-cleanup.md && echo TASK_FILE_OK
```

## Pasos

1. `git worktree list` — documentar
2. Verificar `umbral-agent-stack-lane-sqlite-impl`: clean, 0 commits ahead, no remote branch
3. **Sin autorización explícita de David en el mensaje:** solo reporte read-only
4. **Con autorización:** `git worktree remove` + delete branch local si aplica
5. Evidencia: `~/.coord-ag-evidence/D3.1-cleanup/`

## VEREDICTO

_Pendiente → **D31_WORKTREE_CLEANUP_OK**_
