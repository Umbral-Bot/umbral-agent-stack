---
id: "019"
title: "Error Alert System — Notificaciones push de fallos"
assigned_to: codex
status: done
branch: feat/codex-error-alerts
priority: critical
round: 5
---

# Error Alert System

## Problema
Cuando una tarea falla, nadie se entera. El error queda en ops_log y Redis, pero David
no recibe ninguna notificación. Necesitamos un sistema de alertas push.

## Tu tarea

### A. Módulo dispatcher/alert_manager.py
Crear un AlertManager que envíe notificaciones cuando ocurren eventos críticos:

```python
class AlertManager:
    def __init__(self, worker_client, control_room_page_id):
        self.wc = worker_client
        self.page_id = control_room_page_id
        self._cooldown = {}  # evitar spam de alertas repetidas

    def alert_task_failed(self, task_id, task_name, team, error, envelope):
        """Postea alerta en Notion Control Room cuando una tarea falla."""
        # Formato:
        # Rick: ⚠️ Tarea fallida
        # Task: research.web | Team: marketing
        # Error: Connection timeout
        # ID: abc123...

    def alert_worker_down(self, worker_url, error):
        """Alerta cuando un Worker no responde."""

    def alert_queue_overflow(self, pending_count, threshold=50):
        """Alerta cuando hay demasiadas tareas en cola."""

    def _should_alert(self, key, cooldown_seconds=300):
        """Cooldown para no spamear (5 min entre alertas iguales)."""
```

### B. Integrar en dispatcher/service.py
- Después de `queue.fail_task()`, llamar `alert_manager.alert_task_failed()`
- Después de un connection refused al Worker, llamar `alert_manager.alert_worker_down()`
- Cuando `pending_count > 50`, llamar `alert_manager.alert_queue_overflow()`
- Todo fire-and-forget (daemon threads)

### C. Resumen de alertas en daily digest
Modificar `scripts/daily_digest.py`:
- Contar tareas fallidas del día
- Si hay más de 0 fallos, agregar sección "Alertas" al digest

### D. Tests
Crear `tests/test_alert_manager.py`:
- Test: task_failed genera comment correcto
- Test: worker_down genera alerta
- Test: cooldown previene alertas duplicadas en 5 min
- Test: alert_task_failed con envelope sin campos opcionales no crashea

## Archivos relevantes
- `dispatcher/service.py` — integrar alertas en fail_task y connection refused
- `client/worker_client.py` — WorkerClient (para notion.add_comment)
- `infra/ops_logger.py` — OpsLogger (referencia, no modificar)
- `scripts/daily_digest.py` — agregar sección de alertas

## Log
### [codex] 2026-03-04 08:45
- Implementado `dispatcher/alert_manager.py` con alertas `task_failed`, `worker_down`, `queue_overflow` y cooldown de 300s por clave.
- Integrado en `dispatcher/service.py`:
  - alerta al fallar tarea después de `queue.fail_task(...)`
  - alerta de worker caído en `httpx.ConnectError`
  - alerta de cola saturada cuando `pending_count > 50`
  - todas las notificaciones como fire-and-forget en daemon threads
- Actualizado `scripts/daily_digest.py` con sección `Alertas` cuando hay fallas en la ventana.
- Añadidos tests en `tests/test_alert_manager.py` y ajustados tests de `_run_worker` por nueva firma.
- Tests ejecutados:
  - `python -m pytest tests/test_alert_manager.py tests/test_dispatcher_resilience.py tests/test_webhook_callback.py tests/test_daily_digest.py -v -p no:cacheprovider` → 63 passed
  - `python -m pytest tests/ -q -p no:cacheprovider` → 327 passed, 1 skipped
