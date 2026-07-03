#!/usr/bin/env python3
"""Promote OpenClaw agents to azure-openai-responses/gpt-5.5 with xhigh thinking."""
from __future__ import annotations

import json
from pathlib import Path

TARGET = "azure-openai-responses/gpt-5.5"
FALLBACKS = [
    "azure-openai-responses/gpt-5.4",
    "azure-openai-responses/gpt-5.2-chat",
    "openai/gpt-5.4",
    "google/gemini-3.1-pro-preview",
]
TRACKER_FALLBACKS = [
    "google-vertex/gemini-3.1-pro-preview",
    "google/gemini-3-flash-preview",
    "azure-openai-responses/gpt-5.4",
]


def main() -> None:
    path = Path.home() / ".openclaw" / "openclaw.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    defaults = data.setdefault("agents", {}).setdefault("defaults", {})
    defaults["thinkingDefault"] = "xhigh"

    model_defaults = defaults.setdefault("model", {})
    model_defaults["primary"] = TARGET
    fallbacks = list(model_defaults.get("fallbacks") or [])
    if "azure-openai-responses/gpt-5.4" not in fallbacks:
        fallbacks = ["azure-openai-responses/gpt-5.4"] + [
            x for x in fallbacks if x != TARGET
        ]
    model_defaults["fallbacks"] = fallbacks

    allow = defaults.setdefault("models", {})
    allow.setdefault(TARGET, {})

    for agent in data["agents"].get("list", []):
        agent_id = agent.get("id")
        if agent_id == "rick-tracker":
            agent["thinkingDefault"] = "medium"
            agent["model"] = {"primary": TARGET, "fallbacks": TRACKER_FALLBACKS}
        else:
            agent["thinkingDefault"] = "xhigh"
            agent["model"] = {"primary": TARGET, "fallbacks": FALLBACKS}

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("PATCH_OK")
    print("DEFAULT", defaults["model"]["primary"], defaults.get("thinkingDefault"))
    for agent in data["agents"]["list"]:
        model = agent.get("model", {})
        print(agent["id"], model.get("primary"), agent.get("thinkingDefault"))


if __name__ == "__main__":
    main()
