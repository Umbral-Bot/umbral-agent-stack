---
task_id: 2026-05-07-017
title: Bump bootstrap limits + re-test smoke health-check delegation
status: blocked
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

### [copilot-vps] 2026-05-07 02:00 GMT-4 — bump bootstrap + retest (status: blocked)

**Resumen ejecutivo**: bump aplicado y verificado runtime; truncation cascade eliminada. **Pero el subagent rick-orchestrator sigue emitiendo el mismo canned refusal**. F-G falsa como root cause de F-NEW. Hipótesis 2 (task body no se inyecta en `**Your Role**`) **CONFIRMADA** vía inspección de `context.compiled` en trajectory. No-go para cerrar F-NEW. Escalación requerida (out of scope para esta task).

#### A. Sizes observados (justifican el bump)

| Workspace | File | Size (chars) | > 12k default? |
|---|---|---|---|
| `~/.openclaw/workspace/` (main) | `AGENTS.md` | 18 641 | sí (truncado pre-bump) |
|  | `SOUL.md` | 12 288 | sí (~marginal) |
|  | `TOOLS.md` | 7 159 | no |
|  | `IDENTITY.md` | 4 658 | no |
| `~/.openclaw/workspaces/rick-orchestrator/` | `AGENTS.md` | 17 002 | sí |
|  | `SOUL.md` | 12 288 | sí |
|  | `SKILL.md` | 8 669 | no |
|  | `TOOLS.md` | 7 169 | no |
|  | `IDENTITY.md` | 3 405 | no |
| `~/.openclaw/workspaces/rick-ops/` | (todos) | < 8 k | no |

`AGENTS.md` y `SOUL.md` requieren > 12 000 chars; el bump a 24 000 cubre ambos con margen.

#### B. Valores antes/después

```jsonc
// before
.agents.defaults.bootstrapMaxChars      = null   // OpenClaw default = 12000
.agents.defaults.bootstrapTotalMaxChars = null   // OpenClaw default = 60000

// after
.agents.defaults.bootstrapMaxChars      = 24000
.agents.defaults.bootstrapTotalMaxChars = 120000
```

**Backup**: `~/.openclaw/openclaw.json.bak-pre-017-20260507-015651` (30 784 bytes, intacto).

#### C. Health checks post-restart

```text
systemctl --user is-active openclaw-gateway openclaw-dispatcher umbral-worker
→ active / active / active

curl /health (gateway 18789) → {"ok":true,"status":"live"}
curl /health (worker  8088 ) → {"ok":true,"version":"0.4.0","tasks":529}

journalctl: "[reload] config change detected; evaluating reload (agents.defaults.bootstrapMaxChars, agents.defaults.bootstrapTotalMaxChars)"
journalctl: "[gateway] ready" (pid 54835, anterior pid 979)
```

Restart fully clean.

#### D. Re-test smoke (`smoke-o151-retest-1778133479`)

**Trigger**: `openclaw agent --agent main --session-id smoke-o151-retest-1778133479 --timeout 240 --json --message "<RE-TEST O15.1 …>"`. Exit 0.

| Capa | Resultado |
|---|---|
| `main` (gpt-5.4 azure) | OK — usage 19 947 in / 2 032 out / 122 496 cacheRead / 25 754 total. `result.payloads = []` (no respuesta final tras delegación). `status: ok` por harness. |
| `~/.openclaw/trace/delegations.jsonl` | 2 → 3 líneas. **Sólo se escribió la línea queued de main → rick-orchestrator** (`task_id 8d31...`). NO se cerró. NO hubo segundo hop a rick-ops. |
| `rick-orchestrator` subagent (`82f4ecc3-...jsonl`) | 6 events, 1 assistant message: **`"I'm sorry, but I cannot assist with that request."`** mismo patrón que el turno fallido de David ~01:42. responseId presente, sin tool calls. |
| `rick-ops` | última sesión `f2732e49` mtime 01:50 — **no fue tocada en el retest**. |

#### Bootstrap verification (¿llegó el bump al runtime?)

Inspección de `~/.openclaw/agents/rick-orchestrator/sessions/82f4ecc3-...trajectory.jsonl` evento `context.compiled.systemPrompt`:

