---
id: "2026-03-24-007"
title: "Accion 6: bootstrap y gobernanza fina por agente en OpenClaw"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R24
created_at: 2026-03-24T16:05:00-03:00
updated_at: 2026-03-24T16:55:00-03:00
---

## Objetivo
Cerrar el frente pendiente de bootstrap y gobernanza por agente en OpenClaw, distinguiendo si `BOOTSTRAP.md` debe existir de forma persistente o si su ausencia es canónica, y regularizar el archivo persistente que sí conviene mantener por workspace/rol.

## Contexto
- El diagnóstico integral `2026-03-23-018` marcó `BOOTSTRAP.md` como ausente en todos los agentes activos.
- La Acción 2 ya alineó skills y archivos base (`AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `TOOLS.md`, `USER.md`) en el runtime de la VPS.
- `openclaw status --all` sigue mostrando `Bootstrap file ABSENT` para todos los agentes.
- En runtime sí existen `HEARTBEAT.md` por workspace, pero no están versionados en el repo ni gobernados de forma canónica.

## Criterios de aceptación
- [x] Queda decisión explícita y justificada sobre `BOOTSTRAP.md` para workspaces maduros.
- [x] Queda regularizado el archivo persistente de gobernanza por agente/workspace (`HEARTBEAT.md` u otro equivalente).
- [x] El repo incorpora la convención canónica y el runbook para sincronizarla.
- [x] La VPS queda alineada con esa convención y validada con `openclaw status --all` / smokes mínimos.

## Log
### [codex] 2026-03-24 16:05
Tarea creada. Se releen protocolo y board, se contrasta el runtime actual de OpenClaw en la VPS contra los templates del repo y se prepara un cierre que no reintroduzca ruido permanente en el system prompt.

### [codex] 2026-03-24 16:55
Accion 6 cerrada.

Decision final:

- `BOOTSTRAP.md` queda versionado en el repo como asset de onboarding / rebuild, pero no se persiste en workspaces maduros.
- `HEARTBEAT.md` pasa a ser la capa persistente y breve de gobernanza por rol.

Cambio repo-side:

- alta de `openclaw/workspace-templates/BOOTSTRAP.md`
- alta de `openclaw/workspace-templates/HEARTBEAT.md`
- overrides por agente en `openclaw/workspace-agent-overrides/<agentId>/HEARTBEAT.md`
- nuevo script `scripts/sync_openclaw_workspace_governance.py`
- runbook actualizado en `docs/03-setup-vps-openclaw.md`
- artefacto de cierre: `docs/audits/openclaw-bootstrap-governance-2026-03-24.md`

VPS:

- `HEARTBEAT.md` sincronizado al workspace compartido y workspaces activos
- backups en `~/.openclaw/.sync-backups/governance-20260324T062609Z`
- `agents.defaults.skipBootstrap = true` fijado en `~/.openclaw/openclaw.json`
- `BOOTSTRAP.md` removido otra vez de los workspaces activos
- reinicio de `openclaw-gateway.service`

Validacion viva:

- `python3 scripts/sync_openclaw_workspace_governance.py --dry-run`
- `python3 scripts/sync_openclaw_workspace_governance.py --execute`
- `openclaw status --all` -> `6 total · 0 bootstrapping`
- `openclaw agent --agent main ...` -> `OK-ACCION-6-MAIN`
- `openclaw agent --agent rick-ops ...` -> `OK-ACCION-6-RICK-OPS`
- `openclaw agent --agent rick-tracker ...` -> `OK-ACCION-6-RICK-TRACKER`
