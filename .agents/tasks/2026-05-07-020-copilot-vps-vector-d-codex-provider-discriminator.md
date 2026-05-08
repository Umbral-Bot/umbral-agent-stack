---
task_id: 2026-05-07-020
title: Vector D — discriminar 3a vs 3b vía openai-codex/gpt-5.4 (mismo modelo, distinto provider)
status: done
requested_by: copilot-chat
assigned_to: copilot-vps
related: 2026-05-07-019 (H3 aislada a 3a/3b vía receta α; falta discriminar provider stack)
priority: medium
deadline: 2026-05-08
estimated_turns: 1
---

# Vector D — discriminador 3a vs 3b

## Contexto

Task 019 cerró con verdict **3a/3b** (model+provider stack). Receta α (4 dispatches `sessions_spawn(model=)` per-call, sin file edits ni restart) probó:

- v1 baseline `azure-openai-responses/gpt-5.4` → REFUSAL canned, `usage:null`, 0 tokens billed, 2s.
- v2 trivial body "pong" mismo modelo → REFUSAL canned, 0 tokens billed, 2s.
- v3 swap a `google-vertex/gemini-3.1-pro-preview` mismo body → NORMAL, 193,660 tokens, 90s, ejecutó `exec uuidgen`.
- v4 bootstrap minimal 95B mismo modelo Azure → REFUSAL canned, 0 tokens billed, 6s.

Fingerprint (`usage:null` + 0 tokens billed + 2-6s wall + mensaje canned determinista) **apunta fuerte a 3b — Azure content-filter pre-block** (un refusal intrínseco del modelo billarías input tokens). Pero falta discriminar al 100%.

**Vector D**: spawnear el mismo modelo `gpt-5.4` desde un provider distinto (`openai-codex/gpt-5.4`). Si responde NORMAL → **3b confirmado** (filtro Azure-side). Si refusa con mismo fingerprint → **3a confirmado** (policy del modelo). Si refusa con fingerprint distinto (usage no-null, tokens billed) → **3a parcial** + nuevo análisis.

Report task 019: `reports/copilot-cli/f10-h3-model-refusal-isolation-2026-05-07.md` (referencia para baseline body, sha256, trajectory paths).

## Objetivo

Producir veredicto `3a | 3b | 3a+3b combinación` con evidencia de tokens y wall time, y consolidar fix permanente (switch a `google-vertex/gemini-3.1-pro-preview` queda confirmado como solución correcta independiente del verdict).

## Restricciones duras

