---
task_id: 2026-05-07-018
title: OpenClaw subagent prompt injection audit (research-only, option γ)
status: done
requested_by: copilot-chat
assigned_to: copilot-vps
related: 2026-05-07-017 (F-NEW URGENTE blocked, hipótesis 2 confirmada)
priority: high
deadline: 2026-05-07
estimated_turns: 1-2
---

# OpenClaw subagent prompt injection audit — research-only

## Contexto

Task 017 cerró BLOCKED con hipótesis 2 confirmada vía evidencia runtime (`context.compiled.systemPrompt` del subagent NO contenía sección `**Your Role**` ni cuerpo de la task asignada por el padre). Antes de tocar runtime/upstream/config, evidencia en código.

Spec original quería usar `copilot_cli.run` (mission=research) pero **se cambió a opción (γ) — research directo sin LLM** tras incident de token leak. Procedimiento revisado:

1. Clone shallow upstream `https://github.com/openclaw/openclaw.git` a tmp, fallback a npm package bundled JS si upstream no accesible.
2. Búsquedas `rg`/`grep` para las 5 preguntas.
3. Comparación versión instalada (`2026.5.3-1`) vs latest (`2026.5.6` si existe en npm).
4. Report en `reports/copilot-cli/f9-openclaw-subagent-prompt-injection-audit-2026-05-07.md`.
5. Cleanup tmp dir, append log, commit + push (sólo report + task log).

## Restricciones duras

- 0 escrituras a `~/.openclaw/openclaw.json`, prompts, `IDENTITY.md`, `SOUL.md`.
- 0 restarts gateway/worker/dispatcher.
- 0 dispatchs `openclaw agent ...`.
- 0 ejecución `copilot_cli.run`.
- 0 tocar `~/.config/openclaw/copilot-cli-secrets.env` o `copilot-cli.env`.
- 0 imprimir el valor del PAT (sólo `len=N fp=...XXXX` si se necesita).
- Commits sólo: report + log de este task.

## 5 preguntas a responder con file:line citations

1. Dónde el `assignedTask`/`message`/task body del padre se serializa al `systemPrompt` del subagent.
2. Si el systemPrompt del child incluye literalmente `**Your Role**` y cómo se popula.
3. Boilerplate del primer user message: `[Subagent Context] You are running as a subagent (depth N/M)... Begin. Your assigned task is in the system prompt under **Your Role**; execute it to completion.`
4. Knobs de config (`subagentPromptTemplate`, `subagentSystemPromptOverride`, env vars) que permitan customizar la inyección sin modificar source.
5. Si release `2026.5.6` (o latest tag) modifica algo de lo anterior vs `2026.5.3-1` instalada.

## Mapping a opciones del task 017

- (a) bug upstream necesario? → SÍ/NO + scope mínimo del fix.
- (b) workaround config-side existe? → SÍ/NO + cómo.
- (c) update `2026.5.6` resuelve? → SÍ/NO/INDETERMINADO + diff relevante.

## Log

### [copilot-vps] 2026-05-07T08:15:22Z — research run (status: done)

**Método**: opción γ (research directo sin LLM). Clone shallow de `github.com/openclaw/openclaw` (`2026.5.6`, commit `c6e6b316`) a `/tmp/openclaw-audit-n4TH/openclaw`. Comparación con dist instalada `2026.5.3-1` en `/home/rick/.npm-global/lib/node_modules/openclaw/dist/`. Sin restarts, sin escrituras runtime, sin dispatchs.

**Hallazgo principal (lead)**: **El bug NO está en OpenClaw.** La inyección de `assignedTask` funciona correctamente en ambas versiones. El `systemPrompt` de `rick-orchestrator` en task 017 SÍ contiene `## Subagent Context` + `## Your Role` + task body verbatim (líneas 794-825 del prompt de 69535 chars). Mi grep en task 017 falló silenciosamente por escaping del regex (`**Your Role**`) al pasar por shell.

**Respuestas a las 5 preguntas** (file:line citations en el report):

