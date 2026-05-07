---
task_id: 2026-05-07-019
title: H3 isolation — aislar disparador del refusal canned en subagent rick-orchestrator
status: blocked
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

### [copilot-vps] 2026-05-07T13:44:58Z — pre-flight blocked (status: blocked)

**Estado**: Bloque 0 (setup + backups) ejecutado OK. Bloque 1+ NO ejecutados. Status flipped a `blocked` por hallazgo procedural en Vector B que invalida la receta del task spec y requiere confirmación tuya antes de proceder con dispatchs costosos.

#### Backups creados (intactos)

```
~/.openclaw/openclaw.json.bak-pre-019-20260507-093659                       (30858 bytes)
~/.openclaw/workspaces/rick-orchestrator.bak-pre-019-20260507-093659/       (full tree, ls verified)
```

#### Setup data verificada

- Modelo actual rick-orchestrator: `primary=azure-openai-responses/gpt-5.4`, fallbacks=`[gpt-5.2-chat, openai-codex/gpt-5.4]`.
- Modelos disponibles para Vector B: `gpt-5.4-mini` **NO** existe en el catálogo. Candidatos viables (en orden):
  - `google-vertex/gemini-3.1-pro-preview` (provider distinto, alta capacidad).
  - `azure-openai-responses/gpt-5.4-pro` (mismo provider, modelo más capaz).
  - `google/gemini-3-pro-preview` (provider distinto, 195k ctx).
- Gateway running: pid 54835, uptime desde 2026-05-07 01:57:16 -04 (~7h45min al momento del setup).
- Trajectory baseline confirmado: `82f4ecc3-...` con `assistantTexts: ["I'm sorry, but I cannot assist with that request."]`, `promptCache.lastCallUsage = {input:0, output:0, cacheRead:0, cacheWrite:0, total:0}`, `compactionCount: 0`. **Refusal verificada en datos reales del runtime**.
- Dispatch path original (extraído de `agent:main:explicit:smoke-o151-retest-1778133479`): `agent:main` invocó tool `sessions_spawn` con args:
  `{runtime: "subagent", agentId: "rick-orchestrator", label: "...", cwd: "...", timeoutSeconds: 180, task: "<smoke task body>"}` (sin `model` param, hereda del config).

#### Blocker — Vector B según receta del task spec NO funciona

**Receta del task** (Bloque 3):

```bash
jq --arg m "<MODEL_ID>" '(.agents.list[] | select(.id=="rick-orchestrator") | .model.primary) = $m' ~/.openclaw/openclaw.json > /tmp/...
mv /tmp/... ~/.openclaw/openclaw.json
# disparar test
cp .bak ~/.openclaw/openclaw.json   # revert
```

**Por qué NO funciona**:

OpenClaw `2026.5.3-1` (instalada) implementa el config como **singleton pinned snapshot por proceso**. Evidencia desde dist:

1. `/home/rick/.npm-global/lib/node_modules/openclaw/dist/io-FwM1Kn_Q.js`:

   ```js
   function loadConfig() {
     return loadPinnedRuntimeConfig(() => createConfigIO().loadConfig());
   }
   function getRuntimeConfig() {
     return loadConfig();
   }
   ```

2. `/home/rick/.npm-global/lib/node_modules/openclaw/dist/runtime-snapshot-DLdUvYCx.js`:

   ```js
   function loadPinnedRuntimeConfig(loadFresh) {
     if (runtimeConfigSnapshot) return runtimeConfigSnapshot;  // ← cache hit
     const config = loadFresh();
     setRuntimeConfigSnapshot(config);
     return getRuntimeConfigSnapshot() ?? config;
   }
   ```

   El refresh sólo se dispara desde el lifecycle de WRITE oficial (`finalizeRuntimeSnapshotWrite`), no por edits raw del archivo desde fuera del proceso. `fs.watch` sobre `openclaw.json` no aparece en la dist (`grep -lF "fs.watch" dist/*.js` no encuentra el archivo de config en watchers).

⇒ El gateway lleva `runtimeConfigSnapshot` cargado desde `2026-05-07 01:57:16`. Editar `openclaw.json` a las 09:36 **NO** modifica el snapshot en memoria. El spawn de rick-orchestrator seguiría usando `gpt-5.4`, dando un falso negativo del Vector B.

