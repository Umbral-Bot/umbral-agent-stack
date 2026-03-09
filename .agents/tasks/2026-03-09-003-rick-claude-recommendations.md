---
id: "2026-03-09-003"
title: "Recomendaciones Claude para guardrails runtime y trazabilidad de Rick"
status: assigned
assigned_to: claude-code
created_by: codex
priority: high
sprint: R21
created_at: 2026-03-09T00:05:34-03:00
updated_at: 2026-03-09T00:05:34-03:00
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

- [ ] Entregar recomendaciones concretas y priorizadas
- [ ] Identificar donde conviene endurecer codigo, config o prompts
- [ ] Proponer al menos 2 checks automaticos para detectar "fake progress"
- [ ] Proponer al menos 1 test E2E/manual reproducible para evitar regresion
- [ ] Dejar el resultado en el `## Log` de esta tarea

## Log

### [codex] 2026-03-09 00:05 -03:00
Tarea creada por pedido directo de David tras la auditoria del live test de Rick.
Se requiere foco en recomendaciones de guardrails runtime y trazabilidad operativa.
