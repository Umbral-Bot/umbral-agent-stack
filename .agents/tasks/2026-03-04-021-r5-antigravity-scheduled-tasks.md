---
id: "021"
title: "Scheduled Tasks Manager — Tareas programadas via Notion"
assigned_to: antigravity
status: assigned
branch: feat/antigravity-scheduled-tasks
priority: high
round: 5
---

# Scheduled Tasks Manager

## Problema
Las tareas solo se ejecutan cuando David escribe en Notion o cuando cron las lanza.
No hay forma de programar una tarea para que se ejecute en el futuro. David debería
poder escribir "investiga tendencias BIM mañana a las 9:00" y Rick lo programa.

## Tu tarea

### A. Módulo dispatcher/scheduler.py
```python
class TaskScheduler:
    """Gestiona tareas programadas almacenadas en Redis."""

    SCHEDULE_KEY = "umbral:scheduled_tasks"

    def schedule(self, envelope, run_at_utc: datetime):
        """Almacena una tarea para ejecutar a la hora indicada."""
        # Guardar en Redis sorted set con score = timestamp

    def check_and_enqueue(self, queue: TaskQueue):
        """Revisa tareas cuyo run_at ya pasó y las encola."""
        # Llamado cada 60s por el poller o un cron

    def list_scheduled(self):
        """Lista tareas programadas (para dashboard)."""

    def cancel(self, task_id):
        """Cancela una tarea programada."""
```

### B. Integrar en intent_classifier.py
Agregar detección de intenciones temporales:
- "mañana a las 9" → schedule para tomorrow 09:00 UTC
- "en 2 horas" → schedule para now + 2h
- "todos los lunes" → crear cron entry (o schedule recurrente)
- Nuevo intent: "scheduled_task" con campo `run_at`

Palabras clave: "mañana", "tomorrow", "en X horas", "a las X",
"próximo lunes", "every", "cada", "programar", "schedule"

### C. Integrar en notion_poller.py
- Si el intent es "scheduled_task", usar scheduler.schedule() en vez de encolar directamente
- Responder: "Rick: Tarea programada para [fecha/hora]. ID: [task_id]"

### D. Check loop
Agregar al daemon del poller (notion-poller-daemon.py) o crear un cron separado
que cada 60s ejecute `scheduler.check_and_enqueue()`.

### E. Endpoint GET /scheduled
Agregar a `worker/app.py` un endpoint que liste las tareas programadas:
```
GET /scheduled
Authorization: Bearer <WORKER_TOKEN>

Response: {"scheduled": [...], "count": 5}
```

### F. Tests
Crear `tests/test_scheduler.py`:
- Test: schedule almacena en Redis sorted set
- Test: check_and_enqueue mueve tareas vencidas a la cola
- Test: tareas futuras no se encolan prematuramente
- Test: cancel elimina la tarea
- Test: detección de "mañana a las 9" en intent_classifier
- Test: detección de "en 2 horas"

## Archivos relevantes
- `dispatcher/queue.py` — TaskQueue (referencia para encolar)
- `dispatcher/intent_classifier.py` — agregar detección temporal
- `dispatcher/notion_poller.py` — integrar scheduler
- `scripts/vps/notion-poller-daemon.py` — agregar check loop
- `worker/app.py` — endpoint /scheduled
