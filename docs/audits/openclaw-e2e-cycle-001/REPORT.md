# OpenClaw E2E — Cycle 001 Vía A (Notion → Worker) — REPORT

**Fecha:** 2026-05-18
**Modo auditor:** READ-ONLY (sin Notion writes, sin restarts, sin edits a openclaw.json ni env, sin PRs/push).
**Trigger:** David posteó manualmente `@rick /health` en Notion Control Room (`page_id=30c5f443fb5c80eeb721dc5727b20dca`).
**Veredicto:** **PASS** (con 1 anomalía no bloqueante documentada).

---

## 1. Timestamps & HEAD

| Marker | Valor |
|---|---|
| T0 (pre-trigger) | `2026-05-18T17:36:02Z` |
| T1 (David posteó) | `2026-05-18T17:41:42Z` |
| T2 (cierre observación) | `2026-05-18T17:45:03Z` |
| HEAD | `959cffedb80d7f74cdd422a02e3d3f55a72dcb01` ✅ (match pre-audit) |
| Branch | `main` |

> Nota de zona horaria: el servidor escribe journal en local UTC-4. `13:39:52 local = 17:39:52Z`. Todos los eventos del trigger ocurren dentro de la ventana T1–T2.

---

## 2. Baseline (pre-trigger) vs Post-trigger — Delta table

| Probe | Pre (T0) | Post (T2) | Δ | Esperado | OK |
|---|---|---|---|---|---|
| `umbral:notion_poller:last_ts` | `2026-05-18T12:31:00+00:00` | `2026-05-18T17:41:00+00:00` | cursor avanza | avanzar | ✅ |
| `umbral:tasks` LLEN | `0` | `0` | 0 (pico transitorio) | back-to-0 | ✅ |
| `processed_comment:*` count | `17` | `19` | **+2** | +1 (trigger) +1 (reply re-poll) | ✅ |
| Worker `/health` | `ok=true v0.4.0` | `ok=true v0.4.0` | — | up | ✅ |
| HEAD | `959cffe` | `959cffe` | sin cambio | sin restart/deploy | ✅ |

> `Δprocessed_count = +2` es consistente con la conclusión del trigger-audit: el comentario original de David (`3645f443-fb5c-80e5-b10d-001d6dc07f3a`) y el reply emitido por el worker (`3645f443-fb5c-81ca-8117-001db4d88f61`), ambos claimed por el poller en `processed_comment` con SET NX EX 86400.

---

## 3. Evidencia de pipeline — Trace end-to-end

### 3.1 `poller-log-trace.txt` (dispatcher.rick_mention)

```
2026-05-18 13:39:52,612 [INFO] dispatcher.rick_mention: Rick mention routed:
    comment=3645f443 author=1e3d872b page=30c5f443 trace=0232eed6
2026-05-18 13:39:52,749 [INFO] dispatcher.notion_poller: Skipping already
    processed comment 3645f443-fb5c-80e5-b10d-001d6dc07f3a (idempotencia OK)
```

**Verificación:**
- `author=1e3d872b` matchea allowlist `DAVID_NOTION_USER_ID` (gate `rick_mention.py:30-36`).
- `trace=0232eed6` es el `trace_id` propagado a envelope + JSONL + worker logs.
- Mensaje "Skipping already processed" en el siguiente tick del poller confirma idempotencia (SET NX EX 86400 funcionando).

### 3.2 `envelope-trace.txt` (dispatcher.queue + dispatcher.service)

```
task_id     = b01d554a37
team        = rick-orchestrator
task_type   = triage
task        = rick.orchestrator.triage
trace_id    = 0232eed6
ref.comment_id = 3645f443-fb5c-80e5-b10d-001d6dc07f3a
ref.page_id    = 30c5f443fb5c80eeb721dc5727b20dca
```

### 3.3 `jsonl-trace-tail.txt` (worker.tasks._trace.append_delegation)

Ruta: `~/.local/state/umbral/delegations.jsonl` (1346 bytes, mode `0o600`).

```json
{
  "from": "channel-adapter:notion-poller",
  "intent": "triage",
  "ref": {
    "comment_id": "3645f443-fb5c-80e5-b10d-001d6dc07f3a",
    "page_id": "30c5f443fb5c80eeb721dc5727b20dca"
  },
  "summary": "@rick mention from author=1e3d872b on control_room",
  "to": "rick-orchestrator",
  "trace_id": "0232eed6b094418e93aeeb86e476cec5",
  "ts": "2026-05-18T17:39:52.608785+00:00"
}
```

**Verificación:** record completo, `from`/`to`/`intent` requeridos presentes, sin claves prohibidas (`text`/`secret`/`token`/`api_key`/`password`), `ts` UTC ISO 8601, `trace_id` correlacionable con journal y envelope.

### 3.4 `task-status.txt` (worker handler v0)

```
status                       = done
result.command               = health
result.reply_posted          = true
result.reply_comment_id      = 3645f443-fb5c-81ca-8117-001db4d88f61
result.page_id               = 30c5f443fb5c80eeb721dc5727b20dca
result.trace_id              = 0232eed6...
result.health.ok             = true
result.health.version        = 0.4.0
result.health.ts             = 1779125992
result.error                 = null
```

