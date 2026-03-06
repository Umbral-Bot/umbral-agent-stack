# Task R21 - Quick Wins Auditoria: Dispatcher (Codex)

**Fecha:** 2026-03-07  
**Ronda:** 21  
**Agente:** Codex (GPT-5.4)  
**Estado:** done  
**Rama:** `codex/audit-qw-dispatcher` - trabajar solo en esta rama.

---

## Flujo Git (obligatorio)

1. **Antes de tocar codigo:** `git fetch origin && git checkout main && git pull origin main`
2. **Crear tu rama:** `git checkout -b codex/audit-qw-dispatcher`
3. **Trabajar solo en esta rama.** No hacer merge a main ni a otras ramas.
4. **Al terminar:** commit, `git push origin codex/audit-qw-dispatcher`, abrir PR a main. No mergear el PR tu mismo salvo que se te indique.

---

## Objetivo

Implementar la parte **dispatcher** del quick win QW-5: emitir el evento `task_queued` en ops_log cuando el dispatcher re-encola una tarea (retry). Plan: [docs/plan-implementacion-auditoria-2026-03.md](../../docs/plan-implementacion-auditoria-2026-03.md). Bug: P1 #5 (02-bugs).

---

## Tareas

### QW-5 (parte dispatcher): Emitir task_queued al re-encolar

- En `dispatcher/service.py`, en el camino donde se hace **retry** (re-enqueue): despues de `queue.enqueue(envelope)`, llamar a `ops_log.task_queued(task_id, task, team, task_type, trace_id=trace_id)` con los datos del `envelope` (task_id, task, team, task_type, trace_id). El modulo `infra.ops_logger` ya esta importado como `ops_log` en service.py; el metodo `task_queued(task_id, task, team, task_type, trace_id=None)` ya existe en `infra/ops_logger.py`.
- Asegurarse de usar el `task_type` del envelope (p. ej. `envelope.get("task_type", "general")`).
- Opcional: verificar que `scripts/audit_traceability_check.py` detecte el evento cuando se re-encola una tarea; si hace falta, anadir un test unitario que verifique que al re-encolar se escribe el evento en el log.

---

## Criterios de exito

- [x] Tras re-encolar una tarea (retry), se llama a `ops_log.task_queued(...)` con los datos correctos del envelope.
- [x] Tests existentes pasan. PR abierto a main con titulo `fix(R21-104): audit quick wins - dispatcher (task_queued on retry)`.

---

## Restricciones

- No modificar `worker/`, ni `.env.example`, ni scripts de Bitacora (eso va en ramas worker y config). Solo `dispatcher/service.py` para este item.
- No mergear a main. Solo push de tu rama y abrir PR.

---

## Log

### [codex] 2026-03-06 02:39 -03:00

- Se anadio `ops_log.task_queued(...)` en el camino de retry de `dispatcher/service.py` justo despues de `queue.enqueue(envelope)`, reutilizando `task_type` y `trace_id` del envelope.
- Se agrego test en `tests/test_dispatcher_resilience.py` para verificar que el re-encolado emite `task_queued` con los campos correctos.
- Verificacion: `python -m pytest tests/test_dispatcher_resilience.py tests/test_dispatcher.py tests/test_ops_logger.py -q` -> `64 passed`; `python -m pytest tests/ -q` -> `901 passed, 5 skipped`.
