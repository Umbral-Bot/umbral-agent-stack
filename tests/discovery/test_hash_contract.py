"""Cross-stage hash contract tests (Wave 1.5).

Verifies the contract documented in
``docs/editorial-pipeline/hash-contract.md``:

- ``dedup_hash`` (S1, H2) is deterministic and date-independent in the
  ``published_at is None | ""`` case.
- ``content_hash`` (S2, H3) is date-independent but title/excerpt sensitive.
- ``idempotency_key`` (S2, H3) flips iff ``content_hash`` flips for the same
  canonical URL.
"""

from __future__ import annotations

from scripts.discovery.lib.dedup import (
    compute_content_hash,
    compute_idempotency_key,
)
from scripts.discovery.stage1_discover_signals import dedup_hash


URL = "https://example.com/post/abc"
URL_OTHER = "https://example.com/post/zzz"


def test_dedup_hash_deterministic_same_inputs() -> None:
    h1 = dedup_hash(URL, "2026-05-08T12:00:00Z")
    h2 = dedup_hash(URL, "2026-05-08T12:00:00Z")
    assert h1 == h2


def test_dedup_hash_published_at_none_empty_equivalent() -> None:
    h_none = dedup_hash(URL, None)
    h_empty = dedup_hash(URL, "")
    assert h_none == h_empty


def test_dedup_hash_changes_when_published_at_differs() -> None:
    h_no_date = dedup_hash(URL, None)
    h_with_date = dedup_hash(URL, "2026-05-08T12:00:00Z")
    assert h_no_date != h_with_date


def test_dedup_hash_changes_when_url_differs() -> None:
    h_a = dedup_hash(URL, None)
    h_b = dedup_hash(URL_OTHER, None)
    assert h_a != h_b


def test_content_hash_ignores_published_at() -> None:
    """content_hash takes (url, title, excerpt) — date is not an input."""
    h1 = compute_content_hash(URL, "Title A", "Excerpt A")
    h2 = compute_content_hash(URL, "Title A", "Excerpt A")
    assert h1 == h2


def test_content_hash_changes_with_title() -> None:
    h_a = compute_content_hash(URL, "Title A", "Excerpt")
    h_b = compute_content_hash(URL, "Title B", "Excerpt")
    assert h_a != h_b


def test_content_hash_changes_with_excerpt() -> None:
    h_a = compute_content_hash(URL, "Title", "Excerpt A")
    h_b = compute_content_hash(URL, "Title", "Excerpt B")
    assert h_a != h_b


def test_idempotency_key_flips_with_content_hash() -> None:
    ch_a = compute_content_hash(URL, "Title A", "Excerpt")
    ch_b = compute_content_hash(URL, "Title B", "Excerpt")
    k_a = compute_idempotency_key(URL, ch_a)
    k_b = compute_idempotency_key(URL, ch_b)
    assert k_a != k_b


def test_idempotency_key_stable_for_same_content_hash() -> None:
    ch = compute_content_hash(URL, "Title", "Excerpt")
    k1 = compute_idempotency_key(URL, ch)
    k2 = compute_idempotency_key(URL, ch)
    assert k1 == k2
