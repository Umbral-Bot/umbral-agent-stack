---
task_id: 2026-05-07-031
title: Diagnosticar POST /run 400 Bad Request en task type rick.orchestrator.triage (smoke O15.1b)
status: done
requested_by: copilot-chat (autorizado por David 2026-05-07 post smoke real)
assigned_to: copilot-vps
related: 2026-05-07-026 (mention detection validated H1), 2026-05-07-021 (F-NEW fix Vertex primary), notion-governance plan O15.1b smoke 2026-05-07T16:25Z PASS PARCIAL, ADR notion-governance/docs/architecture/16-multichannel-rick-channels.md (referencia local en docs/external-context/adr-16-multichannel-rick-channels.md)
priority: high
deadline: 2026-05-10
estimated_turns: 1-2
---

# Diagnose POST /run 400 — task type `rick.orchestrator.triage`

## Contexto

Smoke real O15.1b ejecutado 2026-05-07T16:25Z (13:25 ART). David posteó plain text `@Rick ping worker /health y devolveme el JSON acá como reply` en Control Room (Notion page id `30c5f443fb5c80eeb721dc5727b20dca` = página "OpenClaw").

**Canal Notion: PASS end-to-end ✅**

Evidencia VPS extraída por Copilot Chat 2026-05-07T16:30Z:

```
13:25:51,353 [INFO] dispatcher.rick_mention: Rick mention routed:
  comment=3595f443 author=1e3d872b page=? trace=f04510d8

13:25:51,346 [INFO] dispatcher.queue: Dequeued task 9574eb63b4b346cab89b1965111912b0
13:25:51,398 [INFO] dispatcher.service: [worker 1] Executing task 9574eb63b4b346cab89b1965111912b0
  (task=rick.orchestrator.triage, team=rick-orchestrator, model=azure_foundry) -> VPS

13:25:51,512 [INFO] httpx: HTTP Request: POST http://127.0.0.1:8088/run "HTTP/1.1 400 Bad Request"
13:25:51,521 [INFO] dispatcher.service: [escalation] Skipping non-canonical failure for task 9574eb63...
  (source=notion-poller, source_kind=notion.comment.mention)
13:25:51,522 [ERROR] dispatcher.service: [worker 1] Task 9574eb63... failed:
  Client error '400 Bad Request' for url 'http://127.0.0.1:8088/run'
```

Reply en Control Room con autor "Rick" (integration bot, NO guest "Invitado") confirmado en screenshot — write-back al canal funciona, identidad visible es la correcta:

```
Rick: ⚠️ Tarea fallida
Task: rick.orchestrator.triage | Team: rick-orchestrator | Type: triage
Error: Client error '400 Bad Request' for url 'http://127.0.0.1:8088/run'
Model: n/a
ID: 9574eb63b4b346cab89b1965111912b0
```

**Bug aislado a downstream worker /run**, NO al canal Notion. Otros task types (`notion.poll_comments` etc) hacen POST /run consistentemente con `200 OK` en el mismo journal:

```
13:28:12 [INFO] HTTP Request: GET https://api.notion.com/v1/comments?... "HTTP/1.1 200 OK"
INFO:     127.0.0.1:33214 - "POST /run HTTP/1.1" 200 OK
```

→ El 400 es específico al payload del task type `rick.orchestrator.triage`.

## Detalle ⚠️ a verificar

El log dispatch dice `model=azure_foundry`, NO `google-vertex/gemini-3.1-pro-preview`. Esto contradice lo esperado post-task 021 (donde `agents.list[id=="rick-orchestrator"].model.primary` se setteó a Vertex).

Hipótesis preliminares:
- **HA**: El dispatcher resuelve el modelo del task type por una ruta distinta a `agents.list[].model.primary` (probablemente `team_workflows.yaml`, default por team, o hardcoded en el dispatcher para `rick.orchestrator.triage`). El fix de task 021 NO engaging para esta ruta de invocación.
- **HB**: El payload generado por la rama `azure_foundry` es schema-incompatible con el endpoint `/run` del worker (faltan campos requeridos o tienen tipos inválidos).
- **HC**: El worker rechaza el `team=rick-orchestrator` específicamente (autorización, registry, etc.).
- **HD**: F-NEW reincidente — Azure pre-block del modelo retorna 400 (no 200 + canned refusal como en F-NEW original). Menos probable porque el fingerprint clásico era `200 OK + usage:null + canned refusal text`, no 400.

