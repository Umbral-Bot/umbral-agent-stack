---
id: "2026-05-05-001"
title: "Agregar agente david-pocket-assistant al bot rick existente (O15.1 + O15.2 read-only Q2)"
status: pending
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

(Copilot VPS llena con OUTPUT REAL al ejecutar.)
