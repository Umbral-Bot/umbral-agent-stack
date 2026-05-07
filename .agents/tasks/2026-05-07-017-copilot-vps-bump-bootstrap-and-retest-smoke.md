---
task_id: 2026-05-07-017
title: Bump bootstrap limits + re-test smoke health-check delegation
status: queued
requested_by: copilot-chat
assigned_to: copilot-vps
related: 2026-05-07-016 (F-G + F-NEW)
priority: high
deadline: 2026-05-07 (mismo día — bloquea próximas delegaciones reales de David)
estimated_turns: 3
---

# Bump bootstrap limits + re-test smoke

## Contexto

Task 016 follow-up §F + §G identificó:

- **F-NEW (URGENTE)**: subagent `rick-orchestrator` (gpt-5.4 azure) devolvió canned refusal `"I'm sorry, but I cannot assist with that request"` con `usage 0/0/0/0 tokens, ~2s, stopReason:stop, responseId presente` — patrón Azure content-filter o canned self-refuse.
- **F-G (runtime cause más probable, 80%)**: bootstrap truncation cascade. `AGENTS.md` (18456→11999) y `SOUL.md` (12285→11999) llegan truncados mid-sentence a `bootstrapMaxChars=12000` per-file. System prompt malformado → Azure modera o gpt-5.4 self-refuses.

David recibió respuesta inútil en Telegram tras un health-check trivial. **Bloquea próximas delegaciones reales hasta resolver.**

JSONL prompt-driven YA funcionó (line 2 §3.3 válida en `~/.openclaw/trace/delegations.jsonl` con `task_id 85610454-…` status:queued huérfano por la rotura del subagent).

## Procedimiento

### Bloque A — Defensive checks pre-edit

```bash
cd /home/rick/umbral-agent-stack
git stash -u  # multi-agent terminal hazard, defensivo aunque no haya cambios pending
git pull origin main 2>&1 | tail -3

TS=$(date +%Y%m%d-%H%M%S); echo "TS=$TS"
# 1) Backup openclaw.json
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-017-${TS}
ls -la ~/.openclaw/openclaw.json.bak-pre-017-${TS}

# 2) Inspect workspace files sizes (to size the bump correctly)
echo "=== ~/.openclaw/workspace/ (main) ==="
wc -c ~/.openclaw/workspace/*.md 2>/dev/null

echo "=== ~/.openclaw/workspaces/rick-orchestrator/ ==="
wc -c ~/.openclaw/workspaces/rick-orchestrator/*.md 2>/dev/null

echo "=== ~/.openclaw/workspaces/rick-ops/ ==="
wc -c ~/.openclaw/workspaces/rick-ops/*.md 2>/dev/null

# 3) Current bootstrap config
echo "=== current agents.defaults bootstrap config ==="
jq '.agents.defaults | {bootstrapMaxChars, bootstrapTotalMaxChars}' ~/.openclaw/openclaw.json
```

### Bloque B — Bump limits

Decisión defaults propuesta (basada en sizes observados):

- `bootstrapMaxChars`: 12000 → **24000** (cubre `AGENTS.md` 18456 + margen para futuras adiciones moderadas; no 100k para no inflar context unnecessariamente).
- `bootstrapTotalMaxChars`: 60000 → **120000** (proporcional 2x; ~30k tokens budget total para system prompt entre todos los files).

Si `wc -c` revela files > 24000 chars, escalar a 32000 y reportar.

```bash
TS=$(date +%Y%m%d-%H%M%S)
jq '.agents.defaults.bootstrapMaxChars = 24000 | .agents.defaults.bootstrapTotalMaxChars = 120000' \
  ~/.openclaw/openclaw.json > /tmp/openclaw-017-${TS}.json

# Validate JSON
jq -e . /tmp/openclaw-017-${TS}.json > /dev/null && echo "[jq OK]" || { echo "[jq FAIL] aborting"; exit 1; }

# Diff to confirm only the 2 keys changed
diff <(jq -S . ~/.openclaw/openclaw.json) <(jq -S . /tmp/openclaw-017-${TS}.json)

# Commit edit
mv /tmp/openclaw-017-${TS}.json ~/.openclaw/openclaw.json

# Verify post-edit
jq '.agents.defaults | {bootstrapMaxChars, bootstrapTotalMaxChars}' ~/.openclaw/openclaw.json
```

### Bloque C — Reload + health

```bash
# Restart gateway to pick up new bootstrap config
systemctl --user restart openclaw-gateway
sleep 3
systemctl --user is-active openclaw-gateway openclaw-dispatcher umbral-worker
curl -fsS http://127.0.0.1:18789/health
curl -fsS http://127.0.0.1:8088/health | jq -c '{ok, version, tasks: .tasks_in_memory}'

# Verify no truncation warnings in next bootstrap
journalctl --user-unit openclaw-gateway --since "1 minute ago" --no-pager | grep -iE "bootstrap|truncat|max-chars" | tail -10
```

### Bloque D — Re-test smoke (mismo prompt que David por Telegram)

Disparar el mismo health-check que David envió por Telegram, ahora desde CLI con session aislada para evitar contaminar la sesión real de David:

