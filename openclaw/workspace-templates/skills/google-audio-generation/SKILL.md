---
name: google-audio-generation
description: >-
  Generar audio con la task `google.audio.generate` usando Gemini TTS preview.
  Usar cuando David pida "texto a voz con Google", "audio Gemini", "crear wav",
  "locucion" o cuando un agente necesite documentar honestamente la ruta TTS
  de Google sin inventar soporte.
metadata:
  openclaw:
    emoji: "\U0001F50A"
    requires:
      env:
        - GOOGLE_API_KEY
---

# Google Audio Generation

Esta skill cubre la task `google.audio.generate` del Worker. La implementacion
actual usa la Gemini API preview de TTS y devuelve audio WAV en base64 o lo
guarda a disco si se indica `output_path`.

## Requisitos reales

- `GOOGLE_API_KEY` en el Worker
- salida de red hacia Gemini API
- modelo TTS disponible: por defecto `gemini-2.5-flash-preview-tts`

Si falta `GOOGLE_API_KEY`, la task responde:

```json
{"ok": false, "error": "Google Gemini API no configurada"}
```

## Task disponible

Task: `google.audio.generate`

### Payload minimo

```json
{
  "text": "Hola, soy Rick y este es un audio de prueba."
}
```

### Payload recomendado

```json
{
  "text": "Hola David. Te dejo un resumen de los cambios de hoy.",
  "voice": "Kore",
  "model": "gemini-2.5-flash-preview-tts",
  "instructions": "Habla en espanol neutro, tono profesional y ritmo pausado.",
  "output_path": "G:\\Mi unidad\\Rick-David\\audio\\resumen.wav"
}
```

## Parametros

| Campo | Tipo | Requerido | Notas |
|------|------|-----------|-------|
| `text` | str | si | Texto a convertir en audio |
| `voice` | str | no | Voz prebuilt; default `Kore` |
| `model` | str | no | Default `gemini-2.5-flash-preview-tts` |
| `instructions` | str | no | Instrucciones de estilo o tono |
| `output_path` | str | no | Guarda el WAV a disco ademas de devolver base64 |

## Respuesta

```json
{
  "audio_b64": "UklGR...",
  "audio_size_bytes": 48244,
  "duration_seconds": 4.7,
  "voice": "Kore",
  "model": "gemini-2.5-flash-preview-tts",
  "mime_type": "audio/L16;codec=pcm;rate=24000",
  "usage": {
    "promptTokenCount": 12,
    "candidatesTokenCount": 80,
    "totalTokenCount": 92
  },
  "output_path": "G:\\Mi unidad\\Rick-David\\audio\\resumen.wav"
}
```

## Comportamiento real del handler

- la API devuelve PCM y el Worker lo envuelve como WAV;
- la muestra por defecto es `24 kHz`, `PCM16`, mono;
- `duration_seconds` se calcula a partir del buffer real;
- si Gemini responde HTTP error, el handler levanta `RuntimeError` con el body seguro;
- si no viene `inlineData`, la task falla de forma explicita.

## Cuando conviene usarla

- pruebas de TTS con Google o Gemini
- borradores de locucion
- audio corto de validacion
- comparacion contra `azure.audio.generate`

## Cuando no conviene usarla

- si necesitas garantia de soporte estable de produccion;
- si la VM o el Worker no tienen `GOOGLE_API_KEY`;
- si necesitas streaming o control fino de formato mas alla del WAV que genera el Worker.

## Anti-patrones

- No prometer soporte mas alla de la task actual.
- No asumir que usa Vertex; hoy usa `GOOGLE_API_KEY` y Gemini API.
- No declarar exito si el archivo no se guardo y tampoco llego `audio_b64`.
- No inventar una lista de voces "oficial" mas alla de la voz realmente probada o configurada.

## Siguiente verificacion util

Para comprobar la ruta completa, usa una prueba corta con `output_path` y revisa:

- que el archivo exista;
- que `audio_size_bytes > 0`;
- que `duration_seconds` sea razonable;
- y que el `usage` venga poblado.
