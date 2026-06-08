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

Only the blog blob + canonical URL are produced here. LinkedIn/X are never
auto-published (see docs/ops/notion-blog-linkedin-v3-content-model.md).

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
}

# Fields that are worker-side gates and must NOT be forwarded to the function.
_GATE_FIELDS = frozenset({"autorizar_publicacion", "aprobado_contenido"})


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


def _build_payload_from_notion(
    notion_page_id: str, prop_map: Dict[str, str]
) -> Dict[str, Any]:
    """Read a Publicaciones page and map its properties to post fields.

    Best-effort: the Publicaciones schema is not versioned in this repo, so
    property names are configurable. Long bodies that live in the page body
    rather than a ``Copy Blog`` property are out of scope for v1 (documented).
    """
    from .. import notion_client

    page = notion_client.get_page(notion_page_id)
    props = page.get("properties") or {}

    def read(field: str) -> Any:
        name = prop_map.get(field)
        if not name:
            return None
        return _flatten_notion_prop(props.get(name))

    payload: Dict[str, Any] = {
        "notion_page_id": str(page.get("id") or notion_page_id),
        "slug": read("slug") or "",
        "title": read("title") or _page_title(page),
        "body_markdown": read("body_markdown") or "",
        "excerpt": read("excerpt") or "",
        "hero_image_url": read("hero_image_url") or "",
        "tags": read("tags") or [],
        "published_at": read("published_at") or "",
        "canonical_url": read("canonical_url") or "",
        "autorizar_publicacion": _as_bool(read("autorizar_publicacion")),
        "aprobado_contenido": _as_bool(read("aprobado_contenido")),
    }
    return payload


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

    logger.info("Publishing editorial post slug=%s (%d bytes)", payload.get("slug"), len(body))
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
            page_id=notion_page_id,
            properties={prop_name: {"url": published_url}},
        )
        return {"ok": True, "property": prop_name}
    except Exception as exc:  # noqa: BLE001 — never fail the publish over write-back
        logger.warning("Notion write-back failed: %s", exc)
        return {"ok": False, "error": str(exc), "property": prop_name}


# ---------------------------------------------------------------------------
# Visual asset resolution (deliverable F — stub, schema not in repo)
# ---------------------------------------------------------------------------


def resolve_visual_asset_urls(
    notion_page: Dict[str, Any], selection: Optional[List[str]] = None
) -> Dict[str, str]:
    """STUB (F): map `Selección imagen` → `imagen_alt_N_url`.

    The Publicaciones visual-asset schema is not versioned in this repo yet, so
    this is a documented no-op placeholder. See
    docs/ops/notion-blog-linkedin-v3-content-model.md §"Visual assets" for the
    intended mapping. Tracked by a skipped test in tests/test_editorial_publish.py.
    """
    # TODO(editorial-v3): read `Selección imagen` + imagen_alt_N_url properties
    # and return {"hero_image_url": ..., "imagen_alt_1_url": ...} once the
    # Publicaciones visual schema is confirmed.
    return {}


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------


def handle_web_publish_editorial_post(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Publish a blog post to Azure Blob via the editorial-publish function.

    Input (one of ``payload`` / ``notion_page_id`` is required):
        payload (dict): explicit post fields + ``autorizar_publicacion`` gate.
        notion_page_id (str): read post fields + gates from a Publicaciones page.
        dry_run (bool, default False): validate + build, do not call the network.
        write_back_to_notion (bool, default False): persist published_url to Notion.
        notion_prop_map (dict, optional): override Notion property names.
        timeout (int, default 30): function call timeout (1-120).

    Returns a dict with ``ok``. ``ok=False`` + ``would_publish=False`` means the
    gate blocked publication (no network call was made).
    """
    if not isinstance(input_data, dict):
        raise ValueError("input must be a JSON object")

    explicit_payload = input_data.get("payload")
    notion_page_id = str(input_data.get("notion_page_id") or "").strip()
    dry_run = bool(input_data.get("dry_run", False))
    timeout = int(input_data.get("timeout", 30))
    if not (1 <= timeout <= 120):
        raise ValueError("'timeout' must be between 1 and 120 seconds")
    prop_map = {**_DEFAULT_NOTION_PROP_MAP, **(input_data.get("notion_prop_map") or {})}

    # 1) Resolve source + raw payload.
    if isinstance(explicit_payload, dict):
        source = "payload"
        raw = dict(explicit_payload)
        authorized = _as_bool(raw.get("autorizar_publicacion"))
        content_approved = _as_bool(raw.get("aprobado_contenido")) if "aprobado_contenido" in raw else True
    elif notion_page_id:
        source = "notion"
        raw = _build_payload_from_notion(notion_page_id, prop_map)
        authorized = _as_bool(raw.get("autorizar_publicacion"))
        content_approved = _as_bool(raw.get("aprobado_contenido"))
    else:
        raise ValueError("provide either 'payload' (dict) or 'notion_page_id' (str)")

    # 2) Normalize/validate the post fields (raises ValueError on malformed input).
    post = _normalize_payload(raw)
    if not post.get("canonical_url"):
        post["canonical_url"] = _canonical_url(post["slug"])

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
            "gates": {
                "autorizar_publicacion": authorized,
                "aprobado_contenido": content_approved,
            },
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

    return response
