"""
Dispatcher task routing helpers.

Centraliza la decision de si una task debe ejecutarse en la VM o puede correr
en el Worker local, incluso cuando el equipo base requiera VM.
"""

from __future__ import annotations

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