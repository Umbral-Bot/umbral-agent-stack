# Doc 43 — Agente Gpt-Rick (Azure AI Foundry Cursor)

> Fecha: 2026-03-08
> Rick puede asignar tareas al agente Gpt-Rick publicado en Azure AI Foundry.

## Resumen

El agente **Gpt-Rick** está publicado como Agent Application en el proyecto `rick-api-david-project` del recurso `cursor-api-david.services.ai.azure.com`. Rick puede invocarlo vía Responses API o Activity Protocol.

## Endpoints

| Protocolo | URL |
|-----------|-----|
| **Responses API** | `https://cursor-api-david.services.ai.azure.com/api/projects/rick-api-david-project/applications/Gpt-Rick/protocols/openai/responses?api-version=2025-11-15-preview` |
| **Activity Protocol** | `https://cursor-api-david.services.ai.azure.com/api/projects/rick-api-david-project/applications/Gpt-Rick/protocols/activityprotocol?api-version=2025-11-15-preview` |

El Activity Protocol se usa cuando el agente está publicado en Microsoft 365 o Teams.

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `GPT_RICK_API_KEY` | API key para el agente (opcional) |
| `AZURE_OPENAI_API_KEY` | Fallback si no se define GPT_RICK_API_KEY (mismo proyecto rick-api-david) |
| `GPT_RICK_RESPONSES_URL` | Override de la URL de Responses API (opcional) |
| `GPT_RICK_ACTIVITY_PROTOCOL_URL` | Override de la URL de Activity Protocol (opcional) |

Configurar en `~/.config/openclaw/env` (VPS) o `.env` (local).

## Tests de acceso (stack Rick)

| Test | Descripción |
|------|-------------|
| **Gpt-Rick (Responses API)** | `python3 scripts/test_gpt_rick_agent.py` — verifica acceso al agente publicado. |
| **gpt-realtime (audio)** | `python3 scripts/test_gpt_realtime_audio.py` — genera audio con el deployment gpt-realtime en `cursor-api-david.cognitiveservices.azure.com` y guarda el WAV en el repo. |

### Test de audio (gpt-realtime)

Endpoint: `https://cursor-api-david.cognitiveservices.azure.com` (Cognitive Services).  
Texto de prueba: *"Hola, este es un audio de prueba para el proyecto de Rick"*.  
Salida: `assets/audio/rick_audio_prueba.wav`.

Requiere: `AZURE_OPENAI_ENDPOINT` (opcional; por defecto cursor-api-david.cognitiveservices.azure.com), `AZURE_OPENAI_API_KEY`.  
Dependencia: `websockets` (ya usada por el Worker para `azure.audio.generate`).

## Uso desde Rick

Rick puede delegar tareas al agente Gpt-Rick enviando requests al endpoint de Responses API con `input` como string o mensajes. Ver `openclaw/workspace-templates/TOOLS.md` y `docs/rick-estado-y-capacidades.md`.
