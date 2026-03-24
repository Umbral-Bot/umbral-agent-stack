"""Shared research backends for Worker handlers and operational scripts."""

from __future__ import annotations

import html
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from json import JSONDecoder
from typing import Any

from worker.task_errors import TaskExecutionError

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TAVILY_API_URL = "https://api.tavily.com/search"

TAVILY_PROVIDER = "tavily"
GEMINI_SEARCH_PROVIDER = "gemini_google_search"
GOOGLE_LEGACY_PROVIDER = "google_legacy"

ResearchResult = dict[str, str]

_QUOTA_MARKERS = (
    "usage limit",
    "rate limit",
    "quota",
    "credits",
    "too many requests",
)


def safe_http_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")[:1000]
    except Exception:
        return ""


def _unique_results(results: list[ResearchResult], count: int) -> list[ResearchResult]:
    deduped: list[ResearchResult] = []
    seen: set[tuple[str, str]] = set()
    for item in results:
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        snippet = str(item.get("snippet", "")).strip()
        if not title or not url or not snippet:
            continue
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"title": title, "url": url, "snippet": snippet})
        if len(deduped) >= count:
            break
    return deduped


def search_tavily(query: str, count: int, *, search_depth: str = "basic") -> list[ResearchResult]:
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        raise TaskExecutionError(
            "research.web unavailable: TAVILY_API_KEY not configured",
            status_code=503,
            error_code="research_provider_not_configured",
            error_kind="configuration",
            retryable=False,
            provider=TAVILY_PROVIDER,
        )

    body = json.dumps({
        "query": query,
        "max_results": min(count, 20),
        "search_depth": search_depth,
    }).encode("utf-8")

    req = urllib.request.Request(
        TAVILY_API_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            items = data.get("results") or []
    except urllib.error.HTTPError as exc:
        body_str = safe_http_error_body(exc)
        body_lower = body_str.lower()

        if exc.code in {429, 432} or any(marker in body_lower for marker in _QUOTA_MARKERS):
            raise TaskExecutionError(
                "research.web unavailable: Tavily plan/quota exceeded",
                status_code=503,
                error_code="research_provider_quota_exceeded",
                error_kind="quota",
                retryable=False,
                provider=TAVILY_PROVIDER,
                upstream_status=exc.code,
            ) from exc

        if exc.code in {401, 403}:
            raise TaskExecutionError(
                "research.web unavailable: Tavily authentication or permissions failed",
                status_code=503,
                error_code="research_provider_auth_failed",
                error_kind="auth",
                retryable=False,
                provider=TAVILY_PROVIDER,
                upstream_status=exc.code,
            ) from exc

        if 500 <= exc.code <= 599:
            raise TaskExecutionError(
                f"research.web unavailable: Tavily upstream error {exc.code}",
                status_code=502,
                error_code="research_provider_upstream_error",
                error_kind="upstream",
                retryable=True,
                provider=TAVILY_PROVIDER,
                upstream_status=exc.code,
            ) from exc

        raise TaskExecutionError(
            f"research.web unavailable: Tavily HTTP error {exc.code}",
            status_code=502,
            error_code="research_provider_http_error",
            error_kind="upstream",
            retryable=False,
            provider=TAVILY_PROVIDER,
            upstream_status=exc.code,
        ) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, socket.timeout):
            raise TaskExecutionError(
                "research.web unavailable: Tavily request timed out",
                status_code=504,
                error_code="research_provider_timeout",
                error_kind="timeout",
                retryable=True,
                provider=TAVILY_PROVIDER,
            ) from exc
        raise TaskExecutionError(
            f"research.web unavailable: Tavily connection failed ({exc.reason})",
            status_code=504,
            error_code="research_provider_connection_failed",
            error_kind="network",
            retryable=True,
            provider=TAVILY_PROVIDER,
        ) from exc
    except TimeoutError as exc:
        raise TaskExecutionError(
            "research.web unavailable: Tavily request timed out",
            status_code=504,
            error_code="research_provider_timeout",
            error_kind="timeout",
            retryable=True,
            provider=TAVILY_PROVIDER,
        ) from exc
    except json.JSONDecodeError as exc:
        raise TaskExecutionError(
            "research.web unavailable: Tavily returned invalid JSON",
            status_code=502,
            error_code="research_provider_invalid_response",
            error_kind="upstream",
            retryable=False,
            provider=TAVILY_PROVIDER,
        ) from exc

    results = [
        {
            "title": str(item.get("title", "")).strip(),
            "url": str(item.get("url", "")).strip(),
            "snippet": (item.get("content") or "").replace("\n", " ").strip()[:500],
        }
        for item in items
    ]
    return _unique_results(results, count)


