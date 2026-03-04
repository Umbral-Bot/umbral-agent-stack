"""
Tasks: LLM generation via Google Gemini API.

- llm.generate: generar texto con un modelo de lenguaje.
"""

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any, Dict

logger = logging.getLogger("worker.tasks.llm")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def handle_llm_generate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera texto usando Google Gemini API.

    Input:
        prompt (str, required): Texto/pregunta para el modelo.
        model (str, optional): Modelo a usar (default: "gemini-2.0-flash").
        max_tokens (int, optional): Máximo de tokens en la respuesta (default: 1024).
        temperature (float, optional): Temperatura de sampling (default: 0.7).
        system (str, optional): System prompt.

    Returns:
        {"text": "...", "model": "...", "usage": {...}}
    """
    prompt = input_data.get("prompt", "").strip()
    if not prompt:
        raise ValueError("'prompt' is required and cannot be empty")

    model = input_data.get("model", "gemini-2.0-flash")
    max_tokens = int(input_data.get("max_tokens", 1024))
    temperature = float(input_data.get("temperature", 0.7))
    system_prompt = input_data.get("system", "")

    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not configured")

    contents = []
    if system_prompt:
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})
        contents.append({"role": "model", "parts": [{"text": "Entendido."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }

    url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={key}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("No candidates in Gemini response")
            text = ""
            for part in candidates[0].get("content", {}).get("parts", []):
                text += part.get("text", "")

            usage = data.get("usageMetadata", {})
            return {
                "text": text,
                "model": model,
                "usage": {
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0),
                },
            }
    except urllib.error.HTTPError as e:
        body_str = ""
        try:
            body_str = e.read().decode()[:300]
        except Exception:
            pass
        raise RuntimeError(f"Gemini API error {e.code}: {body_str}")
    except Exception as e:
        if "RuntimeError" in type(e).__name__:
            raise
        raise RuntimeError(f"Gemini generation failed: {str(e)[:300]}")
