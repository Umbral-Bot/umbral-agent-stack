#!/usr/bin/env python3
"""Diagnose why backfill of contenido_html only matched 1/20 promoted items.

For each promoted-but-uncaptured row, re-fetch the referente's feed(s) and
compare the SQLite ``url_canonica`` against every feed entry's URL under
several normalization strategies:

- exact: feed url string == sqlite url_canonica
- canonicalize_url: stage2's current canonicalize_url applied to feed url
- loose: lowercase, drop scheme, drop ``www.``, strip trailing ``/``, drop
  ``utm_*``/``fbclid``/``gclid``/``ref``/``mc_*``, drop fragment

Pure read-only. No DB writes, no Notion writes. Token only used in headers.
Outputs ``reports/diagnose-backfill-url-match-<ts>.json`` plus a human table
to stdout.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from scripts.discovery.stage2_ingest import (
    DEFAULT_NOTION_API_VERSION,
    canonicalize_url,
    fetch_referentes,
    get_runtime_notion_api_key,
    is_direct_rss_candidate,
    load_registry,
    normalize_referente,
    parse_feed_xml,
    parse_youtube_channel_id,
)

DEFAULT_SQLITE_PATH = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_REGISTRY_PATH = Path("vendor/notion-governance/registry/notion-data-sources.template.yaml")
DEFAULT_RSSHUB_BASE = "http://127.0.0.1:1200"
DEFAULT_REPORTS_DIR = Path("reports")

LOOSE_TRACKING_PREFIXES = ("utm_", "mc_")
LOOSE_TRACKING_EXACT = {"fbclid", "gclid", "ref", "mc_cid", "mc_eid"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def loose_normalize(url: str) -> str:
    """Aggressive normalization for fuzzy comparison only — never persisted."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = (parsed.path or "")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    cleaned = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=False):
        kl = k.lower()
        if kl in LOOSE_TRACKING_EXACT:
            continue
        if any(kl.startswith(p) for p in LOOSE_TRACKING_PREFIXES):
            continue
        cleaned.append((k, v))
    query = urlencode(cleaned)
    # Drop scheme + fragment for the loose key.
    return urlunparse(("", netloc, path, parsed.params, query, ""))


