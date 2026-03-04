# Hackathon: Resiliencia del Dispatcher + Notion Poller clasificador

**Assigned:** claude-code  
**Priority:** P0  
**Status:** done
**Updated:** 2026-03-04
**Created:** 2026-03-04

## Contexto

Claude Code (Opus 4.6) se une al hackathon como cuarto agente. El sistema tiene un flujo e2e funcional (Enqueue → Dispatcher → Worker → Complete), pero necesita mayor resiliencia y un Poller más inteligente.

## Tareas

### A. Resiliencia del Dispatcher (prioridad alta)

El Dispatcher actual tiene varios puntos frágiles:

1. **Hacer `_notion_upsert` y `_notify_linear_completion` realmente fire-and-forget**:
   - En `dispatcher/service.py`, las funciones `_notion_upsert()` y `_notify_linear_completion()` ya tienen try/except, pero el Worker VPS se cae cuando la DB Kanban de Notion no existe (404).
   - Envolver las llamadas a estas funciones en `threading.Thread(target=..., daemon=True).start()` para que no bloqueen ni retrasen el flujo principal.

2. **Retry automático para tareas fallidas por timeout**:
   - En `_run_worker()`, cuando una tarea falla con "timed out", re-encolarla automáticamente (máximo 2 retries).
   - Agregar campo `retry_count` al envelope y verificar antes de re-encolar.
   - Loguear el retry en OpsLogger: `ops_log.task_retried(task_id, task, team, retry_count)`.

3. **Graceful handling de Worker caído**:
   - Si el Worker VPS devuelve connection refused (no solo timeout), loguear y esperar 5s antes de reintentar el dequeue.
   - Evitar loops de error que generen miles de líneas de log.

### B. Notion Poller inteligente — clasificación de intención

El Notion Poller actual (`dispatcher/notion_poller.py`) solo responde "Rick: Recibido." sin procesar el contenido. Mejorarlo:

1. **Clasificar la intención del comentario**:
   - Parsear el texto del comentario de David.
   - Usar heurísticas por keywords:
     - Contiene "haz", "crea", "revisa", "genera", "busca", "investiga" → tipo `tarea`
     - Contiene "?" → tipo `pregunta`
     - Contiene "configura", "cambia", "actualiza", "instala" → tipo `instrucción`
   - Mapear a equipo según keywords:
     - "mercado", "clientes", "ventas", "marketing", "embudo" → `marketing`
     - "BIM", "construcción", "tendencias", "arquitectura" → `advisory`
     - "código", "deploy", "fix", "test", "sistema" → `improvement`
     - Otro → `system`

2. **Encolar tarea al equipo correcto**:
   - Si es `tarea`: crear TaskEnvelope y encolarlo en Redis vía `TaskQueue.enqueue()`.
   - Elegir task_type: "research" si menciona buscar/investigar, "writing" si menciona redactar/generar.

3. **Responder con contexto**:
   - En vez de "Rick: Recibido.", responder: "Rick: Entendido. Creé tarea [task] para equipo [team]. ID: [task_id]."
   - Si es pregunta: responder "Rick: Analizando tu pregunta..."

## Archivos relevantes

- `dispatcher/service.py` — loop principal (parte A)
- `dispatcher/notion_poller.py` — Poller actual (parte B)
- `dispatcher/queue.py` — TaskQueue.enqueue()
- `dispatcher/team_config.py` + `config/teams.yaml` — equipos
- `infra/ops_logger.py` — OpsLogger

## Notas de conectividad

- VPS accesible via SSH: `ssh rick@100.113.249.25` (via Tailscale)
- Worker VPS: `http://127.0.0.1:8088/health`
- Redis: `redis-cli ping` → PONG
- Env vars: `source ~/.config/openclaw/env`
- Notion Control Room page ID: `30c5f443fb5c80eeb721dc5727b20dca`

## Entrega

Responder en `.agents/board.md` con estado de la tarea y commit con los cambios.

## Log

### [claude-code] 2026-03-04

**Parte A — Resiliencia del Dispatcher: COMPLETADA**

Archivos modificados:
- `dispatcher/service.py` — 3 mejoras implementadas:
  1. **Fire-and-forget real**: Todas las llamadas a `_notion_upsert()` y `_notify_linear_completion()` ahora corren en `threading.Thread(daemon=True)`. Esto evita que un 404 de Notion o un error de Linear bloquee o retrase el worker thread principal. Aplica a 7 call sites (quota blocked, VM offline, running, done, failed × notion + linear).
  2. **Retry automático para timeouts**: Si una tarea falla con `httpx.ReadTimeout` o `httpx.WriteTimeout` y `retry_count < 2`, se re-encola automáticamente con `retry_count` incrementado. Máximo 2 retries. Se loguea via `ops_log.task_retried()`.
  3. **Graceful handling de connection refused**: Si el Worker devuelve `httpx.ConnectError`, se loguea una vez y se espera 5 segundos antes de continuar el loop. Evita miles de líneas de log por segundo cuando el Worker cae.
- `infra/ops_logger.py` — Nuevo método `task_retried(task_id, task, team, retry_count)` + docstring actualizado.

**Parte B — Notion Poller inteligente: YA COMPLETADA POR ANTIGRAVITY (tarea 006)**
- `dispatcher/intent_classifier.py` ya existe con clasificación de intención, ruteo por equipo, y generación de envelopes con respuestas contextuales.
- 33 tests unitarios puros pasan.
- No se duplicó trabajo.

**Tests:** 147 passed, 1 skipped (el fallo en `test_worker.py::TestRunAuth` es pre-existente y no relacionado).
