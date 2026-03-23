---
id: "2026-03-23-010"
title: "Fase 4: rediseño UX/copy de OpenClaw y unificación de Dashboard Rick"
status: in_progress
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-23T13:40:00-03:00
updated_at: 2026-03-23T18:28:00-03:00
---

## Objetivo
Resolver en Fase 4 la deuda visual y editorial del panel `OpenClaw`, separándola explícitamente de Fase 1. El problema ya no es cron ni alerting, sino composición, copy, legibilidad y arquitectura de navegación.

## Contexto
- El super diagnóstico de interconectividad ya dejó confirmado que `OpenClaw` sí se refresca y que el problema residual es de UX/composición (`P1.5`).
- Fase 1 cerró supervisor + alerting Notion; no cubre diseño gráfico ni regularización de nombres del panel.
- El panel actual muestra problemas concretos vistos en vivo:
  - faltan tildes y hay copy ASCII/mixto;
  - algunas tarjetas y tablas quedan visualmente arrinconadas o con alineación pobre;
  - las definiciones del resumen requieren revisión editorial/operativa;
  - aparecen dos accesos etiquetados como `Dashboard Rick`, lo que genera ambigüedad entre dashboard técnico y página de alertas/salud.

## Criterios de aceptación
- [ ] Se redefine la jerarquía visual del resumen de `OpenClaw` con una composición más robusta y legible.
- [ ] El copy visible del panel queda en español correcto, con tildes y nombres operativos consistentes.
- [ ] Se revisan y corrigen las definiciones del resumen para que reflejen bien su uso humano vs técnico.
- [ ] Se regulariza la navegación para que no existan dos entradas ambiguas llamadas `Dashboard Rick`.
- [ ] La solución queda validada visualmente en Notion vivo, no solo en tests.

## Log
### [codex] 2026-03-23 13:40
Tarea creada como pendiente de Fase 4 por instrucción de David. Se mueve aquí la deuda visual/editorial detectada en `OpenClaw` para no contaminar Fase 1, que ya quedó cerrada como supervisor/alerting.

### [codex] 2026-03-23 18:28
Inicio de ejecución de Fase 4. Se confirma en vivo que `OpenClaw` tiene dos child pages distintas tituladas `Dashboard Rick`: la página técnica canónica (`NOTION_DASHBOARD_PAGE_ID=3265...`) y la página dedicada de alertas del Supervisor (`NOTION_SUPERVISOR_ALERT_PAGE_ID=0fd1...`). El rediseño atacará composición del resumen, copy con acentos, definiciones operativas y regularización de nombres reales en Notion.
