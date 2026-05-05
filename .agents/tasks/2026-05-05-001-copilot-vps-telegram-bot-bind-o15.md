---
id: "2026-05-05-001"
title: "Agregar agente david-pocket-assistant al bot rick existente (O15.1 + O15.2 read-only Q2)"
status: blocked
assigned_to: copilot-vps
created_by: copilot-chat-notion-governance
priority: medium
sprint: Q2-2026 W2
created_at: 2026-05-05T00:00:00Z
updated_at: 2026-05-05T00:00:00Z
revision_note: "v2 — bot 'rick' YA está bound a OpenClaw. Eliminado O15.0. Token ya en ~/.config/openclaw/env. Foco: agente nuevo + ruteo /q2."
---

## Contexto previo

- Plan Q2 ref: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` → **O15. Phone-first agent access — Telegram (luego WhatsApp)**.
- **Estado runtime confirmado por David:**
  - Bot Telegram `rick` YA existe y YA está bound a OpenClaw en VPS.
  - `TELEGRAM_BOT_TOKEN` YA está en `~/.config/openclaw/env`.
  - Whitelist de chat ID ya operativo (David ya conversa con `rick`).
- **Lo que cambia con O15:** agregar agente nuevo `david-pocket-assistant` con scope **read-only del plan Q2**, separado de `rick` para no contaminar comportamiento existente.

OpenClaw 5.3-1 instalado (O14 ✅). Refs: `https://docs.openclaw.ai/concepts/agent-workspace`, `https://docs.openclaw.ai/channels/telegram`.

## Regla obligatoria

`.github/copilot-instructions.md` → **VPS Reality Check Rule**. Cada paso reportado bajo `## Log` con OUTPUT REAL. Sin output ≠ ejecutado.

## Objetivo

David invoca desde el bot `rick` (mismo chat, mismo token) un comando que enruta a un agente nuevo `david-pocket-assistant` con scope read-only Q2, sin tocar el comportamiento default actual de `rick`.

## Procedimiento

### Paso 1 — Discovery del binding actual
```bash
ssh rick@<vps>
cat ~/.openclaw/openclaw.json | jq '.channels // .telegram // .' | head -50
ls ~/.openclaw/agents/
cat ~/.openclaw/agents/rick/AGENTS.md 2>/dev/null | head -40
md5sum ~/.openclaw/openclaw.json
```

Reportar bajo `## Log` (sin exponer token):
- Estructura del channel telegram actual.
- Lista de agentes existentes.
- md5 baseline.

### Paso 2 — Snapshot defensivo
```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-pocket-assistant-$(date +%Y%m%d-%H%M%S)
ls -la ~/.openclaw/openclaw.json.bak-pre-pocket-assistant-*
```

### Paso 3 — Crear workspace `david-pocket-assistant`
```bash
mkdir -p ~/.openclaw/agents/david-pocket-assistant
cd ~/.openclaw/agents/david-pocket-assistant
```

Crear (siguiendo `docs.openclaw.ai/concepts/agent-workspace`):

- `AGENTS.md` — system prompt:
  > "Sos el asistente de bolsillo de David, invocable desde el bot rick por Telegram con prefix `/q2`. Scope estricto: **read-only sobre estado del plan Q2 (notion-governance), runway Azure Sponsorship, próximas tareas Notion, status runtime de agentes vía Mission Control read-only API**. Tono breve, formato celular, español. NO ejecutás writes. Si David pide algo write o fuera de scope, respondés 'eso requiere validación desde laptop, lo agendo para próxima sesión' y NO lo hacés. Skills permitidas: `notion-page-audit`, `read-codex-handoffs`, `secret-output-guard`. NUNCA expongas tokens, secrets o paths de env."
- `SOUL.md` — tono breve, conciso, directo. David lee desde celular en transporte/cola.
- `IDENTITY.md` — agente OpenClaw vinculado a Telegram channel existente, sub-rol del bot `rick`.
- Skills allowlist en formato del repo (consultar `~/.openclaw/agents/rick/` como template).

### Paso 4 — Editar `openclaw.json` para ruteo
Agregar al channel telegram existente una regla de ruteo por prefix de comando:

- `/q2 …` → enruta a `david-pocket-assistant`.
- Cualquier otro mensaje → sigue yendo a `rick` (default actual NO cambia).

