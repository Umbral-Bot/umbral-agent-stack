---
task_id: 2026-05-07-020
title: Vector D — discriminar 3a vs 3b vía openai-codex/gpt-5.4 (mismo modelo, distinto provider)
status: pending
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
