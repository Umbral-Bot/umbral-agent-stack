"""
Operations Logger — Registro append-only de operaciones del sistema.

Escribe eventos en formato JSONL para tracking detallado y analisis de efectividad.
Ubicacion default: ~/.config/umbral/ops_log.jsonl

Eventos:
  task_queued, task_completed, task_failed, task_blocked, task_retried,
  model_selected, llm_usage, research_usage, quota_warning, quota_restricted, worker_health_change,
  system_activity, notion.operation_trace,
  publish_attempt, publish_success, publish_failed

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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

logger = logging.getLogger("infra.ops_logger")

_DEFAULT_LOG_DIR = Path.home() / ".config" / "umbral"
_DEFAULT_LOG_FILE = "ops_log.jsonl"
_lock = threading.Lock()

# Phase 6A — Structured supervisor telemetry whitelist.
#
# Only stable keys emitted by ``to_log_fields()`` on the passive Phase 5
# building blocks (AmbiguitySignal, SupervisorResolution, plus the noop /
# config-validation event builders) may be persisted. Anything else is
# discarded silently to prevent raw user/task text from being written to
# ``ops_log.jsonl``.
_SAFE_SUPERVISOR_FIELD_KEYS: frozenset[str] = frozenset({
    # AmbiguitySignal.to_log_fields()
    "team",
    "is_ambiguous",
    "candidate_for_supervisor_review",
    "reason",
    "signal_type",
    "confidence",
    "matched_terms",
    "fallback",
    # SupervisorResolution.to_log_fields()
    "supervisor_label",
    "resolution_status",
    "target_type",
    "target",
    "fallback_used",
    "should_block",
    # Config validation event fields
    "issue_count",
    "error_count",
    "warning_count",
    "issues",
})

_SUPERVISOR_EVENT_PREFIX = "supervisor."
_SUPERVISOR_SCALAR_TYPES = (str, int, float, bool, type(None))

# Notion manual operation trace — size limits.
#
# These limits exist to keep ``ops_log.jsonl`` small and to block raw
# transcripts, prompts or long Notion page bodies from being persisted as
# part of a ``notion.operation_trace`` event. The event is meant as an audit
# breadcrumb (who / what / when / on which pages), not as a content archive.
_NOTION_OP_DETAILS_MAX = 500
_NOTION_OP_REASON_MAX = 300
_NOTION_OP_ACTION_MAX = 120
_NOTION_OP_ACTOR_MAX = 120
_NOTION_OP_STATUS_MAX = 60
_NOTION_OP_SOURCE_MAX = 200
_NOTION_OP_TARGET_MAX_COUNT = 25
_NOTION_OP_TARGET_ENTRY_MAX = 200
_NOTION_OP_PAGE_ID_MAX = 200
_NOTION_OPERATION_EVENT = "notion.operation_trace"


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

    def supervisor_event(self, record: Any) -> None:
        """
        Persist a structured supervisor observability event (Phase 6A).

        ``record`` is the JSON-serializable dict returned by
        ``SupervisorObservabilityEvent.to_log_record()`` — the stable top-level
        keys are ``event_type``, ``team``, ``task_id``, ``task_type``,
        ``outcome``, ``severity``, ``fields``.

        Design:
        - The event is written to ``ops_log.jsonl`` with ``event``
          set to the ``event_type`` (e.g. ``"supervisor.ambiguity_signal"``)
          so it is filterable by the existing ``read_events(event_filter=...)``
          API and by the monitoring script.
        - Only keys from ``_SAFE_SUPERVISOR_FIELD_KEYS`` are kept in ``fields``.
          Any free-text field (``text``, ``prompt``, ``original_request``,
          ``query``, ``question``) is dropped to preserve the no-raw-text
          invariant established by PR #241.
        - ``event_type`` must start with ``"supervisor."``; otherwise the
          record is silently dropped. This keeps the sink scoped to the
          supervisor telemetry surface only.
        - Defensive end to end: any failure (malformed input, I/O error,
          serialization error) is logged at debug level and swallowed. The
          method never raises, so dispatch is never affected.
        """
        try:
            if not isinstance(record, Mapping):
                return
            event_type = record.get("event_type")
            if not isinstance(event_type, str) or not event_type.startswith(
                _SUPERVISOR_EVENT_PREFIX
            ):
                return

            ev: Dict[str, Any] = {
                "event": event_type,
                "event_type": event_type,
                "team": _coerce_supervisor_scalar(record.get("team")),
                "task_id": _coerce_supervisor_scalar(record.get("task_id")),
                "task_type": _coerce_supervisor_scalar(record.get("task_type")),
                "outcome": _coerce_supervisor_scalar(record.get("outcome")),
                "severity": _coerce_supervisor_scalar(record.get("severity")),
                "fields": _sanitize_supervisor_fields(record.get("fields")),
            }
            self._write(ev)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("supervisor_event persistence failed: %s", exc)

    def notion_operation(
        self,
        *,
        actor: str,
        action: str,
        reason: str,
        raw_page_id: str | None = None,
        target_page_ids: Iterable[str] | None = None,
        source: str | None = None,
        source_kind: str | None = None,
        notion_reads: int | None = None,
        notion_writes: int | None = None,
        status: str = "ok",
        details: str | None = None,
        operation_id: str | None = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Registrar una operacion manual/directa sobre Notion como breadcrumb auditable.

        Uso tipico: scripts/curl/API calls que regularizan Notion por fuera
        del pipeline del Worker (ej. una capitalizacion corregida a mano) y
        que de otra forma no dejarian traza central en ``ops_log.jsonl``.

        Emite un unico evento ``notion.operation_trace`` append-only. El
        metodo:

        - genera un ``operation_id`` UUID4 si no viene provisto;
        - trunca ``details`` / ``reason`` / ``action`` / ``actor`` /
          ``target_page_ids`` a longitudes seguras (ver constantes
          ``_NOTION_OP_*_MAX``);
        - nunca persiste ``raw`` transcript, prompts completos o contenido
          largo de paginas Notion — eso es responsabilidad del caller;
        - nunca rompe la operacion del caller: cualquier fallo de
          serializacion / IO queda contenido y devuelve el evento igual.

        Retorna el dict del evento efectivamente construido (con el
        ``operation_id`` resuelto y los campos truncados), para que el
        caller pueda imprimirlo en stdout / JSON sin tener que releer el
        log.
        """
        resolved_op_id = _normalize_operation_id(operation_id)

        ev: Dict[str, Any] = {
            "event": _NOTION_OPERATION_EVENT,
            "operation_id": resolved_op_id,
            "actor": _truncate(actor, _NOTION_OP_ACTOR_MAX) or "unknown",
            "action": _truncate(action, _NOTION_OP_ACTION_MAX) or "unspecified",
            "reason": _truncate(reason, _NOTION_OP_REASON_MAX) or "",
            "status": _truncate(status, _NOTION_OP_STATUS_MAX) or "ok",
        }

        if source:
            ev["source"] = _truncate(source, _NOTION_OP_SOURCE_MAX)
        if source_kind:
            ev["source_kind"] = _truncate(source_kind, _NOTION_OP_SOURCE_MAX)
        if raw_page_id:
            ev["raw_page_id"] = _truncate(raw_page_id, _NOTION_OP_PAGE_ID_MAX)

        targets = _sanitize_target_page_ids(target_page_ids)
        if targets:
            ev["target_page_ids"] = targets

        if notion_reads is not None:
            try:
                ev["notion_reads"] = int(notion_reads)
            except (TypeError, ValueError):
                pass
        if notion_writes is not None:
            try:
                ev["notion_writes"] = int(notion_writes)
            except (TypeError, ValueError):
                pass

        if details:
            ev["details"] = _truncate(details, _NOTION_OP_DETAILS_MAX)

        if dry_run:
            ev = dict(ev)
            ev["dry_run"] = True
            return ev

        try:
            self._write(ev)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("notion_operation persistence failed: %s", exc)
        return ev

    # ------------------------------------------------------------------
    # Publish tracking events (publish_attempt / publish_success / publish_failed)
    # ------------------------------------------------------------------

    def _build_publish_event(
        self,
        event_name: str,
        *,
        channel: str,
        content_hash: str = "empty",
        idempotency_key: str | None = None,
        publication_id: str | None = None,
        notion_page_id: str | None = None,
        platform_post_id: str | None = None,
        publication_url: str | None = None,
        attempt: int = 1,
        error_kind: str | None = None,
        error_code: str | None = None,
        retryable: bool | None = None,
        provider: str | None = None,
        metadata: Dict[str, Any] | None = None,
        trace_id: str | None = None,
        source: str | None = None,
        source_kind: str | None = None,
        **extra: Any,
    ) -> None:
        from infra.publish_tracking import (
            _SENSITIVE_FIELD_NAMES,
            normalize_publish_channel,
            _derive_idempotency_key,
        )

        norm_channel = normalize_publish_channel(channel)
        safe_hash = str(content_hash or "empty")[:64]
        if not idempotency_key:
            idempotency_key = _derive_idempotency_key(
                norm_channel, safe_hash, notion_page_id,
            )

        ev: Dict[str, Any] = {
            "event": event_name,
            "channel": norm_channel,
            "status": event_name.replace("publish_", ""),
            "content_hash": safe_hash,
            "idempotency_key": idempotency_key[:40],
            "attempt": int(attempt),
        }

        # Optional fields
        if publication_id is not None:
            ev["publication_id"] = str(publication_id)[:200]
        if notion_page_id is not None:
            ev["notion_page_id"] = str(notion_page_id)[:200]
        if platform_post_id is not None:
            ev["platform_post_id"] = str(platform_post_id)[:200]
        if publication_url is not None:
            ev["publication_url"] = str(publication_url)[:500]
        if error_kind is not None:
            ev["error_kind"] = str(error_kind)[:120]
        if error_code is not None:
            ev["error_code"] = str(error_code)[:60]
        if retryable is not None:
            ev["retryable"] = bool(retryable)
        if provider is not None:
            ev["provider"] = str(provider)[:120]
        if trace_id is not None:
            ev["trace_id"] = str(trace_id)[:300]
        if source is not None:
            ev["source"] = str(source)[:200]
        if source_kind is not None:
            ev["source_kind"] = str(source_kind)[:200]

        # Metadata — strip sensitive keys
        if metadata and isinstance(metadata, dict):
            safe_meta = {
                k: v for k, v in metadata.items()
                if k.lower() not in _SENSITIVE_FIELD_NAMES
            }
            if safe_meta:
                ev["metadata"] = safe_meta

        # Extra kwargs — strip sensitive
        for k, v in extra.items():
            if k.lower() not in _SENSITIVE_FIELD_NAMES and k not in ev:
                ev[k] = str(v)[:300] if isinstance(v, str) else v

        self._write(ev)

    def publish_attempt(self, **kwargs: Any) -> None:
        """Record a publish_attempt event (before calling the platform API)."""
        self._build_publish_event("publish_attempt", **kwargs)

    def publish_success(self, **kwargs: Any) -> None:
        """Record a publish_success event (platform confirmed publication)."""
        self._build_publish_event("publish_success", **kwargs)

    def publish_failed(self, **kwargs: Any) -> None:
        """Record a publish_failed event (platform rejected or errored)."""
        self._build_publish_event("publish_failed", **kwargs)

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


