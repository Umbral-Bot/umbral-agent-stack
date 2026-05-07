---
id: "2026-05-07-016"
title: "Copilot VPS — F-C rick-tracker→Vertex + Ola 1.5 smoke real (primera delegación end-to-end main→rick-ops)"
status: done
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

### [copilot-vps] 2026-05-07 01:25 -04 — F-C + Ola 1.5 cerrada (status: done)

VPS `srv1431451`, repo `umbral-agent-stack` HEAD post-pull `17cc085` → este commit `task(F-C+Ola1.5): rick-tracker→Vertex + smoke real delegacion end-to-end` (commit `17cc085` ya estaba en main; nuestro append es separado).

#### 1) Bloque A — F-C `rick-tracker.model.primary` → Vertex Gemini ✅ (verificación; SIN edit)

**Hallazgo crítico que corrige reporte O15.1 §5:** el runtime YA tiene exactamente la config §5.3 esperada. Mi análisis previo en O15.1 fue incorrecto (probablemente confundí `agents.defaults.models[].id` con per-agent `model.primary`).

Estado real verificado:

```json
".agents.list[id==rick-tracker].model" = {
  "primary":   "google-vertex/gemini-3.1-pro-preview",
  "fallbacks": ["google/gemini-3-pro-preview", "google/gemini-3-flash-preview"]
}
```

- **ID Vertex elegido**: ya estaba `google-vertex/gemini-3.1-pro-preview` (exactamente el §5.3). Confirmado en `agents.defaults.models` (lista de 10 modelos disponibles, incluye este + 4 azure + 2 google + 2 openai-codex).
- **Fallbacks**: chain doble Google (`gemini-3-pro-preview` → `gemini-3-flash-preview`), sin azure como ultimate fallback. Documentado pero NO modificado (anti-scope: §5.3 no exige azure-as-graceful, y agregar fallback fuera-de-spec sería cambio unilateral).
- **Provider wiring**: `models.providers` solo tiene literal `azure-openai-responses`. PERO gateway logs muestran cada heartbeat (cada hora desde `May 06 15:33`):
  ```
  The user provided Vertex AI API key will take precedence over the project/location from the environment variables.
  ```
  → Vertex SÍ está wired, vía mecanismo implícito de OpenClaw 5.3-1 (probablemente lectura directa de `GOOGLE_API_KEY` + `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` del env, todos presentes en `~/.config/openclaw/env`).
- **Backup defensivo creado igual**: `~/.openclaw/openclaw.json.bak-pre-016-20260507-011955` (30,784 bytes, idéntico al actual).
- **JSON edit / restart**: NO realizados (no había nada que cambiar). Health post-verificación: worker `{"ok":true}`, dispatcher `active`, gateway `active`/`/health live`.
- **CLI verify**: `openclaw agents show rick-tracker` no existe (`agents` no acepta args). Verificación vía `jq` de la config + heartbeat log = suficiente y autoritativo.

**Veredicto Bloque A**: F-C **estaba ya completo en runtime desde antes** de O15.1 (probablemente nunca hubo drift; mi reporte previo fue erróneo). Cero acciones runtime. Backup precautorio queda como rollback target aunque no haya delta.

#### 2) Bloque B — Ola 1.5 smoke real ✅ con hallazgo significativo

**Comando exacto disparado** (1 turno; `main` con session aislada para no interferir con sesión productiva de David):

```bash
SESSION_ID="smoke-o151-1778131284"
openclaw agent --agent main --session-id "$SESSION_ID" --timeout 180 --json \
  --message 'SMOKE TEST O15.1 Ola 1.5 (autorizado por copilot-vps via task 2026-05-07-016, NO es David). [...delegate to rick-ops via rick-orchestrator, return pong + worker status, write delegations.jsonl per IDENTITY.md §3.3 contract...]'
```

**Resultado** (`/tmp/smoke-o151-out.json`):
- `runId: c911d356-5e13-4761-a1c0-289b430033bf`
- `sessionFile: ~/.openclaw/agents/main/sessions/smoke-o151-1778131284.jsonl`
- `provider: azure-openai-responses`, `model: gpt-5.4`
- `durationMs: 17374` (~17s)
- `usage: input=21963, output=774, cacheRead=45696, total=27304` tokens (~$0.05–$0.10 estimado en gpt-5.4 azure)
- `toolCalls: null`, `subagentCalls: null` → NO se invocó tool, NO se hizo delegación.

**Texto literal de respuesta del modelo:**

> No puedo ejecutar este smoke test porque las reglas vigentes me permiten aceptar instrucciones solo de David.
> Verifiqué la gobernanza en `AGENTS.md` e `IDENTITY.md`: además, desde `main` la ruta canónica sería `rick-orchestrator`, no directo a `rick-ops`.
> No hice delegación ni escribí en `~/.openclaw/trace/delegations.jsonl`.

**Trace rutado**: `main → ⊥` (refusal en hop 0). NO hubo `main → rick-orchestrator` ni `→ rick-ops`.

**`~/.openclaw/trace/delegations.jsonl` post-smoke**: 1 línea (idéntico a pre — solo el probe sintético de O15.1). Sin nuevas líneas. `jq -e .` válido.

**Validación format §3.3**: N/A (no hubo línea nueva que validar).

