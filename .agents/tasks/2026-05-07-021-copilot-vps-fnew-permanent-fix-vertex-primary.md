---
task_id: 2026-05-07-021
title: F-NEW fix permanente — switch rick-orchestrator.model.primary a google-vertex/gemini-3.1-pro-preview + restart gateway + smoke
status: done
requested_by: copilot-chat (autorizado por David)
assigned_to: copilot-vps
related: 2026-05-07-019 (H3 aislada 3a/3b), 2026-05-07-020 (vector D ERROR auth → verdict 3b heurístico)
priority: high
deadline: 2026-05-08
estimated_turns: 1-2
---

# F-NEW fix permanente — switch primary a Vertex + restart gateway + smoke

## Contexto

- Task 019 (commit `545b9a6`) aisló refusal a **3a/3b** (model+provider stack). v3 con `google-vertex/gemini-3.1-pro-preview` funcionó NORMAL (193,660 tokens, exec uuidgen). v1/v2/v4 con `azure-openai-responses/gpt-5.4` REFUSAL canned.
- Task 020 (commit `348b0ab`) intentó vector D con `openai-codex/gpt-5.4` → ERROR auth (OAuth caducado, fallbackStepFromFailureReason `auth`, chain_exhausted). Verdict consolidado: **3b heurístico**.
- Bloqueo de delegaciones padre→hijo se mantiene hasta este task. One-hop directo a `main` operativo.
- Bump bootstrap (24k/120k) se mantiene.

## Objetivo

Aplicar **fix permanente**: cambiar `agents.list[id=="rick-orchestrator"].model.primary` de `azure-openai-responses/gpt-5.4` a `google-vertex/gemini-3.1-pro-preview` en `~/.openclaw/openclaw.json`, **restart 1 vez del gateway** (autorizado), smoke test del baseline body de task 019. Resultado esperado: subagent responde NORMAL (no canned refusal).

Re-auth de `openai-codex` + retry vD para discriminación 100% queda como **sub-bloque opcional al final** (si el OAuth refresh es trivial); si requiere intervención manual de David, defer a task 022.

## Restricciones duras

- Sólo **1 restart** del gateway. Cualquier restart adicional debe pararse y reportar.
- Backup obligatorio de `~/.openclaw/openclaw.json` antes del edit (con timestamp pre-021).
- No tocar workspaces (`~/.openclaw/workspaces/*`). No tocar bootstrap. No tocar `~/.config/openclaw/copilot-cli-secrets.env` (salvo sub-bloque opcional re-auth codex).
- `secret-output-guard` regla #8 vigente: NO `grep "COPILOT" /proc/$PID/environ`.
- F-INC-002 vigente: chequeo `git fetch origin && git log origin/main..HEAD && git log HEAD..origin/main` antes de cada `git pull`/`git push`.
- Rollback path obligatorio: si smoke falla → restaurar backup `openclaw.json` + restart gateway segunda vez (excepción autorizada para revert) → reportar.
- Backups task 019 (`*.bak-pre-019-20260507-093659`) **no borrar** todavía. David cierra F-NEW post-021.

## Procedimiento

### Bloque 0 — Setup + backup

```bash
cd /home/rick/umbral-agent-stack
git fetch origin
git log --oneline origin/main..HEAD
git log --oneline HEAD..origin/main
git stash -u 2>&1 | tail -2 || true
git pull origin main 2>&1 | tail -3

TS=$(date +%Y%m%d-%H%M%S); echo "TS=$TS"

# Backup pre-021
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-021-${TS}
echo "Backup: ~/.openclaw/openclaw.json.bak-pre-021-${TS}"

# Snapshot config rick-orchestrator pre-edit
jq '.agents.list[] | select(.id=="rick-orchestrator") | {id, model}' ~/.openclaw/openclaw.json | tee /tmp/021-config-pre.json

# Gateway pid pre-restart (debería seguir siendo el de pre-019, normalmente pid 54835)
GATEWAY_PID_PRE=$(pgrep -f "openclaw-gateway" | head -1)
echo "GATEWAY_PID_PRE=$GATEWAY_PID_PRE"
```

