"""
Operations Logger — Registro append-only de operaciones del sistema.

Escribe eventos en formato JSONL para tracking detallado y analisis de efectividad.
Ubicacion default: ~/.config/umbral/ops_log.jsonl

Eventos:
  task_queued, task_completed, task_failed, task_blocked,
  model_selected, quota_warning, quota_restricted, worker_health_change
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("infra.ops_logger")

_DEFAULT_LOG_DIR = Path.home() / ".config" / "umbral"
_DEFAULT_LOG_FILE = "ops_log.jsonl"
_lock = threading.Lock()


class OpsLogger:
    def __init__(self, log_dir: Optional[Path] = None):
        self._dir = log_dir or Path(os.environ.get("UMBRAL_OPS_LOG_DIR", str(_DEFAULT_LOG_DIR)))
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / _DEFAULT_LOG_FILE

    def _write(self, event: Dict[str, Any]) -> None:
        event["ts"] = datetime.now(timezone.utc).isoformat()
        line = json.dumps(event, default=str, ensure_ascii=False)
        with _lock:
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception as e:
                logger.error("Failed to write ops log: %s", e)

    def task_queued(self, task_id: str, task: str, team: str, task_type: str = "general") -> None:
        self._write({
            "event": "task_queued",
            "task_id": task_id,
            "task": task,
            "team": team,
            "task_type": task_type,
        })

    def task_completed(
        self,
        task_id: str,
        task: str,
        team: str,
        model: str,
        duration_ms: float,
        worker: str = "vps",
    ) -> None:
        self._write({
            "event": "task_completed",
            "task_id": task_id,
            "task": task,
            "team": team,
            "model": model,
            "duration_ms": round(duration_ms),
            "worker": worker,
        })

    def task_failed(self, task_id: str, task: str, team: str, error: str, model: str = "") -> None:
        self._write({
            "event": "task_failed",
            "task_id": task_id,
            "task": task,
            "team": team,
            "model": model,
            "error": error[:500],
        })

    def task_blocked(self, task_id: str, task: str, team: str, reason: str) -> None:
        self._write({
            "event": "task_blocked",
            "task_id": task_id,
            "task": task,
            "team": team,
            "reason": reason[:300],
        })

    def model_selected(self, task_id: str, task_type: str, model: str, reason: str = "") -> None:
        self._write({
            "event": "model_selected",
            "task_id": task_id,
            "task_type": task_type,
            "model": model,
            "reason": reason,
        })

    def quota_warning(self, provider: str, usage_pct: float) -> None:
        self._write({
            "event": "quota_warning",
            "provider": provider,
            "usage_pct": round(usage_pct * 100, 1),
        })

    def quota_restricted(self, provider: str, usage_pct: float) -> None:
        self._write({
            "event": "quota_restricted",
            "provider": provider,
            "usage_pct": round(usage_pct * 100, 1),
        })

    def worker_health_change(self, worker: str, online: bool) -> None:
        self._write({
            "event": "worker_health_change",
            "worker": worker,
            "online": online,
        })

    def read_events(self, limit: int = 1000, event_filter: Optional[str] = None) -> list[Dict[str, Any]]:
        """Lee los ultimos N eventos del log (para reportes)."""
        events: list[Dict[str, Any]] = []
        if not self._path.exists():
            return events
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        if event_filter and ev.get("event") != event_filter:
                            continue
                        events.append(ev)
                    except json.JSONDecodeError:
                        continue
            if len(events) > limit:
                events = events[-limit:]
        except Exception as e:
            logger.error("Failed to read ops log: %s", e)
        return events

    @property
    def path(self) -> Path:
        return self._path


ops_log = OpsLogger()
