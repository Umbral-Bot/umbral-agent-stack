# 61 — Auditoría, Trazabilidad y Gobernanza

> **Fecha:** 2026-03-05  
> **Ronda:** 13 (R13)  
> **Autor:** cursor-agent-cloud  
> **Estado:** Análisis completo — gaps identificados, propuestas incluidas

---

## 1. Inventario de componentes de tracking

| # | Componente | Archivo(s) | Qué registra | Destino |
|---|-----------|------------|--------------|---------|
| 1 | **OpsLogger** | `infra/ops_logger.py` | `task_queued`, `task_completed`, `task_failed`, `task_blocked`, `task_retried`, `model_selected`, `quota_warning`, `quota_restricted`, `worker_health_change` | `~/.config/umbral/ops_log.jsonl` (append-only JSONL) |
| 2 | **TaskEnvelope** | `worker/models/__init__.py` | `task_id`, `trace_id` (UUID), `team`, `task_type`, `status`, `created_at`, `selected_model`, `callback_url` | Redis `umbral:task:{id}` (TTL 7 días) |
| 3 | **GET /task/{id}/status** | `worker/app.py` | `task_id`, `status`, `task`, `team`, `task_type`, `result`, `error`, `created_at`, `queued_at`, `started_at`, `completed_at` | Respuesta HTTP |
| 4 | **GET /task/history** | `worker/app.py`, `dispatcher/task_history.py` | Envelopes completos con filtros `hours`, `team`, `status`, paginación | Respuesta HTTP (incluye `trace_id` si presente) |
| 5 | **Notion upsert_task** | `worker/notion_client.py` | Task, Status, Team, Task ID, Result Summary, Error, Input Summary, Model, Created | Base de datos "Tareas Umbral" en Notion |
| 6 | **Langfuse Tracing** | `worker/tracing.py` | `model`, `provider`, `prompt`, `system`, `response_text`, `usage` (tokens), `duration_ms`, `task_id`, `task_type` | Langfuse Cloud (trace + generation) |
| 7 | **OODA Report** | `scripts/ooda_report.py` | Reporte semanal: Redis stats + Langfuse (traces, generations, tokens, latencia, cost) | Markdown / JSON (para Notion/Telegram) |
| 8 | **Quota Usage Report** | `scripts/quota_usage_report.py` | Uso de cuotas por provider, distribución de task_type, model completions/failures | stdout / JSON / Notion comment |
| 9 | **Dashboard Report VPS** | `scripts/dashboard_report_vps.py` | Worker health, Redis stats, quotas, teams, recent tasks, ops summary, uptime, errors, alerts | Notion Dashboard (via `notion.update_dashboard`) |
| 10 | **Effectiveness Report** | `scripts/effectiveness_report.py` | Tareas/día, success rate, por modelo, por equipo, por task_type, distribución worker | Markdown / JSON |
| 11 | **Redis Task Store** | `dispatcher/queue.py` | Envelopes en `umbral:task:{id}`, listas `umbral:tasks:pending`, `umbral:tasks:blocked` | Redis (TTL 7 días) |
| 12 | **Source field** | `dispatcher/linear_webhook.py`, `dispatcher/intent_classifier.py`, `dispatcher/smart_reply.py` | Campo `source` en envelope: `linear_webhook`, `notion_poller`, `smart_reply`, `workflow_engine` | Redis envelope (solo si el enqueuer lo establece) |

---

## 2. Análisis de gaps — Trazabilidad

### 2.1 Campos del OpsLogger vs. TaskEnvelope

| Campo | OpsLogger | TaskEnvelope | Gap |
|-------|-----------|--------------|-----|
| `task_id` | ✅ Sí | ✅ Sí | — |
| `trace_id` | ❌ No | ✅ Sí | **ALTO** — No se puede correlacionar un flujo end-to-end usando ops_log |
| `source` | ❌ No | ✅ Parcial (solo algunos enqueuers) | **ALTO** — No se puede auditar de dónde vino cada tarea |
| `team` | ✅ Sí | ✅ Sí | — |
| `task_type` | ✅ Parcial (solo `task_queued` y `model_selected`) | ✅ Sí | **MEDIO** — `task_completed` y `task_failed` no incluyen `task_type` |
| `model` | ✅ Sí (completed/failed) | ❌ Solo `selected_model` | — |
| `duration_ms` | ✅ Sí (completed) | ❌ No | — |
| `worker` | ✅ Sí (completed) | ❌ No | — |
| `input_summary` | ❌ No | ❌ No (input completo en Redis, TTL 7d) | **MEDIO** — Sin input para auditoría post-TTL |
| `result_summary` | ❌ No | ❌ No (result en Redis, TTL 7d) | **MEDIO** — Sin resultado para auditoría post-TTL |

