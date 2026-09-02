"""Azure Function (Python v2 model) — editorial blog publisher.

POST /api/publish-editorial-post

Writes ``posts/{slug}.json`` and idempotently upserts ``index.json`` into the
``editorial-posts`` blob container, then returns the canonical published URL.

Auth (defense in depth):
  1. Azure function key  (authLevel = FUNCTION; header ``x-functions-key``)
  2. Optional shared secret ``x-worker-token`` validated against ``WORKER_TOKEN``
     when that app setting is configured.

Storage access uses Managed Identity (DefaultAzureCredential) against
``EDITORIAL_BLOG_STORAGE_ACCOUNT``. For local dev, set
``EDITORIAL_BLOG_CONNECTION_STRING`` (e.g. Azurite) to use a connection string.

The pure validation + idempotent-upsert logic lives in ``shared.py`` and is unit
tested in ``tests/test_editorial_function_shared.py``.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

import azure.functions as func
from azure.core.exceptions import HttpResponseError, ResourceModifiedError, ResourceNotFoundError

from shared import (
    PayloadError,
    SLUG_RE,
    build_post_document,
    index_entry_from_post,
    now_iso,
    remove_from_index,
    upsert_index,
)

logger = logging.getLogger("editorial_publish")

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

INDEX_BLOB = "index.json"
POSTS_PREFIX = "posts"
ASSETS_PREFIX = "assets"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_HERO_PNG_BYTES = 12 * 1024 * 1024
_INDEX_MAX_RETRIES = 5


# ---------------------------------------------------------------------------
# Config + storage client
# ---------------------------------------------------------------------------


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _get_container_client():
    """Return a BlobContainerClient via connection string (local) or MI (cloud)."""
    container = _env("EDITORIAL_BLOG_CONTAINER", "editorial-posts")
    conn = _env("EDITORIAL_BLOG_CONNECTION_STRING")
    from azure.storage.blob import BlobServiceClient

    if conn:
        service = BlobServiceClient.from_connection_string(conn)
    else:
        account = _env("EDITORIAL_BLOG_STORAGE_ACCOUNT")
        if not account:
            raise RuntimeError(
                "Set EDITORIAL_BLOG_STORAGE_ACCOUNT (MI) or "
                "EDITORIAL_BLOG_CONNECTION_STRING (local)"
            )
        from azure.identity import DefaultAzureCredential

        service = BlobServiceClient(
            account_url=f"https://{account}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )
    return service.get_container_client(container)


def _ensure_container(container_client) -> None:
    try:
        container_client.create_container()
    except HttpResponseError:
        # Already exists (ContainerAlreadyExists) — fine.
        pass


# ---------------------------------------------------------------------------
# Blob IO
# ---------------------------------------------------------------------------


def _dumps(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False).encode("utf-8")


def _write_post(container_client, slug: str, doc: Dict[str, Any]) -> str:
    blob_path = f"{POSTS_PREFIX}/{slug}.json"
    blob = container_client.get_blob_client(blob_path)
    blob.upload_blob(
        _dumps(doc),
        overwrite=True,
        content_settings=_json_content_settings(),
    )
    return blob_path


def _delete_post(container_client, slug: str) -> bool:
    """Delete ``posts/{slug}.json``. Returns False when it was already absent."""
    blob_path = f"{POSTS_PREFIX}/{slug}.json"
    blob = container_client.get_blob_client(blob_path)
    try:
        blob.delete_blob()
        return True
    except ResourceNotFoundError:
        return False


def _json_content_settings():
    from azure.storage.blob import ContentSettings

    # short cache; the SPA can also bust with ?v=content_hash
    return ContentSettings(content_type="application/json; charset=utf-8", cache_control="public, max-age=60")


def _png_content_settings():
    from azure.storage.blob import ContentSettings

    # Heroes are immutable per publish: a new body means a new content_hash and
    # a fresh upload, so a long cache is safe and keeps the SPA fast.
    return ContentSettings(content_type="image/png", cache_control="public, max-age=31536000")


def _write_hero_asset(container_client, slug: str, png: bytes) -> str:
    """Store the hero PNG next to the post JSON and return its blob path.

    The canonical HITL-2 asset stays in Google Drive; this is the servable copy.
    A Drive ``/view`` link is a viewer page, not an image, so the worker sends
    the bytes and the blog serves them from its own container.
    """
    blob_path = f"{ASSETS_PREFIX}/{slug}.png"
    blob = container_client.get_blob_client(blob_path)
    blob.upload_blob(png, overwrite=True, content_settings=_png_content_settings())
    return blob_path


def _hero_asset_url(blob_path: str, *, cdn_base: str, container: str) -> str:
    """Public https URL for a stored asset, CDN first, storage account second."""
    if cdn_base:
        return f"{cdn_base.rstrip('/')}/{container}/{blob_path}"
    account = _env("EDITORIAL_BLOG_STORAGE_ACCOUNT")
    if not account:
        return ""
    return f"https://{account}.blob.core.windows.net/{container}/{blob_path}"


def _decode_hero_png(payload: Dict[str, Any]) -> Optional[bytes]:
    """Validate and decode ``hero_image_png_base64``; fail closed on garbage."""
    raw = payload.get("hero_image_png_base64")
    if raw in (None, ""):
        return None
    if not isinstance(raw, str):
        raise PayloadError("'hero_image_png_base64' must be a base64 string")
    # Checked on the encoded string first: decoding a 200 MB body just to reject
    # it is how a consumption-plan worker gets OOM-killed instead of answering
    # 400. Base64 inflates by 4/3, so this bound is exact enough to be safe.
    if len(raw) > (MAX_HERO_PNG_BYTES // 3 + 1) * 4 + 4:
        raise PayloadError(f"hero PNG over the {MAX_HERO_PNG_BYTES} byte cap")
    try:
        png = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PayloadError("'hero_image_png_base64' is not valid base64") from exc
    if not png.startswith(PNG_SIGNATURE):
        raise PayloadError("'hero_image_png_base64' is not a PNG")
    if len(png) > MAX_HERO_PNG_BYTES:
        raise PayloadError(f"hero PNG over the {MAX_HERO_PNG_BYTES} byte cap")
    return png


def _read_index(container_client) -> Tuple[Optional[list], Optional[str]]:
    """Return (index_array_or_None, etag_or_None)."""
    blob = container_client.get_blob_client(INDEX_BLOB)
    try:
        downloader = blob.download_blob()
        raw = downloader.readall()
        etag = downloader.properties.etag
        data = json.loads(raw.decode("utf-8")) if raw else []
        if not isinstance(data, list):
            logger.warning("index.json was not a JSON array; resetting")
            data = []
        return data, etag
    except ResourceNotFoundError:
        return None, None


def _write_index(container_client, items: list, etag: Optional[str]) -> None:
    blob = container_client.get_blob_client(INDEX_BLOB)
    kwargs: Dict[str, Any] = {
        "overwrite": True,
        "content_settings": _json_content_settings(),
    }
    if etag:
        # optimistic concurrency: only write if nobody changed it since we read
        kwargs["etag"] = etag
        kwargs["match_condition"] = _match_etag()
    else:
        # create-only: fail if it appeared between our read and write
        kwargs["match_condition"] = _match_if_missing()
    blob.upload_blob(_dumps(items), **kwargs)


def _match_etag():
    from azure.core import MatchConditions

    return MatchConditions.IfNotModified


def _match_if_missing():
    from azure.core import MatchConditions

    return MatchConditions.IfMissing


def _upsert_index_with_retry(container_client, entry: Dict[str, Any]) -> bool:
    """Read-modify-write index.json with ETag retry. Returns whether it changed."""
    last_err: Optional[Exception] = None
    for attempt in range(_INDEX_MAX_RETRIES):
        index, etag = _read_index(container_client)
        items, changed = upsert_index(index, entry)
        if not changed:
            return False
        try:
            _write_index(container_client, items, etag)
            return True
        except (ResourceModifiedError, HttpResponseError) as exc:
            status = getattr(exc, "status_code", None)
            if status not in (409, 412):
                raise
            last_err = exc
            logger.info("index.json concurrency conflict (attempt %d), retrying", attempt + 1)
    raise RuntimeError(f"index.json upsert failed after {_INDEX_MAX_RETRIES} retries: {last_err}")


def _remove_index_with_retry(
    container_client,
    *,
    slug: Optional[str] = None,
    notion_page_id: Optional[str] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Read-modify-write index.json for unpublish. Returns (changed, removed)."""
    last_err: Optional[Exception] = None
    for attempt in range(_INDEX_MAX_RETRIES):
        index, etag = _read_index(container_client)
        items, changed, removed = remove_from_index(
            index, slug=slug, notion_page_id=notion_page_id
        )
        if not changed:
            return False, removed
        try:
            _write_index(container_client, items, etag)
            return True, removed
        except (ResourceModifiedError, HttpResponseError) as exc:
            status = getattr(exc, "status_code", None)
            if status not in (409, 412):
                raise
            last_err = exc
            logger.info("index.json concurrency conflict (attempt %d), retrying", attempt + 1)
    raise RuntimeError(f"index.json remove failed after {_INDEX_MAX_RETRIES} retries: {last_err}")


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