def _extract_first_json_document(text: str) -> Any | None:
    decoder = JSONDecoder()
    for idx, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            payload, _ = decoder.raw_decode(text[idx:])
            return payload
        except json.JSONDecodeError:
            continue
    return None


def _strip_citation_noise(text: str) -> str:
    cleaned = re.sub(r"\s*\[cite:\s*\d+\]\s*", " ", text or "")
    return " ".join(cleaned.split())


def _extract_redirect_links(rendered: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for href, raw_title in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', rendered, re.I | re.S):
        title = re.sub(r"<[^>]+>", "", raw_title)
        title = " ".join(html.unescape(title).split())
        if not href or not title:
            continue
        links.append({"title": title, "url": href})
    return links


def _coerce_gemini_results(text: str, meta: dict[str, Any], count: int) -> list[ResearchResult]:
    payload = _extract_first_json_document(text)
    items: list[Any]
    if isinstance(payload, dict):
        items = payload.get("results") or []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    results: list[ResearchResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        snippet = _strip_citation_noise(str(item.get("snippet", "")).strip())
        if url.startswith("http") and title and snippet:
            results.append({"title": title, "url": url, "snippet": snippet[:500]})

    results = _unique_results(results, count)
    if results:
        return results

    rendered = str((meta.get("searchEntryPoint") or {}).get("renderedContent", ""))
    links = _extract_redirect_links(rendered)
    summary = _strip_citation_noise(text)
    if summary:
        for link in links:
            results.append({
                "title": link["title"],
                "url": link["url"],
                "snippet": summary[:500],
            })
    return _unique_results(results, count)


def search_gemini_google_search(query: str, count: int) -> list[ResearchResult]:
    key = (
        os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY_NANO", "").strip()
    )
    if not key:
        raise TaskExecutionError(
            "research.web unavailable: GOOGLE_API_KEY not configured for Gemini grounded search",
            status_code=503,
            error_code="research_provider_not_configured",
            error_kind="configuration",
            retryable=False,
            provider=GEMINI_SEARCH_PROVIDER,
        )

    prompt = (
        f'Usa Google Search para encontrar informacion web actual sobre "{query}". '
        f'Devuelve SOLO JSON valido con esta forma exacta: '
        f'{{"results":[{{"title":"","url":"","snippet":""}}]}}. '
        f"Reglas: incluye hasta {count} resultados reales, URLs completas http/https, "
        "snippets breves en espanol, sin markdown, sin texto adicional. "
        'Si no encuentras resultados confiables, devuelve {"results":[]}.'
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 768,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    url = f"{GEMINI_BASE_URL}/gemini-2.5-flash:generateContent?key={key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_str = safe_http_error_body(exc)
        body_lower = body_str.lower()
        if exc.code in {401, 403}:
            raise TaskExecutionError(
                "research.web unavailable: Gemini grounded search authentication or permissions failed",
                status_code=503,
                error_code="research_provider_auth_failed",
                error_kind="auth",
                retryable=False,
                provider=GEMINI_SEARCH_PROVIDER,
                upstream_status=exc.code,
            ) from exc
        if exc.code == 429 or any(marker in body_lower for marker in _QUOTA_MARKERS):
            raise TaskExecutionError(
                "research.web unavailable: Gemini grounded search quota exceeded",
                status_code=503,
                error_code="research_provider_quota_exceeded",
                error_kind="quota",
                retryable=False,
                provider=GEMINI_SEARCH_PROVIDER,
                upstream_status=exc.code,
            ) from exc
        if 500 <= exc.code <= 599:
            raise TaskExecutionError(
                f"research.web unavailable: Gemini grounded search upstream error {exc.code}",
                status_code=502,
                error_code="research_provider_upstream_error",
                error_kind="upstream",
                retryable=True,
                provider=GEMINI_SEARCH_PROVIDER,
                upstream_status=exc.code,
            ) from exc
        raise TaskExecutionError(
            f"research.web unavailable: Gemini grounded search HTTP error {exc.code}",
            status_code=502,
            error_code="research_provider_http_error",
            error_kind="upstream",
            retryable=False,
            provider=GEMINI_SEARCH_PROVIDER,
            upstream_status=exc.code,
        ) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, socket.timeout):
            raise TaskExecutionError(
                "research.web unavailable: Gemini grounded search request timed out",
                status_code=504,
                error_code="research_provider_timeout",
                error_kind="timeout",
                retryable=True,
                provider=GEMINI_SEARCH_PROVIDER,
            ) from exc
        raise TaskExecutionError(
            f"research.web unavailable: Gemini grounded search connection failed ({exc.reason})",
            status_code=504,
            error_code="research_provider_connection_failed",
            error_kind="network",
            retryable=True,
            provider=GEMINI_SEARCH_PROVIDER,
        ) from exc
    except TimeoutError as exc:
        raise TaskExecutionError(
            "research.web unavailable: Gemini grounded search request timed out",
            status_code=504,
            error_code="research_provider_timeout",
            error_kind="timeout",
            retryable=True,
            provider=GEMINI_SEARCH_PROVIDER,
        ) from exc
    except json.JSONDecodeError as exc:
        raise TaskExecutionError(
            "research.web unavailable: Gemini grounded search returned invalid JSON",
            status_code=502,
            error_code="research_provider_invalid_response",
            error_kind="upstream",
            retryable=False,
            provider=GEMINI_SEARCH_PROVIDER,
        ) from exc

    candidate = (data.get("candidates") or [{}])[0]
    text = "".join(
        str(part.get("text", ""))
        for part in candidate.get("content", {}).get("parts", [])
        if isinstance(part, dict)
    )
    meta = candidate.get("groundingMetadata") or {}
    results = _coerce_gemini_results(text, meta, count)
    if not results:
        raise TaskExecutionError(
            "research.web unavailable: Gemini grounded search returned no usable results",
            status_code=502,
            error_code="research_provider_invalid_response",
            error_kind="upstream",
            retryable=False,
            provider=GEMINI_SEARCH_PROVIDER,
        )
    return results


def search_google_legacy(query: str, count: int) -> tuple[list[ResearchResult], str | None]:
    key = (
        os.environ.get("GOOGLE_CSE_API_KEY_RICK_UMBRAL_2")
        or os.environ.get("GOOGLE_CSE_API_KEY_RICK_UMBRAL")
        or os.environ.get("GOOGLE_CSE_API_KEY")
    )
    cx = os.environ.get("GOOGLE_CSE_CX")

    if not key:
        return [], "skip:no_key_GOOGLE_CSE_API_KEY"
    if not cx:
        return [], "skip:no_key_GOOGLE_CSE_CX"

    qs = urllib.parse.urlencode({"key": key, "cx": cx, "q": query, "num": min(count, 10)})
    req = urllib.request.Request(f"{GOOGLE_CSE_URL}?{qs}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data: dict[str, Any] = json.loads(r.read().decode())
            items = data.get("items") or []
            results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "").replace("\n", " ").strip(),
                }
                for item in items
            ]
            return _unique_results(results, count), None
    except urllib.error.HTTPError as e:
        body = safe_http_error_body(e)
        if e.code == 403:
            return [], "403:forbidden"
        return [], f"http:{e.code}:{body[:200]}"
    except Exception as e:
        err = str(e)
        if "403" in err:
            return [], "403:forbidden"
        return [], f"error:{err[:200]}"
