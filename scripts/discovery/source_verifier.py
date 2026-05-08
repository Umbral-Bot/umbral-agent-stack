"""Stage 7.5 pre-LLM source URL verifier.

Verifies a proposal's source URL **before** any LLM call. Hard-blocks copies
built on suspect sources (sandbox TLDs, dead links, redirects to a different
domain, non-textual content-types, malformed arXiv URLs). Soft-warns on
moderate signals (very new domain, missing ``<title>``, very short body).

Cache: SQLite at ``~/.cache/rick-discovery/source_verification.sqlite``,
TTL 7 days. Cached entries short-circuit the HTTP probe.

Public API
----------
``verify_source(url, *, config=None, cache_db=None, use_cache=True,
ops_log=None, client=None) -> dict``

Returns a verdict dict::

    {
      "ok": bool,                # False ⇒ caller MUST hard-block
      "url": "https://...",
      "reason": "blocklist_domain" | "http_404" | ... | "" if ok,
      "warnings": ["new_domain", ...],
      "details": {
          "host": "arxiv.org",
          "status_code": 200,
          "content_type": "text/html",
          "final_url": "https://...",
          "title": "...",
          "body_chars": 12345,
          "from_cache": False,
          "cache_age_s": null,
      },
    }

The verifier is **fail-closed on infrastructure errors** when the URL is not
explicitly trusted: a transport error after one retry is treated as
``http_unreachable`` (hard-block). Use ``--skip-source-verify`` (Stage 7.5)
or pass ``use_cache=False`` and a stub ``client`` for development.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

DEFAULT_CACHE_DB = Path.home() / ".cache" / "rick-discovery" / "source_verification.sqlite"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "source_verifier.yaml"
DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"

CACHE_TTL_S = 7 * 24 * 3600  # 7 days
HTTP_TIMEOUT_S = 10.0
HTTP_RETRIES = 1  # one retry on transport error
USER_AGENT = "umbral-source-verifier/1.0 (+https://umbral.bot)"

ALLOWED_CONTENT_TYPES = (
    "text/html",
    "application/pdf",
    "application/xml",
    "text/xml",
    "application/xhtml+xml",
)

DEFAULT_BLOCKLIST_TLDS = (".test", ".invalid", ".local", ".example")
DEFAULT_BLOCKLIST_DOMAINS = ("example.com", "example.org", "example.net", "localhost")
DEFAULT_HIGH_TRUST = (
    "arxiv.org",
    "autodesk.com",
    "buildingsmart.org",
    "sedibim.cl",
    "mit.edu",
    "acm.org",
    "ieee.org",
    "sciencedirect.com",
    "springer.com",
    "wiley.com",
    "construible.es",
    "aecweekly.com",
    "revistabit.cl",
    "linkedin.com",
    "github.com",
)

# arXiv abs URL (post-2007 scheme): /abs/YYMM.NNNNN[vN]/?  where YY = year-2000
# and MM ∈ [01, 12]. Year resolved as 2000+YY must lie in
# [arxiv_min_year, current_year + arxiv_max_year_offset].
_ARXIV_ABS_RE = re.compile(r"^/abs/(\d{2})(\d{2})\.(\d{4,5})(v\d+)?/?$")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass
class VerifierConfig:
    blocklist_domains: tuple[str, ...] = DEFAULT_BLOCKLIST_DOMAINS
    blocklist_tlds: tuple[str, ...] = DEFAULT_BLOCKLIST_TLDS
    allowlist_high_trust: tuple[str, ...] = DEFAULT_HIGH_TRUST
    warning_new_domain_days: int = 180
    arxiv_min_year: int = 2020
    arxiv_max_year_offset: int = 1
    short_body_min_chars: int = 400
    allowed_content_types: tuple[str, ...] = ALLOWED_CONTENT_TYPES
    http_timeout_s: float = HTTP_TIMEOUT_S
    http_retries: int = HTTP_RETRIES

    @classmethod
    def default(cls) -> "VerifierConfig":
        return cls()


def load_config(path: Path | str | None = None) -> VerifierConfig:
    """Load verifier config from YAML; fall back to defaults if missing."""
    p = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not p.is_file():
        return VerifierConfig.default()
    try:
        import yaml  # type: ignore
    except Exception:
        return VerifierConfig.default()
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return VerifierConfig.default()
    if not isinstance(data, dict):
        return VerifierConfig.default()

    def _tup(key: str, default: tuple[str, ...]) -> tuple[str, ...]:
        v = data.get(key)
        if isinstance(v, (list, tuple)):
            return tuple(str(x).strip().lower() for x in v if str(x).strip())
        return default

    return VerifierConfig(
        blocklist_domains=_tup("blocklist_domains", DEFAULT_BLOCKLIST_DOMAINS),
        blocklist_tlds=_tup("blocklist_tlds", DEFAULT_BLOCKLIST_TLDS),
        allowlist_high_trust=_tup("allowlist_high_trust", DEFAULT_HIGH_TRUST),
        warning_new_domain_days=int(data.get("warning_new_domain_days", 180)),
        arxiv_min_year=int(data.get("arxiv_min_year", 2020)),
        arxiv_max_year_offset=int(data.get("arxiv_max_year_offset", 1)),
        short_body_min_chars=int(data.get("short_body_min_chars", 400)),
        allowed_content_types=_tup("allowed_content_types", ALLOWED_CONTENT_TYPES),
        http_timeout_s=float(data.get("http_timeout_s", HTTP_TIMEOUT_S)),
        http_retries=int(data.get("http_retries", HTTP_RETRIES)),
    )


# --------------------------------------------------------------------------- #
# URL parsing helpers
# --------------------------------------------------------------------------- #

def _parse_host(url: str) -> str:
    try:
        u = urlparse(url)
    except Exception:
        return ""
    return (u.hostname or "").lower()


def _registrable_suffix(host: str) -> str:
    """Naive registrable-domain suffix (last 2 labels)."""
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _matches_suffix(host: str, suffixes: tuple[str, ...]) -> bool:
    """True if host ends with one of the given dot-prefixed TLDs (e.g. ``.test``)."""
    if not host:
        return False
    for s in suffixes:
        s = s.lower()
        if not s.startswith("."):
            s = "." + s
        if host == s.lstrip(".") or host.endswith(s):
            return True
    return False


def _is_blocklisted(host: str, config: VerifierConfig) -> str | None:
    if not host:
        return "malformed_url"
    host = host.lower()
    if _matches_suffix(host, config.blocklist_tlds):
        return "blocklist_tld"
    for d in config.blocklist_domains:
        d = d.lower()
        if host == d or host.endswith("." + d):
            return "blocklist_domain"
    return None


def _is_high_trust(host: str, config: VerifierConfig) -> bool:
    if not host:
        return False
    host = host.lower()
    for d in config.allowlist_high_trust:
        d = d.lower()
        if host == d or host.endswith("." + d):
            return True
    return False


def _check_arxiv(url: str, config: VerifierConfig) -> str | None:
    """Return reason if arXiv URL is malformed, else None."""
    try:
        u = urlparse(url)
    except Exception:
        return "arxiv_malformed"
    host = (u.hostname or "").lower()
    if not (host == "arxiv.org" or host.endswith(".arxiv.org")):
        return None  # not an arXiv URL → not our concern
    m = _ARXIV_ABS_RE.match(u.path or "")
    if not m:
        return "arxiv_malformed"
    yy = int(m.group(1))
    mm = int(m.group(2))
    if mm < 1 or mm > 12:
        return "arxiv_malformed"
    year = 2000 + yy  # arXiv new scheme started in 2007 (YYMM.NNNNN)
    current_year = datetime.now(timezone.utc).year
    if year < config.arxiv_min_year or year > current_year + config.arxiv_max_year_offset:
        return "arxiv_year_out_of_range"
    return None


# --------------------------------------------------------------------------- #
# Cache (sqlite)
# --------------------------------------------------------------------------- #

_CACHE_DDL = """
CREATE TABLE IF NOT EXISTS source_verification_cache (
    url TEXT PRIMARY KEY,
    verdict_json TEXT NOT NULL,
    cached_at INTEGER NOT NULL
)
"""


def _ensure_cache(db: Path) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        conn.execute(_CACHE_DDL)
        # Self-heal if a legacy/corrupt schema exists without our columns.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(source_verification_cache)")}
        required = {"url", "verdict_json", "cached_at"}
        if not required.issubset(cols):
            conn.execute("DROP TABLE source_verification_cache")
            conn.execute(_CACHE_DDL)
        conn.commit()
    finally:
        conn.close()


def cache_get(db: Path, url: str, *, ttl_s: int = CACHE_TTL_S) -> dict | None:
    if not db.is_file():
        return None
    try:
        conn = sqlite3.connect(db)
        try:
            row = conn.execute(
                "SELECT verdict_json, cached_at FROM source_verification_cache WHERE url=?",
                (url,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if not row:
        return None
    verdict_json, cached_at = row
    age = int(time.time()) - int(cached_at)
    if age > ttl_s:
        return None
    try:
        verdict = json.loads(verdict_json)
    except json.JSONDecodeError:
        return None
    verdict.setdefault("details", {})
    verdict["details"]["from_cache"] = True
    verdict["details"]["cache_age_s"] = age
    return verdict


def cache_put(db: Path, url: str, verdict: dict) -> None:
    try:
        _ensure_cache(db)
    except sqlite3.Error:
        return
    payload = dict(verdict)
    # Don't persist transient fields.
    details = dict(payload.get("details") or {})
    details.pop("from_cache", None)
    details.pop("cache_age_s", None)
    payload["details"] = details
    try:
        conn = sqlite3.connect(db)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO source_verification_cache (url, verdict_json, cached_at) VALUES (?,?,?)",
                (url, json.dumps(payload, ensure_ascii=False), int(time.time())),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error:
        # Cache is best-effort; never break verification on cache failure.
        return


# --------------------------------------------------------------------------- #
# Ops log
# --------------------------------------------------------------------------- #

def _log_event(event: str, *, ops_log: Path | None, **fields: Any) -> None:
    if ops_log is None:
        return
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    try:
        ops_log.parent.mkdir(parents=True, exist_ok=True)
        with open(ops_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        # Logging must never break verification.
        pass


# --------------------------------------------------------------------------- #
# HTTP probe
# --------------------------------------------------------------------------- #

@dataclass
class _ProbeResult:
    ok: bool
    status_code: int | None = None
    content_type: str = ""
    final_url: str = ""
    title: str = ""
    body_chars: int = 0
    redirect_chain: list[str] = field(default_factory=list)
    error: str = ""


def _http_probe(url: str, *, config: VerifierConfig, client: httpx.Client | None = None) -> _ProbeResult:
    """HEAD probe with GET fallback; returns ``_ProbeResult``.

    Manages its own client if none is provided. Follows redirects but records
    the chain so callers can detect redirect-domain hijacks.
    """
    own_client = client is None
    if own_client:
        client = httpx.Client(
            timeout=config.http_timeout_s,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        )
    assert client is not None
    try:
        last_err = ""
        for attempt in range(config.http_retries + 1):
            try:
                # HEAD first (cheap). Some servers reject HEAD → fall back to GET.
                try:
                    resp = client.head(url)
                    if resp.status_code in (405, 403, 501):
                        raise httpx.HTTPError("head_not_supported")
                except httpx.HTTPError:
                    resp = client.get(url)
                redirect_chain = [str(h.url) for h in resp.history] + [str(resp.url)]
                ct = (resp.headers.get("content-type") or "").lower()
                title = ""
                body_chars = 0
                # If text-y AND we used HEAD, do a small GET to capture body.
                if resp.request.method == "HEAD" and ct.startswith("text/"):
                    try:
                        gr = client.get(url)
                        text = gr.text or ""
                        body_chars = len(text)
                        m = _TITLE_RE.search(text)
                        if m:
                            title = re.sub(r"\s+", " ", m.group(1)).strip()[:300]
                        ct = (gr.headers.get("content-type") or ct).lower()
                        resp = gr
                        redirect_chain = [str(h.url) for h in gr.history] + [str(gr.url)]
                    except httpx.HTTPError as e:
                        last_err = f"get_after_head:{e!s:.120s}"
                elif resp.request.method == "GET":
                    text = resp.text or ""
                    body_chars = len(text)
                    if ct.startswith("text/"):
                        m = _TITLE_RE.search(text)
                        if m:
                            title = re.sub(r"\s+", " ", m.group(1)).strip()[:300]
                return _ProbeResult(
                    ok=True,
                    status_code=resp.status_code,
                    content_type=ct,
                    final_url=str(resp.url),
                    title=title,
                    body_chars=body_chars,
                    redirect_chain=redirect_chain,
                )
            except httpx.HTTPError as e:
                last_err = f"{type(e).__name__}:{e!s:.120s}"
                if attempt >= config.http_retries:
                    break
                time.sleep(0.2)
        return _ProbeResult(ok=False, error=last_err or "transport_error")
    finally:
        if own_client:
            client.close()


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def verify_source(
    url: str,
    *,
    config: VerifierConfig | None = None,
    cache_db: Path | None = None,
    use_cache: bool = True,
    ops_log: Path | None = None,
    client: httpx.Client | None = None,
) -> dict:
    """Verify a source URL. Returns a verdict dict (see module docstring)."""
    config = config or VerifierConfig.default()
    cache_db = cache_db if cache_db is not None else DEFAULT_CACHE_DB
    url = (url or "").strip()

    verdict: dict[str, Any] = {
        "ok": False,
        "url": url,
        "reason": "",
        "warnings": [],
        "details": {
            "host": "",
            "status_code": None,
            "content_type": "",
            "final_url": "",
            "title": "",
            "body_chars": 0,
            "from_cache": False,
            "cache_age_s": None,
        },
    }

    # Sanity: empty / no scheme.
    if not url:
        verdict["reason"] = "empty_url"
        _log_event("stage7_5.source_blocked", ops_log=ops_log, url=url, reason="empty_url")
        return verdict

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        verdict["reason"] = "malformed_url"
        _log_event("stage7_5.source_blocked", ops_log=ops_log, url=url, reason="malformed_url")
        return verdict

    host = parsed.hostname.lower()
    verdict["details"]["host"] = host

    # 0) Cache hit.
    if use_cache:
        cached = cache_get(cache_db, url)
        if cached is not None:
            _log_event(
                "stage7_5.source.cache_hit",
                ops_log=ops_log, url=url, ok=cached.get("ok"),
                reason=cached.get("reason", ""),
                cache_age_s=cached.get("details", {}).get("cache_age_s"),
            )
            return cached

    # 1) Blocklist (TLD + domain) — hard.
    bl = _is_blocklisted(host, config)
    if bl is not None:
        verdict["reason"] = bl
        _log_event("stage7_5.source_blocked", ops_log=ops_log, url=url, host=host, reason=bl)
        if use_cache:
            cache_put(cache_db, url, verdict)
        return verdict

    # 2) arXiv format (hard).
    arxiv_reason = _check_arxiv(url, config)
    if arxiv_reason is not None:
        verdict["reason"] = arxiv_reason
        _log_event("stage7_5.source_blocked", ops_log=ops_log, url=url, host=host, reason=arxiv_reason)
        if use_cache:
            cache_put(cache_db, url, verdict)
        return verdict

    # 3) HTTP probe (hard on 4xx/5xx, transport error, redirect domain change,
    #    bad content-type).
    probe = _http_probe(url, config=config, client=client)
    if not probe.ok:
        verdict["reason"] = "http_unreachable"
        verdict["details"]["body_chars"] = 0
        _log_event(
            "stage7_5.source_blocked",
            ops_log=ops_log, url=url, host=host,
            reason="http_unreachable", error=probe.error,
        )
        if use_cache:
            cache_put(cache_db, url, verdict)
        return verdict

    verdict["details"]["status_code"] = probe.status_code
    verdict["details"]["content_type"] = probe.content_type
    verdict["details"]["final_url"] = probe.final_url
    verdict["details"]["title"] = probe.title
    verdict["details"]["body_chars"] = probe.body_chars

    if probe.status_code is not None and probe.status_code >= 400:
        verdict["reason"] = f"http_{probe.status_code}"
        _log_event(
            "stage7_5.source_blocked",
            ops_log=ops_log, url=url, host=host,
            reason=verdict["reason"], status_code=probe.status_code,
        )
        if use_cache:
            cache_put(cache_db, url, verdict)
        return verdict

    final_host = _parse_host(probe.final_url)
    if final_host:
        # Redirect to a different *registrable* domain ⇒ hard block.
        if _registrable_suffix(final_host) != _registrable_suffix(host):
            # Also check whether the final host is itself blocklisted.
            final_bl = _is_blocklisted(final_host, config)
            verdict["reason"] = (
                "redirect_domain_change"
                if final_bl is None
                else f"redirect_to_{final_bl}"
            )
            _log_event(
                "stage7_5.source_blocked",
                ops_log=ops_log, url=url, host=host,
                final_host=final_host, reason=verdict["reason"],
            )
            if use_cache:
                cache_put(cache_db, url, verdict)
            return verdict

    # Content-type whitelist (case-insensitive prefix match).
    ct = (probe.content_type or "").split(";")[0].strip().lower()
    if ct and not any(ct == a or ct.startswith(a) for a in config.allowed_content_types):
        verdict["reason"] = "content_type_rejected"
        verdict["details"]["content_type"] = ct
        _log_event(
            "stage7_5.source_blocked",
            ops_log=ops_log, url=url, host=host,
            reason="content_type_rejected", content_type=ct,
        )
        if use_cache:
            cache_put(cache_db, url, verdict)
        return verdict

    # 4) Soft warnings (don't block).
    warnings: list[str] = []
    if not _is_high_trust(host, config):
        # We can't actually check WHOIS age cheaply, so flag any non-allowlist
        # host as "new_domain" only when the body is very thin too — to keep
        # noise down.
        if probe.body_chars and probe.body_chars < config.short_body_min_chars:
            warnings.append("new_domain")
    if ct.startswith("text/") and not probe.title:
        warnings.append("missing_title")
    if ct.startswith("text/") and probe.body_chars and probe.body_chars < config.short_body_min_chars:
        warnings.append("short_body")
    verdict["warnings"] = warnings

    # 5) OK.
    verdict["ok"] = True
    verdict["reason"] = ""
    _log_event(
        "stage7_5.source.verified",
        ops_log=ops_log, url=url, host=host,
        status_code=probe.status_code, content_type=ct,
        warnings=warnings,
    )
    if warnings:
        _log_event(
            "stage7_5.source_warnings",
            ops_log=ops_log, url=url, host=host, warnings=warnings,
        )
    if use_cache:
        cache_put(cache_db, url, verdict)
    return verdict


# --------------------------------------------------------------------------- #
# CLI smoke
# --------------------------------------------------------------------------- #

def _main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Stage 7.5 source verifier (manual smoke).")
    p.add_argument("url", help="URL to verify")
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--cache-db", default=str(DEFAULT_CACHE_DB))
    p.add_argument("--config", default=None)
    p.add_argument("--ops-log", default=str(DEFAULT_OPS_LOG))
    args = p.parse_args(argv)

    cfg = load_config(args.config) if args.config else VerifierConfig.default()
    verdict = verify_source(
        args.url,
        config=cfg,
        cache_db=Path(args.cache_db),
        use_cache=not args.no_cache,
        ops_log=Path(args.ops_log),
    )
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
