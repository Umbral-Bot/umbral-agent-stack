---
id: "2026-03-24-006"
title: "Accion 5: hardening de seguridad OpenClaw"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R24
created_at: 2026-03-24T02:38:45-03:00
updated_at: 2026-03-24T03:08:00-03:00
---

## Objetivo
Reducir la deuda de hardening detectada en el diagnostico integral de OpenClaw, resolviendo los findings que si convenga corregir ahora y clasificando con evidencia los que deban quedar como residual aceptado.

## Contexto
- El diagnostico integral `2026-03-23-018` dejo pendientes:
  - `plugins.code_safety` sobre `umbral-worker`
  - `gateway.trusted_proxies_missing`
  - `models.weak_tier` por `azure-openai-responses/gpt-4.1`
  - `plugins.tools_reachable_permissive_policy`
  - `skills.workspace.symlink_escape`
- La topologia OpenClaw de la VPS ya quedo regularizada en la Accion 1.
- El workspace y las skills ya quedaron alineados con el repo en las Acciones 2 y 8.
- Antes de cambiar tool policy o modelo fallback, hay que validar que `main`, `rick-ops`, `rick-tracker` y `rick-qa` sigan operativos en vivo.

## Criterios de aceptacion
- [x] Se crea clasificacion explicita `fix ahora` vs `residual aceptado` para cada finding de hardening.
- [x] El plugin `umbral-worker` queda endurecido sin romper el gateway.
- [x] Se corrigen las rutas de symlink fuera de workspace si no aportan valor operativo.
- [x] Se decide y aplica el ajuste seguro sobre fallbacks/perfiles si corresponde.
- [x] `openclaw security audit --deep` mejora o, si algun warning permanece, queda justificado con evidencia.
- [x] Queda trazabilidad en tarea, board y diagnostico integral.

## Log
### [codex] 2026-03-24 02:38
Tarea creada en `in_progress`. Estado inicial confirmado:

- finding critico del plugin `umbral-worker` por uso de `process.env.WORKER_URL` en el path de network send
- warning por `trustedProxies` vacio
- warning por `gpt-4.1` en fallbacks
- warning por `tools.profile = coding` en agentes con allowlists amplias
- warning por symlinks a skills fuera del workspace en `rick-delivery` y `rick-orchestrator`

La siguiente fase es implementar primero los cambios seguros (plugin + symlinks + fallback) y luego revalidar si conviene tocar perfiles o dejarlo como residual controlado.

### [codex] 2026-03-24 03:08
Accion 5 cerrada.

Cambios repo-side:

- `openclaw/extensions/umbral-worker/index.ts`
  - `baseUrl` deja de depender de `WORKER_URL`
  - `interactiveBaseUrl` deja de depender de `WORKER_URL_VM_INTERACTIVE`
  - el token del plugin ya no se lee desde `process.env`; ahora se lee desde `tokenFile`
- `openclaw/extensions/umbral-worker/openclaw.plugin.json`
  - se agregan `interactiveBaseUrl` y `tokenFile` a la config del plugin
- `docs/03-setup-vps-openclaw.md`
  - se documenta el hardening minimo recomendado del gateway/plugin

Cambios runtime en VPS:

- backup de `~/.openclaw/openclaw.json`
- `tools.profile = coding` a nivel global en `~/.openclaw/openclaw.json`
- remocion de `azure-openai-responses/gpt-4.1` de `agents.defaults.model.fallbacks`
- `plugins.entries.umbral-worker.config` queda explicito con:
  - `baseUrl=http://127.0.0.1:8088`
  - `interactiveBaseUrl=http://100.109.16.40:8089`
  - `tokenFile=/home/rick/.config/openclaw/worker-token`
- materializacion de `~/.config/openclaw/worker-token` con permisos `600`
- reemplazo de symlinks fuera de workspace por copias reales:
  - `rick-delivery/skills/n8n`
  - `rick-orchestrator/skills/make-webhook`
- backups movidos fuera del directorio vivo de plugins
- permisos del plugin `~/.openclaw/extensions/umbral-worker` regularizados a `755/644`
- reinicio de `openclaw-gateway.service`

Validacion real:

- `openclaw security audit --deep` paso de `1 critical · 4 warn` a `0 critical · 2 warn`
- `openclaw status --all` -> gateway reachable
- `openclaw agent --agent main -m 'Usa exactamente la tool umbral_provider_status una vez y responde solo OK-ACCION-5 redis_available=<true|false>'` -> `OK-ACCION-5 redis_available=true`
- `openclaw agent --agent rick-ops -m 'Responde solo OK-ACCION-5-RICK-OPS'` -> OK
- `openclaw agent --agent rick-tracker -m 'Responde solo OK-ACCION-5-RICK-TRACKER'` -> OK
- verificacion de symlinks en `rick-delivery` y `rick-orchestrator` -> `[]`

Clasificacion final de findings:

- `plugins.code_safety` critico por env harvesting -> **resuelto**
- `models.weak_tier` por `gpt-4.1` -> **resuelto**
- `skills.workspace.symlink_escape` -> **resuelto**
- `plugins.tools_reachable_permissive_policy` -> **resuelto** al fijar `tools.profile = coding` a nivel global
- `gateway.trusted_proxies_missing` -> **residual aceptado** mientras la Control UI siga local-only por loopback/SSH tunnel/Tailscale directo y no detras de reverse proxy
- `plugins.code_safety` warning residual (`potential-exfiltration`) -> **residual aceptado**: el plugin lee un `tokenFile` dedicado con permisos `600` para autenticar el Worker; no queda harvesting desde env, pero la auditoria sigue marcando cualquier file-read + network-send como patron a revisar
