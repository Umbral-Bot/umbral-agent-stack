---
id: "2026-03-24-007"
title: "Accion 6: bootstrap y gobernanza fina por agente en OpenClaw"
status: in_progress
assigned_to: codex
created_by: codex
priority: medium
sprint: R24
created_at: 2026-03-24T16:05:00-03:00
updated_at: 2026-03-24T16:05:00-03:00
---

## Objetivo
Cerrar el frente pendiente de bootstrap y gobernanza por agente en OpenClaw, distinguiendo si `BOOTSTRAP.md` debe existir de forma persistente o si su ausencia es canónica, y regularizar el archivo persistente que sí conviene mantener por workspace/rol.

## Contexto
- El diagnóstico integral `2026-03-23-018` marcó `BOOTSTRAP.md` como ausente en todos los agentes activos.
- La Acción 2 ya alineó skills y archivos base (`AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `TOOLS.md`, `USER.md`) en el runtime de la VPS.
- `openclaw status --all` sigue mostrando `Bootstrap file ABSENT` para todos los agentes.
- En runtime sí existen `HEARTBEAT.md` por workspace, pero no están versionados en el repo ni gobernados de forma canónica.

## Criterios de aceptación
- [ ] Queda decisión explícita y justificada sobre `BOOTSTRAP.md` para workspaces maduros.
- [ ] Queda regularizado el archivo persistente de gobernanza por agente/workspace (`HEARTBEAT.md` u otro equivalente).
- [ ] El repo incorpora la convención canónica y el runbook para sincronizarla.
- [ ] La VPS queda alineada con esa convención y validada con `openclaw status --all` / smokes mínimos.

## Log
### [codex] 2026-03-24 16:05
Tarea creada. Se releen protocolo y board, se contrasta el runtime actual de OpenClaw en la VPS contra los templates del repo y se prepara un cierre que no reintroduzca ruido permanente en el system prompt.
