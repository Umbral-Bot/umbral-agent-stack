"""
S7 — Sanitización de inputs.

Validaciones básicas para prevenir abuse e injection.
"""

import json
import re
from typing import Any, Dict

# Límites
MAX_TASK_NAME_LEN = 128
MAX_INPUT_JSON_BYTES = 256 * 1024  # 256 KB
MAX_STRING_VALUE_LEN = 4096
ALLOWED_TASK_PATTERN = re.compile(r"^[a-zA-Z0-9_.\-]+$")
ALLOWED_FLOW_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


def sanitize_task_name(task: str) -> str:
    """Valida y devuelve el nombre de la tarea. Raise ValueError si inválido."""
    if not task or not isinstance(task, str):
        raise ValueError("task must be non-empty string")
    if len(task) > MAX_TASK_NAME_LEN:
        raise ValueError(f"task name too long (max {MAX_TASK_NAME_LEN})")
    if not ALLOWED_TASK_PATTERN.match(task):
        raise ValueError(f"task name contains invalid characters: {task!r}")
    return task.strip()


def sanitize_pad_flow_name(flow_name: str) -> str:
    """Valida flow_name para PAD. Raise ValueError si inválido."""
    if not flow_name or not isinstance(flow_name, str):
        raise ValueError("flow_name must be non-empty string")
    if len(flow_name) > MAX_TASK_NAME_LEN:
        raise ValueError(f"flow_name too long (max {MAX_TASK_NAME_LEN})")
    if not ALLOWED_FLOW_PATTERN.match(flow_name):
        raise ValueError(f"flow_name contains invalid characters: {flow_name!r}")
    return flow_name.strip()


def sanitize_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida tamaño y estructura del input. No modifica contenido.
    Raise ValueError si excede límites.
    """
    if not isinstance(input_data, dict):
        raise ValueError("input must be a JSON object")
    raw = json.dumps(input_data, default=str)
    if len(raw.encode("utf-8")) > MAX_INPUT_JSON_BYTES:
        raise ValueError(f"input too large (max {MAX_INPUT_JSON_BYTES // 1024} KB)")
    return input_data