## Restricciones duras

- **NO restart gateway**: Vertex Fase 1 estabilidad ventana activa hasta 2026-05-14.
- **NO tocar `openclaw.json`** ni `model.primary`.
- **NO inline fix**: este task es **diagnóstico read-only** + propuesta. Si el fix es trivial y obvio (e.g., un campo missing en el payload del dispatcher), proponerlo en el report y abrir task 032 separado para aplicación + restart si aplicara.
- **F-INC-002 vigente**: `git fetch + log origin/main..HEAD + log HEAD..origin/main` antes pull/push.
- **`secret-output-guard` regla #8**: NUNCA imprimir tokens (Notion, Azure, Vertex, GitHub) en logs/reports/commits. Usar fingerprint o nombre de env var.
- **SOUL Reglas 21+22**: si una herramienta requerida falta o no podés reproducir el error real, reportá el gap honestamente — NO inventes payloads ni respuestas para satisfacer gobernanza performativamente.

## Procedimiento

### Bloque 0 — Pre-flight

```bash
cd ~/umbral-agent-stack
git fetch origin
git log --oneline origin/main..HEAD ; echo "(ahead)"
git log --oneline HEAD..origin/main ; echo "(behind)"
git pull --ff-only origin main 2>&1 | tail -3
```

### Bloque 1 — Capturar payload exacto del POST /run que retornó 400

El task `9574eb63b4b346cab89b1965111912b0` ya está fail-flagged en la queue. Para capturar el payload exacto:

1. Inspeccionar el dispatcher para identificar dónde construye el body del POST /run para task type `rick.orchestrator.triage`. Probables ubicaciones:
   - `dispatcher/service.py` (worker dispatch loop)
   - `dispatcher/orchestrator_router.py` o similar
   - `dispatcher/payloads.py` o `dispatcher/run_builder.py`
2. Loguear el payload (sanitizado, sin tokens) que se hubiera enviado para ese task — ya sea:
   - Replay del task desde la queue (si `dispatcher` soporta replay sin re-encolar permanente).
   - Build dry-run del payload con los mismos parámetros (`task_id=9574...`, `team=rick-orchestrator`, `type=triage`, `source=notion-poller`, `source_kind=notion.comment.mention`).
   - Si nada de lo anterior es posible sin restart, leer el código y **reconstruir el payload manualmente** documentando cada campo.
3. Hacer POST manual contra el worker con ese payload y capturar el body de la response 400:
   ```bash
   curl -X POST http://127.0.0.1:8088/run \
     -H "Authorization: Bearer $WORKER_TOKEN" \
     -H "Content-Type: application/json" \
     -d @/tmp/031/payload-9574.json \
     -i 2>&1 | head -50
   ```
   El response body del 400 debería decir qué campo falta o falla validation (FastAPI/Pydantic devuelve detalles en JSON).

Output bloque 1: `/tmp/031/payload-and-400-response.md` con (a) payload sanitizado JSON, (b) response 400 completa.

### Bloque 2 — Code archeology del routing model `azure_foundry` vs Vertex

1. `grep -rn "azure_foundry" dispatcher/ openclaw/ config/` — identificar dónde se decide ese provider para `rick.orchestrator.triage`.
2. Leer `config/team_workflows.yaml` (si existe) y `config/teams.yaml` para ver si hay model override por team o type.
3. Leer dispatcher routing logic — entender el orden de precedencia: `task.model > team_workflow.model > team.model > openclaw.json agents.list[].model.primary > default`.
4. Confirmar que el fix de task 021 (Vertex en `agents.list[].model.primary`) NO está siendo override por una ruta superior para este task type.

Output bloque 2: `/tmp/031/model-routing.md` con (a) cadena de precedencia, (b) por qué `azure_foundry` ganó para `rick.orchestrator.triage`, (c) si es bug o by-design.

### Bloque 3 — Validar hipótesis HA/HB/HC/HD

Combinar bloques 1+2 para concluir cuál hipótesis es la correcta:

