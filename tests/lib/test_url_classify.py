"""Tests for ``scripts.discovery.lib.url_classify``.

Pure / offline. No HTTP, no domain blocklist — the classifier is structural.
"""

from __future__ import annotations

import pytest

from scripts.discovery.lib.url_classify import is_home_or_feed_url


# ---------------------------------------------------------------------------
# Home pages — must be flagged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://www.buildingsmart.org/",  # real negative example, CAND-OLA3-03
        "https://www.buildingsmart.org",  # no trailing slash either
        "http://example.com/",
        "https://example.com",
        "https://sub.example.com/",
    ],
)
def test_home_page_is_flagged(url):
    assert is_home_or_feed_url(url) is True


# ---------------------------------------------------------------------------
# Feeds — must be flagged, on any domain
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://blog.example.com/feed",
        "https://blog.example.com/feed/",
        "https://example.com/rss",
        "https://example.com/atom",
        "https://example.com/feed.xml",
        "https://example.com/blog/rss.xml",
        "https://example.com/feed.atom",
    ],
)
def test_feed_url_is_flagged(url):
    assert is_home_or_feed_url(url) is True


# ---------------------------------------------------------------------------
# Concrete pieces — must NOT be flagged, including on the same domain as the
# negative example above (this is a structural check, not a domain blocklist)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://www.buildingsmart.org/ifc-4-3-approved-as-a-final-standard/",
        "https://example.com/2026/03/09/some-article-slug",
        "https://example.com/blog/a-specific-post-title",
        "https://example.com/reports/annual-report-2026.pdf",
        "https://example.com/p/12345",
        "https://example.com/news/company-announces-something-specific",
    ],
)
def test_concrete_item_url_is_not_flagged(url):
    assert is_home_or_feed_url(url) is False


# ---------------------------------------------------------------------------
# Fail-closed edge cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        None,
        "not-a-url",
        "buildingsmart.org",  # missing scheme
        "ftp://",  # scheme but no netloc
    ],
)
def test_empty_or_unparseable_is_flagged(url):
    assert is_home_or_feed_url(url) is True
