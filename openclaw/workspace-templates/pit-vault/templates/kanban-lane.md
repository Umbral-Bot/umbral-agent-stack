---
kanban-plugin: board
pit_id: "{{pit_id}}"
lane_id: "{{lane_id}}"
---

<!--
Plantilla kanban por lane PIT — 9 columnas canónicas (no renombrar ni reordenar:
el parser de estado del torneo asume estos títulos exactos).
Protocolo: docs/ops/pit-kanban-kpi-protocol.md
Una tarjeta = una unidad de trabajo de la iteración activa. Formato sugerido:
- [ ] iter-<n> · <título corto> #iter<n>
-->

## Backlog

- [ ] iter-1 · Formular preguntas de research (perfil: {{research_profile}})

## Research

## Hypothesis

<!-- Hipótesis = variable clave correlacionada a un KPI del spec.
Tarjeta mínima: variable + kpi_id + dirección esperada. -->

## Prototype

<!-- Gate visual Magnific 4:3: recién en esta columna (o con hipótesis validada)
se puede pedir generación visual vía Rick broker. docs/ops/pit-visual-magnific.md -->

## KPI Track

<!-- Medición contra kpi_expected del spec. Personas sintéticas: señales
SIEMPRE etiquetadas [synthetic]. -->

## Fulfillment

<!-- Calcular fulfillment_score 0-1 (fórmula en pit-kanban-kpi-protocol.md)
y escribir kpi_pack.json de la iteración antes de mover a Review. -->

## Review

<!-- Revisión del lane-agent + supervisor: ¿la hipótesis se confirma?
¿Siguiente iteración o cierre? -->

## Done

## Stuck

<!-- Bloqueos que requieren a Rick o a David. Una tarjeta en Stuck > 1 iteración
escala automáticamente al outcome report. -->
