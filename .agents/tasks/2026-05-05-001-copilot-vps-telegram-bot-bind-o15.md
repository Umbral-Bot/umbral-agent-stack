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
