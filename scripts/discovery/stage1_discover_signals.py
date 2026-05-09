"""Stage 1 — Discover raw signals from RSS / Web channels.

Reads referentes_snapshot from SQLite, fetches RSS feeds and Web pages with
robots.txt + per-domain rate-limit, and persists deduplicable raw signals
into ``signals_raw``.

Policies:
- User-Agent: ``UmbralBIM-Editorial-Bot/1.0 (+contacto@umbralbim.cl)``.
- Per-domain min interval (default 2 s).
- Robots: fail-open on network error; otherwise ``can_fetch`` decides.
- Retries: 1 s + 3 s backoff on 5xx and timeouts.
- LinkedIn: SKIPPED with two-layer guard (canal_tipo == linkedin OR host).
- Dedup: ``sha256(canonical_url + "\\n" + (iso_pub or ""))`` UNIQUE in DB.
- YouTube / otros canales: snapshot only, ``out_of_scope_stage1`` row.

CLI:
    python -m scripts.discovery.stage1_discover_signals \\
        --sqlite ~/.cache/rick-discovery/state.sqlite \\
        [--canal {rss,web,all}] [--max-per-canal N] \\
        [--min-interval 2.0] [--snapshot-max-age-hours N] \\
        [--dry-run] [--verbose]
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Iterable
from xml.etree import ElementTree as ET

import httpx

USER_AGENT = "UmbralBIM-Editorial-Bot/1.0 (+contacto@umbralbim.cl)"
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_MIN_INTERVAL_S = 2.0
RETRY_BACKOFFS_S: tuple[float, ...] = (1.0, 3.0)
LINKEDIN_DOMAINS = {"linkedin.com", "www.linkedin.com", "m.linkedin.com"}

DROP_QUERY_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                     "utm_content", "fbclid", "gclid", "ref", "ref_src"}

log = logging.getLogger("stage1_discover_signals")


# -------------------- helpers --------------------

def canonicalize_url(url: str) -> str:
    p = urllib.parse.urlsplit(url.strip())
    scheme = (p.scheme or "http").lower()
    host = (p.hostname or "").lower()
    netloc = host
    if p.port and not (
        (scheme == "http" and p.port == 80) or (scheme == "https" and p.port == 443)
    ):
        netloc = f"{host}:{p.port}"
    qs = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
        if k.lower() not in DROP_QUERY_PARAMS
    ]
    query = urllib.parse.urlencode(qs)
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))


def is_linkedin(url: str) -> bool:
    try:
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return False
    if not host:
        return False
    if host in LINKEDIN_DOMAINS:
        return True
    return host.endswith(".linkedin.com")


def dedup_hash(canonical_url: str, published_at: str | None) -> str:
    s = f"{canonical_url}\n{published_at or ''}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _to_iso(text: str | None) -> str | None:
    if not text:
        return None
    s = text.strip()
    if not s:
        return None
    # Try ISO 8601
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        pass
    # Try RFC 822 (RSS pubDate)
    try:
        dt = parsedate_to_datetime(s)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# -------------------- robots + rate-limit --------------------

class RobotsCache:
    """Per-host robots.txt cache. Fail-open on network errors."""

    def __init__(
        self,
        *,
        fetcher: Callable[[str], str | None] | None = None,
        user_agent: str = USER_AGENT,
    ) -> None:
        self._cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._fetcher = fetcher
        self._user_agent = user_agent

    def _default_fetch(self, robots_url: str) -> str | None:
        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT_S, headers={"User-Agent": self._user_agent}) as c:
                r = c.get(robots_url)
                if r.status_code >= 400:
                    return None
                return r.text
        except Exception as exc:  # noqa: BLE001
            log.debug("robots fetch error %s: %s", robots_url, exc)
            return None

    def can_fetch(self, url: str) -> bool:
        p = urllib.parse.urlsplit(url)
        host = (p.hostname or "").lower()
        if not host:
            return True
        scheme = p.scheme or "https"
        key = f"{scheme}://{host}"
        if key not in self._cache:
            robots_url = f"{key}/robots.txt"
            text = (self._fetcher or self._default_fetch)(robots_url)
            if text is None:
                self._cache[key] = None
            else:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(text.splitlines())
                self._cache[key] = rp
        rp = self._cache[key]
        if rp is None:
            return True  # fail-open
        return rp.can_fetch(self._user_agent, url)


class RateLimiter:
    """Per-domain min-interval gate."""

    def __init__(
        self,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        *,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.min_interval_s = float(min_interval_s)
        self._last: dict[str, float] = {}
        self._clock = clock or time.monotonic
        self._sleeper = sleeper or time.sleep
        self.hits = 0

    def wait(self, host: str) -> float:
        now = self._clock()
        last = self._last.get(host)
        slept = 0.0
        if last is not None:
            elapsed = now - last
            if elapsed < self.min_interval_s:
                slept = self.min_interval_s - elapsed
                self._sleeper(slept)
                self.hits += 1
                now = self._clock()
        self._last[host] = now
        return slept


# -------------------- fetch --------------------

@dataclass
class FetchResult:
    status: str   # ok|http_404|http_5xx|http_error|timeout
    body: str = ""
    final_url: str = ""
    last_modified: str | None = None
    error: str | None = None


def fetch_url(
    url: str,
    *,
    client: httpx.Client,
    timeout: float = DEFAULT_TIMEOUT_S,
    backoffs: tuple[float, ...] = RETRY_BACKOFFS_S,
    sleeper: Callable[[float], None] = time.sleep,
) -> FetchResult:
    """GET with retry on 5xx + timeout. Returns classified FetchResult."""
    attempts = 1 + len(backoffs)
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            r = client.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        except (httpx.TimeoutException,) as exc:
            last_exc = exc
            if i < attempts - 1:
                sleeper(backoffs[i])
                continue
            return FetchResult(status="timeout", error=str(exc))
        except httpx.HTTPError as exc:
            return FetchResult(status="http_error", error=str(exc))
        if 500 <= r.status_code < 600:
            if i < attempts - 1:
                sleeper(backoffs[i])
                continue
            return FetchResult(status="http_5xx", error=f"HTTP {r.status_code}")
        if r.status_code == 404:
            return FetchResult(status="http_404", error="HTTP 404")
        if r.status_code >= 400:
            return FetchResult(status="http_error", error=f"HTTP {r.status_code}")
        return FetchResult(
            status="ok",
            body=r.text,
            final_url=str(r.url),
            last_modified=r.headers.get("Last-Modified"),
        )
    # Unreachable, but for completeness
    return FetchResult(status="http_error", error=str(last_exc) if last_exc else "unknown")


# -------------------- parsing --------------------

def parse_rss(text: str) -> list[dict[str, str | None]]:
    """Parse RSS 2.0 or Atom 1.0. Returns list of dicts."""
    out: list[dict[str, str | None]] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"parse_error: {exc}") from exc

    def _local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    # Walk all element nodes; pick items/entries.
    for el in root.iter():
        tag = _local(el.tag)
        if tag == "item":
            link = (el.findtext("link") or "").strip()
            title = (el.findtext("title") or "").strip()
            pub = (el.findtext("pubDate") or el.findtext("{http://purl.org/dc/elements/1.1/}date") or "").strip()
            desc = (el.findtext("description") or "").strip()
            if link:
                out.append({
                    "url": link,
                    "title": title or None,
                    "published_at": _to_iso(pub),
                    "excerpt": (desc[:280] if desc else None),
                })
        elif tag == "entry":
            href = None
            for child in el:
                if _local(child.tag) == "link":
                    href = child.attrib.get("href") or (child.text or "").strip()
                    if href:
                        break
            title = ""
            pub = ""
            summ = ""
            for child in el:
                t = _local(child.tag)
                if t == "title":
                    title = (child.text or "").strip()
                elif t in ("updated", "published"):
                    if not pub:
                        pub = (child.text or "").strip()
                elif t == "summary":
                    summ = (child.text or "").strip()
            if href:
                out.append({
                    "url": href,
                    "title": title or None,
                    "published_at": _to_iso(pub),
                    "excerpt": (summ[:280] if summ else None),
                })
    return out


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)


def parse_web_page(html: str, url: str, last_modified: str | None) -> dict[str, str | None]:
    title = None
    m = _TITLE_RE.search(html)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip() or None
    desc = None
    m2 = _META_DESC_RE.search(html)
    if m2:
        d = m2.group(1).strip()
        desc = (d[:280] if d else None)
    return {
        "url": url,
        "title": title,
        "published_at": _to_iso(last_modified),
        "excerpt": desc,
    }


# -------------------- DB --------------------

def _insert_signal(
    conn: sqlite3.Connection,
    *,
    referente_id: str,
    canal_tipo: str,
    url: str | None,
    canonical_url: str | None,
    title: str | None,
    excerpt: str | None,
    published_at: str | None,
    discovered_at: str,
    dedup_h: str,
    source_status: str,
) -> bool:
    try:
        conn.execute(
            """
            INSERT INTO signals_raw
                (referente_id, canal_tipo, url, canonical_url, title, excerpt,
                 published_at, discovered_at, dedup_hash, source_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (referente_id, canal_tipo, url, canonical_url, title, excerpt,
             published_at, discovered_at, dedup_h, source_status),
        )
        return True
    except sqlite3.IntegrityError:
        return False


