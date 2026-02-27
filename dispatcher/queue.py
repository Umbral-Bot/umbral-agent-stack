"""
Dispatcher — Cola de tareas respaldada por Redis.

Encola TaskEnvelopes para ejecución por el Worker (VM),
con soporte para reintento, TTL, y consulta de estado.

Requiere Redis corriendo en el VPS (redis://localhost:6379).
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("dispatcher.queue")


class TaskQueue:
    """
    Cola de tareas persistente usando Redis.

    Streams:
        umbral:tasks:pending   — tareas esperando ejecución
        umbral:tasks:running   — tareas en ejecución
        umbral:tasks:done      — tareas completadas
        umbral:tasks:failed    — tareas fallidas
        umbral:tasks:blocked   — tareas bloqueadas (VM offline, cuota, etc.)

    Hash:
        umbral:task:{task_id}  — estado completo de cada tarea
    """

    QUEUE_PENDING = "umbral:tasks:pending"
    QUEUE_BLOCKED = "umbral:tasks:blocked"
    TASK_KEY_PREFIX = "umbral:task:"
    TASK_TTL_SECONDS = 86400 * 7  # 7 días

    def __init__(self, redis_client):
        """
        Args:
            redis_client: instancia de redis.Redis o redis.asyncio.Redis
        """
        self.redis = redis_client

    # --- Enqueue ---

    def enqueue(self, envelope: Dict[str, Any]) -> str:
        """
        Encola una tarea para ejecución.

        Args:
            envelope: TaskEnvelope como dict

        Returns:
            task_id
        """
        task_id = envelope["task_id"]
        envelope["status"] = "queued"
        envelope["queued_at"] = time.time()

        pipe = self.redis.pipeline()

        # Guardar estado completo
        task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
        pipe.set(task_key, json.dumps(envelope))
        pipe.expire(task_key, self.TASK_TTL_SECONDS)

        # Agregar a cola pendiente (LPUSH para FIFO con RPOP)
        pipe.lpush(self.QUEUE_PENDING, json.dumps({
            "task_id": task_id,
            "task": envelope.get("task", "unknown"),
            "team": envelope.get("team", "system"),
            "task_type": envelope.get("task_type", "general"),
            "queued_at": envelope["queued_at"],
        }))

        pipe.execute()
        logger.info("Enqueued task %s (team=%s, type=%s)",
                     task_id, envelope.get("team"), envelope.get("task_type"))
        return task_id

    # --- Dequeue ---

    def dequeue(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Desencola la siguiente tarea pendiente (blocking pop).

        Args:
            timeout: segundos a esperar si la cola está vacía

        Returns:
            TaskEnvelope dict o None si timeout
        """
        result = self.redis.brpop(self.QUEUE_PENDING, timeout=timeout)
        if result is None:
            return None

        _, raw = result
        meta = json.loads(raw)
        task_id = meta["task_id"]

        # Cargar estado completo
        task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
        full_raw = self.redis.get(task_key)
        if full_raw is None:
            logger.warning("Task %s expired before dequeue", task_id)
            return None

        envelope = json.loads(full_raw)
        envelope["status"] = "running"
        envelope["started_at"] = time.time()
        self.redis.set(task_key, json.dumps(envelope))

        logger.info("Dequeued task %s", task_id)
        return envelope

    # --- Block (VM offline / cuota) ---

    def block_task(self, task_id: str, reason: str) -> None:
        """Mueve una tarea de pendiente a bloqueada."""
        task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
        raw = self.redis.get(task_key)
        if raw is None:
            return

        envelope = json.loads(raw)
        envelope["status"] = "blocked"
        envelope["block_reason"] = reason
        envelope["blocked_at"] = time.time()

        # Remove from pending list (scan and remove matching task_id)
        pending_items = self.redis.lrange(self.QUEUE_PENDING, 0, -1)
        for item in pending_items:
            try:
                meta = json.loads(item)
                if meta.get("task_id") == task_id:
                    self.redis.lrem(self.QUEUE_PENDING, 1, item)
                    break
            except (json.JSONDecodeError, TypeError):
                continue

        pipe = self.redis.pipeline()
        pipe.set(task_key, json.dumps(envelope))
        pipe.lpush(self.QUEUE_BLOCKED, json.dumps({
            "task_id": task_id,
            "reason": reason,
            "blocked_at": envelope["blocked_at"],
        }))
        pipe.execute()
        logger.warning("Blocked task %s: %s", task_id, reason)

    def unblock_all(self) -> List[str]:
        """Re-encola todas las tareas bloqueadas. Retorna IDs."""
        unblocked = []
        while True:
            raw = self.redis.rpop(self.QUEUE_BLOCKED)
            if raw is None:
                break
            meta = json.loads(raw)
            task_id = meta["task_id"]

            task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
            full_raw = self.redis.get(task_key)
            if full_raw is None:
                continue

            envelope = json.loads(full_raw)
            envelope["status"] = "queued"
            envelope.pop("block_reason", None)
            envelope.pop("blocked_at", None)

            self.redis.set(task_key, json.dumps(envelope))
            self.redis.lpush(self.QUEUE_PENDING, json.dumps({
                "task_id": task_id,
                "task": envelope.get("task", "unknown"),
                "team": envelope.get("team", "system"),
                "task_type": envelope.get("task_type", "general"),
                "queued_at": time.time(),
            }))
            unblocked.append(task_id)

        if unblocked:
            logger.info("Unblocked %d tasks: %s", len(unblocked), unblocked)
        return unblocked

    # --- Complete / Fail ---

    def complete_task(self, task_id: str, result: Dict[str, Any]) -> None:
        """Marca tarea como completada."""
        task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
        raw = self.redis.get(task_key)
        if raw is None:
            return

        envelope = json.loads(raw)
        envelope["status"] = "done"
        envelope["result"] = result
        envelope["completed_at"] = time.time()
        self.redis.set(task_key, json.dumps(envelope))
        logger.info("Completed task %s", task_id)

    def fail_task(self, task_id: str, error: str) -> None:
        """Marca tarea como fallida."""
        task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
        raw = self.redis.get(task_key)
        if raw is None:
            return

        envelope = json.loads(raw)
        envelope["status"] = "failed"
        envelope["error"] = error
        envelope["failed_at"] = time.time()
        self.redis.set(task_key, json.dumps(envelope))
        logger.warning("Failed task %s: %s", task_id, error)

    # --- Query ---

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Consulta estado de una tarea."""
        task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
        raw = self.redis.get(task_key)
        if raw is None:
            return None
        return json.loads(raw)

    def pending_count(self) -> int:
        """Cantidad de tareas pendientes."""
        return self.redis.llen(self.QUEUE_PENDING)

    def blocked_count(self) -> int:
        """Cantidad de tareas bloqueadas."""
        return self.redis.llen(self.QUEUE_BLOCKED)

    def queue_stats(self) -> Dict[str, int]:
        """Estadísticas de las colas."""
        return {
            "pending": self.pending_count(),
            "blocked": self.blocked_count(),
        }
