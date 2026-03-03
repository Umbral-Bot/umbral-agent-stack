#!/usr/bin/env python3
"""
Busqueda web via Azure Bing Web Search API (Cognitive Services).
Uso: AZURE_BING_SEARCH_KEY en .env o entorno; luego:
  python scripts/bing_search.py "keyword"
  python scripts/bing_search.py "keyword" --count 5
Devuelve JSON con webPages.value para uso en SIM / discovery.
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

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from scripts.env_loader import load as load_env
    load_env()
except ImportError:
    pass

BING_API_URL = "https://api.bing.microsoft.com/v7.0/search"


def search(query: str, count: int = 10) -> dict:
    key = os.environ.get("AZURE_BING_SEARCH_KEY") or os.environ.get("BING_SEARCH_KEY")
    if not key:
        return {"error": "AZURE_BING_SEARCH_KEY no definida en .env o entorno"}
    qs = urllib.parse.urlencode({"q": query, "count": min(count, 50)})
    req = urllib.request.Request(
        f"{BING_API_URL}?{qs}",
        headers={"Ocp-Apim-Subscription-Key": key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {
            "error": f"HTTP {e.code}",
            "body": e.read().decode()[:500] if e.fp else "",
        }
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Azure Bing Web Search para SIM/discovery")
    ap.add_argument("query", nargs="?", default="", help="Texto a buscar")
    ap.add_argument("--count", type=int, default=5, help="Numero de resultados (max 50)")
    args = ap.parse_args()
    if not args.query.strip():
        print("Uso: python scripts/bing_search.py \"keyword\" [--count 5]", file=sys.stderr)
        sys.exit(1)
    out = search(args.query.strip(), count=args.count)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
