---
id: "014"
title: "Webhook Callback System"
assigned_to: codex
status: done
branch: feat/codex-webhook-callback
priority: high
round: 3
---

# Webhook Callback System

## Problema
Cuando Make.com o n8n encolan tareas via POST /enqueue, no hay forma de recibir
el resultado de vuelta. El caller tiene que hacer polling con GET /task/{id}/status.
Necesitamos un mecanismo de callback automático.

## Tu tarea

### A. Campo callback_url en TaskEnvelope
Modificar `dispatcher/queue.py`:
- Agregar soporte para campo `callback_url` en el envelope
- Documentar en el docstring

Modificar `worker/app.py`:
- En POST /enqueue, aceptar campo opcional `callback_url` en EnqueueRequest
- Almacenar en el envelope

### B. Callback en el Dispatcher
Modificar `dispatcher/service.py`:
- Después de complete_task o fail_task, verificar si el envelope tiene `callback_url`
- Si existe, hacer POST al callback_url con el resultado:
  ```json
  {
    "task_id": "...",
    "status": "done",
    "task": "research.web",
    "result": {...},
    "completed_at": 1234567890
  }
  ```
- Usar httpx con timeout=10s
- Fire-and-forget (no bloquear el dispatcher si el callback falla)
- Loguear éxito/fallo del callback

### C. Retry del callback
- Si el callback falla (timeout, 5xx), reintentar 1 vez después de 5 segundos
- Loguear si el retry también falla (no bloquear)

### D. Tests
Crear `tests/test_webhook_callback.py`:
- Test: enqueue con callback_url lo almacena en envelope
- Test: complete_task con callback_url hace POST al URL
- Test: callback failure no crashea el dispatcher
- Test: callback retry en 5xx
- Test: sin callback_url no intenta POST

### E. Documentar
Actualizar `docs/07-worker-api-contract.md` con el nuevo campo callback_url.

## Archivos relevantes
- `worker/app.py` — POST /enqueue (agregar callback_url)
- `dispatcher/service.py` — post-ejecución (agregar callback logic)
- `dispatcher/queue.py` — TaskQueue (documentar callback_url)

## Log

### [codex] 2026-03-04 04:51 -03:00
- Implementado soporte `callback_url` en el flujo de enqueue:
  - `worker/models/__init__.py`: `TaskEnvelope` ahora incluye `callback_url` opcional.
  - `worker/app.py`: `POST /enqueue` acepta `callback_url` y lo persiste en el envelope Redis.
  - `dispatcher/queue.py`: docstrings actualizados para documentar el nuevo campo.
- Implementado callback webhook en Dispatcher:
  - `dispatcher/service.py`: al completar/fallar tarea, si hay `callback_url`, dispara POST asíncrono (fire-and-forget).
  - Timeout de callback: 10s.
  - Retry: 1 reintento tras 5s para timeout o HTTP 5xx.
  - Logging explícito de éxito/fallo/retry del callback.
- Tests nuevos:
  - `tests/test_webhook_callback.py` con 5 escenarios:
    - enqueue guarda `callback_url`
    - completion dispara POST
    - fallo de callback no rompe dispatcher
    - retry en 5xx
    - sin `callback_url` no hace POST
- Documentación actualizada:
  - `docs/07-worker-api-contract.md` con `callback_url` en `/enqueue` y contrato del payload webhook.
- Validación ejecutada:
  - `python -m pytest tests/test_enqueue_api.py tests/test_webhook_callback.py tests/test_dispatcher_resilience.py -v -p no:cacheprovider`
  - Resultado: `42 passed`.
