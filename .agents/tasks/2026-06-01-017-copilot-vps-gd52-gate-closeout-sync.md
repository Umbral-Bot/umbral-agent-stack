# Task 017 — G-D5.2 gate closeout sync (Copilot-VPS)

- **assigned_to:** copilot-vps
- **status:** assigned
- **created:** 2026-06-02
- **depends_on:** 016 (G_D52_CALENDAR_E2E_OK), PR #438 merged (`1187eaa9`), Notion ADR16_LIVE_LOG_OK
- **gate:** G-D5.2 (cierre formal spine Q2)

## Objective

Cerrar el gate **G-D5.2 OAuth scopes** en runtime + repo alineado post-merge docs, sin tocar secrets ni re-OAuth.

## Preflight repo

```bash
cd ~/umbral-agent-stack && git fetch origin main && git checkout main && git pull --ff-only origin main && git log -1 --oneline
test -f .agents/tasks/2026-06-01-017-copilot-vps-gd52-gate-closeout-sync.md && echo TASK_FILE_OK
```

Esperado HEAD: commit con mensaje `Align Google OAuth docs with ADR scopes (#438)` (`1187eaa9` o posterior).

## Procedure

1. Confirmar task 016 `status: done` y evidencia `~/.coord-ag-evidence/G-D5.2/calendar-david-primary-list.json` (`ok=true`, `inner_ok=true`).
2. `bash scripts/vps/write-gd52-traceability.sh` — refrescar reporte (incluye calendar David + docs merge si script actualizado).
3. `bash scripts/vps/smoke-gd52-oauth.sh` — re-smoke PASS.
4. `curl` read-only `list_events` con `calendar_id=david.a.moreira.m@gmail.com` — reconfirmar PASS (no crear eventos).
5. Anotar en Log: HEAD repo, paths evidencia, veredictos previos O/P/N.

## Pass criteria

- [ ] `git log -1` incluye docs/35 merge (#438)
- [ ] traceability-report.md actualizado con fecha UTC reciente
- [ ] smoke + calendar David primary PASS
- [ ] NO patch `~/.config/openclaw/env`
- [ ] NO restart gateway salvo smoke FAIL nuevo

## Boundaries

- NO merge PRs
- NO print secrets
- Worktree dirty (`smoke-gd52-oauth.sh` u otros): documentar, no revertir salvo autorización David

## VEREDICTO

(pending) → **G_D52_GATE_CLOSED** or **G_D52_GATE_BLOCKED** with reason

## Log