- Si bloque 1 muestra response 400 con `detail: "field 'X' is required"` o similar → **HB** (schema mismatch), recomendar fix dispatcher.
- Si bloque 1 muestra response 400 con `detail` apuntando a `team` o autorización → **HC**, recomendar fix worker registry o team config.
- Si bloque 1 muestra response 400 con texto del modelo (azure content filter o similar) → **HD**, F-NEW reincidente — vincular con sección F-NEW del plan.
- Si bloque 2 muestra que el modelo override correcto sería Vertex y el bug es solo el routing → **HA**, recomendar fix config (sin tocar `openclaw.json` si se puede via `team_workflows.yaml`).

Output bloque 3: `/tmp/031/verdict.md` con hipótesis confirmada + 1-line root cause + propuesta de fix mínimo.

### Bloque 4 — Smoke de regresión post-diagnóstico (opcional, sin restart)

Si bloque 3 propone un fix que NO requiere restart gateway (e.g., editar `team_workflows.yaml` que se relee en cada poll), aplicarlo y pedir a David que repita el `@Rick ping worker /health` smoke.

Si requiere restart o edit `openclaw.json` → DIFERIR a task 032 (NO consumir restart durante Vertex Fase 1).

### Bloque 5 — Capitalizar

Append-only en `.agents/board.md`:

```
## 2026-05-07-031 — diagnose orchestrator triage 400 (smoke O15.1b)
- status: <done | blocked | partial>
- hipótesis confirmada: <HA|HB|HC|HD>
- root cause: <1-line>
- fix propuesto: <comando o edit, sin aplicar si requiere restart>
- requires restart? <yes/no>
- task 032 follow-up? <yes/no — para qué>
- evidencia: /tmp/031/*.md
- F-INC-002: clean pre y post push
- secret-output-guard: respetado (ningún token impreso)
- SOUL Reglas 21+22: <respetadas / N/A>
```

Commit en branch `copilot-vps/031-diagnose-orchestrator-triage-400` + PR a main:

```
task(031): diagnose POST /run 400 rick.orchestrator.triage — hipótesis <X>
confirmada, root cause <Y>, fix propuesto <Z> (NO aplicado, requires restart=<yes/no>);
canal Notion confirmado PASS end-to-end (mention H1 + dispatch + write-back con autor
Rick integration); F-INC-002 verificado, model.primary intacto, gateway pid 75421
sin restart, Vertex Fase 1 ventana respetada
```

## Criterios de done

- [ ] Payload exacto del POST /run (sanitizado) capturado y archivado.
- [ ] Response body del 400 capturada y leída.
- [ ] Cadena de precedencia de model routing documentada.
- [ ] Hipótesis confirmada (HA/HB/HC/HD) con evidencia.
- [ ] Fix propuesto (sin aplicar si requiere restart).
- [ ] Board actualizado.
- [ ] Commit + PR a main.
- [ ] NO restart consumido en este task.

## NO hacer

- ❌ NO restart gateway.
- ❌ NO editar `openclaw.json` ni `model.primary`.
- ❌ NO aplicar fix inline si requiere restart — diferir a task 032.
- ❌ NO inventar payload o response si no podés reproducirlos — reportar gap honestamente.
- ❌ NO imprimir tokens.
- ❌ NO escribir en `~/.openclaw/trace/delegations.jsonl` entries fabricadas (SOUL Regla 21).

---

## Log de cierre — 2026-05-07T17:50Z (Copilot VPS)

### Resultado: ✅ done (read-only diagnosis; fix DIFERIDO a task 032 por diseño de handler)

### B0 Pre-flight ✅

- F-INC-002: ahead 0, behind 2 (commits 030 + 031); pull --ff-only OK; nuevo branch `copilot-vps/031-diagnose-orchestrator-triage-400` desde `main` post-pull.
- Working tree limpio salvo leftovers task 013-K (reports/) NO incluidos en commit.

### B1 Payload + response 400 ✅ (reproducido empíricamente)

`curl -X POST http://127.0.0.1:8088/run` con payload reconstruido idéntico al que produce `dispatcher/rick_mention.py` para task `9574eb63b4b346cab89b1965111912b0` → **HTTP 400** con detail Pydantic exacto:

```
"detail":"Invalid request body: 2 validation errors for TaskEnvelope
  team       — Input should be 'marketing'|'advisory'|'improvement'|'lab'|'system' [input='rick-orchestrator']
  task_type  — Input should be 'coding'|'writing'|'research'|'critical'|'ms_stack'|'general' [input='triage']"
```

Evidencia completa en `/tmp/031/payload-and-400-response.md` (response body 514 bytes capturado). Token NUNCA impreso (solo `len=48` para `WORKER_TOKEN`).

