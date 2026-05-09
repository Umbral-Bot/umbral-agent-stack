#!/usr/bin/env python3
"""Stage 2 — Source verification & dedup (Hilo 3 / wave1).

Reads a batch of unverified rows from ``signals_raw`` (Hilo 2 owned),
performs an HTTP HEAD (with GET fallback) probe, resolves the canonical
URL, classifies ``source_status``, computes ``content_hash`` and
``idempotency_key``, and persists the verdict to ``signals_verified``.

This stage runs **before** scoring (S5) and is the single source of
truth for "is this URL real, alive, dedup-able" inside the editorial
pipeline. It does NOT touch Notion, does NOT call any LLM, and does NOT
publish anything.

Stage 2's ``source_status`` enum is **richer** than Hilo 2's (which is
the ingest-time fetch status) and lives in its own table to avoid any
collision with the read side of `signals_raw`.

Reads:
    signals_raw(signal_id INTEGER PK AUTOINCREMENT, url TEXT,
                title TEXT, excerpt TEXT, ...)  — Hilo 2 owns this.

Writes:
    signals_verified(signal_id INTEGER PK,
                     canonical_url TEXT NOT NULL,
                     source_status TEXT NOT NULL,
                     content_hash TEXT NOT NULL,
                     idempotency_key TEXT NOT NULL,
                     paywall_detected INTEGER NOT NULL DEFAULT 0,
                     verified_at TEXT NOT NULL,
                     http_status INTEGER, final_url TEXT, error TEXT)

CLI
---
::

    python -m scripts.discovery.stage2_verify_sources \
        --dry-run --batch 5 --verbose

Status mapping
--------------
====================  =============================================
``source_status``     condition
====================  =============================================
``ok``                final response 2xx, no redirect across hosts
``redirect``          followed redirect to a different canonical URL
``404``               final response 404
``410``               final response 410
``paywall``           HTTP 402, paywall keywords, or thin body (<500 chars)
``timeout``           transport timeout after retries
``blocked``           4xx other than 404/410, 5xx, malformed URL, etc.
====================  =============================================
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import httpx

from scripts.discovery.lib.dedup import (
    compute_content_hash,
    compute_idempotency_key,
)

DEFAULT_DB = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_BATCH = 50
HTTP_TIMEOUT_S = 10.0
HTTP_RETRY_BACKOFFS_S = (1.0, 3.0)
USER_AGENT = "umbral-stage2-verify/1.0 (+https://umbral.bot)"

# Stage-2-status values we will re-probe under --retry-failed.
RETRY_STATUSES = ("timeout", "blocked")

# Default paywall keywords. Conservative; meant to flag, not to gatekeep.
DEFAULT_PAYWALL_KEYWORDS = (
    "paywall",
    "subscribe to read",
    "subscribe to continue",
    "members only",
    "for subscribers only",
    "inicia sesi\u00f3n para continuar",
    "suscr\u00edbete para continuar",
    "este art\u00edculo es exclusivo",
)

PAYWALL_MIN_BODY_CHARS = 500

_CANONICAL_RE = re.compile(
    r"<link[^>]+rel=[\"']canonical[\"'][^>]*href=[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


# --------------------------------------------------------------------------- #
# Schema bootstrap
# --------------------------------------------------------------------------- #

SIGNALS_VERIFIED_DDL = """
CREATE TABLE IF NOT EXISTS signals_verified (
    signal_id        INTEGER PRIMARY KEY,
    canonical_url    TEXT NOT NULL,
    source_status    TEXT NOT NULL,
    content_hash     TEXT NOT NULL,
    idempotency_key  TEXT NOT NULL,
    paywall_detected INTEGER NOT NULL DEFAULT 0,
    verified_at      TEXT NOT NULL,
    http_status      INTEGER,
    final_url        TEXT,
    error            TEXT
);
CREATE INDEX IF NOT EXISTS idx_signals_verified_content_hash
    ON signals_verified(content_hash);
