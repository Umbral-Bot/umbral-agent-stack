---
id: "016"
title: "Task History API + Redis Pagination"
assigned_to: codex
status: assigned
branch: feat/codex-task-history-api
priority: high
round: 4
---

# Task History API + Redis Pagination

## Problema
El endpoint GET /tasks actual lee solo tareas en memoria (in-memory dict del Worker).
Cuando el Worker se reinicia, se pierden. Además no hay forma de filtrar por fecha,
equipo o estado. El daily digest de Copilot tiene que escanear Redis manualmente.
Necesitamos un API unificado para consultar historial de tareas desde Redis.

## Tu tarea

### A. Nuevo endpoint GET /tasks/history en Worker
En `worker/app.py`:

```
GET /task/history
Authorization: Bearer <WORKER_TOKEN>

Query params:
  hours: int = 24      — ventana temporal (últimas N horas)
  team: str = None     — filtrar por equipo
  status: str = None   — filtrar por status (done/failed/queued/running)
  limit: int = 100     — máximo resultados
  offset: int = 0      — paginación

Response:
{
  "tasks": [...],
  "total": 42,
  "page": {"offset": 0, "limit": 100, "has_more": false},
  "stats": {
    "done": 35, "failed": 5, "queued": 2,
    "teams": {"marketing": 10, "system": 32}
  }
}
```

El endpoint lee de Redis (scan `umbral:task:*`), filtra por los parámetros,
y retorna los resultados paginados. Usar `dispatcher.queue.TaskQueue` como referencia.

### B. Clase TaskHistory helper
Crear `dispatcher/task_history.py`:
- `TaskHistory(redis_client)` — wrapper para consultas de historial
- `query(hours, team, status, limit, offset)` — escanea Redis con filtros
- `stats(hours)` — estadísticas agregadas por status y team
- Optimización: usar SCAN con cursor (no KEYS *) para no bloquear Redis

### C. Actualizar daily_digest.py de Copilot
Modificar `scripts/daily_digest.py` para usar el nuevo endpoint
`GET /task/history?hours=24` en vez de scan manual de Redis.

### D. Tests
Crear `tests/test_task_history.py`:
- Test: query sin filtros retorna todas las tareas
- Test: filtro por team funciona
- Test: filtro por status funciona
- Test: filtro por hours excluye tareas viejas
- Test: paginación funciona (limit + offset)
- Test: stats agrega correctamente
- Test: Redis vacío retorna lista vacía sin error

## Archivos relevantes
- `worker/app.py` — agregar endpoint
- `dispatcher/queue.py` — TASK_KEY_PREFIX, TaskQueue (referencia)
- `scripts/daily_digest.py` — actualizar para usar nuevo endpoint
- `docs/07-worker-api-contract.md` — documentar
