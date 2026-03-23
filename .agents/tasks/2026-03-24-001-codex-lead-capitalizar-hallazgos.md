---
id: "2026-03-24-001"
title: "Lead temporal Codex — capitalizar hallazgos, cerrar ramas codex/*, coordinar Claude si aplica"
status: done
assigned_to: codex
created_by: cursor
priority: high
sprint: R23
created_at: 2026-03-24T00:00:00-03:00
updated_at: 2026-03-23T00:58:36-03:00
---

## Objetivo

Con **PR #129** ya mergeado a `main` (907a05a), cerrar el ciclo de **capitalización** de lo encontrado en diagnósticos y trabajo Codex previo: ramas locales/remotas `codex/*` obsoletas, PRs abiertos, y follow-ups accionables en `docs/audits/agent-stack-followups-2026-03-22.md` (sin re-auditar todo el stack).

**Codex tiene el mando de coordinación** (ver `.agents/PROTOCOL.md` — delegación R23). Puede crear subtareas y **asignar a `claude`** si hace falta trabajo mejor hecho en Claude Code (instrucciones completas en el archivo de tarea; David reenvía a Claude).

---

## Criterios de aceptación

- [x] `git branch -a` / GitHub: inventario de ramas `codex/*` — cuáles se borran tras merge o están ya merged; nada útil perdido (changelog o nota en Log).
- [x] PRs abiertos de Codex revisados: mergeados, cerrados, o explícitamente dejados con motivo.
- [x] Al menos una pasada sobre `agent-stack-followups-2026-03-22.md`: próximo slice priorizado (issue Linear o tarea hija) o “no ahora” con justificación breve.
- [x] `board.md` actualizado al cierre de esta ronda de capitalización.
- [x] Log abajo con resumen para David.

## Log

### cursor 2026-03-24
Tarea creada; PROTOCOL.md actualizado con delegación temporal del lead a Codex (R23).

### codex 2026-03-23 00:58 -03:00
Capitalización cerrada desde `main` actualizado (`git pull origin main` -> `2b301e1`).

Inventario final de ramas `codex/*`:

- **Locales borradas por merge o patch-equivalent/superseded:**
  `codex/fix-hallazgos-super-diagnostico`, `codex/super-diagnostico-sistema`,
  `codex/merge-google-auth-rick-vps`, `codex/calendar-gmail-vps-seguimiento`
- **Remotas borradas por ya estar mergeadas en `main`:**
  `codex/081-capitalizar-ramas`, `codex/084-recuperar-rate-limiter`,
  `codex/098-auditoria-notion-keys`, `codex/editorial-loop-tools`,
  `codex/rick-editorial-notion-hardening`,
  `codex/umb-129-unificar-dispatcher`,
  `codex/umb-130-worker-vm-resync`,
  `codex/umb-131-curar-tareas-granola-fix`,
  `codex/vertex-openclaw-audio-hardening`
- **Sin contenido útil perdido pendiente de capitalizar:** no quedó ninguna
  `codex/*` remota viva; en local solo queda la rama de esta tarea.

PRs Codex abiertos revisados:

- `#128` (`codex/calendar-gmail-vps-seguimiento`) cerrado como **superseded**
  y rama remota borrada. Motivo: el trabajo ya quedó capitalizado en `main`
  vía `47b1733`.
- No quedan PRs abiertos con `headRefName` `codex/*`.

Pasada sobre `docs/audits/agent-stack-followups-2026-03-22.md`:

- **No abrir nuevo slice ahora.** Los cuatro follow-ups del documento ya
  quedaron capitalizados y cerrados en Linear como `UMB-129`, `UMB-130`,
  `UMB-131` y `UMB-132`, todos en estado `Done` con PRs mergeados
  (`#122`, `#123`, `#124`, `#121`).
- Lo pendiente real ya no es otro slice de repo sino verificación/deploy
  operativo en runtime (VPS/VM) si reaparece drift, especialmente para el
  caso del dispatcher vivo en VPS.

No hizo falta delegar subtareas a Claude en esta ronda.

Archivos tocados en este cierre:

- `.agents/tasks/2026-03-24-001-codex-lead-capitalizar-hallazgos.md`
- `.agents/board.md`

Validación:

- `git fetch --prune origin`
- inventario `git branch --list "codex/*"` y `git branch -r --list "origin/codex/*"`
- `gh pr list --state all ...` filtrando `headRefName` `codex/*`
- `Linear get_issue` para `UMB-129`..`UMB-132`

Resumen para David: capitalización R23 cerrada, sin ramas `codex/*` remotas
pendientes y sin PRs Codex abiertos. Lead devuelto a Cursor.