def _truncate(value: Any, limit: int) -> str | None:
    """Return ``str(value)`` truncated to ``limit`` chars, or ``None`` if empty."""
    if value is None:
        return None
    try:
        text = str(value)
    except Exception:
        return None
    text = text.strip()
    if not text:
        return None
    if limit > 0 and len(text) > limit:
        return text[:limit]
    return text


def _normalize_operation_id(operation_id: Any) -> str:
    """Return a non-empty operation id, generating a UUID4 if missing/invalid."""
    if operation_id is None:
        return str(uuid.uuid4())
    try:
        text = str(operation_id).strip()
    except Exception:
        return str(uuid.uuid4())
    if not text:
        return str(uuid.uuid4())
    if len(text) > _NOTION_OP_PAGE_ID_MAX:
        text = text[:_NOTION_OP_PAGE_ID_MAX]
    return text


def _sanitize_target_page_ids(targets: Any) -> list[str]:
    """Normalize target_page_ids into a short list of bounded strings."""
    if targets is None:
        return []
    if isinstance(targets, (str, bytes)):
        targets = [targets]
    try:
        iterable = list(targets)
    except TypeError:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in iterable:
        if item is None:
            continue
        try:
            text = str(item).strip()
        except Exception:
            continue
        if not text:
            continue
        if len(text) > _NOTION_OP_TARGET_ENTRY_MAX:
            text = text[:_NOTION_OP_TARGET_ENTRY_MAX]
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= _NOTION_OP_TARGET_MAX_COUNT:
            break
    return out


