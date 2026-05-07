---
id: "2026-05-07-016"
title: "Copilot VPS — F-C rick-tracker→Vertex + Ola 1.5 smoke real (primera delegación end-to-end main→rick-ops)"
status: queued
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026
created_at: 2026-05-07T01:30:00-03:00
---

## Contexto previo

Esta tarea sigue al cierre de O15.1 (commits `314a5b3` + `6e4db38`). Combina dos follow-ups complementarios:

- **F-C**: alinear `rick-tracker.model.primary` runtime con modelo organizacional §5.3 (que manda Vertex Gemini para tracker; runtime tiene `azure-openai-responses/gpt-5.4`).
- **F-D / Ola 1.5**: ejecutar smoke real end-to-end de la mecánica de delegación implementada en O15.1 (que quedó deferred porque consume tokens en sesión productiva — pero ahora es turno explícito autorizado).

Antes de empezar:

1. `cd /home/rick/umbral-agent-stack && git pull origin main`.
2. Releer `.github/copilot-instructions.md` (VPS Reality Check Rule).
3. Releer el log de tu task previa: `.agents/tasks/2026-05-07-015-copilot-vps-o15-1-rick-ceo-fundamentos-ola1.md` — especialmente §6 follow-ups.

## Objetivo

Dos bloques en orden estricto:

### Bloque A — F-C: `rick-tracker.model.primary` → Vertex Gemini

Modelo §5.3 declara `rick-tracker` como "único en Vertex" (decisión de costo y latencia para trazabilidad ligera). Runtime actual lo tiene en `azure-openai-responses/gpt-5.4` (drift).

**Acciones:**
1. Backup defensivo `~/.openclaw/openclaw.json` con timestamp ISO.
2. Verificar en `agents.defaults.models` qué identificador exacto está disponible para Vertex Gemini Pro. Probable: `google-vertex/gemini-3.1-pro-preview` (mencionado en task previa). Si no existe ese exacto, usar el más cercano disponible y documentar la decisión.
3. `jq` edit de `.agents.list[] | select(.id=="rick-tracker") | .model.primary` al ID Vertex elegido.
4. Conservar `model.fallback` en su valor actual (NO tocar fallback chain — solo primary). Si no tiene fallback, agregar `azure-openai-responses/gpt-5.4` como fallback (degradación graceful si Vertex está caído).
5. Validar JSON: `jq . ~/.openclaw/openclaw.json > /dev/null`.
6. Reload o restart gateway (lo que aplique). Health check antes/después.
7. Verificar en runtime: `openclaw agents show rick-tracker` (o equivalente) confirma `model.primary` nuevo.

**Done report Bloque A:**
- Path backup + timestamp.
- ID Vertex exacto elegido + por qué (si no era el esperado).
- Diff `jq` del cambio.
- Health check pre/post.
- Output `openclaw agents show rick-tracker` confirmando.

### Bloque B — Ola 1.5: smoke real delegación end-to-end

Validar la mecánica prompt-driven implementada en O15.1 con UNA delegación trivial real, sin consumir tokens excesivos.

**Plan del smoke:**

1. **Disparar desde `main` (Rick CEO)** un mensaje de tipo: *"Necesito un health check rápido del worker. Delegá a rick-ops: que responda con (a) `pong`, (b) status del worker FastAPI 8088, (c) última task procesada. Registrá la delegación en `~/.openclaw/trace/delegations.jsonl` según el contrato §3.3 que está en mi IDENTITY.md v1.1."*
2. **Observar:**
   - ¿`main` decide delegar a `rick-orchestrator` (camino canónico) o directo a `rick-ops`? (Modelo §5.3 dice que canónicamente debería ser vía orchestrator, pero el prompt v1.1 deja margen para mono-gerencia directa. Documentar lo que pasa.)
   - ¿Aparece línea jsonl en `~/.openclaw/trace/delegations.jsonl` con format §3.3 válido?
   - ¿La gerencia `rick-ops` recibe + responde + cierra con `status: done`?
3. **Si la línea jsonl NO se escribe** (modelo no obedece la instrucción del prompt): es señal de que **necesitamos la skill `delegation-trace-writer`** ya en Ola 1, no en Ola 2. Documentar como F-A urgente.
4. **Si se escribe parcialmente** (e.g. `requested_by` correcto pero falta `task_id` o `status`): documentar gaps específicos.
5. **Si se escribe correctamente**: confirmar que el contrato funciona prompt-driven y F-A puede esperar a Ola 2.

**Tope de gasto:** máximo 3 turnos de modelo (1 disparo + 1-2 follow-ups si rick-ops pide aclaración). Si se va de 3 turnos, abortar y reportar como "smoke necesita skill custom para ser viable".

**Done report Bloque B:**
- Comando exacto usado para disparar (e.g. `openclaw agent main --message "..."` o equivalente).
- Path/timestamp/conversation-id de la sesión.
- Trace rutado: `main → ?` (orchestrator o directo a ops).
- Líneas jsonl producidas (cat completo, redactando datos sensibles si hay).
- Validación format §3.3: `jq -e` por línea.
- Veredicto: ¿prompt-driven viable Ola 1, o necesita `delegation-trace-writer` urgente?
- Gasto real (nº turnos + estimado de tokens si es visible).

