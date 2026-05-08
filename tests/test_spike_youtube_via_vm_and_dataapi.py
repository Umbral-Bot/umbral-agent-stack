"""Tests for spike 013-K script (parser + skip-on-no-key)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make `scripts/` importable as a top-level package even though the repo runs
# the script as `python -m scripts.discovery.spike_youtube_via_vm_and_dataapi`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.discovery import spike_youtube_via_vm_and_dataapi as spike  # noqa: E402


SAMPLE_DATA_API_RESPONSE = {
    "kind": "youtube#videoListResponse",
    "items": [
        {
            "id": "dQw4w9WgXcQ",
            "snippet": {
                "publishedAt": "2009-10-25T06:57:33Z",
                "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "channelTitle": "Rick Astley",
                "title": "Rick Astley - Never Gonna Give You Up",
                "description": (
                    "The official video for 'Never Gonna Give You Up' by Rick "
                    "Astley. " * 30
                ),
                "tags": ["Rick Astley", "Never Gonna Give You Up", "music"],
                "categoryId": "10",
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "contentDetails": {"duration": "PT3M33S"},
            "statistics": {
                "viewCount": "1500000000",
                "likeCount": "16000000",
                "commentCount": "2000000",
            },
        }
    ],
}


def test_parse_data_api_response_extracts_useful_fields():
    parsed = spike.parse_data_api_response(SAMPLE_DATA_API_RESPONSE)

    assert parsed["found"] is True
    assert parsed["has_long_description"] is True
    assert parsed["has_tags"] is True
    assert parsed["has_duration"] is True

    fields = parsed["fields"]
    assert fields["title"] == "Rick Astley - Never Gonna Give You Up"
    assert fields["channel_id"] == "UCuAXFkgsw1L7xaCfnd5JJOw"
    assert fields["channel_title"] == "Rick Astley"
    assert fields["published_at"] == "2009-10-25T06:57:33Z"
    assert fields["duration_iso"] == "PT3M33S"
    assert fields["duration_seconds"] == 3 * 60 + 33
    assert fields["tags_count"] == 3
    assert fields["description_len"] > 500
    assert fields["view_count"] == "1500000000"
    assert fields["category_id"] == "10"
    assert fields["default_language"] == "en"


def test_parse_data_api_response_handles_empty_items():
    parsed = spike.parse_data_api_response({"items": []})
    assert parsed == {"found": False, "fields": {}}


def test_parse_iso_duration_variants():
    assert spike.parse_iso_duration("PT1H2M3S") == 3723
    assert spike.parse_iso_duration("PT45S") == 45
    assert spike.parse_iso_duration("PT10M") == 600
    assert spike.parse_iso_duration("PT2H") == 7200
    assert spike.parse_iso_duration("") is None
    assert spike.parse_iso_duration(None) is None
    assert spike.parse_iso_duration("garbage") is None


@pytest.mark.skipif(
    bool(os.environ.get("YOUTUBE_DATA_API_KEY")),
    reason="YOUTUBE_DATA_API_KEY is set; live Data API test belongs in integration suite.",
)
def test_data_api_skipped_without_key():
    """This test documents the blocker: VIA B is unusable until David provides
    YOUTUBE_DATA_API_KEY in the dispatcher environment. Skipped automatically
    when the env var is present (use a separate live integration test for that)."""
    assert os.environ.get("YOUTUBE_DATA_API_KEY") in (None, "")