### 2.2 Propagación de trace_id

| Etapa | trace_id presente? | Detalle |
|-------|-------------------|---------|
| Enqueue via Worker API (`/enqueue`) | ✅ Sí | Se genera UUID en TaskEnvelope |
| Enqueue via Linear webhook | ✅ Sí | Se genera UUID |
| Enqueue via Notion Poller / Smart Reply | ❌ No | Envelopes creados sin `trace_id` explícito (se genera nuevo pero no se propaga) |
| Dispatcher → Worker (via `WorkerClient.run()`) | ❌ **No** | `WorkerClient` envía solo `{"task": ..., "input": ...}` — el `trace_id` del envelope se pierde |
| Worker `/run` response | ✅ Sí | Pero es un `trace_id` **nuevo**, no el del envelope original |
| OpsLogger events | ❌ No | Ningún método acepta `trace_id` |
| Langfuse trace | ❌ No | Solo recibe `task_id` y `task_type`, no `trace_id` |
| Notion upsert_task | ❌ No | No almacena `trace_id` |
| GET /task/{id}/status | ❌ No | No devuelve `trace_id` |

**Conclusión:** `trace_id` está definido pero roto — no se propaga end-to-end.

### 2.3 Evento `task_queued` — Nunca se emite

`OpsLogger.task_queued()` existe como método pero no es invocado en ningún lugar del codebase. Solo se llaman: `task_completed`, `task_failed`, `task_blocked`, `task_retried`, `model_selected`.

---

## 3. Gaps identificados — Lista priorizada

| # | Gap | Impacto | Prioridad | Pregunta afectada |
|---|-----|---------|-----------|-------------------|
| G1 | `trace_id` no se propaga end-to-end (Dispatcher → Worker lo pierde) | No se puede auditar un flujo completo | **ALTO** | "¿Se puede rastrear un flujo completo?" |
| G2 | `trace_id` ausente en OpsLogger | ops_log no correlaciona con envelopes/Langfuse | **ALTO** | "¿Se puede correlacionar ops_log con Redis?" |
| G3 | `source` (origen) no se registra en OpsLogger ni en todos los enqueue paths | No se sabe de dónde vino cada tarea | **ALTO** | "¿De dónde vino cada tarea?" |
| G4 | `task_queued` nunca se emite | Falta el evento de inicio del ciclo de vida | **ALTO** | "¿Cuántas tareas se encolaron?" |
| G5 | `task_type` ausente en `task_completed` y `task_failed` | No se puede agregar por tipo en esos eventos | **MEDIO** | "¿Cuál fue la tasa de éxito por task_type?" |
| G6 | Sin retención/rotación de ops_log.jsonl | Archivo crece indefinidamente, riesgo de disco | **MEDIO** | — (operacional) |
| G7 | `input_summary` y `result_summary` no en ops_log | No hay audit trail post-TTL de Redis (7 días) | **MEDIO** | "¿Qué input/output se usó?" |
| G8 | Langfuse `trace_id` no correlacionado con envelope `trace_id` | Dos sistemas de trazabilidad desconectados | **MEDIO** | "¿Qué modelo usó cada tarea?" |
| G9 | `_task_id` y `_task_type` no propagados por Dispatcher a Worker para Langfuse | Langfuse traces con `task_id=None`, `task_type=None` | **MEDIO** | "¿Qué modelo usó cada team?" |
| G10 | GET /task/{id}/status no devuelve `trace_id` | No se puede trazar desde la API | **BAJO** | — |
| G11 | Notion upsert_task no almacena `trace_id` ni `source` | No se puede auditar en Notion | **BAJO** | — |
| G12 | `/enqueue` API no establece `source` automáticamente | Tareas encoladas via API no tienen origen | **BAJO** | "¿De dónde vino cada tarea?" |

---

## 4. Matriz de preguntas de gobernanza vs. capacidad actual

