---
task_id: 2026-05-07-019
title: H3 isolation — aislar disparador del refusal canned en subagent rick-orchestrator
status: pending
requested_by: copilot-chat
assigned_to: copilot-vps
related: 2026-05-07-017 (F-NEW URGENTE blocked), 2026-05-07-018 (audit OpenClaw — H1+H2 falsificadas, H3 activa)
priority: high
deadline: 2026-05-08
estimated_turns: 2-3
---

# H3 isolation — refusal canned del subagent

## Contexto

- Task 017 BLOCKED. Bump bootstrap aplicado (12k→24k per-file, 60k→120k total) pero **F-G era falsa** — bootstrap NO estaba truncando. Bump se mantiene como mejora colateral.
- Task 018 DONE. Audit Copilot CLI (option γ, research-only) confirmó **H2 también falsa**: OpenClaw inyecta correctamente `## Subagent Context` + `**Your Role**` + task body al `systemPrompt` del subagent (líneas 794-825 de 69535 chars en trajectory `82f4ecc3-…`). El bug **NO** está en OpenClaw. Mapping (a)/(b)/(c) del 017: las 3 caen.
- **Hipótesis 3 (activa)**: refusal `"I'm sorry, but I cannot assist with that request"` (~2k tokens, 0 tool calls, ~2s, responseId presente, stopReason:stop) viene del **modelo `gpt-5.4` (azure-openai-responses)**. Tres causas posibles:
  - **3a (modelo)**: gpt-5.4 (versión/deployment específica) refusa por policy interna ante el prompt completo del subagent.
  - **3b (Azure content filter)**: filtro pre-tx de Azure detecta algo en `systemPrompt` o `task body` y devuelve refusal canned.
  - **3c (workspace bootstrap)**: contenido específico de `~/.openclaw/workspaces/rick-orchestrator/{AGENTS.md,SOUL.md,IDENTITY.md}` (o cualquier file bootstrapeado) dispara la refusa.

Hasta resolver, **delegaciones padre→hijo siguen bloqueadas**. One-hop directo a `main` (David → CLI → agente único) sigue operativo.

## Objetivo

Producir veredicto `3a | 3b | 3c | combinación` con ≥1 vector que "responda OK" y ≥1 que "siga refusando", y propuesta de fix mínimo.

## Restricciones duras

