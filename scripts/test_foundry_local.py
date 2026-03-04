#!/usr/bin/env python3
"""
Test local de Azure AI Foundry — ejecutar ANTES de deployar al VPS.

Uso:
  # Opción 1: pasar como env vars
  AZURE_OPENAI_ENDPOINT=https://mi-recurso.openai.azure.com \
  AZURE_OPENAI_API_KEY=mi-key \
  AZURE_OPENAI_DEPLOYMENT=gpt-5.3-codex \
  python3 scripts/test_foundry_local.py

  # Opción 2: interactivo (te pide los datos)
  python3 scripts/test_foundry_local.py --interactive
"""
import json
import os
import sys
import urllib.error
import urllib.request

API_VERSION = "2024-12-01-preview"

def get_config(interactive: bool):
    if interactive:
        endpoint = input("Endpoint (https://...): ").strip().rstrip("/")
        api_key = input("API Key: ").strip()
        deployment = input("Deployment name [gpt-5.3-codex]: ").strip() or "gpt-5.3-codex"
    else:
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.3-codex").strip()
    return endpoint, api_key, deployment


def build_url(endpoint: str, deployment: str) -> str:
    if "services.ai.azure.com" in endpoint:
        return f"{endpoint}/models/{deployment}/chat/completions?api-version={API_VERSION}"
    return f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={API_VERSION}"


def test_call(endpoint: str, api_key: str, deployment: str):
    url = build_url(endpoint, deployment)
    print(f"\n--- Test Azure AI Foundry ---")
    print(f"Endpoint:   {endpoint}")
    print(f"Deployment: {deployment}")
    print(f"URL:        {url}")
    print(f"API Key:    {api_key[:8]}...{api_key[-4:]}")
    print()

    payload = {
        "messages": [
            {"role": "system", "content": "Sos un asistente conciso. Respondé en español."},
            {"role": "user", "content": "Decime en una oración qué sos y qué modelo estás usando."},
        ],
        "max_tokens": 150,
        "temperature": 0.3,
    }
    if "services.ai.azure.com" in endpoint:
        payload["model"] = deployment

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    print("Enviando request...")
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode()[:500]
        except Exception:
            body = ""
        print(f"\n[FAIL] HTTP {exc.code}")
        print(f"Response: {body}")
        if exc.code == 404:
            print("\nPosible causa: deployment no existe o nombre incorrecto.")
            print("Verificá en Azure Portal > tu recurso > Model deployments")
        elif exc.code == 401:
            print("\nPosible causa: API key incorrecta.")
        elif exc.code == 429:
            print("\nPosible causa: cuota excedida o rate limit.")
        return False
    except Exception as exc:
        print(f"\n[FAIL] {exc}")
        return False

    choices = data.get("choices", [])
    if not choices:
        print(f"\n[FAIL] Sin choices en respuesta: {json.dumps(data, indent=2)[:300]}")
        return False

    text = choices[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    model_used = data.get("model", "unknown")

    print(f"\n[OK] Respuesta recibida")
    print(f"  Modelo reportado: {model_used}")
    print(f"  Texto: {text}")
    print(f"  Tokens: prompt={usage.get('prompt_tokens', '?')}, "
          f"completion={usage.get('completion_tokens', '?')}, "
          f"total={usage.get('total_tokens', '?')}")
    print(f"\n  Variables para ~/.config/openclaw/env:")
    print(f"    AZURE_OPENAI_ENDPOINT={endpoint}")
    print(f"    AZURE_OPENAI_API_KEY={api_key}")
    print(f"    AZURE_OPENAI_DEPLOYMENT={deployment}")
    return True


def main():
    interactive = "--interactive" in sys.argv or "-i" in sys.argv
    endpoint, api_key, deployment = get_config(interactive)

    if not endpoint or not api_key:
        print("Faltan datos. Usá --interactive o setea las env vars:")
        print("  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT")
        sys.exit(1)

    ok = test_call(endpoint, api_key, deployment)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
