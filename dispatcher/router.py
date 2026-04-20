"""
Dispatcher - TeamRouter.

Enruta TaskEnvelopes al equipo correcto y gestiona la logica de dispatch.
Opera en el Control Plane (VPS). Equipos y supervisores se cargan desde config/teams.yaml.

Phase 5 slice — supervisor observability wiring (non-blocking, improvement-only):
    ``TeamRouter.dispatch()`` invokes ``_emit_supervisor_observability()`` after
    the dispatch decision has been made. That helper calls the passive Phase 5
    building blocks (``ambiguity_signal``, ``supervisor_resolution``,
    ``supervisor_observability``) to emit structured log records for ambiguous
    improvement tasks only. It never changes the dispatch return value, never
    raises, never enqueues supervisor work, never calls OpenClaw, and never
    includes raw task text in emitted events.
"""

import logging
from typing import Any, Callable, Dict, Optional

from . import ambiguity_signal as _ambiguity_signal
from . import supervisor_observability as _supervisor_observability
from . import supervisor_resolution as _supervisor_resolution
from .health import HealthMonitor
from .queue import TaskQueue
from .task_routing import task_requires_vm
from .team_config import get_team_capabilities

logger = logging.getLogger("dispatcher.router")

# Keys under ``envelope["input"]`` that may carry free-text context for
# ambiguity detection. Text is passed to ``detect_ambiguity_signal()`` only;
# it is never attached to emitted events or log records.
_SUPERVISOR_TEXT_KEYS: tuple[str, ...] = (
    "original_request",
    "text",
    "query",
    "prompt",
    "question",
)

TEAM_CAPABILITIES = get_team_capabilities()