# -------------------- pipeline --------------------

@dataclass
class StageStats:
    referentes_processed: int = 0
    domains: set[str] = field(default_factory=set)
    signals_unique: int = 0
    signals_duplicate: int = 0
    linkedin_skips: int = 0
    robots_disallow: int = 0
    rate_limit_hits: int = 0
    errors_by_status: dict[str, int] = field(default_factory=dict)


def _bump(d: dict[str, int], k: str) -> None:
    d[k] = d.get(k, 0) + 1


def process_channel(
    *,
    referente_id: str,
    canal_tipo: str,
    canal_url: str,
    conn: sqlite3.Connection,
    client: httpx.Client,
    robots: RobotsCache,
    limiter: RateLimiter,
    stats: StageStats,
    max_items: int | None = None,
    dry_run: bool = False,
) -> None:
    discovered_at = _now_iso()

    # Two-layer LinkedIn guard: canal_tipo OR host.
    if canal_tipo == "linkedin" or is_linkedin(canal_url):
        host = (urllib.parse.urlsplit(canal_url).hostname or "").lower()
        log.warning(
            "linkedin canal pendiente referente=%s modo=manual_or_apify_tbd url_host=%s",
            referente_id, host,
        )
        stats.linkedin_skips += 1
        if not dry_run:
            canon = canonicalize_url(canal_url)
            h = dedup_hash(canon, None)
            ok = _insert_signal(
                conn, referente_id=referente_id, canal_tipo="linkedin",
                url=canal_url, canonical_url=canon, title=None, excerpt=None,
                published_at=None, discovered_at=discovered_at,
                dedup_h=h, source_status="linkedin_skip",
            )
            if ok:
                stats.signals_unique += 1
            else:
                stats.signals_duplicate += 1
            conn.commit()
        return

    if canal_tipo not in ("rss", "web"):
        # youtube / otros → out_of_scope_stage1 marker.
        if not dry_run:
            canon = canonicalize_url(canal_url)
            h = dedup_hash(canon, None)
            _insert_signal(
                conn, referente_id=referente_id, canal_tipo=canal_tipo,
                url=canal_url, canonical_url=canon, title=None, excerpt=None,
                published_at=None, discovered_at=discovered_at,
                dedup_h=h, source_status="out_of_scope_stage1",
            )
            conn.commit()
        return

    host = (urllib.parse.urlsplit(canal_url).hostname or "").lower()
    if host:
        stats.domains.add(host)

    if not robots.can_fetch(canal_url):
        stats.robots_disallow += 1
        if not dry_run:
            canon = canonicalize_url(canal_url)
            h = dedup_hash(canon, None)
            _insert_signal(
                conn, referente_id=referente_id, canal_tipo=canal_tipo,
                url=canal_url, canonical_url=canon, title=None, excerpt=None,
                published_at=None, discovered_at=discovered_at,
                dedup_h=h, source_status="robots_disallow",
            )
        conn.commit()
        return

    if host:
        limiter.wait(host)

    fr = fetch_url(canal_url, client=client)
    stats.rate_limit_hits = limiter.hits

    if fr.status != "ok":
        _bump(stats.errors_by_status, fr.status)
        if not dry_run:
            canon = canonicalize_url(canal_url)
            h = dedup_hash(canon, None)
            _insert_signal(
                conn, referente_id=referente_id, canal_tipo=canal_tipo,
                url=canal_url, canonical_url=canon, title=None, excerpt=None,
                published_at=None, discovered_at=discovered_at,
                dedup_h=h, source_status=fr.status,
            )
        conn.commit()
        return

    # OK → parse.
    items: list[dict[str, str | None]]
    if canal_tipo == "rss":
        try:
            items = parse_rss(fr.body)
        except ValueError as exc:
            _bump(stats.errors_by_status, "parse_error")
            log.warning("rss parse_error referente=%s url=%s err=%s",
                        referente_id, canal_url, exc)
            if not dry_run:
                canon = canonicalize_url(canal_url)
                h = dedup_hash(canon, None)
                _insert_signal(
                    conn, referente_id=referente_id, canal_tipo=canal_tipo,
                    url=canal_url, canonical_url=canon, title=None, excerpt=None,
                    published_at=None, discovered_at=discovered_at,
                    dedup_h=h, source_status="parse_error",
                )
            conn.commit()
            return
    else:
        items = [parse_web_page(fr.body, fr.final_url or canal_url, fr.last_modified)]

    if max_items is not None:
        items = items[:max_items]

    for item in items:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        try:
            canon = canonicalize_url(url)
        except Exception:  # noqa: BLE001
            continue
        if is_linkedin(canon):
            # Defensive: a feed link to LinkedIn should not enter the pipeline.
            stats.linkedin_skips += 1
            continue
        h = dedup_hash(canon, item.get("published_at"))
        if dry_run:
            stats.signals_unique += 1
            continue
        ok = _insert_signal(
            conn,
            referente_id=referente_id,
            canal_tipo=canal_tipo,
            url=url,
            canonical_url=canon,
            title=item.get("title"),
            excerpt=item.get("excerpt"),
            published_at=item.get("published_at"),
            discovered_at=discovered_at,
            dedup_h=h,
            source_status="ok",
        )
        if ok:
            stats.signals_unique += 1
        else:
            stats.signals_duplicate += 1
    conn.commit()


