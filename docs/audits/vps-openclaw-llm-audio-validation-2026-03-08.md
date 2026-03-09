# VPS OpenClaw / LLM / Audio Validation — 2026-03-08

## Objetivo

Dejar a Rick operativo en la VPS sin depender de la VM para sus funciones principales:

- coordinación multi-agente con OpenClaw
- tools del Worker para Notion, Linear, Tavily y dominio Umbral
- modelos OpenAI-family disponibles por API keys de la VPS
- Vertex AI operativo para Gemini 3.1
- audio TTS por Azure y Google
- Claude deshabilitado temporalmente

## Cambios aplicados

### Código del repo

- `worker/tasks/llm.py`
  - agrega `UMBRAL_DISABLE_CLAUDE`
  - mantiene alias `gemini_vertex_31`
  - corrige Vertex AI para modelos Gemini 3.x usando `locations/global`
- `dispatcher/model_router.py`
  - si `UMBRAL_DISABLE_CLAUDE=true`, Claude deja de contarse como provider configurado
- `worker/tasks/google_audio.py`
  - nuevo task `google.audio.generate`
- `worker/tasks/azure_audio.py`
  - compatibilidad segura con FastAPI event loop para realtime TTS
- `openclaw/extensions/umbral-worker/index.ts`
  - sanea `audio_b64` en respuestas del gateway para no romper sesiones de Rick
- `openclaw/workspace-templates/skills/llm-generate/SKILL.md`
  - documenta aliases vigentes y `UMBRAL_DISABLE_CLAUDE`

### Configuración y despliegue en VPS

- `~/.config/openclaw/env`
  - `UMBRAL_DISABLE_CLAUDE=true`
  - tokenes y endpoints Worker/Google/Azure sincronizados
- `~/.openclaw/.env`
  - sincronizado para variables que OpenClaw usa al interpolar config
- `~/.openclaw/openclaw.json`
  - `main` y subagentes fijados a `google/gemini-2.5-flash`
  - fallbacks directos limpiados para priorizar Google + Vertex + Azure
  - `umbral_google_audio_generate` agregado a la allowlist de Rick
- `~/.openclaw/extensions/umbral-worker`
  - plugin desplegado y cargado

## Realidad de credenciales en la VPS

Presentes:

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_BASE_URL`
- `KIMI_AZURE_API_KEY`
- `GOOGLE_API_KEY`
- `GOOGLE_API_KEY_RICK_UMBRAL`
- `GOOGLE_CLOUD_PROJECT_RICK_UMBRAL`
- `WORKER_TOKEN`
- `NOTION_API_KEY`
- `LINEAR_API_KEY`
- `TAVILY_API_KEY`

Ausentes:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `FIGMA_API_KEY`
- `GOOGLE_GMAIL_TOKEN`
- `GOOGLE_CALENDAR_TOKEN`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

Conclusión: el acceso OpenAI-family en producción hoy es vía Azure AI Foundry, no vía OpenAI nativo.

## Validación directa del Worker

Probado en `http://127.0.0.1:8088/run` con `WORKER_TOKEN`.

Resultados:

- `llm.generate model=gemini_vertex_31` → `200 OK`
  - provider: `vertex`
  - model real: `gemini-3.1-pro-preview`
- `llm.generate model=gpt-4.1` → `200 OK`
- `llm.generate model=gpt-5.2` → `200 OK`
- `llm.generate model=kimi_azure` → `200 OK`
- `azure.audio.generate` → `200 OK`
  - escribe WAV en `~/.cache/umbral/audio/azure-audio-test.wav`
- `google.audio.generate` → `200 OK`
  - escribe WAV en `~/.cache/umbral/audio/google-audio-test.wav`

## Validación E2E con Rick vía OpenClaw

Probado en `http://127.0.0.1:18789/v1/chat/completions` con `x-openclaw-agent-id: main`.

### Tools de negocio

- `umbral_provider_status` → `azure_foundry, gemini_flash, gemini_flash_lite, gemini_pro, gemini_vertex`
- `umbral_notion_poll_comments` → `OK`
- `umbral_linear_list_teams` → `Umbral`
- `umbral_research_web` → `OK`

### LLMs vía Rick

Validación estable por criterio de disponibilidad de tool:

- `umbral_llm_generate model=gpt-4.1` → `FINAL_GPT41_OK`
- `umbral_llm_generate model=gpt-5.2` → `OK`
- `umbral_llm_generate model=kimi_azure` → `OK`
- `umbral_llm_generate model=gemini_vertex_31` → `OK`

Nota:

- En algunas corridas, `gpt-5.2` devolvió `No response from OpenClaw` aun cuando el Worker respondió `200 OK`.
- Después de fijar `agents.defaults.model.primary` en `google/gemini-2.5-flash` y limpiar fallbacks, la validación volvió a pasar.
- Se considera una inestabilidad de composición del turno del gateway, no del Worker ni del deployment Azure.

### Audio vía Rick

- `umbral_google_audio_generate` → `OK`
  - salida validada en `~/.cache/umbral/audio/final-rick-google.wav`
- `umbral_azure_audio_generate` → `OK`
  - salida validada en `~/.cache/umbral/audio/final-rick-azure.wav`

## Sesiones activas observadas

Resumen al cierre:

- `main`: `103` sesiones registradas
- `rick-ops`: `1`
- `rick-orchestrator`: `1`
- `rick-tracker`: `1`
- `abortedLastRun` en las 20 más recientes de `main`: `0`

Interpretación:

- el runtime ya no está entrando con `tools.entries: []`
- Rick responde con tools reales y no hay abortos persistentes en las sesiones recientes

## Riesgos y pendientes

- `OPENAI_API_KEY` nativa sigue ausente; no se validó OpenAI directo fuera de Azure
- `FIGMA`, `Gmail` y `Calendar` siguen bloqueados por falta de credenciales en la VPS
- OpenClaw todavía puede mostrar warnings menores de allowlist para `apply_patch` en `tools.profile`, pero no bloquean las tools Umbral

## Referencias oficiales usadas

- Google Vertex AI Gemini 3 preview:
  - https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro
- Google Gemini API TTS:
  - https://ai.google.dev/gemini-api/docs/speech-generation
- Google Vertex AI inference:
  - https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference
