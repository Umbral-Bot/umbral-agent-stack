---
id: "2026-03-23-010"
title: "Fase 4: rediseño UX/copy de OpenClaw y unificación de Dashboard Rick"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-23T13:40:00-03:00
updated_at: 2026-03-23T19:08:00-03:00
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
- [x] Se redefine la jerarquía visual del resumen de `OpenClaw` con una composición más robusta y legible.
- [x] El copy visible del panel queda en español correcto, con tildes y nombres operativos consistentes.
- [x] Se revisan y corrigen las definiciones del resumen para que reflejen bien su uso humano vs técnico.
- [x] Se regulariza la navegación para que no existan dos entradas ambiguas llamadas `Dashboard Rick`.
- [x] La solución queda validada visualmente en Notion vivo, no solo en tests.

## Log
### [codex] 2026-03-23 13:40
Tarea creada como pendiente de Fase 4 por instrucción de David. Se mueve aquí la deuda visual/editorial detectada en `OpenClaw` para no contaminar Fase 1, que ya quedó cerrada como supervisor/alerting.

### [codex] 2026-03-23 18:28
Inicio de ejecución de Fase 4. Se confirma en vivo que `OpenClaw` tiene dos child pages distintas tituladas `Dashboard Rick`: la página técnica canónica (`NOTION_DASHBOARD_PAGE_ID=3265...`) y la página dedicada de alertas del Supervisor (`NOTION_SUPERVISOR_ALERT_PAGE_ID=0fd1...`). El rediseño atacará composición del resumen, copy con acentos, definiciones operativas y regularización de nombres reales en Notion.

### [codex] 2026-03-23 19:08
Fase 4 cerrada. Se rediseñó `OpenClaw` con `Resumen ejecutivo` + tabla `Lectura rápida`, se corrigió el copy visible con acentos y se limpió la navegación inferior a `Bases operativas y paneles`. En vivo, `OpenClaw` quedó con una sola entrada `Dashboard Rick` para el panel técnico (`3265...`) y la página de alertas quedó renombrada a `Alertas del Supervisor` (`0fd1...`). También se actualizó el copy visible de `Dashboard Rick` técnico (`Este dashboard es técnico...`, `Éxito`, `Operación Notion`, `Ruido técnico / sistema`). Validación local: `1214 passed, 4 skipped, 1 warning`. Validación Notion vivo: `scripts/openclaw_panel_vps.py` dio `validation.ok=true` y la lectura posterior por API confirmó headings, copy y navegación unificados.
