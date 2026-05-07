"""Tests for scripts/discovery/spike_youtube_extractor.py (013-J)."""
from __future__ import annotations

from scripts.discovery.spike_youtube_extractor import parse_video_id


class TestParseVideoId:
    def test_watch_v(self):
        assert parse_video_id("https://www.youtube.com/watch?v=Vht4hoRHEek") == "Vht4hoRHEek"

    def test_youtu_be(self):
        assert parse_video_id("https://youtu.be/9Gr2QjvSQ-I") == "9Gr2QjvSQ-I"

    def test_with_extra_params_t(self):
        assert (
            parse_video_id("https://www.youtube.com/watch?v=npmoS_dqAho&t=42s")
            == "npmoS_dqAho"
        )

    def test_with_list_param(self):
        assert (
            parse_video_id("https://www.youtube.com/watch?v=A0lQPphWTkQ&list=PLxx")
            == "A0lQPphWTkQ"
        )

    def test_invalid_url_returns_none(self):
        assert parse_video_id("https://example.com/foo") is None

    def test_empty_returns_none(self):
        assert parse_video_id("") is None
