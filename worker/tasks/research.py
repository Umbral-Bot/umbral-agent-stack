"""
Tasks: Web research via Tavily API.

- research.web: buscar información en la web sobre un tema.
"""

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any, Dict

logger = logging.getLogger("worker.tasks.research")

TAVILY_API_URL = "https://api.tavily.com/search"


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
        raise RuntimeError("TAVILY_API_KEY not configured")

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
    except urllib.error.HTTPError as e:
        body_str = ""
        try:
            body_str = e.read().decode()[:200]
        except Exception:
            pass
        raise RuntimeError(f"Tavily API error {e.code}: {body_str}")
    except Exception as e:
        raise RuntimeError(f"Tavily search failed: {str(e)[:300]}")
