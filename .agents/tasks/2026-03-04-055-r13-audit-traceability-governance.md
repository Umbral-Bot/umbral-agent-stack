# Task R13 — Revisión de trazabilidad para auditoría y gobernanza

**Fecha:** 2026-03-04  
**Ronda:** 13  
**Agente:** Codex / Code Claude / Cursor Agent Cloud  
**Branch:** `feat/audit-traceability-governance`

---

## Contexto

El responsable de mantenimiento del sistema (David) necesita **ver y evaluar qué se hace y cómo se hace** para medir estrategias. La trazabilidad en procesos de auditoría y gobernanza es crítica: sin ella no se puede responder preguntas como "¿qué tareas se ejecutaron esta semana?", "¿qué modelo usó cada team?", "¿cuál fue la tasa de éxito por tipo de task?" ni "¿quién/origen de cada encolado?".

**Objetivo:** Revisar si el sistema Umbral Agent Stack tiene tracking suficiente para auditoría y gobernanza de procesos. Identificar gaps. Proponer mejoras concretas para medir estrategias.

---

## Qué revisar (inventario existente)

| Componente | Ubicación | Qué registra |
|------------|-----------|--------------|
| **OpsLogger** | `infra/ops_logger.py`, `~/.config/umbral/ops_log.jsonl` | task_queued, task_completed, task_failed, task_blocked, task_retried, model_selected, quota_warning |
| **trace_id** | `worker/models/__init__.py`, envelope en Redis | UUID end-to-end por tarea |
| **Task store** | Redis `umbral:task:{id}` | task_id, status, result, started_at, completed_at (TTL) |
| **GET /task/history** | `worker/app.py` | Historial paginado desde Redis |
| **GET /task/{id}/status** | `worker/app.py` | Estado de tarea por ID |
| **Notion upsert_task** | `worker/notion_client.py` | Estado en Notion (task_id, status, team, task, input_summary, result_summary) |
| **Langfuse** | `worker/tracing.py` | Traces de llamadas LLM (model, provider, usage, duration) |
| **OODA report** | `scripts/ooda_report.py` | Resumen semanal (Redis + ops_log + Langfuse) |
| **quota_usage_report** | `scripts/quota_usage_report.py` | Uso de cuotas por provider |
| **dashboard_report_vps** | `scripts/dashboard_report_vps.py` | Payload para Notion dashboard |

---

## Tareas requeridas

### 1. Análisis de gaps de trazabilidad

Identificar qué **no** está cubierto hoy para auditoría/gobernanza:

- [ ] ¿Se registra `trace_id` en `ops_log.jsonl`? (para correlacionar eventos)
- [ ] ¿Se registra origen/origenator de la tarea? (Telegram, Notion, Linear, Make, cron, manual)
- [ ] ¿Se guarda input/output truncado para auditoría? (privacy vs traceability)
- [ ] ¿Hay retención configurable de ops_log? (el archivo crece indefinidamente)
- [ ] ¿GET /task/history incluye trace_id y metadata suficiente?
- [ ] ¿Se puede agregar por team, por task_type, por período para medir estrategias?
- [ ] ¿Langfuse trace_id se correlaciona con task_id/trace_id del envelope?

---

### 2. Documento de diseño: `docs/61-audit-traceability-governance.md`

Crear documento con:

1. **Inventario actual** — tabla de componentes de tracking (formato arriba, ampliada)
2. **Gaps identificados** — lista priorizada con impacto (alto/medio/bajo)
3. **Propuestas de mejora** — para cada gap, propuesta concreta (código/archivo, campo nuevo)
4. **Métricas de gobernanza** — qué KPIs se pueden derivar hoy vs. con mejoras
5. **Recomendaciones** — orden de implementación sugerido

---

### 3. Matriz de preguntas vs. capacidad actual

| Pregunta de gobernanza | ¿Se puede responder hoy? | Con qué datos |
|------------------------|---------------------------|---------------|
| ¿Cuántas tareas se ejecutaron por día/semana? | Sí/No | ops_log, Redis |
| ¿Cuál fue la tasa de éxito por task_type? | Sí/No | ops_log |
| ¿Qué modelo usó cada team? | Sí/No | ops_log, model_selected |
| ¿Cuál es el tiempo medio por task? | Sí/No | ops_log, duration_ms |
| ¿De dónde vino cada tarea? | Sí/No | ??? |
| ¿Qué input se usó (resumen)? | Sí/No | Notion upsert_task |
| ¿Se puede auditar un flujo completo por trace_id? | Sí/No | trace_id en envelope, ¿en ops_log? |

---

### 4. Script de verificación rápida

Crear `scripts/audit_traceability_check.py` que:

- Lee `~/.config/umbral/ops_log.jsonl` (o `UMBRAL_OPS_LOG_DIR`) y verifica estructura de eventos
- Cuenta eventos por tipo (task_completed, task_failed, etc.)
- Verifica si `trace_id` aparece en los eventos
- Verifica si hay retención/rotación del archivo
- Imprime resumen: "Trazabilidad: OK / Parcial / Insuficiente" y lista de gaps detectados

---

## Criterios de éxito

- [x] `docs/61-audit-traceability-governance.md` — documento completo
- [x] Matriz de preguntas vs. capacidad actual
- [x] Lista priorizada de gaps y propuestas de mejora
- [x] `scripts/audit_traceability_check.py` — script de verificación rápida
- [x] PR abierto a `main`

## Log

### [cursor-agent-cloud] 2026-03-05 08:00

**Archivos creados:**
- `docs/61-audit-traceability-governance.md` — Documento completo con inventario de 12 componentes, 12 gaps priorizados, 10 preguntas de gobernanza, 9 propuestas de mejora, KPIs y recomendaciones de implementación.
- `scripts/audit_traceability_check.py` — Script de verificación que lee ops_log.jsonl, valida estructura de eventos, verifica presencia de trace_id/source/task_type, evalúa retención, y emite veredicto (OK/Parcial/Insuficiente).

**Archivos modificados:**
- `.agents/board.md` — Agregada Ronda 13 con tarea 055.

**Hallazgos clave:**
- `trace_id` está definido en TaskEnvelope pero no se propaga end-to-end (WorkerClient.run() envía solo {task, input}).
- `task_queued` nunca se emite (método existe pero no se invoca).
- `source` (origen) solo se establece en 4 de N enqueuers y no se registra en OpsLogger.
- Sin rotación de ops_log.jsonl — archivo crece indefinidamente.
- Langfuse traces no correlacionados con envelope trace_id.

**Tests:** Script ejecutado correctamente, detecta todos los gaps esperados.