def _load_snapshot_rows(
    conn: sqlite3.Connection,
    *,
    canal: str,
    snapshot_max_age_hours: int | None = None,
) -> list[sqlite3.Row]:
    sql = "SELECT referente_id, nombre, canal_tipo, canal_url, snapshot_at FROM referentes_snapshot"
    where: list[str] = []
    params: list[Any] = []
    if canal != "all":
        where.append("canal_tipo = ?")
        params.append(canal)
    if snapshot_max_age_hours is not None:
        cutoff = (
            datetime.now(timezone.utc).timestamp() - snapshot_max_age_hours * 3600
        )
        where.append("strftime('%s', snapshot_at) >= ?")
        params.append(str(int(cutoff)))
    if where:
        sql += " WHERE " + " AND ".join(where)
    return list(conn.execute(sql, params))


def run(
    *,
    sqlite_path: Path,
    canal: str = "all",
    max_per_canal: int | None = None,
    min_interval: float = DEFAULT_MIN_INTERVAL_S,
    snapshot_max_age_hours: int | None = None,
    dry_run: bool = False,
    client: httpx.Client | None = None,
    robots: RobotsCache | None = None,
    limiter: RateLimiter | None = None,
) -> dict[str, Any]:
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    # Ensure schema.
    from scripts.discovery.stage0_load_referentes import apply_migrations
    apply_migrations(conn)

    rows = _load_snapshot_rows(conn, canal=canal, snapshot_max_age_hours=snapshot_max_age_hours)
    stats = StageStats()

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=DEFAULT_TIMEOUT_S, follow_redirects=True)
        owns_client = True
    robots = robots or RobotsCache()
    limiter = limiter or RateLimiter(min_interval_s=min_interval)

    seen_referentes: set[str] = set()
    try:
        for row in rows:
            referente_id = row["referente_id"]
            seen_referentes.add(referente_id)
            process_channel(
                referente_id=referente_id,
                canal_tipo=row["canal_tipo"],
                canal_url=row["canal_url"],
                conn=conn,
                client=client,
                robots=robots,
                limiter=limiter,
                stats=stats,
                max_items=max_per_canal,
                dry_run=dry_run,
            )
    finally:
        if owns_client:
            client.close()
        conn.close()

    stats.referentes_processed = len(seen_referentes)
    stats.rate_limit_hits = limiter.hits
    return {
        "snapshot_rows": len(rows),
        "referentes_processed": stats.referentes_processed,
        "domains": sorted(stats.domains),
        "signals_unique": stats.signals_unique,
        "signals_duplicate": stats.signals_duplicate,
        "linkedin_skips": stats.linkedin_skips,
        "robots_disallow": stats.robots_disallow,
        "rate_limit_hits": stats.rate_limit_hits,
        "errors_by_status": stats.errors_by_status,
        "dry_run": dry_run,
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 1: discover signals from RSS/Web")
    p.add_argument("--sqlite", type=Path, required=True)
    p.add_argument("--canal", choices=("rss", "web", "all"), default="all")
    p.add_argument("--max-per-canal", type=int, default=None)
    p.add_argument("--min-interval", type=float, default=DEFAULT_MIN_INTERVAL_S)
    p.add_argument("--snapshot-max-age-hours", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )
    try:
        summary = run(
            sqlite_path=args.sqlite,
            canal=args.canal,
            max_per_canal=args.max_per_canal,
            min_interval=args.min_interval,
            snapshot_max_age_hours=args.snapshot_max_age_hours,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("stage1 failed: %s", exc)
        return 1
    import json
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
