---
id: "031"
title: "Linear Webhooks → Rick: issues nuevos se convierten en tareas"
assigned_to: codex
branch: feat/codex-linear-webhooks
round: 8
status: done
created: 2026-02-27
---

## Objetivo

Implementar webhooks de Linear para que cuando se cree o asigne un issue en Linear, Rick lo detecte y encole la tarea correspondiente en Redis automáticamente.

## Contexto

- `worker/tasks/linear.py` — ya tiene `linear.create_issue` y `linear.update_issue_status`
- `worker/linear_client.py` — cliente GraphQL para Linear
- `dispatcher/service.py` — loop principal del Dispatcher
- El flujo top-down (Rick → Linear) ya funciona. Falta el bottom-up (Linear → Rick).

## Requisitos

### 1. Endpoint webhook en el Dispatcher

Agregar un endpoint HTTP POST en el Dispatcher (o en un mini-server separado) que reciba webhooks de Linear:

```python
# POST /webhooks/linear
# Body: { "action": "create", "data": { "id": "...", "title": "...", ... }, "type": "Issue" }
```

- Validar la firma del webhook (Linear envía `Linear-Signature` header)
- Filtrar: solo actuar en `action: "create"` o `action: "update"` cuando `assignee` sea Rick
- Extraer: title, description, labels, priority, team
- Crear un TaskEnvelope y encolarlo en Redis

### 2. Mapeo Linear Issue → TaskEnvelope

```python
def linear_issue_to_envelope(issue_data: dict) -> dict:
    # Inferir task_type desde labels (ej. label "coding" → task_type "coding")
    # Inferir team desde labels (ej. label "Marketing" → team "marketing")
    # Mapear priority: Linear 1=urgent → envelope priority high
    return {
        "task_id": f"lin-{issue_data['id'][:8]}",
        "task": "llm.generate",  # default, override con label "task:xxx"
        "team": inferred_team,
        "task_type": inferred_task_type,
        "input": {"prompt": issue_data["description"], ...},
        "linear_issue_id": issue_data["id"],
    }
```

### 3. Tests

- `tests/test_linear_webhooks.py`:
  - Test webhook signature validation
  - Test issue → envelope mapping
  - Test filtering (solo issues asignados a Rick)
  - Test que issues con label "no-auto" se ignoran

### 4. Documentación

- Actualizar `docs/30-linear-notion-architecture.md` con el flujo bidireccional
- Agregar instrucciones para configurar el webhook en Linear settings

## Archivos a crear/modificar

- `dispatcher/linear_webhook.py` (nuevo)
- `tests/test_linear_webhooks.py` (nuevo)
- `docs/30-linear-notion-architecture.md` (actualizar)

## Criterio de éxito

- Crear un issue en Linear con label "coding" y assignee "Rick" → aparece como tarea en Redis
- Issue sin assignee Rick → se ignora
- Tests pasan

## Log

### [codex] 2026-03-04 14:38
- Implementado `dispatcher/linear_webhook.py` con endpoint `POST /webhooks/linear`, validacion de firma `Linear-Signature` (HMAC SHA256), filtro por eventos `Issue create|update`, filtro por assignee Rick (`LINEAR_RICK_IDENTIFIERS`) y exclusion por label `no-auto`.
- Implementado mapeo `linear_issue_to_envelope(...)` con inferencia por labels: `task` default `llm.generate` (override `task:xxx`), `task_type`, `team` y prioridad (`1/2 -> high`, `3 -> medium`, `4 -> low`).
- Agregado `tests/test_linear_webhooks.py` con cobertura de firma, mapping, filtros y enqueue real en Redis (fakeredis).
- Actualizada `docs/30-linear-notion-architecture.md` con flujo bidireccional Linear -> Dispatcher -> Redis e instrucciones para configurar el webhook en Linear.
- Actualizado `dispatcher/requirements.txt` para incluir `fastapi` y `uvicorn`.
- Tests ejecutados:
  - `python -m pytest tests/test_linear_webhooks.py -v -p no:cacheprovider` -> 6 passed
  - `python -m pytest tests/test_linear.py tests/test_linear_team_router.py tests/test_linear_webhooks.py -q -p no:cacheprovider` -> 41 passed