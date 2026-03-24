---
id: "2026-03-24-002"
title: "Accion 8: revisar skills faltantes en OpenClaw VPS y decidir sync vs skill nueva"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R24
created_at: 2026-03-24T00:52:00-03:00
updated_at: 2026-03-24T02:18:00-03:00
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
- [x] Queda inventario de skills faltantes en la VPS respecto del repo.
- [x] Queda clasificacion `sync existente` vs `crear skill nueva`.
- [x] Se documenta impacto operativo por agente/canal/runtime.
- [x] Se deja propuesta priorizada y trazable.

## Log
### [codex] 2026-03-24 00:52
Tarea creada como pendiente futura tras cerrar Accion 1. Se mantiene separada para no mezclar topologia gateway con regularizacion de skills/workspace.

### [codex] 2026-03-24 02:18
Accion 8 cerrada.

Inventario repo vs runtime:

- `main` declaraba en `AGENTS.md` el uso de `external-reference-intelligence`, pero la skill no estaba montada en `~/.openclaw/workspace/skills/`.
- `rick-qa` declaraba `system-interconnectivity-diagnostics`, pero la skill no estaba montada en `~/.openclaw/workspaces/rick-qa/skills/`.
- `main` ya tenia `browser-automation-vm` montada, pero `openclaw skills check` la degradaba por faltar `BROWSER_HEADLESS` en `~/.config/openclaw/env`.

Cambios aplicados:

- repo:
  - se agrego `BROWSER_HEADLESS=false` a `.env.example` y `openclaw/env.template`
  - se actualizo `openclaw/workspace-templates/AGENTS.md` para reflejar que `main` tambien debe poder operar `browser-automation-vm` y `windows`, y que `rick-ops` usa tambien `windows`
- VPS:
  - backup de `~/.config/openclaw/env`
  - backup de `~/.openclaw/workspace/AGENTS.md`
  - sync de `external-reference-intelligence` a `~/.openclaw/workspace/skills/`
  - sync de `windows` a `~/.openclaw/workspace/skills/`
  - sync de `system-interconnectivity-diagnostics` a `~/.openclaw/workspaces/rick-qa/skills/`
  - sync de `AGENTS.md` al workspace compartido
  - alta explicita de `BROWSER_HEADLESS=false` en `~/.config/openclaw/env`
  - reinicio de `openclaw-gateway.service`

Validacion:

- hash match contra el repo para las tres skills sincronizadas
- `openclaw status --all` -> gateway `reachable`
- `openclaw skills check` en `main` -> `Missing requirements: 0`
- `openclaw skills check` en `rick-qa` -> `Missing requirements: 0`
- `openclaw agent --agent main -m 'Responde solo OK-ACCION-8-MAIN'` -> OK
- `openclaw agent --agent rick-qa -m 'Responde solo OK-ACCION-8-RICK-QA'` -> OK

Clasificacion final:

- `sync existente`: `external-reference-intelligence` -> `main`, `windows` -> `main`, `system-interconnectivity-diagnostics` -> `rick-qa`
- `env/runtime`: `BROWSER_HEADLESS=false`
- `crear skill nueva`: no hace falta para este slice

Relacion con Accion 4:

- no quedo un pendiente de skills derivado del saneamiento de sesiones/transcripts
- ese frente sigue siendo runbook + `openclaw doctor` / `openclaw sessions cleanup`, no skill nueva

Artefacto de apoyo:

- `docs/audits/openclaw-skills-role-selection-2026-03-24.md`
