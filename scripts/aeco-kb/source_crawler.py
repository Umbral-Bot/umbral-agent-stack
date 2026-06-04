"""
source_crawler.py — O16.2 sub-task 048

Crawler parametrizado por --source-type que descarga documentos desde seeds
estáticos (`scripts/aeco-kb/seeds/{source_type}.yaml`), aplica rate-limit +
dedupe SHA-256, y persiste en `crudos/aeco/raw/{source_type}/{doc_id}.{ext}`.

Manifest append-only en `crudos/aeco/raw/_manifest/{source_type}.jsonl`.

Auth: DefaultAzureCredential
    - Local: az login (Storage Blob Data Contributor)
    - Container Apps Job: UAMI uami-umbral-agents-prod (RBAC ya en O16.1)

Uso:
    python scripts/aeco-kb/source_crawler.py --source-type buildingsmart --max-docs 30
    python scripts/aeco-kb/source_crawler.py --source-type buildingsmart --preflight-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("aeco-source-crawler")

# ---------------------------------------------------------------------------
# Constants (task 048 §D13-D15)
# ---------------------------------------------------------------------------

CRAWLER_VERSION = "v1.0.0"
USER_AGENT = "umbral-aeco-crawler/0.1 (+contacto@umbralbim.cl)"
RATE_LIMIT_SECONDS = 1.0
HTTP_TIMEOUT_SECONDS = 60
RETRY_BACKOFFS = [1, 4, 16]

DEFAULT_STORAGE_ACCOUNT = "stumbralagentsprod"
DEFAULT_CONTAINER = "crudos"
SEEDS_DIR = Path(__file__).parent / "seeds"

VALID_SOURCE_TYPES = {"buildingsmart", "minvu", "iram", "nmx"}
VALID_JURISDICTIONS = {"intl", "cl", "ar", "mx"}
CONTENT_TYPE_EXTENSIONS = {
    "application/pdf": "pdf",
    "text/html": "html",
    "text/plain": "txt",
}
URL_EXTENSION_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".html": "text/html",
    ".htm": "text/html",
    ".exp": "text/plain",
    ".txt": "text/plain",
    ".md": "text/plain",
}


@dataclass
class Seed:
    url: str
    doc_id: str
    version: str | None
    valid_from: str | None
    expected_content_type: str | None
    source_type: str
    jurisdiction: str
    doc_type: str
    default_lang: str


@dataclass
class SeedPreflight:
    seed: Seed
    ok: bool
    status_code: int | None
    content_type: str | None
    error: str | None = None


# ---------------------------------------------------------------------------
# Seeds loader
# ---------------------------------------------------------------------------


def load_seeds(source_type: str) -> list[Seed]:
    import yaml

    path = SEEDS_DIR / f"{source_type}.yaml"
    if not path.exists():
        log.error("No seeds file for source_type=%s (expected %s)", source_type, path)
        sys.exit(2)

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not raw or not raw.get("seeds"):
        log.warning("Seeds file %s exists but has no seeds (placeholder).", path)
        return []

    base = {
        "source_type": raw["source_type"],
        "jurisdiction": raw["jurisdiction"],
        "doc_type": raw["doc_type"],
        "default_lang": raw.get("default_lang", "es"),
    }
    seeds: list[Seed] = []
    for entry in raw["seeds"]:
        seeds.append(
            Seed(
                url=entry["url"],
                doc_id=entry["doc_id"],
                version=entry.get("version"),
                valid_from=entry.get("valid_from"),
                expected_content_type=entry.get("content_type") or entry.get("expected_content_type"),
                **base,
            )
        )
    log.info("Loaded %d seeds from %s", len(seeds), path)
    return seeds


# ---------------------------------------------------------------------------
# Robots.txt (best-effort)
# ---------------------------------------------------------------------------


_robots_cache: dict[str, RobotFileParser] = {}


def can_fetch(url: str) -> bool:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robots_cache:
        rp = RobotFileParser()
        rp.set_url(f"{base}/robots.txt")
        try:
            rp.read()
        except Exception as exc:  # pragma: no cover — network defensive
            log.warning("robots.txt fetch failed for %s: %s — assuming allowed", base, exc)
            rp = None  # type: ignore
        _robots_cache[base] = rp  # type: ignore
    rp = _robots_cache[base]
    if rp is None:
        return True
    return rp.can_fetch(USER_AGENT, url)


# ---------------------------------------------------------------------------
# HTTP preflight/download with retry
# ---------------------------------------------------------------------------


def normalize_content_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


def infer_content_type_from_url(url: str) -> str | None:
    suffix = Path(urlparse(url).path).suffix.lower()
    return URL_EXTENSION_CONTENT_TYPES.get(suffix)


def effective_content_type(header_value: str | None, url: str) -> str:
    ct = normalize_content_type(header_value)
    if not ct or ct == "application/octet-stream":
        return infer_content_type_from_url(url) or ct
    return ct


def supported_extension(content_type: str | None, url: str) -> str | None:
    ct = normalize_content_type(content_type) or infer_content_type_from_url(url)
    return CONTENT_TYPE_EXTENSIONS.get(ct or "")


def preflight_seed_url(client, seed: Seed) -> SeedPreflight:
    import httpx

    try:
        response = client.head(seed.url)
        content_type = effective_content_type(response.headers.get("content-type"), seed.url)
        if response.status_code in {403, 405} or (response.status_code < 400 and not content_type):
            response = client.get(seed.url, headers={"Range": "bytes=0-0"})
            content_type = effective_content_type(response.headers.get("content-type"), seed.url)
        status_code = response.status_code
        if status_code >= 400:
            return SeedPreflight(
                seed=seed,
                ok=False,
                status_code=status_code,
                content_type=content_type or None,
                error=f"HTTP {status_code}",
            )
        expected = normalize_content_type(seed.expected_content_type)
        if expected and content_type != expected:
            return SeedPreflight(
                seed=seed,
                ok=False,
                status_code=status_code,
                content_type=content_type or None,
                error=f"content_type {content_type or 'unknown'} != expected {expected}",
            )
        if not supported_extension(content_type, seed.url):
            return SeedPreflight(
                seed=seed,
                ok=False,
                status_code=status_code,
                content_type=content_type or None,
                error=f"unsupported content_type {content_type or 'unknown'}",
            )
        return SeedPreflight(
            seed=seed,
            ok=True,
            status_code=status_code,
            content_type=content_type or None,
        )
    except httpx.HTTPError as exc:
        return SeedPreflight(
            seed=seed,
            ok=False,
            status_code=None,
            content_type=None,
            error=f"{type(exc).__name__}: {exc}",
        )


def preflight_seeds(seeds: list[Seed]) -> list[SeedPreflight]:
    import httpx

    results: list[SeedPreflight] = []
    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(HTTP_TIMEOUT_SECONDS),
        follow_redirects=True,
    ) as client:
        for seed in seeds:
            results.append(preflight_seed_url(client, seed))
    return results


def log_preflight_results(results: list[SeedPreflight]) -> None:
    for result in results:
        status = "OK" if result.ok else "FAIL"
        detail = result.error or result.content_type or ""
        log.info(
            "preflight %s status=%s content_type=%s doc_id=%s url=%s %s",
            status,
            result.status_code,
            result.content_type or "unknown",
            result.seed.doc_id,
            result.seed.url,
            detail,
        )


def download(url: str) -> tuple[bytes, str]:
    """Devuelve (content_bytes, content_type). Retry 3x con backoff."""
    import httpx

    last_exc: Exception | None = None
    for attempt, backoff in enumerate([0] + RETRY_BACKOFFS):
        if backoff:
            log.info("Retry %d after %ds for %s", attempt, backoff, url)
            time.sleep(backoff)
        try:
            with httpx.Client(
                headers={"User-Agent": USER_AGENT},
                timeout=httpx.Timeout(HTTP_TIMEOUT_SECONDS),
                follow_redirects=True,
            ) as client:
                r = client.get(url)
                if r.status_code == 429 or r.status_code >= 500:
                    last_exc = RuntimeError(f"HTTP {r.status_code}")
                    continue
                r.raise_for_status()
                ct = effective_content_type(r.headers.get("content-type"), url)
                return r.content, ct
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Download failed after retries: {url}") from last_exc


# ---------------------------------------------------------------------------
# Storage I/O
# ---------------------------------------------------------------------------


def get_blob_service(account: str, credential):
    from azure.storage.blob import BlobServiceClient

    return BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net", credential=credential
    )


def existing_sha256(blob_client) -> str | None:
    try:
        if not blob_client.exists():
            return None
        props = blob_client.get_blob_properties()
        return (props.metadata or {}).get("sha256")
    except Exception as exc:
        log.warning("Could not fetch existing blob metadata: %s", exc)
        return None


def upload_blob(blob_client, content: bytes, sha256_hex: str, content_type: str) -> None:
    from azure.storage.blob import ContentSettings

    blob_client.upload_blob(
        content,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
        metadata={"sha256": sha256_hex, "crawler_version": CRAWLER_VERSION},
    )


def append_manifest(blob_client, line: dict) -> None:
    """Manifest JSONL append-only — usa AppendBlob."""
    from azure.storage.blob import BlobType

    encoded = (json.dumps(line, ensure_ascii=False) + "\n").encode("utf-8")
    if not blob_client.exists():
        blob_client.create_append_blob()
    blob_client.append_block(encoded)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run(
    source_type: str,
    max_docs: int,
    storage_account: str,
    container: str,
    dry_run: bool,
    preflight_only: bool = False,
    skip_preflight: bool = False,
) -> int:
    from azure.identity import DefaultAzureCredential

    if source_type not in VALID_SOURCE_TYPES:
        log.error("Invalid source_type=%s. Must be one of %s", source_type, VALID_SOURCE_TYPES)
        return 2

    seeds = load_seeds(source_type)
    if not seeds:
        log.warning("No seeds — nothing to do (placeholder file).")
        return 0
    seeds = seeds[:max_docs]

    if not skip_preflight:
        preflight = preflight_seeds(seeds)
        log_preflight_results(preflight)
        failures = [result for result in preflight if not result.ok]
        if failures:
            log.error("Seed preflight failed for %d/%d seeds; aborting before Azure I/O.", len(failures), len(seeds))
            return 1
        if preflight_only:
            log.info("Preflight passed for %d seeds.", len(seeds))
            return 0
    elif preflight_only:
        log.warning("--preflight-only with --skip-preflight has no work.")
        return 0

    credential = None if dry_run else DefaultAzureCredential()
    svc = None if dry_run else get_blob_service(storage_account, credential)

    manifest_path = f"aeco/raw/_manifest/{source_type}.jsonl"
    manifest_client = None if dry_run else svc.get_blob_client(container=container, blob=manifest_path)

    counts = {"new": 0, "skipped": 0, "updated": 0, "failed": 0, "robots_blocked": 0, "unsupported": 0}

    for i, seed in enumerate(seeds):
        if i > 0:
            time.sleep(RATE_LIMIT_SECONDS)

        if not can_fetch(seed.url):
            log.warning("robots.txt disallows %s", seed.url)
            counts["robots_blocked"] += 1
            continue

        log.info("[%d/%d] Downloading %s", i + 1, len(seeds), seed.url)
        try:
            content, content_type = download(seed.url)
        except Exception as exc:
            log.error("Download failed for %s: %s", seed.url, exc)
            counts["failed"] += 1
            continue

        ext = supported_extension(content_type, seed.url)
        if not ext:
            log.warning("Unsupported content-type=%s for %s", content_type, seed.url)
            counts["unsupported"] += 1
            continue

        sha256_hex = hashlib.sha256(content).hexdigest()
        blob_path = f"aeco/raw/{source_type}/{seed.doc_id}.{ext}"

        if dry_run:
            log.info("[dry-run] %s -> %s/%s (%d bytes, sha=%s)",
                     seed.url, container, blob_path, len(content), sha256_hex[:12])
            counts["new"] += 1
            continue

        blob_client = svc.get_blob_client(container=container, blob=blob_path)
        prev_sha = existing_sha256(blob_client)
        if prev_sha == sha256_hex:
            log.info("Skip %s (unchanged sha256)", blob_path)
            counts["skipped"] += 1
            continue

        status = "updated" if prev_sha else "new"
        upload_blob(blob_client, content, sha256_hex, content_type)
        log.info("%s %s (%d bytes, sha=%s)", status.capitalize(), blob_path, len(content), sha256_hex[:12])
        counts[status] += 1

        append_manifest(manifest_client, {
            "doc_id": seed.doc_id,
            "sha256": sha256_hex,
            "source_url": seed.url,
            "source_type": seed.source_type,
            "jurisdiction": seed.jurisdiction,
            "doc_type": seed.doc_type,
            "content_type": content_type,
            "size_bytes": len(content),
            "version": seed.version,
            "valid_from": seed.valid_from,
            "default_lang": seed.default_lang,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
        })

    log.info("Crawler done. Counts: %s", counts)
    return 0 if counts["failed"] == 0 and counts["unsupported"] == 0 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-type", default=os.environ.get("SOURCE_TYPE"), choices=sorted(VALID_SOURCE_TYPES))
    p.add_argument("--max-docs", type=int, default=int(os.environ.get("MAX_DOCS", "100")))
    p.add_argument("--storage-account", default=os.environ.get("STORAGE_ACCOUNT", DEFAULT_STORAGE_ACCOUNT))
    p.add_argument("--container", default=os.environ.get("CONTAINER", DEFAULT_CONTAINER))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--preflight-only", action="store_true", help="Validate seed URLs and exit before Azure I/O.")
    p.add_argument("--skip-preflight", action="store_true", help="Bypass seed URL preflight.")
    args = p.parse_args(argv)
    if not args.source_type:
        p.error("--source-type required (or env SOURCE_TYPE)")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        source_type=args.source_type,
        max_docs=args.max_docs,
        storage_account=args.storage_account,
        container=args.container,
        dry_run=args.dry_run,
        preflight_only=args.preflight_only,
        skip_preflight=args.skip_preflight,
    )


if __name__ == "__main__":
    sys.exit(main())
