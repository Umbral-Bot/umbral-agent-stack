"""Pure URL classification: concrete item vs. organization home/feed page.

No HTTP, no network calls, no side effects — purely structural URL
inspection. Backs rule #7 of ``docs/ops/editorial-source-attribution-policy.md``:
the citable source of an editorial candidate must be the concrete piece
(``item_url`` — the specific article, report, video, or post), never the
organization's home page or feed. Real negative example that motivated this
guard: CAND-OLA3-03 cited ``https://www.buildingsmart.org/`` (the bare
domain home page) instead of a specific piece.

Deliberately not a domain blocklist — a single ``if domain == "buildingsmart.org"``
would only ever catch this one org. The check is structural: does the URL's
path look like "nothing" (a home page) or a syndication feed, regardless of
which domain it's on.

Note: :mod:`scripts.discovery.stage2_ingest` has its own, separate
``RSS_FEED_SUFFIXES`` / ``is_direct_rss_candidate`` — that one decides
RSS-parse vs. HTML-scrape for a referente's *known, configured* feed URL at
ingest time, a different question from classifying an arbitrary citation
URL's shape at promotion/publish time. Not merged on purpose; keep both in
sync if the feed-suffix vocabulary changes in one.
"""

from __future__ import annotations

from urllib.parse import urlparse

# Path suffixes that mark a syndication feed regardless of the rest of the path.
_FEED_SUFFIXES = (".rss", ".atom", ".xml")

# Path segments that mark a feed endpoint when they are the *last* segment
# (e.g. "/blog/feed", "/rss", "/feed/atom" all end in one of these).
_FEED_LAST_SEGMENTS = ("feed", "feeds", "rss", "atom")


def is_home_or_feed_url(url: str) -> bool:
    """Return True when ``url`` looks like an org home page or a feed,
    rather than a concrete item (article/report/video/post).

    Heuristic, not exhaustive, and deliberately fail-closed: an empty
    string, a non-absolute string, or anything unparseable is also treated
    as "not a concrete item" (return True) rather than silently passing.

    Known limitation (fail-closed side, no repo usage found today): a URL
    whose item identifier lives only in the query string with an empty path
    (e.g. ``https://example.com/?post=123``) is flagged as a home page,
    since only the path is inspected. Scoped this way on purpose — this
    guard targets the documented rule #7 pattern (bare home/feed), not
    general web-page classification.
    """
    url = (url or "").strip()
    if not url:
        return True

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        # Not a real absolute URL — cannot be a concrete item either.
        return True

    path = parsed.path.rstrip("/")
    if not path:
        # Bare domain, or domain + trailing slash(es) only: the org's home page.
        return True

    lowered = path.lower()
    if lowered.endswith(_FEED_SUFFIXES):
        return True

    last_segment = lowered.rsplit("/", 1)[-1]
    if last_segment in _FEED_LAST_SEGMENTS:
        return True

    return False
