"""YouTube Data API v3 extractor for canal=youtube items.

Stage 2 / backfill helper that resolves a YouTube ``video_id`` into structured
metadata via ``GET https://www.googleapis.com/youtube/v3/videos`` with parts
``snippet,contentDetails,statistics``.

Decision rationale (spike 013-K, PR #342, reports
``reports/spike-youtube-vm-dataapi-20260507T1{43958,44115}Z.{json,md}``):

* VIA A (residential-IP probe via VM ``browser.navigate``) was invalidated:
  100% of requests redirected to ``google.com/sorry/index?...`` reCAPTCHA wall
  (the VM IP is also flagged by Google).
* VIA B (this module) achieved 8/8 individual coverage, 7/8 in batch with a
  single intermittent ``HTTP 400 "API key expired"`` flake per run that
  succeeds on a single retry. The retry-once policy below absorbs this flake.

Captions / transcript are intentionally NOT covered in v1: ``captions.list`` is
available but ``captions.download`` requires OAuth2 scope
``youtube.force-ssl`` (not API-key auth), and Stage 2 v1 only needs
``description`` (>500 chars in 7/8 of the spike sample) to defeat the
``created_no_body`` guard in ``stage4_push_notion.py``.

The API key is read from ``YOUTUBE_DATA_API_KEY``. Never hardcode it.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

YOUTUBE_VIDEOS_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"
DEFAULT_PARTS = "snippet,contentDetails,statistics"
DEFAULT_TIMEOUT_S = 15.0
RETRY_BACKOFF_S = 1.0
MAX_RETRIES = 1  # spike 013-K: 1 retry absorbs the Google-side flake.

# Heuristic markers for the engaño-flake "API key expired" 400 we saw on the
# spike. We retry only on these; on any other 4xx we fail fast.
_RETRYABLE_400_MARKERS = ("api key expired", "api_key_invalid")

# ISO 8601 duration parser — YouTube emits ``PT#H#M#S`` for videos.
_ISO_DURATION_RE = re.compile(
    r"^P"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?"
    r")?$"
)

# Chapter line: "0:00 Intro", "1:23 Setup", "1:02:33 Q&A".
# Anchored to start of line (multiline mode is applied at use site).
_CHAPTER_LINE_RE = re.compile(
    r"^(?P<ts>\d{1,2}(?::\d{2}){1,2})[\s\u00a0\-\u2013\u2014:]+(?P<title>\S.*?)\s*$"
)


class YoutubeExtractionError(RuntimeError):
    """Network or API error talking to YouTube Data API v3."""


class YoutubeVideoNotFound(YoutubeExtractionError):
    """Endpoint returned 200 with empty ``items`` for the given id."""


class YoutubeApiKeyMissing(YoutubeExtractionError):
    """``YOUTUBE_DATA_API_KEY`` env var is not set."""


@dataclass
class YoutubeExtractionResult:
    video_id: str
    title: str
    description: str
    published_at: datetime | None
    channel_id: str
    channel_title: str
    duration_seconds: int
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    tags: list[str] = field(default_factory=list)
    category_id: str | None = None
    chapters: list[dict[str, Any]] | None = None


# ---------- Pure helpers (testable without HTTP) ----------

def _parse_iso_duration(iso: str | None) -> int:
    """Parse ISO 8601 video duration (``PT1H4M56S``) → seconds.

    Returns 0 for ``None`` / empty / unparseable input. Live streams return
    ``"P0D"`` from the API; treat those as 0.
    """
    if not iso:
        return 0
    m = _ISO_DURATION_RE.match(iso.strip())
    if not m:
        return 0
    days = int(m.group("days") or 0)
    hours = int(m.group("hours") or 0)
    minutes = int(m.group("minutes") or 0)
    seconds = int(m.group("seconds") or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _ts_to_seconds(ts: str) -> int | None:
    """``"1:02:33"`` → 3753, ``"0:42"`` → 42. Returns None on bad input."""
    parts = ts.split(":")
    if not 2 <= len(parts) <= 3:
        return None
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        h, m, s = 0, nums[0], nums[1]
    else:
        h, m, s = nums
    if any(n < 0 for n in (h, m, s)) or m >= 60 or s >= 60:
        return None
    return h * 3600 + m * 60 + s


def _parse_chapters_from_description(description: str | None) -> list[dict[str, Any]] | None:
    """Best-effort chapter extraction from a video description.

    Looks for lines that start with a timestamp (``M:SS`` or ``H:MM:SS``)
    followed by a separator and a title. Returns ``None`` if fewer than 2
    timestamped lines are found (YouTube requires the first chapter to start
    at ``0:00`` and at least 3 chapters to render its UI; we keep the parsing
    permissive and let consumers decide).
    """
    if not description:
        return None
    out: list[dict[str, Any]] = []
    for line in description.splitlines():
        m = _CHAPTER_LINE_RE.match(line.strip())
        if not m:
            continue
        secs = _ts_to_seconds(m.group("ts"))
        if secs is None:
            continue
        title = m.group("title").strip()
        if not title:
            continue
        out.append({"start_seconds": secs, "title": title})
    if len(out) < 2:
        return None
    return out


def _is_retryable_400(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    err = payload.get("error") or {}
    msg = (err.get("message") or "").lower()
    if any(marker in msg for marker in _RETRYABLE_400_MARKERS):
        return True
    for sub in err.get("errors", []) or []:
        if isinstance(sub, dict):
            if any(marker in (sub.get("message") or "").lower()
                   for marker in _RETRYABLE_400_MARKERS):
                return True
    return False


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    # YouTube emits ``2024-04-28T14:23:11Z``.
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value[:-1]).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_video_payload(video_id: str, payload: dict[str, Any]) -> YoutubeExtractionResult:
    """Parse a ``videos.list`` response item into :class:`YoutubeExtractionResult`.

    Raises :class:`YoutubeVideoNotFound` if ``items`` is empty.
    """
    items = payload.get("items") or []
    if not items:
        raise YoutubeVideoNotFound(f"video_id={video_id} not found")
    item = items[0]
    snippet = item.get("snippet") or {}
    content = item.get("contentDetails") or {}
    stats = item.get("statistics") or {}
    description = snippet.get("description") or ""
    return YoutubeExtractionResult(
        video_id=video_id,
        title=snippet.get("title") or "",
        description=description,
        published_at=_parse_published_at(snippet.get("publishedAt")),
        channel_id=snippet.get("channelId") or "",
        channel_title=snippet.get("channelTitle") or "",
        duration_seconds=_parse_iso_duration(content.get("duration")),
        view_count=_safe_int(stats.get("viewCount")),
        like_count=_safe_int(stats.get("likeCount")),
        comment_count=_safe_int(stats.get("commentCount")),
        tags=list(snippet.get("tags") or []),
        category_id=snippet.get("categoryId"),
        chapters=_parse_chapters_from_description(description),
    )


# ---------- HTTP entry point ----------

def _resolve_api_key(api_key: str | None) -> str:
    key = api_key or os.environ.get("YOUTUBE_DATA_API_KEY")
    if not key:
        raise YoutubeApiKeyMissing(
            "YOUTUBE_DATA_API_KEY not set; load ~/.config/openclaw/env "
            "before invoking the extractor."
        )
    return key


async def extract_youtube_video(
    video_id: str,
    *,
    http: httpx.AsyncClient,
    api_key: str | None = None,
    parts: str = DEFAULT_PARTS,
    timeout: float = DEFAULT_TIMEOUT_S,
    max_retries: int = MAX_RETRIES,
    retry_backoff_s: float = RETRY_BACKOFF_S,
) -> YoutubeExtractionResult:
    """Fetch + parse a single YouTube video via Data API v3.

    Retries up to ``max_retries`` (default 1) on ``HTTP 400`` whose JSON body
    contains the ``"API key expired"`` / ``API_KEY_INVALID`` flake observed in
    the 013-K spike (the same key works on the next call seconds later).

    Any other 4xx/5xx, network error, or JSON parse error raises
    :class:`YoutubeExtractionError`. Empty ``items`` raises
    :class:`YoutubeVideoNotFound`.
    """
    if not video_id or not isinstance(video_id, str):
        raise YoutubeExtractionError(f"invalid video_id: {video_id!r}")
    key = _resolve_api_key(api_key)
    params = {"part": parts, "id": video_id, "key": key}

    attempt = 0
    last_400_payload: dict[str, Any] | None = None
    while True:
        try:
            response = await http.get(
                YOUTUBE_VIDEOS_ENDPOINT, params=params, timeout=timeout
            )
        except httpx.HTTPError as exc:
            raise YoutubeExtractionError(
                f"HTTP error talking to YouTube Data API: {exc.__class__.__name__}: {exc}"
            ) from exc

        if response.status_code == 200:
            try:
                payload = response.json()
            except ValueError as exc:
                raise YoutubeExtractionError(
                    f"non-JSON response from YouTube Data API: {exc}"
                ) from exc
            return parse_video_payload(video_id, payload)

        if response.status_code == 400 and attempt < max_retries:
            try:
                last_400_payload = response.json()
            except ValueError:
                last_400_payload = None
            if _is_retryable_400(last_400_payload):
                attempt += 1
                await asyncio.sleep(retry_backoff_s)
                continue
        # Non-retryable, or retries exhausted.
        # Never log the URL with the key embedded.
        body_brief = response.text[:300] if response.text else ""
        raise YoutubeExtractionError(
            f"YouTube Data API HTTP {response.status_code} for video_id={video_id}: "
            f"{body_brief}"
        )
