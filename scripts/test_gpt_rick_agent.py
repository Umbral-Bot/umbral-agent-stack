#!/usr/bin/env python3
"""
Prueba acceso al agente Gpt-Rick (Azure AI Foundry Cursor API).

Invocación vía Responses API para verificar que el stack puede asignar tareas
al agente publicado en cursor-api-david.services.ai.azure.com.

Carga la API key desde .env, ~/.config/openclaw/env o ~/.openclaw/.env.
Usa GPT_RICK_API_KEY o AZURE_OPENAI_API_KEY como fallback (mismo proyecto rick-api-david).

Uso (Linux/VPS): python3 scripts/test_gpt_rick_agent.py
Uso (Windows):   python scripts/test_gpt_rick_agent.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip().replace("export ", "", 1).strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ.setdefault(k, v)


_load_env_file(_REPO_ROOT / ".env")
_load_env_file(Path.home() / ".config" / "openclaw" / "env")
_load_env_file(Path.home() / ".openclaw" / ".env")

# Endpoints publicados del agente Gpt-Rick (ver imagen de confirmación de publicación)
RESPONSES_URL = os.environ.get(
    "GPT_RICK_RESPONSES_URL",
    "https://cursor-api-david.services.ai.azure.com/api/projects/rick-api-david-project"
    "/applications/Gpt-Rick/protocols/openai/responses?api-version=2025-11-15-preview",
)
ACTIVITY_PROTOCOL_URL = os.environ.get(
    "GPT_RICK_ACTIVITY_PROTOCOL_URL",
    "https://cursor-api-david.services.ai.azure.com/api/projects/rick-api-david-project"
    "/applications/Gpt-Rick/protocols/activityprotocol?api-version=2025-11-15-preview",
)


def main() -> int:
    api_key = (
        os.environ.get("GPT_RICK_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")
    )
    api_key = (api_key or "").strip()
    if not api_key:
        print(
            "ERROR: GPT_RICK_API_KEY o AZURE_OPENAI_API_KEY no definida. "
            "Ponla en .env o ~/.config/openclaw/env"
        )
        return 1

    try:
        import httpx
    except ImportError:
        print("ERROR: instala httpx con: pip install httpx")
        return 1

    payload = {"input": "Responde en una sola palabra: capital de Francia."}
    print("Llamando a Gpt-Rick (Azure AI Foundry Responses API)...")
    print(f"  URL: {RESPONSES_URL[:80]}...")

    try:
        r = httpx.post(
            RESPONSES_URL,
            json=payload,
            headers={"Content-Type": "application/json", "api-key": api_key},
            timeout=30.0,
        )
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    if r.status_code != 200:
        print(f"ERROR: HTTP {r.status_code}")
        print(r.text[:500])
        return 1

    data = r.json()
    # Responses API: output_text o structure según formato
    output = data.get("output_text", "")
    if not output and data.get("output"):
        items = data.get("output", [])
        if items and isinstance(items[0], dict):
            content = items[0].get("content", [])
            if content and isinstance(content[0], dict):
                output = content[0].get("text", "")
        elif isinstance(items, str):
            output = items

    print(f"OK: Gpt-Rick responde correctamente")
    print(f"  Output: {output[:200] if output else '(vacio)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
