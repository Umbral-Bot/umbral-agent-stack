"""
S7 — Sanitización de inputs.

Validaciones para prevenir abuse e injection.
Incluye detección de patrones de inyección, truncado de campos largos,
y validación de tipos esperados.
"""

import json
import logging
import re
from typing import Any, Dict

logger = logging.getLogger("worker.sanitize")

# Límites
MAX_TASK_NAME_LEN = 128
MAX_INPUT_JSON_BYTES = 256 * 1024  # 256 KB
MAX_STRING_VALUE_LEN = 10_000      # per-field max chars
ALLOWED_TASK_PATTERN = re.compile(r"^[a-zA-Z0-9_.\-]+$")
ALLOWED_FLOW_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")

# Injection patterns
_INJECTION_PATTERNS = [
    re.compile(r";\s*(rm|del|drop|exec|system|eval)\b", re.IGNORECASE),
    re.compile(r"\.\./\.\./"),                          # path traversal
    re.compile(r"<script\b", re.IGNORECASE),            # XSS
    re.compile(r"(\bUNION\b.*\bSELECT\b)", re.IGNORECASE),  # SQL injection
    re.compile(r"\$\{.*\}"),                             # template injection
    # Backticks are common in markdown for paths, tasks and file names.
    # Only block command-like content inside backticks, not any inline code span.
    re.compile(
        r"`\s*(rm|del|drop|exec|system|eval|curl|wget|bash|sh|powershell|cmd|python|node)\b[^`]*`",
        re.IGNORECASE,
    ),
]


def _check_injection(value: str, field: str) -> None:
    """Raise ValueError if value matches known injection patterns."""
    for pat in _INJECTION_PATTERNS:
        if pat.search(value):
            logger.warning(
                "Injection attempt blocked in field %r: matched pattern %s (truncated value: %.100r)",
                field, pat.pattern, value[:100],
            )
            raise ValueError(f"Potentially unsafe input detected in {field}")


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


def _sanitize_value(value: Any, path: str = "root") -> Any:
    """
    Recursively sanitize a value:
      - Truncate strings > MAX_STRING_VALUE_LEN
      - Check strings for injection patterns
      - Recurse into dicts and lists
    Returns the sanitized value.
    """
    if isinstance(value, str):
        _check_injection(value, path)
        if len(value) > MAX_STRING_VALUE_LEN:
            logger.warning("Truncating field %r from %d to %d chars", path, len(value), MAX_STRING_VALUE_LEN)
            return value[:MAX_STRING_VALUE_LEN]
        return value
    if isinstance(value, dict):
        return {k: _sanitize_value(v, f"{path}.{k}") for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(v, f"{path}[{i}]") for i, v in enumerate(value)]
    # primitives (int, float, bool, None) pass through
    return value


def sanitize_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida tamaño y estructura del input. Trunca strings demasiado largos.
    Detecta y rechaza posibles intentos de inyección.
    Raise ValueError si excede límites globales.
    """
    if not isinstance(input_data, dict):
        raise ValueError("input must be a JSON object")
    raw = json.dumps(input_data, default=str)
    if len(raw.encode("utf-8")) > MAX_INPUT_JSON_BYTES:
        raise ValueError(f"input too large (max {MAX_INPUT_JSON_BYTES // 1024} KB)")
    return _sanitize_value(input_data, "input")
