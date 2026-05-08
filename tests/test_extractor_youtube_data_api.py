"""Tests for ``dispatcher.extractors.youtube_data_api``.

All HTTP is mocked via ``httpx.MockTransport``; no real network, no real key.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx
import pytest

from dispatcher.extractors.youtube_data_api import (
    YOUTUBE_VIDEOS_ENDPOINT,
    YoutubeApiKeyMissing,
    YoutubeExtractionError,
    YoutubeVideoNotFound,
    _is_retryable_400,
    _parse_chapters_from_description,
    _parse_iso_duration,
    extract_youtube_video,
    parse_video_payload,
)


# ---------- Pure helpers ----------

class TestParseIsoDuration:
    def test_full_format(self):
        assert _parse_iso_duration("PT1H4M56S") == 3896

    def test_minutes_only(self):
        assert _parse_iso_duration("PT4M3S") == 243

    def test_short_clip(self):
        assert _parse_iso_duration("PT42S") == 42

    def test_seconds_zero(self):
        assert _parse_iso_duration("PT0S") == 0

    def test_long_form_with_hours_only(self):
        assert _parse_iso_duration("PT2H") == 7200

    def test_live_stream_p0d(self):
        assert _parse_iso_duration("P0D") == 0

    @pytest.mark.parametrize("bad", [None, "", "garbage", "1h", "PTXM"])
    def test_unparseable_returns_zero(self, bad):
        assert _parse_iso_duration(bad) == 0


class TestParseChapters:
    def test_basic_three_chapters(self):
        desc = (
            "Welcome to the video!\n"
            "0:00 Intro\n"
            "1:23 Setup\n"
            "5:42 Demo\n"
            "Thanks for watching."
        )
        chapters = _parse_chapters_from_description(desc)
        assert chapters == [
            {"start_seconds": 0, "title": "Intro"},
            {"start_seconds": 83, "title": "Setup"},
            {"start_seconds": 342, "title": "Demo"},
        ]

    def test_with_hours_format(self):
        desc = "0:00 Start\n1:02:33 Q&A"
        chapters = _parse_chapters_from_description(desc)
        assert chapters is not None
        assert chapters[1] == {"start_seconds": 3753, "title": "Q&A"}

    def test_dash_separator(self):
        desc = "0:00 - Intro\n2:15 - Body"
        chapters = _parse_chapters_from_description(desc)
        assert chapters is not None
        assert chapters[0]["title"] == "Intro"
        assert chapters[1]["start_seconds"] == 135

    def test_single_timestamp_is_not_chapters(self):
        desc = "Recorded on 8:30 PM. Enjoy!"
        # Even if the regex picks one up it must return None (need >=2).
        assert _parse_chapters_from_description(desc) is None

    def test_no_timestamps(self):
        assert _parse_chapters_from_description("Plain description, no times.") is None

    def test_empty(self):
        assert _parse_chapters_from_description("") is None
        assert _parse_chapters_from_description(None) is None


class TestRetryableDetection:
    def test_message_at_top_level(self):
        payload = {"error": {"code": 400, "message": "API key expired. Please renew."}}
        assert _is_retryable_400(payload) is True

    def test_api_key_invalid_marker(self):
        payload = {"error": {"code": 400, "errors": [{"message": "API_KEY_INVALID"}]}}
        assert _is_retryable_400(payload) is True

    def test_unrelated_400_not_retryable(self):
        payload = {"error": {"code": 400, "message": "Invalid videoId"}}
        assert _is_retryable_400(payload) is False

    def test_none_payload(self):
        assert _is_retryable_400(None) is False


# ---------- Payload parsing ----------

VIDEO_OK_PAYLOAD = {
    "items": [
        {
            "id": "Vht4hoRHEek",
            "snippet": {
                "title": "Learn ETL Pipelines in Databricks in Under 1 Hour",
                "description": (
                    "Welcome.\n0:00 Intro\n1:30 Setup\n12:00 Demo\nMore text below."
                ),
                "publishedAt": "2026-04-28T14:23:11Z",
                "channelId": "UC1234",
                "channelTitle": "Alex The Analyst",
                "tags": ["databricks", "etl"],
                "categoryId": "27",
            },
            "contentDetails": {"duration": "PT1H4M56S"},
            "statistics": {"viewCount": "12345", "likeCount": "678", "commentCount": "42"},
        }
    ]
}


def test_parse_video_payload_extracts_all_fields():
    result = parse_video_payload("Vht4hoRHEek", VIDEO_OK_PAYLOAD)
    assert result.video_id == "Vht4hoRHEek"
    assert result.title.startswith("Learn ETL")
    assert "0:00 Intro" in result.description
    assert result.published_at == datetime(2026, 4, 28, 14, 23, 11, tzinfo=timezone.utc)
    assert result.channel_id == "UC1234"
    assert result.channel_title == "Alex The Analyst"
    assert result.duration_seconds == 3896
    assert result.view_count == 12345
    assert result.like_count == 678
    assert result.comment_count == 42
    assert result.tags == ["databricks", "etl"]
    assert result.category_id == "27"
    assert result.chapters and len(result.chapters) == 3


def test_parse_video_payload_empty_items_raises():
    with pytest.raises(YoutubeVideoNotFound):
        parse_video_payload("zzzzzzzzzzz", {"items": []})


def test_parse_video_payload_missing_optional_stats():
    payload = {
        "items": [
            {
                "snippet": {
                    "title": "T", "description": "",
                    "publishedAt": "2025-01-01T00:00:00Z",
                    "channelId": "UC", "channelTitle": "C",
                },
                "contentDetails": {"duration": "PT30S"},
                "statistics": {},
            }
        ]
    }
    r = parse_video_payload("abc", payload)
    assert r.view_count is None and r.like_count is None and r.comment_count is None
    assert r.duration_seconds == 30
    assert r.tags == []


# ---------- HTTP integration via MockTransport ----------

API_KEY_EXPIRED_PAYLOAD = {
    "error": {
        "code": 400,
        "message": "API key expired. Please renew the API key.",
        "errors": [{"reason": "badRequest"}],
        "status": "INVALID_ARGUMENT",
    }
}


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


def test_extract_returns_result_on_200(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DATA_API_KEY", "fake-key")
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.path.endswith("/videos")
        # API key MUST be in params (we never embed in path).
        assert "key=fake-key" in str(request.url)
        return httpx.Response(200, json=VIDEO_OK_PAYLOAD)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await extract_youtube_video(
                "Vht4hoRHEek", http=client, retry_backoff_s=0.0
            )

    result = _run(go())
    assert result.title.startswith("Learn ETL")
    assert len(calls) == 1


def test_extract_retries_once_on_api_key_expired_flake(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DATA_API_KEY", "fake-key")
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        if seen["n"] == 1:
            return httpx.Response(400, json=API_KEY_EXPIRED_PAYLOAD)
        return httpx.Response(200, json=VIDEO_OK_PAYLOAD)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await extract_youtube_video(
                "Vht4hoRHEek", http=client, retry_backoff_s=0.0
            )

    result = _run(go())
    assert seen["n"] == 2
    assert result.video_id == "Vht4hoRHEek"


def test_extract_fails_after_retries_exhausted(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DATA_API_KEY", "fake-key")
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        return httpx.Response(400, json=API_KEY_EXPIRED_PAYLOAD)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            await extract_youtube_video(
                "Vht4hoRHEek", http=client, retry_backoff_s=0.0
            )

    with pytest.raises(YoutubeExtractionError):
        _run(go())
    # 1 initial + 1 retry = 2.
    assert seen["n"] == 2


def test_extract_does_not_retry_on_unrelated_400(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DATA_API_KEY", "fake-key")
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        return httpx.Response(
            400,
            json={"error": {"code": 400, "message": "Invalid value for id."}},
        )

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            await extract_youtube_video(
                "BAD_ID", http=client, retry_backoff_s=0.0
            )

    with pytest.raises(YoutubeExtractionError):
        _run(go())
    assert seen["n"] == 1  # no retry on non-flake 400.


def test_extract_raises_video_not_found_on_empty_items(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DATA_API_KEY", "fake-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": []})

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            await extract_youtube_video(
                "zzzzzzzzzzz", http=client, retry_backoff_s=0.0
            )

    with pytest.raises(YoutubeVideoNotFound):
        _run(go())


def test_extract_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("YOUTUBE_DATA_API_KEY", raising=False)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as client:
            await extract_youtube_video("Vht4hoRHEek", http=client)

    with pytest.raises(YoutubeApiKeyMissing):
        _run(go())


def test_extract_raises_on_5xx(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DATA_API_KEY", "fake-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream temporarily unavailable")

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            await extract_youtube_video(
                "Vht4hoRHEek", http=client, retry_backoff_s=0.0
            )

    with pytest.raises(YoutubeExtractionError):
        _run(go())
