"""
Dispatcher task routing helpers.

Centraliza la decision de si una task debe ejecutarse en la VM o puede correr
en el Worker local, incluso cuando el equipo base requiera VM.
"""

from __future__ import annotations

from typing import Any, Dict, List

from worker.models import TaskType, Team

_VM_REQUIRED_PREFIXES = (
    "windows.",
    "browser.",
    "gui.",
)

_LOCAL_ONLY_PREFIXES = (
    "research.",
    "llm.",
    "composite.",
    "notion.",
    "linear.",
    "n8n.",
    "google.",
    "azure.",
    "openai.",
    "make.",
    "document.",
    "figma.",
    "gmail.",
    "google_audio.",
    "google_image.",
    "granola.",  # runs on VPS worker, not VM
)


_VALID_TEAM_VALUES = {member.value for member in Team}
_VALID_TASK_TYPE_VALUES = {member.value for member in TaskType}


def normalize_envelope_identity(envelope: Dict[str, Any]) -> List[str]:
    """Coerce team/task_type desconocidos a defaults seguros antes del POST al worker.

    El worker valida TaskEnvelope contra enums cerrados (Team/TaskType) y responde
    400 "Invalid request body" ante valores libres que algunos productores encolan
    sin validar (p. ej. tools del gateway con workerTeam/workerTaskType arbitrarios:
    windows.fs.list con team="ops", task_type="cron"). Diagnostico:
    docs/ops/uas-fossil-disc-plus-20260811.md. Muta el envelope in-place y devuelve
    la lista de correcciones aplicadas (vacia si no hubo).
    """
    fixes: List[str] = []
    team = envelope.get("team")
    if team is not None and team not in _VALID_TEAM_VALUES:
        envelope["team"] = Team.SYSTEM.value
        fixes.append(f"team '{team}' -> '{Team.SYSTEM.value}'")
    task_type = envelope.get("task_type")
    if task_type is not None and task_type not in _VALID_TASK_TYPE_VALUES:
        envelope["task_type"] = TaskType.GENERAL.value
        fixes.append(f"task_type '{task_type}' -> '{TaskType.GENERAL.value}'")
    return fixes


def task_requires_vm(team_requires_vm: bool, task: str) -> bool:
    """
    Decide si una task debe ir a la VM.

    Reglas:
    - si el equipo no requiere VM, nunca forzar VM
    - si la task es local-only, quedarse en VPS aunque el equipo base use VM
    - si la task coincide con prefijos explicitos de VM, usar VM
    - fallback: respetar el requires_vm del equipo
    """
    if not team_requires_vm:
        return False

    for prefix in _LOCAL_ONLY_PREFIXES:
        if task.startswith(prefix):
            return False

    for prefix in _VM_REQUIRED_PREFIXES:
        if task.startswith(prefix):
            return True

    return team_requires_vm