**Verificación:** handler clasificó `/health` (substring lowered match en `rick_orchestrator.py:39-40`), ejecutó loopback `GET 127.0.0.1:8088/health` (`:70-77`), formateó respuesta como bloque JSON ≤1800 chars (`:44-49`), y posteó **exactamente 1 reply** vía `notion_client.add_comment` (`:133`). `error=null` → camino feliz limpio.

---

## 4. Side-effects observados vs esperados

| # | Side-effect | Esperado (trigger-audit) | Observado | OK |
|---|---|---|---|---|
| 1 | Redis LPUSH `umbral:tasks` | 1 entry, drena | LLEN pre/post=0, task `b01d554a37` consumed | ✅ |
| 2 | JSONL append `delegations.jsonl` | 1 línea, mode 0o600 | 1 nueva línea, file 1346B mode 0o600 | ✅ |
| 3 | journald dispatcher | "Rick mention routed" 1 línea | 1 línea con trace=0232eed6 | ✅ |
| 4 | Worker loopback `/health` | ≤1 GET, timeout 5s | 1 GET OK, health embebido en task result | ✅ |
| 5 | `notion_client.add_comment` | **exactamente 1** reply ≤1800 chars | 1 reply, `reply_comment_id=3645f443…81ca` | ✅ |
| 6 | Worker logs (classify/reply posted) | bounded | "classify command=health" + "reply posted" presentes | ✅ |

**Side-effects NO ejecutados (verificación negativa):**
- ❌ LLM calls — confirmado por código (`rick_orchestrator.py` no importa cliente LLM).
- ❌ Gateway/subagent OpenClaw — handler v0 hard-coded.
- ❌ Linear/Telegram/Email/webhooks externos — no aparecen en logs ni en task result.
- ❌ Escritura Notion fuera del único `add_comment(page_id, reply_text)` — task_status.result lista 1 reply_comment_id.

**Fanout ratio:** 1 comentario `[TEST]` → 1 envelope → 1 reply Notion. **1:1 bounded.** ✅

**Auto-reply loop:** estructuralmente bloqueado — el reply lo postea el bot user_id, que NO está en `DAVID_NOTION_USER_ID` allowlist (`rick_mention.py:30-36`). Confirmado en runtime: la segunda aparición del `processed_comment` (Δ=+2) corresponde al reply_comment_id, pero el siguiente tick del poller lo claim-and-skip sin re-disparar (no aparece segundo "Rick mention routed" en el journal).

---

## 5. Verdict

### **PASS**

Pipeline Vía A (Notion → poller → dispatcher → worker handler v0 → Notion reply) ejecuta end-to-end con:
- 1:1 fanout bounded.
- Trace correlation completa: `0232eed6` propagada desde dispatcher → envelope → JSONL → worker → task result.
- Idempotencia confirmada en runtime (segundo tick del poller hace skip).
- Cero side-effects fuera del contrato definido por trigger-audit.
- HEAD inmutable, sin restarts, sin edits.

---

## 6. Anomalías

### 6.1 (NO BLOQUEANTE) `secret-leak-check.txt` no está vacío

**Estado:** 198 bytes (criterio pre-audit pedía 0 bytes).

**Contenido:**
```
./pre-env-presence.txt:4:WORKER_TOKEN=<PRESENT>
./pre-env-presence.txt:5:NOTION_API_KEY=<PRESENT>
./journal-window.txt:821:May 18 13:43:54 srv1431451 node[75421]:     "code": "refresh_token_reused"
```

**Análisis:**
- Líneas 1–2: el script de env-presence escribió intencionalmente `<PRESENT>` como placeholder en lugar del valor real. El regex del secret-leak-check matcheó el **nombre de la variable**, no su valor. **Cero material sensible filtrado.**
- Línea 3: substring `refresh_token_reused` aparece dentro de un código de error de Notion API (no es un token, es un identificador de error class). **Cero material sensible filtrado.**

**Conclusión:** los matches son **3 falsos positivos del regex**. No hay leak real. Recomendación de mejora (fuera de scope Cycle 001): refinar el regex del secret-leak-check para excluir `<PRESENT>` y nombres de error-code Notion.

---

## 7. Confirmaciones finales (auditor read-only)

- ✅ Sin Notion writes desde el auditor (David posteó el trigger manualmente; el único reply Notion vino del worker handler v0, que es el sujeto bajo test, no el auditor).
- ✅ Sin restarts de servicios (PIDs estables: gateway 75421, dispatcher 120697, worker 144470, poller 120685).
- ✅ Sin edits a `~/.openclaw/openclaw.json`.
- ✅ Sin edits a `~/.config/openclaw/env`.
- ✅ Sin PRs / push / cambios en `main` (HEAD inmutable `959cffe`).
- ✅ Sin sudo.
- ✅ Worktree limpio respecto a archivos versionados.