CREATE INDEX IF NOT EXISTS idx_signals_verified_idempotency_key
    ON signals_verified(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_signals_verified_status
    ON signals_verified(source_status);
"""

# Minimal signals_raw shape used as a safety net when 0001 has not been
# applied yet (e.g. test DBs). We never DROP an existing table.
SIGNALS_RAW_FALLBACK_DDL = """
CREATE TABLE IF NOT EXISTS signals_raw (
    signal_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT,
    title         TEXT,
    excerpt       TEXT,
    canonical_url TEXT,
    source_status TEXT
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SIGNALS_VERIFIED_DDL)
    conn.executescript(SIGNALS_RAW_FALLBACK_DDL)
    conn.commit()


# --------------------------------------------------------------------------- #
# Verdict structure
# --------------------------------------------------------------------------- #

@dataclass
class Verdict:
    signal_id: int
    canonical_url: str
    source_status: str
    content_hash: str
    idempotency_key: str
    paywall_detected: bool
    verified_at: str
    http_status: int | None
    final_url: str
    error: str

    def to_row(self) -> tuple:
        return (
            self.signal_id,
            self.canonical_url,
            self.source_status,
            self.content_hash,
            self.idempotency_key,
            1 if self.paywall_detected else 0,
            self.verified_at,
            self.http_status,
            self.final_url,
            self.error,
        )

    def to_json(self) -> str:
        d = {
            "signal_id": self.signal_id,
            "canonical_url": self.canonical_url,
            "source_status": self.source_status,
            "content_hash": self.content_hash,
            "idempotency_key": self.idempotency_key,
            "paywall_detected": self.paywall_detected,
            "verified_at": self.verified_at,
            "http_status": self.http_status,
            "final_url": self.final_url,
            "error": self.error,
        }
        return json.dumps(d, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Probe
# --------------------------------------------------------------------------- #

@dataclass
class _Probe:
    status_code: int | None
    final_url: str
    body_text: str
    content_type: str
    error: str
    transport_failed: bool


def _http_probe(
    url: str,
    *,
    client: httpx.Client,
    timeout_s: float = HTTP_TIMEOUT_S,
    backoffs: tuple[float, ...] = HTTP_RETRY_BACKOFFS_S,
    sleep=time.sleep,
) -> _Probe:
    """HEAD-first probe with GET fallback and 2-step backoff retry on transport error."""
    last_err = ""
    attempts = len(backoffs) + 1
    for attempt in range(attempts):
        try:
            try:
                resp = client.head(url, timeout=timeout_s)
            except httpx.TimeoutException:
                raise
            except httpx.HTTPError:
                resp = client.get(url, timeout=timeout_s)
            else:
                if resp.status_code in (405, 403, 501):
                    resp = client.get(url, timeout=timeout_s)
                else:
                    ct_head = (resp.headers.get("content-type") or "").lower()
                    if 200 <= resp.status_code < 400 and ct_head.startswith("text/"):
                        resp = client.get(url, timeout=timeout_s)
            ct = (resp.headers.get("content-type") or "").lower()
            try:
                body = resp.text if resp.content else ""
            except Exception:
                body = ""
            return _Probe(
                status_code=resp.status_code,
                final_url=str(resp.url),
                body_text=body or "",
                content_type=ct,
                error="",
                transport_failed=False,
            )
        except httpx.TimeoutException as e:
            last_err = f"timeout:{type(e).__name__}"
            if attempt < attempts - 1:
                sleep(backoffs[attempt])
                continue
            return _Probe(None, url, "", "", last_err, transport_failed=True)
        except httpx.HTTPError as e:
            last_err = f"transport:{type(e).__name__}:{e!s:.120s}"
            if attempt < attempts - 1:
                sleep(backoffs[attempt])
                continue
            return _Probe(None, url, "", "", last_err, transport_failed=True)
    return _Probe(None, url, "", "", last_err or "unknown", transport_failed=True)


# --------------------------------------------------------------------------- #
# Canonical / paywall extraction
# --------------------------------------------------------------------------- #


def _extract_canonical(html: str, fallback_url: str) -> str:
    if not html:
        return fallback_url
    m = _CANONICAL_RE.search(html)
    if not m:
        return fallback_url
    href = (m.group(1) or "").strip()
    if not href:
        return fallback_url
    parsed = urlparse(href)
    if parsed.scheme in ("http", "https") and parsed.hostname:
        return href
    return fallback_url


def _visible_text_chars(html: str) -> int:
    if not html:
        return 0
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = _TAG_RE.sub(" ", cleaned)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text)


def _detect_paywall(
    *,
    status_code: int | None,
    body_text: str,
    paywall_keywords: Iterable[str] = DEFAULT_PAYWALL_KEYWORDS,
    min_body_chars: int = PAYWALL_MIN_BODY_CHARS,
) -> bool:
    if status_code == 402:
        return True
    if not body_text:
        return False
    lower = body_text.lower()
    for kw in paywall_keywords:
        if kw and kw.lower() in lower:
            return True
    if _visible_text_chars(body_text) < min_body_chars:
        return True
    return False


# --------------------------------------------------------------------------- #
# Verdict builder
# --------------------------------------------------------------------------- #


def _classify(probe: _Probe, original_url: str) -> tuple[str, bool]:
    """Return ``(source_status, paywall_detected)``."""
    if probe.transport_failed:
        if probe.error.startswith("timeout"):
            return "timeout", False
        return "blocked", False
    sc = probe.status_code
    if sc is None:
        return "blocked", False
    if sc == 402:
        return "paywall", True
    if sc == 404:
        return "404", False
    if sc == 410:
        return "410", False
    if 400 <= sc < 600:
        return "blocked", False
    if 200 <= sc < 400:
        if _detect_paywall(status_code=sc, body_text=probe.body_text):
            return "paywall", True
        try:
            orig_host = (urlparse(original_url).hostname or "").lower()
            final_host = (urlparse(probe.final_url).hostname or "").lower()
        except Exception:
            orig_host = final_host = ""
        if orig_host and final_host and orig_host != final_host:
            return "redirect", False
        return "ok", False
    return "blocked", False


def verify_signal(
    signal_id: int,
    source_url: str,
    title: str,
    excerpt: str,
    *,
    client: httpx.Client,
    now=None,
) -> Verdict:
    """Probe ``source_url`` and build the full ``Verdict``."""
    now_fn = now or (lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    url = (source_url or "").strip()

    if not url or urlparse(url).scheme not in ("http", "https"):
        canonical = url
        ch = compute_content_hash(canonical, title or "", excerpt or "")
        return Verdict(
            signal_id=signal_id,
            canonical_url=canonical,
            source_status="blocked",
            content_hash=ch,
            idempotency_key=compute_idempotency_key(canonical, ch),
            paywall_detected=False,
            verified_at=now_fn(),
            http_status=None,
            final_url="",
            error="malformed_url",
        )

    probe = _http_probe(url, client=client)
    canonical = _extract_canonical(probe.body_text, probe.final_url or url)
    status, paywall = _classify(probe, url)

    ch = compute_content_hash(canonical, title or "", excerpt or "")
    ik = compute_idempotency_key(canonical, ch)
    return Verdict(
        signal_id=signal_id,
        canonical_url=canonical,
        source_status=status,
        content_hash=ch,
        idempotency_key=ik,
        paywall_detected=paywall,
        verified_at=now_fn(),
        http_status=probe.status_code,
        final_url=probe.final_url,
        error=probe.error,
    )


# --------------------------------------------------------------------------- #
# DB I/O
# --------------------------------------------------------------------------- #


def fetch_unverified(
    conn: sqlite3.Connection,
    *,
    batch: int,
    retry_failed: bool,
) -> list[tuple]:
    """Return ``[(signal_id, url, title, excerpt), ...]`` rows to verify.

    Pulls from ``signals_raw`` rows that either have no row in
    ``signals_verified`` yet, or — when ``retry_failed`` is True — already
    have a verdict in ``RETRY_STATUSES``.

    Tolerates schemas where columns ``title`` / ``excerpt`` are missing.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signals_raw)")}
    if not cols or "signal_id" not in cols:
        return []
    if "url" in cols:
        url_col = "r.url"
    elif "source_url" in cols:
        url_col = "r.source_url"
    else:
        return []
    title_col = "COALESCE(r.title, '')" if "title" in cols else "''"
    excerpt_col = "COALESCE(r.excerpt, '')" if "excerpt" in cols else "''"

    placeholders = ",".join("?" * len(RETRY_STATUSES))
    retry_clause = (
        f"v.source_status IN ({placeholders})" if retry_failed else "0"
    )
    sql = f"""
        SELECT r.signal_id, {url_col}, {title_col}, {excerpt_col}
          FROM signals_raw r
          LEFT JOIN signals_verified v ON v.signal_id = r.signal_id
         WHERE v.signal_id IS NULL OR ({retry_clause})
         LIMIT ?
    """
    params: list = []
    if retry_failed:
        params.extend(RETRY_STATUSES)
    params.append(int(batch))
    return [tuple(row) for row in conn.execute(sql, params).fetchall()]


def upsert_verdict(conn: sqlite3.Connection, v: Verdict) -> None:
    conn.execute(
        """
        INSERT INTO signals_verified
            (signal_id, canonical_url, source_status, content_hash,
             idempotency_key, paywall_detected, verified_at, http_status,
             final_url, error)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(signal_id) DO UPDATE SET
            canonical_url    = excluded.canonical_url,
            source_status    = excluded.source_status,
            content_hash     = excluded.content_hash,
            idempotency_key  = excluded.idempotency_key,
            paywall_detected = excluded.paywall_detected,
            verified_at      = excluded.verified_at,
            http_status      = excluded.http_status,
            final_url        = excluded.final_url,
            error            = excluded.error
        """,
        v.to_row(),
    )
    conn.commit()


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def run(
    *,
    conn: sqlite3.Connection,
    client: httpx.Client,
    batch: int = DEFAULT_BATCH,
    retry_failed: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    out_stream=sys.stdout,
) -> list[Verdict]:
    ensure_schema(conn)
    rows = fetch_unverified(conn, batch=batch, retry_failed=retry_failed)
    verdicts: list[Verdict] = []
    for signal_id, url, title, excerpt in rows:
        v = verify_signal(signal_id, url or "", title or "", excerpt or "", client=client)
        if not dry_run:
            upsert_verdict(conn, v)
        if verbose:
            print(v.to_json(), file=out_stream)
        verdicts.append(v)
    return verdicts


def _build_client(timeout_s: float = HTTP_TIMEOUT_S) -> httpx.Client:
    return httpx.Client(
        timeout=timeout_s,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stage 2 — verify sources & dedup.")
    p.add_argument("--db", default=str(DEFAULT_DB), help="Discovery state SQLite path.")
    p.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="Max rows per run.")
    p.add_argument("--dry-run", action="store_true", help="Probe but do not persist.")
    p.add_argument("--retry-failed", action="store_true",
                   help="Re-process timeout/blocked rows.")
    p.add_argument("--verbose", action="store_true", help="Emit one JSON line per verdict.")
    args = p.parse_args(argv)

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        with _build_client() as client:
            verdicts = run(
                conn=conn,
                client=client,
                batch=args.batch,
                retry_failed=args.retry_failed,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
    finally:
        conn.close()
    summary = {
        "processed": len(verdicts),
        "by_status": {},
        "paywalls": sum(1 for v in verdicts if v.paywall_detected),
        "dry_run": args.dry_run,
    }
    for v in verdicts:
        summary["by_status"][v.source_status] = summary["by_status"].get(v.source_status, 0) + 1
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
