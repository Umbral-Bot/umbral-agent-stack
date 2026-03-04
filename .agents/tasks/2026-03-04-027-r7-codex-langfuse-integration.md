---
id: "027"
title: "Langfuse Tracing — Instrumentar LLM calls con observabilidad"
assigned_to: codex
branch: feat/codex-langfuse
round: 7
status: assigned
created: 2026-03-04
---

## Objetivo

Integrar Langfuse como sistema de trazabilidad para todas las llamadas LLM del sistema, sin dependencia de LiteLLM. Instrumentación directa en el Worker.

## Contexto

- `worker/tasks/llm.py` — handler multi-LLM (post-tarea 023)
- `infra/docker/docker-compose.langfuse.yml` — scaffold existente para Langfuse
- `docs/24-s6-langfuse-observability.md` — documentación del plan S6
- `scripts/ooda_report.py` — tiene TODO para Langfuse

## Requisitos

### 1. Instalar Langfuse SDK

Agregar `langfuse` al `requirements.txt` del Worker.

### 2. Crear `worker/tracing.py`

Módulo de trazabilidad que envuelve las llamadas LLM:

```python
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("worker.tracing")

_langfuse = None

def _get_langfuse():
    global _langfuse
    if _langfuse is None:
        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
        host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
        if public_key and secret_key:
            from langfuse import Langfuse
            _langfuse = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            logger.info("Langfuse initialized (host=%s)", host)
        else:
            logger.info("Langfuse disabled (no keys)")
    return _langfuse

def trace_llm_call(
    model: str,
    provider: str,
    prompt: str,
    system: str,
    response_text: str,
    usage: Dict[str, int],
    duration_ms: float,
    task_id: Optional[str] = None,
    task_type: Optional[str] = None,
) -> None:
    lf = _get_langfuse()
    if lf is None:
        return
    try:
        trace = lf.trace(
            name=f"llm.generate",
            metadata={
                "task_id": task_id,
                "task_type": task_type,
                "provider": provider,
            },
        )
        trace.generation(
            name=f"{provider}/{model}",
            model=model,
            input=prompt,
            output=response_text,
            usage={
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            },
            metadata={"system_prompt": system, "duration_ms": duration_ms},
        )
    except Exception:
        logger.warning("Langfuse trace failed", exc_info=True)

def flush():
    lf = _get_langfuse()
    if lf:
        lf.flush()
```

### 3. Integrar en `worker/tasks/llm.py`

Después de cada llamada LLM exitosa, llamar `trace_llm_call`:

```python
import time
from worker.tracing import trace_llm_call

# En cada provider:
start = time.monotonic()
result = _call_gemini(...)  # o _call_openai, _call_anthropic
duration_ms = (time.monotonic() - start) * 1000

trace_llm_call(
    model=model, provider=provider,
    prompt=prompt, system=system_prompt,
    response_text=result["text"], usage=result["usage"],
    duration_ms=duration_ms,
    task_id=input_data.get("_task_id"),
    task_type=input_data.get("_task_type"),
)
```

### 4. Graceful degradation

- Si `LANGFUSE_PUBLIC_KEY` no está configurado → tracing deshabilitado, sin errores
- Si Langfuse falla → log warning, no afecta la respuesta del LLM
- Flush al shutdown del Worker (signal handler)

### 5. Actualizar `.env.example`

Agregar:
```
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 6. Tests

- Test tracing disabled cuando no hay keys
- Test trace_llm_call con mock de Langfuse
- Test que llm.generate funciona igual con y sin Langfuse

## Entregable

PR a `main` desde `feat/codex-langfuse` con todos los tests pasando.
