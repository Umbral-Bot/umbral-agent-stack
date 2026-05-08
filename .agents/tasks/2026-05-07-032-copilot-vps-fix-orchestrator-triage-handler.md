---
task_id: 2026-05-07-032
title: Fix POST /run 400 rick.orchestrator.triage — extender enums + implementar handler + restart worker
status: in-review
requested_by: copilot-chat (autorizado por David 2026-05-07 post task 031 merged)
assigned_to: copilot-vps
related: 2026-05-07-031 (diagnosis HB+HA+HC, PR #346 merged commit 100af660), 2026-05-07-021 (Vertex primary fix), 2026-05-07-026 (mention H1 validated), notion-governance plan O15.1b smoke 2026-05-07T16:25Z PASS PARCIAL
priority: high
deadline: 2026-05-12
estimated_turns: 2-3
---

# Fix orchestrator triage handler — make smoke O15.1b PASS 100%

## Contexto

Task 031 (PR #346 merged en `100af660`) confirmó:

- **HB primaria**: `worker/models/__init__.py:43,51` — `Team` enum no incluye `'rick-orchestrator'`; `TaskType` enum no incluye `'triage'`. FastAPI rechaza con 400 antes del dispatch.
- **HC latente**: aunque enums acepten, `worker/tasks/__init__.py:TASK_HANDLERS` no tiene `rick.orchestrator.triage` → 400 `Unknown task: ...`.
- **HA secundaria**: `dispatcher/model_router.py` normaliza `triage→general→azure_foundry` independiente de `agents.list[].model.primary`. Si el handler nuevo invoca al subagente OpenClaw vía gateway, ahí sí se honra el fix Vertex de task 021. Si pipelinea internamente con `llm.generate`, hereda el routing del model_router.

**Canal Notion ya PASS end-to-end** (mention H1 + dispatch + write-back con autor "Rick" integration). Solo falta cerrar el handler downstream para que el smoke completo (`@Rick ping worker /health` → JSON real en reply) pase.

## Decisión de diseño pendiente (resolver en B1)

¿El handler `rick.orchestrator.triage` debe:

- **Opción A — Proxy al subagente OpenClaw**: invocar al agente `rick-orchestrator` configurado en `openclaw.json` (`agents.list[id=="rick-orchestrator"]`, primary=Vertex post-task-021) vía el gateway local (`http://127.0.0.1:18789`). Ventaja: hereda la lógica de SOUL + Reglas 21/22 + tool whitelist. Desventaja: mayor latencia, dependencia del gateway (que está en Fase 1 estabilidad hasta 2026-05-14).
- **Opción B — Pipeline interno**: parsear el `text` del comment y resolver "intents" simples (`ping worker /health`, `status`, etc.) directamente con tareas existentes (`http.get`, `worker.health`) sin invocar LLM. Ventaja: zero-cost, zero-latency, no consume gateway. Desventaja: solo cubre comandos hard-coded; falta razonamiento real.
- **Opción C — Híbrido**: pipeline interno para comandos pre-definidos (whitelist `/health`, `/status`, `/version`); fallback a Opción A para texto libre.

**Recomendación Copilot Chat**: empezar con **Opción C minimal** — solo `/health` hard-coded para cerrar el smoke de O15.1b al 100%, dejar Opción A como follow-up (task 033) post Vertex Fase 1 (after 2026-05-14). Razón: el smoke pide específicamente `ping worker /health y devolveme el JSON acá como reply`, no necesita razonamiento.

Copilot VPS valida o propone alternativa en bloque B1 antes de implementar.

## Restricciones duras

- **NO restart gateway** (Vertex Fase 1 hasta 2026-05-14). El restart es del **worker** (`umbral-worker` user systemd unit), NO de `openclaw-gateway`.
- **NO tocar `openclaw.json`** ni `model.primary` salvo que la Opción A elegida en B1 lo requiera explícitamente — y en ese caso DIFERIR a task 033 post-Fase-1.
- **F-INC-002**: `git fetch + log origin/main..HEAD + log HEAD..origin/main` antes pull/push.
- **`secret-output-guard` regla #8**: NUNCA imprimir tokens.
- **SOUL Reglas 21+22**: si el handler no puede ejecutar el comando real, debe retornar el gap honestamente — NO inventar JSON ni mock responses para satisfacer gobernanza.
- **Tests primero**: agregar tests de unit/integration ANTES o EN el mismo commit que el handler (no dejar el handler sin cobertura).

## Procedimiento

### Bloque 0 — Pre-flight

```bash
cd ~/umbral-agent-stack
git fetch origin
git log --oneline origin/main..HEAD ; echo "(ahead)"
git log --oneline HEAD..origin/main ; echo "(behind)"
git pull --ff-only origin main 2>&1 | tail -3
git checkout -b copilot-vps/032-fix-orchestrator-triage-handler
```

### Bloque 1 — Decisión de diseño (Opción A/B/C)

1. Leer `dispatcher/rick_mention.py` para entender qué espera el dispatcher como response del worker (forma del JSON, campos requeridos, error contract).
2. Leer `dispatcher/notion_responder.py` (o equivalente) para entender cómo se renderiza la response en el Notion comment reply (formato del texto del reply visible).
3. Decidir A/B/C con justificación 2-3 líneas. Documentar en `/tmp/032/design.md`.
4. Si Opción A: confirmar que el gateway acepta requests POST sin restart (debería, es solo invocar `agents.list[].invoke` API existente).

### Bloque 2 — Extender enums (HB fix)

`worker/models/__init__.py`:

- `Team` enum → agregar `RICK_ORCHESTRATOR = "rick-orchestrator"`.
- `TaskType` enum → agregar `TRIAGE = "triage"`.

Verificar que ningún test rompa por enum exhaustiveness checks (e.g., `match` statements sin caso default).

### Bloque 3 — Implementar handler (HC fix)

Según decisión B1:

- Crear `worker/tasks/rick_orchestrator.py` con `async def handle_rick_orchestrator_triage(envelope: TaskEnvelope) -> TaskResult`.
- Para Opción C minimal: parsear `envelope.input.text`, detectar `/health` substring, ejecutar `httpx.get("http://127.0.0.1:8088/health")` (self-call), devolver el JSON formateado en el `output.text` del result.
- Registrar en `worker/tasks/__init__.py:TASK_HANDLERS["rick.orchestrator.triage"] = handle_rick_orchestrator_triage`.

### Bloque 4 — Tests

`tests/test_rick_orchestrator.py`:

- `test_triage_health_command_returns_json`: input `"@Rick ping worker /health y devolveme el JSON acá como reply"`, mock httpx, assert output contiene JSON parseado.
- `test_triage_unknown_command_returns_honest_gap`: input texto libre sin comando reconocido, assert output dice "no implementado, gap reconocido" (SOUL Regla 22).
- `test_triage_invalid_envelope_rejects`: envelope con `team="rick-orchestrator"` pero `task_type="invalid"` → 400 (smoke contra el enum extension).

Run completo: `WORKER_TOKEN=test python -m pytest tests/test_rick_orchestrator.py tests/test_rick_mention.py tests/test_notion_mention_router.py -v`.

### Bloque 5 — Restart worker + smoke local

```bash
systemctl --user restart umbral-worker
systemctl --user is-active umbral-worker  # debe ser active
curl -fsS http://127.0.0.1:8088/health | jq  # smoke worker básico
```

Reproducir POST /run con el payload del task 031 (`/tmp/031/payload-9574.json` si todavía existe, sino reconstruir):

```bash
curl -X POST http://127.0.0.1:8088/run \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/032/payload-replay.json -i
```

Esperado: HTTP 200 + JSON body con el `/health` parseado.

### Bloque 6 — Smoke real coordinar con David

Antes de pedir a David que repita el `@Rick ping worker /health` en Control Room:

- Verificar que el daemon `notion_poller` sigue vivo (`cat /tmp/notion_poller.pid && kill -0 $(cat /tmp/notion_poller.pid)`).
- Confirmar que el cron `*/5` sigue activo (`crontab -l | grep notion-poller-cron`).

Pedir a David por mailbox o vía mensaje: "Postear `@Rick ping worker /health y devolveme el JSON acá como reply` en Control Room (page id `30c5f443fb5c80eeb721dc5727b20dca`)". Avisar timestamp.

Verificación post-post:

```bash
tail -50 /tmp/notion_poller.log | grep -i "rick mention routed"
journalctl --user -u openclaw-dispatcher --since "5 min ago" | grep "rick.orchestrator.triage" | tail -10
journalctl --user -u umbral-worker --since "5 min ago" | grep -E "POST /run|rick.orchestrator" | tail -10
```

Esperado:
- `Rick mention routed` con nuevo comment_id.
- Dispatcher: `POST http://127.0.0.1:8088/run "HTTP/1.1 200 OK"`.
- Reply visible en Notion con autor "Rick" + JSON real del `/health`.

### Bloque 7 — Capitalizar

Append-only en `.agents/board.md` (constraint: solo se appendea en `main` post-merge — Copilot Chat lo hace, NO Copilot VPS desde branch):

```
## 2026-05-07-032 — fix orchestrator triage handler [DONE]
- decisión diseño: <A|B|C> + justificación
- enums extendidos + handler implementado + N tests pasando
- worker restart: pid old → pid new, active
- smoke real timestamp: <UTC>
- O15.1b: PASS 100% ✅
- F-INC-002 + secret-output-guard + SOUL Reglas 21/22: respetadas
- gateway pid 75421 sin restart, openclaw.json intacto, Vertex Fase 1 intacta
```

Commit + PR a main:

```
task(032): fix POST /run rick.orchestrator.triage handler — extiende enums Team+TaskType,
implementa handle_rick_orchestrator_triage (opción <X>), N tests pasando, worker restart
+ smoke real PASS; canal Notion O15.1b cierra al 100%; gateway pid 75421 sin restart,
openclaw.json intacto, Vertex Fase 1 ventana respetada
```

## Criterios de done

- [ ] Decisión de diseño A/B/C justificada en `/tmp/032/design.md`.
- [ ] Enums `Team.RICK_ORCHESTRATOR` y `TaskType.TRIAGE` añadidos.
- [ ] Handler `handle_rick_orchestrator_triage` implementado y registrado.
- [ ] ≥3 tests nuevos pasando (health command + unknown command + envelope validation).
- [ ] Tests existentes (`test_rick_mention`, `test_notion_mention_router`) siguen pasando.
- [ ] Worker reiniciado, `/health` responde 200.
- [ ] POST /run replay del payload 031 retorna 200 + JSON esperado.
- [ ] David ejecuta smoke real en Control Room → reply con autor "Rick" + JSON real.
- [ ] Plan O15.1b actualizable a "PASS 100%".
- [ ] Branch + PR + merge.
- [ ] NO restart del gateway, NO edit a `openclaw.json`.

## NO hacer

- ❌ NO restart gateway.
- ❌ NO editar `openclaw.json` ni `model.primary` (si Opción A lo requiere → DIFERIR a task 033 post-2026-05-14).
- ❌ NO inventar JSON de respuesta ni mock para satisfacer gobernanza (SOUL Regla 21).
- ❌ NO imprimir tokens.
- ❌ NO escribir entries fabricadas en `~/.openclaw/trace/delegations.jsonl`.
- ❌ NO implementar handler sin tests en el mismo commit.

---

## Close log — Copilot VPS 2026-05-07T18:35Z (in-review)

### Decisión de diseño (B1): **Opción C minimal**

Pipeline interno hard-coded (NO LLM, NO subagent OpenClaw, NO gateway). Comando `/health` reconocido → self-call al worker → reply al Notion comment con JSON real. Comando desconocido → reply honesto "no implementado en triage v0" (SOUL Regla 22). Justificación completa en `/tmp/032/design.md`.

Razones para descartar A/B puras:
- **Opción A** (proxy gateway): toca al gateway pid 75421 en ventana Vertex Fase 1 (hasta 2026-05-14); riesgo regresión task 021. Diferida a task 033 post-Fase-1.
- **Opción B pura**: lo que se implementó. Suficiente para cerrar O15.1b.

### Cambios (en este commit)

| Archivo | Cambio |
|---|---|
| `worker/models/__init__.py` | `Team.RICK_ORCHESTRATOR='rick-orchestrator'`, `TaskType.TRIAGE='triage'` (HB fix) |
| `worker/tasks/rick_orchestrator.py` | NUEVO — `handle_rick_orchestrator_triage` (Opción C minimal) |
| `worker/tasks/__init__.py` | import + registro `"rick.orchestrator.triage"` en `TASK_HANDLERS` (HC fix) |
| `tests/test_rick_orchestrator.py` | NUEVO — 16 tests (enum, registro, classifier, formato, integración con mocks) |

### Tests

- **16 tests nuevos pasando** (`tests/test_rick_orchestrator.py`).
- **30/30 pasando** en suite combinada `test_rick_orchestrator + test_rick_mention + test_notion_mention_router`.
- Pre-existentes en `test_worker.py` y `test_model_router.py` siguen fallando — verificado con stash: **NO son regresión** (problema de fixture cargando token al import time + precedencia claude_pro vs gemini_pro). Reportado pero fuera de scope.

### Worker restart + smoke local (B5)

```
PID_OLD=59402  PID_NEW=96364  status=active
GET /health → 200 OK; "rick.orchestrator.triage" presente en tasks_registered (104 total)
POST /run smoke replay (payload /tmp/032/payload-replay.json, page_id=null)
  → HTTP 200
  → result.command="health"
  → result.health={"ok":true,"version":"0.4.0",...}  (JSON real del worker, NO inventado)
  → result.reply_posted=false, result.error="no_page_id_in_envelope"  (gap honesto SOUL Regla 22)
```

### Salvavidas honrados

- ✅ **Gateway pid 75421 sin restart** (`ps -p 75421` ELAPSED ~04:00:00 → uptime continuo).
- ✅ `openclaw.json` y `model.primary` no editados.
- ✅ F-INC-002 verificado pre-pull (ahead=0, behind=3 → ff a `b82f88a`).
- ✅ `secret-output-guard` regla #8: ningún token impreso.
- ✅ SOUL Reglas 21+22: handler devuelve gap honesto cuando no puede ejecutar; tests verifican explícitamente que NO inventa JSON falso.
- ✅ Tests en el mismo commit que el handler.

### Pendiente B6 — smoke real con David

David debe postear en Control Room (`30c5f443fb5c80eeb721dc5727b20dca`):
> `@Rick ping worker /health y devolveme el JSON acá como reply`

Verificación post-post (a ejecutar Copilot VPS con timestamp UTC del post):
```bash
tail -50 /tmp/notion_poller.log | grep -i "rick mention routed"
journalctl --user -u openclaw-dispatcher --since "5 min ago" | grep "rick.orchestrator.triage" | tail -10
journalctl --user -u umbral-worker --since "5 min ago" | grep -E "POST /run|rick.orchestrator" | tail -10
```

Esperado: `Rick mention routed` → `POST /run 200 OK` → reply en Notion con autor "Rick" + JSON real `/health`.

### Texto sugerido para `.agents/board.md` (Copilot Chat lo appendea post-merge)

```
## 2026-05-07-032 — fix orchestrator triage handler [DONE]
- decisión diseño: Opción C minimal (pipeline interno hard-coded /health; sin LLM, sin subagent, sin gateway)
- enums extendidos (Team.RICK_ORCHESTRATOR + TaskType.TRIAGE) + handler implementado + 16 tests pasando
- worker restart: pid 59402 → 96364, active, 104 tasks_registered (incluye rick.orchestrator.triage)
- smoke local: POST /run 200, JSON real de /health en result, gap honesto cuando page_id null
- smoke real timestamp: <COMPLETAR cuando David poste>
- O15.1b: <PASS 100% si smoke real OK>
- F-INC-002 + secret-output-guard #8 + SOUL Reglas 21/22: respetadas
- gateway pid 75421 sin restart, openclaw.json intacto, Vertex Fase 1 ventana respetada
- follow-up task 033: Opción A proxy a OpenClaw subagent rick-orchestrator (post 2026-05-14)
```

### Working notes locales (NO commit)

- `/tmp/032/design.md` — decisión A/B/C + justificación.
- `/tmp/032/payload-replay.json` — payload smoke local.
- `/tmp/032/response-200.json` — response 200 captura.