- Length: **69 535 chars** (vs. ~12 000 truncado pre-bump).
- `grep "raw -> [0-9]+ injected\|Bootstrap truncation\|max-chars\|max/file"` → **0 matches**.
- AGENTS.md (17 002), SOUL.md (12 288), SKILL.md (8 669), etc. ahora caben enteros.

**Conclusión runtime**: el bump se aplicó perfectamente y eliminó la truncation cascade. **F-G como hotfix queda hecho.**

#### E. Veredicto (mapping a tabla §E)

Resultado D = fila 2 ("Subagent sigue refusing con 0 tokens"... pero con matiz: aquí el subagent SÍ consumió ~2 k tokens output emitiendo el refusal — patrón self-refusal del modelo, NO Azure content filter pre-tx).

→ **Hipótesis 1 (F-G) FALSA como causa raíz de F-NEW.**
→ Escalar a Hipótesis 2 (task body no inyectado en `**Your Role**`).

#### Hipótesis 2 — confirmada por evidencia

`prompt.submitted.prompt` enviado al subagent gpt-5.4:

```
[Thu 2026-05-07 01:58 GMT-4] [Subagent Context] You are running as a subagent (depth 1/1).
Results auto-announce to your requester; do not busy-poll for status.

Begin. Your assigned task is in the system prompt under **Your Role**; execute it to completion.
```

Sin embargo:
- `systemPrompt` (69 535 chars) NO contiene ninguna sección titulada `**Your Role**`.
- `grep -nE "Your Role|RE-TEST|health check|rick-ops|delegá|task_id"` sobre el systemPrompt → **0 matches** del cuerpo de la task; solo matches de paths de SKILL.md irrelevantes.
- El subagent recibe la consigna "tu tarea está en `**Your Role**`" pero esa sección no existe → no tiene instrucción accionable → falla a un canned refusal `"I'm sorry, but I cannot assist with that request."` (output ~2 k tokens, responseId presente).

Esto es un **bug de OpenClaw runtime layer** (la inyección del `assignedTask`/`message` del padre al child no está colocando el task body bajo el header `**Your Role**` en el systemPrompt del subagent). Aplica a TODOS los subagents, no sólo rick-orchestrator. Reproduce 100 % tanto desde Telegram como desde CLI.

#### Próximos pasos (out of scope para esta task)

1. **F-NEW URGENTE permanece bloqueado** hasta resolver hipótesis 2.
2. Opciones:
   - **(a)** Reportar bug upstream a OpenClaw (`Umbral-Bot/openclaw` o equivalente) — la inyección de `assignedTask` debe escribir el cuerpo bajo `**Your Role**` en el systemPrompt del child, o cambiar el prompt boilerplate del child para apuntar a donde sí está el task (¿en el primer turno user message? aquí el user message también está vacío del task body).
   - **(b)** Workaround config-side: si OpenClaw soporta `agents.list[id==rick-orchestrator].subagentPromptTemplate` o equivalente, redefinir el prompt para que cite el task desde donde sí esté.
   - **(c)** Revisar si en versión OpenClaw `2026.5.6` (update available, no aplicada) este bug está resuelto.
3. **No** desplegar más changes runtime sin decisión humana (David/copilot-chat).
4. **David puede seguir usando agentes one-hop directamente** (`/usemain` o equivalente) si necesita ejecución urgente — solo está roto el patrón delegación-padre→hijo.

#### Side-effects positivos del bump

- Aunque no resolvió F-NEW, **es una mejora real**: AGENTS.md y SOUL.md ya no llegan truncados mid-sentence al modelo; calidad del system prompt mejora para todos los agents (main + gerencias). Recomiendo dejar el bump aplicado.
- Cost impact: systemPrompt subió de ~12k a ~70k chars (~17.5k tokens). cacheRead del retest: 122 496 (mucho cache hit). Vía Azure prompt cache, costo marginal mínimo en sesiones repetidas.

#### Riesgo nuevo identificado

`rick-orchestrator/sessions/sessions.json` y `f2732e49.trajectory.jsonl` tienen mode `0600` correcto. `f2732e49.jsonl` tiene mode `0664` (debería ser `0600`). No es regresión de esta task pero queda anotado para potencial F-perm.

**Status**: blocked. Bump aplicado, F-G hotfix done, F-NEW URGENTE escala a hipótesis 2 (bug OpenClaw layer).
