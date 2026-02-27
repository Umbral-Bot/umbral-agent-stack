"""Task: ping — Echo de prueba."""

from typing import Any, Dict


def handle_ping(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Devuelve el input recibido como echo."""
    return {"echo": input_data}