def _json_response(body: Dict[str, Any], status: int) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
    )


def _worker_token_ok(req: func.HttpRequest) -> bool:
    expected = _env("WORKER_TOKEN")
    if not expected:
        return True  # not configured → rely on the Azure function key only
    return req.headers.get("x-worker-token", "") == expected


def _unpublish_payload(payload: Any) -> Tuple[str, str, bool]:
    if not isinstance(payload, dict):
        raise PayloadError("payload must be a JSON object")
    slug = str(payload.get("slug") or "").strip()
    notion_page_id = str(payload.get("notion_page_id") or "").strip()
    if not slug and not notion_page_id:
        raise PayloadError("provide 'slug' or 'notion_page_id'")
    if slug and not SLUG_RE.match(slug):
        raise PayloadError(
            "'slug' must be lowercase kebab-case (a-z, 0-9, single hyphens)"
        )
    delete_post_blob = payload.get("delete_post_blob", True)
    if not isinstance(delete_post_blob, bool):
        raise PayloadError("'delete_post_blob' must be a boolean")
    return slug, notion_page_id, delete_post_blob


@app.route(route="publish-editorial-post", methods=["POST"])
def publish_editorial_post(req: func.HttpRequest) -> func.HttpResponse:
    if not _worker_token_ok(req):
        return _json_response({"ok": False, "error": "unauthorized"}, 401)

    try:
        payload = req.get_json()
    except ValueError:
        return _json_response({"ok": False, "error": "invalid_json_body"}, 400)

    canonical_base = _env("EDITORIAL_BLOG_CANONICAL_BASE_URL", "https://umbralbim.io")
    cdn_base = _env("EDITORIAL_BLOG_CDN_BASE_URL")

    try:
        # The hero arrives as bytes, not as a link: a Drive share URL is a viewer
        # page and renders nothing as a blog hero. Decoded before the document is
        # built so a malformed image is a 400, never a post with a broken hero.
        hero_png = _decode_hero_png(payload if isinstance(payload, dict) else {})
        doc = build_post_document(payload, canonical_base_url=canonical_base, now=now_iso())
    except PayloadError as exc:
        return _json_response({"ok": False, "error": "invalid_payload", "detail": str(exc)}, 400)

    slug = doc["slug"]
    hero_blob_path = None
    container_client = None
    try:
        container_client = _get_container_client()
        _ensure_container(container_client)
        if hero_png is not None:
            hero_blob_path = _write_hero_asset(container_client, slug, hero_png)
            hero_url = _hero_asset_url(
                hero_blob_path,
                cdn_base=cdn_base,
                container=_env("EDITORIAL_BLOG_CONTAINER", "editorial-posts"),
            )
            if not hero_url:
                return _json_response(
                    {
                        "ok": False,
                        "error": "hero_asset_url_unresolvable",
                        "detail": "set EDITORIAL_BLOG_CDN_BASE_URL or EDITORIAL_BLOG_STORAGE_ACCOUNT",
                    },
                    500,
                )
            doc["hero_image_url"] = hero_url
        blob_path = _write_post(container_client, slug, doc)
        index_updated = _upsert_index_with_retry(container_client, index_entry_from_post(doc))
    except Exception as exc:  # noqa: BLE001 — surface a clean 500 to the worker
        logger.exception("editorial publish failed for slug=%s", slug)
        # The hero landed but the post did not: drop the orphan so the container
        # never holds an image no published document points at.
        if hero_blob_path and container_client is not None:
            try:
                container_client.get_blob_client(hero_blob_path).delete_blob()
            except Exception:  # noqa: BLE001 — cleanup is best effort
                logger.warning("orphan hero cleanup failed for %s", hero_blob_path)
        return _json_response({"ok": False, "error": "storage_error", "detail": str(exc)}, 500)

    container_name = _env("EDITORIAL_BLOG_CONTAINER", "editorial-posts")
    public_json_url = (
        f"{cdn_base.rstrip('/')}/{container_name}/{blob_path}" if cdn_base else None
    )

    return _json_response(
        {
            "ok": True,
            "published_url": doc["canonical_url"],
            "blob_path": blob_path,
            "index_updated": index_updated,
            "slug": slug,
            "content_hash": doc["content_hash"],
            "public_json_url": public_json_url,
            "hero_image_url": doc["hero_image_url"],
            "hero_blob_path": hero_blob_path,
        },
        200,
    )


