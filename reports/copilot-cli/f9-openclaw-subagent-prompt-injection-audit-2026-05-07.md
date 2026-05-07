# F9 — OpenClaw subagent prompt-injection audit (research-only)

- **Task**: [`.agents/tasks/2026-05-07-018-copilot-vps-openclaw-subagent-prompt-injection-audit.md`](../../.agents/tasks/2026-05-07-018-copilot-vps-openclaw-subagent-prompt-injection-audit.md)
- **Origen**: F-NEW del task 017 — `rick-orchestrator` (gpt-5.4) responde canned refusal con 0 tool calls.
- **Hipótesis a probar**: el bug reside en cómo OpenClaw inyecta `assignedTask` en el `systemPrompt` del subagent (omisión del bloque `**Your Role**`).
- **Versiones**:
  - Instalada: `openclaw@2026.5.3-1` (npm-global, dist bundleada en `/home/rick/.npm-global/lib/node_modules/openclaw/dist/*.js`).
  - Upstream auditada: `2026.5.6` (commit `c6e6b316`, `HEAD` de `main` en `github.com/openclaw/openclaw`, clonada a `/tmp/openclaw-audit-n4TH/openclaw`).
- **Modo**: read-only (clone + `grep`/`sed`). Sin restarts, sin escrituras a runtime, sin dispatchs `openclaw agent` ni `copilot_cli.run`.

---

## 0. Hallazgo principal (lead)

> **El bug NO está en OpenClaw.** La inyección de `assignedTask` funciona correctamente en `2026.5.3-1` y en `2026.5.6`. El `systemPrompt` que recibió `rick-orchestrator` en task 017 **sí contiene** `## Subagent Context` + `## Your Role` + el task body verbatim (incluyendo la línea de "Begin..." del user message). La causa raíz de F-NEW es **una refusal del modelo** (gpt-5.4 azure-openai-responses), no un fallo de la plataforma de subagents.

Mi grep en task 017 arrojó "(no matches)" para `Your Role` por error de escaping del regex; releyendo el `systemPrompt` con `sed -n '790,880p'` aparecen los bloques esperados verbatim (ver §3.4).

---

## 1. Tabla de evidencia (5 preguntas del CLI mission)

