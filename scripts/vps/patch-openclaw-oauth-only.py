#!/usr/bin/env python3
"""Revert OpenClaw to ChatGPT OAuth only — remove Azure AI Foundry.

Rick (`main`) -> openai/gpt-5.6-sol (ChatGPT OAuth, flagship tier).
Other agents keep role-tiered OAuth refs from pre-Foundry matrix.

Run on VPS as user `rick`:
  python3 ~/umbral-agent-stack/scripts/vps/patch-openclaw-oauth-only.py
  openclaw doctor --fix
  systemctl --user restart openclaw-gateway.service
  openclaw models status --probe-provider openai
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path.home() / ".openclaw" / "openclaw.json"
FOUNDRY_PREFIX = "azure-openai-responses/"
OAUTH_PROVIDER_PREFIXES = ("openai-codex/", "openai/")
RICK_MAIN_AGENT = "main"
RICK_MAIN_MODEL = "openai/gpt-5.6-sol"
RICK_MAIN_FALLBACKS = [
    "openai/gpt-5.5",
    "openai-codex/gpt-5.4",
]
OAUTH_DEFAULT_PRIMARY = "openai-codex/gpt-5.4"
OAUTH_DEFAULT_FALLBACKS = [
    "openai-codex/gpt-5.3-codex",
]
CODEX_HEAVY_AGENTS = {
    "rick-orchestrator",
    "rick-communication-director",
    "rick-linkedin-writer",
}
CODEX_LIGHT_AGENTS = {
    "rick-delivery",
    "rick-qa",
    "rick-ops",
    "rick-tracker",
}


def _is_foundry(model_id: str) -> bool:
    return model_id.startswith(FOUNDRY_PREFIX)


def _is_oauth_model(model_id: str) -> bool:
    return model_id.startswith(OAUTH_PROVIDER_PREFIXES)


def _filter_oauth(models: list[str]) -> list[str]:
    return [m for m in models if m and _is_oauth_model(m) and not _is_foundry(m)]


def _oauth_primary_for_agent(agent_id: str) -> str:
    if agent_id == RICK_MAIN_AGENT:
        return RICK_MAIN_MODEL
    if agent_id in CODEX_HEAVY_AGENTS:
        return OAUTH_DEFAULT_PRIMARY
    if agent_id in CODEX_LIGHT_AGENTS:
        return "openai-codex/gpt-5.3-codex"
    return OAUTH_DEFAULT_PRIMARY


def _oauth_fallbacks_for_agent(agent_id: str, existing: list[str]) -> list[str]:
    kept = _filter_oauth(existing)
    if agent_id == RICK_MAIN_AGENT:
        merged = list(RICK_MAIN_FALLBACKS)
        for item in kept:
            if item != RICK_MAIN_MODEL and item not in merged:
                merged.append(item)
        return merged
    merged = list(OAUTH_DEFAULT_FALLBACKS)
    for item in kept:
        if item not in merged:
            merged.append(item)
    return merged


def _patch_agent_model(agent: dict) -> dict[str, str]:
    agent_id = agent.get("id", "")
    primary = _oauth_primary_for_agent(agent_id)
    model = agent.get("model")
    fallbacks: list[str] = []

    if isinstance(model, dict):
        fallbacks = list(model.get("fallbacks") or [])
    elif isinstance(model, str) and not _is_foundry(model) and _is_oauth_model(model):
        if agent_id != RICK_MAIN_AGENT:
            primary = model

    oauth_fallbacks = _oauth_fallbacks_for_agent(agent_id, fallbacks)
    agent["model"] = {"primary": primary, "fallbacks": oauth_fallbacks}
    if agent_id == "rick-tracker":
        agent["thinkingDefault"] = "medium"
    else:
        agent.pop("thinkingDefault", None)
    return {"id": agent_id, "primary": primary, "fallbacks": oauth_fallbacks}


def main() -> int:
    if not CONFIG.exists():
        print(f"ERROR: missing {CONFIG}")
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = CONFIG.with_suffix(f".json.bak.oauth-only.{stamp}")
    shutil.copy2(CONFIG, backup)

    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    models = data.setdefault("models", {})
    providers = models.setdefault("providers", {})
    removed_provider = providers.pop("azure-openai-responses", None)

    defaults = data.setdefault("agents", {}).setdefault("defaults", {})
    defaults.pop("thinkingDefault", None)

    model_defaults = defaults.setdefault("model", {})
    model_defaults["primary"] = OAUTH_DEFAULT_PRIMARY
    model_defaults["fallbacks"] = list(OAUTH_DEFAULT_FALLBACKS)

    allow = defaults.setdefault("models", {})
    oauth_allow = {
        key: value for key, value in allow.items() if _is_oauth_model(key)
    }
    for key in (
        RICK_MAIN_MODEL,
        "openai/gpt-5.5",
        OAUTH_DEFAULT_PRIMARY,
        "openai-codex/gpt-5.3-codex",
    ):
        oauth_allow.setdefault(key, {})
    defaults["models"] = oauth_allow

    agent_reports: list[dict] = []
    for agent in data.get("agents", {}).get("list", []):
        agent_reports.append(_patch_agent_model(agent))

    CONFIG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("PATCH_OK oauth-only")
    print(f"backup={backup}")
    print(f"removed_provider={'yes' if removed_provider else 'no'}")
    print(f"rick_main={RICK_MAIN_MODEL}")
    print(f"defaults_primary={model_defaults['primary']}")
    print(f"defaults_fallbacks={model_defaults['fallbacks']}")
    for report in agent_reports:
        print(
            f"agent={report['id']} primary={report['primary']} "
            f"fallbacks={report['fallbacks']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
