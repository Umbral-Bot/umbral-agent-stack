---
id: "024"
title: "Dispatcher Model Routing — Integrar ModelRouter al flujo real de despacho"
assigned_to: github-copilot
branch: feat/copilot-model-routing
round: 6
status: done
created: 2026-03-04
---

## Objetivo

El `ModelRouter` existe en `dispatcher/model_router.py` pero no está integrado al flujo real de despacho. Conectarlo para que cada tarea que pase por el Dispatcher reciba el modelo óptimo antes de enviarse al Worker.

## Contexto

- `dispatcher/service.py` — loop principal del Dispatcher. Dequeue de Redis → envía a Worker. No usa ModelRouter.
- `dispatcher/model_router.py` — `ModelRouter.select_model(task_type)` devuelve `ModelSelectionDecision(model, reason, requires_approval)`.
- `dispatcher/quota_tracker.py` — `QuotaTracker` trackea uso por provider en Redis.
- `worker/tasks/llm.py` — acepta campo `model` en input (tras tarea 023 soportará multi-provider).

## Requisitos

### 1. Integrar ModelRouter en el Dispatcher loop

En `dispatcher/service.py`, antes de enviar la tarea al Worker:

```python
# Pseudocódigo:
if envelope.get("task") in ("llm.generate", "composite.research_report"):
    decision = model_router.select_model(envelope.get("task_type", "general"))
    if decision.requires_approval:
        logger.warning("Quota exceeded for %s, needs approval", decision.model)
        # Opcional: mover a cola blocked
    else:
        envelope.setdefault("input", {})["model"] = _map_provider_to_model(decision.model)
        logger.info("ModelRouter selected %s (reason: %s)", decision.model, decision.reason)
```

### 2. Mapeo provider → modelo real

Crear un mapeo de provider names (`gemini_pro`, `chatgpt_plus`, `claude_pro`) a model strings que el Worker entiende:

```python
PROVIDER_MODEL_MAP = {
    "gemini_pro": "gemini-2.5-flash",
    "chatgpt_plus": "gpt-4o-mini",
    "claude_pro": "claude-sonnet-4-20250514",
    "copilot_pro": "gpt-4o",  # via OpenAI key
}
```

### 3. Registrar uso de cuota post-ejecución

Después de que el Worker responde con éxito, registrar el uso en QuotaTracker:

```python
usage = result.get("result", {}).get("usage", {})
total_tokens = usage.get("total_tokens", 0)
quota_tracker.record_usage(decision.model, tokens=total_tokens)
```

### 4. OpsLogger integration

Logear la decisión de modelo en OpsLogger:

```python
ops_logger.log_event("model_selection", {
    "task_id": envelope["task_id"],
    "task_type": envelope.get("task_type"),
    "model_selected": decision.model,
    "reason": decision.reason,
    "requires_approval": decision.requires_approval,
})
```

### 5. Tests

Crear o actualizar tests:
- Test que el Dispatcher inyecta `model` en el envelope para tareas LLM
- Test que QuotaTracker se actualiza post-ejecución
- Test que tareas non-LLM no reciben model injection
- Test fallback cuando modelo preferido en restrict

### 6. Cron de scheduled tasks

Agregar un cron que ejecute `check_and_enqueue` del `TaskScheduler` cada minuto:

- Crear `scripts/vps/scheduled-tasks-cron.sh` que ejecute el scheduler
- Agregar entrada a `scripts/vps/install-cron.sh`: `* * * * *` (cada minuto)

## Entregable

PR a `main` desde `feat/copilot-model-routing` con todos los tests pasando.

## Log

### [github-copilot] 2026-03-04

- Added `PROVIDER_MODEL_MAP` and `map_provider_to_model()` to `dispatcher/model_router.py`
- Updated `dispatcher/service.py` to inject `input_data["model"]` with the mapped model string for LLM tasks (`llm.generate`, `composite.research_report`)
- Created `scripts/vps/scheduled-tasks-cron.sh` — calls `TaskScheduler.check_and_enqueue()`
- Added scheduled-tasks cron entry to `scripts/vps/install-cron.sh` (`* * * * *`)
- Created `tests/test_dispatcher_model_routing.py` — 19 tests covering: PROVIDER_MODEL_MAP, map_provider_to_model, model injection for LLM tasks, no injection for non-LLM tasks, quota post-execution, fallback on restrict, critical override
- All 420 tests pass (1 skipped)
