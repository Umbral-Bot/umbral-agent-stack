"""
Tasks: Azure AI Foundry — Audio generation via GPT Realtime API.

- azure.audio.generate: genera audio (text-to-speech) usando el deployment
  gpt-realtime de Azure AI Foundry a través de la WebSocket Realtime API.

Requiere env vars:
    AZURE_OPENAI_ENDPOINT — endpoint del recurso Cognitive Services
    AZURE_OPENAI_API_KEY  — api-key del recurso

El audio se devuelve como base64 PCM16 24kHz mono envuelto en WAV,
o se guarda a disco si se indica output_path.
"""

import asyncio
import base64
import json
import logging
import os
import struct
from typing import Any, Dict, Optional

try:
    import websockets as _websockets  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    _websockets = None  # type: ignore[assignment]

logger = logging.getLogger("worker.tasks.azure_audio")

# Defaults
DEFAULT_DEPLOYMENT = "gpt-realtime"
DEFAULT_API_VERSION = "2025-04-01-preview"
DEFAULT_VOICE = "alloy"
DEFAULT_SAMPLE_RATE = 24000
SUPPORTED_VOICES = ("alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse")


def _pcm16_to_wav(pcm_data: bytes, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """Wrap raw PCM16 mono data in a WAV container."""
    num_channels = 1
    bits_per_sample = 16
    data_size = len(pcm_data)
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,                  # fmt chunk size
        1,                   # PCM format
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_data


async def _realtime_tts(
    text: str,
    endpoint: str,
    api_key: str,
    deployment: str = DEFAULT_DEPLOYMENT,
    api_version: str = DEFAULT_API_VERSION,
    voice: str = DEFAULT_VOICE,
    instructions: str = "",
) -> Dict[str, Any]:
    """Connect to Azure OpenAI Realtime API via WebSocket and generate audio from text."""
    if _websockets is None:
        raise RuntimeError("websockets package required: pip install websockets")

    host = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
    ws_url = f"wss://{host}/openai/realtime?api-version={api_version}&deployment={deployment}"
    headers = {"api-key": api_key}

    async with _websockets.connect(ws_url, additional_headers=headers) as ws:
        # 1) Configure session
        session_cfg: Dict[str, Any] = {
            "modalities": ["text", "audio"],
            "voice": voice,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": None,
        }
        if instructions:
            session_cfg["instructions"] = instructions
        await ws.send(json.dumps({"type": "session.update", "session": session_cfg}))

        # Wait for session.updated
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            if msg["type"] == "session.updated":
                break
            if msg["type"] == "error":
                raise RuntimeError(f"Session error: {msg.get('error', msg)}")

        # 2) Send text as user message
        await ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}],
            },
        }))
        await ws.send(json.dumps({"type": "response.create"}))

        # 3) Collect response
        audio_chunks = []
        transcript = ""
        usage = {}
        done = False

        while not done:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=30)
                msg = json.loads(raw)
                t = msg["type"]

                if t == "response.audio.delta":
                    audio_chunks.append(base64.b64decode(msg["delta"]))
                elif t == "response.audio_transcript.done":
                    transcript = msg.get("transcript", "")
                elif t == "response.done":
                    resp = msg.get("response", {})
                    usage = resp.get("usage", {})
                    done = True
                elif t == "error":
                    raise RuntimeError(f"Realtime API error: {msg.get('error', msg)}")
            except asyncio.TimeoutError:
                raise RuntimeError("Timeout waiting for Realtime API response")

    pcm_data = b"".join(audio_chunks)
    return {
        "pcm_data": pcm_data,
        "transcript": transcript,
        "usage": usage,
    }


def handle_azure_audio_generate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera audio (TTS) usando Azure AI Foundry gpt-realtime via WebSocket.

    Input:
        text (str, required): Texto a convertir en audio.
        voice (str, optional): Voz a usar. Default: "alloy".
            Opciones: alloy, ash, ballad, coral, echo, sage, shimmer, verse.
        instructions (str, optional): System instructions para el modelo.
        deployment (str, optional): Nombre del deployment. Default: "gpt-realtime".
        output_path (str, optional): Si se indica, guarda el .wav a disco.
            Ejemplo: "C:/output/rick_audio.wav"

    Returns:
        {
            "audio_b64": "...",          # WAV completo en base64
            "audio_size_bytes": 12345,   # Tamano del WAV en bytes
            "duration_seconds": 4.7,     # Duracion estimada del audio
            "transcript": "...",         # Transcripcion del audio generado
            "voice": "alloy",
            "deployment": "gpt-realtime",
            "usage": {...},
            "output_path": "..."         # Solo si se indico output_path
        }
    """
    text = input_data.get("text", "").strip()
    if not text:
        raise ValueError("'text' is required and cannot be empty")

    voice = input_data.get("voice", DEFAULT_VOICE).lower().strip()
    if voice not in SUPPORTED_VOICES:
        raise ValueError(f"Unsupported voice '{voice}'. Options: {', '.join(SUPPORTED_VOICES)}")

    instructions = input_data.get("instructions", "")
    deployment = input_data.get("deployment", DEFAULT_DEPLOYMENT)
    output_path = input_data.get("output_path", "")

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()

    if not endpoint:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT not configured")
    if not api_key:
        raise RuntimeError("AZURE_OPENAI_API_KEY not configured")

    api_version = os.environ.get("AZURE_OPENAI_API_VERSION_REALTIME", DEFAULT_API_VERSION)

    # Run async function
    result = asyncio.run(_realtime_tts(
        text=text,
        endpoint=endpoint,
        api_key=api_key,
        deployment=deployment,
        api_version=api_version,
        voice=voice,
        instructions=instructions,
    ))

    pcm_data = result["pcm_data"]
    wav_data = _pcm16_to_wav(pcm_data)
    duration = len(pcm_data) / (DEFAULT_SAMPLE_RATE * 2)  # 16-bit mono = 2 bytes/sample

    response: Dict[str, Any] = {
        "audio_b64": base64.b64encode(wav_data).decode("ascii"),
        "audio_size_bytes": len(wav_data),
        "duration_seconds": round(duration, 2),
        "transcript": result["transcript"],
        "voice": voice,
        "deployment": deployment,
        "usage": result["usage"],
    }

    if output_path:
        output_path = output_path.strip()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(wav_data)
        response["output_path"] = output_path
        logger.info("Audio saved to %s (%d bytes, %.1fs)", output_path, len(wav_data), duration)

    logger.info(
        "Audio generated: voice=%s, duration=%.1fs, size=%d bytes, transcript='%s'",
        voice, duration, len(wav_data), result["transcript"][:100],
    )
    return response