@app.route(route="unpublish-editorial-post", methods=["POST"])
def unpublish_editorial_post(req: func.HttpRequest) -> func.HttpResponse:
    if not _worker_token_ok(req):
        return _json_response({"ok": False, "error": "unauthorized"}, 401)

    try:
        payload = req.get_json()
    except ValueError:
        return _json_response({"ok": False, "error": "invalid_json_body"}, 400)

    try:
        slug, notion_page_id, delete_post_blob = _unpublish_payload(payload)
    except PayloadError as exc:
        return _json_response({"ok": False, "error": "invalid_payload", "detail": str(exc)}, 400)

    try:
        container_client = _get_container_client()
        _ensure_container(container_client)
        index_updated, removed = _remove_index_with_retry(
            container_client, slug=slug or None, notion_page_id=notion_page_id or None
        )
        target_slug = slug or str((removed or {}).get("slug") or "")
        if delete_post_blob and target_slug:
            post_blob_deleted: Any = _delete_post(container_client, target_slug)
        elif delete_post_blob:
            post_blob_deleted = "skipped"
        else:
            post_blob_deleted = "skipped"
    except Exception as exc:  # noqa: BLE001 — surface a clean 500 to the worker
        logger.exception("editorial unpublish failed slug=%s notion_page_id=%s", slug, notion_page_id)
        return _json_response({"ok": False, "error": "storage_error", "detail": str(exc)}, 500)

    return _json_response(
        {
            "ok": True,
            "slug": target_slug or slug or None,
            "index_updated": index_updated,
            "post_blob_deleted": post_blob_deleted,
            "removed_from_index": bool(index_updated),
        },
        200,
    )
