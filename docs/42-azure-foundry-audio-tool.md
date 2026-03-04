# Doc 42 — Azure AI Foundry: Setup, Testing & Audio Tool

> Fecha: 2026-03-04
> Autor: github-copilot
> Sprint: S6-S7 (Hackathon multi-modelo)

## Resumen

Se integró Azure AI Foundry como proveedor LLM y se creó una herramienta de
generación de audio (TTS) disponible como tarea del Worker (`azure.audio.generate`).

## Deployments disponibles en AI Foundry

Recurso: `cursor-api-david.cognitiveservices.azure.com`
Proyecto: `rick-api-david-project`

| Deployment | Modelo | API | Estado |
|---|---|---|---|
| `gpt-5.2-chat` | gpt-5.2-chat-latest | Chat Completions | ✅ Verificado |
| `gpt-4.1` | gpt-4.1-2025-04-14 | Chat Completions | ✅ Verificado |
| `gpt-realtime` | GPT Realtime | WebSocket Realtime API | ✅ Verificado |

### Notas técnicas
- **gpt-5.2-chat** requiere `max_completion_tokens` (NO `max_tokens`).
- **gpt-realtime** NO soporta Chat Completions REST. Usa WebSocket Realtime API.
- La API de listing de deployments (`/openai/deployments`) retorna 404;
  usar el MCP Foundry tool o Azure Portal para listar.

## Variables de entorno

Agregar en `~/.config/openclaw/env`:

```bash
# --- Azure AI Foundry ---
AZURE_OPENAI_ENDPOINT=https://cursor-api-david.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=<tu-key>
AZURE_OPENAI_DEPLOYMENT=gpt-5.2-chat
AZURE_OPENAI_API_VERSION=2024-05-01-preview
AZURE_FOUNDRY_PROJECT=rick-api-david-project
```

El Dispatcher detecta estas variables al reiniciar y activa `azure_foundry`
en el fallback chain de `coding`, `general`, `ms_stack` y `critical`.

## Herramienta: `azure.audio.generate`

### Descripción
Rick puede generar audio (text-to-speech) cuando David lo solicite.
Usa el deployment `gpt-realtime` vía WebSocket Realtime API de Azure OpenAI.

### Cómo invocar

```json
{
  "task": "azure.audio.generate",
  "input": {
    "text": "Hola David, soy Rick. Aquí tienes tu reporte de audio.",
    "voice": "alloy",
    "instructions": "Habla en español de forma profesional.",
    "output_path": "C:/output/rick_audio.wav"
  }
}
```

### Parámetros

| Campo | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `text` | string | ✅ | — | Texto a convertir en audio |
| `voice` | string | — | `alloy` | Voz: alloy, ash, ballad, coral, echo, sage, shimmer, verse |
| `instructions` | string | — | `""` | System instructions para el modelo |
| `deployment` | string | — | `gpt-realtime` | Nombre del deployment |
| `output_path` | string | — | — | Si se indica, guarda el .wav a disco |

### Respuesta

```json
{
  "audio_b64": "<WAV base64>",
  "audio_size_bytes": 225644,
  "duration_seconds": 4.7,
  "transcript": "Hola David, soy Rick. Aquí tienes tu reporte de audio.",
  "voice": "alloy",
  "deployment": "gpt-realtime",
  "usage": {
    "total_tokens": 163,
    "input_tokens": 37,
    "output_tokens": 126
  },
  "output_path": "C:/output/rick_audio.wav"
}
```

### Voces disponibles

| Voz | Descripción |
|---|---|
| `alloy` | Neutral, polivalente |
| `ash` | Clara, firme |
| `ballad` | Suave, melódica |
| `coral` | Cálida, conversacional |
| `echo` | Profunda, resonante |
| `sage` | Sabia, pausada |
| `shimmer` | Brillante, energética |
| `verse` | Narrativa, expresiva |

## Integración con Model Router

Se agregó `azure_foundry` como proveedor en:
- `config/quota_policy.yaml` — con límite de 1000 req/día, warn 80%, restrict 95%
- `dispatcher/model_router.py` — `PROVIDER_MODEL_MAP["azure_foundry"] = "gpt-5.2-chat"`
- Fallback chains: `coding`, `ms_stack`, `general`, `critical` ahora incluyen `azure_foundry`

## Pruebas realizadas

1. **Chat Completions con gpt-5.2-chat** — Respuesta exitosa ("Hola Rick")
2. **Chat Completions con gpt-4.1** — Respuesta exitosa ("Hola Rick, soy GPT-4.1")
3. **Realtime Audio con gpt-realtime** — Audio generado (4.7s WAV, transcript correcto)
4. **Tests unitarios** — 17 tests para `azure.audio.generate` (WAV helper, validación, mock WebSocket, errores)

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `openclaw/env.template` | Agregado bloque Azure AI Foundry |
| `worker/tasks/azure_audio.py` | **NUEVO** — Handler `azure.audio.generate` |
| `worker/tasks/__init__.py` | Registrado handler en `TASK_HANDLERS` |
| `config/quota_policy.yaml` | Agregado provider `azure_foundry` y actualizado routing |
| `dispatcher/model_router.py` | Agregado `azure_foundry` en `PROVIDER_MODEL_MAP` y `DEFAULT_ROUTING` |
| `tests/test_azure_audio.py` | **NUEVO** — 17 tests unitarios |
| `docs/42-azure-foundry-audio-tool.md` | **NUEVO** — Esta documentación |
