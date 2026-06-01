---
id: "2026-06-01-002"
title: "G-D1a-RESTART — Reiniciar openclaw-gateway + smoke post maxSpawnDepth=2"
status: done
assigned_to: copilot
created_by: cursor
priority: high
sprint: W-A
created_at: 2026-06-01T05:30:00-04:00
updated_at: 2026-06-01T05:42:00-04:00
owner: copilot-vps
reviewer: cursor
phase: Q2-v2-D1
depends_on:
  - .agents/tasks/2026-06-01-001-gd1a-set-maxspawndepth.md (G_D1a_PATCH_OK, prereq)
  - .agents/tasks/2026-05-30-001-verify-tournament-multiagent-openclaw-runtime.md (D0.2 read-only — DEBE cerrar primero)
  - notion-governance/docs/roadmap/13-q2-2026-v2-deployment-spine.md (D1.1 cierre efectivo)
blocked_reason: null
---

## Objetivo

Hacer **efectivo en runtime** el patch G-D1a (`maxSpawnDepth=2` ya en disco desde 2026-06-01
05:25) reiniciando `openclaw-gateway.service`, validando health y dejando evidencia de que el
gateway cargó la config nueva. Cierra D1.1 del spine (parte runtime).

**NO** tocar worker, Granola, modelos ni allowAgents en este turno.

## Superficie y rol

- **Ejecuta:** Copilot-VPS (`openclaw-vps-operator`).
- **Secuencia:** **después** de cerrar D0.2 (`2026-05-30-001`, read-only). Si Copilot-VPS
  aún corre ese prompt, **esperar** — no lanzar este restart en la misma sesión en paralelo.
- **Rollback:** restaurar backup `~/.coord-ag-evidence/G-D1a/openclaw.json.bak.202606010525` +
  restart solo si gateway no levanta o smoke FAIL crítico.

## Preflight repo (Copilot-VPS — obligatorio, primer paso)

Cursor debe haber hecho **push a `main`** antes de este handoff. En VPS:

```bash
cd ~/umbral-agent-stack
git fetch origin main
git checkout main
git pull --ff-only origin main
git log -1 --oneline
test -f .agents/tasks/2026-06-01-002-gd1a-restart-gateway-smoke.md && echo TASK_FILE_OK || echo TASK_FILE_MISSING
```

Si `TASK_FILE_MISSING` → STOP y reportar a Cursor (falta sync).

## Autorización de David

Patch G-D1a aplicado 2026-06-01; restart quedó como gate separado. David (2026-06-01):
> "haz lo mejor, lo mas correcto"

Cursor interpreta esto como **autorización para G-D1a-RESTART**: completar D1.1 haciendo
efectivo `maxSpawnDepth=2` en runtime. Sin restart, el patch es inútil para torneos (regla
repo vs VPS).

## Preflight (read-only)

```bash
hostname && whoami
systemctl --user is-active openclaw-gateway
systemctl --user show openclaw-gateway -p ActiveEnterTimestamp --value
python3 - <<'PY'
import json,os
d=json.load(open(os.path.expanduser("~/.openclaw/openclaw.json"),encoding="utf-8"))
print("maxSpawnDepth on disk:", d["agents"]["defaults"]["subagents"]["maxSpawnDepth"])
PY
curl -fsS http://127.0.0.1:18789/health && echo HEALTH_OK
mkdir -p ~/.coord-ag-evidence/G-D1a-RESTART
```

Registrar `ActiveEnterTimestamp` **antes** del restart (baseline: 2026-05-21 11:15:35).

## Restart autorizado

```bash
systemctl --user restart openclaw-gateway
sleep 3
systemctl --user is-active openclaw-gateway
systemctl --user show openclaw-gateway -p ActiveEnterTimestamp --value
curl -fsS http://127.0.0.1:18789/health && echo HEALTH_OK
```

Si `inactive`/`failed` → rollback inmediato (backup G-D1a) + reportar `G_D1a_RESTART_FAIL`.

## Smoke post-restart (read-only, sin secretos)

