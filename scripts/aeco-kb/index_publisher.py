"""
index_publisher.py — O16.2 sub-task 049

Pipeline post-detector:
1. Resuelve index activo via alias (o crea desde 0 si first run).
2. Crea nuevo index `aeco-kb-es-vYYYYMMDD[-HHMM]` clonando schema del activo
   (o usando bootstrap si first run via 046's create_initial_index).
3. Para cada source_type: lee parsed chunks, embebe via Foundry
   `umbralbim-resource` text-embedding-3-small (cross-RG), sube docs.
4. Valida: doc count >= 95% expected + sample query devuelve >= 3 results.
5. Si gate OK: alias swap atómico. Escribe manifest del nuevo index.
6. Si gate KO: NO swap, exit 1.

Auth: DefaultAzureCredential con UAMI roles
    - Storage Blob Data Contributor (storage)
    - Search Index Data Contributor + Search Service Contributor (AI Search)
    - Cognitive Services OpenAI User (umbralbim-resource para embeddings)

Uso:
    python scripts/aeco-kb/index_publisher.py --source-types buildingsmart minvu
    python scripts/aeco-kb/index_publisher.py --source-types buildingsmart --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("aeco-index-publisher")

PUBLISHER_VERSION = "v1.0.0"
DEFAULT_STORAGE_ACCOUNT = "stumbralagentsprod"
DEFAULT_CONTAINER = "crudos"
DEFAULT_SEARCH_SERVICE = "srch-umbral-kb-prod"
DEFAULT_ALIAS = "aeco-kb-es-current"
DEFAULT_EMBEDDING_ENDPOINT = "https://umbralbim-resource.openai.azure.com"
DEFAULT_EMBEDDING_DEPLOYMENT = "text-embedding-3-small"
DEFAULT_EMBEDDING_API_VERSION = "2024-10-21"
SEARCH_API_VERSION = "2024-07-01"

EMBED_BATCH_SIZE = 16
EMBED_RETRY_BACKOFFS = [2, 8, 32]
GATE_DOC_COUNT_TOLERANCE = 0.95
GATE_SAMPLE_QUERY = "IFC OR norma OR construcción"
GATE_MIN_RESULTS = 3
GATE_MAX_FAILURE_PCT = 0.05

VALID_SOURCE_TYPES = {"buildingsmart", "minvu", "iram", "nmx"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def new_index_name(alias_base: str, existing_names: set[str]) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    candidate = f"{alias_base}-v{today}"
    if candidate not in existing_names:
        return candidate
    hhmm = datetime.now(timezone.utc).strftime("%H%M")
    return f"{candidate}-{hhmm}"


def search_request(method: str, url: str, token: str, body=None, timeout=60):
    import httpx

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=timeout) as client:
        r = client.request(method, url, headers=headers, json=body)
        r.raise_for_status()
        return r.json() if r.content else {}


def get_active_index(search_service: str, alias: str, token: str) -> str | None:
    import httpx

    url = f"https://{search_service}.search.windows.net/aliases/{alias}?api-version={SEARCH_API_VERSION}"
    with httpx.Client(timeout=30) as client:
        r = client.get(url, headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json().get("indexes", [None])[0]


def list_indexes(search_service: str, token: str) -> set[str]:
    url = f"https://{search_service}.search.windows.net/indexes?api-version={SEARCH_API_VERSION}&$select=name"
    data = search_request("GET", url, token)
    return {x["name"] for x in data.get("value", [])}


def get_index_definition(search_service: str, index_name: str, token: str) -> dict:
    url = f"https://{search_service}.search.windows.net/indexes/{index_name}?api-version={SEARCH_API_VERSION}"
    return search_request("GET", url, token)


def create_index(search_service: str, definition: dict, token: str) -> None:
    name = definition["name"]
    url = f"https://{search_service}.search.windows.net/indexes/{name}?api-version={SEARCH_API_VERSION}"
    search_request("PUT", url, token, body=definition)
    log.info("Created index %s", name)


def upload_docs(search_service: str, index_name: str, docs: list[dict], token: str) -> int:
    """Upload via Index batch API. Returns failed count."""
    if not docs:
        return 0
    url = f"https://{search_service}.search.windows.net/indexes/{index_name}/docs/index?api-version={SEARCH_API_VERSION}"
    failed = 0
    BATCH = 500
    for i in range(0, len(docs), BATCH):
        batch = docs[i:i + BATCH]
        body = {"value": [{"@search.action": "upload", **d} for d in batch]}
        result = search_request("POST", url, token, body=body, timeout=120)
        for r in result.get("value", []):
            if not r.get("status"):
                failed += 1
                log.warning("Upload failed key=%s err=%s", r.get("key"), r.get("errorMessage"))
    return failed


def get_doc_count(search_service: str, index_name: str, token: str) -> int:
    url = f"https://{search_service}.search.windows.net/indexes/{index_name}/docs/$count?api-version={SEARCH_API_VERSION}"
    import httpx

    with httpx.Client(timeout=30) as client:
        r = client.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "text/plain"})
        r.raise_for_status()
        return int(r.text.strip())


def sample_query(search_service: str, index_name: str, token: str, query: str, top: int) -> int:
    url = f"https://{search_service}.search.windows.net/indexes/{index_name}/docs/search?api-version={SEARCH_API_VERSION}"
    data = search_request("POST", url, token, body={"search": query, "top": top})
    return len(data.get("value", []))


def alias_swap(search_service: str, alias: str, new_index: str, token: str) -> None:
    url = f"https://{search_service}.search.windows.net/aliases/{alias}?api-version={SEARCH_API_VERSION}"
    body = {"name": alias, "indexes": [new_index]}
    search_request("PUT", url, token, body=body)
    log.info("Alias %s swapped → %s", alias, new_index)


# ---------------------------------------------------------------------------
# Embeddings (Foundry cross-RG)
# ---------------------------------------------------------------------------


def embed_batch(endpoint: str, deployment: str, api_version: str, texts: list[str], token: str) -> list[list[float]]:
    import httpx

    url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"
    body = {"input": texts}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    last_exc: Exception | None = None
    for attempt, backoff in enumerate([0] + EMBED_RETRY_BACKOFFS):
        if backoff:
            log.info("Embed retry %d after %ds", attempt, backoff)
            time.sleep(backoff)
        try:
            with httpx.Client(timeout=60) as client:
                r = client.post(url, json=body, headers=headers)
                if r.status_code == 429 or r.status_code >= 500:
                    last_exc = RuntimeError(f"HTTP {r.status_code}")
                    continue
                r.raise_for_status()
                return [d["embedding"] for d in r.json()["data"]]
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Embedding failed after retries: {last_exc}")


# ---------------------------------------------------------------------------
# Chunks loader
# ---------------------------------------------------------------------------


def load_chunks_for_source(svc, container: str, source_type: str) -> list[dict]:
    container_client = svc.get_container_client(container)
    prefix = f"aeco/parsed/{source_type}/"
    out: list[dict] = []
    for blob in container_client.list_blobs(name_starts_with=prefix):
        if not blob.name.endswith(".chunks.jsonl"):
            continue
        bc = container_client.get_blob_client(blob.name)
        raw = bc.download_blob().readall().decode("utf-8")
        meta = {}
        for line in raw.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("_meta"):
                meta = obj
                continue
            obj["_doc_meta"] = meta
            obj["source_type"] = source_type
            out.append(obj)
    log.info("Loaded %d chunks for source_type=%s", len(out), source_type)
    return out


def chunk_to_search_doc(chunk: dict, kb_version: str) -> dict:
    meta = chunk.get("_doc_meta", {})
    doc_id = meta.get("doc_id") or chunk.get("parent_doc_id", "unknown")
    chunk_id = chunk.get("chunk_id", 0)
    return {
        "id": f"{doc_id}__{chunk_id}",
        "content": chunk.get("content", ""),
        "content_vector": chunk.get("content_vector"),
        "source_url": meta.get("source_url", ""),
        "source_type": chunk.get("source_type"),
        "jurisdiction": meta.get("jurisdiction", ""),
        "doc_type": meta.get("doc_type", ""),
        "version": meta.get("version", ""),
        "lang": meta.get("default_lang", "es"),
        "valid_from": meta.get("valid_from"),
        "valid_to": meta.get("valid_to"),
        "chunk_id": chunk_id,
        "parent_doc_id": doc_id,
        "kb_version": kb_version,
    }


# ---------------------------------------------------------------------------
# Manifest writer
# ---------------------------------------------------------------------------


def write_index_manifest(svc, container: str, index_name: str, summaries: list[dict]) -> None:
    """Manifest del index recién publicado, leído por version_detector en próximo run."""
    path = f"aeco/index/{index_name}/manifest.jsonl"
    bc = svc.get_blob_client(container=container, blob=path)
    body = "\n".join(json.dumps(s, ensure_ascii=False) for s in summaries) + "\n"
    bc.upload_blob(body.encode("utf-8"), overwrite=True)
    log.info("Wrote manifest %s (%d entries)", path, len(summaries))


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(
    source_types: list[str],
    storage_account: str,
    container: str,
    search_service: str,
    alias: str,
    embedding_endpoint: str,
    embedding_deployment: str,
    embedding_api_version: str,
    dry_run: bool,
) -> int:
    import hashlib

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    invalid = [s for s in source_types if s not in VALID_SOURCE_TYPES]
    if invalid:
        log.error("Invalid source_types: %s", invalid)
        return 2

    credential = DefaultAzureCredential()
    svc = BlobServiceClient(
        account_url=f"https://{storage_account}.blob.core.windows.net", credential=credential
    )

    search_token = credential.get_token("https://search.azure.com/.default").token
    cog_token = credential.get_token("https://cognitiveservices.azure.com/.default").token

    # 1. Resolve active index + clone schema
    active_index = get_active_index(search_service, alias, search_token)
    if not active_index:
        log.error("Alias %s has no active index. Run 046 (create_initial_index.py) first.", alias)
        return 1
    log.info("Active index: %s", active_index)

    existing = list_indexes(search_service, search_token)
    new_index = new_index_name("aeco-kb-es", existing)
    log.info("New index name: %s", new_index)

    if dry_run:
        for st in source_types:
            chunks = load_chunks_for_source(svc, container, st)
            log.info("[dry-run] source=%s chunks=%d", st, len(chunks))
        log.info("[dry-run] would create %s and swap alias %s", new_index, alias)
        return 0

    definition = get_index_definition(search_service, active_index, search_token)
    definition["name"] = new_index
    for k in ("@odata.etag", "@odata.context"):
        definition.pop(k, None)
    create_index(search_service, definition, search_token)

    # 2. For each source: load + embed + upload
    total_uploaded = 0
    total_failed = 0
    manifest_entries: list[dict] = []
    docs_for_upload: list[dict] = []

    for st in source_types:
        chunks = load_chunks_for_source(svc, container, st)
        if not chunks:
            log.warning("No chunks for source=%s — skipping", st)
            continue

        # Embed in batches if chunk lacks content_vector
        texts_to_embed_idx: list[int] = []
        for i, c in enumerate(chunks):
            if not c.get("content_vector"):
                texts_to_embed_idx.append(i)

        log.info("source=%s embedding %d/%d chunks", st, len(texts_to_embed_idx), len(chunks))
        for i in range(0, len(texts_to_embed_idx), EMBED_BATCH_SIZE):
            idx_batch = texts_to_embed_idx[i:i + EMBED_BATCH_SIZE]
            texts = [chunks[j].get("content", "") for j in idx_batch]
            try:
                vectors = embed_batch(embedding_endpoint, embedding_deployment,
                                      embedding_api_version, texts, cog_token)
            except Exception as exc:
                log.error("Embedding batch failed: %s", exc)
                total_failed += len(idx_batch)
                continue
            for j, v in zip(idx_batch, vectors):
                chunks[j]["content_vector"] = v

        # Build manifest entries (per-doc summary)
        per_doc: dict[str, list[dict]] = {}
        for c in chunks:
            if not c.get("content_vector"):
                continue
            doc_id = (c.get("_doc_meta") or {}).get("doc_id") or c.get("parent_doc_id", "unknown")
            per_doc.setdefault(doc_id, []).append(c)
        for doc_id, doc_chunks in per_doc.items():
            h = hashlib.sha256()
            for c in sorted(doc_chunks, key=lambda x: x.get("chunk_id", 0)):
                h.update((c.get("content", "") + "\n").encode("utf-8"))
            manifest_entries.append({
                "doc_id": doc_id,
                "source_type": st,
                "chunks_sha256": h.hexdigest(),
                "chunk_count": len(doc_chunks),
            })

        # Build search docs
        for c in chunks:
            if not c.get("content_vector"):
                continue
            docs_for_upload.append(chunk_to_search_doc(c, new_index))

    log.info("Uploading %d docs to %s", len(docs_for_upload), new_index)
    failed_upload = upload_docs(search_service, new_index, docs_for_upload, search_token)
    total_uploaded = len(docs_for_upload) - failed_upload
    total_failed += failed_upload

    # 3. Validation gate
    expected = len(docs_for_upload)
    failure_pct = total_failed / max(expected, 1)
    log.info("Validation: uploaded=%d failed=%d failure_pct=%.2f%%",
             total_uploaded, total_failed, failure_pct * 100)

    if failure_pct > GATE_MAX_FAILURE_PCT:
        log.error("Gate FAIL: failure_pct %.2f%% > %.2f%%",
                  failure_pct * 100, GATE_MAX_FAILURE_PCT * 100)
        return 1

    # Wait for indexing eventual consistency
    time.sleep(5)
    actual_count = get_doc_count(search_service, new_index, search_token)
    if actual_count < expected * GATE_DOC_COUNT_TOLERANCE:
        log.error("Gate FAIL: doc_count %d < expected %d * %.2f",
                  actual_count, expected, GATE_DOC_COUNT_TOLERANCE)
        return 1

    sample_count = sample_query(search_service, new_index, search_token,
                                GATE_SAMPLE_QUERY, GATE_MIN_RESULTS)
    if sample_count < GATE_MIN_RESULTS:
        log.error("Gate FAIL: sample query returned %d < %d", sample_count, GATE_MIN_RESULTS)
        return 1

    log.info("Gate PASS — proceeding with alias swap")

    # 4. Atomic swap + manifest
    alias_swap(search_service, alias, new_index, search_token)
    write_index_manifest(svc, container, new_index, manifest_entries)
    log.info("Publish complete. Alias %s → %s (docs=%d)", alias, new_index, actual_count)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-types", nargs="+", required=False,
                   default=os.environ.get("SOURCE_TYPES", "").split() or None,
                   choices=sorted(VALID_SOURCE_TYPES))
    p.add_argument("--storage-account", default=os.environ.get("STORAGE_ACCOUNT", DEFAULT_STORAGE_ACCOUNT))
    p.add_argument("--container", default=os.environ.get("CONTAINER", DEFAULT_CONTAINER))
    p.add_argument("--search-service", default=os.environ.get("SEARCH_SERVICE", DEFAULT_SEARCH_SERVICE))
    p.add_argument("--alias", default=os.environ.get("ALIAS_NAME", DEFAULT_ALIAS))
    p.add_argument("--embedding-endpoint",
                   default=os.environ.get("EMBEDDING_ENDPOINT", DEFAULT_EMBEDDING_ENDPOINT))
    p.add_argument("--embedding-deployment",
                   default=os.environ.get("EMBEDDING_DEPLOYMENT", DEFAULT_EMBEDDING_DEPLOYMENT))
    p.add_argument("--embedding-api-version",
                   default=os.environ.get("EMBEDDING_API_VERSION", DEFAULT_EMBEDDING_API_VERSION))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if not args.source_types:
        p.error("--source-types required (or env SOURCE_TYPES space-separated)")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        source_types=args.source_types,
        storage_account=args.storage_account,
        container=args.container,
        search_service=args.search_service,
        alias=args.alias,
        embedding_endpoint=args.embedding_endpoint,
        embedding_deployment=args.embedding_deployment,
        embedding_api_version=args.embedding_api_version,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
