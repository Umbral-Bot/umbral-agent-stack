"""Task: web.publish_editorial_post — publish a blog post to the Azure layer.

Orchestrates the editorial blog publish step defined in ADR-010:

    Notion (Copy Blog + gates)  OR  explicit payload
      → Worker (this handler) — validates + enforces the human gate
        → Azure Function POST /api/publish-editorial-post
          → Blob editorial-posts/posts/{slug}.json + index.json

Hard product rule (do not weaken): the code NEVER publishes unless
``autorizar_publicacion`` is ``True`` in the validated payload. For a Notion
source the value is read from the page gate; for an explicit payload the caller
must set it. Anything else returns ``ok=False`` with ``would_publish=False`` and
performs **no network call**.

When a Notion page has the v2 ``Selección imagen`` property, its visual gate
must also be ready. Legacy pages without that property keep their historical
image behavior.

P2.6 / D3 (locked, docs/ops/editorial-norte-hitl-contract-2026-07-22.md §5.H):
the HITL-2 trigger requires a THIRD, equally hard condition — a Telegram "ok
publica" confirmation, asserted via the ``telegram_confirmed`` input. This
handler never infers it (nothing in this repo parses inbound Telegram
messages, see docs/ops/editorial-hitl2-publish-bridge-p26-2026-07-23.md) — an
external bridge (n8n workflow, operator) must have verified the reply and pass
``telegram_confirmed=True`` explicitly. Omitting it fails closed exactly like
the other two gates, for every source (``payload`` or ``notion_page_id``).

Only the blog blob + canonical URL are produced here: this handler never
auto-publishes LinkedIn or X (see
docs/ops/notion-blog-linkedin-v3-content-model.md). LinkedIn publishing lives
in a *separate* script (scripts/discovery/stage9c_linkedin_publish.py), which
is itself contained fail-closed — it blocks every real POST until the ADR-009
Company-page handler ``editorial.publish.linkedin_org`` exists (see
docs/plans/tanda-b-security-execution-plan-2026-07-19.md §5). So "no auto-
publish to LinkedIn/X" is true both here and, by containment, in stage9c.

Network call uses ``urllib`` (no extra deps), mirroring ``make_webhook`` so tests
patch ``worker.tasks.editorial_publish.urllib.request.urlopen``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("worker.tasks.editorial_publish")

# Fields the Azure Function requires (content_hash is auto-computed if missing).
_REQUIRED_POST_FIELDS = ("slug", "title", "body_markdown", "notion_page_id")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VISUAL_ALT_RE = re.compile(r"^Alt ([1-5])$")
_DEFAULT_AUTHOR = "David Moreira"
_DEFAULT_CANONICAL_BASE = "https://umbralbim.io"

# Default Publicaciones property names → post fields. Override per call via
# input_data["notion_prop_map"]. Schema lives in
# docs/ops/notion-blog-linkedin-v3-content-model.md.
_DEFAULT_NOTION_PROP_MAP: Dict[str, str] = {
    "slug": "Slug",
    "title": "Title",
    "body_markdown": "Copy Blog",
    "excerpt": "Bajada",
    "hero_image_url": "Hero Image",
    "tags": "Tags",
    "published_at": "Fecha publicación",
    "canonical_url": "published_url",
    "autorizar_publicacion": "autorizar_publicacion",
    "aprobado_contenido": "aprobado_contenido",
    # Fila I = B (P2.7) — RRSS link injection + terminal state, never used by
    # the publish payload itself (Azure never sees these).
    "copy_linkedin": "Copy LinkedIn",
    "copy_x": "Copy X",
    "copy_linkedin_empresa": "Copy LinkedIn empresa",
    "listo_rrss": "listo_rrss",
}

# Fields that are worker-side gates and must NOT be forwarded to the function.
_GATE_FIELDS = frozenset({"autorizar_publicacion", "aprobado_contenido"})

# Task B — post-publish RAG hook. After a successful (non-dry-run, gated) publish
# the body is indexed into Azure AI Search by reusing worker/tasks/rag.py (no
# duplicated embedding logic). Best-effort: missing env / errors never fail the
# publish — the blog blob is already live.
_DEFAULT_RAG_INDEX = "umbral-editorial"
_RAG_REQUIRED_ENV = (
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
)
_RAG_SOURCE_TYPE = "editorial_blog"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _content_hash(body_markdown: str, title: str = "", excerpt: str = "") -> str:
    """Match functions/editorial-publish/shared.compute_content_hash byte-for-byte."""
    h = hashlib.sha256()
    h.update((title or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((excerpt or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((body_markdown or "").encode("utf-8"))
    return h.hexdigest()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "sí", "si"}
    return False


def _flatten_notion_prop(prop: Any) -> Any:
    """Flatten a single Notion property value to a plain Python value."""
    if not isinstance(prop, dict):
        return None
    ptype = prop.get("type")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if ptype == "url":
        return prop.get("url")
    if ptype == "select":
        return (prop.get("select") or {}).get("name")
    if ptype == "status":
        return (prop.get("status") or {}).get("name")
    if ptype == "multi_select":
        return [item.get("name", "") for item in prop.get("multi_select", [])]
    if ptype == "checkbox":
        return bool(prop.get("checkbox"))
    if ptype == "number":
        return prop.get("number")
    if ptype == "date":
        return (prop.get("date") or {}).get("start")
    if ptype == "files":
        files = prop.get("files", [])
        for f in files:
            if f.get("type") == "external":
                return (f.get("external") or {}).get("url")
            if f.get("type") == "file":
                return (f.get("file") or {}).get("url")
        return None
    return None


def _page_title(page: Dict[str, Any]) -> str:
    props = page.get("properties") or {}
    if isinstance(props, dict):
        for meta in props.values():
            if isinstance(meta, dict) and meta.get("type") == "title":
                return _flatten_notion_prop(meta) or ""
    return ""


def _clean_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _evaluate_notion_visual_gate(
    page: Dict[str, Any], prop_map: Dict[str, str]
) -> tuple[str, Dict[str, Any]]:
    """Resolve the Notion hero and report whether the v2 visual gate is ready."""
    props = page.get("properties") or {}
    if not isinstance(props, dict):
        props = {}

    canonical_url = _clean_string(
        _flatten_notion_prop(props.get("Visual asset URL"))
    )
    legacy_prop = prop_map.get("hero_image_url")
    legacy_url = _clean_string(
        _flatten_notion_prop(props.get(legacy_prop)) if legacy_prop else None
    )
    selection_property_present = "Selección imagen" in props
    selection = _clean_string(
        _flatten_notion_prop(props.get("Selección imagen"))
    ) or None
    state = _clean_string(
        _flatten_notion_prop(props.get("Estado imagen"))
    ) or None

    detail: Dict[str, Any] = {
        "selection_property_present": selection_property_present,
        "selection": selection,
        "state": state,
        "ready": True,
        "reason": "legacy_compatible",
        "selected_property": None,
        "selected_url": "",
        "canonical_url": canonical_url,
        "hero_source": "none",
    }

    if not selection_property_present:
        hero_image_url = canonical_url or legacy_url
        detail["hero_source"] = (
            "visual_asset_url"
            if canonical_url
            else ("legacy_hero" if legacy_url else "none")
        )
        return hero_image_url, detail

    if selection == "Sin imagen":
        detail.update(
            ready=True,
            reason="explicit_no_image",
            hero_source="none",
        )
        return "", detail

    match = _VISUAL_ALT_RE.fullmatch(selection or "")
    if not match:
        reason = {
            None: "selection_missing",
            "Pendiente": "selection_pending",
            "Regenerar": "regeneration_requested",
        }.get(selection, "selection_invalid")
        detail.update(ready=False, reason=reason)
        return "", detail

    selected_property = f"imagen_alt_{match.group(1)}_url"
    selected_url = _clean_string(
        _flatten_notion_prop(props.get(selected_property))
    )
    detail.update(
        selected_property=selected_property,
        selected_url=selected_url,
    )

    if not selected_url:
        detail.update(ready=False, reason="selected_alt_url_missing")
        return "", detail
    if state != "Seleccionada":
        detail.update(ready=False, reason="image_state_not_selected")
        return "", detail
    if canonical_url and canonical_url != selected_url:
        detail.update(ready=False, reason="canonical_url_mismatch")
        return "", detail

    if canonical_url:
        detail.update(reason="selected_canonical", hero_source="visual_asset_url")
        return canonical_url, detail

    detail.update(reason="selected_alt_transition", hero_source="selected_alt")
    return selected_url, detail


def _build_payload_from_notion(
    notion_page_id: str, prop_map: Dict[str, str]
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Read a Publicaciones page and map its properties to post fields.

    Core property names remain configurable. The visual selection uses the
    versioned v2 schema in
    ``docs/ops/notion-publicaciones-v2-visual-gates-schema.md``. Long bodies
    that live in the page body rather than a ``Copy Blog`` property are out of
    scope for v1 (documented).
    """
    from .. import notion_client

    page = notion_client.get_page(notion_page_id)
    props = page.get("properties") or {}

    def read(field: str) -> Any:
        name = prop_map.get(field)
        if not name:
            return None
        return _flatten_notion_prop(props.get(name))

    hero_image_url, visual_gate = _evaluate_notion_visual_gate(page, prop_map)

    payload: Dict[str, Any] = {
        "notion_page_id": str(page.get("id") or notion_page_id),
        "slug": read("slug") or "",
        "title": read("title") or _page_title(page),
        "body_markdown": read("body_markdown") or "",
        "excerpt": read("excerpt") or "",
        "hero_image_url": hero_image_url,
        "tags": read("tags") or [],
        "published_at": read("published_at") or "",
        "canonical_url": read("canonical_url") or "",
        "autorizar_publicacion": _as_bool(read("autorizar_publicacion")),
        "aprobado_contenido": _as_bool(read("aprobado_contenido")),
    }
    return payload, visual_gate