## Procedimiento mínimo

```bash
# === Bloque A: F-C rick-tracker → Vertex ===
ssh rick@<vps>
cd ~/umbral-agent-stack && git pull origin main

TS=$(date +%Y%m%d-%H%M%S)
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-016-${TS}
echo "[backup] $(ls -la ~/.openclaw/openclaw.json.bak-pre-016-${TS})"

# Discover Vertex IDs disponibles
jq '.agents.defaults.models // .models // empty | keys' ~/.openclaw/openclaw.json
jq '.agents.list[] | select(.id=="rick-tracker") | .model' ~/.openclaw/openclaw.json
# Elegir ID Vertex apropiado (gemini-3.1-pro-preview u otro disponible)

# Edit (ajustar VERTEX_ID al exacto disponible)
VERTEX_ID="google-vertex/gemini-3.1-pro-preview"  # validar antes
jq --arg vid "$VERTEX_ID" \
  '(.agents.list[] | select(.id=="rick-tracker") | .model.primary) = $vid' \
  ~/.openclaw/openclaw.json > /tmp/openclaw-fc.json
diff ~/.openclaw/openclaw.json /tmp/openclaw-fc.json
# revisar diff; si OK:
mv /tmp/openclaw-fc.json ~/.openclaw/openclaw.json
jq . ~/.openclaw/openclaw.json > /dev/null && echo "JSON OK"

# Reload + health
systemctl --user reload openclaw-gateway || systemctl --user restart openclaw-gateway
sleep 2
curl -fsS http://127.0.0.1:18789/health && echo
curl -fsS http://127.0.0.1:8088/health | jq -c '{ok, version}'
systemctl --user is-active openclaw-gateway openclaw-dispatcher umbral-worker

# Verify runtime
openclaw agents show rick-tracker 2>&1 | head -30 || \
  jq '.agents.list[] | select(.id=="rick-tracker") | .model' ~/.openclaw/openclaw.json

# === Bloque B: Ola 1.5 smoke ===
# Pre-state del jsonl
wc -l ~/.openclaw/trace/delegations.jsonl
tail -5 ~/.openclaw/trace/delegations.jsonl

# Disparar smoke (comando exacto depende de CLI — usar el que esté disponible)
# Opciones probables (en orden de preferencia):
openclaw agent main --message "..." || \
  openclaw send main "..." || \
  openclaw chat main --prompt "..."

# Observar nuevas líneas
tail -10 ~/.openclaw/trace/delegations.jsonl
jq -e . ~/.openclaw/trace/delegations.jsonl > /dev/null && echo "[OK] jsonl válido"

# Health post-smoke
curl -fsS http://127.0.0.1:8088/health | jq -c '{ok}'
journalctl --user-unit openclaw-gateway --since '5 minutes ago' --no-pager | grep -iE "error|fail" | tail -10 || echo "[clean]"
```

## Reportar de vuelta

Appendear log al final de este file con:

1. **Bloque A** done report (5 ítems §A).
2. **Bloque B** done report (7 ítems §B).
3. **Decisión sobre F-A urgencia** (¿skill `delegation-trace-writer` para Ola 1 sí/no?).
4. **Marcar `status: done` en frontmatter.**
5. Commit + push con `task(copilot-vps): F-C tracker Vertex + Ola 1.5 smoke real done`.

## Lo que NO incluye

- NO Ola 1b multicanal OAuth (eso será task separado con preflight).
- NO crear skill `delegation-trace-writer` (decisión depende del veredicto Bloque B).
- NO tocar otros agents fuera de `rick-tracker`.
- NO refactor de prompts de O15.1.
- NO smoke test masivo (solo 1 delegación trivial).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| `google-vertex/gemini-3.1-pro-preview` no existe en `defaults.models` | Discover paso antes; usar el ID Vertex disponible más cercano; documentar |
| Vertex auth no configurado en VPS | Si auth falla → revertir desde backup, marcar F-C como blocked, reportar credentials gap |
| Smoke disparo bloqueado por `plugins.allow` (como pasó en O15.1) | Habilitar plugin específico temporalmente o usar ruta CLI alternativa; si imposible → reportar y diferir Ola 1.5 a otro vector (e.g. Telegram bot) |
| Modelo no obedece instrucción de escribir jsonl | Es exactamente lo que queremos descubrir → reportar como veredicto "F-A urgente" |
| Gasto >3 turnos | Abortar y reportar |

## Referencias

- Task previa O15.1: `.agents/tasks/2026-05-07-015-copilot-vps-o15-1-rick-ceo-fundamentos-ola1.md`.
- Plan Q2-2026 §O15: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` (no accesible VPS).
- Modelo §5.3: `notion-governance/docs/architecture/15-rick-organizational-model.md` (no accesible VPS).
- IDENTITY.md v1.1 deltas vivos en `~/.openclaw/workspace/IDENTITY.md` y `~/.openclaw/workspaces/rick-orchestrator/IDENTITY.md`.

---

## Log de ejecución

(Copilot VPS appendea acá)
