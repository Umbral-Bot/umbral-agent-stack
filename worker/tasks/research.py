"""
Tasks: web research with provider fallback.

- research.web: buscar informacion en la web sobre un tema.
"""

from __future__ import annotations

from typing import Any, Dict

from worker.research_backends import (
    GEMINI_SEARCH_PROVIDER,
    TAVILY_PROVIDER,
    search_gemini_google_search,
    search_tavily,
)
from worker.task_errors import TaskExecutionError


def _should_try_gemini_fallback(error: TaskExecutionError) -> bool:
    return error.provider == TAVILY_PROVIDER


def handle_research_web(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Busca en la web con Tavily como primario y Gemini grounded search como fallback real.

    Input:
        query (str, required): termino o pregunta de busqueda.
        count (int, optional): numero de resultados (default: 5, max: 20).
        search_depth (str, optional): "basic" o "advanced" (default: "basic").

    Returns:
        {"results": [...], "count": N, "engine": "...", "fallback_reason": "...?"}
    """
    query = str(input_data.get("query", "")).strip()
    if not query:
        raise ValueError("'query' is required and cannot be empty")

    count = min(int(input_data.get("count", 5)), 20)
    search_depth = str(input_data.get("search_depth", "basic") or "basic")

    try:
        results = search_tavily(query, count, search_depth=search_depth)
        return {"results": results, "count": len(results), "engine": TAVILY_PROVIDER}
    except TaskExecutionError as tavily_error:
        if not _should_try_gemini_fallback(tavily_error):
            raise

        try:
            results = search_gemini_google_search(query, count)
            return {
                "results": results,
                "count": len(results),
                "engine": GEMINI_SEARCH_PROVIDER,
                "fallback_reason": tavily_error.error_code,
            }
        except TaskExecutionError:
            raise tavily_error
