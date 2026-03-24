---
id: "2026-03-23-019"
title: "Accion 1: regularizar topologia OpenClaw en VPS y dejar un solo gateway canonico"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-23T21:39:21-03:00
updated_at: 2026-03-24T00:52:00-03:00
---

## Objetivo
Regularizar la topologia de OpenClaw en la VPS para dejar un solo gateway systemd activo y canonico, eliminando el drift detectado en el diagnostico integral de OpenClaw. Debe quedar verificado que el dashboard, el CLI y las ejecuciones de agentes siguen funcionando tras el cambio.

## Contexto
- El diagnostico integral `2026-03-23-018` detecto dos unidades activas:
  - `openclaw-gateway.service` (gateway real)
  - `openclaw.service` (gateway duplicado que entra en loop `already running under systemd`)
- `openclaw-gateway.service` esta enabled y es el servicio que realmente atiende en `127.0.0.1:18789`.
- `openclaw.service` esta disabled pero sigue activo y genera ruido operativo.
- El usuario tambien pide dejar anotada una nueva accion futura para revisar skills faltantes o nuevas skills necesarias.

## Criterios de aceptacion
- [x] Solo queda un gateway systemd activo/canonico en la VPS.
- [x] `openclaw status --all`, `openclaw dashboard` y una ejecucion minima de agente siguen funcionando.
- [x] Se documenta el cambio y se deja trazabilidad en board/task.
- [x] Queda agregada la accion 8 en el plan/pedientes para revisar skills faltantes o nuevas.

## Log
### [codex] 2026-03-23 21:39
Tarea creada y marcada `in_progress`. Inicio de regularizacion de topologia OpenClaw en VPS tras el diagnostico integral.

### [codex] 2026-03-24 00:52
Accion 1 cerrada.

Cambios repo-side:
- `scripts/vps/openclaw-systemd-setup.sh` ahora instala y habilita `openclaw-gateway.service` como unidad canonica y deshabilita/archiva `openclaw.service` como legacy.
- `openclaw/systemd/openclaw-gateway.service.template` agregado como plantilla canonica.
- `docs/03-setup-vps-openclaw.md` y `openclaw/config/notes.md` alineados al nombre canonico del servicio.
- `openclaw/systemd/openclaw.service.template` marcado explicitamente como wrapper legacy.

Cambios operativos en VPS:
- `openclaw.service` eliminado de las units activas; ya no existe como unidad cargada.
- Residuo `openclaw.service.disabled-` renombrado a `openclaw.service.legacy-disabled`.
- Quedaron activos solo:
  - `openclaw-gateway.service`
  - `openclaw-dispatcher.service`
  - `umbral-worker.service`

Validacion real en VPS:
- `systemctl --user is-enabled openclaw-gateway.service` -> `enabled`
- `systemctl --user is-active openclaw-gateway.service` -> `active`
- `systemctl --user status openclaw.service` -> `Unit openclaw.service could not be found.`
- `openclaw status --all` -> gateway `reachable`
- `openclaw dashboard` -> URL/token del dashboard OK
- `openclaw agent --agent main --message 'Responde exactamente OK-ACTION-1.'` -> `OK-ACTION-1`

Seguimiento:
- Se creo la tarea futura `2026-03-24-002` para la Accion 8 de skills faltantes/sync vs skill nueva.