### Bloque 1 — Edit `model.primary`

Conservador: **sólo cambiar `primary`**. Dejar `fallbacks` como están (`gpt-5.2-chat`, `openai-codex/gpt-5.4`) — si primary funciona, fallback raramente dispara; cambiar fallbacks ahora añade scope sin necesidad.

```bash
# Edit atómico: tmpfile + jq + mv
jq '(.agents.list[] | select(.id=="rick-orchestrator") | .model.primary) = "google-vertex/gemini-3.1-pro-preview"' \
  ~/.openclaw/openclaw.json > /tmp/021-openclaw-new.json

# Validar JSON parsea
jq empty /tmp/021-openclaw-new.json && echo "JSON OK"

# Validar el cambio aplicó
jq '.agents.list[] | select(.id=="rick-orchestrator") | {id, model}' /tmp/021-openclaw-new.json | tee /tmp/021-config-post.json

# Diff humano
diff /tmp/021-config-pre.json /tmp/021-config-post.json

# Aplicar
mv /tmp/021-openclaw-new.json ~/.openclaw/openclaw.json
echo "Applied edit at $(date -u +%FT%TZ)"
```

### Bloque 2 — Restart gateway (1 vez autorizado)

```bash
# Usar el comando estándar — el gateway corre como user systemd unit o npm-global binary.
# Path A (preferido): systemctl --user
systemctl --user restart openclaw-gateway 2>&1 | tee /tmp/021-restart.log
sleep 5

# Path B (fallback si no hay unit user systemd): kill + relaunch
# (Sólo si Path A no aplica — reportar y consultar antes de ejecutar B)

# Verificar gateway up + nuevo pid
GATEWAY_PID_POST=$(pgrep -f "openclaw-gateway" | head -1)
echo "GATEWAY_PID_PRE=$GATEWAY_PID_PRE / GATEWAY_PID_POST=$GATEWAY_PID_POST"
ss -tlnp 2>/dev/null | grep 18789 || sudo ss -tlnp 2>/dev/null | grep 18789

# Health check
curl -fsS http://127.0.0.1:18789/health 2>&1 | head -5 || openclaw status 2>&1 | head -10
```

Si gateway no levanta en 30s → rollback inmediato (Bloque 4) y reportar.

### Bloque 3 — Smoke test (baseline body task 019)

Reusar baseline body de task 019 (sha256 `206c896c…b15a72a5ea43f9eba11197e38e84`, 977-995 chars). Ejecutar **vía path canónico** (no `sessions_spawn(model=)` override — queremos validar que la config nueva engancha por defecto).

```bash
# Verificar baseline body intacto
sha256sum /tmp/019/baseline-task.txt
# EXPECTED: 206c896cc0e4ceae0f37009ff4b4e63bfc95b15a72a5ea43f9eba11197e38e84

# Dispatch sin model override (queremos que use model.primary del config nuevo)
TS_DISPATCH=$(date -u +%Y%m%dT%H%M%SZ)
SID="021-smoke-default-${TS_DISPATCH}"
mkdir -p /tmp/021

START_TS=$(date -u +%s)
openclaw agent --agent rick-orchestrator --session-id "$SID" --timeout 360 \
  --message "$(cat /tmp/019/baseline-task.txt)" \
  > /tmp/021/smoke-stdout.txt 2> /tmp/021/smoke-stderr.txt
EXIT=$?
END_TS=$(date -u +%s)
echo "EXIT=$EXIT WALL=$((END_TS-START_TS))s"
tail -30 /tmp/021/smoke-stdout.txt
```

Localizar trajectory + extraer:
- `session.started`: confirmar `modelId == "gemini-3.1-pro-preview"` y `provider == "google-vertex"`.
- `model.completed`: `usage` (in/out/cache), `assistantTexts`, `finishReason`, `tool calls`.
- `session.ended`.