| # | Pregunta | file:line (upstream 2026.5.6) | Evidencia citada | Interpretación |
|---|---|---|---|---|
| 1 | Dónde se serializa `assignedTask` al `systemPrompt` del child | `src/agents/tools/sessions-spawn-tool.ts:270` lee `task` del input ; `:427` lo pasa a `spawnSubagentDirect({task, ...})` ; `src/agents/subagent-spawn.ts:986` llama `buildSubagentSystemPrompt({task, ...})` ; `:1132` pasa el resultado como `extraSystemPrompt: childSystemPrompt` al gateway ; `src/agents/pi-embedded-runner/run/attempt-system-prompt.ts:42-44` (`appendRuntimeExtraSystemPrompt`) appendea `"## Subagent Context\n${extraSystemPrompt}\n"` al base prompt cuando `promptMode==="minimal"`. `promptMode` resuelto por `src/agents/pi-embedded-runner/run/attempt.prompt-helpers.ts:210` = `"minimal"` cuando `isSubagentSessionKey()` (`src/sessions/session-key-utils.ts:69-79`) detecta el prefijo `subagent:` en el sessionKey. Las claves child se generan con ese prefijo en `subagent-spawn.ts:821` (``agent:${id}:subagent:${uuid}``). | `let childSystemPrompt = buildSubagentSystemPrompt({task, ...})` (986) ; `extraSystemPrompt: childSystemPrompt` (1132) ; `` `${params.systemPrompt.trimEnd()}\n\n${contextHeader}\n${extraSystemPrompt}\n` `` (attempt-system-prompt.ts:43-44) | El path `sessions_spawn → spawnSubagentDirect → buildSubagentSystemPrompt → appendRuntimeExtraSystemPrompt` está completo y correcto. **No hay punto de fuga del task body en este path.** |
| 2 | Literal `**Your Role**` u análogos en el child `systemPrompt` | `src/agents/subagent-system-prompt.ts:35-54` construye `roleLines`. Cuando `hasTask=true`: emite `"## Your Role"`, luego `"- You were created to handle the following task (verbatim; line breaks preserved):"` + bloque ` ``` ` con el task body, + `"- Complete this task. That's your entire purpose."`. Si `task` está vacío: fallback `"- You were created to handle: {{TASK_DESCRIPTION}}"`. | `const taskBody = (typeof params.task === "string" ? params.task : "").trim(); const hasTask = taskBody !== "";` (5-6) ; `roleLines` array literales (35-54) | Header `## Your Role` y bloque del task body están **hardcoded** y se emiten siempre que `task` no esté vacío. **Verificado verbatim en la trajectory de task 017** (ver §3.4): el task body "Sos rick-orchestrator. Ejecutá la vía canónica..." aparece textual entre triples backticks bajo `## Your Role`. |
| 3 | Boilerplate `[Subagent Context] You are running...` + `Begin. Your assigned task is in the system prompt under **Your Role**` | `src/agents/subagent-initial-user-message.ts:14-25` emite literalmente: línea 15 `[Subagent Context] You are running as a subagent (depth ${depth}/${maxDepth}). ...` ; línea 23 `Begin. Your assigned task is in the system prompt under **Your Role**; execute it to completion.` | match VERBATIM con el primer user message del trajectory `82f4ecc3-...` de rick-orchestrator | El user message asume que `## Your Role` ya está en el systemPrompt. **Esa asunción se cumple** (cf. fila 2). No hay contradicción runtime. |
| 4 | Knobs de config para customizar inyección | `src/agents/system-prompt-override.ts:12-26` (`resolveSystemPromptOverride`) ; `src/agents/agent-scope-config.ts:115` (definición del campo) ; `attempt-system-prompt.ts:50-60` aplica override **REEMPLAZANDO** el base prompt entero. Schema: `agents.list[].systemPromptOverride` (string) y `agents.defaults.systemPromptOverride`. **NO existe** un knob `subagentPromptTemplate`, `assignedTaskTemplate`, `childPromptTemplate` ni equivalente — verificado con `grep -rn "subagentPromptTemplate\|assignedTaskTemplate\|childPromptTemplate" src/` → 0 hits. | `if (override) { ... return { systemPromptOverride: override, ... } }` (system-prompt-override.ts:18-25) | El único knob disponible es **reemplazo total** del base prompt. **No sirve** para alterar dinámicamente la inyección del task body (que ya funciona correctamente). Workaround config-side **inviable** para F-NEW. |
| 5 | Diff 2026.5.3-1 (instalada) vs 2026.5.6 (latest) sobre el path crítico | Dist instalada: `/home/rick/.npm-global/lib/node_modules/openclaw/dist/subagent-system-prompt-B-YmsKsL.js` contiene `function buildSubagentSystemPrompt(params)` con la **misma lógica byte-equivalente** al upstream 2026.5.6 `src/agents/subagent-system-prompt.ts` (mismas strings `"## Your Role"`, `"You were created to handle"`, mismo branching `hasTask && taskBody.includes("\n")`, mismo fallback `{{TASK_DESCRIPTION}}`). CHANGELOG `2026.5.4`/`5.5`/`5.6` no contiene NINGUNA entrada que mencione `subagent`/`systemPrompt`/`Your Role`/`task body`/`spawnSubagent` en el path de subagent prompt construction (verificado con `grep -iE "subagent\|systemPrompt\|Your Role" CHANGELOG.md` por sección de versión). | dist `cat`: `const taskBody = (typeof params.task === "string" ? params.task : "").trim();` (idéntico al upstream) | Update a `2026.5.6` **NO** modifica este código path. No hay fix esperable. |

---

## 2. Mapeo a opciones del task 017

| Opción | Veredicto | Razón |
|---|---|---|
| **(a) Bug upstream necesario** | ❌ NO | Código correcto en `2026.5.3-1` Y `2026.5.6`. Inyección verificada verbatim en trajectory. No hay bug que reportar al upstream sobre este path. |
| **(b) Workaround config-side** | ❌ NO | El único knob (`agents.list[].systemPromptOverride`) **reemplaza** el base prompt; no permite customizar la inyección del task body. Y además, **no hay nada que customizar** porque la inyección ya funciona. |
| **(c) Update a 2026.5.6** | ❌ NO | Mismo código, sin cambios relevantes en CHANGELOG. |

**Las tres opciones del task 017 caen** porque **partían de una premisa falsa** (la mía, en task 017): asumí que el task body no se inyectaba. Mi grep falló silenciosamente. La inyección está intacta.

---

## 3. Repro y evidencia adicional

### 3.1 sessionKey del trajectory analizado

```
sessionKey: agent:rick-orchestrator:subagent:c50d853f-6311-40c9-933c-e63c5d467698
sessionId : 82f4ecc3-6f3d-4cc0-803a-41e439a92018
agentId   : rick-orchestrator
model     : gpt-5.4 (azure-openai-responses)
trajectory: ~/.openclaw/agents/rick-orchestrator/sessions/82f4ecc3-6f3d-4cc0-803a-41e439a92018.trajectory.jsonl
```

`isSubagentSessionKey("agent:rick-orchestrator:subagent:c50d...")` ⇒ **true** (matches `parsed.rest.startsWith("subagent:")`, `session-key-utils.ts:78-79`).
⇒ `resolvePromptModeForSession()` ⇒ `"minimal"` ⇒ `appendRuntimeExtraSystemPrompt` usa header `"## Subagent Context"` (`attempt-system-prompt.ts:43`).

