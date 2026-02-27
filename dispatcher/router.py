"""
Dispatcher — TeamRouter.

Enruta TaskEnvelopes al equipo correcto y gestiona la dispatch logic.
Opera en el Control Plane (VPS).
"""

import logging
from typing import Any, Callable, Dict, Optional

from .health import HealthMonitor, SystemLevel
from .queue import TaskQueue

logger = logging.getLogger("dispatcher.router")


# ---------------------------------------------------------------------------
# Equipos disponibles y sus capacidades
# ---------------------------------------------------------------------------

TEAM_CAPABILITIES = {
    "marketing": {
        "description": "Estrategia y ejecución digital",
        "requires_vm": False,  # Puede operar con LLM-only
        "roles": ["supervisor", "seo", "social_media", "copywriting"],
    },
    "advisory": {
        "description": "Asesoría personal y financiera",
        "requires_vm": False,
        "roles": ["supervisor", "financial", "lifestyle"],
    },
    "improvement": {
        "description": "Mejora continua del sistema (OODA)",
        "requires_vm": True,  # Necesita acceso a Langfuse, ChromaDB
        "roles": ["supervisor", "sota_research", "self_evaluation", "implementation"],
    },
    "lab": {
        "description": "Experimentos y pruebas",
        "requires_vm": True,
        "roles": ["researcher"],
    },
    "system": {
        "description": "Tareas internas del sistema",
        "requires_vm": False,
        "roles": ["ping", "health", "admin"],
    },
}


class TeamRouter:
    """
    Enruta TaskEnvelopes al equipo y cola correspondiente.

    Decisiones de routing:
    1. Si VM offline + equipo requiere VM → bloquear tarea
    2. Si VM offline + equipo no requiere VM → ejecutar LLM-only
    3. Si VM online → encolar normalmente
    """

    def __init__(
        self,
        queue: TaskQueue,
        health: HealthMonitor,
        on_alert: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        """
        Args:
            queue: TaskQueue para encolar/bloquear
            health: HealthMonitor para saber estado del sistema
            on_alert: callback(message, context) para alertar a David
        """
        self.queue = queue
        self.health = health
        self.on_alert = on_alert

    def dispatch(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Despacha un TaskEnvelope al equipo correcto.

        Returns:
            Dict con resultado del dispatch:
            - action: "enqueued" | "blocked" | "rejected"
            - task_id: str
            - reason: str (si blocked/rejected)
        """
        task_id = envelope.get("task_id", "unknown")
        team = envelope.get("team", "system")
        task = envelope.get("task", "unknown")

        # Validar equipo
        if team not in TEAM_CAPABILITIES:
            logger.warning("Unknown team '%s' for task %s", team, task_id)
            return {
                "action": "rejected",
                "task_id": task_id,
                "reason": f"Unknown team: {team}. Available: {list(TEAM_CAPABILITIES.keys())}",
            }

        team_info = TEAM_CAPABILITIES[team]

        # ¿VM requerida y no disponible?
        if team_info["requires_vm"] and not self.health.vm_online:
            reason = (
                f"Team '{team}' requires VM but VM is offline. "
                f"Task '{task}' blocked until VM is available."
            )
            logger.warning(reason)
            # Enqueue first to store task state, then block
            self.queue.enqueue(envelope)
            # Dequeue from pending since we're blocking it
            self.queue.block_task(task_id, reason)

            # Alertar a David
            if self.on_alert:
                self.on_alert(
                    f"⚠️ Tarea bloqueada: {task} (equipo {team}). VM offline.",
                    {"task_id": task_id, "team": team, "task": task},
                )

            return {
                "action": "blocked",
                "task_id": task_id,
                "reason": reason,
                "system_level": self.health.level.value,
            }

        # Encolar normalmente
        self.queue.enqueue(envelope)
        logger.info("Dispatched task %s → team %s", task_id, team)

        return {
            "action": "enqueued",
            "task_id": task_id,
            "team": team,
            "system_level": self.health.level.value,
            "queue_stats": self.queue.queue_stats(),
        }

    def on_vm_back(self) -> Dict[str, Any]:
        """
        Llamado cuando la VM vuelve a estar online.
        Re-encola todas las tareas bloqueadas.
        """
        unblocked = self.queue.unblock_all()
        if unblocked:
            msg = f"✅ VM online. {len(unblocked)} tareas re-encoladas: {unblocked}"
            logger.info(msg)
            if self.on_alert:
                self.on_alert(msg, {"unblocked": unblocked})
        return {"unblocked": unblocked}

    def get_team_info(self, team: str) -> Optional[Dict[str, Any]]:
        """Retorna info del equipo o None si no existe."""
        return TEAM_CAPABILITIES.get(team)

    def list_teams(self) -> Dict[str, Any]:
        """Lista equipos disponibles con su estado."""
        teams = {}
        for name, info in TEAM_CAPABILITIES.items():
            available = True
            if info["requires_vm"] and not self.health.vm_online:
                available = False
            teams[name] = {
                **info,
                "available": available,
            }
        return teams
