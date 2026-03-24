# OpenClaw - seleccion de skills por rol en VPS - 2026-03-24

## Objetivo

Cerrar la Accion 8 del diagnostico integral OpenClaw distinguiendo:

- drift real de workspace en la VPS;
- skills existentes en repo que solo faltaban sincronizar;
- gaps de env/runtime que hacian ver una skill como no elegible;
- y huecos reales que ameritarian skill nueva.

## Fuente canónica

Asignacion esperada por rol, segun [C:\GitHub\umbral-agent-stack-codex\openclaw\workspace-templates\AGENTS.md](C:\GitHub\umbral-agent-stack-codex\openclaw\workspace-templates\AGENTS.md):

| Rol | Skills esperadas |
|---|---|
| `main` | `linear-delivery-traceability`, `subagent-result-integration`, `notion-project-registry`, `system-interconnectivity-diagnostics`, `editorial-source-curation`, `competitive-funnel-benchmark`, `external-reference-intelligence`, `browser-automation-vm`, `windows` |
| `rick-orchestrator` | `subagent-result-integration`, `linear-issue-triage`, `linear-delivery-traceability`, `agent-handoff-governance`, `external-reference-intelligence` |
| `rick-qa` | `linear-project-auditor`, `linear-delivery-traceability`, `system-interconnectivity-diagnostics` |
| `rick-tracker` | `editorial-source-curation` |
| `rick-ops` | `n8n-editorial-orchestrator`, `browser-automation-vm`, `windows` |

## Hallazgos antes del fix

Comparando repo vs runtime OpenClaw en la VPS:

- `main` no tenia montadas `external-reference-intelligence` ni `windows` en `~/.openclaw/workspace/skills/`.
- `rick-qa` no tenia montada `system-interconnectivity-diagnostics` en `~/.openclaw/workspaces/rick-qa/skills/`.
- `browser-automation-vm` ya estaba montada en `main`, pero `openclaw skills check` la marcaba como no elegible porque faltaba `BROWSER_HEADLESS` en `~/.config/openclaw/env`.
- No aparecio ningun hueco que justificara skill nueva para este slice.

## Cambios aplicados

### Repo

- Se explicito `BROWSER_HEADLESS=false` en [C:\GitHub\umbral-agent-stack-codex\.env.example](C:\GitHub\umbral-agent-stack-codex\.env.example) y [C:\GitHub\umbral-agent-stack-codex\openclaw\env.template](C:\GitHub\umbral-agent-stack-codex\openclaw\env.template).
- Se actualizo [C:\GitHub\umbral-agent-stack-codex\openclaw\workspace-templates\AGENTS.md](C:\GitHub\umbral-agent-stack-codex\openclaw\workspace-templates\AGENTS.md) para reflejar que `main` debe poder operar browser/VM directamente y que `rick-ops` usa tambien `windows`.

### VPS

- Backup de `~/.config/openclaw/env`.
- Backup de `~/.openclaw/workspace/AGENTS.md`.
- Alta explicita de `BROWSER_HEADLESS=false` en `~/.config/openclaw/env`.
- Sync de `external-reference-intelligence` a `~/.openclaw/workspace/skills/`.
- Sync de `windows` a `~/.openclaw/workspace/skills/`.
- Sync de `system-interconnectivity-diagnostics` a `~/.openclaw/workspaces/rick-qa/skills/`.
- Sync de `AGENTS.md` al workspace compartido.
- Reinicio de `openclaw-gateway.service`.

## Validacion

Validaciones vivas corridas en la VPS:

- hash match de las skills sincronizadas contra el repo;
- `openclaw status --all` -> gateway reachable;
- `openclaw skills check` en `~/.openclaw/workspace` -> `Missing requirements: 0`;
- `openclaw skills check` en `~/.openclaw/workspaces/rick-qa` -> `Missing requirements: 0`;
- `/home/rick/.npm-global/bin/openclaw agent --agent main -m 'Responde solo OK-ACCION-8-MAIN'` -> `OK-ACCION-8-MAIN`;
- `/home/rick/.npm-global/bin/openclaw agent --agent rick-qa -m 'Responde solo OK-ACCION-8-RICK-QA'` -> `OK-ACCION-8-RICK-QA`.

## Clasificacion final

### Sync existente

- `external-reference-intelligence` -> `main`
- `windows` -> `main`
- `system-interconnectivity-diagnostics` -> `rick-qa`

### Env/runtime

- `BROWSER_HEADLESS=false` era el gap real que hacia ver `browser-automation-vm` como no elegible en `main`.

### Skill nueva

- No hizo falta crear ninguna skill nueva para cerrar la Accion 8.

## Relacion con la Accion 4

No quedo un pendiente de skills derivado de la Accion 4.

La limpieza de sesiones/transcripts sigue siendo:

- operacion administrativa;
- `openclaw doctor` + `openclaw sessions cleanup`;
- backup previo + runbook;

y no amerita skill nueva por ahora.

## Pendiente opcional futuro

Si David quiere que `rick-tracker` o `rick-orchestrator` absorban mas trabajo directo sobre referencias externas o VM, eso ya seria curacion adicional de rol, no cierre de drift. La Accion 8 actual queda cerrada sin deuda bloqueante.