**Para que la receta original funcione** habría que reiniciar el gateway entre el edit y el dispatch — pero el task spec lo prohíbe explícitamente:
> "0 restarts gateway/worker/dispatcher."

#### Adaptación viable propuesta (necesita tu green light)

**Vector B via `sessions_spawn` con `model` override** (sin tocar `openclaw.json`, sin restart):

Confirmado en dist (`openclaw-tools-D7Zj4hDN.js`): el handler de `sessions_spawn` lee `const modelOverride = readStringParam(params, "model");` y lo aplica per-spawn. Coincide con la audit del task 018 (subagent-spawn.ts:280 upstream).

Procedimiento adaptado:

```text
[Baseline] openclaw agent --agent main --session-id 019-baseline-<TS> --message "<directiva: invocá sessions_spawn con runtime=subagent, agentId=rick-orchestrator, label=019-baseline, timeoutSeconds=180, task=<<<task body literal smoke health-check verbatim del baseline>>>>"

[Vector A] Mismo, pero task = "Respondé únicamente con la palabra: pong. Nada más."

[Vector B] Mismo task body que baseline + parámetro extra "model: google-vertex/gemini-3.1-pro-preview" en el sessions_spawn.

[Vector C] mv AGENTS.md/SOUL.md/IDENTITY.md a backup tmp + AGENTS.md mínimo + dispatch baseline + revert.
```

**Ventajas**:
- Cero file edits a `openclaw.json`.
- Cero restarts.
- Vector B usa el mismo mecanismo per-call que ya existe en el código (zero-risk).

**Riesgos/limitaciones que requieren tu confirmación**:

1. **Determinismo del driver `main`**: tengo que esperar que `main` (gpt-5.4 también) invoque `sessions_spawn` con los args literales que le pido. Si interpreta o reformula el `task` body, contamino el experimento. Mitigación: incluir el task body entre delimitadores explícitos (`<<<TASK_BODY>>>` ... `<<<END>>>`) y pedirle "copia-pega exacto, no parafrases". Riesgo residual: ~15-25% de que main edite el body de algún vector.
2. **Costo en tokens**: 4 dispatches × (main turn ~10-20k input + subagent turn ~70k systemPrompt). Estimado total: ~400-500k tokens input + outputs. Azure pricing aplicable.
3. **Vector C** (bootstrap minimal): la receta del task funciona OK (mover archivos + revert), no hay blocker procedural.
4. **Caveat de Vector A**: si simplifico el task body, también cambio el contenido del bloque `## Your Role`, lo cual puede confundir el aislamiento entre 3a/3b/3c. Si A=OK no podemos saber si fue task body simplificado o si el modelo pasó por menor "carga" de prompt.

#### Lo que NO hice (intencional, esperando confirmación)

- ❌ Bloque 1 baseline replicate.
- ❌ Bloque 2 Vector A.
- ❌ Bloque 3 Vector B.
- ❌ Bloque 4 Vector C.
- ❌ Bloque 5 tabla veredicto.
- ❌ Report `reports/copilot-cli/f10-...md`.
- ❌ Edits a `openclaw.json` (la receta original lo pedía pero como no funciona, evité gastar el ciclo).

#### Pregunta para David

**¿Aprobás la adaptación?** Tres opciones:

(α) **Adaptado**: proceder con `sessions_spawn(model=X)` per-call (sin file edits, sin restart). Acepto el riesgo de determinismo del driver main; lo mitigo con delimitadores literales.

(β) **Original con restart**: autorizás 1 (uno) restart controlado del gateway entre Vector B edit y revert (con health check antes y después). Esto preserva la receta del spec literal.

(γ) **Bypass del wrapper subagent**: invocar `openclaw agent --agent rick-orchestrator --model X --message "<prompt completo equivalente>"` directamente (sin pasar por main + sessions_spawn). Determinístico pero NO replica el path real del subagent (no hay `## Subagent Context` en systemPrompt). Útil sólo como sanity check, no como repro.

(δ) **Otra**: indicame.

**Backups conservados intactos hasta tu cierre.**
