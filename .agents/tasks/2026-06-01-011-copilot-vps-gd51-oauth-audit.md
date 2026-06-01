---
id: 2026-06-01-011-copilot-vps-gd51-oauth-audit
title: "G-D5.1 — VPS read-only Google OAuth audit (Gmail + Calendar)"
status: assigned
assigned_to: copilot-vps
created_by: cursor
created: 2026-06-01
gates:
  - David approved option b (2026-06-01 chat)
  - Discovery D51_OAUTH_DISCOVERY_OK (task 010)
---

# G-D5.1 — OAuth audit VPS (read-only)

## Objetivo

Confirmar qué credenciales Google usa **runtime VPS** y si Gmail/Calendar responden vía Worker — **sin** imprimir tokens, **sin** re-OAuth, **sin** editar `openclaw.json`.

## Preflight repo

```bash
cd ~/umbral-agent-stack
git pull --ff-only origin main
git log -1 --oneline
test -f .agents/tasks/2026-06-01-011-copilot-vps-gd51-oauth-audit.md && echo TASK_FILE_OK
```

## Fuentes

- `notion-governance/docs/architecture/16-multichannel-rick-channels.md` (ADR-16, G1–G5)
- Task 010 Log (drift scope ADR vs docs/35)
- VPS env: `~/.config/openclaw/env` (names only in report)

## Pasos (read-only)

1. Evidencia: `~/.coord-ag-evidence/G-D5.1/`
2. Listar **nombres** de vars `GOOGLE_*` presentes/ausentes en `~/.config/openclaw/env` (redact values → `[REDACTED]` or `SET`/`UNSET`)
3. Worker health `:8088/health`
4. Si vars presentes: smoke mínimo vía Worker API o handler documentado:
   - Gmail: list drafts o equivalente read-only (ADR G2)
   - Calendar: list events read-only
5. Documentar scope drift vs ADR-16 (qualitative: "token likely issued with scope X" only if inferable without printing secrets)
6. Tabla final: canal | VPS vars | smoke | blocker | next gate

## Boundaries

- NO `echo $GOOGLE_*` en output
- NO OAuth browser flow
- NO gateway restart
- NO merge PRs

## Criterios

- [ ] Tabla canal × VPS state
- [ ] Smoke result PASS/FAIL/BLOCKED per channel
- [ ] Recomendación G-D5.2 (re-OAuth con scopes ADR) si aplica
- [ ] VEREDICTO in Log

## Log

### 2026-06-01 — Cursor

Task creada post-aprobación David (opción b).

## VEREDICTO

_Pendiente → **G_D51_VPS_AUDIT_OK**_
