# OpenClaw - bootstrap y gobernanza por agente - 2026-03-24

## Decision canonica

Para workspaces maduros de OpenClaw en la VPS:

- `BOOTSTRAP.md` se mantiene **versionado en el repo** como asset de onboarding o rebuild.
- `BOOTSTRAP.md` **no se persiste** en los workspaces activos.
- `agents.defaults.skipBootstrap = true` queda fijado en la VPS para declarar que esos workspaces ya estan poblados y no requieren ritual de bootstrap en runtime.
- El archivo persistente de gobernanza por agente pasa a ser `HEARTBEAT.md`.

Esta decision evita dos problemas:

1. dejar `BOOTSTRAP.md` ausente sin explicacion operativa;
2. dejar `BOOTSTRAP.md` persistente, lo que hacia que `openclaw status --all` contara a todos los agentes como `bootstrapping`.

## Repo

Se agrego al repo:

- `openclaw/workspace-templates/BOOTSTRAP.md`
- `openclaw/workspace-templates/HEARTBEAT.md`
- `openclaw/workspace-agent-overrides/<agentId>/HEARTBEAT.md`
- `scripts/sync_openclaw_workspace_governance.py`

Convencion:

- `BOOTSTRAP.md`: solo para onboarding / rebuild, no para persistirlo en workspaces maduros.
- `HEARTBEAT.md`: checklist breve persistente por rol.

## VPS

Cambios aplicados en la VPS:

- `HEARTBEAT.md` sincronizado a:
  - `~/.openclaw/workspace`
  - `~/.openclaw/workspaces/rick-delivery`
  - `~/.openclaw/workspaces/rick-ops`
  - `~/.openclaw/workspaces/rick-orchestrator`
  - `~/.openclaw/workspaces/rick-qa`
  - `~/.openclaw/workspaces/rick-tracker`
- backups previos en `~/.openclaw/.sync-backups/governance-20260324T062609Z`
- `skipBootstrap = true` fijado en `~/.openclaw/openclaw.json`
- `BOOTSTRAP.md` removido otra vez de los workspaces activos
- `openclaw-gateway.service` reiniciado

## Validacion

Validaciones vivas corridas en la VPS:

- `python3 scripts/sync_openclaw_workspace_governance.py --dry-run`
- `python3 scripts/sync_openclaw_workspace_governance.py --execute`
- `systemctl --user restart openclaw-gateway`
- `/home/rick/.npm-global/bin/openclaw status --all`
- `/home/rick/.npm-global/bin/openclaw agent --agent main -m 'Responde solo OK-ACCION-6-MAIN'`
- `/home/rick/.npm-global/bin/openclaw agent --agent rick-ops -m 'Responde solo OK-ACCION-6-RICK-OPS'`
- `/home/rick/.npm-global/bin/openclaw agent --agent rick-tracker -m 'Responde solo OK-ACCION-6-RICK-TRACKER'`

Resultado:

- `Agents: 6 total · 0 bootstrapping`
- `Bootstrap file ABSENT` en todos los agentes activos, ahora como estado aceptado y coherente con `skipBootstrap=true`
- `main`, `rick-ops` y `rick-tracker` siguieron respondiendo OK

## Conclusiones

- El problema real no era "crear BOOTSTRAP por crear".
- El cierre correcto era separar:
  - bootstrap one-shot
  - gobernanza persistente
- `HEARTBEAT.md` queda como capa persistente ligera.
- `AGENTS.md` sigue siendo la capa fuerte de reglas operativas.
- `BOOTSTRAP.md` queda reservado para nuevos workspaces o reconstrucciones controladas.
