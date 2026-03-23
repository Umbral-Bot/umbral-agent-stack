---
id: "2026-03-23-003"
title: "UMB-140: endurecer auto-issues con deduplicacion y proyecto canonico"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-23T01:37:46-03:00
updated_at: 2026-03-23T02:19:00-03:00
---

## Objetivo

Cerrar `UMB-140` despues de `UMB-141`: endurecer la generacion automatica de issues para que el Dispatcher publique follow-ups canonicos en Linear con mejor contexto y deduplicacion operativa, en vez de producir ruido repetido.

## Contexto

- Issue fuente: `UMB-140`
- Dependencia ya cerrada: `UMB-141`
- Codigo relevante:
  - `dispatcher/service.py`
  - `worker/tasks/linear.py`
  - `worker/linear_client.py`
  - `docs/67-linear-agent-stack-protocol.md`
  - `tests/test_dispatcher_escalation.py`
  - `tests/test_linear.py`

## Criterios de aceptacion

- [x] La auto-escalacion usa el proyecto canonico de Agent Stack con estructura rica y evidencia util.
- [x] Se deduplican fallos repetidos con una regla explicita de fingerprint + ventana temporal.
- [x] Cuando aplica dedupe, se comenta/actualiza una issue existente en vez de abrir otra.
- [x] Tests relevantes cubren creacion nueva y reutilizacion de issue existente.
- [x] Task y board quedan actualizados al cierre.

## Log

### codex 2026-03-23 01:37 -03:00
Tarea creada desde `main` tras cerrar `UMB-141`.

Inspeccion inicial:

- `dispatcher/service.py` ya usa `linear.publish_agent_stack_followup`, pero el titulo actual incluye `task_id[:8]`, lo que hace cada follow-up inherentemente unico.
- `worker/tasks/linear.py` resuelve el proyecto canonico y labels base, pero `handle_linear_publish_agent_stack_followup()` siempre crea una issue nueva; no existe aun regla de dedupe ni comentario sobre issue existente.
- `worker/linear_client.py` ya sabe listar issues por proyecto y agregar comentarios, asi que el slice natural es implementar dedupe en el handler canonico y pasarle al Dispatcher un fingerprint util.

### codex 2026-03-23 02:19 -03:00
Trabajo completado en `codex/umb-140-auto-issues-canonical`.

Resultado:

- `dispatcher/service.py` ahora publica follow-ups automaticos con `auto_generated`, fingerprint estable, ventana de dedupe configurable, `worker_endpoint`, `selected_model`, `retry_count` y `error_class`.
- `worker/tasks/linear.py` reutiliza una issue abierta reciente del proyecto canonico cuando encuentra el mismo fingerprint, agrega comentario de nueva ocurrencia y refresca labels/estado en vez de crear otra.
- `worker/linear_client.py` amplio `list_project_issues()` para incluir `description`, `createdAt` y `updatedAt`, que son necesarios para dedupe temporal.
- `docs/67-linear-agent-stack-protocol.md` documenta la regla de fingerprint + ventana de deduplicacion.
- Tests actualizados en `tests/test_dispatcher_escalation.py` y `tests/test_linear.py`.

Validacion:

- `python -m pytest tests/test_dispatcher_escalation.py tests/test_linear.py -q` -> `35 passed`
- `python -m pytest tests -q` -> `1187 passed, 4 skipped, 1 warning`
- `git diff --check` -> OK (solo warnings CRLF del checkout Windows)
