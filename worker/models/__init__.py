"""
TaskEnvelope v0.1 — Contrato estándar para tareas en Umbral Agent Stack.

Toda tarea que entra al sistema se envuelve en un TaskEnvelope.
El worker acepta tanto el formato legacy {task, input} como el envelope completo.

Campos core (v0.1):
    schema_version: Versión del schema ("0.1")
    task_id:        UUID único de la tarea
    team:           Equipo destino (marketing, advisory, improvement, lab, system)
    task_type:      Tipo de tarea para routing LLM (coding, writing, research, critical, ms_stack)
    selected_model: Modelo LLM sugerido (puede ser sobrescrito por ModelRouter)
    status:         Estado actual (queued, running, done, failed, degraded, blocked)
    trace_id:       UUID para trazabilidad end-to-end
    created_at:     Timestamp ISO-8601 de creación
    task:           Nombre del handler a ejecutar (e.g. "ping", "notion.add_comment")
    input:          Payload para el handler
    callback_url:   URL opcional para recibir callback HTTP al terminar la tarea
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class Team(str, Enum):
    MARKETING = "marketing"
    ADVISORY = "advisory"
    IMPROVEMENT = "improvement"
    LAB = "lab"
    SYSTEM = "system"


class TaskType(str, Enum):
    CODING = "coding"
    WRITING = "writing"
    RESEARCH = "research"
    CRITICAL = "critical"
    MS_STACK = "ms_stack"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# TaskEnvelope
# ---------------------------------------------------------------------------


class TaskEnvelope(BaseModel):
    """TaskEnvelope v0.1 — contrato mínimo para toda tarea."""

    schema_version: str = "0.1"
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    team: Team = Team.SYSTEM
    task_type: TaskType = TaskType.GENERAL
    selected_model: Optional[str] = None
    status: TaskStatus = TaskStatus.QUEUED
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: Optional[str] = None
    source_kind: Optional[str] = None
    source_comment_id: Optional[str] = None
    linear_issue_id: Optional[str] = None
    project_name: Optional[str] = None
    project_page_id: Optional[str] = None
    deliverable_name: Optional[str] = None
    deliverable_page_id: Optional[str] = None
    notion_track: bool = False

    # --- Payload (compatible con formato legacy) ---
    task: str
    input: Dict[str, Any] = {}
    callback_url: Optional[str] = None


class TaskResult(BaseModel):
    """Resultado de una tarea ejecutada."""

    task_id: str
    task: str
    status: TaskStatus
    result: Dict[str, Any] = {}
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Legacy compat
# ---------------------------------------------------------------------------


class LegacyRunRequest(BaseModel):
    """Formato legacy {task, input} — backward compat."""

    task: str
    input: Dict[str, Any] = {}

    def to_envelope(self) -> TaskEnvelope:
        """Convierte formato legacy a TaskEnvelope."""
        return TaskEnvelope(task=self.task, input=self.input)
