---
id: "023"
title: "Multi-LLM Worker — Soporte OpenAI + Anthropic + Gemini"
assigned_to: codex
branch: feat/codex-multi-llm
round: 6
status: done
created: 2026-03-04
---

## Objetivo

El handler `llm.generate` actualmente solo soporta Google Gemini. Refactorizarlo para que soporte **3 proveedores** reales: Gemini, OpenAI y Anthropic, seleccionando el proveedor según el campo `model` del input.

## Contexto

- `worker/tasks/llm.py` — handler actual, hardcodeado a Gemini API vía `urllib`.
- `dispatcher/model_router.py` — ya selecciona modelo por `task_type` y devuelve nombres como `gemini_pro`, `chatgpt_plus`, `claude_pro`.
- El Dispatcher ya enruta pero el Worker solo sabe hablar con Gemini.

## Requisitos

### 1. Refactorizar `worker/tasks/llm.py`

Crear un sistema de **providers** dentro de `llm.py`:

```python
# Interfaz:
def handle_llm_generate(input_data):
    model = input_data.get("model", "gemini-2.5-flash")
    provider = _detect_provider(model)
    return PROVIDERS[provider](input_data, model)

def _detect_provider(model: str) -> str:
    if "gemini" in model:
        return "gemini"
    elif "gpt" in model or "o1" in model or "o3" in model:
        return "openai"
    elif "claude" in model:
        return "anthropic"
    else:
        return "gemini"  # default
```

### 2. Provider OpenAI (`_call_openai`)

- API: `https://api.openai.com/v1/chat/completions`
- Auth: `Authorization: Bearer {OPENAI_API_KEY}`
- Modelos soportados: `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini`, `gpt-4`
- Mapear `system` a role `system` en messages
- Usar `urllib.request` (sin dependencias nuevas)
- Devolver mismo formato: `{"text": "...", "model": "...", "usage": {...}}`

### 3. Provider Anthropic (`_call_anthropic`)

- API: `https://api.anthropic.com/v1/messages`
- Auth: `x-api-key: {ANTHROPIC_API_KEY}`, `anthropic-version: 2023-06-01`
- Modelos soportados: `claude-sonnet-4-20250514`, `claude-3-5-sonnet`, `claude-3-haiku`
- System prompt va en campo `system` (no en messages)
- Devolver mismo formato

### 4. Mantener backward compatibility

- Si `model` no se pasa, usar `gemini-2.5-flash` (igual que ahora)
- Si `OPENAI_API_KEY` no está y se pide OpenAI → error claro
- Si `ANTHROPIC_API_KEY` no está y se pide Anthropic → error claro

### 5. Tests

Actualizar `tests/test_llm_handler.py`:
- Test OpenAI success (mock urllib)
- Test Anthropic success (mock urllib)
- Test _detect_provider para cada caso
- Test error cuando falta API key del provider solicitado

### 6. Actualizar docs

- `docs/07-worker-api-contract.md` — documentar el campo `model` con proveedores soportados
- `.env.example` — agregar `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

## Entregable

PR a `main` desde `feat/codex-multi-llm` con todos los tests pasando.

## Log

### [codex] 2026-03-04 09:29
- Refactor completo de `worker/tasks/llm.py` a arquitectura multi-provider con deteccion por modelo (`gemini`, `openai`, `anthropic`) y fallback default a Gemini.
- Agregada compatibilidad backward para `selected_model` (ademas de `model`) y resolucion de aliases de routing (`gemini_pro`, `chatgpt_plus`, `claude_pro`, `copilot_pro`) a modelos reales de API.
- Implementados providers:
  - OpenAI (`/v1/chat/completions`, header `Authorization: Bearer ...`)
  - Anthropic (`/v1/messages`, headers `x-api-key` + `anthropic-version`)
  - Gemini existente mantenido como provider dedicado
- Mensajes de error claros por API keys faltantes:
  - `OPENAI_API_KEY not configured`
  - `ANTHROPIC_API_KEY not configured`
- Tests actualizados en `tests/test_llm_handler.py`:
  - OpenAI success mock
  - Anthropic success mock
  - `_detect_provider` parametrizado
  - errores por API key faltante
- Docs actualizadas:
  - `.env.example` (agregadas `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
  - `docs/07-worker-api-contract.md` (campo `model`, proveedores/modelos soportados, errores de configuracion)
- Tests ejecutados:
  - `python -m pytest tests/test_llm_handler.py -v -p no:cacheprovider` -> 13 passed
  - `python -m pytest tests/ -q -p no:cacheprovider` -> 376 passed, 1 skipped