**Mapping**:
- Trajectory muestra `provider=google-vertex` + response NORMAL + tokens billed >0 + tool calls >0 → ✅ **fix exitoso**, F-NEW resuelto.
- Trajectory muestra `provider=google-vertex` + REFUSAL canned → 3a/3b también afectan a Vertex; **rollback** + reportar (verdict cambia, requiere análisis nuevo).
- Trajectory muestra `provider=azure-openai-responses` (config no enganchó) → posible cache adicional o edit no aplicado; **rollback** + reportar.
- Cualquier otro error → **rollback** + reportar.

### Bloque 4 — Rollback (sólo si smoke falla)

```bash
# Restaurar backup
cp ~/.openclaw/openclaw.json.bak-pre-021-${TS} ~/.openclaw/openclaw.json
jq '.agents.list[] | select(.id=="rick-orchestrator") | .model' ~/.openclaw/openclaw.json

# Restart gateway segunda vez (excepción autorizada por rollback)
systemctl --user restart openclaw-gateway 2>&1 | tail -3
sleep 5
pgrep -f "openclaw-gateway" | head -1
curl -fsS http://127.0.0.1:18789/health 2>&1 | head -5
```

Reportar y devolver control. **No** intentar más fixes en este task.

### Bloque 5 (OPCIONAL) — Re-auth `openai-codex` + retry vector D para discriminación 100%

Sólo si Bloque 3 fue exitoso, `openclaw login openai-codex` (o equivalente) es trivial sin input interactivo de David, y no requiere segundo restart del gateway:

```bash
# Tantear si CLI permite re-auth no interactivo
openclaw login --help 2>&1 | head -20
# Si requiere browser/device-code → defer a task 022 + skip este bloque.

# Si trivial y no requiere restart:
#   1. Re-auth.
#   2. Retry vector D igual que task 020 (mismo build-directive con openai-codex/gpt-5.4).
#   3. Capturar trajectory + verdict 3a vs 3b 100%.
```

Si este bloque se ejecuta, agregar tabla actualizada al log de cierre. Si se defer, registrarlo y dejar task 022 sugerida.

### Cierre

- Append log estructurado al final de este task con:
  - Bloques 0-3 detallados (timestamps, pids, sha256, diff jq).
  - Tabla smoke vs baseline task 019 (provider, response, tokens, wall, tool calls).
  - Estado final: gateway pid, openclaw.json hash, workspace untouched check.
  - Verdict: F-NEW resuelto ✅ / rollback ejecutado ❌.
  - Bloque 5 (si ejecutado): tabla 6 vectores con verdict 3a vs 3b 100%; (si deferido): nota a task 022.
- Commit: `task(021): F-NEW fix permanente done — primary=google-vertex/gemini-3.1-pro-preview + restart + smoke <OK|ROLLBACK>`
- Push (con chequeo F-INC-002 antes).

## Output esperado

1. Verdict explícito: F-NEW resuelto o rollback.
2. Smoke trajectory path + tokens billed.
3. Confirmación gateway healthy post-restart.
4. Diff `openclaw.json` antes/después (1 línea: `model.primary`).
5. Nueva fila en tabla 5-vectores task 020 con resultado smoke "default config" (sin override).
6. (Opcional) verdict 3a vs 3b 100% si Bloque 5 ejecutó.

## Salvavidas

- Si gateway no recupera tras rollback → escalada inmediata a David (gateway down = Rick offline = bloqueo total).
- Si edit jq falla validation → no aplicar, reportar.
- Si smoke trajectory no aparece en 360s → asumir falla, rollback.

---

## Log de ejecución — 2026-05-07T14:38-14:40Z (copilot-vps)

### Bloque 0 — Setup + backup

