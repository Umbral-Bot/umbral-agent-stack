"""
Dispatcher - TeamRouter.

Enruta TaskEnvelopes al equipo correcto y gestiona la logica de dispatch.
Opera en el Control Plane (VPS). Equipos y supervisores se cargan desde config/teams.yaml.
"""

import logging
from typing import Any, Callable, Dict, Optional

from .health import HealthMonitor
from .queue import TaskQueue
from .task_routing import task_requires_vm
from .team_config import get_team_capabilities

logger = logging.getLogger("dispatcher.router")

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

            return {
                "action": "blocked",
                "task_id": task_id,
                "reason": reason,
                "system_level": self.health.level.value,
            }

        self.queue.enqueue(envelope)
        logger.info("Dispatched task %s -> team %s", task_id, team)

        return {
            "action": "enqueued",
            "task_id": task_id,
            "team": team,
            "system_level": self.health.level.value,
            "queue_stats": self.queue.queue_stats(),
        }

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