| # | Pregunta de gobernanza | ¿Se puede responder hoy? | Con qué datos | Con mejoras propuestas |
|---|------------------------|--------------------------|---------------|------------------------|
| P1 | ¿Cuántas tareas se ejecutaron por día/semana? | ✅ **Sí** | `ops_log` (`task_completed` + `task_failed`), `effectiveness_report.py` | — (ya cubierto) |
| P2 | ¿Cuál fue la tasa de éxito por task_type? | ⚠️ **Parcial** | `ops_log` solo tiene `task_type` en `model_selected`, no en `completed`/`failed` | Agregar `task_type` a `task_completed`/`task_failed` (G5) |
| P3 | ¿Qué modelo usó cada team? | ✅ **Sí** | `ops_log` (`task_completed` tiene `team` + `model`) | — |
| P4 | ¿Cuál es el tiempo medio por task? | ✅ **Sí** | `ops_log` (`task_completed` tiene `duration_ms`) | — |
| P5 | ¿De dónde vino cada tarea? | ❌ **No** | `source` solo en algunos envelopes de Redis (TTL 7d), no en ops_log | Agregar `source` a OpsLogger y a todos los enqueuers (G3) |
| P6 | ¿Qué input se usó (resumen)? | ⚠️ **Parcial** | `input_summary` en Notion (si se upsertea), `input` completo en Redis (TTL 7d) | Agregar `input_summary` truncado a ops_log (G7) |
| P7 | ¿Se puede auditar un flujo completo por trace_id? | ❌ **No** | `trace_id` existe en envelope pero no se propaga end-to-end, no está en ops_log ni Langfuse | Propagar `trace_id` end-to-end y registrar en ops_log + Langfuse (G1, G2, G8) |
| P8 | ¿Cuántas tareas se encolaron vs. ejecutaron? | ❌ **No** | `task_queued` nunca se emite | Emitir `task_queued` en Dispatcher al encolar (G4) |
| P9 | ¿Cuál es la latencia de LLM por provider? | ✅ **Sí** | Langfuse (si configurado), `ooda_report.py` agrega latencia por provider | — |
| P10 | ¿Cuál es el costo estimado por período? | ✅ **Sí** | `ooda_report.py` estima costo por tokens | — |

---

## 5. Propuestas de mejora

### P1 — Propagar `trace_id` end-to-end [ALTO]

**Archivos a modificar:**
- `client/worker_client.py` → Enviar `trace_id` y `task_type` en el payload a `/run`
- `worker/app.py` → Recibir y usar `trace_id` del payload si viene incluido
- `dispatcher/service.py` → Pasar `trace_id` del envelope al `WorkerClient.run()`

**Resultado:** Un solo UUID permite rastrear tarea desde enqueue → dispatch → worker → complete → Langfuse.

### P2 — Agregar `trace_id` y `source` a OpsLogger [ALTO]

**Archivo:** `infra/ops_logger.py`

Agregar parámetros opcionales `trace_id` y `source` a `task_queued`, `task_completed`, `task_failed`, `task_blocked`, `task_retried`:

```python
def task_completed(self, task_id, task, team, model, duration_ms,
                   worker="vps", trace_id=None, source=None, task_type=None):
    entry = { "event": "task_completed", "task_id": task_id, ... }
    if trace_id:
        entry["trace_id"] = trace_id
    if source:
        entry["source"] = source
    if task_type:
        entry["task_type"] = task_type
    self._write(entry)
```

### P3 — Emitir `task_queued` en Dispatcher [ALTO]

**Archivo:** `dispatcher/service.py` (o donde se encolan tareas)

Llamar `ops_log.task_queued(task_id, task, team, task_type)` al momento de encolar cada tarea en Redis. Hoy este método existe pero nunca se invoca.

### P4 — Agregar `task_type` a `task_completed` y `task_failed` [MEDIO]

**Archivo:** `infra/ops_logger.py`

Agregar parámetro `task_type` a los métodos relevantes. Luego actualizar los call sites en `dispatcher/service.py`.

### P5 — Rotación de ops_log.jsonl [MEDIO]

**Archivo:** `infra/ops_logger.py`

Opciones:
1. **Rotación por tamaño:** Al escribir, verificar si el archivo excede N MB y rotar (`ops_log.jsonl.1`, `.2`, etc., máximo K archivos).
2. **Rotación por tiempo:** Un script cron que mueve el archivo diariamente.
3. **Usar `RotatingFileHandler`** de logging estándar de Python.

Recomendación: opción 1 con un máximo de 10 archivos de 10 MB cada uno (100 MB total).

### P6 — Guardar `input_summary` y `result_summary` en ops_log [MEDIO]

**Archivo:** `infra/ops_logger.py`

Agregar campos opcionales truncados (200 chars) para tener audit trail más allá del TTL de Redis:

```python
def task_completed(self, ..., input_summary=None, result_summary=None):
    entry = { ... }
    if input_summary:
        entry["input_summary"] = input_summary[:200]
    if result_summary:
        entry["result_summary"] = result_summary[:200]
```

### P7 — Correlacionar Langfuse con envelope `trace_id` [MEDIO]

