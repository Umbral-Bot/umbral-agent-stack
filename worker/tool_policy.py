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


def get_fs_max_bytes_b64() -> int:
    """Max bytes allowed for base64 binary writes."""
    policy = _load_policy()
    fs = policy.get("tools", {}).get("fs", {})
    val = fs.get("max_bytes_b64", 5_000_000)
    try:
        return int(val)
    except Exception:
        return 5_000_000


# ---------------------------------------------------------------------------
# Copilot CLI capability — F3 policy gate (DISABLED by default).
# Mirrors the YAML stanza ``copilot_cli:`` in config/tool_policy.yaml.
# Defense-in-depth: this is the L2 layer; the L1 env flag
# RICK_COPILOT_CLI_ENABLED must ALSO be true to enable the capability.
# ---------------------------------------------------------------------------

def _copilot_cli_section() -> Dict[str, Any]:
    policy = _load_policy()
    section = policy.get("copilot_cli", {})
    return section if isinstance(section, dict) else {}


def is_copilot_cli_policy_enabled() -> bool:
    """L2 gate: copilot_cli.enabled in tool_policy.yaml. Default False."""
    return bool(_copilot_cli_section().get("enabled", False))


def get_copilot_cli_missions() -> Dict[str, Any]:
    """Return the (possibly empty) missions allowlist.

    Each value is a mission descriptor dict. Empty by default.
    """
    missions = _copilot_cli_section().get("missions", {}) or {}
    return missions if isinstance(missions, dict) else {}


def is_copilot_cli_mission_allowed(name: str) -> bool:
    return bool(name) and name in get_copilot_cli_missions()


def get_copilot_cli_banned_subcommands() -> List[str]:
    raw = _copilot_cli_section().get("banned_subcommands", []) or []
    if not isinstance(raw, list):
        return []
    return [str(p) for p in raw if isinstance(p, str) and p.strip()]


def get_copilot_cli_allowed_models() -> List[str]:
    """Return optional model allowlist for Copilot CLI.

    Empty means "no repo-side restriction beyond input-shape validation".
    Actual availability is still enforced by GitHub Copilot plan/org policy and
    by the installed Copilot CLI version.
    """
    raw = _copilot_cli_section().get("allowed_models", []) or []
    if not isinstance(raw, list):
        return []
    return [str(p).strip() for p in raw if isinstance(p, str) and p.strip()]


def get_copilot_cli_model_aliases() -> Dict[str, str]:
    """Return display-name -> CLI-slug aliases for Copilot CLI models."""
    raw = _copilot_cli_section().get("model_aliases", {}) or {}
    if not isinstance(raw, dict):
        return {}
    aliases: Dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str):
            src = key.strip()
            dst = value.strip()
            if src and dst:
                aliases[src] = dst
    return aliases


def get_copilot_cli_default_model() -> Optional[str]:
    """Return the policy default model slug, if configured."""
    raw = _copilot_cli_section().get("default_model")
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    return value or None


def is_copilot_cli_default_model_forced() -> bool:
    """Whether explicit model overrides must resolve to the default model."""
    return bool(_copilot_cli_section().get("force_default_model", False))


def get_copilot_cli_default_reasoning_effort() -> Optional[str]:
    """Return Copilot CLI reasoning effort, constrained to documented values."""
    raw = _copilot_cli_section().get("default_reasoning_effort")
    if not isinstance(raw, str):
        return None
    value = raw.strip().lower()
    return value if value in {"low", "medium", "high"} else None


def get_copilot_cli_default_limits() -> Dict[str, int]:
    """Return per-mission default ceilings (wall_sec, tokens, files_touched)."""
    s = _copilot_cli_section()
    return {
        "max_wall_sec": int(s.get("default_max_wall_sec", 120) or 120),
        "max_tokens": int(s.get("default_max_tokens", 8000) or 8000),
        "max_files_touched": int(s.get("default_max_files_touched", 0) or 0),
    }


def is_copilot_cli_egress_activated() -> bool:
    """Triple-flag egress activation. Default False — F2/F3/F4 must be False."""
    egress = _copilot_cli_section().get("egress", {}) or {}
    return bool(egress.get("activated", False))
