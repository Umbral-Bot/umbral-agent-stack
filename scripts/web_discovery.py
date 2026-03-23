#!/usr/bin/env python3
"""
Discovery web para SIM: Tavily como backend primario.

Google Custom Search quedo como camino legado/experimental porque este stack no
ha mostrado evidencia de uso exitoso y los proyectos nuevos suelen recibir 403.
Azure Bing no esta disponible para cuentas nuevas (Microsoft depreco).

Variables desde .env:
  TAVILY_API_KEY                                       - Tavily Search (primario)
  GOOGLE_CSE_API_KEY_RICK_UMBRAL / GOOGLE_CSE_API_KEY - Google Custom Search (legado)
  GOOGLE_CSE_CX                                        - Custom Search engine ID
  WEB_DISCOVERY_ENABLE_GOOGLE_CSE=1                    - habilita fallback legado a Google

Formato de salida unificado: [{"title", "url", "snippet", "source": "google"|"tavily"}]

Uso:
  python scripts/web_discovery.py "keyword" [--count 5] [--force-tavily] [--allow-google-legacy] [--output json|md]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Cargar variables desde .env si existe env_loader
try:
    from scripts.env_loader import load as _load_env
    _load_env()
except ImportError:
    pass

# ── Constantes de APIs ──────────────────────────────────────────────────────

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
TAVILY_API_URL = "https://api.tavily.com/search"


# ── Tipos ───────────────────────────────────────────────────────────────────

Result = dict[str, str]  # {"title", "url", "snippet", "source"}


# ── Custom Search (Google legacy) ──────────────────────────────────────────

def _search_google(query: str, count: int) -> tuple[list[Result], str | None]:
    """
    Busca con Google Custom Search JSON API.
    Ruta legado/experimental, no operativa por defecto.
    Retorna (resultados, error).
    Si hay 403, error="403:forbidden".
    """
    key = (
        os.environ.get("GOOGLE_CSE_API_KEY_RICK_UMBRAL_2")
        or os.environ.get("GOOGLE_CSE_API_KEY_RICK_UMBRAL")
        or os.environ.get("GOOGLE_CSE_API_KEY")
    )
    cx = os.environ.get("GOOGLE_CSE_CX")

    if not key:
        return [], "skip:no_key_GOOGLE_CSE_API_KEY"
    if not cx:
        return [], "skip:no_key_GOOGLE_CSE_CX"

    qs = urllib.parse.urlencode({"key": key, "cx": cx, "q": query, "num": min(count, 10)})
    req = urllib.request.Request(f"{GOOGLE_CSE_URL}?{qs}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data: dict[str, Any] = json.loads(r.read().decode())
            items = data.get("items") or []
            results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "").replace("\n", " ").strip(),
                    "source": "google",
                }
                for item in items
            ]
            return results, None
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()
        except Exception:
            pass
        if e.code == 403:
            return [], "403:forbidden"
        return [], f"http:{e.code}:{body[:200]}"
    except Exception as e:
        err = str(e)
        if "403" in err:
            return [], "403:forbidden"
        return [], f"error:{err[:200]}"


# ── Tavily Search (backend operativo primario) ─────────────────────────────

def _search_tavily(query: str, count: int) -> tuple[list[Result], str | None]:
    """
    Busca con Tavily Search API (orientada a agentes AI). Free: 1000 creditos/mes.
    Retorna (resultados, error).
    """
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return [], "skip:no_key_TAVILY_API_KEY"

    body = json.dumps({
        "query": query,
        "max_results": min(count, 20),
        "search_depth": "basic",
    }).encode("utf-8")
    req = urllib.request.Request(
        TAVILY_API_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key.strip()}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
            items = data.get("results") or []
            results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": (item.get("content") or "").replace("\n", " ").strip()[:500],
                    "source": "tavily",
                }
                for item in items
            ]
            return results, None
    except urllib.error.HTTPError as e:
        body_str = ""
        try:
            body_str = e.read().decode()
        except Exception:
            pass
        return [], f"http:{e.code}:{body_str[:200]}"
    except Exception as e:
        return [], f"error:{str(e)[:200]}"


# ── Función principal (Tavily primero; Google solo opt-in legado) ──────────

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
    Busca intentando primero Tavily.
    Google Custom Search solo se usa si el caller lo habilita explicitamente
    mediante allow_google_legacy=True o WEB_DISCOVERY_ENABLE_GOOGLE_CSE=1.
    Azure Bing no esta disponible para cuentas nuevas (deprecado por Microsoft).

    Retorna: query, engine_used ("google"|"tavily"|"none"), fallback_reason, results, error.
    """
    google_legacy_enabled = _google_legacy_enabled(allow_google_legacy)

    results, err = _search_tavily(query, count)
    if err is None:
        return {
            "query": query,
            "engine_used": "tavily",
            "fallback_reason": None,
            "results": results,
            "error": None,
        }
    tavily_error = err

    if google_legacy_enabled and not force_tavily:
        results, err = _search_google(query, count)
        if err is None:
            return {
                "query": query,
                "engine_used": "google",
                "fallback_reason": tavily_error,
                "results": results,
                "error": None,
            }
        error = err
    else:
        error = tavily_error

    return {
        "query": query,
        "engine_used": "none",
        "fallback_reason": tavily_error if google_legacy_enabled and not force_tavily else None,
        "results": [],
        "error": error,
    }


# ── Formatos de salida ────────────────────────────────────────────────────────

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


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Discovery web: Tavily como motor primario; Google Custom Search solo legado/opt-in"
    )
    ap.add_argument("query", nargs="?", default="", help="Texto a buscar")
    ap.add_argument("--count", type=int, default=5, help="Numero de resultados (default: 5)")
    ap.add_argument(
        "--force-tavily",
        action="store_true",
        help="Usar solo Tavily y saltar cualquier fallback legado",
    )
    ap.add_argument(
        "--allow-google-legacy",
        action="store_true",
        help="Si Tavily falla, intentar Google Custom Search como fallback legado",
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
