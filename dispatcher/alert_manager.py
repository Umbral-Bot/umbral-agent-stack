"""
Dispatcher Alert Manager.

Push alerts to Notion Control Room for critical operational events with cooldown.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from client.worker_client import WorkerClient

logger = logging.getLogger("dispatcher.alert_manager")


class AlertManager:
    """Post critical alerts and suppress duplicates with cooldown."""

    def __init__(
        self,
        worker_client: WorkerClient,
        control_room_page_id: Optional[str] = None,
        cooldown_seconds: int = 300,
        time_fn: Callable[[], float] = time.time,
    ):
        self.wc = worker_client
        self.page_id = control_room_page_id
        self.default_cooldown_seconds = cooldown_seconds
        self._time_fn = time_fn
        self._cooldown: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _should_alert(self, key: str, cooldown_seconds: Optional[int] = None) -> bool:
        """Return True if enough time has passed since the same alert key."""
        window = cooldown_seconds if cooldown_seconds is not None else self.default_cooldown_seconds
        now = self._time_fn()
        with self._lock:
            last = self._cooldown.get(key)
            if last is not None and (now - last) < window:
                return False
            self._cooldown[key] = now
            return True

    def _post(self, text: str) -> bool:
        try:
            self.wc.notion_add_comment(text=text, page_id=self.page_id)
            return True
        except Exception as exc:
            logger.warning("Failed to post alert to Notion: %s", exc)
            return False

    def alert_task_failed(
        self,
        task_id: str,
        task_name: str,
        team: str,
        error: str,
        envelope: Dict[str, Any],
    ) -> bool:
        """Alert when a task fails."""
        err = str(error or "unknown error").strip()[:400]
        task_type = str(envelope.get("task_type", "general"))
        model = str((envelope.get("input") or {}).get("selected_model", "n/a"))
        alert_key = f"task_failed:{task_name}:{team}:{err[:120]}"
        if not self._should_alert(alert_key):
            return False

        text = "\n".join(
            [
                "Rick: ⚠️ Tarea fallida",
                f"Task: {task_name} | Team: {team} | Type: {task_type}",
                f"Error: {err}",
                f"Model: {model}",
                f"ID: {task_id}",
            ]
        )
        return self._post(text)

    def alert_worker_down(self, worker_url: str, error: str) -> bool:
        """Alert when Worker is unavailable (connection refused)."""
        alert_key = f"worker_down:{worker_url}"
        if not self._should_alert(alert_key):
            return False

        err = str(error or "connection refused").strip()[:400]
        text = "\n".join(
            [
                "Rick: 🚨 Worker no responde",
                f"Worker: {worker_url}",
                f"Error: {err}",
            ]
        )
        return self._post(text)

    def alert_queue_overflow(self, pending_count: int, threshold: int = 50) -> bool:
        """Alert when queue pending count exceeds a threshold."""
        alert_key = f"queue_overflow:{threshold}"
        if not self._should_alert(alert_key):
            return False

        text = "\n".join(
            [
                "Rick: ⚠️ Cola saturada",
                f"Pending: {pending_count}",
                f"Threshold: {threshold}",
            ]
        )
        return self._post(text)
