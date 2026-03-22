---
id: "033"
title: "Multi-Agent E2E Validation + Linear Escalation Tests"
assigned_to: claude-code
branch: feat/claude-multiagent-e2e
round: 8
status: done
updated_at: "2026-03-22T19:04:21-03:00"
created: 2026-02-27
---

## Objetivo

Validar de punta a punta que el sistema multiagente funciona con múltiples providers en paralelo y que la escalación automática a Linear opera correctamente.

## Contexto

- `scripts/e2e_validation.py` — suite E2E existente
- `dispatcher/service.py` — tiene `_escalate_failure_to_linear()` nuevo
- `dispatcher/model_router.py` — tiene `get_configured_providers()` nuevo
- `worker/tasks/llm.py` — providers: anthropic, gemini, vertex, azure_foundry

## Requisitos

### 1. Tests E2E multimodelo

Agregar a `scripts/e2e_validation.py`:

```python
# Test: Claude provider funciona
# POST /run con llm.generate y model="claude-sonnet-4-6"
# Verificar que responde y provider="anthropic"

# Test: Gemini provider funciona  
# POST /run con llm.generate y model="gemini-3.1-pro-preview-customtools"
# Verificar que responde y provider="gemini"

# Test: Vertex provider funciona (si configurado)
# POST /run con llm.generate y model="gemini-3.1-pro-preview" y alias "gemini_vertex"

# Test: Routing elige Claude para coding
# POST /run con task_type="coding" sin especificar model
# Verificar que el modelo seleccionado es claude-sonnet-4-6

# Test: Routing elige Gemini para research
# POST /run con task_type="research" sin especificar model
# Verificar que el modelo seleccionado es gemini-3.1-pro-preview-customtools
```

### 2. Tests unitarios de escalación a Linear

En `tests/test_dispatcher_escalation.py` (nuevo):

```python
# Test: _escalate_failure_to_linear crea issue con datos correctos
# Test: No crea issue si envelope ya tiene linear_issue_id
# Test: No crea issue para tareas linear.* (evitar recursión)
# Test: No crea issue si ESCALATE_FAILURES_TO_LINEAR=false
# Test: Priority mapping correcto (critical=1, coding=2, etc.)
```

### 3. Test de detección de providers

En `tests/test_provider_detection.py` (nuevo):

```python
# Test: get_configured_providers() detecta Anthropic cuando ANTHROPIC_API_KEY está
# Test: get_configured_providers() no incluye azure_foundry sin env vars
# Test: get_configured_providers() detecta todos con env vars completos
# Test: ModelRouter salta provider no configurado en select_model
```

### 4. Test de flujo completo

```python
# Test: Tarea llm.generate con task_type="coding" → selecciona claude_pro → Worker ejecuta → quota se incrementa
# Test: Si claude_pro está en restrict → cae a gemini_pro → Worker ejecuta con gemini
```

## Archivos a crear/modificar

- `scripts/e2e_validation.py` — agregar tests multimodelo
- `tests/test_dispatcher_escalation.py` (nuevo)
- `tests/test_provider_detection.py` (nuevo)

## Criterio de éxito

- Suite E2E pasa con al menos 2 providers distintos respondiendo
- Tests de escalación cubren todos los edge cases
- Tests de detección de providers validan la lógica de env vars
- `python -m pytest tests/ -q` sigue 100% green

## Log

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
