---
id: "026"
title: "Multi-Model E2E Tests + Scheduled Tasks Validation"
assigned_to: claude-code
branch: feat/claude-multi-model-e2e
round: 6
status: done
updated_at: "2026-03-22T19:04:21-03:00"
created: 2026-03-04
---

## Objetivo

Ampliar `scripts/e2e_validation.py` para validar el sistema multi-modelo y las tareas programadas, asegurando que todo el pipeline ModelRouter → Worker multi-LLM funcione de punta a punta.

## Contexto

- `scripts/e2e_validation.py` — suite E2E existente con 9-10 tests
- Tras la Ronda 6, el Worker soportará Gemini + OpenAI + Anthropic
- `dispatcher/scheduler.py` — scheduler de tareas programadas
- `worker/app.py` — endpoint `/scheduled` ya existe

## Requisitos

### 1. Nuevos tests E2E

Agregar los siguientes tests a `run_e2e_suite()`:

```python
# 11. Multi-model: OpenAI
# POST /run con llm.generate y model="gpt-4o-mini" (si OPENAI_API_KEY disponible)
# Verificar que responde con provider correcto en result

# 12. Multi-model: Anthropic
# POST /run con llm.generate y model="claude-3-haiku-20240307" (si ANTHROPIC_API_KEY disponible)
# Verificar respuesta

# 13. Scheduled tasks: GET /scheduled
# Verificar endpoint responde 200 con lista (puede estar vacía)

# 14. Scheduled tasks: POST + verify
# Encolar una tarea con run_at futuro (+5min), verificar aparece en /scheduled, cancelar

# 15. Quota status: GET /quota/status
# Verificar endpoint responde 200 con providers

# 16. Model routing: verify model injection
# Enviar task con task_type="research", verificar que el resultado usa gemini
# Enviar task con task_type="writing", verificar que intenta claude (o fallback)
```

### 2. Tests condicionales (skip si no hay key)

Para OpenAI y Anthropic, usar skip condicional:

```python
if not os.environ.get("OPENAI_API_KEY"):
    results.append(("Multi-model: OpenAI", "SKIP", 0, "OPENAI_API_KEY not set"))
```

### 3. Actualizar reporte Notion

El reporte E2E en Notion debe incluir los nuevos tests y mostrar SKIP para los que no tienen API key.

### 4. Script de smoke test rápido

Crear `scripts/smoke_test.py` — versión ligera del E2E que solo hace:
- Worker health
- Ping
- Redis connectivity
- Quota status

Para uso rápido post-deploy (< 5 segundos).

### 5. Tests unitarios

- Tests para los nuevos checks E2E (mock HTTP)
- Tests para smoke_test.py

## Entregable

PR a `main` desde `feat/claude-multi-model-e2e` con todos los tests pasando.

## Log

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
