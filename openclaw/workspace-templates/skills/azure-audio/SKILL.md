---
name: azure-audio
description: >-
  Generate text-to-speech audio via Azure AI Foundry GPT Realtime WebSocket API.
  Use when "generate audio", "text to speech", "TTS", "create voice audio",
  "azure audio", "speak this text", "convert text to audio".
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
- `AZURE_OPENAI_API_KEY`: API key del recurso Azure AI Foundry.

## Tasks disponibles

### 1. Generar audio (TTS)

Task: `azure.audio.generate`

```json
{
  "text": "Hola, soy Rick y estoy probando la generación de audio.",
  "voice": "alloy",
  "instructions": "Habla en español mexicano, tono cálido.",
  "output_path": "/tmp/rick_audio.wav"
}
```

Parámetros:

| Parámetro | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `text` | str | ✅ | — | Texto a convertir en audio |
| `voice` | str | — | `alloy` | Voz a usar (ver lista abajo) |
| `instructions` | str | — | — | System instructions para el modelo |
| `deployment` | str | — | `gpt-realtime` | Nombre del deployment en Azure |
| `output_path` | str | — | — | Ruta para guardar el .wav a disco |

### Voces disponibles

| Voz | Descripción |
|---|---|
| `alloy` | Neutral, versátil |
| `ash` | Cálida, conversacional |
| `ballad` | Melodiosa, expresiva |
| `coral` | Clara, articulada |
| `echo` | Grave, resonante |
| `sage` | Madura, reflexiva |
| `shimmer` | Brillante, energética |
| `verse` | Poética, narrativa |

### Respuesta

```json
{
  "audio_b64": "UklGR...",
  "audio_size_bytes": 12345,
  "duration_seconds": 4.7,
  "transcript": "Hola, soy Rick...",
  "voice": "alloy",
  "deployment": "gpt-realtime",
  "usage": {"total_tokens": 100, "input_tokens": 20, "output_tokens": 80},
  "output_path": "/tmp/rick_audio.wav"
}
```

El audio se devuelve como WAV base64 (PCM16, 24kHz, mono). Si se indica `output_path`, también se guarda a disco.

## Notas

- Todas las tasks se encolan vía el Dispatcher a Redis y las ejecuta el Worker.
- El deployment `gpt-realtime` usa la WebSocket Realtime API (no REST Chat Completions).
- Requiere el paquete `websockets` instalado en el Worker.
