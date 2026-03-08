#!/usr/bin/env python3
"""
Prueba de audio con gpt-realtime (Azure Cognitive Services).

Genera un WAV con el texto "Hola, este es un audio de prueba para el proyecto de Rick"
usando el endpoint cursor-api-david.cognitiveservices.azure.com y guarda el archivo
en el repo (assets/audio/rick_audio_prueba.wav).

Carga API key desde .env, ~/.config/openclaw/env o ~/.openclaw/.env.
Variables: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY.

Uso (Linux/VPS): python3 scripts/test_gpt_realtime_audio.py
Uso (Windows):   python scripts/test_gpt_realtime_audio.py
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

# Endpoint gpt-realtime (Cognitive Services)
DEFAULT_ENDPOINT = "https://cursor-api-david.cognitiveservices.azure.com"
AUDIO_TEXT = "Hola, este es un audio de prueba para el proyecto de Rick"
OUTPUT_REL_PATH = "assets/audio/rick_audio_prueba.wav"


def main() -> int:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/") or DEFAULT_ENDPOINT
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()

    if not api_key:
        print(
            "ERROR: AZURE_OPENAI_API_KEY no definida. "
            "Ponla en .env o ~/.config/openclaw/env"
        )
        return 1

    output_path = _REPO_ROOT / OUTPUT_REL_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure worker is importable
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    from worker.tasks.azure_audio import handle_azure_audio_generate

    os.environ["AZURE_OPENAI_ENDPOINT"] = endpoint

    print("Generando audio con gpt-realtime...")
    print(f"  Endpoint: {endpoint}")
    print(f"  Texto: {AUDIO_TEXT}")
    print(f"  Salida: {output_path}")

    try:
        result = handle_azure_audio_generate({
            "text": AUDIO_TEXT,
            "voice": "alloy",
            "instructions": "Habla en español de forma clara y natural.",
            "deployment": "gpt-realtime",
            "output_path": str(output_path),
        })
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    if result.get("error") or not result.get("audio_b64"):
        print(f"ERROR: {result.get('error', 'no audio generated')}")
        return 1

    size = result.get("audio_size_bytes", 0)
    duration = result.get("duration_seconds", 0)
    transcript = result.get("transcript", "")
    print(f"OK: Audio guardado en {output_path}")
    print(f"  Tamaño: {size} bytes, duración: {duration}s")
    print(f"  Transcript: {transcript[:80]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