def basename_of(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    path = (parsed.path or "/").rstrip("/")
    if not path:
        return ""
    return path.rsplit("/", 1)[-1]


def select_pending(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT rowid, url_canonica, referente_id, referente_nombre, canal, titulo "
        "FROM discovered_items "
        "WHERE promovido_a_candidato_at IS NOT NULL AND contenido_html IS NULL "
        "ORDER BY rowid"
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def fetch_feed_urls(client: httpx.Client, url: str | None) -> list[dict[str, Any]]:
    """Return list of {url, titulo} for a single feed; empty on any error."""
    if not url:
        return []
    try:
        r = client.get(url, timeout=20.0, follow_redirects=True)
        if r.status_code >= 400:
            return [{"_error": f"HTTP {r.status_code}", "url": None}]
        items = parse_feed_xml(r.text)
    except Exception as exc:  # noqa: BLE001
        return [{"_error": f"{exc.__class__.__name__}: {exc}", "url": None}]
    return [
        {
            "url": (it.get("url") or "").strip(),
            "titulo": (it.get("titulo") or "")[:80],
        }
        for it in items
        if (it.get("url") or "").strip()
    ]


def referente_feed_urls(
    ref, *, rsshub_base: str
) -> list[tuple[str, str]]:
    """Return list of (channel_label, fetch_url) to probe for a referente."""
    out: list[tuple[str, str]] = []
    if ref.rss_url:
        out.append(("rss", ref.rss_url))
    if ref.web_url:
        if is_direct_rss_candidate(ref.web_url):
            out.append(("web_rss", ref.web_url))
        yt = parse_youtube_channel_id(ref.web_url)
        if yt:
            ident, kind = yt
            if kind == "channel":
                out.append(("youtube", f"{rsshub_base}/youtube/channel/{ident}"))
            elif kind == "user":
                out.append(("youtube", f"{rsshub_base}/youtube/user/{ident}"))
            elif kind == "c":
                out.append(("youtube", f"{rsshub_base}/youtube/c/{ident}"))
            elif kind == "handle":
                out.append(("youtube", f"{rsshub_base}/youtube/user/@{ident}"))
    if ref.youtube_url:
        yt = parse_youtube_channel_id(ref.youtube_url)
        if yt:
            ident, kind = yt
            if kind == "channel":
                out.append(("youtube", f"{rsshub_base}/youtube/channel/{ident}"))
    return out


def diagnose(
    *,
    sqlite_path: Path,
    registry_path: Path,
    rsshub_base: str,
    reports_dir: Path,
) -> dict[str, Any]:
    conn = sqlite3.connect(str(sqlite_path))
    pending = select_pending(conn)

    summary: dict[str, Any] = {
        "started": _now_iso(),
        "pending_total": len(pending),
        "match_counts": {
            "exact": 0,
            "canonical": 0,
            "loose": 0,
            "basename_only": 0,
            "no_match": 0,
        },
        "rows": [],
    }
    if not pending:
        summary["finished"] = _now_iso()
        return _persist(summary, reports_dir)

    api_key = get_runtime_notion_api_key()
    registry = load_registry(registry_path)
    raw = fetch_referentes(
        data_source_id=registry["data_source_id"],
        api_key=api_key,
        api_version=DEFAULT_NOTION_API_VERSION,
    )
    referentes = {r.id: r for r in (normalize_referente(row) for row in raw)}

    pending_by_ref: dict[str, list[dict[str, Any]]] = {}
    for row in pending:
        pending_by_ref.setdefault(row["referente_id"], []).append(row)

    feed_cache: dict[str, list[dict[str, Any]]] = {}

    with httpx.Client(headers={"User-Agent": "umbral-013g-diagnose/1.0"}) as client:
        for ref_id, rows in pending_by_ref.items():
            ref = referentes.get(ref_id)
            ref_label = ref.nombre if ref else f"<missing:{ref_id}>"
            channels: list[tuple[str, str]] = []
            if ref is not None:
                channels = referente_feed_urls(ref, rsshub_base=rsshub_base)

            # Aggregate candidates across all channels for this referente.
            feed_items: list[dict[str, Any]] = []
            for label, url in channels:
                key = f"{label}|{url}"
                if key not in feed_cache:
                    feed_cache[key] = fetch_feed_urls(client, url)
                for it in feed_cache[key]:
                    if it.get("_error"):
                        feed_items.append({"_error": it["_error"], "channel": label})
                    elif it.get("url"):
                        feed_items.append({**it, "channel": label})

            for row in rows:
                sqlite_url = row["url_canonica"]
                sqlite_loose = loose_normalize(sqlite_url)
                sqlite_basename = basename_of(sqlite_url)
                same_basename: list[dict[str, Any]] = []
                exact_hit = canon_hit = loose_hit = None
                for it in feed_items:
                    if it.get("_error"):
                        continue
                    feed_url = it["url"]
                    if feed_url == sqlite_url:
                        exact_hit = feed_url
                    if canonicalize_url(feed_url) == sqlite_url:
                        canon_hit = feed_url
                    if loose_normalize(feed_url) == sqlite_loose:
                        loose_hit = feed_url
                    if basename_of(feed_url) == sqlite_basename and sqlite_basename:
                        same_basename.append(
                            {"feed_url": feed_url, "channel": it.get("channel")}
                        )

                if exact_hit:
                    bucket = "exact"
                elif canon_hit:
                    bucket = "canonical"
                elif loose_hit:
                    bucket = "loose"
                elif same_basename:
                    bucket = "basename_only"
                else:
                    bucket = "no_match"
                summary["match_counts"][bucket] += 1

                summary["rows"].append({
                    "sqlite_id": row["rowid"],
                    "referente": ref_label,
                    "canal": row["canal"],
                    "titulo": (row["titulo"] or "")[:80],
                    "sqlite_url_canonica": sqlite_url,
                    "match_bucket": bucket,
                    "exact_hit": exact_hit,
                    "canonical_hit": canon_hit,
                    "loose_hit": loose_hit,
                    "same_basename_in_feed": same_basename[:5],
                    "feed_items_total": sum(
                        1 for it in feed_items if not it.get("_error")
                    ),
                    "feed_errors": [
                        it["_error"] for it in feed_items if it.get("_error")
                    ],
                })

    summary["finished"] = _now_iso()
    return _persist(summary, reports_dir)


def _persist(summary: dict[str, Any], reports_dir: Path) -> dict[str, Any]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"diagnose-backfill-url-match-{_now_ts()}.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    summary["_report_path"] = str(path)
    return summary


def print_table(summary: dict[str, Any]) -> None:
    print(f"\n=== Diagnose backfill URL match ({summary['started']}) ===")
    print(f"Pending total: {summary['pending_total']}")
    print(f"Match counts:  {summary['match_counts']}")
    print(f"Report:        {summary.get('_report_path')}\n")
    print(f"{'id':>4}  {'bucket':<14} {'referente':<22} {'canal':<10} url")
    print("-" * 110)
    for row in summary["rows"]:
        print(
            f"{row['sqlite_id']:>4}  {row['match_bucket']:<14} "
            f"{row['referente'][:22]:<22} {row['canal']:<10} {row['sqlite_url_canonica'][:60]}"
        )
        if row["match_bucket"] == "basename_only" and row["same_basename_in_feed"]:
            for hit in row["same_basename_in_feed"][:1]:
                print(f"      ↳ feed has same basename: {hit['feed_url'][:80]} ({hit['channel']})")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Diagnose backfill URL matching.")
    p.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE_PATH)
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    p.add_argument("--rsshub-base", default=DEFAULT_RSSHUB_BASE)
    p.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    summary = diagnose(
        sqlite_path=args.sqlite,
        registry_path=args.registry,
        rsshub_base=args.rsshub_base,
        reports_dir=args.reports_dir,
    )
    print_table(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
