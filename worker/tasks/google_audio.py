"""
Tasks: Google audio generation via Gemini API preview TTS models.

- google.audio.generate: genera audio (text-to-speech) usando Gemini API
  `gemini-2.5-flash-preview-tts` con GOOGLE_API_KEY.

El audio se devuelve como base64 PCM16 24kHz mono envuelto en WAV,
o se guarda a disco si se indica output_path.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict

from .azure_audio import DEFAULT_SAMPLE_RATE, _pcm16_to_wav
from .llm import GEMINI_BASE_URL, _safe_http_error_body

logger = logging.getLogger("worker.tasks.google_audio")

DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = "Kore"
DEFAULT_MAX_OUTPUT_TOKENS = 256


def _detect_sample_rate(mime_type: str) -> int:
    match = re.search(r"rate=(\d+)", mime_type or "")
    if match:
        return int(match.group(1))
    return DEFAULT_SAMPLE_RATE


def handle_google_audio_generate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera audio (TTS) usando Gemini API preview TTS.

    Input:
        text (str, required): Texto a convertir en audio.
        voice (str, optional): Nombre de voz prebuilt. Default: "Kore".
        model (str, optional): Modelo TTS. Default: gemini-2.5-flash-preview-tts.
        instructions (str, optional): System instructions para el modelo.
        output_path (str, optional): Si se indica, guarda el .wav a disco.

    Returns:
        {
            "audio_b64": "...",
            "audio_size_bytes": 12345,
            "duration_seconds": 4.7,
            "voice": "Kore",
            "model": "gemini-2.5-flash-preview-tts",
            "mime_type": "audio/L16;codec=pcm;rate=24000",
            "usage": {...},
            "output_path": "..."
        }
    """
    text = str(input_data.get("text", "")).strip()
    if not text:
        raise ValueError("'text' is required and cannot be empty")

    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "Google Gemini API no configurada"}

    model = str(input_data.get("model") or DEFAULT_MODEL).strip()
    voice = str(input_data.get("voice") or DEFAULT_VOICE).strip()
    instructions = str(input_data.get("instructions") or "").strip()
    output_path = str(input_data.get("output_path") or "").strip()

    payload: Dict[str, Any] = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice,
                    }
                }
            },
            "maxOutputTokens": DEFAULT_MAX_OUTPUT_TOKENS,
        },
    }
    if instructions:
        payload["systemInstruction"] = {"parts": [{"text": instructions}]}

    url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_str = _safe_http_error_body(exc)
        raise RuntimeError(f"Google audio API error {exc.code}: {body_str}")
    except Exception as exc:
        raise RuntimeError(f"Google audio generation failed: {str(exc)[:300]}")

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("No candidates in Google audio response")

    parts = candidates[0].get("content", {}).get("parts", [])
    inline = None
    for part in parts:
        inline_data = part.get("inlineData")
        if inline_data and inline_data.get("data"):
            inline = inline_data
            break
    if not inline:
        raise RuntimeError(f"No audio inlineData in Google audio response: {json.dumps(data)[:500]}")

    mime_type = str(inline.get("mimeType") or "")
    pcm_data = base64.b64decode(str(inline.get("data") or ""))
    sample_rate = _detect_sample_rate(mime_type)
    wav_data = _pcm16_to_wav(pcm_data, sample_rate=sample_rate)
    duration = len(pcm_data) / (sample_rate * 2)

    response: Dict[str, Any] = {
        "audio_b64": base64.b64encode(wav_data).decode("ascii"),
        "audio_size_bytes": len(wav_data),
        "duration_seconds": round(duration, 2),
        "voice": voice,
        "model": model,
        "mime_type": mime_type,
        "usage": data.get("usageMetadata", {}),
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(wav_data)
        response["output_path"] = output_path
        logger.info("Google audio saved to %s (%d bytes, %.1fs)", output_path, len(wav_data), duration)

    logger.info(
        "Google audio generated: voice=%s model=%s duration=%.1fs size=%d bytes",
        voice,
        model,
        duration,
        len(wav_data),
    )
    return response
