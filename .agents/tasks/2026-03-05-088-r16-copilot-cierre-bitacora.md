---
id: "2026-03-05-088"
title: "R16 — Documentar scripts Bitácora y dependencias faltantes"
status: done
assigned_to: github-copilot
created_by: david
priority: medium
sprint: R16
created_at: 2026-03-05T06:00:00-06:00
updated_at: 2026-03-05T06:20:00-06:00
---

## Objetivo
Crear documentación detallada de los scripts de enriquecimiento de la Bitácora Notion (recuperados en tarea 085) y la lista precisa de funciones faltantes en worker/ que se necesitan implementar en un PR futuro.

## Criterios de aceptación
- [x] `docs/bitacora-scripts.md` creado con: qué hace cada script, cómo ejecutarlo, env vars, y lista de 9 funciones faltantes con firma y descripción
- [x] README.md actualizado con enlace a `docs/bitacora-scripts.md` en tabla de documentación
- [x] Board actualizado con tarea 088
- [x] PR abierto desde `copilot/088-cierre-bitacora` a main (solo documentación)
- [x] No se modifica worker, dispatcher ni CI

## Log
### [github-copilot] 2026-03-05 06:20
- Creado `docs/bitacora-scripts.md`: documentación de enrich_bitacora_pages.py, add_resumen_amigable.py, 34 tests
- Documentadas 6 funciones faltantes en notion_client.py con firma exacta (extraída de PR #72)
- Documentadas 3 funciones faltantes en notion.py con firma exacta
- Orden de implementación recomendado
- README: enlace añadido en tabla de documentación
- Board: tarea 088 añadida, estado R16 actualizado
