---
id: "2026-03-09-001"
title: "Recomendaciones Antigravity para corregir la ejecucion de Rick en proyectos reales"
status: assigned
assigned_to: antigravity
created_by: codex
priority: high
sprint: R21
created_at: 2026-03-09T00:05:34-03:00
updated_at: 2026-03-09T00:05:34-03:00
---

## Objetivo

Revisar la auditoria detallada del live test de Rick y proponer recomendaciones concretas para corregir el problema de fondo: Rick entiende el contexto, pero no pasa de declaracion a ejecucion real.

## Contexto

Documentos de referencia:

- `docs/audits/rick-live-test-2026-03-08.md`
- `docs/audits/rick-live-test-2026-03-09-followup.md`
- `docs/audits/rick-live-test-2026-03-09-detailed.md`

Hallazgos ya confirmados:

- la infra base ya funciona para Notion y VM filesystem
- el proyecto `Proyecto-Embudo-Ventas` fue aclarado y el contexto fue entendido
- Rick no ejecuto tool calls nuevos despues del prompt corregido
- Rick no toco Linear, Notion ni el filesystem del proyecto
- Rick no delego a subagentes
- cron sigue interfiriendo en la misma sesion de trabajo

## Enfoque pedido a Antigravity

Se necesitan recomendaciones desde el angulo de:

- instrucciones y skills
- flujo operativo del agente principal
- disciplina de ejecucion
- conversion de prompts de proyecto en acciones reales
- forma de usar subagentes sin perder contexto

## Criterios de aceptacion

- [ ] Entregar 5-10 recomendaciones concretas y priorizadas
- [ ] Indicar si el problema principal esta en prompt, skills, workspace, contexto o policy
- [ ] Proponer un cambio minimo y uno estructural
- [ ] Identificar al menos un experimento rapido para validar mejora
- [ ] Dejar el resultado en el `## Log` de esta tarea

## Log

### [codex] 2026-03-09 00:05 -03:00
Tarea creada por pedido directo de David tras la auditoria del live test de Rick.
Se requiere foco en recomendaciones, no implementacion inmediata.