class TeamRouter:
    """
    Enruta TaskEnvelopes al equipo y cola correspondiente.

    Decisiones de routing:
    1. Si la task requiere VM y la VM esta offline -> bloquear tarea
    2. Si la task no requiere VM -> encolar normalmente
    3. Si la VM esta online -> encolar normalmente
    """

    def __init__(
        self,
        queue: TaskQueue,
        health: HealthMonitor,
        on_alert: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        team_capabilities: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.queue = queue
        self.health = health
        self.on_alert = on_alert
        self._capabilities = team_capabilities if team_capabilities is not None else get_team_capabilities()

    def dispatch(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        task_id = envelope.get("task_id", "unknown")
        team = envelope.get("team", "system")
        task = envelope.get("task", "unknown")

        if team not in self._capabilities:
            logger.warning("Unknown team '%s' for task %s", team, task_id)
            return {
                "action": "rejected",
                "task_id": task_id,
                "reason": f"Unknown team: {team}. Available: {list(self._capabilities.keys())}",
            }

        team_info = self._capabilities[team]
        requires_vm = task_requires_vm(bool(team_info["requires_vm"]), task)

        if requires_vm and not self.health.vm_online:
            reason = (
                f"Task '{task}' for team '{team}' requires VM but VM is offline. "
                f"Task '{task}' blocked until VM is available."
            )
            logger.warning(reason)
            self.queue.enqueue_blocked(envelope, reason)

            if self.on_alert:
                self.on_alert(
                    f"Tarea bloqueada: {task} (equipo {team}). VM offline.",
                    {"task_id": task_id, "team": team, "task": task},
                )

            blocked_result = {
                "action": "blocked",
                "task_id": task_id,
                "reason": reason,
                "system_level": self.health.level.value,
            }

            self._emit_supervisor_observability(envelope)
            return blocked_result

        self.queue.enqueue(envelope)
        logger.info("Dispatched task %s -> team %s", task_id, team)

        result = {
            "action": "enqueued",
            "task_id": task_id,
            "team": team,
            "system_level": self.health.level.value,
            "queue_stats": self.queue.queue_stats(),
        }

        self._emit_supervisor_observability(envelope)
        return result

    def _emit_supervisor_observability(self, envelope: Dict[str, Any]) -> None:
        """
        Build and emit supervisor observability events for ambiguous improvement tasks.

        Contract:
        - Improvement-team only: other teams short-circuit immediately.
        - Ambiguity-gated: non-ambiguous improvement tasks emit no events.
        - Non-blocking: any exception is swallowed and dispatch continues.
        - No raw task text in emitted events or log records.
        - No external calls (no OpenClaw, no HTTP, no Redis writes).
        - ``should_block`` from the resolver is ignored for dispatch purposes;
          observability records it, but routing is never affected.
        """
        try:
            team = envelope.get("team") if isinstance(envelope, dict) else None
            if team != "improvement":
                return

            task_id_raw = envelope.get("task_id")
            task_id = task_id_raw if isinstance(task_id_raw, str) else None
            task_raw = envelope.get("task")
            task = task_raw if isinstance(task_raw, str) and task_raw.strip() else None
            task_type_raw = envelope.get("task_type")
            task_type = task_type_raw if isinstance(task_type_raw, str) and task_type_raw.strip() else None

            text = _extract_supervisor_text(envelope)

            try:
                signal = _ambiguity_signal.detect_ambiguity_signal(
                    text,
                    team=team,
                    task=task,
                    task_type=task_type,
                )
            except Exception:
                logger.warning(
                    "supervisor_ambiguity_detection_failed task_id=%s team=%s",
                    task_id,
                    team,
                    exc_info=True,
                )
                return

            if not getattr(signal, "is_ambiguous", False):
                return

            try:
                ambiguity_event = _supervisor_observability.build_ambiguity_signal_event(
                    signal,
                    task_id=task_id,
                    task_type=task_type,
                )
                self._log_supervisor_event(ambiguity_event)
            except Exception:
                logger.warning(
                    "supervisor_ambiguity_event_failed task_id=%s team=%s",
                    task_id,
                    team,
                    exc_info=True,
                )
                return

            try:
                registry = _supervisor_resolution.load_supervisor_registry()
                resolution = _supervisor_resolution.resolve_supervisor(
                    team,
                    teams_config={"teams": self._capabilities},
                    registry=registry,
                )
            except Exception:
                logger.warning(
                    "supervisor_resolution_failed task_id=%s team=%s",
                    task_id,
                    team,
                    exc_info=True,
                )
                return

            try:
                resolution_event = _supervisor_observability.build_supervisor_resolution_event(
                    resolution,
                    task_id=task_id,
                    task_type=task_type,
                )
                self._log_supervisor_event(resolution_event)
            except Exception:
                logger.warning(
                    "supervisor_resolution_event_failed task_id=%s team=%s",
                    task_id,
                    team,
                    exc_info=True,
                )
                return
        except Exception:
            logger.warning(
                "supervisor_observability_failed",
                exc_info=True,
            )

    def _log_supervisor_event(self, event: Any) -> None:
        """Emit a single supervisor observability event via the module logger.

        Safe no-op on any error. Never raises.
        """
        try:
            record = event.to_log_record()
        except Exception:
            return

        try:
            logger.info(
                "supervisor_observability",
                extra={"supervisor_event": record},
            )
        except Exception:
            pass

    def on_vm_back(self) -> Dict[str, Any]:
        unblocked = self.queue.unblock_all()
        if unblocked:
            msg = f"VM online. {len(unblocked)} tareas re-encoladas: {unblocked}"
            logger.info(msg)
            if self.on_alert:
                self.on_alert(msg, {"unblocked": unblocked})
        return {"unblocked": unblocked}

    def get_team_info(self, team: str) -> Optional[Dict[str, Any]]:
        return self._capabilities.get(team)

    def list_teams(self) -> Dict[str, Any]:
        teams = {}
        for name, info in self._capabilities.items():
            available = True
            if info["requires_vm"] and not self.health.vm_online:
                available = False
            teams[name] = {
                **info,
                "available": available,
            }
        return teams


def _extract_supervisor_text(envelope: Dict[str, Any]) -> str:
    """
    Extract free-text context for ambiguity detection only.

    The returned string is passed to ``detect_ambiguity_signal()`` and must
    never be attached to emitted events or log records. Returns an empty
    string when no safe text field is available.
    """
    if not isinstance(envelope, dict):
        return ""
    input_data = envelope.get("input")
    if not isinstance(input_data, dict):
        return ""
    for key in _SUPERVISOR_TEXT_KEYS:
        value = input_data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""
