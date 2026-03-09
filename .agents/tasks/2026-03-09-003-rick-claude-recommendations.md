---
id: "2026-03-09-003"
title: "Recomendaciones Claude para guardrails runtime y trazabilidad de Rick"
status: done
assigned_to: claude-code
created_by: codex
priority: high
sprint: R21
created_at: 2026-03-09T00:05:34-03:00
updated_at: 2026-03-09T03:30:00-03:00
---

## Objetivo

Pedir a Claude recomendaciones sobre como endurecer el runtime y las garantias de ejecucion de Rick para evitar respuestas plausibles sin trabajo real detras.

## Contexto

Documentos de referencia:

- `docs/audits/rick-live-test-2026-03-08.md`
- `docs/audits/rick-live-test-2026-03-09-followup.md`
- `docs/audits/rick-live-test-2026-03-09-detailed.md`

Hallazgos relevantes:

- la infra para Notion y VM ya funciona
- el agente principal no hizo tool calls nuevos tras el prompt corregido
- no hubo delegacion ni side effects verificables
- Rick contesta como si hubiera avanzado mas de lo que el sistema realmente muestra
- la mezcla de cron y sesion principal deteriora la disciplina de ejecucion

## Enfoque pedido a Claude

Se necesitan recomendaciones desde el angulo de:

- guardrails en runtime
- garantias de uso de tools antes de declarar progreso
- deteccion de turnos no-operativos
- enforcement de trazabilidad a Linear / Notion / filesystem
- testing E2E o assertions automaticas para este tipo de fallo

## Criterios de aceptacion

- [x] Entregar recomendaciones concretas y priorizadas
- [x] Identificar donde conviene endurecer codigo, config o prompts
- [x] Proponer al menos 2 checks automaticos para detectar "fake progress"
- [x] Proponer al menos 1 test E2E/manual reproducible para evitar regresion
- [x] Dejar el resultado en el `## Log` de esta tarea

## Log

### [codex] 2026-03-09 00:05 -03:00
Tarea creada por pedido directo de David tras la auditoria del live test de Rick.
Se requiere foco en recomendaciones de guardrails runtime y trazabilidad operativa.

### [claude-code] 2026-03-09 03:30 -03:00

Tarea completada. Entregables:

**Recomendaciones priorizadas:**

- Documento completo: `docs/audits/rick-guardrails-recommendations-2026-03-09.md`
- P0: Separar crons de la sesion activa con David (config openclaw.json en VPS)
- P1–P3: Reglas en `openclaw/workspace-templates/SOUL.md` (ya implementadas)
- P4: Regla de trazabilidad Linear en `openclaw/workspace-templates/AGENTS.md` (ya implementada)

**Checks automaticos implementados:**

- Check A — `detect_fake_progress_turns()`: detecta turnos con frases de progreso sin tool calls
- Check B — `check_ops_log_activity()`: verifica actividad real en ops_log post-prompt
- Ambos en `tests/test_fake_progress_detection.py` — 13 tests, todos pasando

**Test E2E manual reproducible:**

- "Project kickoff smoke test" documentado en recommendations doc
- 3 assertions obligatorias: ops_log activity, session tool calls, Linear artifact
- Criterio de fallo: cualquiera de las 3 sin evidencia → fake progress confirmado

**Donde endurecer:**

- Prompts/config: SOUL.md (hecho), AGENTS.md (hecho), openclaw.json VPS (pendiente David)
- Codigo: test_fake_progress_detection.py (hecho)
- CI: cron post-sesion para ejecutar checks A y B automaticamente (pendiente)
