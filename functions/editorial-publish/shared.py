"""Pure, dependency-free helpers for the editorial-publish function.

Stdlib only — no ``azure.*`` imports here so the validation + idempotent index
upsert logic can be unit-tested without the Azure Functions runtime (see
``tests/test_editorial_function_shared.py``).

Contract (mirrors docs/ops/azure-editorial-blog-runbook.md):

    posts/{slug}.json   full post document (schema_version 1)
    index.json          array of light entries, sorted published_at desc

Idempotency: re-publishing the same content (same ``notion_page_id`` /
``content_hash``) updates in place and never duplicates a slug.
Unpublishing removes one entry by ``notion_page_id`` or ``slug`` and keeps the
remaining entries sorted with the same ordering contract.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = 1

# Fields the caller MUST provide.
REQUIRED_FIELDS: Tuple[str, ...] = (
    "slug",
    "title",
    "body_markdown",
    "notion_page_id",
    "content_hash",
)

# Light fields surfaced in index.json for the SPA listing. ``notion_page_id`` and
# ``content_hash`` are also carried so the upsert stays idempotent across runs.
INDEX_FIELDS: Tuple[str, ...] = (
    "slug",
    "title",
    "excerpt",
    "hero_image_url",
    "published_at",
    "tags",
    "notion_page_id",
    "content_hash",
)

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

DEFAULT_AUTHOR = "David Moreira"
NEWS_PATH = "noticias"


class PayloadError(ValueError):
    """Raised when an incoming payload fails validation (maps to HTTP 400)."""


def now_iso() -> str:
    """UTC timestamp, second precision, Zulu suffix (e.g. 2026-06-07T12:00:00Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_content_hash(body_markdown: str, title: str = "", excerpt: str = "") -> str:
    """Deterministic sha256 over the meaningful content fields."""
    h = hashlib.sha256()
    h.update((title or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((excerpt or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((body_markdown or "").encode("utf-8"))
    return h.hexdigest()


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PayloadError(f"'{key}' is required and must be a non-empty string")
    return value.strip()


def _coerce_tags(raw: Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise PayloadError("'tags' must be a list of strings")
    tags: List[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise PayloadError("'tags' entries must be strings")
        cleaned = item.strip()
        if cleaned and cleaned not in tags:
            tags.append(cleaned)
    return tags


def validate_payload(payload: Any) -> Dict[str, Any]:
    """Validate + normalize an incoming publish payload.

    Returns a cleaned dict. Raises :class:`PayloadError` on any problem.
    """
    if not isinstance(payload, dict):
        raise PayloadError("payload must be a JSON object")

    missing = [f for f in REQUIRED_FIELDS if not str(payload.get(f, "")).strip()]
    if missing:
        raise PayloadError(f"missing required field(s): {', '.join(sorted(missing))}")

    slug = _require_str(payload, "slug")
    if not SLUG_RE.match(slug):
        raise PayloadError(
            "'slug' must be lowercase kebab-case (a-z, 0-9, single hyphens)"
        )
    if len(slug) > 120:
        raise PayloadError("'slug' too long (>120 chars)")

    title = _require_str(payload, "title")
    body_markdown = _require_str(payload, "body_markdown")
    notion_page_id = _require_str(payload, "notion_page_id")
    content_hash = _require_str(payload, "content_hash")

    excerpt = payload.get("excerpt") or ""
    if not isinstance(excerpt, str):
        raise PayloadError("'excerpt' must be a string")

    hero_image_url = payload.get("hero_image_url") or ""
    if not isinstance(hero_image_url, str):
        raise PayloadError("'hero_image_url' must be a string")

    author = (payload.get("author") or DEFAULT_AUTHOR)
    if not isinstance(author, str) or not author.strip():
        raise PayloadError("'author' must be a non-empty string")

    published_at = payload.get("published_at") or ""
    updated_at = payload.get("updated_at") or ""
    if not isinstance(published_at, str) or not isinstance(updated_at, str):
        raise PayloadError("'published_at'/'updated_at' must be ISO-8601 strings")

    canonical_url = payload.get("canonical_url") or ""
    if not isinstance(canonical_url, str):
        raise PayloadError("'canonical_url' must be a string")

    return {
        "slug": slug,
        "title": title.strip(),
        "excerpt": excerpt.strip(),
        "body_markdown": body_markdown,
        "hero_image_url": hero_image_url.strip(),
        "author": author.strip(),
        "published_at": published_at.strip(),
        "updated_at": updated_at.strip(),
        "notion_page_id": notion_page_id,
        "content_hash": content_hash,
        "tags": _coerce_tags(payload.get("tags")),
        "canonical_url": canonical_url.strip(),
    }


def build_canonical_url(slug: str, canonical_base_url: str) -> str:
    base = (canonical_base_url or "").rstrip("/")
    return f"{base}/{NEWS_PATH}/{slug}"


def build_post_document(
    payload: Dict[str, Any],
    *,
    canonical_base_url: str,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the full ``posts/{slug}.json`` document from a validated payload."""
    clean = validate_payload(payload)
    ts = now or now_iso()
    published_at = clean["published_at"] or ts
    updated_at = clean["updated_at"] or ts
    canonical_url = clean["canonical_url"] or build_canonical_url(
        clean["slug"], canonical_base_url
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "slug": clean["slug"],
        "title": clean["title"],
        "excerpt": clean["excerpt"],
        "body_markdown": clean["body_markdown"],
        "hero_image_url": clean["hero_image_url"],
        "author": clean["author"],
        "published_at": published_at,
        "updated_at": updated_at,
        "notion_page_id": clean["notion_page_id"],
        "content_hash": clean["content_hash"],
        "tags": clean["tags"],
        "canonical_url": canonical_url,
    }


def index_entry_from_post(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Project a full post document down to a light index entry."""
    return {k: doc.get(k) for k in INDEX_FIELDS}


def _sort_key(entry: Dict[str, Any]) -> Tuple[str, str]:
    # published_at desc → reverse the string; tie-break on slug for stability.
    return (entry.get("published_at") or "", entry.get("slug") or "")


def upsert_index(
    index: Any, entry: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], bool]:
    """Insert/replace ``entry`` in ``index`` idempotently.

    Match precedence: existing ``notion_page_id`` (handles slug renames), then
    ``slug`` (the canonical URL key). Returns ``(sorted_index, changed)`` where
    ``changed`` is False when the entry is byte-identical to what was there.
    """
    if index is None:
        items: List[Dict[str, Any]] = []
    elif isinstance(index, list):
        items = [dict(x) for x in index if isinstance(x, dict)]
    else:
        raise PayloadError("index.json must contain a JSON array")

    target = dict(entry)
    match_i = -1
    for i, existing in enumerate(items):
        if (
            target.get("notion_page_id")
            and existing.get("notion_page_id") == target["notion_page_id"]
        ):
            match_i = i
            break
    if match_i == -1:
        for i, existing in enumerate(items):
            if existing.get("slug") == target.get("slug"):
                match_i = i
                break

    changed = True
    if match_i >= 0:
        if items[match_i] == target:
            changed = False
        else:
            items[match_i] = target
    else:
        items.append(target)

    items.sort(key=_sort_key, reverse=True)
    return items, changed


def remove_from_index(
    index: Any,
    *,
    slug: Optional[str] = None,
    notion_page_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], bool, Optional[Dict[str, Any]]]:
    """Remove one entry from ``index`` idempotently.

    If ``notion_page_id`` is supplied it is the lookup key; otherwise ``slug`` is
    used. A missing entry is not an error and returns ``changed=False``.
    """
    clean_slug = (slug or "").strip()
    clean_notion_page_id = (notion_page_id or "").strip()
    if not clean_slug and not clean_notion_page_id:
        raise PayloadError("provide 'slug' or 'notion_page_id'")
    if clean_slug and not SLUG_RE.match(clean_slug):
        raise PayloadError(
            "'slug' must be lowercase kebab-case (a-z, 0-9, single hyphens)"
        )

    if index is None:
        items: List[Dict[str, Any]] = []
    elif isinstance(index, list):
        items = [dict(x) for x in index if isinstance(x, dict)]
    else:
        raise PayloadError("index.json must contain a JSON array")

    match_i = -1
    if clean_notion_page_id:
        for i, existing in enumerate(items):
            if existing.get("notion_page_id") == clean_notion_page_id:
                match_i = i
                break
    else:
        for i, existing in enumerate(items):
            if existing.get("slug") == clean_slug:
                match_i = i
                break

    if match_i == -1:
        items.sort(key=_sort_key, reverse=True)
        return items, False, None

    removed = items.pop(match_i)
    items.sort(key=_sort_key, reverse=True)
    return items, True, removed
