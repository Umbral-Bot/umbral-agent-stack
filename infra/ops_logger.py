"""
Operations Logger — Registro append-only de operaciones del sistema.

Escribe eventos en formato JSONL para tracking detallado y analisis de efectividad.
Ubicacion default: ~/.config/umbral/ops_log.jsonl

Eventos:
  task_queued, task_completed, task_failed, task_blocked, task_retried,
  model_selected, llm_usage, research_usage, quota_warning, quota_restricted, worker_health_change,
  system_activity

Parámetros opcionales de auditoría:
  trace_id      — ID de traza del envelope para correlacionar eventos end-to-end.
                   Disponible en: task_queued, task_completed, task_failed,
                   task_blocked, task_retried, model_selected.
  source        — Origen del envelope (ej. openclaw_gateway, notion_poller).
  source_kind   — Subtipo/canal del origen (ej. tool_enqueue, cron, action_item).
  task_type     — Tipo de tarea lógico para auditoría y métricas.
  input_summary — Resumen truncado (max 200 chars) del input de la tarea.
                   Disponible en: task_completed, task_failed.

Retención:
  El archivo ops_log.jsonl crece indefinidamente. Usar el script
  ``scripts/ops_log_rotate.py`` para purgar eventos antiguos.
  Variable: UMBRAL_OPS_LOG_RETENTION_DAYS (default: 90).
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

    @staticmethod
    def _coerce(value: Any) -> Any:
        return getattr(value, "value", value)

    def _apply_audit_context(
        self,
        event: Dict[str, Any],
        *,
        trace_id: str | None = None,
        task_type: str | None = None,
        source: str | None = None,
        source_kind: str | None = None,
        input_summary: str | None = None,
    ) -> None:
        if trace_id:
            event["trace_id"] = trace_id
        if task_type:
            event["task_type"] = str(self._coerce(task_type))
        if source:
            event["source"] = str(self._coerce(source))[:200]
        if source_kind:
            event["source_kind"] = str(self._coerce(source_kind))[:200]
        if input_summary:
            event["input_summary"] = input_summary[:200]

    def task_queued(
        self,
        task_id: str,
        task: str,
        team: str,
        task_type: str = "general",
        trace_id: str | None = None,
        source: str | None = None,
        source_kind: str | None = None,
    ) -> None:
        ev: Dict[str, Any] = {
            "event": "task_queued",
            "task_id": task_id,
            "task": task,
            "team": self._coerce(team),
            "task_type": str(self._coerce(task_type)),
        }
        self._apply_audit_context(
            ev,
            trace_id=trace_id,
            source=source,
            source_kind=source_kind,
        )
        self._write(ev)

    def task_completed(
        self,
        task_id: str,
        task: str,
        team: str,
        model: str,
        duration_ms: float,
        worker: str = "vps",
        trace_id: str | None = None,
        input_summary: str | None = None,
        task_type: str | None = None,
        source: str | None = None,
        source_kind: str | None = None,
    ) -> None:
        ev: Dict[str, Any] = {
            "event": "task_completed",
            "task_id": task_id,
            "task": task,
            "team": self._coerce(team),
            "model": self._coerce(model),
            "duration_ms": round(duration_ms),
            "worker": worker,
        }
        self._apply_audit_context(
            ev,
            trace_id=trace_id,
            task_type=task_type,
            source=source,
            source_kind=source_kind,
            input_summary=input_summary,
        )
        self._write(ev)

    def task_failed(
        self,
        task_id: str,
        task: str,
        team: str,
        error: str,
        model: str = "",
        trace_id: str | None = None,
        input_summary: str | None = None,
        task_type: str | None = None,
        source: str | None = None,
        source_kind: str | None = None,
    ) -> None:
        ev: Dict[str, Any] = {
            "event": "task_failed",
            "task_id": task_id,
            "task": task,
            "team": self._coerce(team),
            "model": self._coerce(model),
            "error": error[:500],
        }
        self._apply_audit_context(
            ev,
            trace_id=trace_id,
            task_type=task_type,
            source=source,
            source_kind=source_kind,
            input_summary=input_summary,
        )
        self._write(ev)

    def task_blocked(
        self,
        task_id: str,
        task: str,
        team: str,
        reason: str,
        trace_id: str | None = None,
        task_type: str | None = None,
        source: str | None = None,
        source_kind: str | None = None,
    ) -> None:
        ev: Dict[str, Any] = {
            "event": "task_blocked",
            "task_id": task_id,
            "task": task,
            "team": self._coerce(team),
            "reason": reason[:300],
        }
        self._apply_audit_context(
            ev,
            trace_id=trace_id,
            task_type=task_type,
            source=source,
            source_kind=source_kind,
        )
        self._write(ev)

    def task_lost(self, task_id: str, reason: str) -> None:
        self._write({
            "event": "task_lost",
            "task_id": task_id,
            "reason": reason,
        })

    def model_selected(
        self,
        task_id: str,
        task_type: str,
        model: str,
        reason: str = "",
        trace_id: str | None = None,
    ) -> None:
        ev: Dict[str, Any] = {
            "event": "model_selected",
            "task_id": task_id,
            "task_type": task_type,
            "model": model,
            "reason": reason,
        }
        if trace_id:
            ev["trace_id"] = trace_id
        self._write(ev)

    def llm_usage(
        self,
        *,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        duration_ms: float,
        task_id: str | None = None,
        task_type: str | None = None,
        source: str | None = None,
        source_kind: str | None = None,
        usage_component: str | None = None,
    ) -> None:
        ev: Dict[str, Any] = {
            "event": "llm_usage",
            "model": self._coerce(model),
            "provider": self._coerce(provider),
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
            "duration_ms": round(duration_ms),
        }
        if task_id:
            ev["task_id"] = task_id
        if usage_component:
            ev["usage_component"] = str(self._coerce(usage_component))[:120]
        self._apply_audit_context(
            ev,
            task_type=task_type,
            source=source,
            source_kind=source_kind,
        )
        self._write(ev)

    def research_usage(
        self,
        *,
        provider: str,
        result_count: int,
        fallback_reason: str | None = None,
        task_id: str | None = None,
        task_type: str | None = None,
        source: str | None = None,
        source_kind: str | None = None,
    ) -> None:
        ev: Dict[str, Any] = {
            "event": "research_usage",
            "provider": str(self._coerce(provider)),
            "result_count": int(result_count),
        }
        if fallback_reason:
            ev["fallback_reason"] = str(fallback_reason)[:120]
        if task_id:
            ev["task_id"] = task_id
        self._apply_audit_context(
            ev,
            task_type=task_type,
            source=source,
            source_kind=source_kind,
        )
        self._write(ev)

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

    def task_retried(
        self,
        task_id: str,
        task: str,
        team: str,
        retry_count: int,
        trace_id: str | None = None,
        task_type: str | None = None,
        source: str | None = None,
        source_kind: str | None = None,
    ) -> None:
        ev: Dict[str, Any] = {
            "event": "task_retried",
            "task_id": task_id,
            "task": task,
            "team": self._coerce(team),
            "retry_count": retry_count,
        }
        self._apply_audit_context(
            ev,
            trace_id=trace_id,
            task_type=task_type,
            source=source,
            source_kind=source_kind,
        )
        self._write(ev)

    def worker_health_change(self, worker: str, online: bool) -> None:
        self._write({
            "event": "worker_health_change",
            "worker": worker,
            "online": online,
        })

    def system_activity(
        self,
        component: str,
        action: str,
        status: str,
        duration_ms: float,
        *,
        trigger: str | None = None,
        fingerprint: str | None = None,
        notion_reads: int | None = None,
        notion_writes: int | None = None,
        worker_calls: int | None = None,
        db_rows_read: int | None = None,
        details: str | None = None,
    ) -> None:
        ev: Dict[str, Any] = {
            "event": "system_activity",
            "component": component[:120],
            "action": action[:120],
            "status": status[:120],
            "duration_ms": round(duration_ms),
        }
        if trigger:
            ev["trigger"] = trigger[:200]
        if fingerprint:
            ev["fingerprint"] = fingerprint[:64]
        if notion_reads is not None:
            ev["notion_reads"] = int(notion_reads)
        if notion_writes is not None:
            ev["notion_writes"] = int(notion_writes)
        if worker_calls is not None:
            ev["worker_calls"] = int(worker_calls)
        if db_rows_read is not None:
            ev["db_rows_read"] = int(db_rows_read)
        if details:
            ev["details"] = details[:300]
        self._write(ev)

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