def _normalize_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate + normalize a post payload (from either source)."""
    if not isinstance(raw, dict):
        raise ValueError("'payload' must be an object")

    slug = str(raw.get("slug") or "").strip()
    title = str(raw.get("title") or "").strip()
    body_markdown = str(raw.get("body_markdown") or "")
    notion_page_id = str(raw.get("notion_page_id") or "").strip()

    missing = [
        f
        for f, v in (
            ("slug", slug),
            ("title", title),
            ("body_markdown", body_markdown.strip()),
            ("notion_page_id", notion_page_id),
        )
        if not v
    ]
    if missing:
        raise ValueError(f"missing required field(s): {', '.join(missing)}")
    if not _SLUG_RE.match(slug):
        raise ValueError("'slug' must be lowercase kebab-case (a-z, 0-9, hyphens)")

    excerpt = str(raw.get("excerpt") or "").strip()
    content_hash = str(raw.get("content_hash") or "").strip() or _content_hash(
        body_markdown, title, excerpt
    )
    tags_raw = raw.get("tags") or []
    if not isinstance(tags_raw, list):
        raise ValueError("'tags' must be a list")
    tags = [str(t).strip() for t in tags_raw if str(t).strip()]

    payload: Dict[str, Any] = {
        "slug": slug,
        "title": title,
        "excerpt": excerpt,
        "body_markdown": body_markdown,
        "hero_image_url": str(raw.get("hero_image_url") or "").strip(),
        "author": str(raw.get("author") or _DEFAULT_AUTHOR).strip() or _DEFAULT_AUTHOR,
        "published_at": str(raw.get("published_at") or "").strip(),
        "notion_page_id": notion_page_id,
        "content_hash": content_hash,
        "tags": tags,
        "canonical_url": str(raw.get("canonical_url") or "").strip(),
    }
    return payload


def _canonical_url(slug: str) -> str:
    base = (os.environ.get("EDITORIAL_BLOG_CANONICAL_BASE_URL") or _DEFAULT_CANONICAL_BASE).rstrip("/")
    return f"{base}/noticias/{slug}"


def _function_url() -> str:
    return (os.environ.get("EDITORIAL_BLOG_FUNCTION_URL") or "").strip()


def _unpublish_function_url() -> str:
    url = _function_url()
    if url.endswith("/publish-editorial-post"):
        return f"{url.rsplit('/', 1)[0]}/unpublish-editorial-post"
    return url


def _validate_function_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("EDITORIAL_BLOG_FUNCTION_URL must be http(s)")
    host = (parsed.hostname or "").lower()
    is_local = host in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme == "http" and not is_local:
        raise ValueError("EDITORIAL_BLOG_FUNCTION_URL must use https (http only for localhost)")


def _post_to_function(url: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "UmbralWorker/0.4.0",
    }
    key = (os.environ.get("EDITORIAL_BLOG_FUNCTION_KEY") or "").strip()
    if key:
        headers["x-functions-key"] = key
    worker_token = (os.environ.get("WORKER_TOKEN") or "").strip()
    if worker_token:
        headers["x-worker-token"] = worker_token

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)

    logger.info("Calling editorial function slug=%s (%d bytes)", payload.get("slug"), len(body))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            data = json.loads(text) if text.strip() else {}
            return {"status_code": resp.status, "data": data}
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:1000]
        except Exception:  # noqa: BLE001
            pass
        logger.warning("Editorial function HTTP %d: %s", exc.code, err_body[:200])
        return {"status_code": exc.code, "data": _safe_json(err_body), "error_body": err_body}
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Editorial function connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"Editorial function timed out after {timeout}s") from exc


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        return {"raw": text}


def _maybe_write_back(notion_page_id: str, published_url: str, prop_name: str) -> Dict[str, Any]:
    """Best-effort: persist published_url back to the Notion page (url property)."""
    try:
        from .. import notion_client

        notion_client.update_page_properties(
            page_id_or_url=notion_page_id,
            properties={prop_name: {"url": published_url}},
        )
        return {"ok": True, "property": prop_name}
    except Exception as exc:  # noqa: BLE001 — never fail the publish over write-back
        logger.warning("Notion write-back failed: %s", exc)
        return {"ok": False, "error": str(exc), "property": prop_name}


# ---------------------------------------------------------------------------
# Fila I = B (P2.7) — post-publish RRSS link injection + listo_rrss
# ---------------------------------------------------------------------------

_RRSS_COPY_FIELDS = ("copy_linkedin", "copy_x", "copy_linkedin_empresa")


def _rt_chunks(text: str, size: int = 1900) -> List[Dict[str, Any]]:
    if not text:
        return [{"text": {"content": ""}}]
    return [{"text": {"content": text[i : i + size]}} for i in range(0, len(text), size)]


def inject_rrss_copies_and_mark_ready(
    notion_page_id: str,
    prop_map: Dict[str, str],
    *,
    published_url: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Fila I = B (docs/ops/editorial-norte-hitl-contract-2026-07-22.md §5.I):
    after a successful blog publish, inject ``published_url`` into each
    per-channel RRSS copy that doesn't already contain it, and mark
    ``listo_rrss = true`` — the terminal RRSS state under Fila I = B. The
    actual LinkedIn/X **post** stays manual (Fila I = B, ADR-010 §Contexto);
    this function makes **zero** calls to any social API — only Notion
    rich_text/checkbox properties.

    Fail-closed + idempotent, mirroring the P2.1/P2.4/P2.5 pattern: re-fetches
    the page live (never trusts a caller-supplied snapshot), no-ops
    (``already_ready=True``) if ``listo_rrss`` is already true, and is also
    idempotent per-channel — a copy that already contains ``published_url``
    (e.g. a previous partial run) is left untouched rather than appending the
    link a second time.

    ``published_url`` may be passed explicitly (the inline post-publish hook
    already has it from the just-completed Azure call) or omitted, in which
    case it's read from the page's own ``canonical_url`` property (the
    standalone/backfill task path) — required either way; a page with no
    ``published_url`` anywhere fails closed rather than injecting an empty
    link.
    """
    from .. import notion_client

    try:
        page = notion_client.get_page(notion_page_id)
    except Exception as exc:
        logger.warning("RRSS injection: failed to read page %s: %s", notion_page_id, exc)
        return {
            "ok": False,
            "error": str(exc),
            "notion_page_id": notion_page_id,
            "dry_run": dry_run,
            "already_ready": False,
            "injected_channels": [],
        }

    props = page.get("properties") or {}
    listo_rrss_prop = prop_map.get("listo_rrss", "listo_rrss")
    if _flatten_notion_prop(props.get(listo_rrss_prop)):
        return {
            "ok": True,
            "error": None,
            "dry_run": dry_run,
            "already_ready": True,
            "injected_channels": [],
            "notion_page_id": notion_page_id,
        }

    resolved_url = (published_url or "").strip() or _clean_string(
        _flatten_notion_prop(props.get(prop_map.get("canonical_url", "published_url")))
    )
    if not resolved_url:
        return {
            "ok": False,
            "error": "published_url_missing",
            "notion_page_id": notion_page_id,
            "dry_run": dry_run,
            "already_ready": False,
            "injected_channels": [],
        }

    updated_properties: Dict[str, Any] = {}
    injected_channels: List[str] = []
    for field in _RRSS_COPY_FIELDS:
        prop_name = prop_map.get(field)
        if not prop_name:
            continue
        current_text = _flatten_notion_prop(props.get(prop_name)) or ""
        if not current_text.strip():
            continue  # nothing to inject the link into
        if resolved_url in current_text:
            continue  # already injected (idempotent per-channel)
        new_text = f"{current_text.rstrip()}\n\n{resolved_url}"
        updated_properties[prop_name] = {"rich_text": _rt_chunks(new_text)}
        injected_channels.append(field)

    canonical_url_prop = prop_map.get("canonical_url", "published_url")
    updated_properties[canonical_url_prop] = {"url": resolved_url}
    updated_properties[listo_rrss_prop] = {"checkbox": True}

    if dry_run:
        return {
            "ok": True,
            "error": None,
            "dry_run": True,
            "would_inject": True,
            "already_ready": False,
            "injected_channels": injected_channels,
            "notion_page_id": notion_page_id,
        }

    try:
        notion_client.update_page_properties(
            page_id_or_url=notion_page_id,
            properties=updated_properties,
        )
    except Exception as exc:
        logger.warning("RRSS injection: failed to write page %s: %s", notion_page_id, exc)
        return {
            "ok": False,
            "error": str(exc),
            "notion_page_id": notion_page_id,
            "dry_run": dry_run,
            "already_ready": False,
            "injected_channels": [],
        }

    logger.info(
        "RRSS injection: page %s listo_rrss=true injected_channels=%s",
        notion_page_id[:8],
        injected_channels,
    )
    return {
        "ok": True,
        "error": None,
        "dry_run": False,
        "already_ready": False,
        "injected_channels": injected_channels,
        "notion_page_id": notion_page_id,
    }


