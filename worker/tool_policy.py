"""
S5 — ToolPolicy: allowlist de herramientas Windows.

Solo las herramientas/flujos listados en config/tool_policy.yaml
pueden ser invocadas por Rick desde la VM.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("worker.tool_policy")

_DEFAULT = {
    "tools": {
        "pad": {"allowed_flows": ["EchoTest"], "default_timeout_sec": 60},
        "scripts": {"allowed": ["Get-SystemInfo"], "base_path": "C:\\GitHub\\umbral-agent-stack\\scripts\\windows"},
        # Windows filesystem tools (no PAD). Restrict to safe bases.
        "fs": {"allowed_base_paths": ["C:\\Windows\\Temp"]},
        "mcp": {"enabled": False},
    }
}


def _load_policy() -> Dict[str, Any]:
    """Carga config/tool_policy.yaml o devuelve default."""
    try:
        import yaml
    except ImportError:
        return _DEFAULT
    repo = Path(__file__).resolve().parent.parent
    path = repo / "config" / "tool_policy.yaml"
    if not path.is_file():
        return _DEFAULT
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else _DEFAULT
    except Exception as e:
        logger.warning("Failed to load tool_policy.yaml: %s", e)
        return _DEFAULT


def is_pad_flow_allowed(flow_name: str) -> bool:
    """Comprueba si el flujo PAD está permitido."""
    policy = _load_policy()
    allowed = policy.get("tools", {}).get("pad", {}).get("allowed_flows", [])
    ok = flow_name in allowed
    if not ok:
        logger.warning("PAD flow '%s' not in allowlist: %s", flow_name, allowed)
    return ok


def get_pad_timeout_sec() -> int:
    """Timeout por defecto para flujos PAD (segundos)."""
    policy = _load_policy()
    return int(policy.get("tools", {}).get("pad", {}).get("default_timeout_sec", 60))


def is_script_allowed(script_name: str) -> bool:
    """Comprueba si el script está permitido."""
    policy = _load_policy()
    allowed = policy.get("tools", {}).get("scripts", {}).get("allowed", [])
    return script_name in allowed


def get_scripts_base_path() -> str:
    """Ruta base de scripts permitidos."""
    policy = _load_policy()
    return policy.get("tools", {}).get("scripts", {}).get("base_path", "C:\\GitHub\\umbral-agent-stack\\scripts\\windows")


def get_fs_allowed_base_paths() -> List[str]:
    """Allowlist de rutas base para operaciones filesystem en Windows."""
    policy = _load_policy()
    bases = policy.get("tools", {}).get("fs", {}).get("allowed_base_paths", [])
    if not isinstance(bases, list):
        return []
    return [str(x) for x in bases if isinstance(x, str) and x.strip()]
