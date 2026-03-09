---
id: "2026-03-09-002"
title: "Recomendaciones Cursor para orquestacion y politica de ejecucion de Rick"
status: assigned
assigned_to: cursor
created_by: codex
priority: high
sprint: R21
created_at: 2026-03-09T00:05:34-03:00
updated_at: 2026-03-09T00:05:34-03:00
---

## Objetivo

Pedir a Cursor recomendaciones como lead sobre como enfrentar el problema de ejecucion observado en Rick durante el live test del proyecto `Proyecto-Embudo-Ventas`.

## Contexto

Documentos de referencia:

- `docs/audits/rick-live-test-2026-03-08.md`
- `docs/audits/rick-live-test-2026-03-09-followup.md`
- `docs/audits/rick-live-test-2026-03-09-detailed.md`

Problemas observados:

- Rick comprende el proyecto, pero no dispara trabajo nuevo
- Rick reutiliza validaciones previas y las reporta como avance actual
- no hay trazabilidad real en Linear, Notion ni filesystem
- cron contamina la misma sesion de trabajo
- no hay regla fuerte que obligue una primera accion trazable por proyecto

## Enfoque pedido a Cursor

Se necesitan recomendaciones desde el angulo de:

- arquitectura de sesiones
- separacion entre trabajo interactivo y mensajes de cron
- politica de ejecucion minima por proyecto
- uso de Linear como contexto operativo oficial
- delegacion y control de subagentes
- metricas para saber si Rick esta realmente avanzando

## Criterios de aceptacion

- [ ] Entregar recomendaciones priorizadas a nivel de sistema y de workflow
- [ ] Proponer como separar cron vs trabajo directo con David
- [ ] Proponer como exigir side effects verificables por proyecto
- [ ] Definir 3-5 metricas o checks para medir si Rick avanza de verdad
- [ ] Dejar el resultado en el `## Log` de esta tarea

## Log

### [codex] 2026-03-09 00:05 -03:00
Tarea creada por pedido directo de David tras la auditoria del live test de Rick.
Se requiere foco en recomendaciones de orquestacion y politica de ejecucion.

