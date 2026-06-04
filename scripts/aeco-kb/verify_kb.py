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
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("aeco-verify-kb")

DEFAULT_SEARCH_SERVICE = "srch-umbral-kb-prod"
DEFAULT_ALIAS = "aeco-kb-es-current"
SEARCH_API_VERSION = "2024-07-01"
ALIAS_API_CANDIDATES = (
    ("2026-04-01", "odata"),
    ("2025-11-01-preview", "odata"),
    ("2023-07-01-Preview", "classic"),
)
DEFAULT_SAMPLE_QUERIES = ["IFC", "ISO 19650", "BIM"]


def alias_url(search_service: str, alias: str, api_version: str, style: str) -> str:
    endpoint = f"https://{search_service}.search.windows.net"
    encoded = quote(alias, safe="")
    if style == "odata":
        return f"{endpoint}/aliases('{encoded}')?api-version={api_version}"
    return f"{endpoint}/aliases/{encoded}?api-version={api_version}"


def csv_list(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def get_active_index(search_service: str, alias: str, token: str) -> str | None:
    import httpx

    diagnostics: list[str] = []
    with httpx.Client(timeout=30) as client:
        for api_version, style in ALIAS_API_CANDIDATES:
            url = alias_url(search_service, alias, api_version, style)
            r = client.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
            if r.status_code == 200:
                indexes = r.json().get("indexes", [])
                return indexes[0] if indexes else None
            if r.status_code in {400, 404}:
                body = r.text.replace("\n", " ")[:300]
                diagnostics.append(f"{api_version}/{style} -> HTTP {r.status_code}: {body}")
                continue
            r.raise_for_status()
    log.error("Alias %s could not be resolved. Attempts: %s", alias, "; ".join(diagnostics))
    return None


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


def run(
    search_service: str,
    alias: str,
    min_chunks: int,
    jurisdictions: list[str],
    sample_queries: list[str],
) -> int:
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
    for q in sample_queries:
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
    p.add_argument("--sample-queries",
                   default=os.environ.get("SAMPLE_QUERIES", ",".join(DEFAULT_SAMPLE_QUERIES)),
                   help="Comma-separated smoke queries. Default: IFC,ISO 19650,BIM")
    args = p.parse_args(argv)
    juris = csv_list(args.jurisdictions)
    sample_queries = csv_list(args.sample_queries)
    if not sample_queries:
        p.error("--sample-queries must include at least one query")
    return run(args.search_service, args.alias, args.min_chunks, juris, sample_queries)


if __name__ == "__main__":
    sys.exit(main())