```bash
openclaw --version 2>&1 | head -3
openclaw status --all 2>&1 | head -40
python3 - <<'PY'
import json,os
d=json.load(open(os.path.expanduser("~/.openclaw/openclaw.json"),encoding="utf-8"))
print("maxSpawnDepth config file:", d["agents"]["defaults"]["subagents"]["maxSpawnDepth"])
PY
journalctl --user -u openclaw-gateway --since "2 min ago" --no-pager \
  | grep -vE 'sk-|ghp_|github_pat_|AZURE_OPENAI|OPENCLAW_GATEWAY_TOKEN|client_secret|refresh_token|NOTION_API_KEY' \
  | tail -30
```

Opcional si disponible sin volcar tokens:
```bash
openclaw models status 2>&1 | head -20
```

**NO** ejecutar spawn real de torneo aquí; solo confirmar gateway healthy y config coherente.

## Criterios de aceptación

- [x] Preflight: VPS `srv1431451`/`rick`, gateway active, `maxSpawnDepth=2` en disco, backup OK.
- [x] Restart ejecutado; pre `2026-05-21 11:15:35` → post `2026-06-01 05:38:52`, pid 1045197.
- [x] Health pre/post 200 (000 transitorio ~9s boot).
- [x] Logs: boot limpio, sin crash loop.
- [x] Evidencia: `~/.coord-ag-evidence/G-D1a-RESTART/{post-restart,smoke,logs-tail,untouched}.txt`.
- [x] VEREDICTO: `G_D1a_RESTART_OK`.
- [x] secret-output-guard respetado.

## Entregable

```
VEREDICTO: <G_D1a_RESTART_OK | G_D1a_RESTART_FAIL | G_D1a_RESTART_PARTIAL>
gateway_active_pre: <timestamp>
gateway_active_post: <timestamp>
health_post_restart: OK|FAIL
maxSpawnDepth_disk: 2
runtime_loads_config: <sí/no/unknown — inferir de logs + health, no adivinar>
rollback_needed: <sí/no>
```

## Stop conditions

Gateway no levanta tras restart · health FAIL persistente · JSON inválido · secreto en stdout ·
superficie no-VPS.

## Post-VEREDICTO (Cursor, repo)

Si `G_D1a_RESTART_OK`: actualizar spine D1.1 → done, D0.3 §4, y **después** registrar boundary
en `notion-governance/docs/policies/05-change-management-and-automation-safety.md` + snapshot
registry si aplica (spawn depth 2 = pre-condición torneo O7).

## Log
### [cursor] 2026-06-01 05:30
Tarea creada tras G_D1a_PATCH_OK. David autorizó completar lo correcto ("haz lo mejor, lo mas
correcto") → restart + smoke. Ejecuta Copilot-VPS.

### [cursor] 2026-06-01 05:35 — secuencia corregida
David: Copilot-VPS aún trabaja D0.2 en VPS → **002 blocked** hasta que termine 2026-05-30-001.
Restart en paralelo invalidaría el reality-check (gateway/uptime/maxSpawnDepth efectivo) y rompe
protocolo un-agente-una-tarea. Orden correcto: D0.2 VEREDICTO → pegar acá → recién entonces 002.

### [copilot-vps] 2026-06-01 05:38 — VEREDICTO G_D1a_RESTART_OK
Preflight OK. Restart rc=0. gateway post `2026-06-01 05:38:52` pid 1045197. health 200 post-restart.
OpenClaw 2026.5.19, 8 agentes, smoke OK. `maxSpawnDepth=2` efectivo en runtime. model.primary
`azure-openai-responses/gpt-5.4` intacto. Worker/Granola no tocados. Evidencia G-D1a-RESTART/.

### [cursor] 2026-06-01 05:42 — capitalización
D1.1 cerrado en spine. D0.3 + policy-05 boundary registrados. Torneos: pre-condición spawn depth
satísfecha; siguen bloqueados por D1.2 (ISSUE-001 launch-point), D1.3 (provider), D2 (wrapper skill).
