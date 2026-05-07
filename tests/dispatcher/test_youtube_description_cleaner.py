"""Tests for dispatcher.extractors.youtube_description_cleaner."""

from __future__ import annotations

import pytest

from dispatcher.extractors.youtube_description_cleaner import (
    REASONS,
    Removal,
    clean_html,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HEADER = '<p><em>Duración: 12min · 1234 vistas · Likes: 567</em></p><h2>Descripción</h2>'
CAPITULOS = '<h2>Capítulos</h2><ul><li>0:00 Intro</li><li>2:30 Tema</li></ul>'


def _wrap(*paragraphs: str, with_capitulos: bool = True) -> str:
    """Build a contenido_html with header + given paragraphs + optional capitulos."""
    body = "".join(paragraphs)
    return HEADER + body + (CAPITULOS if with_capitulos else "")


def _reasons(removals: list[Removal]) -> list[str]:
    return [r.reason for r in removals]


# ---------------------------------------------------------------------------
# Reason coverage: positive + negative per reason
# ---------------------------------------------------------------------------


class TestSectionHeader:
    def test_drops_become_a_member(self) -> None:
        html = _wrap("<p>Real prose.</p>", "<p>BECOME A MEMBER</p>")
        _, removals = clean_html(html)
        assert _reasons(removals) == ["section_header"]
        assert removals[0].text == "BECOME A MEMBER"

    def test_drops_resources_with_colon(self) -> None:
        html = _wrap("<p>RESOURCES:</p>", "<p>Body text.</p>")
        _, removals = clean_html(html)
        assert _reasons(removals) == ["section_header"]

    def test_keeps_paragraph_mentioning_resources_in_prose(self) -> None:
        # "Resources" appearing inside a sentence is NOT a section header.
        html = _wrap("<p>I built these resources for the community to enjoy.</p>")
        clean, removals = clean_html(html)
        assert removals == []
        assert "resources for the community" in clean


class TestHashtagOnly:
    def test_drops_hashtag_line(self) -> None:
        html = _wrap("<p>#linux #bim #construction</p>")
        _, removals = clean_html(html)
        assert _reasons(removals) == ["hashtag_only"]

    def test_keeps_paragraph_with_hashtag_inside_prose(self) -> None:
        html = _wrap("<p>We talked about #linux at the meetup last week.</p>")
        _, removals = clean_html(html)
        assert removals == []


class TestPromoKeyword:
    def test_drops_use_code_promo(self) -> None:
        html = _wrap("<p>Get 50% off, use code RICK at checkout.</p>")
        _, removals = clean_html(html)
        assert _reasons(removals) == ["promo_keyword"]

    def test_drops_paid_promotion_disclaimer(self) -> None:
        html = _wrap(
            "<p>This video contains paid promotion from our sponsor.</p>"
        )
        _, removals = clean_html(html)
        assert _reasons(removals) == ["promo_keyword"]

    def test_keeps_word_code_in_normal_context(self) -> None:
        # "code" alone is not promo; only "use code", "promo code", etc.
        html = _wrap("<p>The Python code we wrote in the previous lesson.</p>")
        _, removals = clean_html(html)
        assert removals == []


class TestLegalDisclaimer:
    def test_drops_all_rights_reserved(self) -> None:
        html = _wrap("<p>© 2025 Channel name. All rights reserved.</p>")
        _, removals = clean_html(html)
        assert "legal_disclaimer" in _reasons(removals)

    def test_drops_not_financial_advice(self) -> None:
        html = _wrap("<p>This video is not financial advice. Do your own research.</p>")
        _, removals = clean_html(html)
        assert _reasons(removals) == ["legal_disclaimer"]

    def test_keeps_paragraph_about_law_topic(self) -> None:
        html = _wrap(
            "<p>The new law about open-source licensing is interesting to study.</p>"
        )
        _, removals = clean_html(html)
        assert removals == []


class TestSponsorDomainOnly:
    def test_drops_short_label_with_sponsor_link(self) -> None:
        # Real backfill format: bare URLs in paragraph text (no <a> wrapping).
        html = _wrap("<p>VPN: https://surfshark.com/promo</p>")
        _, removals = clean_html(html)
        assert _reasons(removals) == ["sponsor_domain_only"]

    def test_drops_bitly_link_with_short_label(self) -> None:
        html = _wrap("<p>Link: https://bit.ly/abc123</p>")
        _, removals = clean_html(html)
        assert _reasons(removals) == ["sponsor_domain_only"]

    def test_keeps_long_prose_that_happens_to_cite_bitly(self) -> None:
        # Non-link text is well above 60 chars → not dropped.
        long_text = (
            "In this episode we deep-dive into the architecture decisions "
            "behind our new platform, with all the trade-offs explained."
        )
        html = _wrap(f"<p>{long_text} See https://bit.ly/x</p>")
        _, removals = clean_html(html)
        assert removals == []


class TestSocialLinksOnly:
    def test_drops_two_social_links_with_short_label(self) -> None:
        html = _wrap(
            "<p>IG: https://instagram.com/me, TW: https://twitter.com/me</p>"
        )
        _, removals = clean_html(html)
        assert _reasons(removals) == ["social_links_only"]

    def test_keeps_single_social_link(self) -> None:
        # Threshold requires ≥2 social links.
        html = _wrap("<p>My IG: https://instagram.com/me</p>")
        _, removals = clean_html(html)
        assert removals == []


# ---------------------------------------------------------------------------
# Region preservation
# ---------------------------------------------------------------------------


class TestRegionPreservation:
    def test_header_preserved_intact(self) -> None:
        html = _wrap("<p>BECOME A MEMBER</p>", "<p>Body.</p>")
        clean, _ = clean_html(html)
        # Original header markup must appear verbatim at the start.
        assert clean.startswith(HEADER)

    def test_capitulos_preserved_intact(self) -> None:
        html = _wrap("<p>BECOME A MEMBER</p>", "<p>Body.</p>", with_capitulos=True)
        clean, _ = clean_html(html)
        assert clean.endswith(CAPITULOS)
        assert "0:00 Intro" in clean and "2:30 Tema" in clean

    def test_no_capitulos_region_does_not_invent_one(self) -> None:
        html = _wrap("<p>Body.</p>", with_capitulos=False)
        clean, _ = clean_html(html)
        assert "Capítulos" not in clean and "Capitulos" not in clean


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


class TestIdempotence:
    def test_clean_clean_equals_clean(self) -> None:
        html = _wrap(
            "<p>Real content paragraph one.</p>",
            "<p>BECOME A MEMBER</p>",
            "<p>#hashtag #only</p>",
            "<p>VPN: https://surfshark.com/x</p>",
            "<p>Real content paragraph two.</p>",
        )
        once, removals_once = clean_html(html)
        twice, removals_twice = clean_html(once)
        assert once == twice
        assert removals_twice == []
        assert len(removals_once) == 3


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_string(self) -> None:
        clean, removals = clean_html("")
        assert clean == ""
        assert removals == []

    def test_no_descripcion_marker_treats_all_as_description(self) -> None:
        # Without the standard marker, the whole input is the description region.
        html = "<p>BECOME A MEMBER</p><p>Real prose.</p>"
        clean, removals = clean_html(html)
        assert _reasons(removals) == ["section_header"]
        assert "Real prose" in clean

    def test_malformed_html_does_not_raise(self) -> None:
        # Unclosed tags, mismatched, garbage — must not raise.
        bad = "<p>broken<p>also broken<h2>Descripción<p>x</p"
        clean, removals = clean_html(bad)
        # No assertion on content; only that the call returned cleanly.
        assert isinstance(clean, str)
        assert isinstance(removals, list)

    def test_empty_paragraphs_dropped_silently(self) -> None:
        html = _wrap("<p></p>", "<p>   </p>", "<p>Real.</p>")
        clean, removals = clean_html(html)
        # Empty paragraphs do NOT produce Removal records.
        assert removals == []
        assert "Real." in clean


# ---------------------------------------------------------------------------
# Borderline / known false-positive (documented decision)
# ---------------------------------------------------------------------------


class TestBorderlineDecisions:
    def test_enroll_now_bitly_is_dropped(self) -> None:
        """Spike sid=261 (Andrew Ng / DeepLearning.AI) — borderline FP.

        "Enroll now: bit.ly/4cPZYGJ" is a CTA to the course that's the
        subject of the video, not a third-party sponsor. The conservative
        threshold (sponsor_domain + non-link text < 60 chars) catches it
        because "Enroll now: " is only 12 chars.

        Trade-off: we accept this drop because (a) the title + description
        already convey the value proposition; (b) the bit.ly URL by itself
        is opaque; (c) un-dropping would require either whitelisting course
        domains (impractical) or raising the char threshold (would re-admit
        real sponsor noise). David can override case-by-case after re-publish.
        """
        html = _wrap("<p>Enroll now: https://bit.ly/4cPZYGJ</p>")
        _, removals = clean_html(html)
        assert _reasons(removals) == ["sponsor_domain_only"]


# ---------------------------------------------------------------------------
# Known coverage gaps — expected to fail until Fase 3 regex tuning
# ---------------------------------------------------------------------------


class TestKnownGaps:
    @pytest.mark.xfail(
        reason="Spike sid=408 QuantumFracture — PREPLY pattern 'código: QUANTUM50' "
        "not yet covered. PROMO_KEYWORDS_RE matches 'código de descuento' or "
        "'usa el código' but not bare 'código: TOKEN'. To be added in Fase 3 "
        "(default-ON flip) along with regex r'\\bc[oó]digo\\s*[:\\-]\\s*[A-Z0-9]{3,}\\b'.",
        strict=True,
    )
    def test_preply_codigo_token_should_drop(self) -> None:
        html = _wrap(
            "<p>Consigue un 50% de descuento en tu primera clase con el "
            "código: QUANTUM50</p>"
        )
        _, removals = clean_html(html)
        assert "promo_keyword" in _reasons(removals)

    @pytest.mark.xfail(
        reason="Spike sid=408 QuantumFracture — Spanish CTA 'HAZTE MIEMBRO DE QF' "
        "not in SECTION_HEADERS. SECTION_HEADERS lists 'BECOME A MEMBER' (en) "
        "and 'Subscríbete' (es) but not 'HAZTE MIEMBRO'. To be added in Fase 3 "
        "alongside 'SUSCRIBIRTE' (infinitive) and 'SUSCRÍBETE' (imperative caps).",
        strict=True,
    )
    def test_hazte_miembro_should_drop(self) -> None:
        html = _wrap("<p>HAZTE MIEMBRO DE QF</p>")
        _, removals = clean_html(html)
        assert _reasons(removals) == ["section_header"]


# ---------------------------------------------------------------------------
# Sanity: REASONS constant matches actual emit set
# ---------------------------------------------------------------------------


def test_reasons_constant_complete() -> None:
    assert set(REASONS) == {
        "section_header",
        "hashtag_only",
        "promo_keyword",
        "legal_disclaimer",
        "sponsor_domain_only",
        "social_links_only",
    }
