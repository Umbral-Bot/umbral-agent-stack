---
name: llm-generate
description: >-
  Generate text using multiple LLM providers via the Umbral Worker task llm.generate.
  Supports Claude, GPT, Gemini with automatic provider detection and quota-based fallback.
  Use when "generate text", "ask llm", "use claude", "use gemini", "generate with gpt",
  "llm generate", "ask ai model", "text generation".
metadata:
  openclaw:
    emoji: "\U0001F9E0"
    requires:
      env_any:
        - OPENCLAW_GATEWAY_TOKEN
        - ANTHROPIC_API_KEY
        - AZURE_OPENAI_ENDPOINT
        - OPENAI_API_KEY
        - GOOGLE_API_KEY
        - GOOGLE_API_KEY_RICK_UMBRAL
---

# LLM Generate Skill

Rick puede generar texto usando múltiples proveedores LLM a través de la task `llm.generate` del Umbral Worker.

## Requisitos

Se necesita **al menos una** de las siguientes credenciales:

| Provider | Variables de entorno requeridas |
|----------|-------------------------------|
| OpenClaw Proxy (Claude) | `OPENCLAW_GATEWAY_TOKEN` |
| Anthropic directo (Claude) | `ANTHROPIC_API_KEY` |
| Azure AI Foundry (GPT) | `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` |
| OpenAI directo (GPT) | `OPENAI_API_KEY` |
| Google AI Studio (Gemini) | `GOOGLE_API_KEY` |
| Google Vertex AI (Gemini) | `GOOGLE_API_KEY_RICK_UMBRAL` + `GOOGLE_CLOUD_PROJECT_RICK_UMBRAL` |

## Task

### `llm.generate`

Genera texto con detección automática de provider según el modelo solicitado.

**Input:**

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `prompt` | str | **Sí** | — | Texto del prompt |
| `model` | str | No | `gemini-3.1-pro-preview-customtools` | Modelo o alias a usar |
| `max_tokens` | int | No | 1024 | Límite de tokens de respuesta |
| `temperature` | float | No | 0.7 | Temperatura de sampling |
| `system` | str | No | `""` | System prompt |

**Output:**

```json
{"text": "...", "model": "modelo-usado", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}
```

## Providers y auto-detección

El provider se elige automáticamente según el nombre del modelo:

### Claude (modelos con `claude` en el nombre)

1. Si `OPENCLAW_GATEWAY_TOKEN` está configurado → **openclaw_proxy** (gateway local puerto 18789)
2. Si no pero `ANTHROPIC_API_KEY` existe → **anthropic** (API directa)
3. Si ninguno → error explicativo

### GPT / Codex (modelos con `gpt`, `o1`, `o3`, `codex`, `chatgpt`)

1. Si `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` → **azure_foundry**
2. Si no pero `OPENAI_API_KEY` existe → **openai** (API directa)
3. Si ninguno → error explicativo

### Gemini (modelos con `gemini` en el nombre)

1. Si el alias contiene `vertex` → **vertex** (Vertex AI)
2. Si no → **gemini** (Google AI Studio)

## Aliases de modelo

En lugar del nombre completo del modelo, se puede usar un alias:

| Alias | Modelo real | Provider |
|-------|-------------|----------|
| `azure_foundry` | `gpt-5.3-codex` | Azure AI Foundry |
| `claude_pro` | `claude-sonnet-4-6` | openclaw_proxy / anthropic |
| `claude_opus` | `claude-opus-4-6` | openclaw_proxy / anthropic |
| `claude_haiku` | `claude-haiku-4-5` | openclaw_proxy / anthropic |
| `gemini_pro` | `gemini-3.1-pro-preview-customtools` | gemini (AI Studio) |
| `gemini_flash` | `gemini-flash-latest` | gemini (AI Studio) |
| `gemini_flash_lite` | `gemini-flash-lite-latest` | gemini (AI Studio) |
| `gemini_vertex` | `gemini-3.1-pro-preview` | vertex (Vertex AI) |

## Ejemplos de uso

### Claude vía OpenClaw Proxy

```json
{
  "task_type": "llm.generate",
  "input": {
    "prompt": "Resumí este documento en 3 puntos clave",
    "model": "claude_pro",
    "max_tokens": 512,
    "system": "Sos un asistente de análisis de documentos."
  }
}
```

### GPT vía Azure AI Foundry

```json
{
  "task_type": "llm.generate",
  "input": {
    "prompt": "Generá unit tests para esta función Python",
    "model": "azure_foundry",
    "max_tokens": 2048,
    "temperature": 0.3
  }
}
```

### Gemini vía AI Studio (default)

```json
{
  "task_type": "llm.generate",
  "input": {
    "prompt": "Investigá las mejores prácticas de observabilidad en microservicios",
    "model": "gemini_pro",
    "max_tokens": 4096,
    "temperature": 0.5
  }
}
```

### Gemini vía Vertex AI

```json
{
  "task_type": "llm.generate",
  "input": {
    "prompt": "Analizá esta data de ventas y generá insights",
    "model": "gemini_vertex",
    "max_tokens": 2048
  }
}
```

### Claude Opus (tareas críticas)

```json
{
  "task_type": "llm.generate",
  "input": {
    "prompt": "Revisá esta arquitectura y señalá vulnerabilidades de seguridad",
    "model": "claude_opus",
    "max_tokens": 4096,
    "system": "Sos un auditor de seguridad senior."
  }
}
```

### Modelo por defecto (sin especificar)

```json
{
  "task_type": "llm.generate",
  "input": {
    "prompt": "Explicá qué es OODA loop en español"
  }
}
```

Usa `gemini-3.1-pro-preview-customtools` por defecto.

## Routing por task_type (Dispatcher)

El Dispatcher selecciona el modelo óptimo según el tipo de tarea:

| task_type | Preferido | Fallback chain |
|-----------|-----------|----------------|
| `coding` | claude_pro | gemini_pro → azure_foundry → gemini_flash |
| `general` | claude_pro | gemini_pro → azure_foundry → gemini_flash |
| `writing` | claude_pro | claude_opus → gemini_pro |
| `research` | gemini_pro | gemini_vertex → claude_pro → gemini_flash |
| `critical` | claude_opus | claude_pro → gemini_pro |
| `light` | gemini_flash | gemini_flash_lite → claude_haiku → gemini_pro |

## Notas

- Todas las llamadas se tracean en Langfuse (`trace_llm_call`) con modelo, provider, tokens, latencia.
- Las cuotas se gestionan por el `QuotaTracker` en Redis con ventanas configurables.
- Si un provider no responde en 60s (90s para OpenClaw), timeout automático.
- Los modelos `o1` y `o3` de OpenAI no soportan `temperature` ni `max_tokens` estándar — se usan `max_completion_tokens`.
- Referencia: `worker/tasks/llm.py`, `docs/15-model-quota-policy.md`.