- Pre-flight F-INC-002: `git fetch origin` → main al día con `36a9b2a` (task 021 spec). Worktree limpio, fast-forward pull desde `348b0ab` OK.
- TS = `20260507-103811`.
- Backup creado: `~/.openclaw/openclaw.json.bak-pre-021-20260507-103811` (30858 B, idéntico tamaño a backup pre-019).
- Snapshot pre-edit (`/tmp/021-config-pre.json`):
  ```json
  {"id":"rick-orchestrator","model":{"primary":"azure-openai-responses/gpt-5.4","fallbacks":["azure-openai-responses/gpt-5.2-chat","openai-codex/gpt-5.4"]}}
  ```
- Gateway pid pre-restart: **54835** (uptime 8h, `active (running)` desde 2026-05-07T05:57:16Z).

### Bloque 1 — Edit `model.primary`

Edit atómico con jq + tmpfile + mv:

```diff
--- pre
+++ post
-    "primary": "azure-openai-responses/gpt-5.4",
+    "primary": "google-vertex/gemini-3.1-pro-preview",
```

- Validación `jq empty /tmp/021-openclaw-new.json` → JSON OK.
- `model.fallbacks` intacto (`gpt-5.2-chat`, `openai-codex/gpt-5.4`) — conservador.
- Aplicado: 2026-05-07T14:38:40Z.
- Verificación scope: `diff <(jq -S 'del(.agents.list[]|select(.id=="rick-orchestrator")|.model.primary)' openclaw.json) <(jq -S 'del(...)' openclaw.json.bak-pre-021-...)` → **EMPTY**. Confirma que **solo** `model.primary` cambió, nada más tocado.
- Hash final `openclaw.json`: `cca6f7428f516b253bb1eade8b9fdb5b3aee86e7be0cdaed077c743832f82abf`.

### Bloque 2 — Restart gateway (1× autorizado)

- Comando: `systemctl --user restart openclaw-gateway`. Sin errores.
- Gateway pid post-restart: **75421** (active (running) desde 2026-05-07T10:38:41 -04, sin failures en boot).
- Listening confirmado: `127.0.0.1:18789` + `100.113.249.25:18789` (tailnet) + IPv6 loopback + tailnet IPv6.
- Sin segundo restart.

### Bloque 3 — Smoke test (baseline body task 019, sin model override)

- Comando: `openclaw agent --agent rick-orchestrator --session-id 021-smoke-default-20260507T143900Z --timeout 360 --message "$(cat /tmp/019/baseline-task.txt)"`.
- Baseline body sha256 reusado verbatim: `206c896cc0e4ceae0f37009ff4b4e63bfc95b15a72a5ea43f9eba11197e38e84`.
- Wall = **30s**. Exit 0. **NO se usó model override** (validamos que la config nueva engancha por defecto).
- Trayectoria: `~/.openclaw/agents/rick-orchestrator/sessions/021-smoke-default-20260507T143900Z.trajectory.jsonl`
- `session.started`:
  ```json
  {"ts":"2026-05-07T14:39:10.803Z","modelId":"gemini-3.1-pro-preview","provider":"google-vertex","sessionKey":"agent:rick-orchestrator:explicit:021-smoke-default-20260507t143900z"}
  ```
  ✅ provider=`google-vertex`, modelId=`gemini-3.1-pro-preview` — config enganchó por defecto.
- `model.completed` (consolidado):
  - `usage`: input=24017, output=994, cacheRead=16212, total=**41,223 tokens**
  - `aborted=false`, `finishReason=null`, `errorSource=null`
  - `lastCallUsage`: input=4128, output=29, cacheRead=16212, cacheWrite=0
- Tool calls ejecutadas (1 sample c/u en messagesSnapshot): `exec`, `sessions_spawn`, `sessions_yield`. **Comportamiento NORMAL canónico** (rick-orchestrator delegando a rick-ops vía sessions_spawn como espera el baseline body).
- `session.ended`: `{"status":"success","aborted":false,"externalAbort":false,"timedOut":false,"idleTimedOut":false}`.
- `model.fallback_step`: **0** (primary funcionó al primer intento, no se disparó fallback chain).

#### Verdict

