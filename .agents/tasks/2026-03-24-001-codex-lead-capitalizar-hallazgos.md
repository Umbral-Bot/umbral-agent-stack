---
id: "2026-03-24-001"
title: "Lead temporal Codex — capitalizar hallazgos, cerrar ramas codex/*, coordinar Claude si aplica"
status: in_progress
assigned_to: codex
created_by: cursor
priority: high
sprint: R23
created_at: 2026-03-24T00:00:00-03:00
updated_at: 2026-03-24T00:00:00-03:00
---

## Objetivo

Con **PR #129** ya mergeado a `main` (907a05a), cerrar el ciclo de **capitalización** de lo encontrado en diagnósticos y trabajo Codex previo: ramas locales/remotas `codex/*` obsoletas, PRs abiertos, y follow-ups accionables en `docs/audits/agent-stack-followups-2026-03-22.md` (sin re-auditar todo el stack).

**Codex tiene el mando de coordinación** (ver `.agents/PROTOCOL.md` — delegación R23). Puede crear subtareas y **asignar a `claude`** si hace falta trabajo mejor hecho en Claude Code (instrucciones completas en el archivo de tarea; David reenvía a Claude).

---

## Criterios de aceptación

- [ ] `git branch -a` / GitHub: inventario de ramas `codex/*` — cuáles se borran tras merge o están ya merged; nada útil perdido (changelog o nota en Log).
- [ ] PRs abiertos de Codex revisados: mergeados, cerrados, o explícitamente dejados con motivo.
- [ ] Al menos una pasada sobre `agent-stack-followups-2026-03-22.md`: próximo slice priorizado (issue Linear o tarea hija) o “no ahora” con justificación breve.
- [ ] `board.md` actualizado al cierre de esta ronda de capitalización.
- [ ] Log abajo con resumen para David.

## Log

### cursor 2026-03-24
Tarea creada; PROTOCOL.md actualizado con delegación temporal del lead a Codex (R23).
