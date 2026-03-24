#!/usr/bin/env python3
"""
Discovery web para SIM: Tavily como backend primario y Gemini grounded search como fallback real.

Google Custom Search queda solo como camino legado/experimental porque este
stack no ha mostrado evidencia de uso estable y los proyectos nuevos suelen
recibir 403.

Variables desde .env:
  TAVILY_API_KEY                                       - Tavily Search (primario)
  GOOGLE_API_KEY / GOOGLE_API_KEY_NANO                 - Gemini grounded search (fallback real)
  GOOGLE_CSE_API_KEY_RICK_UMBRAL / GOOGLE_CSE_API_KEY - Google Custom Search (legado)
  GOOGLE_CSE_CX                                        - Custom Search engine ID
  WEB_DISCOVERY_ENABLE_GOOGLE_CSE=1                    - habilita fallback legado a Google

Formato de salida unificado: [{"title", "url", "snippet", "source"}]

Uso:
  python scripts/web_discovery.py "keyword" [--count 5] [--force-tavily] [--allow-google-legacy] [--output json|md]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from scripts.env_loader import load as _load_env

    _load_env()
except ImportError:
    pass

from worker.research_backends import (
    GEMINI_SEARCH_PROVIDER,
    GOOGLE_LEGACY_PROVIDER,
    TAVILY_PROVIDER,
    search_gemini_google_search,
    search_google_legacy,
    search_tavily,
)
from worker.task_errors import TaskExecutionError

Result = dict[str, str]


def _with_source(results: list[dict[str, str]], source: str) -> list[Result]:
    return [{**item, "source": source} for item in results]


def _search_tavily(query: str, count: int) -> tuple[list[Result], str | None]:
    try:
        return _with_source(search_tavily(query, count), TAVILY_PROVIDER), None
    except TaskExecutionError as exc:
        return [], f"{exc.error_code}:{exc.error_kind}"


def _search_gemini_grounded(query: str, count: int) -> tuple[list[Result], str | None]:
    try:
        return _with_source(search_gemini_google_search(query, count), GEMINI_SEARCH_PROVIDER), None
    except TaskExecutionError as exc:
        return [], f"{exc.error_code}:{exc.error_kind}"


def _search_google(query: str, count: int) -> tuple[list[Result], str | None]:
    results, error = search_google_legacy(query, count)
    return _with_source(results, GOOGLE_LEGACY_PROVIDER), error


def _google_legacy_enabled(explicit_opt_in: bool) -> bool:
    if explicit_opt_in:
        return True

    raw = os.environ.get("WEB_DISCOVERY_ENABLE_GOOGLE_CSE", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def search(
    query: str,
    count: int = 10,
    force_tavily: bool = False,
    allow_google_legacy: bool = False,
) -> dict[str, Any]:
    """
    Busca intentando primero Tavily y luego Gemini grounded search.
    Google Custom Search solo se usa como tercer intento si el caller lo habilita.

    Retorna: query, engine_used, fallback_reason, results, error.
    """
    google_legacy_enabled = _google_legacy_enabled(allow_google_legacy)

    results, err = _search_tavily(query, count)
    if err is None:
        return {
            "query": query,
            "engine_used": TAVILY_PROVIDER,
            "fallback_reason": None,
            "results": results,
            "error": None,
        }
    tavily_error = err

    if force_tavily:
        return {
            "query": query,
            "engine_used": "none",
            "fallback_reason": None,
            "results": [],
            "error": tavily_error,
        }

    results, err = _search_gemini_grounded(query, count)
    if err is None:
        return {
            "query": query,
            "engine_used": GEMINI_SEARCH_PROVIDER,
            "fallback_reason": tavily_error,
            "results": results,
            "error": None,
        }
    gemini_error = err

    if google_legacy_enabled and not force_tavily:
        results, err = _search_google(query, count)
        if err is None:
            return {
                "query": query,
                "engine_used": GOOGLE_LEGACY_PROVIDER,
                "fallback_reason": f"{tavily_error} -> {gemini_error}",
                "results": results,
                "error": None,
            }
        error = err
    else:
        error = gemini_error

    return {
        "query": query,
        "engine_used": "none",
        "fallback_reason": (
            f"{tavily_error} -> {gemini_error}" if google_legacy_enabled and not force_tavily else tavily_error
        ),
        "results": [],
        "error": error,
    }


def _format_markdown(payload: dict[str, Any]) -> str:
    lines = [f"# Web Discovery - `{payload['query']}`\n"]
    lines.append(f"**Motor:** {payload['engine_used']}")
    if payload.get("fallback_reason"):
        lines.append(f"**Fallback:** {payload['fallback_reason']}")
    if payload.get("error"):
        lines.append(f"\n> Error: {payload['error']}")
        return "\n".join(lines)
    lines.append("")
    for i, r in enumerate(payload["results"], 1):
        lines.append(f"## {i}. [{r['title']}]({r['url']})")
        lines.append(r["snippet"])
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Discovery web: Tavily como motor primario, Gemini grounded search como fallback real y Google CSE solo legado/opt-in"
    )
    ap.add_argument("query", nargs="?", default="", help="Texto a buscar")
    ap.add_argument("--count", type=int, default=5, help="Numero de resultados (default: 5)")
    ap.add_argument(
        "--force-tavily",
        action="store_true",
        help="Usar solo Tavily y saltar cualquier fallback",
    )
    ap.add_argument(
        "--allow-google-legacy",
        action="store_true",
        help="Si Tavily y Gemini grounded fallan, intentar Google Custom Search como fallback legado",
    )
    ap.add_argument(
        "--output",
        choices=["json", "md"],
        default="json",
        help="Formato: json (default) | md",
    )
    args = ap.parse_args()

    if not args.query.strip():
        print(
            'Uso: python scripts/web_discovery.py "keyword" [--count 5] [--force-tavily] [--allow-google-legacy] [--output md]',
            file=sys.stderr,
        )
        sys.exit(1)

    payload = search(
        args.query.strip(),
        count=args.count,
        force_tavily=args.force_tavily,
        allow_google_legacy=args.allow_google_legacy,
    )

    if args.output == "md":
        print(_format_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
