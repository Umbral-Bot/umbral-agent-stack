---
id: "2026-03-05-082"
title: "R16 — Capitalizar PRs cerrados: inventario de ramas"
status: done
assigned_to: github-copilot
created_by: cursor
priority: medium
sprint: R16
created_at: 2026-03-05T04:00:00-06:00
updated_at: 2026-03-05T04:30:00-06:00
---

## Objetivo
Crear inventario de los 11 PRs cerrados en la tarea 080, documentando rama, contenido y decisión de recuperar o no. Actualizar board.

## Contexto
En la tarea 080 se cerraron 11 PRs obsoletos con comentario. Algunos tienen contenido único que podría rescatarse (cherry-pick). Este inventario documenta qué hay en cada rama cerrada para decisiones futuras.

## Criterios de aceptación
- [x] Inventario en `docs/branches-cerrados-inventario.md` con tabla: PR | rama | contenido | ¿recuperar?
- [x] Board actualizado con tareas 079-082
- [x] PR abierto desde `copilot/082-capitalizar-cerrados` a main (solo docs + board)

## Log
### [github-copilot] 2026-03-05 04:30
- Leídos 11 PRs cerrados via GitHub API (número, título, rama, body, +/-, archivos)
- Creado `docs/branches-cerrados-inventario.md`: tabla de 11 PRs con rama, contenido en 1 línea, decisión recuperar
  - 7 PRs → no recuperar (duplicados/stale)
  - 3 PRs → recuperar parcial (#72 enrich_bitacora, #78 Power BI research, #81 browser automation plan)
  - Incluye instrucciones de cherry-pick
- Board actualizado: 079/080 done, 081 pendiente, 082 en curso
- PR abierto desde `copilot/082-capitalizar-cerrados` a main
