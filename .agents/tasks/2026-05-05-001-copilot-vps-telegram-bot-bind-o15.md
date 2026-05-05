---
id: "2026-05-05-001"
title: "Bind Telegram bot a OpenClaw + crear agente david-pocket-assistant (O15.0 + O15.1 + O15.2)"
status: pending
assigned_to: copilot-vps
created_by: copilot-chat-notion-governance
priority: medium
sprint: Q2-2026 W2
created_at: 2026-05-05T00:00:00Z
updated_at: 2026-05-05T00:00:00Z
---

## Contexto previo

- Plan Q2 referencia: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` → **O15. Phone-first agent access — Telegram (luego WhatsApp)** (NUEVO 2026-05-05).
- David quiere retomar consulta a agentes desde celular. Ventana C7 (Copilot Pro+ vence 1-jun) presiona validar UX antes que se cierre.
- OpenClaw 5.3-1 ya instalado en VPS (O14 ✅). Channels nativos disponibles.
- Refs OpenClaw: `https://docs.openclaw.ai/channels/telegram`, `https://docs.openclaw.ai/concepts/agent-workspace`.

## Regla obligatoria

`.github/copilot-instructions.md` → sección **"VPS Reality Check Rule"**. Cada paso reportado en este archivo bajo `## Log` con OUTPUT REAL de los comandos. Sin output ≠ ejecutado.

## Pre-requisito humano (David)

Antes de que Copilot VPS arranque, David debe:

1. Abrir Telegram → chat con `@BotFather`.
2. `/newbot` → nombre sugerido: `David Pocket Assistant` → username sugerido: `umbral_david_pocket_bot` (o variante disponible).
3. **Copiar el bot token** que entrega BotFather (formato `123456789:ABC-DEF...`).
4. Abrir Telegram → chat con `@userinfobot` → `/start` → **copiar el chat ID numérico de David**.
5. Pegar ambos valores cifrados a Copilot VPS por canal seguro (NO en este archivo, NO en commit, NO en logs).

> ⚠️ Aplica `secret-output-guard` skill. El token NUNCA se commitea ni se loguea en claro. Si en algún momento aparece en pantalla, regenerarlo en BotFather con `/revoke` antes de continuar.

## Objetivo

Dejar operativo desde el celular de David un bot Telegram (`@umbral_david_pocket_bot` o alias asignado) que:

