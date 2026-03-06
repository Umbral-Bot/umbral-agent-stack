"""
Prueba el endpoint Kimi-K2.5 en Azure Cognitive Services.
Carga KIMI_AZURE_API_KEY desde .env del repo, o ~/.config/openclaw/env, o ~/.openclaw/.env.
Uso (Linux/VPS): python3 scripts/test_kimi_azure.py
Uso (Windows):   python scripts/test_kimi_azure.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

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

_REPO_ROOT = Path(__file__).resolve().parent.parent
_load_env_file(_REPO_ROOT / ".env")
if not os.environ.get("KIMI_AZURE_API_KEY"):
    _load_env_file(Path.home() / ".config" / "openclaw" / "env")
if not os.environ.get("KIMI_AZURE_API_KEY"):
    _load_env_file(Path.home() / ".openclaw" / ".env")

import httpx

ENDPOINT = "https://cursor-api-david.cognitiveservices.azure.com/openai/deployments/Kimi-K2.5/chat/completions"
API_VERSION = "2024-05-01-preview"
URL = f"{ENDPOINT}?api-version={API_VERSION}"


def main() -> int:
    api_key = os.environ.get("KIMI_AZURE_API_KEY", "").strip()
    if not api_key:
        print("ERROR: KIMI_AZURE_API_KEY no está definida. Ponla en .env o export KIMI_AZURE_API_KEY=...")
        return 1

    payload = {
        "model": "Kimi-K2.5",
        "messages": [{"role": "user", "content": "Responde en una sola palabra: capital de Francia."}],
        "max_tokens": 100,
        "temperature": 0.2,
    }

    print("Llamando a Kimi-K2.5 (Azure)...")
    try:
        r = httpx.post(
            URL,
            json=payload,
            headers={"Content-Type": "application/json", "api-key": api_key},
            timeout=30.0,
        )
    except httpx.ConnectError as e:
        print(f"ERROR de conexión: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    if r.status_code != 200:
        print(f"HTTP {r.status_code}: {r.text[:500]}")
        return 1

    data = r.json()
    choices = data.get("choices", [])
    if not choices:
        print("Respuesta sin 'choices':", data)
        return 1

    first = choices[0]
    msg = first.get("message") or {}
    # Azure/Kimi: content puede ser null y la respuesta estar en reasoning_content
    content = msg.get("content")
    if isinstance(content, list):
        content = " ".join(
            (c.get("text", "") if isinstance(c, dict) else str(c)) for c in content
        )
    if content is None or (isinstance(content, str) and not content.strip()):
        content = (msg.get("reasoning_content") or "").strip()
    content = str(content or "").strip()
    if content:
        # Mostrar solo el final si es muy largo (reasoning_content)
        if len(content) > 400:
            content = content[-350:].strip()
        print(f"OK. Respuesta: {content}")
    else:
        finish = first.get("finish_reason", "?")
        print(f"OK (conexión y clave válidas). Sin texto en content/reasoning (finish_reason={finish}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
