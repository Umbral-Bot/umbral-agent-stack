---
id: "019"
title: "Error Alert System — Notificaciones push de fallos"
assigned_to: codex
status: assigned
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