1. Solo acepta mensajes del chat ID whitelisted de David (fail-closed para cualquier otro).
2. Responde como agente `david-pocket-assistant` con scope read-only:
   - Lectura del plan Q2 (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`).
   - Lectura de Mejora Continua / próximas tareas vía Notion MCP read-only.
   - Status runtime básico (Mission Control read-only `/health`, `/quotas`).
3. NO ejecuta writes en Q2 (próximos pasos: explícitos por David).
4. Modelo: Claude Sonnet vía OpenClaw, con `model-failover` nativo a GPT-5 si cuota Claude crítica.

## Procedimiento

### Paso 1 — Recibir secrets de David por canal seguro
- Confirmar recepción de: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_DAVID_CHAT_ID`.
- NO loguearlos en claro. NO escribirlos en este archivo.

### Paso 2 — Inyectar secrets en env de OpenClaw
```bash
ssh rick@<vps>
# Editar SOLO con permisos 600
sudo -u rick bash -c 'cat >> ~/.config/openclaw/env <<EOF
TELEGRAM_BOT_TOKEN=<...>
TELEGRAM_DAVID_CHAT_ID=<...>
EOF'
chmod 600 ~/.config/openclaw/env
ls -la ~/.config/openclaw/env  # verificar 600 rick:rick
```

### Paso 3 — Crear workspace `david-pocket-assistant`
```bash
mkdir -p ~/.openclaw/agents/david-pocket-assistant
cd ~/.openclaw/agents/david-pocket-assistant
```

Crear archivos mínimos siguiendo `docs.openclaw.ai/concepts/agent-workspace`:

- `AGENTS.md` — system prompt focalizado: "Asistente personal de bolsillo de David. Responde consultas read-only sobre estado del plan Q2, runway Azure, próximas tareas Notion, status runtime de agentes. NO ejecuta writes ni cambios. Si David pide algo write, responde 'esto requiere validación desde laptop, agendado para próxima sesión'."
- `SOUL.md` — tono breve, conciso (formato celular), español.
- `IDENTITY.md` — identidad: agente OpenClaw vinculado a Telegram, scope 1-user.
- Skills allowlist (vía config): `[notion-page-audit, read-codex-handoffs, secret-output-guard]` + Mission Control read-only API.

### Paso 4 — Bind canal Telegram en `~/.openclaw/openclaw.json`
Snapshot defensivo PRIMERO:
```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-telegram-bind-$(date +%Y%m%d-%H%M%S)
md5sum ~/.openclaw/openclaw.json
```

Editar `openclaw.json` agregando channel telegram bound a agente `david-pocket-assistant` con scope chat ID whitelist. Seguir spec exacta de `docs.openclaw.ai/channels/telegram` (consultar antes de editar).

Reload gateway:
```bash
systemctl --user reload openclaw-gateway || systemctl --user restart openclaw-gateway
systemctl --user status openclaw-gateway --no-pager | head -20
journalctl --user -u openclaw-gateway --since "2 minutes ago" | tail -50
```

### Paso 5 — Smoke test
- Pedir a David que envíe "hola" desde su Telegram.
- Verificar log: `journalctl --user -u openclaw-gateway -f` muestra mensaje recibido + chat_id correcto + respuesta enviada.
- Pedir a David que envíe un mensaje desde OTRO chat (si tiene acceso) → debe ser **ignorado** (whitelist fail-closed).
- Pedir a David 3 consultas reales:
  1. "¿en qué objetivo estamos del plan Q2?"
  2. "¿cuánto runway queda en Azure Sponsorship?"
  3. "¿hay tareas Notion vencidas hoy?"

### Paso 6 — Health check
```bash
openclaw status --all | grep -i telegram
openclaw channels list  # si existe el subcomando
```

### Paso 7 — Reporte final en este archivo bajo `## Log`
- OUTPUT REAL de cada paso (sin secrets).
- Confirmación de los 3 smoke tests exitosos.
- md5 del `openclaw.json` antes/después.
- Path del snapshot defensivo.
- Veredicto: **GO** (operativo) / **HOLD** (bloqueado, indicar por qué).

## Criterios de aceptación

- [ ] `~/.config/openclaw/env` contiene las 2 vars con permisos 600 rick:rick (verificado por `ls -la`, NO mostrando los valores).
- [ ] Workspace `~/.openclaw/agents/david-pocket-assistant/` con los 3 archivos mínimos.
- [ ] `~/.openclaw/openclaw.json` con channel telegram bound + snapshot defensivo guardado.
- [ ] Gateway reload/restart exitoso (systemctl status active).
- [ ] David confirma recepción de respuesta a "hola" desde celular.
- [ ] Mensaje desde chat NO whitelisted ignorado (fail-closed).
- [ ] 3 consultas reales respondidas con sentido (no garantía de exactitud, sí de que el pipeline está vivo).
- [ ] Reporte completo bajo `## Log` con OUTPUT REAL.

## Antipatrones que esta tarea prohíbe

- ❌ Commitear el bot token o el chat ID a git (ni en este archivo, ni en ningún otro).
- ❌ Loguear secrets en claro en `journalctl` accesible.
- ❌ Bindear sin snapshot defensivo de `openclaw.json`.
- ❌ Saltarse el whitelist de chat ID ("luego lo arreglamos").
- ❌ Habilitar writes / skills de escritura en Q2 ("ya que estamos…").
- ❌ Auto-responder "todo OK" sin verificar OUTPUT REAL.

## Lo que NO incluye esta tarea (anti-scope-creep)

- NO WhatsApp (es O15.4 condicional Q3).
- NO Slack/Discord/Signal/Matrix.
- NO comandos write (read-only Q2).
- NO multi-agent ruteo (1 agente, no broker).
- NO voice notes / voicewake.
- NO compartir bot con terceros.

## Log

(Copilot VPS llena esta sección con OUTPUT REAL al ejecutar.)
