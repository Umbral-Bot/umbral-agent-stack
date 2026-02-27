"""
Dispatcher — Módulo de orquestación del Control Plane (VPS).

Componentes:
    TaskQueue:      Cola de tareas respaldada por Redis
    HealthMonitor:  Vigila la disponibilidad de la VM
    TeamRouter:     Enruta tareas al equipo correcto
"""

from .health import HealthMonitor, SystemLevel
from .queue import TaskQueue
from .router import TeamRouter, TEAM_CAPABILITIES

__all__ = [
    "TaskQueue",
    "HealthMonitor",
    "SystemLevel",
    "TeamRouter",
    "TEAM_CAPABILITIES",
]