✅ **F-NEW resuelto**. La hipótesis 3a/3b (azure-responses/gpt-5.4 con refusal canned) queda mitigada permanentemente vía switch a `google-vertex/gemini-3.1-pro-preview` como primary del orchestrator. Subagent ahora responde NORMAL, billa tokens, ejecuta tool calls.

#### Tabla 6 vectores (5 task 019/020 + smoke task 021)

| vector | provider/model                               | response | usage(in/out/cache)        | wall | tool calls                             | trajectory |
| ------ | -------------------------------------------- | -------- | -------------------------- | ---- | -------------------------------------- | ---------- |
| v1     | azure-openai-responses/gpt-5.4               | REFUSAL  | null/null/null             | 2s   | 0                                       | `d20c3a76…` |
| v2     | azure-openai-responses/gpt-5.4 (body "pong") | REFUSAL  | null/null/null             | 2s   | 0                                       | `5d5f60e3…` |
| v3     | google-vertex/gemini-3.1-pro-preview (override) | NORMAL | 36188/3114/193660          | 90s  | exec uuidgen                            | `7d4da225…` |
| v4     | azure-openai-responses/gpt-5.4 (95B)         | REFUSAL  | null/null/null             | 6s   | 0                                       | `4461c4c7…` |
| vD     | openai-codex/gpt-5.4 (override)              | ERROR auth | 0/0/0                    | 6s   | 0 (chain_exhausted)                     | `ff4313c1…` |
| **smoke 021** | **google-vertex/gemini-3.1-pro-preview (DEFAULT)** | **NORMAL** | **24017/994/16212 (total 41223)** | **30s** | **exec, sessions_spawn, sessions_yield** | `021-smoke-default-20260507T143900Z` |

### Bloque 5 — Sub-bloque opcional (re-auth codex + retry vD): **DEFERIDO a task 022**

- `openclaw login --help` → CLI bloqueada por `plugins.allow excludes "login"`. Mensaje exacto: `The 'openclaw login' command is unavailable because 'plugins.allow' excludes "login"`.
- Re-habilitar requeriría: (1) editar `plugins.allow` en `openclaw.json` agregando `"login"`, (2) **segundo restart del gateway** (no autorizado en este task), (3) ejecutar el flujo OAuth (probablemente browser/device-code → input interactivo de David).
- Por las restricciones duras (`Sólo 1 restart del gateway autorizado`), **se defer a task 022**.
- Verdict 3a vs 3b queda en **3b heurístico** (de task 020). El fix permanente de F-NEW no depende de discriminar 3a vs 3b — funciona independiente del verdict.

### Estado final

- `openclaw.json` hash: `cca6f7428f516b253bb1eade8b9fdb5b3aee86e7be0cdaed077c743832f82abf`.
- Workspaces (`~/.openclaw/workspaces/rick-orchestrator`) **diff vs backup pre-019 = EMPTY** ✅ (no se tocaron).
- Bootstrap (24k/120k) intacto.
- `~/.config/openclaw/copilot-cli-secrets.env` no tocado.
- Gateway: `systemctl --user is-active openclaw-gateway` → `active`. Pid 75421 (single restart autorizado).
- Backups conservados:
  - `~/.openclaw/openclaw.json.bak-pre-019-20260507-093659` (David cierra F-NEW post-021 — ahora puede eliminar tras validar smoke).
  - `~/.openclaw/openclaw.json.bak-pre-021-20260507-103811` (rollback path; mantener al menos 24h).
- Workspaces backup `~/.openclaw/workspaces/rick-orchestrator.bak-pre-019-20260507-093659/` también preservado.

### Sugerencia para task 022

- Habilitar plugin `login` (editar `plugins.allow`) + re-auth `openai-codex` + retry vector D para discriminación 100% 3a vs 3b.
- Implica **segundo restart de gateway** + posible interacción manual de David para device-code OAuth.
- Sólo si David quiere certeza académica entre 3a y 3b. Operativamente el fix permanente ya está en producción (smoke OK).
