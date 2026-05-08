"""
verify_kb.py — O16.2/050 gate post-pipeline.

Valida que el alias activo apunte a un index con:
- doc_count >= --min-chunks (default 500).
- Cobertura mínima por jurisdicción (>=1 hit por valor en --jurisdictions).
- Sample queries devuelven resultados.

Exit 0 si todos los gates pasan; 1 si alguno falla.

Uso:
    python scripts/aeco-kb/verify_kb.py --min-chunks 500 --jurisdictions ar,cl,mx,intl
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("aeco-verify-kb")

DEFAULT_SEARCH_SERVICE = "srch-umbral-kb-prod"
DEFAULT_ALIAS = "aeco-kb-es-current"
SEARCH_API_VERSION = "2024-07-01"
SAMPLE_QUERIES = ["IFC", "ISO 19650", "BIM", "construcción"]


def get_active_index(search_service: str, alias: str, token: str) -> str | None:
    import httpx

    url = f"https://{search_service}.search.windows.net/aliases/{alias}?api-version={SEARCH_API_VERSION}"
    with httpx.Client(timeout=30) as client:
        r = client.get(url, headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json().get("indexes", [None])[0]


def get_doc_count(search_service: str, index: str, token: str) -> int:
    import httpx

    url = f"https://{search_service}.search.windows.net/indexes/{index}/docs/$count?api-version={SEARCH_API_VERSION}"
    with httpx.Client(timeout=30) as client:
        r = client.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "text/plain"})
        r.raise_for_status()
        return int(r.text.strip())


def count_with_filter(search_service: str, index: str, token: str, odata_filter: str) -> int:
    import httpx

    url = f"https://{search_service}.search.windows.net/indexes/{index}/docs/search?api-version={SEARCH_API_VERSION}"
    body = {"search": "*", "filter": odata_filter, "count": True, "top": 0}
    with httpx.Client(timeout=30) as client:
        r = client.post(url, headers={"Authorization": f"Bearer {token}",
                                       "Content-Type": "application/json"}, json=body)
        r.raise_for_status()
        return int(r.json().get("@odata.count", 0))


def sample_search(search_service: str, index: str, token: str, query: str) -> int:
    import httpx

    url = f"https://{search_service}.search.windows.net/indexes/{index}/docs/search?api-version={SEARCH_API_VERSION}"
    body = {"search": query, "top": 3}
    with httpx.Client(timeout=30) as client:
        r = client.post(url, headers={"Authorization": f"Bearer {token}",
                                       "Content-Type": "application/json"}, json=body)
        r.raise_for_status()
        return len(r.json().get("value", []))


def run(search_service: str, alias: str, min_chunks: int, jurisdictions: list[str]) -> int:
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    token = credential.get_token("https://search.azure.com/.default").token

    active = get_active_index(search_service, alias, token)
    if not active:
        log.error("Alias %s has no active index.", alias)
        return 1
    log.info("Active index: %s", active)

    failures: list[str] = []

    # Gate 1 — doc count
    count = get_doc_count(search_service, active, token)
    log.info("Doc count: %d (min required: %d)", count, min_chunks)
    if count < min_chunks:
        failures.append(f"doc_count {count} < {min_chunks}")

    # Gate 2 — jurisdiction coverage
    for j in jurisdictions:
        c = count_with_filter(search_service, active, token, f"jurisdiction eq '{j}'")
        log.info("  jurisdiction=%s -> %d chunks", j, c)
        if c < 1:
            failures.append(f"jurisdiction '{j}' has 0 chunks")

    # Gate 3 — sample queries
    for q in SAMPLE_QUERIES:
        n = sample_search(search_service, active, token, q)
        log.info("  query='%s' -> %d hits", q, n)
        if n < 1:
            failures.append(f"query '{q}' returned 0 hits")

    if failures:
        log.error("Gate FAIL: %s", "; ".join(failures))
        return 1

    log.info("All gates PASS for index %s", active)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--search-service", default=os.environ.get("SEARCH_SERVICE", DEFAULT_SEARCH_SERVICE))
    p.add_argument("--alias", default=os.environ.get("ALIAS_NAME", DEFAULT_ALIAS))
    p.add_argument("--min-chunks", type=int, default=int(os.environ.get("MIN_CHUNKS", "500")))
    p.add_argument("--jurisdictions",
                   default=os.environ.get("JURISDICTIONS", "ar,cl,mx,intl"),
                   help="Comma-separated list. Default: ar,cl,mx,intl")
    args = p.parse_args(argv)
    juris = [j.strip() for j in args.jurisdictions.split(",") if j.strip()]
    return run(args.search_service, args.alias, args.min_chunks, juris)


if __name__ == "__main__":
    sys.exit(main())
