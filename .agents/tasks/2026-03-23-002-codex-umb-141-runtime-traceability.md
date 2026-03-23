---
id: "2026-03-23-002"
title: "UMB-141: completar trazabilidad de runtime para enriquecer auto-issues"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-23T01:19:29-03:00
updated_at: 2026-03-23T01:25:56-03:00
---

## Objetivo

Capitalizar `UMB-141` sin re-auditar todo el stack: cerrar la brecha de trazabilidad real del runtime para que `ops_log` capture mejor el ciclo de vida de tareas y deje suficiente contexto para auditorías, métricas y auto-issues.

## Contexto

- Diagnóstico base: `docs/audits/super-diagnostico-2026-03-22.md`
- Follow-up asociado: `docs/audits/agent-stack-followups-2026-03-22.md`
- Hallazgo técnico actual:
  - `infra/ops_logger.py` propaga `trace_id`, pero no `source` / `source_kind`
  - `dispatcher/service.py` emite `task_completed` / `task_failed` / `task_blocked` / `task_retried`, pero sin contexto completo del envelope
  - `worker/app.py` en `/run` ejecuta y persiste resultado, pero no emite el ciclo de vida equivalente en `ops_log`
  - `scripts/audit_traceability_check.py` y `scripts/governance_metrics_report.py` dependen de esa señal

## Criterios de aceptación

- [x] `ops_log` propaga `source`, `source_kind` y `task_type` en eventos de ciclo de vida relevantes.
- [x] El Worker directo (`POST /run`) emite eventos suficientes para que `task_completed` / `task_failed` aparezcan también fuera del Dispatcher.
- [x] Scripts de auditoría/métricas quedan alineados con el nuevo contrato de trazabilidad.
- [x] Tests relevantes pasan y el Log deja claro el alcance real del fix.
- [x] `board.md` queda actualizado al cierre.

## Log

### codex 2026-03-23 01:19 -03:00
Tarea creada por instrucción directa de David desde `main` actualizado. Inspección inicial:

- `infra/ops_logger.py` ya soporta `trace_id` e `input_summary`, pero no `source`, `source_kind` ni `task_type` en `task_completed` / `task_failed` / `task_blocked` / `task_retried`.
- `dispatcher/service.py` sí emite ciclo de vida casi completo, pero hoy pierde parte del contexto del envelope al escribir en `ops_log`.
- `worker/app.py` (`/run`) ejecuta tareas y las guarda en memoria, pero no emite `task_completed` / `task_failed` a `ops_log`, lo que explica parte del vacío en `governance_metrics_report` cuando el runtime real no pasa por el mismo flujo.

Arranco implementación en rama `codex/umb-141-runtime-traceability`.

### codex 2026-03-23 01:25 -03:00
`UMB-141` quedó implementada y validada en la rama `codex/umb-141-runtime-traceability`.

Cambios principales:

- `infra/ops_logger.py`: los eventos `task_queued`, `task_completed`, `task_failed`, `task_blocked` y `task_retried` ahora aceptan y escriben `trace_id`, `task_type`, `source` y `source_kind` sin romper compatibilidad previa.
- `dispatcher/service.py`: el ciclo de vida del Dispatcher deja de perder contexto del envelope y ahora propaga `source` / `source_kind` / `task_type` en `blocked`, `completed`, `failed`, `retried`; además se cubre explícitamente el bloqueo por VM offline.
- `worker/app.py`: el Worker directo vía `POST /run` ya emite `task_failed` y `task_completed` a `ops_log`, incluyendo `trace_id`, `task_type`, `source` y `source_kind`; el path de `unknown task` deja de quedar invisible.
- `scripts/audit_traceability_check.py`: la auditoría ahora también mide cobertura de `source_kind`.
- Tests nuevos/ajustados en `tests/test_ops_logger.py`, `tests/test_dispatcher_resilience.py`, `tests/test_enqueue_api.py`, `tests/test_worker.py` y `tests/test_audit_traceability_check.py`.

Validación:

- `WORKER_TOKEN=test python -m pytest tests/test_ops_logger.py tests/test_dispatcher_resilience.py tests/test_enqueue_api.py tests/test_worker.py tests/test_audit_traceability_check.py -q` -> `100 passed`
- `WORKER_TOKEN=test python -m pytest tests/test_governance_metrics.py tests/test_dashboard.py -q` -> `43 passed`
- `WORKER_TOKEN=test python -m pytest tests -q` -> `1185 passed, 4 skipped, 1 warning`
- `git diff --check` -> sin errores de diff; solo warnings de fin de línea CRLF del checkout Windows

Queda lista para PR. No hice redeploy ni verificación de runtime en VPS/VM en esta tarea; el alcance de este slice fue código + tests para cerrar la brecha estructural de trazabilidad.