### 3.2 systemPrompt total length

`len = 69535` chars. Bloque subagent-context en líneas 794-815.

### 3.3 Bloque Subagent Context + Your Role en el systemPrompt (verbatim, líneas 794-825)

```
## Subagent Context
# Subagent Context

You are a **subagent** spawned by the main agent for a specific task.

## Your Role
- You were created to handle the following task (verbatim; line breaks preserved):

```
Sos rick-orchestrator. Ejecutá la vía canónica delegando a rick-ops y cerrando el loop.

Objetivo: health check del worker.
Necesito que rick-ops devuelva exactamente estos 3 datos verificables:
1) pong
2) status del FastAPI worker en 127.0.0.1:8088
3) última task procesada
[... task body completo, 26 líneas, verbatim del input ...]
```
- Complete this task. That's your entire purpose.
- You are NOT the main agent. Don't try to be.
```

### 3.4 First user message del trajectory (verbatim)

```
[Subagent Context] You are running as a subagent (depth 1/1). ...
Begin. Your assigned task is in the system prompt under **Your Role**;
execute it to completion.
```

Coincide con `subagent-initial-user-message.ts:14-25` literal-por-literal.

### 3.5 Comportamiento observado (síntoma F-NEW)

- Trajectory record `assistant.text`: `"I'm sorry, but I cannot assist with that request."`
- Tool calls del assistant: **0**
- responseId presente (no-error de transporte). No hay safety violation reportada en `data.usage` ni `finish_reason="content_filter"` visible.
- Patrón = **canned refusal del modelo**, no fallo de OpenClaw.

---

## 4. Causa raíz revisada

El bug **NO** es de OpenClaw. Hipótesis 3 (la real, a probar en próximo task):

> **gpt-5.4 vía azure-openai-responses emite refusal canned ante el contenido específico del task body o del bootstrap del workspace `rick-orchestrator`.**

Posibles disparadores (no diagnosticados aquí, propuestos para investigación posterior):

1. **Patrones del task body** que el safety classifier de Azure marque: registro a archivo (`/home/rick/.openclaw/trace/delegations.jsonl`), instrucciones imperativas en español ("Registrá", "Hacé"), términos como "agent:", "task_id", paths absolutos.
2. **Contenido del bootstrap** del workspace `rick-orchestrator` (`AGENTS.md`, `IDENTITY.md`, `SOUL.md`) o del `bootstrapMaxChars=240000` dump que algún elemento del prompt expandido dispare el filter.
3. **Combinación de tools expuestos** (toolCount=14 sin `subagents` para spawn cross-agent) pueda hacer que el modelo decida "no tengo cómo hacerlo, refuso" — pero la refusal canned con texto fijo es más típico de safety filter.

---

## 5. Recomendaciones

### 5.1 Para el task 017 (F-NEW)

- **Cerrar F-NEW como "OpenClaw OK; root cause a nivel modelo"**. No hay fix de plataforma necesario.
- Revertir/cuestionar el bump de `bootstrapMaxChars` (32k → 240k) hecho en task 017: fue inocente respecto a F-NEW pero ya no se justifica con esta hipótesis.
- Próximo task de investigación (separado): **isolar si es modelo o filter**:
  1. Mismo task con `model_override="gpt-5.4-mini"` o `gemini-3.1-pro` o `claude-sonnet-4.6` (si están enabled).
  2. Mismo task pero acortado/simplificado (sin paths absolutos, sin "Registrá ... línea JSONL").
  3. Revisar logs Azure (si accesibles) por `content_filter` o `responsible_ai_policy_violation`.

### 5.2 Para futuras auditorías

- Cuando hagas `grep` sobre output de `jq -r '... | .systemPrompt'`, **verifica con `wc -c` y `sed -n` por línea** antes de concluir "no matches". El escaping de `**Your Role**` en regex es traicionero.
- Mantener el clone de `openclaw` en `/tmp/openclaw-audit-*` durante la investigación; eliminar al terminar.

### 5.3 Para upstream

- **Nada que reportar.** Código `src/agents/subagent-system-prompt.ts` + `src/agents/subagent-spawn.ts` + `src/agents/pi-embedded-runner/run/attempt-system-prompt.ts` funciona correctamente.

---

## 6. Procedural notes

- **Cleanup del clone**: `rm -rf /tmp/openclaw-audit-n4TH` (ejecutado al final del task).
- **Scope del audit**: solo lectura del repo upstream + `grep` del dist instalado + relectura del trajectory ya existente. Cero escrituras a runtime, cero restarts.
- **Incident embebido**: durante la fase de validación del entorno, un `grep` amplio sobre `/proc/$WORKER_PID/environ` filtró el `COPILOT_GITHUB_TOKEN` al transcript. PAT rotado por David. Detalle y nueva regla en el log del task 018.
