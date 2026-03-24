---
id: "2026-03-24-003"
title: "Accion 2: sincronizar workspace compartido OpenClaw VPS con el repo"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-24T01:05:00-03:00
updated_at: 2026-03-24T01:20:00-03:00
---

## Objetivo
Sincronizar el workspace compartido `~/.openclaw/workspace` en la VPS con lo que ya quedo mergeado en `openclaw/workspace-templates/` del repo, capitalizando de verdad la Fase 5 sin pisar configuracion operativa local que no corresponda.

## Contexto
- El diagnostico integral `2026-03-23-018` detecto drift de workspace en la VPS.
- El inventario actual muestra que faltan en la VPS skills nuevas o endurecidas del repo, mientras sobreviven skills locales extras como `umbral-worker`.
- Esta accion debe centrarse en sincronizar lo que realmente corresponde al workspace compartido de Rick, no en volcar todas las skills del repo a la VPS.
- Tambien hay que dejar anotado en alguna parte que la VM quedo con Tailscale e internet operativos tras los cambios de red recientes.

## Criterios de aceptacion
- [x] `~/.openclaw/workspace/AGENTS.md` queda alineado con el repo.
- [x] Las skills compartidas que vienen de Fase 5 quedan sincronizadas en la VPS.
- [x] `main`, `rick-ops` y `rick-tracker` siguen funcionando y pueden ver el workspace actualizado.
- [x] Se deja trazabilidad del estado bueno de Tailscale + internet de la VM tras la correccion de red.
- [x] Queda documentado que sigue pendiente y que se difiere a Accion 8.

## Log
### [codex] 2026-03-24 01:05
Tarea creada y marcada `in_progress`. Inicio de sincronizacion quirurgica del workspace compartido de OpenClaw en la VPS contra `openclaw/workspace-templates/` del repo.

### [codex] 2026-03-24 01:20
Accion 2 cerrada.

Sincronizacion aplicada en la VPS:

- `~/.openclaw/workspace/AGENTS.md` sincronizado desde `openclaw/workspace-templates/AGENTS.md`.
- Workspace compartido actualizado con las skills de Fase 5 y sus endurecimientos:
  - `browser-automation-vm`
  - `google-audio-generation`
  - `system-interconnectivity-diagnostics`
  - `notion-project-registry`
  - `linear`
  - `n8n`
  - `notion`
  - `google-cloud-vertex`
- Se crearon backups locales en:
  - `~/.openclaw/workspace/.sync-backups/repo-sync-20260324-005053`
  - `~/.openclaw/workspaces/rick-ops/.sync-backups/repo-sync-20260324-005619`
  - `~/.openclaw/workspaces/rick-tracker/.sync-backups/repo-sync-20260324-005619`

Sincronizacion adicional de workspaces por agente:

- `rick-ops`: `browser-automation-vm`, `notion-project-registry`, `n8n-editorial-orchestrator`, `provider-status`
- `rick-tracker`: `google-cloud-vertex`, `linear`, `notion`, `provider-status`

Validacion:

- Comparacion por hash contra el repo: todas las rutas sincronizadas quedaron `match=True`.
- `systemctl --user restart openclaw-gateway.service` -> OK
- `openclaw status --all` -> gateway `reachable`
- `main`, `rick-ops` y `rick-tracker` respondieron OK en ejecuciones vivas posteriores al sync.

Matiz importante:

- El inventario fisico de skills/workspaces ya quedo alineado con el repo en las rutas sincronizadas.
- La seleccion de skills en runtime sigue siendo dependiente del rol y del prompt; eso no se da por resuelto en esta accion y se deja explicitamente para `2026-03-24-002` (Accion 8).

Red / VM:

- Se dejo documentado el cambio de red hecho en `tarro`: se agrego una segunda NIC de Hyper-V conectada a `Default Switch`, manteniendo la NIC interna existente.
- Durante esa intervencion, la VM recupero internet (`Invoke-WebRequest https://www.google.com` -> `200`) y Tailscale quedo autenticado dentro de la VM.
- Tras el reinicio reciente del host, la reachability VPS -> `100.109.16.40` no se da por estable; queda como follow-up separado y no bloquea el cierre del sync de workspace.