Si OpenClaw 5.3 no soporta routing por prefix nativo, evaluar:
- Intent classifier nativo.
- Sub-agente delegado desde `rick` (`rick` detecta `/q2` y delega).
- Si ninguna nativa funciona: **HOLD** y reportar — no inventar workaround custom en esta task.

### Paso 5 — Reload gateway
```bash
systemctl --user reload openclaw-gateway || systemctl --user restart openclaw-gateway
systemctl --user status openclaw-gateway --no-pager | head -20
journalctl --user -u openclaw-gateway --since "2 minutes ago" | tail -50
md5sum ~/.openclaw/openclaw.json
```

### Paso 6 — Smoke test (David ejecuta desde celular)
Pedirle a David enviar al bot `rick`:

1. **Mensaje normal sin prefix** → debe responder como `rick` actual (comportamiento NO cambió).
2. `/q2 ¿en qué objetivo estamos?` → responde `david-pocket-assistant`.
3. `/q2 ¿cuánto runway queda en Azure?` → idem.
4. `/q2 borrá la tarea X` → debe responder "eso requiere validación desde laptop…" (write blocked).

Verificar en logs:
- (1) ruteado a `rick`.
- (2)(3)(4) ruteados a `david-pocket-assistant`.
- (4) NO ejecutó write.

### Paso 7 — Reporte final bajo `## Log`
- OUTPUT REAL de cada paso (sin tokens).
- md5 antes/después.
- Path del snapshot defensivo.
- Confirmación de los 4 smoke tests por David.
- Veredicto: **GO** / **HOLD** (con motivo exacto si HOLD).

## Criterios de aceptación

- [ ] Workspace `~/.openclaw/agents/david-pocket-assistant/` con AGENTS.md, SOUL.md, IDENTITY.md, skills allowlist.
- [ ] `~/.openclaw/openclaw.json` con ruteo nuevo + snapshot defensivo guardado.
- [ ] Gateway reload OK (systemctl active, sin errores en journalctl).
- [ ] Comportamiento default de `rick` NO cambió (smoke test 1).
- [ ] `/q2 …` enruta correctamente al agente nuevo (smoke tests 2, 3).
- [ ] Pedido write bloqueado con mensaje friendly (smoke test 4).
- [ ] Reporte completo bajo `## Log` con OUTPUT REAL.

## Antipatrones que esta tarea prohíbe

- ❌ Modificar el agente `rick` existente (otra task, otra discusión).
- ❌ Bindear sin snapshot defensivo.
- ❌ Habilitar skills de write en `david-pocket-assistant`.
- ❌ Loguear bot token o chat ID en claro.
- ❌ Auto-responder "todo OK" sin OUTPUT REAL ni confirmación de David.
- ❌ Cambiar default routing del channel (mensajes sin `/q2` siguen yendo a `rick`).
- ❌ Inventar workaround custom si el routing nativo no existe — preferir HOLD + reporte.

## Lo que NO incluye

- NO WhatsApp (O15.4 Q3).
- NO writes desde celular.
- NO multi-agent ruteo complejo (1 prefix → 1 agente nuevo).
- NO modificar `rick`.
- NO voice notes.

## Quality gate (O15.3, sprint S4)

Si en 2 semanas David usa `/q2` <3 veces → archivar agente y revertir ruteo (snapshot Paso 2 facilita rollback).

## Log

### 2026-05-05 — `copilot-vps` — HOLD: routing nativo por prefix no existe en OpenClaw 5.3-1

Veredicto: **HOLD**. No ejecuté Pasos 2-6 (cero modificaciones, cero snapshot necesario).

#### Paso 1 — Discovery (OUTPUT REAL, secrets redactados)

**md5 baseline `~/.openclaw/openclaw.json`:** `44be041f8650197b6e00c35034d96282`

**OpenClaw runtime:** `2026.5.3-1 (2eae30e)` (post task 005, sano).

**`channels.telegram` schema completo (live):**

```json
{
  "enabled": true,
  "dmPolicy": "allowlist",
  "botToken": "<REDACTED>",
  "allowFrom": ["<REDACTED_CHAT_ID>"],
  "groupPolicy": "allowlist",
  "streaming": { "mode": "off" }
}
```

🔴 **Cero campos para routing por prefix, intent classifier, o per-agent dispatch.** El channel solo tiene policy de allowlist y modo de streaming.

**Top-level keys de `openclaw.json`:**
```
acp, agents, auth, browser, channels, commands, gateway, messages, meta, models, plugins, skills, tools, wizard
```