def handle_editorial_inject_rrss_ready(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fila I = B post-publish hook (P2.7), standalone/backfill entry point:
    inject ``published_url`` into RRSS copies + mark ``listo_rrss = true``
    for an already-published Publicaciones row.

    Input:
        notion_page_id (str, required): Publicaciones page id (or URL).
        dry_run (bool, optional): preview without writing.
        notion_prop_map (dict, optional): override Notion property names.

    Returns: see ``inject_rrss_copies_and_mark_ready``.
    """
    dry_run = bool(input_data.get("dry_run", False))
    notion_page_id = str(input_data.get("notion_page_id") or "").strip()
    if not notion_page_id:
        return {
            "ok": False,
            "error": "'notion_page_id' is required",
            "notion_page_id": notion_page_id,
            "dry_run": dry_run,
            "already_ready": False,
            "injected_channels": [],
        }

    prop_map = {**_DEFAULT_NOTION_PROP_MAP, **(input_data.get("notion_prop_map") or {})}

    return inject_rrss_copies_and_mark_ready(notion_page_id, prop_map, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Task B — post-publish RAG indexing (reuses worker/tasks/rag.py)
# ---------------------------------------------------------------------------


def _rag_missing_env() -> List[str]:
    return [k for k in _RAG_REQUIRED_ENV if not (os.environ.get(k) or "").strip()]


def _maybe_index_rag(
    post: Dict[str, Any], *, index_after_publish: bool, skip_rag_index: bool
) -> Dict[str, Any]:
    """Index the published body into Azure AI Search (best-effort).

    Returns a dict merged into the handler response. Never raises: a skip or
    failure leaves the publish ``ok`` untouched.
    """
    if skip_rag_index:
        return {"rag_indexed": False, "rag_skipped_reason": "skip_rag_index"}
    if not index_after_publish:
        return {"rag_indexed": False, "rag_skipped_reason": "index_after_publish_false"}

    missing = _rag_missing_env()
    if missing:
        return {"rag_indexed": False, "rag_skipped_reason": f"missing_env:{','.join(missing)}"}

    index_name = (os.environ.get("EDITORIAL_RAG_INDEX_NAME") or _DEFAULT_RAG_INDEX).strip() or _DEFAULT_RAG_INDEX
    try:
        from .rag import handle_rag_index

        result = handle_rag_index(
            {
                "documents": [
                    {
                        "content": post["body_markdown"],
                        "title": post["title"],
                        "source": post.get("canonical_url") or post["slug"],
                        "source_type": _RAG_SOURCE_TYPE,
                    }
                ],
                "index_name": index_name,
            }
        )
        return {
            "rag_indexed": True,
            "rag_index_name": index_name,
            "rag_chunks": result.get("chunks"),
            "rag_result": result,
        }
    except Exception as exc:  # noqa: BLE001 — RAG is best-effort; publish already succeeded
        logger.warning("RAG index after publish failed (publish still ok): %s", exc)
        return {"rag_indexed": False, "rag_index_name": index_name, "rag_error": str(exc)}


# ---------------------------------------------------------------------------
# Visual asset resolution (Publicaciones visual schema v2)
# ---------------------------------------------------------------------------


def resolve_visual_asset_urls(
    notion_page: Dict[str, Any], selection: Optional[List[str]] = None
) -> Dict[str, str]:
    """Resolve the v2 visual selection into publish-ready image URLs.

    ``Selección imagen`` is the human-owned Notion Select with values
    ``Alt 1`` ... ``Alt 5`` or ``Sin imagen``. Non-empty
    ``imagen_alt_N_url`` properties are preserved as candidates only when an
    ``Alt N`` selection resolves to a non-empty URL; the chosen one is also
    exposed as ``hero_image_url``. Missing, pending, ``Sin imagen``, or
    incomplete selections degrade cleanly to ``{}``.

    ``selection`` is retained for compatibility with callers that already
    flatten a select/relation to a list. The first resolvable ``Alt N`` in list
    order wins deterministically. When it is omitted, the function reads
    ``Selección imagen`` from ``notion_page``. The function is pure and
    performs no Notion writes.
    """
    if not isinstance(notion_page, dict):
        return {}
    props = notion_page.get("properties") or {}
    if not isinstance(props, dict):
        return {}

    assets: Dict[str, str] = {}
    for alt_number in range(1, 6):
        prop_name = f"imagen_alt_{alt_number}_url"
        raw_url = _flatten_notion_prop(props.get(prop_name))
        if isinstance(raw_url, str) and raw_url.strip():
            assets[prop_name] = raw_url.strip()

    if selection is None:
        selected_values: List[Any] = [
            _flatten_notion_prop(props.get("Selección imagen"))
        ]
    elif isinstance(selection, list):
        selected_values = selection
    else:
        selected_values = []

    selected_prop = ""
    for value in selected_values:
        if not isinstance(value, str):
            continue
        match = _VISUAL_ALT_RE.fullmatch(value.strip())
        if not match:
            continue
        candidate_prop = f"imagen_alt_{match.group(1)}_url"
        if candidate_prop in assets:
            selected_prop = candidate_prop
            break

    if not selected_prop:
        return {}

    return {"hero_image_url": assets[selected_prop], **assets}


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------


def handle_web_publish_editorial_post(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Publish a blog post to Azure Blob via the editorial-publish function.

    Input (one of ``payload`` / ``notion_page_id`` is required):
        payload (dict): explicit post fields + ``autorizar_publicacion`` gate.
        notion_page_id (str): read post fields + gates from a Publicaciones page.
        telegram_confirmed (bool, default False): the third HITL-2/D3 gate
            (docs/ops/editorial-norte-hitl-contract-2026-07-22.md §5.H) — must
            be explicitly asserted true by the caller (an n8n bridge or
            operator that verified a Telegram "ok publica" reply); this
            handler never infers it from Notion or anywhere else. Required
            regardless of source (``payload`` or ``notion_page_id``).
        dry_run (bool, default False): validate + build, do not call the network.
        write_back_to_notion (bool, default False): persist published_url to Notion.
        notion_prop_map (dict, optional): override Notion property names.
        timeout (int, default 30): function call timeout (1-120).
        index_after_publish (bool, default True): index body into Azure AI Search
            (index ``EDITORIAL_RAG_INDEX_NAME`` / default ``umbral-editorial``)
            after a successful publish. Skips (publish stays ok) when the
            AZURE_SEARCH_* / AZURE_OPENAI_* env is missing.
        skip_rag_index (bool, default False): force-skip the RAG indexing hook.
        inject_rrss_after_publish (bool, default False): Fila I = B (P2.7) —
            after a successful publish, inject ``published_url`` into the
            per-channel RRSS copies and mark ``listo_rrss = true`` (best-
            effort; never fails the publish). Default off, mirroring
            ``write_back_to_notion``'s own default-False caution for a new
            Notion write path; the standalone task
            ``editorial.inject_rrss_ready`` covers the same row later if this
            was off at publish time. Never calls any LinkedIn/X API — the
            actual RRSS post stays manual (Fila I = B).

    Returns a dict with ``ok``. ``ok=False`` + ``would_publish=False`` means the
    gate blocked publication (no network call was made).
    """
    if not isinstance(input_data, dict):
        raise ValueError("input must be a JSON object")

    explicit_payload = input_data.get("payload")
    notion_page_id = str(input_data.get("notion_page_id") or "").strip()
    dry_run = bool(input_data.get("dry_run", False))
    telegram_confirmed = _as_bool(input_data.get("telegram_confirmed"))
    timeout = int(input_data.get("timeout", 30))
    if not (1 <= timeout <= 120):
        raise ValueError("'timeout' must be between 1 and 120 seconds")
    prop_map = {**_DEFAULT_NOTION_PROP_MAP, **(input_data.get("notion_prop_map") or {})}
    index_after_publish = bool(input_data.get("index_after_publish", True))
    skip_rag_index = bool(input_data.get("skip_rag_index", False))

    # 1) Resolve source + raw payload.
    visual_gate: Optional[Dict[str, Any]] = None
    if isinstance(explicit_payload, dict):
        source = "payload"
        raw = dict(explicit_payload)
        authorized = _as_bool(raw.get("autorizar_publicacion"))
        content_approved = _as_bool(raw.get("aprobado_contenido")) if "aprobado_contenido" in raw else True
    elif notion_page_id:
        source = "notion"
        raw, visual_gate = _build_payload_from_notion(notion_page_id, prop_map)
        authorized = _as_bool(raw.get("autorizar_publicacion"))
        content_approved = _as_bool(raw.get("aprobado_contenido"))
    else:
        raise ValueError("provide either 'payload' (dict) or 'notion_page_id' (str)")

    # 2) Normalize/validate the post fields (raises ValueError on malformed input).
    post = _normalize_payload(raw)
    if not post.get("canonical_url"):
        post["canonical_url"] = _canonical_url(post["slug"])

    gates: Dict[str, Any] = {
        "autorizar_publicacion": authorized,
        "aprobado_contenido": content_approved,
        "telegram_confirmed": telegram_confirmed,
    }
    if visual_gate is not None:
        gates["visual_asset"] = visual_gate

    # 3) HARD GATE — never publish without autorizar_publicacion=true (and, when
    #    coming from Notion, aprobado_contenido=true). No network on failure.
    if not authorized or not content_approved:
        logger.info(
            "Editorial publish blocked by gate slug=%s authorized=%s approved=%s",
            post["slug"], authorized, content_approved,
        )
        return {
            "ok": False,
            "error": "publication_not_authorized",
            "would_publish": False,
            "source": source,
            "slug": post["slug"],
            "gates": gates,
        }

    if visual_gate is not None and not visual_gate["ready"]:
        logger.info(
            "Editorial publish blocked by visual gate slug=%s reason=%s",
            post["slug"],
            visual_gate["reason"],
        )
        return {
            "ok": False,
            "error": "visual_asset_not_ready",
            "would_publish": False,
            "source": source,
            "slug": post["slug"],
            "gates": gates,
        }

    # 3.5) HITL-2 / D3 (locked, docs/ops/editorial-norte-hitl-contract-2026-07-22.md
    #    §5.H): the publish trigger requires THREE conditions, none optional —
    #    Estado imagen=Seleccionada (visual gate above) AND autorizar_publicacion
    #    (above) AND a Telegram "ok publica" confirmation. Nothing in this repo
    #    parses inbound Telegram messages, so `telegram_confirmed` is never
    #    inferred — it must be asserted explicitly by whatever external bridge
    #    (n8n workflow, operator) has verified the Telegram reply. Fail-closed
    #    by default: omitting it blocks publish exactly like the other two.
    if not telegram_confirmed:
        logger.info("Editorial publish blocked by Telegram confirmation gate slug=%s", post["slug"])
        return {
            "ok": False,
            "error": "telegram_confirmation_missing",
            "would_publish": False,
            "source": source,
            "slug": post["slug"],
            "gates": gates,
        }

    # 4) Build the function payload (drop worker-side gate fields).
    function_payload = {k: v for k, v in post.items() if k not in _GATE_FIELDS}

    if dry_run:
        return {
            "ok": True,
            "would_publish": True,
            "dry_run": True,
            "source": source,
            "slug": post["slug"],
            "blob_path": f"posts/{post['slug']}.json",
            "published_url": post["canonical_url"],
            "content_hash": post["content_hash"],
            "payload": function_payload,
            "gates": gates,
            "rag_indexed": False,
            "rag_skipped_reason": "dry_run",
        }

    # 5) Call the Azure Function.
    url = _function_url()
    if not url:
        return {
            "ok": False,
            "error": "not_configured",
            "detail": "EDITORIAL_BLOG_FUNCTION_URL is not set",
            "would_publish": True,
            "source": source,
            "slug": post["slug"],
            "gates": gates,
        }
    _validate_function_url(url)

    result = _post_to_function(url, function_payload, timeout)
    status_code = result["status_code"]
    data = result.get("data") or {}
    ok = 200 <= status_code < 300 and bool(data.get("ok", status_code < 300))

    response: Dict[str, Any] = {
        "ok": ok,
        "published": ok,
        "source": source,
        "slug": post["slug"],
        "status_code": status_code,
        "published_url": data.get("published_url") or post["canonical_url"],
        "blob_path": data.get("blob_path") or f"posts/{post['slug']}.json",
        "index_updated": data.get("index_updated"),
        "content_hash": data.get("content_hash") or post["content_hash"],
        "gates": gates,
    }
    if not ok:
        response["error"] = data.get("error") or "function_error"
        if "error_body" in result:
            response["detail"] = result["error_body"][:500]
        return response

    # 6) Optional best-effort write-back of published_url to Notion.
    if input_data.get("write_back_to_notion") and source == "notion":
        response["notion_write_back"] = _maybe_write_back(
            post["notion_page_id"],
            response["published_url"],
            prop_map.get("canonical_url", "published_url"),
        )

    # 7) Task B — post-publish RAG indexing (best-effort; never fails the publish).
    response.update(
        _maybe_index_rag(
            post,
            index_after_publish=index_after_publish,
            skip_rag_index=skip_rag_index,
        )
    )

    # 8) Fila I = B (P2.7): inject published_url into RRSS copies + mark
    #    listo_rrss=true (best-effort; never fails the publish, and never
    #    calls any LinkedIn/X API — see inject_rrss_copies_and_mark_ready).
    if input_data.get("inject_rrss_after_publish"):
        response["rrss_injection"] = inject_rrss_copies_and_mark_ready(
            post["notion_page_id"],
            prop_map,
            published_url=response["published_url"],
        )

    return response


def handle_web_unpublish_editorial_post(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Unpublish a blog post through the ADR-010 Azure Function.

    Unlike publish, this reverse/cleanup operation does not require
    ``autorizar_publicacion``. It removes the entry from ``index.json`` and, by
    default, asks the Function to delete ``posts/{slug}.json``.
    """
    if not isinstance(input_data, dict):
        raise ValueError("input must be a JSON object")

    slug = str(input_data.get("slug") or "").strip()
    notion_page_id = str(input_data.get("notion_page_id") or "").strip()
    if not slug and not notion_page_id:
        raise ValueError("provide either 'slug' or 'notion_page_id'")
    if slug and not _SLUG_RE.match(slug):
        raise ValueError("'slug' must be lowercase kebab-case (a-z, 0-9, hyphens)")

    timeout = int(input_data.get("timeout", 30))
    if not (1 <= timeout <= 120):
        raise ValueError("'timeout' must be between 1 and 120 seconds")

    delete_post_blob = input_data.get("delete_post_blob", True)
    if not isinstance(delete_post_blob, bool):
        raise ValueError("'delete_post_blob' must be a boolean")

    payload: Dict[str, Any] = {"delete_post_blob": delete_post_blob}
    if slug:
        payload["slug"] = slug
    if notion_page_id:
        payload["notion_page_id"] = notion_page_id

    if input_data.get("dry_run", False):
        return {
            "ok": True,
            "would_unpublish": True,
            "dry_run": True,
            "slug": slug or None,
            "notion_page_id": notion_page_id or None,
            "delete_post_blob": delete_post_blob,
            "payload": payload,
        }

    url = _unpublish_function_url()
    if not url:
        return {
            "ok": False,
            "error": "not_configured",
            "detail": "EDITORIAL_BLOG_FUNCTION_URL is not set",
            "would_unpublish": True,
            "slug": slug or None,
        }
    _validate_function_url(url)

    result = _post_to_function(url, payload, timeout)
    status_code = result["status_code"]
    data = result.get("data") or {}
    ok = 200 <= status_code < 300 and bool(data.get("ok", status_code < 300))
    response: Dict[str, Any] = {
        "ok": ok,
        "unpublished": ok,
        "slug": data.get("slug") or slug or None,
        "notion_page_id": notion_page_id or None,
        "status_code": status_code,
        "index_updated": data.get("index_updated"),
        "removed_from_index": data.get("removed_from_index"),
        "post_blob_deleted": data.get("post_blob_deleted"),
    }
    if not ok:
        response["error"] = data.get("error") or "function_error"
        if "error_body" in result:
            response["detail"] = result["error_body"][:500]
    return response
