---
id: "2026-03-24-009"
title: "Diferidos OpenClaw: tailscale, tracking repo-side, costo y propuesta Tavily"
status: in_progress
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-24T20:05:00-03:00
updated_at: 2026-03-24T20:05:00-03:00
---

## Objetivo
Avanzar durante la noche todo lo posible en los diferidos post-acciones de OpenClaw sin esperar intervencion humana, dejando implementado lo que sea cerrable en repo/VPS y documentado con precision lo que siga dependiendo de un gate de David.

## Contexto
- Las Acciones 1, 2, 3, 4, 5, 6 y 8 ya quedaron cerradas.
- El test general post-acciones (`2026-03-24-008`) tambien quedo cerrado y mergeado a `main`.
- Quedaron como diferidos: snapshot repo-side del tracking de paneles/OpenClaw, atribucion fina de costo/tokens por componente, decision Tavily/proveedor y revalidacion Tailscale VPS -> VM tras reinicio del host.

## Criterios de aceptacion
- [ ] Queda revalidado y documentado el estado real de reachability VPS -> VM por Tailscale.
- [ ] Queda implementado el snapshot repo-side del tracking de paneles/OpenClaw o explicado con precision el bloqueo si apareciera uno real.
- [ ] Queda evaluada la atribucion fina de costo/tokens por componente y, si es viable, implementada.
- [ ] Queda una propuesta operativa clara para Tavily/proveedor con recomendacion y proximos pasos.
- [ ] Quedan anotadas oportunidades adicionales de mejora detectadas durante esta pasada.

## Log
### [codex] 2026-03-24 20:05
Tarea creada. Se arranca por revalidacion Tailscale VPS -> VM y luego se capitaliza tracking repo-side y costo/tokens de OpenClaw sobre la base del `ops_log` y del wiring ya saneado.