def _coerce_supervisor_scalar(value: Any) -> Any:
    """Return ``value`` only if it is a JSON-safe scalar, else ``None``."""
    if isinstance(value, _SUPERVISOR_SCALAR_TYPES):
        return value
    return None


def _sanitize_supervisor_fields(fields: Any) -> Dict[str, Any]:
    """Keep only whitelisted keys with JSON-safe primitive/list/dict values.

    Raw free-text fields are never allowed through. Lists are filtered to
    scalars only. Nested dicts are filtered to scalar-valued entries only.
    """
    if not isinstance(fields, Mapping):
        return {}
    out: Dict[str, Any] = {}
    for key, value in fields.items():
        if not isinstance(key, str):
            continue
        if key not in _SAFE_SUPERVISOR_FIELD_KEYS:
            continue
        if isinstance(value, _SUPERVISOR_SCALAR_TYPES):
            out[key] = value
        elif isinstance(value, (list, tuple)):
            out[key] = [
                item for item in value
                if isinstance(item, _SUPERVISOR_SCALAR_TYPES)
            ]
        elif isinstance(value, Mapping):
            out[key] = {
                kk: vv
                for kk, vv in value.items()
                if isinstance(kk, str)
                and isinstance(vv, _SUPERVISOR_SCALAR_TYPES)
            }
    return out


ops_log = OpsLogger()
