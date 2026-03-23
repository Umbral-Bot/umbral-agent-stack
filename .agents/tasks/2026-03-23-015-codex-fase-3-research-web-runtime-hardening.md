---
id: "2026-03-23-015"
title: "Fase 3: hardening runtime real de research.web"
status: in_progress
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-23T17:56:57-03:00
updated_at: 2026-03-23T17:56:57-03:00
---

## Objetivo
Endurecer `research.web` para que falle con clasificación útil en runtime real, no con `500` genérico, y dejar una validación operativa reproducible contra la VPS.

## Contexto
- El super diagnóstico de interconectividad dejó `research.web` como slice pendiente de Fase 3.
- En la VPS, el fallo real ya no era "falta env", sino un error de cuota/plan en Tavily.
- El handler actual envuelve todo como `RuntimeError`, y el Worker lo traduce a `500 Task failed: ...`.

## Criterios de aceptación
- [ ] `research.web` clasifica al menos configuración, auth, cuota, timeout/red y upstream HTTP.
- [ ] El Worker responde con status útil y cuerpo estructurado para errores tipados de tareas.
- [ ] Existe un smoke directo y corto para `research.web`.
- [ ] Hay tests suficientes para los casos nuevos.
- [ ] La VPS queda validada con evidencia real.

## Log
### [codex] 2026-03-23 17:56
Inicio de Fase 3. Reproducción real previa en VPS: `research.web` respondió `500` con detalle de Tavily `432` por límite de plan. Se implementa hardening para clasificar y exponer ese fallo como error operativo útil.
