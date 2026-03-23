"""
Tasks: Web research via Tavily API.

- research.web: buscar información en la web sobre un tema.
"""

import json
import logging
import os
import socket
import urllib.request
import urllib.error
from typing import Any, Dict

from worker.task_errors import TaskExecutionError

logger = logging.getLogger("worker.tasks.research")

TAVILY_API_URL = "https://api.tavily.com/search"
_RESEARCH_PROVIDER = "tavily"
_QUOTA_MARKERS = (
    "usage limit",
    "rate limit",
    "quota",
    "credits",
    "too many requests",
)


def _safe_http_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")[:400]
    except Exception:
        return ""


def _raise_tavily_http_error(exc: urllib.error.HTTPError) -> None:
    body_str = _safe_http_error_body(exc)
    body_lower = body_str.lower()

    if exc.code in {429, 432} or any(marker in body_lower for marker in _QUOTA_MARKERS):
        raise TaskExecutionError(
            "research.web unavailable: Tavily plan/quota exceeded",
            status_code=503,
            error_code="research_provider_quota_exceeded",
            error_kind="quota",
            retryable=False,
            provider=_RESEARCH_PROVIDER,
            upstream_status=exc.code,
        ) from exc

    if exc.code in {401, 403}:
        raise TaskExecutionError(
            "research.web unavailable: Tavily authentication or permissions failed",
            status_code=503,
            error_code="research_provider_auth_failed",
            error_kind="auth",
            retryable=False,
            provider=_RESEARCH_PROVIDER,
            upstream_status=exc.code,
        ) from exc

    if 500 <= exc.code <= 599:
        raise TaskExecutionError(
            f"research.web unavailable: Tavily upstream error {exc.code}",
            status_code=502,
            error_code="research_provider_upstream_error",
            error_kind="upstream",
            retryable=True,
            provider=_RESEARCH_PROVIDER,
            upstream_status=exc.code,
        ) from exc

    raise TaskExecutionError(
        f"research.web unavailable: Tavily HTTP error {exc.code}",
        status_code=502,
        error_code="research_provider_http_error",
        error_kind="upstream",
        retryable=False,
        provider=_RESEARCH_PROVIDER,
        upstream_status=exc.code,
    ) from exc


def handle_research_web(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Busca en la web usando Tavily Search API.

    Input:
        query (str, required): Término o pregunta de búsqueda.
        count (int, optional): Número de resultados (default: 5, max: 20).
        search_depth (str, optional): "basic" o "advanced" (default: "basic").

    Returns:
        {"results": [...], "count": N, "engine": "tavily"}
    """
    query = input_data.get("query", "").strip()
    if not query:
        raise ValueError("'query' is required and cannot be empty")

    count = min(int(input_data.get("count", 5)), 20)
    search_depth = input_data.get("search_depth", "basic")

    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        raise TaskExecutionError(
            "research.web unavailable: TAVILY_API_KEY not configured",
            status_code=503,
            error_code="research_provider_not_configured",
            error_kind="configuration",
            retryable=False,
            provider=_RESEARCH_PROVIDER,
        )

    body = json.dumps({
        "query": query,
        "max_results": count,
        "search_depth": search_depth,
    }).encode("utf-8")

    req = urllib.request.Request(
        TAVILY_API_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            items = data.get("results") or []
            results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": (item.get("content") or "").replace("\n", " ").strip()[:500],
                }
                for item in items
            ]
            return {"results": results, "count": len(results), "engine": "tavily"}
    except urllib.error.HTTPError as exc:
        _raise_tavily_http_error(exc)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, socket.timeout):
            raise TaskExecutionError(
                "research.web unavailable: Tavily request timed out",
                status_code=504,
                error_code="research_provider_timeout",
                error_kind="timeout",
                retryable=True,
                provider=_RESEARCH_PROVIDER,
            ) from exc
        raise TaskExecutionError(
            f"research.web unavailable: Tavily connection failed ({exc.reason})",
            status_code=504,
            error_code="research_provider_connection_failed",
            error_kind="network",
            retryable=True,
            provider=_RESEARCH_PROVIDER,
        ) from exc
    except TimeoutError as exc:
        raise TaskExecutionError(
            "research.web unavailable: Tavily request timed out",
            status_code=504,
            error_code="research_provider_timeout",
            error_kind="timeout",
            retryable=True,
            provider=_RESEARCH_PROVIDER,
        ) from exc
    except json.JSONDecodeError as exc:
        raise TaskExecutionError(
            "research.web unavailable: Tavily returned invalid JSON",
            status_code=502,
            error_code="research_provider_invalid_response",
            error_kind="upstream",
            retryable=False,
            provider=_RESEARCH_PROVIDER,
        ) from exc
    except TaskExecutionError:
        raise
    except Exception as exc:
        raise TaskExecutionError(
            f"research.web failed unexpectedly: {str(exc)[:200]}",
            status_code=500,
            error_code="research_provider_unexpected_error",
            error_kind="execution",
            retryable=False,
            provider=_RESEARCH_PROVIDER,
        ) from exc
