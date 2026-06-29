"""Editorial production model guard — fail explicit if not GPT-5.5 via OpenClaw."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _REPO_ROOT / "config" / "editorial-model.yaml"


class EditorialModelError(RuntimeError):
    """Raised when editorial copy generation cannot guarantee GPT-5.5."""

    def __init__(self, message: str, *, model: str | None = None, agent: str | None = None):
        self.model = model
        self.agent = agent
        super().__init__(message)


def load_editorial_model_config(path: Path | None = None) -> dict[str, Any]:
    p = path or _CONFIG_PATH
    if not p.is_file():
        raise EditorialModelError(
            f"Missing editorial model config: {p}. "
            "Cannot guarantee GPT-5.5 for editorial production."
        )
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def normalize_model_id(model_id: str) -> str:
    return model_id.strip().lower()


def is_editorial_model_allowed(model_id: str, cfg: dict[str, Any] | None = None) -> bool:
    cfg = cfg or load_editorial_model_config()
    required = cfg["required_model_id"]
    return normalize_model_id(model_id) == normalize_model_id(required)


def assert_editorial_model(
    model_id: str,
    *,
    agent: str | None = None,
    context: str = "editorial copy generation",
) -> str:
    """Return model_id if allowed; raise EditorialModelError otherwise."""
    cfg = load_editorial_model_config()
    required = cfg["required_model_id"]
    normalized = normalize_model_id(model_id)

    if normalized == normalize_model_id(required):
        return model_id

    forbidden = [normalize_model_id(m) for m in cfg.get("forbidden_silent_fallback", [])]
    if normalized in forbidden:
        raise EditorialModelError(
            f"BLOCKED: {context} attempted with forbidden model '{model_id}'. "
            f"Required: {required}. No silent fallback.",
            model=model_id,
            agent=agent,
        )

    raise EditorialModelError(
        f"BLOCKED: {context} model '{model_id}' != required '{required}'. "
        "Use OpenClaw with azure-openai-responses/gpt-5.5 or fail explicitly.",
        model=model_id,
        agent=agent,
    )


def verify_openclaw_agent_model(
    openclaw_json_path: Path,
    agent_id: str,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read openclaw.json and verify an agent's primary model matches editorial contract."""
    cfg = cfg or load_editorial_model_config()
    required = cfg["required_model_id"]

    if not openclaw_json_path.is_file():
        raise EditorialModelError(
            f"OpenClaw config not found: {openclaw_json_path}. "
            "Cannot verify GPT-5.5 for editorial agents on VPS."
        )

    data = json.loads(openclaw_json_path.read_text(encoding="utf-8"))
    agents = data.get("agents", {})
    defaults_primary = (
        agents.get("defaults", {}).get("model", {}).get("primary", "")
    )

    agent_entry = None
    for entry in agents.get("list", []):
        if entry.get("id") == agent_id:
            agent_entry = entry
            break

    primary = (
        (agent_entry or {}).get("model", {}).get("primary")
        or defaults_primary
    )
    if not primary:
        raise EditorialModelError(
            f"No model.primary found for agent '{agent_id}' in {openclaw_json_path}"
        )

    assert_editorial_model(primary, agent=agent_id, context="OpenClaw agent config")

    return {
        "agent_id": agent_id,
        "model_primary": primary,
        "required": required,
        "ok": True,
    }


def editorial_model_status_message() -> str:
    cfg = load_editorial_model_config()
    return (
        f"Editorial production requires {cfg['required_model_id']} "
        f"(provider {cfg['required_provider']}, thinking {cfg['thinking_default_editorial']}). "
        "Verify VPS ~/.openclaw/openclaw.json matches docs/audits/openclaw-gpt-5.5-promotion-20260607.md"
    )