### B2 Code archeology model routing ✅

`model=azure_foundry` viene del `dispatcher.model_router`, NO del gateway OpenClaw:

1. `task_type="triage"` no está en `DEFAULT_ROUTING` ni en `config/quota_policy.yaml`.
2. `_normalize_task_type("triage")` → `"general"`.
3. `routing["general"].preferred = "azure_foundry"`.

`agents.list[].model.primary` (Vertex post-task-021) **no se consulta** desde el dispatcher. Solo se consultaría si el handler hipotético `rick.orchestrator.triage` invocara al subagente vía OpenClaw gateway. **No hay regresión del task 021.** Detalles en `/tmp/031/model-routing.md`.

### B3 Verdict ✅

- **HB primaria** confirmada (Pydantic enum mismatch en `team` y `task_type`).
- **HA secundaria** confirmada (model routing path independiente de openclaw.json).
- **HC latente** confirmada (handler `rick.orchestrator.triage` no existe en `TASK_HANDLERS`).
- **HD descartada** (Azure nunca se invocó; 400 es FastAPI validation pre-dispatch).

**Root cause (1 línea)**: Ola 1b (`dispatcher/rick_mention.py`) introdujo un envelope con `team="rick-orchestrator"` + `task_type="triage"` + `task="rick.orchestrator.triage"` sin extender los enums `Team`/`TaskType` (`worker/models/__init__.py:43,51`) ni registrar el handler en `worker/tasks/__init__.py:TASK_HANDLERS`.

### B4 Smoke regresión ⏸ DIFERIDO

Fix propuesto requiere:

- Restart del **worker** (`umbral-worker`) — NO del gateway. Vertex Fase 1 intacta.
- Implementación nueva del handler `handle_rick_orchestrator_triage` (decisión de diseño: ¿proxy al subagente OpenClaw vía CLI/API, o pipeline interno con `llm.generate`?).
- Tests del handler.
- Coordinación con David para repetir smoke `@Rick ping worker /health`.

→ **Diferido a task 032** (no es trivial; spec del task 031 explícitamente pide diferir si requiere restart o feature work).

### B5 Capitalización ✅

- `.agents/board.md`: nueva entrada `## 2026-05-07-031` con verdict, evidence paths, restart requirement, follow-up task 032 anotado.
- Branch: `copilot-vps/031-diagnose-orchestrator-triage-400`.
- Commit + PR: ver final del log de cierre.

### Files modificados (este commit)

- `.agents/tasks/2026-05-07-031-copilot-vps-diagnose-orchestrator-triage-400.md` (status pending → done + log).
- `.agents/board.md` (append entry 031).

### Files NO modificados (out of scope / preservados)

- `dispatcher/rick_mention.py` — código de producción Ola 1b, NO tocar (fix va en task 032).
- `worker/models/__init__.py` — fix de enums DIFERIDO a task 032.
- `worker/tasks/__init__.py` — registro de handler DIFERIDO a task 032.
- `~/.openclaw/openclaw.json` — `agents.list[].model.primary` Vertex intacto (Vertex Fase 1).
- `~/.config/openclaw/env` — read-only.

### Working notes locales (NO commiteadas)

- `/tmp/031/payload-9574.json` — payload sanitizado del POST /run reproducido.
- `/tmp/031/response-400.txt` — response body completo del 400.
- `/tmp/031/payload-and-400-response.md` — análisis B1.
- `/tmp/031/model-routing.md` — análisis B2.
- `/tmp/031/verdict.md` — verdict B3 + fix proposal.

### Salvavidas honrados

- ✅ Gateway pid 75421 sin restart (no se ejecutó ningún `systemctl restart openclaw-gateway`).
- ✅ `openclaw.json` y `model.primary` intactos (no se editaron).
- ✅ No inline fix aplicado; diferido a task 032 con scope explícito.
- ✅ F-INC-002 verificado pre-pull y pre-push.
- ✅ `secret-output-guard` regla #8: ningún token impreso (`WORKER_TOKEN`, `NOTION_API_KEY`, etc. solo referenciadas por nombre o longitud).
- ✅ SOUL Reglas 21+22: 400 reproducido con curl real, payload reconstruido del código (NO inventado), response body capturado tal cual; verdict apoyado en evidencia verificable.