```bash
SESSION_ID="smoke-o151-retest-$(date +%s)"
echo "session-id=$SESSION_ID"
WC_PRE=$(wc -l < ~/.openclaw/trace/delegations.jsonl); echo "jsonl_pre=$WC_PRE"

openclaw agent \
  --agent main \
  --session-id "$SESSION_ID" \
  --timeout 240 \
  --json \
  --message 'RE-TEST O15.1 Ola 1.5 post bump bootstrap (autorizado por copilot-vps via task 2026-05-07-017, NO es David). Mismo objetivo que el turno de David ~01:42 que falló con "I am sorry" del subagent.

Necesito un health check del worker. Por favor:
1) Delegá a rick-ops vía rick-orchestrator (vía canónica).
2) rick-ops responde con: pong + status del FastAPI worker en 127.0.0.1:8088 + última task procesada.
3) Registrá la delegación en ~/.openclaw/trace/delegations.jsonl según contrato §3.3 de tu IDENTITY.md (una línea jsonl por hop).
4) Cerrá el ciclo: cuando rick-ops responda, escribí línea de cierre con status:done para el task_id correspondiente.
5) Respuesta final corta.' \
  > /tmp/smoke-retest-out.json 2>&1
EXIT=$?
echo "exit=$EXIT"

# Inspect outcome
jq '.result.meta.agentMeta | {provider, model, durationMs, usage, toolCalls: (.toolCalls // null), subagentCalls: (.subagentCalls // null)}' /tmp/smoke-retest-out.json
echo ""
echo "=== final assistant text ==="
jq -r '.result.payloads[0].text' /tmp/smoke-retest-out.json
echo ""
echo "=== jsonl post ==="
WC_POST=$(wc -l < ~/.openclaw/trace/delegations.jsonl); echo "jsonl_post=$WC_POST (expected 4: 2 pre + queued+done o queued main + queued orch + done orch + done main)"
tail -10 ~/.openclaw/trace/delegations.jsonl | jq -c '{requested_by, assigned_to, status, task_id: (.task_id | .[0:8])}'

# Find the orchestrator subagent session that just ran
ORCH_LATEST=$(ls -t ~/.openclaw/agents/rick-orchestrator/sessions/*.jsonl 2>/dev/null | grep -v trajectory | head -1)
echo ""; echo "=== orchestrator subagent latest ($ORCH_LATEST) ==="
echo "wc -l: $(wc -l < $ORCH_LATEST)"
jq -c 'select(.type=="message") | {role: (.message.role // null), text: ((.message.content // .content // "") | tostring | .[0:300])}' "$ORCH_LATEST" | tail -5
```

### Bloque E — Veredicto + reportar

| Resultado bloque D | Diagnóstico | Acción |
|---|---|---|
| Subagent razona, llega a rick-ops, jsonl tiene 3-4 líneas válidas con status:done | F-G/F-NEW resuelto. Bootstrap era el bug. | Cerrar F-G + F-NEW. Notificar David puede re-disparar por Telegram con confianza. |
| Subagent sigue refusing con 0 tokens | Hipótesis 1 falsa. Escalar a hipótesis 2 (task body no se inyecta en `**Your Role**`). | Inspeccionar `~/.openclaw/agents/rick-orchestrator/sessions/<retest>.trajectory.jsonl` campo `context.compiled` para ver system prompt real recibido. NO modificar más runtime. Reportar para escalación. |
| Subagent razona pero falla en otro hop (rick-ops missing, format error, etc.) | Bug diferente. | Documentar y reportar. |
| Gateway no levanta tras restart | JSON malformado o config inválida | `cp ~/.openclaw/openclaw.json.bak-pre-017-${TS} ~/.openclaw/openclaw.json && systemctl --user restart openclaw-gateway`. Reportar. |

## Reportar de vuelta

Append a este file (`.agents/tasks/2026-05-07-017-…md`) sección `### [copilot-vps] <ts> — bump bootstrap + retest (status: done|blocked)` con:

1. Sizes observados de los `.md` files en workspace + workspaces.
2. Valores antes/después de `bootstrapMaxChars` y `bootstrapTotalMaxChars`.
3. Backup path.
4. Health checks post-restart.
5. Resultado del re-test smoke (exit, usage, tool/subagent calls, texto respuesta, jsonl post).
6. Veredicto de la tabla §E + recomendación próxima acción.

Commit con `user.name='copilot-vps'`, push a `origin/main`. Status `done` si re-test verde, `blocked` si necesita decisión humana.

## Scope

**IN**: bump 2 keys en `agents.defaults`, restart gateway, 1 re-test smoke (1-2 turnos modelo).

**OUT**: 
- Modificar prompts/IDENTITY.md/SOUL.md (anti-scope).
- Tocar otros agents besides defaults (no `agents.list[].overrides`).
- Reparar OAuth codex token (F-OAuth-codex separado).
- Reparar Azure reasoning-items `store=false` bug (deferred, requiere actualización OpenClaw o config azure-openai-responses provider).

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Bump rompe OOM en gateway | Improbable (24k chars ≈ 6k tokens, lejos de límites). Backup + rollback step E. |
| Subagent sigue refusing | Tabla E manda a hipótesis 2; NO escalación automática a más fixes runtime. |
| Re-test consume muchos tokens si modelo razona largo | Tope timeout 240s. Smoke trivial debería ser <30s y <30k tokens (similar al smoke 016 que fue ~17s/27k). |
| Multi-agent terminal hazard (Codex en otra branch) | `git stash -u` defensivo bloque A. |
| jq edit malformatea JSON | `jq -e .` validation gate antes de mover. |

## Referencias

- Task 016: [2026-05-07-016-copilot-vps-fc-tracker-vertex-plus-ola15-smoke.md](2026-05-07-016-copilot-vps-fc-tracker-vertex-plus-ola15-smoke.md) §F (F-NEW), §G (recomendación 1).
- Plan: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` O15.1 follow-up F-G.
- Modelo §5.3, §3.3, §3.4 embebidos en `~/.openclaw/workspace/IDENTITY.md` v1.1 y `~/.openclaw/workspaces/rick-orchestrator/IDENTITY.md` v1.1.

## Log
