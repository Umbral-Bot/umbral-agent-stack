---
id: "2026-05-30-001"
title: "Verificación read-only del runtime: torneo + multi-agente + OpenClaw (base Q2 v2)"
status: assigned
assigned_to: copilot
created_by: cursor
priority: high
sprint: W-A
created_at: 2026-05-30T22:00:00-04:00
updated_at: 2026-05-30T22:00:00-04:00
owner: copilot-vps
reviewer: copilot-chat
phase: Q2-v2-D0
depends_on:
  - notion-governance/docs/roadmap/13-q2-2026-v2-deployment-spine.md (paso D0.2)
  - notion-governance/docs/audits/2026-05-30-q2-tournament-multiagent-openclaw-diagnostic.md (§8)
---

## Objetivo

Cerrar los `[VPS?]` del diagnóstico Q2 v2 con una verificación **read-only** del runtime, para no construir el spine de despliegue (torneo + multi-agente) sobre suposiciones. Esta tarea NO modifica nada: solo lee estado y lo reporta separando "repo dice X" vs "VPS muestra Y" (VPS Reality Check Rule, `.github/copilot-instructions.md`).

> El restart del worker (acción A1 / paso D0.1, que revive Granola) es una tarea **separada** que requiere autorización explícita de David. Esta tarea solo diagnostica; si confirma que Granola sigue caído, lo reporta y se detiene.

## Contexto

- Diagnóstico 2026-05-30 (`notion-governance/docs/audits/2026-05-30-q2-tournament-multiagent-openclaw-diagnostic.md`) consolidó estado con datos de hasta 2026-05-20.
- Pendientes de confirmar hoy: `maxSpawnDepth`, `agents.list`, `model.primary` vigente, salud gateway/worker, y estado real de la pipeline Granola (muerta desde 2026-05-11 según VPS check 2026-05-20).
- Skills aplicables: `openclaw-vps-operator`, `windows-vps-execution-split`, `secret-output-guard` (NO imprimir valores de tokens; solo fingerprints/longitud).

## Preflight repo (Copilot-VPS — obligatorio, primer paso)

Cursor debe haber hecho **push a `main`** antes de este handoff. En VPS:

```bash
cd ~/umbral-agent-stack
git fetch origin main
git checkout main
git pull --ff-only origin main
git log -1 --oneline
test -f .agents/tasks/2026-05-30-001-verify-tournament-multiagent-openclaw-runtime.md && echo TASK_FILE_OK || echo TASK_FILE_MISSING
```

Si `TASK_FILE_MISSING` → STOP y reportar a Cursor (falta sync).

## Acciones requeridas (todas read-only)

### 1. Gateway + agentes OpenClaw
```bash
ssh rick@<vps>
openclaw --version
systemctl --user status openclaw-gateway --no-pager | head -20
curl -fsS http://127.0.0.1:18789/health
openclaw status --all 2>&1 | head -60
# Topología y modelos (sin volcar secretos):
jq '.agents.list[] | {id, default, model: .model.primary}' ~/.openclaw/openclaw.json
jq '.agents.defaults.subagents.maxSpawnDepth' ~/.openclaw/openclaw.json
jq '.agents.defaults.subagents // {} | {maxChildrenPerAgent, maxConcurrent}' ~/.openclaw/openclaw.json
```
Reportar: versión, estado gateway, health, lista de agentes + `model.primary` por agente, **valor real de `maxSpawnDepth`** (clave para D1.1), caps de concurrencia.

### 2. Worker (multi-agente)
```bash
curl -fsS -H "Authorization: Bearer $WORKER_TOKEN" http://127.0.0.1:8088/health | jq '{ok, version, tasks_registered: (.tasks_registered | length)}'
systemctl --user status umbral-worker --no-pager | head -15   # confirmar uptime / fecha de arranque (drift)
```
Reportar: version worker, nº de handlers, **desde cuándo corre el proceso** (drift vs HEAD), si `rick.orchestrator.triage` y `granola.*` están en `tasks_registered`.

### 3. Granola pipeline (estado de muerte / vida)
```bash
tail -n 40 /tmp/notion_poller.log 2>/dev/null | grep -iE "granola|500|error" | tail -20
grep -aoE '"task": "granola\.[^"]+"' ~/.config/umbral/ops_log.jsonl | sort | uniq -c | tail
# última ejecución exitosa:
grep -a "granola.classify_raw" ~/.config/umbral/ops_log.jsonl | tail -3
crontab -l | grep -iE "granola|poller" || echo "no granola/poller cron"
```
Reportar: última ejecución exitosa de `granola.classify_raw`, si sigue el HTTP 500, si `granola-gap-check.sh` está o no en crontab. Confirmar si A1 (restart) sigue siendo necesario.

### 4. Provider routing (fase actual)
```bash
jq '.agents.list[] | select(.id=="rick-orchestrator") | .model' ~/.openclaw/openclaw.json
journalctl --user -u openclaw-gateway --since "24 hours ago" --no-pager | grep -iE "fallback|refus|content.?filter|auth" | tail -20
```
Reportar: `model.primary` de `rick-orchestrator` (¿Vertex/Azure/Codex?), evidencia de refusals o fallbacks recientes (relevante para G-D1c y el riesgo de refusal canned en torneos).

### 5. Torneo — pre-condiciones
- Confirmar si existe la skill `multi-agent-tournament-orchestrator` en `~/.openclaw/workspace/skills/` (esperado: ausente).
- Confirmar `docs/79-tournament-protocol-openclaw-native.md` presente en el clone VPS del repo.

## Criterios de aceptación
- [ ] Reporte con tabla "repo dice X" vs "VPS muestra Y" para: gateway, worker, Granola, provider, maxSpawnDepth.
- [ ] Valor real de `maxSpawnDepth` documentado (input directo a D1.1).
- [ ] Estado Granola confirmado (vivo/muerto) + recomendación A1 sí/no.
- [ ] Provider primary vigente de `rick-orchestrator` documentado.
- [ ] CERO mutaciones (no restart, no edit `openclaw.json`, no write Notion). Solo lectura.
- [ ] `secret-output-guard` respetado (sin tokens crudos; usar fingerprint/longitud).
- [ ] Outcome escrito en `notion-governance/docs/audits/2026-05-30-vps-reality-check-q2v2-d0.md` (o handoff a Copilot Chat para redactarlo).

## Log
### [cursor] 2026-05-30 22:00
Tarea creada como paso D0.2 del Plan Q2 v2 (`notion-governance/docs/roadmap/13-q2-2026-v2-deployment-spine.md`). Read-only. El restart del worker (D0.1/A1) queda como gate separado para David.
