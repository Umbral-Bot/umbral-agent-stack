# Bugs y Edge Cases — Análisis de Riesgos Técnicos
> Auditoría: 2026-03-05 | Branch: `claude/090-implementar-notion-bitacora`
> Origen: Top 10 riesgos de `01-mapa.md`, revisión directa de código

**Severidad**: P0 = pérdida de datos / bloqueo total | P1 = comportamiento incorrecto silencioso | P2 = degradado / inconsistencia

---

## Tabla priorizada

| # | Sev | Origen (riesgo) | Archivo | Línea | Problema | Fix sugerido |
|---|-----|-----------------|---------|-------|----------|--------------|
| 1 | **P0** | R3 — Sync handlers bloquean event loop | `worker/app.py` | 270 | `handler(envelope.input)` es síncrono llamado directamente en `async def run_task`. Bloquea el event loop de asyncio, no solo un thread del pool. Durante un `llm.generate` de 30 s, TODAS las peticiones entrantes se estancan. | Envolver con `await asyncio.get_event_loop().run_in_executor(None, handler, envelope.input)` o definir el endpoint como síncrono para que uvicorn lo corra en su threadpool automáticamente. |
| 2 | **P0** | R3 — Sync handlers bloquean event loop | `worker/app.py` | 270 | Mismo problema en `/enqueue`: el endpoint es `async def enqueue_task` pero llama a `queue.enqueue(envelope)` (Redis IO síncrono) sin executor. Bloquea el event loop durante escrituras Redis lentas. | Igual que arriba: `run_in_executor` o cambiar a sync endpoint. |
| 3 | **P0** | R7 — In-memory store / R4 acoplamiento | `worker/app.py` | 234–238 | `sanitize_input(envelope.input)` se llama pero su valor de retorno **se descarta**. La función crea una copia sanitizada (strings truncados), pero `envelope.input` sigue apuntando al dict original sin sanitizar. El handler recibe el input no sanitizado. Solo se detectan errores de tamaño (ValueError), no se aplica truncado de campos. | Capturar el retorno: `envelope.input = sanitize_input(envelope.input)`. Igual en `/enqueue` línea 358. |
| 4 | **P0** | R7 — In-memory store | `dispatcher/queue.py` | 107–111 | `dequeue()`: si la key `umbral:task:{task_id}` expiró entre el `BRPOP` del item (que sí ocurrió) y el `GET` del envelope completo, la función retorna `None`. El item ya fue consumido de `QUEUE_PENDING` y la tarea **se pierde silenciosamente** para siempre. El `retry_count` ni siquiera se registra. | Ante `full_raw is None` tras BRPOP exitoso: loguear como `task_failed`, registrar en ops_log, y no retornar `None` sin trazabilidad. Alternativamente, guardar el envelope completo en el item de la cola para recuperación. |
| 5 | **P1** | R5 — ops_log / observabilidad | `dispatcher/service.py` | (ninguna) | `ops_log.task_queued(...)` existe en `infra/ops_logger.py` (línea 56) pero **nunca se invoca** en `service.py` ni en `queue.py`. El primer evento del ciclo de vida es `model_selected`. Imposible calcular latencia de espera en cola ni detectar tareas huérfanas. | Llamar `ops_log.task_queued(task_id, task, team, task_type, trace_id)` justo después del `queue.enqueue()` en `worker/app.py` línea 394 (endpoint `/enqueue`) y en `dispatcher/service.py` si hay enqueue directo. |
| 6 | **P1** | R4 — Acoplamiento circular | `worker/app.py` | 390, 478, 514, 542, 611 | Imports inline de `dispatcher.*` dentro de funciones de endpoint (`from dispatcher.queue import TaskQueue`, etc.). Si el worker se despliega sin el package `dispatcher` (Docker mínimo, VM Windows sin el paquete), lanza `ImportError` en runtime al acceder a `/enqueue`, `/task/history`, `/scheduled`, `/quota/status`, `/providers/status`. No hay fallback: el endpoint devuelve 500 sin mensaje claro. | Envolver cada import en `try/except ImportError` y devolver `503 Service Unavailable` con mensaje explícito, o mover la lógica compartida a un paquete común independiente de `dispatcher`. |
| 7 | **P1** | R1 — Notion enrich (R2 en esta revisión) | `worker/notion_client.py` | 787–810 | `_convert_block_for_write` acepta un parámetro `client: Any` pero nunca lo usa. Los bloques con `has_children=True` (toggle, listas anidadas) son copiados sin sus hijos: `prepend_blocks_to_page` los re-escribe vacíos. Los subbloques se pierden silenciosamente sin error. | Implementar fetch recursivo de hijos: si `block.get("has_children")` es True, llamar `GET /blocks/{block_id}/children` con el `client` y agregar los hijos en `children` del resultado. |
| 8 | **P1** | R4 — Acoplamiento / R7 | `dispatcher/queue.py` | 134–143 | `block_task()`: usa `lrange` + `lrem` — no atómico. Entre el `lrange` y el `lrem`, un worker puede hacer `brpop` y ejecutar la tarea igualmente. La tarea se bloquea en Redis pero ya está siendo ejecutada. El `lrem` sobre un item ya consumido es no-op (correcto), pero el bloqueo llega tarde: la tarea corrió. | Usar un Lua script atómico (EVAL) para `lrange`+`lrem` como unidad, o alternativamente no intentar remover de QUEUE_PENDING (el item ya fue consumido por brpop) y solo actualizar el key de estado. |
| 9 | **P1** | R6 — Token compartido | `worker/app.py` | 183 | `parts[1] != WORKER_TOKEN` usa comparación directa de strings (`!=`), no comparación en tiempo constante. Vulnerable a timing attacks: un atacante puede medir microsegundos para adivinar el token carácter a carácter. Baja probabilidad de explotación real (red privada Tailscale), pero no hay defensa. | Usar `hmac.compare_digest(parts[1], WORKER_TOKEN)` en lugar de `!=`. |
| 10 | **P1** | R1 — Notion enrich | `worker/notion_client.py` | 183 | `poll_comments`: el filtro `since` usa comparación léxica de strings: `if since and created < since: continue`. Funciona solo si ambas fechas tienen el mismo formato exacto (ambas `Z` o ambas `+00:00`). Notion devuelve `2026-03-05T10:00:00.000Z` (con milisegundos); si `since` llega como `2026-03-05T10:00:00Z` (sin milisegundos), la comparación falla para el mismo instante. Además no hay paginación: máx 100 comentarios retornados, los anteriores se pierden silenciosamente. | Parsear ambas fechas con `datetime.fromisoformat()` antes de comparar. Implementar cursor-based pagination (`next_cursor` de la respuesta). |
| 11 | **P1** | R8 — weasyprint | `worker/tasks/document_generator.py` | 141–146 | `_pdf_from_html` lanza `RuntimeError` si `weasyprint` no está disponible (OSError por librerías de sistema: Cairo, Pango). El error no es descriptivo desde la perspectiva del caller (`/run` devuelve HTTP 500). En el CI ubuntu-latest no se instalan paquetes de sistema, por lo que `document.create_pdf` con `html_content` **nunca se prueba en CI** y puede fallar silenciosamente en producción. | Agregar a CI: `sudo apt-get install -y libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0`. Documentar en README que `document.create_pdf` (modo HTML) requiere estos paquetes. Considerar devolver `{"ok": False, "error": "..."}` en lugar de `RuntimeError` para consistencia con otros handlers. |
| 12 | **P1** | R5 — ops_log | `dispatcher/queue.py` | 46–83 | `enqueue()` guarda en el item de `QUEUE_PENDING` solo los campos `{task_id, task, team, task_type, queued_at}`. El `callback_url` y `trace_id` quedan solo en el key completo `umbral:task:{task_id}`. Si ese key expira (7 días TTL) antes de que la tarea corra, el `dequeue()` retorna `None` (ver bug #4). Pero más importante: el `callback_url` del item de cola se pierde si el key expira; el Dispatcher nunca puede hacer el callback. | Incluir `callback_url` y `trace_id` en el item de `QUEUE_PENDING` para recuperación de emergencia. |
| 13 | **P2** | R2 — Dual RateLimiters | `worker/app.py` | 144; `worker/config.py` | 43 | Dos env vars distintas para la misma funcionalidad: `RATE_LIMIT_RPM` (leída en `app.py` con default 60) y `WORKER_RATE_LIMIT_PER_MIN` (en `config.py` con default 120). `rate_limit.py` lee `WORKER_RATE_LIMIT_PER_MIN` pero la app usa `rate_limiter.py` con `RATE_LIMIT_RPM`. `rate_limit.py` es dead code en producción pero importado en tests. Un operador que configure `WORKER_RATE_LIMIT_PER_MIN` no verá ningún efecto. | Unificar a una sola env var (`RATE_LIMIT_RPM`). Eliminar `rate_limit.py` o integrar en `rate_limiter.py`. Actualizar tests que importen `rate_limit` directamente. |
| 14 | **P2** | R5 — ops_log | `dispatcher/quota_tracker.py` | 43–50 | `_ensure_window()` lee y escribe en dos steps no atómicos: `GET key_end` → evaluar expiración → `PIPELINE SET`. Con N workers en paralelo, todos pueden ver `end_raw=None` simultáneamente y ejecutar el reset. El resultado es múltiples resets solapados: el contador se pone a 0 mientras otro worker ya estaba incrementándolo. En la práctica el error es pequeño (máx N requests perdidos del contador), pero puede llevar a cuota más permisiva de lo real. | Usar `SET key_end ... NX` (set-if-not-exists) o un Lua script atómico para reset de ventana. |
| 15 | **P2** | R4 — Acoplamiento | `worker/notion_client.py` | 492–513 | `update_dashboard_page()` lista todos los bloques hijos para borrar, pero excluye solo `child_page` (`b.get("type") != "child_page"`). No excluye `child_database`. Si el Dashboard tiene una linked database embebida, la función la elimina (mueve a trash). Aunque improbable en uso actual, es un bug silencioso difícil de depurar. | Excluir también `child_database` del borrado: `b.get("type") not in ("child_page", "child_database")`. |
| 16 | **P2** | R10 — Model IDs ficticios | `dispatcher/service.py` | 33–50; `worker/app.py` | 581–590 | `PROVIDER_MODEL_MAP` contiene strings como `"gpt-5.3-codex"`, `"gemini-3.1-pro-preview-customtools"`, `"gemini-flash-latest"` que no corresponden a model IDs reales de ninguna API pública. Si `llm.generate` o `composite.research_report` alguna vez llama realmente a una API LLM con estos strings, la petición fallará. El router de modelos funciona declarativamente pero el string de modelo que llega al handler es inválido. | Auditar y actualizar los model IDs contra las APIs reales: Anthropic SDK usa `claude-sonnet-4-5`, OpenAI usa `gpt-4o`, Google usa `gemini-1.5-pro`. Alternativamente, documentar explícitamente que estos son aliases internos que el handler `llm.generate` mapea internamente. |
| 17 | **P2** | R7 — In-memory store | `worker/app.py` | 779–796 | `GET /tasks` (lista reciente): el filtro `team` usa `t.task.startswith(team) or team in str(t.task_id)`. `t.task_id` es un UUID; buscar un team en un UUID siempre devuelve `False` salvo casualidad. La segunda condición (`team in str(t.task_id)`) es semánticamente incorrecta y puede producir falsos positivos si el nombre del team coincide con una subsecuencia del UUID. | Reemplazar por comparar con `t.task` (nombre de la tarea-handler) o agregar el campo `team` al `TaskResult` model. |

---

## Detalle por riesgo de origen

### R1 — `notion.enrich_bitacora_page` (RESUELTO en PR #96)
Las 9 funciones faltantes documentadas en `docs/bitacora-scripts.md` están implementadas en este branch (`worker/notion_client.py` y `worker/tasks/notion.py`). **Este riesgo queda cerrado al mergear PR #96.** Bugs residuales: #7 (`_convert_block_for_write` pierde hijos) y #10 (date comparison frágil en `poll_comments`).

---

### R2 — Dual RateLimiter
**Bug #13**: `RATE_LIMIT_RPM` vs `WORKER_RATE_LIMIT_PER_MIN` — un env var es dead code.

Confirmado en código:
- `app.py:144`: `rpm = int(os.environ.get("RATE_LIMIT_RPM", "60"))`
- `config.py:43`: `WORKER_RATE_LIMIT_PER_MIN: int = int(os.environ.get("WORKER_RATE_LIMIT_PER_MIN", "120"))`
- `rate_limit.py:22`: `_configured_limit = _cfg` (lee `WORKER_RATE_LIMIT_PER_MIN`)

`rate_limit.py` importado en tests pero nunca por `app.py`. La app siempre usa `rate_limiter.py`.

---

### R3 — Handlers síncronos bloquean event loop
**Bugs #1 y #2** — el más crítico del inventario.

```python
# app.py:270 — BLOQUEA el event loop de asyncio
async def run_task(...):
    ...
    result_data = handler(envelope.input)  # ← sync call en async def
```

Con uvicorn + asyncio, llamar una función síncrona bloqueante directamente en un `async def` **detiene el event loop completo**. No se sirve ninguna otra petición hasta que el handler retorne. Para handlers rápidos (ping, add_comment) el impacto es mínimo. Para `llm.generate`, `document.create_pdf` (weasyprint), `composite.research_report`, el bloqueo puede durar 30-120 segundos.

Fix mínimo:
```python
import asyncio
result_data = await asyncio.get_event_loop().run_in_executor(None, handler, envelope.input)
```

---

### R4 — Acoplamiento circular worker→dispatcher
**Bug #6** — runtime `ImportError` sin fallback.

```python
# app.py:390 (inline import en endpoint /enqueue)
from dispatcher.queue import TaskQueue
# app.py:478 (inline import en /task/history)
from dispatcher.task_history import TaskHistory
```

El Worker se puede desplegar sin `dispatcher/` en el PYTHONPATH (VM Windows minimal install). Los endpoints críticos fallan con 500 sin mensaje informativo.

---

### R5 — `task_queued` nunca emitido
**Bugs #5 y #12** — punto ciego en observabilidad.

`OpsLogger.task_queued()` existe (ops_logger.py:56) pero ningún caller en service.py ni queue.py lo invoca. El ciclo de vida visible empieza en `model_selected`, no en el encolado. Consecuencias:
- Imposible calcular tiempo de espera en cola
- Imposible detectar tareas encoladas pero nunca procesadas
- Scripts de OODA report y governance metrics tienen datos incompletos

---

### R6 — Token compartido
**Bug #9** — timing attack teórico.

```python
# app.py:183
if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != WORKER_TOKEN:
```

`parts[1] != WORKER_TOKEN` es O(n) con early-exit en la primera diferencia. Riesgo práctico bajo (red Tailscale privada) pero no sigue best practices.

---

### R7 — In-memory store no persiste
**Bug #4** — pérdida silenciosa de tareas.

El escenario es:
1. Tarea encolada → item en `QUEUE_PENDING` + key `umbral:task:{id}`
2. Key expira prematuramente (Redis memory pressure + eviction, o borrado manual)
3. Dispatcher hace `brpop` → obtiene item de la cola
4. `redis.get(task_key)` → None
5. `return None` → `service.py` hace `continue`
6. La tarea desapareció. Sin log de fallo, sin callback, sin Linear issue.

**Bug #17** — filtro de `/tasks` semánticamente incorrecto.

---

### R8 — weasyprint en CI
**Bug #11** — `document.create_pdf` con HTML no se prueba en CI.

En `.github/workflows/test.yml` no hay `apt-get install` de librerías de sistema. Cualquier test que llame `_pdf_from_html` con `html_content` fallará en CI con `OSError: cannot load library 'libgobject-2.0.so.0'`. Los tests actuales de `test_document_generator.py` probablemente mockan la importación o usan solo el modo `text_content`. Riesgo: el modo HTML nunca se valida.

---

### R9 — Sprints S5-S7 pendientes
No generan bugs de código propiamente dichos, pero documentar:
- `windows.pad.run_flow`: handler registrado; implementación en `worker/tasks/windows.py` existe pero llama a Power Automate Desktop local — no hay modo fallback, no hay timeout configurado.
- `llm.generate`: si no hay LiteLLM disponible (VPS sin configurar), el handler probablemente lanza excepción sin contexto útil.

---

### R10 — Model IDs ficticios
**Bug #16** — strings inválidos para APIs reales.

`"gpt-5.3-codex"` no existe en OpenAI/Azure API; `"gemini-3.1-pro-preview-customtools"` no existe en Google AI Studio. Cualquier llamada real a LLM con estos strings fallará con un error 404/model_not_found de la API.

---

## Resumen por severidad

| Severidad | Count | Bugs |
|-----------|-------|------|
| **P0** — Pérdida datos / bloqueo total | 3 | #1, #2, #3 (sanitize descartado), #4 (tarea perdida) |
| **P1** — Comportamiento incorrecto silencioso | 8 | #5, #6, #7, #8, #9, #10, #11, #12 |
| **P2** — Degradado / inconsistencia | 5 | #13, #14, #15, #16, #17 |

**Top 3 a corregir primero:**
1. **#3 (P0)** — `sanitize_input` descartado: 1 línea de fix, impacto seguridad
2. **#1/#2 (P0)** — handlers síncronos en event loop: corregir con `run_in_executor`
3. **#4 (P0)** — tarea perdida silenciosamente en TTL expiry: agregar log + callback de fallo
