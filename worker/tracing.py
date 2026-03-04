"""
Langfuse tracing helpers for Worker.

Tracing is optional and enabled only when LANGFUSE_PUBLIC_KEY and
LANGFUSE_SECRET_KEY are configured.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("worker.tracing")

_langfuse = None
_langfuse_initialized = False


def _get_langfuse():
    """Return a singleton Langfuse client, or None when disabled."""
    global _langfuse, _langfuse_initialized
    if _langfuse_initialized:
        return _langfuse

    _langfuse_initialized = True
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").strip() or "https://cloud.langfuse.com"

    if not public_key or not secret_key:
        logger.info("Langfuse disabled (no keys)")
        return None

    try:
        from langfuse import Langfuse
    except Exception:
        logger.warning("Langfuse SDK unavailable; tracing disabled", exc_info=True)
        return None

    try:
        _langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        logger.info("Langfuse initialized (host=%s)", host)
    except Exception:
        _langfuse = None
        logger.warning("Langfuse initialization failed; tracing disabled", exc_info=True)
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
    """Send one LLM generation trace to Langfuse."""
    lf = _get_langfuse()
    if lf is None:
        return

    try:
        trace = lf.trace(
            name="llm.generate",
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
                "input": int(usage.get("prompt_tokens", 0)),
                "output": int(usage.get("completion_tokens", 0)),
                "total": int(usage.get("total_tokens", 0)),
            },
            metadata={
                "system_prompt": system,
                "duration_ms": float(duration_ms),
            },
        )
    except Exception:
        logger.warning("Langfuse trace failed", exc_info=True)


def flush() -> None:
    """Flush pending Langfuse events if tracing is enabled."""
    lf = _get_langfuse()
    if lf is None:
        return
    try:
        lf.flush()
    except Exception:
        logger.warning("Langfuse flush failed", exc_info=True)