**Health post-smoke**: worker `{"ok":true,"tasks":107}`, dispatcher/gateway/worker `active`, `/health live`. Cero degradación.

**Gasto real**: 1 turno de modelo (de los 3 autorizados). `total=27304` tokens. Bajo budget.

**Veredicto Bloque B (THE FINDING)**:

| Aspecto | Estado |
|---|---|
| Governance prompt-driven | ✅ **Funciona excelente**. `main` enforced "único punto contacto = David" sin que tuviera que ser instruido nada extra — basta con su `IDENTITY.md` v1.0 + `AGENTS.md` heredado. Reconoció además canónicamente que la ruta sería vía `rick-orchestrator`, no directa. |
| Decision tree O15.1 (cuándo delegar) | ✅ **Validado indirectamente**. El modelo cita la jerarquía correcta sin haber sido prompteado a hacerlo en este turno. |
| JSONL write-path | ⚠️ **NO validado end-to-end**. El modelo nunca llegó a la fase de escribir porque abortó antes (correctamente). Sigue siendo desconocido si: (a) el modelo *podría* invocar bash tool para `cat >> ~/.openclaw/trace/delegations.jsonl`, (b) el format saldría válido §3.3, (c) un hop ↔ una línea efectivamente. |
| Smoke synthetic via copilot-vps | ❌ **Bloqueado por governance**. Es exactamente lo que queremos en producción (no aceptar órdenes de no-David), pero hace inviable el smoke sin David presente. |

#### 3) Decisión sobre F-A urgencia (skill `delegation-trace-writer`)

**Decisión: NO urgente para Ola 1; SÍ recomendado para Ola 2.**

**Rationale:**

- **No es blocker**: David puede ejercitar la primera delegación real en su próximo turno interactivo (e.g., "andá pingeando worker via rick-ops"). Eso validará el path jsonl-write end-to-end sin necesidad de skill custom.
- **Riesgo de bypass del gate**: agregar a `IDENTITY.md` una excepción tipo "SMOKE TEST autorizado por copilot-vps puede saltarse el gate David" abre vector de prompt injection. **Rechazado**.
- **Razones para Ola 2**:
  1. **Costo**: bash skill determinista evita tokens de tool-call LLM en cada delegación (~500 tokens × N delegaciones/día).
  2. **Format guarantee**: skill bash con `jq -nc` template no falla en estructura, mientras LLM puede generar jsonl mal formado bajo presión de contexto largo.
  3. **Audit-grade**: skill puede agregar campos automáticos (uuid, ts UTC ISO, host) sin depender de obediencia del modelo.
  4. **Asimetría asimismo resuelta**: skill invocable desde main, rick-orchestrator y gerencias por igual → 1 línea por hop garantizada.
- **Alternativa minimalista Ola 1.5**: dejar que David valide en su primer turno real. Si la línea sale válida → confirmar prompt-driven viable. Si sale ausente o malformada → priorizar skill como F-A inmediato.

**Acción recomendada al Cline humano (David):**
> En tu próximo turno con `main`, hacé un comando trivial tipo *"pingeá worker vía rick-ops y registrá la delegación"*. Yo te paso el resultado del jsonl después. Si falla → activamos skill `delegation-trace-writer` Ola 1.5b. Si funciona → queda para Ola 2 como mejora de costo/audit.

#### 4) Estado runtime final

- `rick-tracker` correctamente en Vertex Gemini 3.1-pro (sin drift).
- `main`/orchestrator IDENTITY.md v1.1 deltas operativos y enforce governance correctamente.
- Trace file con 1 línea probe sintético (de O15.1).
- Worker/dispatcher/gateway todos `active`. Tasks count subió 65→107 (carga normal del día).
- Backup `~/.openclaw/openclaw.json.bak-pre-016-20260507-011955` queda como rollback target precautorio.

#### 5) Follow-ups detectados (NO bloquean cierre)

- **F-A** (Ola 2 default; potencialmente Ola 1.5b si David confirma fallo): skill `delegation-trace-writer`.
- **F-C-revised**: corrección a mi reporte O15.1 §5 — no había drift en rick-tracker. Asentado en este log.
- **F-O15.1-A** (de la task previa) sigue pendiente — depende del veredicto de la primera delegación real de David.
- **NEW F-G**: bootstrap truncation warnings en system prompt (`AGENTS.md` rawChars=18456 → injectedChars=11999 truncado; `SOUL.md` 12285→11999 truncado, both `per-file-limit`). El modelo opera con AGENTS.md y SOUL.md PARCIALES. Considerar split o bump del `bootstrapMaxChars` (12000 default) a 20000 para sesiones críticas. Anti-scope para esta task.
- **NEW F-H**: el comando `openclaw agents show <id>` no existe en CLI 5.3-1 (`agents` no acepta args). Para introspección de agente individual hay que usar `jq` directo sobre `openclaw.json` o `openclaw status` (que muestra todos). Documentar como gap CLI.

#### 6) Status

- F-C: ✅ verificado (runtime ya alineado; sin acciones).
- Ola 1.5 smoke: ✅ ejecutado 1 turno; veredicto = governance ok, jsonl-path pending real-David turn.
- F-A: ✅ decisión documentada (Ola 2 default, escalable a 1.5b on-demand).
- `status: done`.