**Archivo:** `worker/tracing.py`

Agregar `trace_id` al metadata de `lf.trace()`:

```python
trace = lf.trace(
    name="llm.generate",
    metadata={"task_id": task_id, "task_type": task_type, "trace_id": trace_id, ...},
)
```

Y propagar `_trace_id` desde el Dispatcher vía `input_data`.

### P8 — Establecer `source` en todos los enqueuers [BAJO]

**Archivos:**
- `worker/app.py` (`/enqueue`) → `source = "api"`
- `dispatcher/linear_webhook.py` → ya tiene `source = "linear_webhook"` ✅
- `dispatcher/intent_classifier.py` → ya tiene `source = "notion_poller"` ✅
- `dispatcher/smart_reply.py` → ya tiene `source = "smart_reply"` ✅
- Scripts cron → agregar `source = "cron_<script_name>"`

### P9 — Incluir `trace_id` en GET /task/{id}/status y Notion upsert [BAJO]

**Archivos:** `worker/app.py`, `worker/notion_client.py`

Agregar `trace_id` a la respuesta del endpoint y como propiedad en Notion.

---

## 6. Métricas de gobernanza — KPIs derivables

### Hoy (sin cambios)

| KPI | Fuente | Fórmula |
|-----|--------|---------|
| Tareas/día | ops_log | count(`task_completed`) + count(`task_failed`) por día |
| Tasa de éxito global | ops_log | completed / (completed + failed) × 100 |
| Tiempo medio por tarea | ops_log | avg(`duration_ms`) de `task_completed` |
| Uso por modelo | ops_log | count por `model` en `task_completed` |
| Uso por equipo | ops_log | count por `team` en `task_completed` |
| Costo estimado semanal | Langfuse | tokens × rates por provider |
| Latencia LLM por provider | Langfuse | avg de `duration_ms` por generation |
| Cola pendiente | Redis | `LLEN umbral:tasks:pending` |
| Alertas de cuota | ops_log | count(`quota_warning`) + count(`quota_restricted`) |

### Con mejoras propuestas

| KPI adicional | Requiere | Propuesta |
|---------------|----------|-----------|
| Tasa de éxito por task_type | P4 | `task_type` en `task_completed`/`task_failed` |
| Distribución por origen/source | P2, P3, P8 | `source` en OpsLogger + en todos los enqueuers |
| Tasa de encolamiento vs. ejecución | P3 | `task_queued` emitido |
| Audit trail completo por trace_id | P1, P2, P7 | `trace_id` propagado end-to-end + en ops_log + Langfuse |
| Historial post-TTL con resumen | P6 | `input_summary` + `result_summary` en ops_log |
| Tiempo en cola (queue latency) | P3 | `task_queued.ts` → `task_completed.ts` con mismo `task_id` |

---

## 7. Recomendaciones — Orden de implementación

| Orden | Propuesta | Esfuerzo | Impacto | Dependencias |
|-------|-----------|----------|---------|--------------|
| 1 | **P3** — Emitir `task_queued` | Bajo (1 línea) | Alto | Ninguna |
| 2 | **P4** — `task_type` en completed/failed | Bajo (2 archivos) | Medio | Ninguna |
| 3 | **P2** — `trace_id` + `source` en OpsLogger | Medio (1 archivo + call sites) | Alto | Ninguna |
| 4 | **P1** — Propagar `trace_id` end-to-end | Medio (3 archivos) | Alto | P2 |
| 5 | **P8** — `source` en todos los enqueuers | Bajo (4-5 archivos) | Medio | P2 |
| 6 | **P5** — Rotación de ops_log | Medio (1 archivo) | Medio | Ninguna |
| 7 | **P6** — `input_summary` / `result_summary` en ops_log | Bajo (1 archivo + call sites) | Medio | Ninguna |
| 8 | **P7** — Correlacionar Langfuse con `trace_id` | Bajo (2 archivos) | Medio | P1 |
| 9 | **P9** — `trace_id` en API status + Notion | Bajo (2 archivos) | Bajo | P1 |

**Estimación total:** ~2-3 sesiones de trabajo enfocado para implementar P1-P5 (los más críticos).

---

## 8. Verificación — Script de auditoría

Ver `scripts/audit_traceability_check.py` para un script que verifica automáticamente la estructura de ops_log, detecta gaps, y emite un veredicto de trazabilidad.

Uso:

```bash
python scripts/audit_traceability_check.py
python scripts/audit_traceability_check.py --log-dir /ruta/custom
python scripts/audit_traceability_check.py --format json
```
