# Instrucciones para GitHub Copilot — Ronda 3

**Repo:** `C:\GitHub\umbral-agent-stack-copilot`  
**Rama:** `feat/copilot-task-api`  
**Tarea nueva:** API HTTP para encolar tareas + endpoint de status

## Contexto

Actualmente la única forma de encolar tareas es con Python (`TaskQueue.enqueue()`). Esto limita quién puede enviar trabajo al sistema. Necesitamos un endpoint HTTP simple en el Worker para que cualquier servicio externo (Make.com webhooks, n8n, cron scripts, o incluso David desde el navegador) pueda encolar tareas.

## Tu tarea

### A. Endpoint POST /enqueue en el Worker
Agregar al Worker (`worker/app.py`) un nuevo endpoint:

```
POST /enqueue
Authorization: Bearer <WORKER_TOKEN>
Content-Type: application/json

{
  "task": "research.web",
  "team": "marketing",
  "input": {"query": "tendencias BIM 2026", "count": 5}
}
```

Respuesta:
```json
{"ok": true, "task_id": "uuid...", "queued": true}
```

El endpoint debe:
1. Validar auth (mismo WORKER_TOKEN que /run)
2. Generar task_id (uuid4)
3. Crear el TaskEnvelope completo
4. Encolar via Redis (importar `TaskQueue` y `redis`)
5. Retornar el task_id

### B. Endpoint GET /task/{task_id}/status
Agregar endpoint para consultar el estado de una tarea:

```
GET /task/uuid.../status
Authorization: Bearer <WORKER_TOKEN>
```

Respuesta:
```json
{"task_id": "...", "status": "done", "task": "research.web", "team": "marketing", "result": {...}}
```

Lee del Redis key `umbral:task:{task_id}`.

### C. Tests
Crear `tests/test_enqueue_api.py`:
- Test que /enqueue requiera auth
- Test que /enqueue cree tarea y retorne task_id
- Test que /task/{id}/status retorne el estado correcto
- Usar mocks de Redis para no requerir Redis real

### D. Documentar
Agregar los nuevos endpoints a `docs/07-worker-api-contract.md`.

## Archivos relevantes
- `worker/app.py` — FastAPI app (agregar endpoints aquí)
- `dispatcher/queue.py` — TaskQueue (importar para encolar)
- `worker/config.py` — WORKER_TOKEN, etc.

## Flujo de trabajo
```bash
git add .
git commit -m "feat: /enqueue and /task/{id}/status API endpoints"
git push -u origin feat/copilot-task-api
gh pr create --base main --title "[Copilot] Task enqueue + status API" --body "Endpoints HTTP para encolar tareas y consultar status"
```
