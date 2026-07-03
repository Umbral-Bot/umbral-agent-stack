#!/usr/bin/env python3
"""Patch main agent model fallbacks for voice-critical reliability on VPS.

Adds kimi-k2.5 and google-vertex before the broken google/gemini-3.1-pro-preview fallback.
Creates backup alongside openclaw.json. Does NOT restart gateway.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path.home() / ".openclaw" / "openclaw.json"
VOICE_FALLBACKS = [
    "azure-openai-responses/gpt-5.4",
    "azure-openai-responses/kimi-k2.5",
    "google-vertex/gemini-3.1-pro-preview",
    "azure-openai-responses/gpt-5.2-chat",
    "openai/gpt-5.4",
]


def main() -> int:
    if not CONFIG.exists():
        print(f"ERROR: missing {CONFIG}")
        return 1

    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    agents = data.get("agents", {}).get("list", [])
    main_agent = next((a for a in agents if a.get("id") == "main"), None)
    if not main_agent:
        print("ERROR: main agent not found")
        return 1

    model = main_agent.setdefault("model", {})
    before = list(model.get("fallbacks", []))
    model["fallbacks"] = VOICE_FALLBACKS

    # Ensure alias entries exist for new fallbacks
    defaults_models = data.setdefault("agents", {}).setdefault("defaults", {}).setdefault("models", {})
    for fb in VOICE_FALLBACKS:
        defaults_models.setdefault(fb, {})

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = CONFIG.with_suffix(f".json.bak.voice-fallback.{stamp}")
    shutil.copy2(CONFIG, backup)

    CONFIG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"backup={backup}")
    print(f"before={before}")
    print(f"after={VOICE_FALLBACKS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
