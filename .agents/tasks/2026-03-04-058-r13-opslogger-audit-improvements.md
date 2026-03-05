# Task R13 — Mejoras de OpsLogger para auditoría

**Fecha:** 2026-03-04  
**Ronda:** 13  
**Agente:** Codex / Code Claude / Cursor Agent Cloud  
**Branch:** `feat/opslogger-audit-improvements`

---

## Contexto

El OpsLogger (`infra/ops_logger.py`) es la fuente principal de eventos para auditoría. Para gobernanza y trazabilidad se requieren mejoras: **trace_id** en eventos, **retención configurable**, y opcionalmente **input_summary** truncado para correlacionar qué input generó cada resultado.

**Dependencia:** Esta tarea asume que la tarea 055 (audit-traceability-governance) identificó los gaps. Si no está hecha, basarse en `docs/61-audit-traceability-governance.md` si existe, o en el análisis implícito: trace_id faltante, retención infinita, input_summary no persistido en ops_log.

---

## Tareas requeridas

### 1. Agregar `trace_id` a todos los eventos OpsLogger

En `infra/ops_logger.py`, los métodos actuales no reciben `trace_id`. El Dispatcher y el Worker tienen acceso al `trace_id` del envelope.

**Cambios:**
- Añadir parámetro opcional `trace_id: str | None = None` a: `task_queued`, `task_completed`, `task_failed`, `task_blocked`, `task_retried`, `model_selected`
- Si se pasa, incluirlo en el JSON del evento: `"trace_id": trace_id`
- Actualizar todas las llamadas en `dispatcher/service.py` para pasar `envelope.get("trace_id", "")` donde haya envelope

**Archivos a modificar:**
- `infra/ops_logger.py`
- `dispatcher/service.py` — en cada `ops_log.task_*` y `ops_log.model_selected`, pasar trace_id del envelope

---

### 2. Retención configurable de ops_log

El archivo `ops_log.jsonl` crece indefinidamente. Añadir soporte para rotación o límite de líneas.

**Opción A — Rotación por tamaño:**
- Variable `UMBRAL_OPS_LOG_MAX_MB` (default: 100)
- Cuando el archivo supere el límite, rotar a `ops_log.jsonl.1`, `ops_log.jsonl.2`, etc. (keep last 3)

**Opción B — Retención por días (más simple):**
- Script `scripts/ops_log_rotate.py` que:
  - Lee `ops_log.jsonl`
  - Filtra eventos con `ts` dentro de los últimos N días (`UMBRAL_OPS_LOG_RETENTION_DAYS`, default: 90)
  - Reescribe el archivo con los eventos restantes
  - Ejecutable desde cron semanal

Implementar **Opción B** (script de rotación) para no tocar OpsLogger en cada write. Documentar en `docs/62-operational-runbook.md` o en docstring del script.

---

### 3. `input_summary` opcional en task_completed / task_failed

Para auditoría, a veces es útil saber un resumen del input (sin exponer datos sensibles).

**Cambios en OpsLogger:**
- `task_completed(..., input_summary: str | None = None)`
- `task_failed(..., input_summary: str | None = None)`
- Si se pasa, incluir en el evento truncado a 200 chars

**Cambios en Dispatcher:**
- Al llamar `task_completed` y `task_failed`, pasar `input_summary=str(envelope.get("input", {}))[:200]`

---

### 4. Tests

Actualizar `tests/test_dispatcher_resilience.py` o crear `tests/test_ops_logger.py`:

- `test_task_completed_includes_trace_id_when_provided`
- `test_task_failed_includes_trace_id_when_provided`
- `test_task_completed_includes_input_summary_when_provided`
- `test_ops_log_rotate_script_keeps_recent_events`
- `test_ops_log_rotate_script_respects_retention_days`

---

### 5. Documentación

Actualizar `infra/ops_logger.py` docstring con:
- Nuevos parámetros `trace_id`, `input_summary`
- Variable `UMBRAL_OPS_LOG_RETENTION_DAYS` para el script de rotación
- Referencia a `scripts/ops_log_rotate.py`

---

## Criterios de éxito

- [ ] `trace_id` incluido en todos los eventos OpsLogger cuando se pasa
- [ ] Dispatcher pasa trace_id en todas las llamadas a ops_log
- [ ] `input_summary` opcional en task_completed y task_failed
- [ ] `scripts/ops_log_rotate.py` — script de retención por días
- [ ] Tests actualizados o nuevos
- [ ] Documentación actualizada
- [ ] PR abierto a `main`
