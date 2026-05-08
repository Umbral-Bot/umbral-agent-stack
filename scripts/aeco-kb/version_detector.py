"""
version_detector.py — O16.2 sub-task 049

Lee `crudos/aeco/parsed/{source}/*.chunks.jsonl` (output 047), compara contra
manifest del index activo en `crudos/aeco/index/{index_name}/manifest.jsonl`,
y emite diff JSON {added, changed, removed, unchanged}.

Si no hay manifest previo → todo es `added`.

Uso:
    python scripts/aeco-kb/version_detector.py --source-type buildingsmart
    python scripts/aeco-kb/version_detector.py --source-type minvu --output diff.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("aeco-version-detector")

DETECTOR_VERSION = "v1.0.0"
DEFAULT_STORAGE_ACCOUNT = "stumbralagentsprod"
DEFAULT_CONTAINER = "crudos"
DEFAULT_SEARCH_SERVICE = "srch-umbral-kb-prod"
DEFAULT_ALIAS = "aeco-kb-es-current"

VALID_SOURCE_TYPES = {"buildingsmart", "minvu", "iram", "nmx"}


@dataclass
class DocSummary:
    doc_id: str
    chunks_sha256: str
    chunk_count: int


def chunks_sha(chunks: list[dict]) -> str:
    """SHA-256 sobre concat ordenada de chunk text."""
    h = hashlib.sha256()
    for c in sorted(chunks, key=lambda x: x.get("chunk_id", 0)):
        h.update((c.get("content", "") + "\n").encode("utf-8"))
    return h.hexdigest()


def load_parsed(svc, container: str, source_type: str) -> dict[str, DocSummary]:
    """Lee todos los .chunks.jsonl bajo aeco/parsed/{source}/."""
    container_client = svc.get_container_client(container)
    prefix = f"aeco/parsed/{source_type}/"
    out: dict[str, DocSummary] = {}
    for blob in container_client.list_blobs(name_starts_with=prefix):
        if not blob.name.endswith(".chunks.jsonl"):
            continue
        bc = container_client.get_blob_client(blob.name)
        raw = bc.download_blob().readall().decode("utf-8")
        lines = [l for l in raw.splitlines() if l.strip()]
        if not lines:
            continue
        # First line is _meta header (set by 047 pdf_parser)
        chunks = []
        doc_id = None
        for line in lines:
            obj = json.loads(line)
            if obj.get("_meta"):
                doc_id = obj.get("doc_id")
                continue
            chunks.append(obj)
        if not doc_id:
            # Fallback: derive from filename
            doc_id = blob.name.split("/")[-1].replace(".chunks.jsonl", "")
        out[doc_id] = DocSummary(
            doc_id=doc_id,
            chunks_sha256=chunks_sha(chunks),
            chunk_count=len(chunks),
        )
    log.info("Loaded %d parsed docs for source_type=%s", len(out), source_type)
    return out


def get_active_index_name(search_service: str, alias: str, credential) -> str | None:
    """Resuelve alias→index activo via REST."""
    import httpx

    token = credential.get_token("https://search.azure.com/.default").token
    url = f"https://{search_service}.search.windows.net/aliases/{alias}?api-version=2024-07-01"
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(url, headers={"Authorization": f"Bearer {token}"})
            if r.status_code == 404:
                log.info("Alias %s not found — first run", alias)
                return None
            r.raise_for_status()
            return r.json().get("indexes", [None])[0]
    except Exception as exc:
        log.warning("Could not resolve alias %s: %s", alias, exc)
        return None


def load_manifest(svc, container: str, index_name: str, source_type: str) -> dict[str, DocSummary]:
    """Lee manifest del index activo. Schema:
    {"doc_id": ..., "chunks_sha256": ..., "chunk_count": ..., "source_type": ...}
    """
    if not index_name:
        return {}
    path = f"aeco/index/{index_name}/manifest.jsonl"
    bc = svc.get_blob_client(container=container, blob=path)
    if not bc.exists():
        log.info("Manifest %s does not exist — treating all as added", path)
        return {}
    raw = bc.download_blob().readall().decode("utf-8")
    out: dict[str, DocSummary] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("source_type") != source_type:
            continue
        out[obj["doc_id"]] = DocSummary(
            doc_id=obj["doc_id"],
            chunks_sha256=obj["chunks_sha256"],
            chunk_count=obj["chunk_count"],
        )
    log.info("Loaded %d manifest entries for source_type=%s from %s", len(out), source_type, index_name)
    return out


def compute_diff(parsed: dict[str, DocSummary], manifest: dict[str, DocSummary]) -> dict:
    parsed_ids = set(parsed.keys())
    manifest_ids = set(manifest.keys())
    added = sorted(parsed_ids - manifest_ids)
    removed = sorted(manifest_ids - parsed_ids)
    changed = []
    unchanged = []
    for doc_id in sorted(parsed_ids & manifest_ids):
        if parsed[doc_id].chunks_sha256 != manifest[doc_id].chunks_sha256:
            changed.append({
                "doc_id": doc_id,
                "old_sha": manifest[doc_id].chunks_sha256[:16],
                "new_sha": parsed[doc_id].chunks_sha256[:16],
            })
        else:
            unchanged.append(doc_id)
    return {"added": added, "changed": changed, "removed": removed, "unchanged": unchanged}


def run(
    source_type: str,
    storage_account: str,
    container: str,
    search_service: str,
    alias: str,
    output: str,
) -> int:
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    if source_type not in VALID_SOURCE_TYPES:
        log.error("Invalid source_type=%s", source_type)
        return 2

    credential = DefaultAzureCredential()
    svc = BlobServiceClient(
        account_url=f"https://{storage_account}.blob.core.windows.net", credential=credential
    )

    parsed = load_parsed(svc, container, source_type)
    if not parsed:
        log.warning("No parsed docs for %s — nothing to diff", source_type)

    active_index = get_active_index_name(search_service, alias, credential)
    manifest = load_manifest(svc, container, active_index, source_type) if active_index else {}

    diff = compute_diff(parsed, manifest)
    result = {
        "source_type": source_type,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "detector_version": DETECTOR_VERSION,
        "previous_index": active_index,
        **diff,
    }
    log.info(
        "Diff: added=%d changed=%d removed=%d unchanged=%d",
        len(diff["added"]), len(diff["changed"]), len(diff["removed"]), len(diff["unchanged"]),
    )

    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if output == "-" or not output:
        print(payload)
    else:
        with open(output, "w", encoding="utf-8") as f:
            f.write(payload)
        log.info("Wrote diff to %s", output)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-type", default=os.environ.get("SOURCE_TYPE"), choices=sorted(VALID_SOURCE_TYPES))
    p.add_argument("--storage-account", default=os.environ.get("STORAGE_ACCOUNT", DEFAULT_STORAGE_ACCOUNT))
    p.add_argument("--container", default=os.environ.get("CONTAINER", DEFAULT_CONTAINER))
    p.add_argument("--search-service", default=os.environ.get("SEARCH_SERVICE", DEFAULT_SEARCH_SERVICE))
    p.add_argument("--alias", default=os.environ.get("ALIAS_NAME", DEFAULT_ALIAS))
    p.add_argument("--output", default="-", help="Path or '-' for stdout")
    args = p.parse_args(argv)
    if not args.source_type:
        p.error("--source-type required (or env SOURCE_TYPE)")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        source_type=args.source_type,
        storage_account=args.storage_account,
        container=args.container,
        search_service=args.search_service,
        alias=args.alias,
        output=args.output,
    )


if __name__ == "__main__":
    sys.exit(main())