- 0 escrituras permanentes a `~/.openclaw/openclaw.json` ni a workspaces sin revert garantizado (todos los cambios son **temporales con backup**).
- 0 restarts gateway/worker/dispatcher.
- 0 tocar `~/.config/openclaw/copilot-cli-secrets.env` ni env del worker.
- 0 ejecutar `copilot_cli.run` (gates L3 siguen cerradas).
- 0 imprimir valores de tokens. Inspección de `/proc/$PID/environ` **prohibida** (no se necesita en este task; si llegara a necesitarse, aplicar skill `secret-output-guard` regla #8).
- Bump bootstrap (24k/120k) **se mantiene** — no revertir.
- Commits sólo: este task log + report final en `reports/copilot-cli/f10-h3-model-refusal-isolation-2026-05-07.md`.

## Procedimiento

### Bloque 0 — Setup + baseline

```bash
cd /home/rick/umbral-agent-stack
git stash -u
git pull origin main 2>&1 | tail -3

TS=$(date +%Y%m%d-%H%M%S); echo "TS=$TS"

# Backup config y workspaces relevantes
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-019-${TS}
cp -r ~/.openclaw/workspaces/rick-orchestrator ~/.openclaw/workspaces/rick-orchestrator.bak-pre-019-${TS}

# Identificar el modelo actualmente configurado para rick-orchestrator
jq '.agents.list[] | select(.id=="rick-orchestrator") | {id, model}' ~/.openclaw/openclaw.json

# Listar modelos disponibles en OpenClaw (para vector B)
openclaw models list 2>&1 | tee /tmp/019-models-${TS}.txt
```

### Bloque 1 — Baseline replicate (confirmar refusal aún ocurre)

Re-ejecutar el smoke health-check delegation original (mismo task body que 016/017). Confirmar:

- `usage 0/0/0/0`
- `~2s wall time`
- `responseId presente, stopReason:stop`
- response body = canned refusal

```bash
# Disparar baseline via JSONL prompt-driven (mismo método que task 016)
# (David: si el comando exacto no es obvio, usar el último entry de
#  ~/.openclaw/trace/delegations.jsonl como template)

# Capturar trajectory ID generada
ls -lt ~/.openclaw/agents/rick-orchestrator/sessions/*.trajectory.jsonl | head -1
```

**Si el baseline NO refusa** (responde OK): F-NEW se autoresolvió por el bump bootstrap u otro cambio entre 017 y ahora. Saltar a "Cierre" y reportar.

**Si el baseline refusa** (esperado): proceder con vectores A → B → C.

### Bloque 2 — Vector A: task body simplificado (mismo modelo)

**Hipótesis a testear**: el contenido específico del task body de smoke (instrucciones, tono, palabras clave) dispara refusal del modelo. Un task body trivial debería pasar.

```bash
# Construir un dispatch JSONL con task body mínimo:
#   "Respondé exactamente con la palabra: pong"
# Mismo agente (rick-orchestrator), mismo modelo (gpt-5.4), sin cambiar nada de config.
# Capturar trajectory.

# Veredicto vector A:
#  - OK (responde pong) → contenido del smoke task body es el disparador (no es modelo puro)
#  - REFUSA → no es task body; pasar a B
```

Capturar en el report: trajectory path, prompt length, response body (primeros 200 chars), usage, tiempo.

### Bloque 3 — Vector B: modelo alternativo (mismo task body que baseline)

**Hipótesis a testear**: gpt-5.4 (azure) específicamente refusa; otros modelos pasan.

Candidatos en orden de preferencia (usar el **primer disponible**):

1. `gpt-5.4-mini` (azure) — mismo provider, modelo más chico.
2. `gemini-3.1-pro` (google) — provider distinto, capacidad similar.
3. `claude-sonnet-4.6` (anthropic) — provider distinto, alta capacidad.
4. `gpt-5.5` (azure) — siguiente major en mismo provider.

```bash
# Edit temporal de openclaw.json: cambiar agents.list[rick-orchestrator].model.primary
# al modelo alternativo elegido. NO tocar fallbacks.
TS2=$(date +%Y%m%d-%H%M%S)
jq --arg m "<MODEL_ID_ELEGIDO>" \
  '(.agents.list[] | select(.id=="rick-orchestrator") | .model.primary) = $m' \
  ~/.openclaw/openclaw.json > /tmp/openclaw-019-vecB-${TS2}.json

jq -e . /tmp/openclaw-019-vecB-${TS2}.json > /dev/null && echo "[jq OK]" || exit 1
mv /tmp/openclaw-019-vecB-${TS2}.json ~/.openclaw/openclaw.json

# Disparar mismo task body que baseline (smoke health-check completo)

# REVERT inmediato post-test
cp ~/.openclaw/openclaw.json.bak-pre-019-${TS} ~/.openclaw/openclaw.json
jq '.agents.list[] | select(.id=="rick-orchestrator") | .model' ~/.openclaw/openclaw.json
# Confirmar que volvió a gpt-5.4

# Veredicto vector B:
#  - OK → modelo es el disparador (3a o 3b confirmadas)
#  - REFUSA → no es modelo-específico; pasar a C
```

### Bloque 4 — Vector C: bootstrap workspace neutralizado (mismo modelo, mismo task body)

**Hipótesis a testear**: contenido de `AGENTS.md`/`SOUL.md`/`IDENTITY.md` del workspace `rick-orchestrator` dispara refusal cuando se inyecta al systemPrompt.

```bash
TS3=$(date +%Y%m%d-%H%M%S)

# Mover bootstrap files a backup
mkdir -p /tmp/rick-orch-bootstrap-bak-${TS3}
mv ~/.openclaw/workspaces/rick-orchestrator/AGENTS.md  /tmp/rick-orch-bootstrap-bak-${TS3}/ 2>/dev/null
mv ~/.openclaw/workspaces/rick-orchestrator/SOUL.md    /tmp/rick-orch-bootstrap-bak-${TS3}/ 2>/dev/null
mv ~/.openclaw/workspaces/rick-orchestrator/IDENTITY.md /tmp/rick-orch-bootstrap-bak-${TS3}/ 2>/dev/null

# Crear AGENTS.md mínimo neutral (solo para que el agent siga teniendo workspace válido)
cat > ~/.openclaw/workspaces/rick-orchestrator/AGENTS.md <<'EOF'
# rick-orchestrator (test workspace H3)

Test temporal task 019. Bootstrap original respaldado.
EOF

# Disparar mismo task body que baseline

# REVERT inmediato post-test
rm ~/.openclaw/workspaces/rick-orchestrator/AGENTS.md
mv /tmp/rick-orch-bootstrap-bak-${TS3}/* ~/.openclaw/workspaces/rick-orchestrator/
ls -la ~/.openclaw/workspaces/rick-orchestrator/

# Veredicto vector C:
#  - OK → bootstrap del workspace contiene el disparador (3c confirmada)
#  - REFUSA → no es bootstrap; combinación o causa más profunda (provider config, headers, tool definitions)
```

### Bloque 5 — Tabla veredicto

Construir tabla en el report:

| Vector | Modelo | Task body | Bootstrap | Resultado | Implicación |
|---|---|---|---|---|---|
| Baseline | gpt-5.4 | smoke completo | original | ? | confirmar refusal |
| A | gpt-5.4 | "responde pong" | original | ? | task body |
| B | `<alt>` | smoke completo | original | ? | modelo |
| C | gpt-5.4 | smoke completo | minimal | ? | bootstrap |

Mapping a sub-hipótesis:

- A=OK → contenido smoke es el problema (no 3a puro).
- B=OK → 3a o 3b (modelo o filter de Azure).
- C=OK → 3c (bootstrap workspace).
- A=B=C=REFUSA → causa más profunda (tool definitions, provider config, headers Azure).

### Bloque 6 — Cleanup + commit

```bash
# Verificar que openclaw.json y workspace están idénticos al baseline
diff <(jq -S . ~/.openclaw/openclaw.json) <(jq -S . ~/.openclaw/openclaw.json.bak-pre-019-${TS})
diff -r ~/.openclaw/workspaces/rick-orchestrator ~/.openclaw/workspaces/rick-orchestrator.bak-pre-019-${TS}
# Ambos diffs deben ser vacíos

# Mantener backups (no rm) hasta que David confirme cierre

# Commit: report + task log
git add reports/copilot-cli/f10-h3-model-refusal-isolation-2026-05-07.md
git add .agents/tasks/2026-05-07-019-copilot-vps-h3-model-refusal-isolation.md
git commit -m "task(copilot-vps): 019 done — H3 isolation veredicto <X>" -m "<resumen 3-5 lineas>"
git push origin main
```

## Quality gate (antes de commit)

- [ ] `openclaw.json` idéntico al backup pre-019 (diff vacío).
- [ ] `workspaces/rick-orchestrator/` idéntico al backup pre-019 (diff vacío).
- [ ] Backups conservados (no removidos).
- [ ] Report incluye trajectory paths + primeros 200 chars de cada response + usage de cada vector.
- [ ] No hay valores de tokens, PATs, secrets, ni dump de `/proc/PID/environ` en log/report (regla `secret-output-guard` #8).
- [ ] Veredicto explícito (`3a | 3b | 3c | combinación`) y propuesta de fix mínimo.
- [ ] Bump bootstrap (24k/120k) sigue activo (no revertido por error).

## Recomendaciones esperadas según veredicto

- **3a (modelo gpt-5.4 azure)**: switchear `agents.list[rick-orchestrator].model.primary` a alternativo viable, reportar bug a Azure si aplica.
- **3b (Azure content filter)**: revisar policy del deployment azure-openai-responses; ajustar severity threshold si está bajo control de David; alternativamente, usar model fuera de Azure.
- **3c (bootstrap workspace)**: identificar substring/sección que dispara, reescribir AGENTS.md/SOUL.md sin él.
- **Combinación / causa más profunda**: abrir task 020 con scope más amplio (provider headers, tool definitions, dispatch path).

## Resultado esperado

Comentario en este task log con tabla veredicto + link al report. Veredicto único o combinación. Fix mínimo propuesto. F-NEW del Plan Q2 actualizable a "diagnóstico cerrado, fix pending" con plan de acción concreto.
