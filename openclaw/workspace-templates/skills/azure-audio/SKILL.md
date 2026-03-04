---
name: azure-audio
description: >-
  Generate text-to-speech audio via Azure OpenAI Realtime API (gpt-realtime
  deployment). Use when "generate audio", "text to speech", "TTS",
  "create audio file", "say this out loud", "read aloud".
metadata:
  openclaw:
    emoji: "\U0001F50A"
    requires:
      env:
        - AZURE_OPENAI_ENDPOINT
        - AZURE_OPENAI_API_KEY
---

# Azure Audio Skill

Rick puede generar audio (text-to-speech) usando el deployment `gpt-realtime` de Azure AI Foundry a través de la WebSocket Realtime API.

## Requisitos

- `AZURE_OPENAI_ENDPOINT`: Endpoint del recurso Cognitive Services (ej. `https://cursor-api-david.cognitiveservices.azure.com/`).
- `AZURE_OPENAI_API_KEY`: API key del recurso.
- Deployment `gpt-realtime` activo en Azure AI Foundry.

## Task disponible

### Generar audio (TTS)

Task: `azure.audio.generate`

```json
{
  "text": "Hola, soy Rick y estoy listo para trabajar.",
  "voice": "alloy",
  "instructions": "Habla en español mexicano con tono profesional.",
  "deployment": "gpt-realtime",
  "output_path": "/tmp/rick_audio.wav"
}
```

### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `text` | str | sí | Texto a convertir en audio |
| `voice` | str | no | Voz a usar (default: `alloy`) |
| `instructions` | str | no | System instructions para el modelo |
| `deployment` | str | no | Nombre del deployment (default: `gpt-realtime`) |
| `output_path` | str | no | Ruta donde guardar el .wav a disco |

### Voces disponibles

| Voz | Descripción |
|-----|-------------|
| `alloy` | Voz neutra, versátil (default) |
| `ash` | Voz masculina grave |
| `ballad` | Voz expresiva, melódica |
| `coral` | Voz femenina cálida |
| `echo` | Voz masculina clara |
| `sage` | Voz femenina profesional |
| `shimmer` | Voz femenina suave |
| `verse` | Voz masculina narrativa |

### Respuesta

```json
{
  "audio_b64": "UklGR...",
  "audio_size_bytes": 48044,
  "duration_seconds": 1.0,
  "transcript": "Hola, soy Rick...",
  "voice": "alloy",
  "deployment": "gpt-realtime",
  "usage": {"total_tokens": 100, "input_tokens": 20, "output_tokens": 80},
  "output_path": "/tmp/rick_audio.wav"
}
```

## Notas

- El audio se devuelve como WAV base64 (PCM16, 24kHz, mono).
- Si se indica `output_path`, el archivo se guarda a disco además de retornar el base64.
- La API Realtime usa WebSocket; no es REST convencional.
- El deployment `gpt-realtime` debe estar provisionado en Azure AI Foundry.
