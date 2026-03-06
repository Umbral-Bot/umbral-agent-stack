# Task R21 — Quick Wins Auditoría: Dispatcher (Codex)

**Fecha:** 2026-03-07  
**Ronda:** 21  
**Agente:** Codex (GPT-5.4)  
**Rama:** `codex/audit-qw-dispatcher` — trabajar solo en esta rama.

---

## Flujo Git (obligatorio)

1. **Antes de tocar código:** `git fetch origin && git checkout main && git pull origin main`
2. **Crear tu rama:** `git checkout -b codex/audit-qw-dispatcher`
3. **Trabajar solo en esta rama.** No hacer merge a main ni a otras ramas.
4. **Al terminar:** commit, `git push origin codex/audit-qw-dispatcher`, abrir PR a main. No mergear el PR tú mismo salvo que se te indique.

---

## Objetivo

Implementar la parte **dispatcher** del quick win QW-5: emitir el evento `task_queued` en ops_log cuando el dispatcher re-encola una tarea (retry). Plan: [docs/plan-implementacion-auditoria-2026-03.md](../../docs/plan-implementacion-auditoria-2026-03.md). Bug: P1 #5 (02-bugs).

---

## Tareas

### QW-5 (parte dispatcher): Emitir task_queued al re-encolar

- En `dispatcher/service.py`, en el camino donde se hace **retry** (re-enqueue): después de `queue.enqueue(envelope)`, llamar a `ops_log.task_queued(task_id, task, team, task_type, trace_id=trace_id)` con los datos del `envelope` (task_id, task, team, task_type, trace_id). El módulo `infra.ops_logger` ya está importado como `ops_log` en service.py; el método `task_queued(task_id, task, team, task_type, trace_id=None)` ya existe en `infra/ops_logger.py`.
- Asegurarse de usar el `task_type` del envelope (p. ej. `envelope.get("task_type", "general")`).
- Opcional: verificar que `scripts/audit_traceability_check.py` detecte el evento cuando se re-encola una tarea; si hace falta, añadir un test unitario que verifique que al re-encolar se escribe el evento en el log.

---

## Criterios de éxito

- [ ] Tras re-encolar una tarea (retry), se llama a `ops_log.task_queued(...)` con los datos correctos del envelope.
- [ ] Tests existentes pasan. PR abierto a main con título `fix(R21-104): audit quick wins — dispatcher (task_queued on retry)`.

---

## Restricciones

- No modificar `worker/`, ni `.env.example`, ni scripts de Bitácora (eso va en ramas worker y config). Solo `dispatcher/service.py` para este ítem.
- No mergear a main. Solo push de tu rama y abrir PR.
