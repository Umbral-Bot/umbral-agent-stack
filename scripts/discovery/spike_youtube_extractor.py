"""Spike 013-J: compare 3 YouTube content extraction strategies.

Read-only. Does NOT write SQLite. Does NOT call Notion API.

Usage:
    python -m scripts.discovery.spike_youtube_extractor \
        [--sqlite-ids 52,81,...] \
        [--output reports/spike-youtube-<TS>.json]

Default: all promoted youtube items in SQLite without notion_page_id.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([\w-]{11})")
CHANNEL_ID_RE = re.compile(r'"channelId":"(UC[\w-]{22})"')

DB_PATH = Path(os.path.expanduser("~/.cache/rick-discovery/state.sqlite"))


def parse_video_id(url: str) -> str | None:
    """Extract YouTube video id from watch?v=, youtu.be, or with extra params."""
    if not url:
        return None
    m = VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def _now_ms() -> int:
    return int(time.monotonic() * 1000)


def _try_yt_dlp(url: str, timeout_s: int = 30) -> dict[str, Any]:
    start = _now_ms()
    try:
        import yt_dlp  # type: ignore

        opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": timeout_s,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        title = info.get("title") or ""
        desc = info.get("description") or ""
        chapters = info.get("chapters") or []
        tags = info.get("tags") or []
        return {
            "ok": True,
            "title_len": len(title),
            "description_len": len(desc),
            "has_chapters": bool(chapters),
            "chapters_count": len(chapters),
            "tags_count": len(tags),
            "duration_seconds": info.get("duration"),
            "channel_id": info.get("channel_id"),
            "channel": info.get("channel"),
            "upload_date": info.get("upload_date"),
            "view_count": info.get("view_count"),
            "elapsed_ms": _now_ms() - start,
        }
    except Exception as exc:  # pragma: no cover - external service
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "elapsed_ms": _now_ms() - start,
        }


def _try_transcript(video_id: str, timeout_s: int = 30) -> dict[str, Any]:
    start = _now_ms()
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore

        api = YouTubeTranscriptApi()
        # API >= 1.0 uses .fetch(); older versions used static .get_transcript().
        try:
            fetched = api.fetch(video_id, languages=["es", "en"])
            segments = list(fetched)
            language = getattr(fetched, "language_code", None) or getattr(
                fetched, "language", None
            )
            is_auto = getattr(fetched, "is_generated", None)
        except AttributeError:
            segments = YouTubeTranscriptApi.get_transcript(  # type: ignore[attr-defined]
                video_id, languages=["es", "en"]
            )
            language = None
            is_auto = None

        # Normalize segment access (objects have .text; dicts use ['text']).
        chars = 0
        for seg in segments:
            t = getattr(seg, "text", None)
            if t is None and isinstance(seg, dict):
                t = seg.get("text", "")
            chars += len(t or "")
        return {
            "ok": True,
            "transcript_segments": len(segments),
            "transcript_chars": chars,
            "language": language,
            "is_auto": is_auto,
            "elapsed_ms": _now_ms() - start,
        }
    except Exception as exc:  # pragma: no cover - external service
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "elapsed_ms": _now_ms() - start,
        }


def _resolve_channel_id_from_watch(video_id: str, timeout_s: int = 30) -> tuple[str | None, str | None]:
    """Light HTTP fetch of the watch page to extract channelId via regex.

    Returns (channel_id, error). Used as alt3 fallback when alt1 (yt-dlp) is bot-blocked.
    """
    try:
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        r = httpx.get(
            watch_url,
            timeout=timeout_s,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        if r.status_code != 200:
            return None, f"watch page status {r.status_code}"
        m = CHANNEL_ID_RE.search(r.text)
        if not m:
            return None, "channelId not found in watch page HTML"
        return m.group(1), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"[:200]


def _try_atom(channel_id: str | None, video_id: str, timeout_s: int = 30) -> dict[str, Any]:
    start = _now_ms()
    resolved_via = "alt1"
    if not channel_id:
        channel_id, resolve_err = _resolve_channel_id_from_watch(video_id, timeout_s)
        resolved_via = "watch_html"
        if not channel_id:
            return {
                "ok": False,
                "error": f"no channel_id (alt1 missing; watch_html: {resolve_err})",
                "channel_id_resolved_via": "failed",
                "elapsed_ms": _now_ms() - start,
            }
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        r = httpx.get(url, timeout=timeout_s, follow_redirects=True)
        r.raise_for_status()
        body = r.text
        # Find the entry with our video_id.
        m = re.search(
            rf"<entry>(?:(?!</entry>).)*?<yt:videoId>{re.escape(video_id)}</yt:videoId>(?:(?!</entry>).)*?</entry>",
            body,
            re.DOTALL,
        )
        if not m:
            return {
                "ok": False,
                "error": "video_id not found in atom feed (may be older than feed window)",
                "feed_status": r.status_code,
                "feed_bytes": len(body),
                "elapsed_ms": _now_ms() - start,
            }
        entry = m.group(0)
        desc_m = re.search(
            r"<media:description>(.*?)</media:description>", entry, re.DOTALL
        )
        desc = desc_m.group(1) if desc_m else ""
        return {
            "ok": True,
            "description_len": len(desc),
            "feed_bytes": len(body),
            "channel_id_resolved_via": resolved_via,
            "channel_id": channel_id,
            "elapsed_ms": _now_ms() - start,
        }
    except Exception as exc:  # pragma: no cover - external service
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "elapsed_ms": _now_ms() - start,
        }


def _load_targets(sqlite_ids: list[int] | None) -> list[dict[str, Any]]:
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    if sqlite_ids:
        placeholders = ",".join("?" * len(sqlite_ids))
        rows = con.execute(
            f"SELECT rowid, url_canonica, referente_id, canal, titulo "
            f"FROM discovered_items WHERE rowid IN ({placeholders})",
            sqlite_ids,
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT rowid, url_canonica, referente_id, canal, titulo "
            "FROM discovered_items "
            "WHERE promovido_a_candidato_at IS NOT NULL "
            "AND notion_page_id IS NULL "
            "AND canal='youtube' "
            "ORDER BY rowid"
        ).fetchall()
    return [dict(r) for r in rows]


def _summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(items)

    def _ok(key: str) -> int:
        return sum(1 for it in items if it.get(key, {}).get("ok"))

    def _avg_ms(key: str) -> float | None:
        vals = [it[key]["elapsed_ms"] for it in items if it.get(key, {}).get("elapsed_ms") is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    def _coverage_desc_500(key: str) -> int:
        return sum(
            1
            for it in items
            if it.get(key, {}).get("ok") and (it[key].get("description_len") or 0) > 500
        )

    transcript_1000 = sum(
        1
        for it in items
        if it.get("alt2_transcript", {}).get("ok")
        and (it["alt2_transcript"].get("transcript_chars") or 0) > 1000
    )

    return {
        "total_items": n,
        "alt1_yt_dlp": {
            "ok_count": _ok("alt1_yt_dlp"),
            "avg_elapsed_ms": _avg_ms("alt1_yt_dlp"),
            "description_len_gt_500": _coverage_desc_500("alt1_yt_dlp"),
        },
        "alt2_transcript": {
            "ok_count": _ok("alt2_transcript"),
            "avg_elapsed_ms": _avg_ms("alt2_transcript"),
            "transcript_chars_gt_1000": transcript_1000,
        },
        "alt3_atom": {
            "ok_count": _ok("alt3_atom"),
            "avg_elapsed_ms": _avg_ms("alt3_atom"),
            "description_len_gt_500": _coverage_desc_500("alt3_atom"),
        },
    }


def _recommendation(summary: dict[str, Any]) -> str:
    n = summary["total_items"]
    a1 = summary["alt1_yt_dlp"]
    a2 = summary["alt2_transcript"]
    a3 = summary["alt3_atom"]
    a1_ok_pct = a1["ok_count"] / n * 100 if n else 0
    a2_ok_pct = a2["ok_count"] / n * 100 if n else 0
    a3_ok_pct = a3["ok_count"] / n * 100 if n else 0
    a2_useful_pct = a2["transcript_chars_gt_1000"] / n * 100 if n else 0
    a1_useful_pct = a1["description_len_gt_500"] / n * 100 if n else 0

    lines = [
        f"Sample: {n} videos.",
        f"alt1 (yt-dlp): ok={a1_ok_pct:.0f}%, useful_desc(>500c)={a1_useful_pct:.0f}%, "
        f"avg={a1['avg_elapsed_ms']} ms.",
        f"alt2 (transcript): ok={a2_ok_pct:.0f}%, useful(>1000c)={a2_useful_pct:.0f}%, "
        f"avg={a2['avg_elapsed_ms']} ms.",
        f"alt3 (atom): ok={a3_ok_pct:.0f}%, avg={a3['avg_elapsed_ms']} ms.",
        "",
    ]
    # Decision tree from spec hypothesis.
    if a2_ok_pct >= 50 and a1_ok_pct >= 75:
        rec = (
            "RECOMENDACIÓN: alt1 + alt2 combinadas. yt-dlp aporta metadata estructurada "
            "(title, description, chapters, channel, duration) y youtube-transcript-api "
            "aporta el cuerpo full-text del video como transcript. Stage 2 adapter debe "
            "renderizar: (1) descripción de yt-dlp si description_len>200 como párrafo, "
            "(2) chapters como lista bulleted con timestamps si has_chapters, "
            "(3) transcript como sección 'Transcripción automática' (toggle/quote) si "
            "alt2.ok. Si alt2 falla para un video puntual, dejar solo metadata de alt1."
        )
    elif a1_ok_pct >= 75:
        rec = (
            "RECOMENDACIÓN: alt1 solo. youtube-transcript-api no llega a cobertura útil "
            ">=50%. Adapter Stage 2 con metadata yt-dlp (description + chapters + tags) "
            "es suficiente para evitar created_no_body. Considerar alt2 como opt-in por "
            "video más adelante."
        )
    elif a3_ok_pct >= 75:
        rec = (
            "RECOMENDACIÓN: fallback a alt3 (atom feed). yt-dlp falla en >25% de los "
            "videos (probable bloqueo geográfico, anti-bot, o videos privados). atom "
            "feed oficial entrega descripción corta pero estable. Adapter Stage 2 con "
            "title+desc del feed evita created_no_body aunque con cuerpo limitado."
        )
    else:
        rec = (
            "RECOMENDACIÓN: NINGUNA alternativa supera 75% de éxito. Revisar bloqueos "
            "(IP de la VPS contra anti-bot YouTube, cookies, captcha). Considerar proxy "
            "o degradar Stage 2 a stub permanente para canal=youtube hasta resolver."
        )
    lines.append(rec)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite-ids", default="", help="Comma-separated rowids; default = all promoted youtube without page_id")
    ap.add_argument(
        "--output",
        default=f"reports/spike-youtube-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json",
    )
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args(argv)

    sqlite_ids = (
        [int(x) for x in args.sqlite_ids.split(",") if x.strip()]
        if args.sqlite_ids
        else None
    )
    targets = _load_targets(sqlite_ids)
    if not targets:
        print("No targets found.", file=sys.stderr)
        return 1

    started = datetime.now(timezone.utc).isoformat()
    items: list[dict[str, Any]] = []
    for t in targets:
        url = t["url_canonica"]
        vid = parse_video_id(url)
        print(f"  [{t['rowid']}] {vid} ...", flush=True)
        item: dict[str, Any] = {
            "sqlite_id": t["rowid"],
            "video_id": vid,
            "url": url,
            "referente_id": t["referente_id"],
            "titulo": t["titulo"],
        }
        if not vid:
            item["error"] = "could not parse video_id from url"
            items.append(item)
            continue
        a1 = _try_yt_dlp(url, args.timeout)
        item["alt1_yt_dlp"] = a1
        a2 = _try_transcript(vid, args.timeout)
        item["alt2_transcript"] = a2
        channel_id = a1.get("channel_id") if a1.get("ok") else None
        a3 = _try_atom(channel_id, vid, args.timeout)
        item["alt3_atom"] = a3
        items.append(item)

    finished = datetime.now(timezone.utc).isoformat()
    summary = _summarize(items)
    report = {
        "started": started,
        "finished": finished,
        "summary": summary,
        "recommendation": _recommendation(summary),
        "items": items,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    out_path.write_text(payload)
    # Backup copy outside the worktree to survive concurrent automation cleanups.
    try:
        Path(f"/tmp/{out_path.name}").write_text(payload)
    except Exception:
        pass
    print(json.dumps(summary, indent=2))
    print()
    print(report["recommendation"])
    print(f"\nReport: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
