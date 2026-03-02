"""Windows FS binary transfer tasks.

Allows copying files between VPS (caller) and Worker VM via base64.
Use with care: size-limited.

Tasks:
- windows.fs.write_bytes_b64: write bytes to file from base64 payload

Security:
- Path restricted by tool_policy fs.allowed_base_paths
- Max bytes restricted by tool_policy fs.max_bytes_b64 (default 5MB)
"""

from __future__ import annotations

import base64
import logging
import os
import sys
from typing import Any, Dict

from .. import tool_policy

logger = logging.getLogger("worker.tasks.windows_fs_bin")


def _require_allowed_path(path: str) -> str:
    # Reuse the same policy logic as windows_fs.py by importing function.
    from .windows_fs import _require_allowed_path as _req

    return _req(path)


def handle_windows_fs_write_bytes_b64(input_data: Dict[str, Any]) -> Dict[str, Any]:
    if sys.platform != "win32":
        return {"ok": False, "error": "Solo disponible en Windows."}

    path = _require_allowed_path(input_data.get("path", ""))
    b64 = input_data.get("b64")
    if not isinstance(b64, str) or not b64.strip():
        raise ValueError("'b64' (str) is required")

    max_bytes = tool_policy.get_fs_max_bytes_b64()

    try:
        data = base64.b64decode(b64.encode("ascii"), validate=True)
    except Exception as e:
        raise ValueError(f"Invalid base64: {e}")

    if len(data) > max_bytes:
        raise ValueError(f"payload too large: {len(data)} bytes, max {max_bytes}")

    try:
        parent = os.path.dirname(path)
        _require_allowed_path(parent)
        os.makedirs(parent, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return {"ok": True, "path": path, "bytes": len(data), "error": None}
    except Exception as e:
        logger.exception("write_bytes_b64 failed")
        return {"ok": False, "path": path, "bytes": 0, "error": str(e)}