- 0 escrituras permanentes a `~/.openclaw/openclaw.json` ni a workspaces.
- 0 restarts gateway/worker/dispatcher.
- 0 tocar `~/.config/openclaw/copilot-cli-secrets.env` ni env del worker.
- 0 ejecutar `copilot_cli.run`.
- 0 imprimir valores de tokens (skill `secret-output-guard` regla #8 vigente — NO `grep "COPILOT" /proc/$PID/environ`).
- Bump bootstrap (24k/120k) se mantiene.
- Receta: `sessions_spawn(model=openai-codex/gpt-5.4)` per-call; **no edits a config**.
- Backups task 019 NO borrar todavía (David cierra F-NEW post-vector-D).

## Procedimiento

### Bloque 0 — Setup

```bash
cd /home/rick/umbral-agent-stack
# F-INC-002 mitigación: chequear divergencia antes de pull
git fetch origin
git log --oneline origin/main..HEAD
git log --oneline HEAD..origin/main
# Si divergencia inesperada → abortar y avisar
git stash -u 2>&1 | tail -2
git pull origin main 2>&1 | tail -3

TS=$(date +%Y%m%d-%H%M%S); echo "TS=$TS"

# Verificar que provider openai-codex está disponible en OpenClaw
openclaw models list 2>&1 | grep -i "codex\|openai" | tee /tmp/020-providers-${TS}.txt
```

Si `openai-codex/gpt-5.4` **no figura** en `models list`:
- Reportar lista completa de providers que sí incluyen `gpt-5.4`.
- Si no hay alternativa que NO sea `azure-openai-responses`, abortar vector D y reportar como **inconcluso** — verdict 3b queda como hipótesis fuerte por fingerprint, sin discriminación 100%. En ese caso, saltar directo a recomendación de fix permanente.

### Bloque 1 — Vector D dispatch (mismo body que v1 baseline task 019)

Reutilizar el baseline body exacto de task 019 (sha256 `206c896c…b15a72a5ea43f9eba11197e38e84`, 977 chars, opens "Sos rick-orchestrator. Ejecutá la vía canónica delegando a rick-ops…").

```bash
# Localizar baseline body desde reports task 019
ls -1 reports/copilot-cli/f10-h3-model-refusal-isolation-2026-05-07.md
# Body completo está en sección "Baseline body" del report; copiar verbatim.

# Dispatch vía sessions_spawn con model override openai-codex
# (mismo patrón que v3 task 019, cambiando model param)
# Capturar:
#  - sessionId
#  - trajectory path
#  - tokens (cacheRead, in, out, total)
#  - wall time
#  - response final (refusal canned vs normal)
#  - tool calls (lista)
```

### Bloque 2 — Verificación verbatim + análisis

```bash
# Verificar body llegó verbatim al subagent (igual que task 019, evita contaminación driver)
# diff sha256 contra baseline.

# Tabla resultado:
# vector | provider/model              | response  | usage(in/out/cache) | wall | tool calls
# v1     | azure/gpt-5.4               | REFUSAL   | null/null/null      | 2s   | 0
# v3     | vertex/gemini-3.1-pro       | NORMAL    | 36188/3114/193660   | 90s  | exec uuidgen
# vD     | openai-codex/gpt-5.4        | ???       | ???                 | ???  | ???
```

### Bloque 3 — Verdict final

Mapping:
- vD NORMAL → **3b confirmado** (filtro Azure-side); fix sigue siendo gemini-3.1-pro-preview (Vertex es path validado y barato vs cambiar provider de gpt-5.4).
- vD REFUSAL fingerprint igual a v1 (`usage:null`, 0 tokens, 2-6s) → **3a confirmado** (policy del modelo gpt-5.4 sin importar provider).
- vD REFUSAL fingerprint distinto (usage no-null, tokens billed >0) → **3a parcial** + filtro Azure adicional (3a+3b combinación).
- vD ERROR (modelo no autenticado / quota) → reportar y abortar; verdict queda 3b por fingerprint heurístico.

### Cierre

- Append log estructurado al final de este task con tabla, sessionId/trajectory, verdict y costo de tokens.
- Commit: `task(020): vector D done — verdict <3a|3b|combinación> (openai-codex/gpt-5.4 <NORMAL|REFUSAL>)`
- NO crear report separado salvo que el verdict cambie significativamente (en ese caso: `reports/copilot-cli/f10b-vector-d-provider-discriminator-2026-05-07.md`).
- NO tocar plan notion-governance — Copilot Chat capitaliza después.

## Output esperado

1. Veredicto final `3a | 3b | 3a+3b` con tabla de evidencia (4 vectores task 019 + vector D).
2. Tokens billed totales del experimento.
3. Recomendación de fix permanente confirmada (esperado: `google-vertex/gemini-3.1-pro-preview` independiente del verdict).
4. Estado state preservado: openclaw.json + workspaces sin tocar, backups conservados.

## Salvavidas

Si algo se rompe (provider error, quota, gate trip), revertir es trivial: no se hizo ningún edit. Solo reportar y devolver control.

---

## Log de ejecución — 2026-05-07T14:19-14:24Z (copilot-vps)

### Bloque 0 — Setup

- Pre-flight F-INC-002: `git fetch origin` → main al día con `2628ee4` (task 020 spec). Worktree limpio. Switch desde branch `copilot-vps/013k-youtube-vm-dataapi-spike` → `main` + fast-forward pull OK.
- Provider check: `openclaw models list` confirma `openai-codex/gpt-5.4` listado como `text 195k fallback#3,configured`. Captura: `/tmp/020-models.txt`.
- TS local = `20260507-101907`. TS UTC dispatch = `20260507T141933Z`.

### Bloque 1 — Vector D dispatch

- Comando: `openclaw agent --agent main --session-id 020-vD-codex-20260507T141933Z --timeout 360 --message <directive>` reusando exactamente `/tmp/019/build-directive.sh "020-vD-codex" /tmp/019/baseline-task.txt "openai-codex/gpt-5.4"` (mismo patrón v3 de task 019, único cambio = `model: openai-codex/gpt-5.4`).
- Baseline body sha256 reusado verbatim: `206c896cc0e4ceae0f37009ff4b4e63bfc95b15a72a5ea43f9eba11197e38e84` (995 B, idéntico al baseline canónico de task 019).
- Wall total dispatch = 36s. Subagent terminó en 6s.
- Exit del CLI = 0; reporte de main: trajectory_path `main -> agent:rick-orchestrator:subagent:4e944c97-eaff-49ec-be55-6f8911caec62`, finishReason `failed — OAuth token refresh failed for openai-codex: Failed to refresh OpenAI Codex token`.

### Bloque 2 — Verificación + análisis

- Trayectoria del subagente (parent rick-orchestrator): `~/.openclaw/agents/rick-orchestrator/sessions/ff4313c1-2145-4d67-8a63-6adda6a47a69.trajectory.jsonl`.
- Único record es `model.fallback_step` (no `session.started`, no `model.completed`, no `prompt.submitted`):
  ```json
  {
    "type": "model.fallback_step",
    "provider": "openai-codex",
    "modelId": "gpt-5.4",
    "data": {
      "fallbackStepType": "fallback_step",
      "fallbackStepFromModel": "openai-codex/gpt-5.4",
      "fallbackStepFromFailureReason": "auth",
      "fallbackStepFromFailureDetail": "OAuth token refresh failed for openai-codex: Failed to refresh OpenAI Codex token. Please try again or re-authenticate. | OAuth token refresh failed for openai-codex: Failed to refresh OpenAI Codex token | Failed to refresh OpenAI Codex token",
      "fallbackStepChainPosition": 1,
      "fallbackStepFinalOutcome": "chain_exhausted"
    }
  }
  ```
- El modelo `openai-codex/gpt-5.4` está **configurado** pero el OAuth token está **expirado / no refrescable** desde esta sesión. Como el override per-call no engancha la fallback chain del provider azure (model override fuerza ese provider exacto), el chain se agotó en posición 1.

#### Tabla consolidada (5 vectores)

| vector | provider/model                               | response | usage(in/out/cache)        | wall | tool calls   | trajectory                                                                                          |
| ------ | -------------------------------------------- | -------- | -------------------------- | ---- | ------------ | --------------------------------------------------------------------------------------------------- |
| v1     | azure-openai-responses/gpt-5.4               | REFUSAL  | null/null/null             | 2s   | 0            | `~/.openclaw/agents/rick-orchestrator/sessions/d20c3a76-981b-4aa0-9601-59e657de9614.trajectory.jsonl` |
| v2     | azure-openai-responses/gpt-5.4 (body "pong") | REFUSAL  | null/null/null             | 2s   | 0            | `~/.openclaw/agents/rick-orchestrator/sessions/5d5f60e3-fc06-42d1-b571-5f8521d5a473.trajectory.jsonl` |
| v3     | google-vertex/gemini-3.1-pro-preview         | NORMAL   | 36188/3114/193660          | 90s  | exec uuidgen | `~/.openclaw/agents/rick-orchestrator/sessions/7d4da225-5dd4-495f-bdc8-c0a488dd8421.trajectory.jsonl` |
| v4     | azure-openai-responses/gpt-5.4 (95B)         | REFUSAL  | null/null/null             | 6s   | 0            | `~/.openclaw/agents/rick-orchestrator/sessions/4461c4c7-8921-4de2-b122-22d897877585.trajectory.jsonl` |
| **vD** | **openai-codex/gpt-5.4**                     | **ERROR** (auth) | 0/0/0              | 6s   | 0            | `~/.openclaw/agents/rick-orchestrator/sessions/ff4313c1-2145-4d67-8a63-6adda6a47a69.trajectory.jsonl` |

### Bloque 3 — Verdict final

Aplicando mapping del spec:

> vD ERROR (modelo no autenticado / quota) → reportar y abortar; verdict queda 3b por fingerprint heurístico.

**Veredicto: 3b por heurística (no discriminado al 100%)**.

Justificación: el OAuth de `openai-codex` está caducado y la receta α prohíbe tocar `~/.config/openclaw/copilot-cli-secrets.env` ni hacer `openclaw login` (alteraría el state que se debe preservar). El fingerprint de v1/v2/v4 (`usage:null` + 0 tokens billed + 2-6s wall + mensaje canned determinista) sigue siendo el indicio más fuerte de **3b — Azure content-filter pre-block** (un refusal intrínseco del modelo billaría input tokens). vD no aporta evidencia adicional ni en pro ni en contra; lo único que demuestra es que no podemos discriminar sin re-auth de codex.

### Costo de tokens del experimento (vector D solo)

- Subagent (rick-orchestrator vía openai-codex): 0 tokens (failed antes de modelo).
- Driver (main vía azure-openai-responses/gpt-5.4): 2 model.completed turns (carga del directive + reporte). Tokens estimados <4k input + <0.5k output (ronda mínima dentro del bump 24k/120k).

### Recomendación de fix permanente (confirmada e independiente del verdict)

`google-vertex/gemini-3.1-pro-preview` queda como path validado (v3 ejecutó NORMAL, 90s, billed 193,660 tokens, ejecutó tool `exec uuidgen` correctamente). Vertex es path barato vs cambiar provider de gpt-5.4 (que además requeriría re-auth de codex, fuera de scope vector D).

Acción de seguimiento (queda para task separada — no en este task):
- **task 021 (sugerida)**: re-auth de `openai-codex` (`openclaw login openai-codex` o equivalente) + retry vector D para discriminación 100% + decisión final sobre cambio de default provider de orchestrator a `google-vertex/gemini-3.1-pro-preview`. Esta task implica restart de gateway y debe ser autorizada explícitamente por David.

### State preservación

- `diff <(jq -S . ~/.openclaw/openclaw.json) <(jq -S . ~/.openclaw/openclaw.json.bak-pre-019-20260507-093659)` → **EMPTY** ✅
- `diff -rq --exclude='.sync-backups' ~/.openclaw/workspaces/rick-orchestrator ~/.openclaw/workspaces/rick-orchestrator.bak-pre-019-20260507-093659` → **EMPTY** ✅
- Gateway pid 54835 (port 18789) intacto ✅
- `~/.config/openclaw/copilot-cli-secrets.env` no tocado ✅
- 0 restarts, 0 edits permanentes, 0 ejecuciones de `copilot_cli.run` ✅
- Backups task 019 preservados (David pendiente de cerrar F-NEW post-vector-D — ahora con verdict heurístico 3b). ✅