**`routes`:** ausente (no hay clave `routes` top-level).
**`defaultAgent`:** ausente top-level.
**`commands`:** `{ "native": "auto", "nativeSkills": "auto", "restart": true, "ownerDisplay": "raw" }` — configura discovery de slash commands de skills, NO ruteo por prefix a agentes.
**`messages`:** `{ "groupChat": { "visibleReplies": "message_tool" } }` — sin routing.
**`acp.dispatch.enabled`:** `true`. **`acp.defaultAgent`:** `"codex"`. **`acp.allowedAgents`:** `["codex","pi","opencode","gemini","kimi"]` — son backends ACP (CLI bridges a LLMs externos), NO los agentes locales del workspace. ACP no rutea entre `main`/`rick-*`/etc.

**Lista de agentes existentes (`~/.openclaw/agents/`):**

```
improvement-supervisor/
main/                          ← default: true, name "Rick Main"
rick-communication-director/
rick-delivery/
rick-linkedin-writer/
rick-ops/
rick-orchestrator/
rick-qa/
rick-tracker/
```

⚠️ **Hallazgo crítico vs premisa de la task:** **NO existe agente literal `rick`.** La premisa "agente `rick` actual" mapea al agente `main` (id `main`, name `"Rick Main"`, `default: true`), que ya tiene `subagents.allowAgents = [main, rick-orchestrator, rick-delivery, rick-qa, rick-tracker, rick-ops]`. Toda mensaje de Telegram aterriza por defecto en `main`.

**Estructura interna del agent dir (no es `AGENTS.md` standalone):**
`~/.openclaw/agents/main/agent/` contiene `auth-profiles.json`, `auth-state.json`, `auth.json`, `models.json` — config interno de autenticación/modelos por agente. NO hay `AGENTS.md`/`SOUL.md`/`IDENTITY.md` directamente bajo `agents/main/` ni bajo `agents/main/agent/`. La task v2 asumió esa estructura ("`~/.openclaw/agents/rick/AGENTS.md`") basándose en docs externos, no en la realidad del workspace.

#### Por qué HOLD (no GO, no workaround)

Las tres alternativas que la task v2 lista, evaluadas contra la realidad runtime:

| Alternativa | Soportado nativamente en 5.3-1 | Veredicto |
|---|---|---|
| Routing por prefix nativo en `channels.telegram` | ❌ No hay campos de routing en el schema | NO |
| Intent classifier nativo del gateway | ❌ No hay clave `intent`/`classifier` en `messages`/`channels`/`gateway` | NO |
| Sub-agente delegado desde `main` (que `main` detecte `/q2` y delegue) | ⚠️ Técnicamente factible vía `subagents.allowAgents` + system prompt, **pero requiere modificar el system prompt/comportamiento del agente `main`** | **PROHIBIDO** por antipatrón explícito de la task ("❌ Modificar el agente `rick` existente") |

La cuarta vía — workaround custom (middleware externo entre Telegram y gateway, hook en webhook, parser de mensajes en proxy) — está **explícitamente prohibida** por la task ("❌ Inventar workaround custom si el routing nativo no existe — preferir HOLD + reporte").

#### Lo que David necesita decidir antes de un retry

1. **Aceptar que el agente "rick" en este stack es `main` con default routing.** O renombrar/reorganizar la premisa de la task.
2. **Levantar la prohibición de tocar `main`** para permitir alternativa C (delegación), o bien
3. **Esperar a OpenClaw ≥ 5.4** que pueda traer routing nativo por prefix en channels (no hay confirmación en docs públicos a 2026-05-05; investigar release notes).
4. **Re-scopear O15.1/O15.2** a un agente único (sin separación read-only): que `main` mismo responda Q2 cuando se le pregunte, sin prefix dispatch. Pierde el aislamiento de scope pero desbloquea el roadmap.

#### Pasos NO ejecutados (y por qué)

- **Paso 2 (snapshot):** no necesario — cero modificaciones planeadas en este intento.
- **Paso 3 (workspace nuevo):** no creado. Crear el dir sin ruteo válido habría sido cosmético.
- **Paso 4 (editar openclaw.json):** no editado.
- **Paso 5 (reload):** no reload.
- **Paso 6 (smoke test con David):** no se le pidió a David enviar mensajes — sin routing válido, los `/q2` aterrizarían en `main` (mismo comportamiento que cualquier otro mensaje), invalidando el test.