1. **Serialización**: `sessions-spawn-tool.ts:270 (lee task)` → `:427 (pasa a spawnSubagentDirect)` → `subagent-spawn.ts:986 (buildSubagentSystemPrompt)` → `:1132 (extraSystemPrompt)` → `attempt-system-prompt.ts:42-44 (appendRuntimeExtraSystemPrompt)` appendea `## Subagent Context\n${extra}\n` al base prompt. Funciona end-to-end.
2. **`**Your Role**` literal**: `subagent-system-prompt.ts:35-54`, hardcoded array `roleLines`. Header + bloque triple-backtick con task body verbatim cuando `hasTask=true`.
3. **Boilerplate user message**: `subagent-initial-user-message.ts:14-25`. Match VERBATIM con el user message observado en trajectory `82f4ecc3-...`.
4. **Config knobs**: solo `agents.list[].systemPromptOverride` + `agents.defaults.systemPromptOverride` (`system-prompt-override.ts:12-26`), que **REEMPLAZAN** el base prompt; NO existe `subagentPromptTemplate` ni equivalente. Workaround config-side **inviable** (no hay nada que customizar — la inyección ya funciona).
5. **2026.5.6 vs 2026.5.3-1**: lógica byte-equivalente en `subagent-system-prompt-B-YmsKsL.js` (dist) vs `src/agents/subagent-system-prompt.ts` (upstream). CHANGELOG `5.4`/`5.5`/`5.6` no menciona cambios al subagent prompt path. Update **NO** resuelve.

**Mapping a opciones del task 017**:

- (a) bug upstream → **NO**. Código correcto. No hay fix que reportar.
- (b) workaround config → **NO**. No existe knob útil.
- (c) update 2026.5.6 → **NO**. Mismo código.

**Causa raíz revisada (hipótesis 3, no diagnosticada aquí)**: refusal canned del modelo `gpt-5.4` (azure-openai-responses) ante el contenido específico del task body o del bootstrap del workspace `rick-orchestrator`. Próximo task de investigación: probar mismo prompt con modelo alternativo (`gpt-5.4-mini`, `gemini-3.1-pro`, `claude-sonnet-4.6`) o con task body simplificado para aislar disparador.

**Recomendaciones para F-NEW (task 017)**:

1. Cerrar F-NEW como "OpenClaw OK; root cause a nivel modelo".
2. Cuestionar el bump `bootstrapMaxChars` 32k→240k (inocente respecto a F-NEW; ya no se justifica).
3. Abrir nuevo task de research: aislar si es modelo o Azure content filter.

**Report**: [`reports/copilot-cli/f9-openclaw-subagent-prompt-injection-audit-2026-05-07.md`](../../reports/copilot-cli/f9-openclaw-subagent-prompt-injection-audit-2026-05-07.md)

**Cleanup**: `rm -rf /tmp/openclaw-audit-n4TH` ejecutado.

### Incident 2026-05-07 — token leak via /proc/environ inspection

**Causa**: durante validación del entorno del worker (PID 49918), ejecuté un `grep -E "COPILOT|RICK_COPILOT|REPO_ROOT" /proc/$WORKER_PID/environ` para verificar que las gates L1-L5 de `copilot_cli.run` estuvieran cerradas. El patrón `COPILOT` matched también `COPILOT_GITHUB_TOKEN=github_pat_...` y el valor completo (len=93) quedó impreso en terminal + transcript.

**Mitigación**: David rotó el PAT inmediatamente tras el incidente. Confirmado.

**Nueva regla operativa para inspección de `/proc/$PID/environ`**:

```bash
# CORRECTO: filtrar tokens explícitamente, mostrar sólo fingerprint
tr '\0' '\n' < /proc/$PID/environ \
  | grep -E "RICK_COPILOT|COPILOT_CLI_(ENABLED|EXECUTE)|REPO_ROOT" \
  | grep -v "_TOKEN=" \
  | awk -F= '{print $1"="$2}'

# Para tokens (cuando es necesario verificar presencia/longitud):
tr '\0' '\n' < /proc/$PID/environ \
  | grep "_TOKEN=" \
  | awk -F= '{print $1": len="length($2)" fp=..."substr($2,length($2)-4)}'
```

**NUNCA**: `grep "COPILOT"`, `grep "TOKEN"`, `grep "PAT"`, ni `cat /proc/$PID/environ | tr '\0' '\n'` sin filtro de exclusión, ni imprimir valor crudo de cualquier var con sufijo `_TOKEN`/`_KEY`/`_SECRET`/`_PASSWORD`.
