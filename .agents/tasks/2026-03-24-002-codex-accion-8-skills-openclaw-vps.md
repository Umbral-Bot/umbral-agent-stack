---
id: "2026-03-24-002"
title: "Accion 8: revisar skills faltantes en OpenClaw VPS y decidir sync vs skill nueva"
status: pending
assigned_to: codex
created_by: codex
priority: medium
sprint: R24
created_at: 2026-03-24T00:52:00-03:00
updated_at: 2026-03-24T00:52:00-03:00
---

## Objetivo
Revisar que skills faltan realmente en el runtime OpenClaw de la VPS, cuales conviene sincronizar desde nuestras skills actuales del repo y cuales ameritan skill nueva en lugar de sync directo.

## Contexto
- El diagnostico integral `2026-03-23-018` detecto drift de workspace en la VPS.
- Fase 5 ya dejo skills nuevas y endurecio varias skills operativas en el repo.
- Antes de crear mas skills conviene separar:
  - skills faltantes por falta de sincronizacion del workspace
  - skills existentes pero mal cableadas o no cargadas
  - huecos reales que si requieren skill nueva

## Criterios de aceptacion
- [ ] Queda inventario de skills faltantes en la VPS respecto del repo.
- [ ] Queda clasificacion `sync existente` vs `crear skill nueva`.
- [ ] Se documenta impacto operativo por agente/canal/runtime.
- [ ] Se deja propuesta priorizada y trazable.

## Log
### [codex] 2026-03-24 00:52
Tarea creada como pendiente futura tras cerrar Accion 1. Se mantiene separada para no mezclar topologia gateway con regularizacion de skills/workspace.