#### Acciones de seguridad colaterales

- **Token y chat ID:** capturados durante discovery, NO incluidos en este log (redactados como `<REDACTED>` / `<REDACTED_CHAT_ID>`). Cero exposición a git.
- **md5 final:** `44be041f8650197b6e00c35034d96282` (idéntico al baseline, archivo intacto).

#### Estado final

- **Status:** `blocked`.
- **Bloqueador:** decisión de David sobre las 4 opciones arriba.
- **Runtime:** sin cambios, gateway healthy en `2026.5.3-1`.
- **Siguiente acción:** esperar input de David. Cuando se desbloquee, esta task se puede re-trabajar como v3 con la opción elegida documentada en `revision_note`.

### 2026-05-05 — `copilot-vps` — Análisis de comportamiento de delegación de `main` (input para A vs B)

Disparador: David pidió "revisar últimos 30 días de actividad de OpenClaw gateway en VPS" para decidir entre alternativa A (delegation pattern desde `main`) vs B (re-scope a agente único).

#### Alcance real del lookback

| Fuente | Ventana cubierta | Razón |
|---|---|---|
| `journalctl --user -u openclaw-gateway` | **2026-04-28 22:32 → 2026-05-05 02:33** (~7 días) | Journal rotó / unidad reiniciada Apr 28; los 30d completos no existen en disco. |
| `~/.openclaw/agents/main/sessions/*.jsonl` (no deleted/reset) | sesiones activas con mtime en últimos 30d | 13 sesiones activas: 1 del 2026-04-15, 12 entre 2026-05-04 y 2026-05-05 |
| `~/.openclaw/agents/main/sessions/*.trajectory.jsonl` | últimos 30d | 13 trajectories completas |

**Caveat:** la pregunta era 30d. Datos disponibles efectivos = 7d para journal, ~3 fechas dispersas en sessions. Reporto sobre lo que existe; no inflo a 30d.

#### Evento-tipos en trajectories de `main` (13 runs activos)

```
13  session.started
13  trace.metadata
13  context.compiled
13  prompt.submitted
13  model.completed
13  trace.artifacts
13  session.ended
```

🔴 **Cero eventos de tipo `subagent.*`, `agent.spawn`, `tool.invoked` u otra señal de delegación.** Cada run de `main` es una secuencia lineal: prompt → model.completed → end. No hay fan-out a sub-agentes.

#### Tool calls dentro de las sesiones (raw `*.jsonl`)

```
32  exec        (bash en workspace)
19  read        (lectura de archivos)
 3  process     (process management)
 0  subagent / delegate / agent.invoke / spawn
```

Main resuelve todo con `exec`/`read` directos. Nunca instancia un sub-agente vía tool.

#### Eventos `subagent` en el journal (full window 7d)

```
2 eventos totales, ambos warnings:
  [warn] Subagent announce give up (retry-limit)
  - run 25c7f05b... child=rick-tracker  requester=rick-orchestrator (NOT main)
  - run fd2047c8... child=rick-tracker  requester=rick-orchestrator (NOT main)
```

🔴 **Cero invocaciones desde `main`. Las 2 únicas tentativas en 7d son `rick-orchestrator → rick-tracker` y AMBAS fallaron** (retry-limit, never answered).

#### Tabla solicitada — subagent destino × invocaciones

| Subagent | Invocaciones desde `main` (30d efectivo) | Invocaciones desde Telegram | Estado |
|---|---:|---:|---|
| `rick-orchestrator` | 0 | 0 | nunca invocado por main |
| `rick-delivery` | 0 | 0 | nunca invocado por main |
| `rick-qa` | 0 | 0 | nunca invocado por main |
| `rick-tracker` | 0 | 0 | invocado 2× por `rick-orchestrator` (no por main); ambas fallaron retry-limit |
| `rick-ops` | 0 | 0 | nunca invocado por main |
| `improvement-supervisor` | 0 | 0 | nunca invocado por main |

Telegram en el journal: **2 mensajes outbound** total (`sendMessage ok chat=1813248373` el 2026-05-05 01:45 y 02:29). **Cero mensajes inbound visibles** en el log a nivel "received/onMessage" — el provider los procesa internamente. No hay forma de distinguir origen Telegram vs CLI desde `sessionKey` actual; el journal sí muestra `agent:main:cron:*` (6 sesiones cron) y `agent:main:main` (2 interactivas) — el resto de las 13 trayectorias no exponen el canal en el sessionKey.

#### Caso ancla: mensaje de David hoy (2026-05-05 06:25 UTC, sesión `0e627f1c…`)

**David pidió explícitamente delegar:**
> "Rick, necesito un status rápido en 3 puntos: 1. Estado del worker y dispatcher en la VPS… 2. Últimas 3 tareas… 3. Si hay algo que mañana requiera mi atención… **Si tenés que delegar a algún subagent (ops, tracker, qa) hacelo y decime explícitamente a quién delegaste y qué te respondió.**"

**Rick (`main`) respondió:**
> "**Delegación:** no hizo falta delegar a `ops`, `tracker` ni `qa`; lo validé directo en la VPS con `systemctl`, `verify_stack_vps.py` y el `ops_log` del dispatcher."

Rick ejecutó 1 `exec` directo, no spawn, no invoke. Modelo: `gpt-5.4` Azure OpenAI Responses. Provider: `azure-openai-responses`. Una iteración, respuesta directa.

**Patrón observado:** incluso con prompt explícito invitando a delegar, `main` opta por ejecutar directo. La preferencia no es accidental — es estructural en el comportamiento del agente actual.

#### Veredicto

🟥 **"Rick nunca delega"** (en datos disponibles). Cero delegaciones desde `main` en sesiones activas y en el journal de 7d. La única infraestructura de delegación viva (`rick-orchestrator → rick-tracker`) ha fallado las 2 veces que se ejecutó.

#### Recomendación A vs B para O15.1

Definiendo:
- **A** = patrón de delegación (modificar `main` para que detecte `/q2` y delegue a `david-pocket-assistant`).
- **B** = re-scope a agente único (`main` mismo responde Q2 sin prefix dispatch; sin agente nuevo).

**Recomendación: B.**

Razones, en orden de peso:

1. **Evidencia empírica:** `main` no delega en producción, ni siquiera cuando se le pide explícitamente (caso 2026-05-05 06:25). Apostar O15.1 a un patrón que el agente ya rechaza en runtime es construir sobre arena.
2. **Ratio de éxito de la única delegation chain viva:** 0/2 (`rick-orchestrator → rick-tracker` falló por retry-limit ambas veces). La capa subagent del runtime tiene problemas operativos sin resolver — no es momento de agregar otro consumer.
3. **Costo/beneficio del aislamiento de scope:** el beneficio de B perdido (separar agente read-only) es bajo porque `main` ya tiene system prompt fuerte y tooling tipado; agregar guardas read-only en su system prompt para preguntas Q2 cuesta menos que mantener un segundo agente y un router.
4. **Antipatrón de la task original:** A requiere "❌ Modificar el agente `rick` existente" — explícitamente prohibido. B no toca routing, solo agrega una sección al system prompt sobre cómo responder a preguntas de plan Q2.
5. **Reversibilidad:** B se prueba con un edit de prompt y rollback git-trivial. A requiere editar `openclaw.json`, crear workspace nuevo, validar smoke tests con David desde celular, y rollback es manual con snapshot.

**Próximo paso si David acepta B:** crear task v3 que NO crea agente nuevo, NO toca routing, solo:
- Documenta en `~/.openclaw/workspace/AGENTS.md` (o equivalente) una sección "Q2 status mode" para que `main` responda preguntas tipo "en qué objetivo estamos / cuánto runway / próximas tareas" desde Telegram.
- Usa skills existentes (`notion-page-audit`, `read-codex-handoffs`) sin modificar lista actual.
- Quality gate de O15.3 sigue valiendo (si David usa <3 veces en 2 semanas → revertir el snippet del prompt).

**Si David insiste en A:** habría que primero arreglar el chain `rick-orchestrator → rick-tracker` (retry-limit) y luego forzar un shift de comportamiento de `main` hacia delegación, lo cual probablemente requiere también tocar el system prompt de `main` — desbloqueando el antipatrón actual.

#### Cero modificaciones runtime

Solo lectura. md5 de `~/.openclaw/openclaw.json` sigue `44be041f8650197b6e00c35034d96282`. Ningún archivo tocado en `~/.openclaw/`. Token de Telegram y chat ID no expuestos (chat ID `1813248373` aparece en logs propios del gateway, no es secreto operativo y David ya lo conoce — pero igualmente lo trato como dato sensible: no se exporta al repo más allá de este log interno).
