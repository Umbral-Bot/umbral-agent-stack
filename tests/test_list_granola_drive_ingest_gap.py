"""
Tests for scripts/list_granola_drive_ingest_gap.py (P1.1b Phase 1 gap-check).
"""

import pytest

from scripts.list_granola_drive_ingest_gap import (
    NOTION_LENGTH_TOLERANCE,
    apply_manual_overrides,
    classify_gap,
    summarize,
)
from scripts.vm.granola_drive_md_ingest import expected_notion_length


def _drive(title, normalized_title, date, relative_path, sha1, filename=None):
    return {
        "filename": filename or relative_path.split("/")[-1],
        "relative_path": relative_path,
        "sha1": sha1,
        "parsed": {"title": title, "normalized_title": normalized_title, "date": date},
    }


def _notion(title, normalized_title, date, *, page_id="p1", url="https://notion.so/p1",
            fuente="granola", shared_folder_path="", sha1=""):
    return {
        "page_id": page_id,
        "url": url,
        "title": title,
        "normalized_title": normalized_title,
        "date": date,
        "fuente": fuente,
        "shared_folder_path": shared_folder_path,
        "sha1": sha1,
    }


class TestNoMatch:
    def test_creates_when_no_title_match(self):
        drive = [_drive("Brand New Meeting", "brand new meeting", "2026-07-01", "Granola/Brand New Meeting.md", "aaa")]
        notion = [_notion("Something Else", "something else", "2026-01-01")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "create"
        assert result[0]["en_notion"] is False

    def test_flags_near_duplicate_title_on_create(self):
        drive = [_drive("BIM Forum GT Radar", "bim forum gt radar", "2026-06-24", "Granola/x.md", "aaa")]
        notion = [_notion("BIM Forum GT Radars", "bim forum gt radars", "2026-01-01")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "create"
        assert result[0]["candidates"], "near-duplicate should be surfaced even though action is create"

    def test_near_duplicate_title_with_exact_date_match_is_escalated_not_created(self):
        # "BIM FOurm" (typo) vs "BIM Forum" — different normalized strings,
        # but same date is strong evidence of the same real-world meeting.
        drive = [_drive("BIM FOurm", "bim fourm", "2026-03-18", "Granola/BIM Forum 2.md", "aaa")]
        notion = [_notion("BIM Forum", "bim forum", "2026-03-18", page_id="real-page")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "review_ambiguous"
        assert result[0]["match_strategy"] == "near_duplicate_title_exact_date"
        assert result[0]["en_notion"] is True
        assert result[0]["candidates"][0]["page_id"] == "real-page"

    def test_near_duplicate_title_without_exact_date_stays_create(self):
        drive = [_drive("Sesion 3 power automate WSP", "sesion 3 power automate wsp", "2026-04-20", "Granola/x.md", "aaa")]
        notion = [_notion("Sesion power automate WSP", "sesion power automate wsp", "2026-01-01")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "create"
        assert "near-duplicate" in result[0]["notes"][0]


class TestExactTitleDateMatch:
    def test_updates_when_single_title_and_date_match(self):
        drive = [_drive("BIM Forum", "bim forum", "2026-03-30", "Granola/BIM Forum 3.md", "aaa")]
        notion = [_notion("BIM Forum", "bim forum", "2026-03-30", fuente="granola_mcp")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "update_transcript"
        assert result[0]["match_strategy"] == "normalized_title_date"
        assert result[0]["matched_page"]["page_id"] == "p1"
        assert any("fuente=" in n for n in result[0]["notes"])

    def test_accent_and_case_insensitive_title_match(self):
        drive = [_drive("Máster en IA — Sesión", "master en ia sesion", "2026-06-04", "Granola/x.md", "aaa")]
        notion = [_notion("MASTER EN IA - SESION", "master en ia sesion", "2026-06-04")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "update_transcript"


class TestAmbiguous:
    def test_multiple_title_matches_different_dates_flagged_ambiguous(self):
        drive = [_drive("Asesoria Discurso", "asesoria discurso", "2026-05-04", "Granola/x.md", "aaa")]
        notion = [
            _notion("Asesoria Discurso", "asesoria discurso", "2026-04-01", page_id="p1"),
            _notion("Asesoria Discurso", "asesoria discurso", "2026-05-04", page_id="p2"),
            _notion("Asesoria Discurso", "asesoria discurso", "2026-06-01", page_id="p3"),
        ]
        # date matches exactly one (p2) so this should actually resolve, not be ambiguous
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "update_transcript"
        assert result[0]["matched_page"]["page_id"] == "p2"

    def test_two_candidates_share_the_same_date_is_ambiguous(self):
        drive = [_drive("Asesoria Discurso", "asesoria discurso", "2026-05-04", "Granola/x.md", "aaa")]
        notion = [
            _notion("Asesoria Discurso", "asesoria discurso", "2026-05-04", page_id="p1"),
            _notion("Asesoria Discurso", "asesoria discurso", "2026-05-04", page_id="p2"),
        ]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "review_ambiguous"
        assert len(result[0]["candidates"]) == 2

    def test_title_matches_but_no_drive_date_is_ambiguous(self):
        drive = [_drive("Reunion Sin Fecha", "reunion sin fecha", "", "Granola/x.md", "aaa")]
        notion = [_notion("Reunion Sin Fecha", "reunion sin fecha", "2026-05-04", page_id="p1")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "review_ambiguous"
        assert result[0]["match_strategy"] == "normalized_title_only_no_drive_date"

    def test_title_matches_but_date_mismatch_no_other_candidate_creates(self):
        # Recurring-series case (e.g. "Konstruedu" on many different dates):
        # same title in Notion, but under a different date than every
        # candidate -> treated as a distinct meeting instance -> create.
        drive = [_drive("Konstruedu", "konstruedu", "2026-07-01", "Granola/x.md", "aaa")]
        notion = [_notion("Konstruedu", "konstruedu", "2026-01-15", page_id="p1")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "create"
        assert result[0]["match_strategy"] == "same_title_no_exact_date_match"
        assert result[0]["candidates"][0]["page_id"] == "p1"

    def test_title_matches_multiple_candidates_share_exact_date_stays_ambiguous(self):
        # Genuine data collision: two existing pages share BOTH the title
        # AND the drive file's date -> cannot auto-resolve.
        drive = [_drive("Konstruedu", "konstruedu", "2026-07-01", "Granola/x.md", "aaa")]
        notion = [
            _notion("Konstruedu", "konstruedu", "2026-07-01", page_id="p1"),
            _notion("Konstruedu", "konstruedu", "2026-07-01", page_id="p2"),
        ]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "review_ambiguous"
        assert result[0]["match_strategy"] == "normalized_title_multiple_or_date_mismatch"


class TestSharedFolderPathTraceability:
    def test_skip_when_path_and_sha1_both_match(self):
        drive = [_drive("X", "x", "2026-07-01", "Granola/x.md", "aaa")]
        notion = [_notion("X", "x", "2026-07-01", shared_folder_path="Granola/x.md", sha1="aaa")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "skip"
        assert result[0]["match_strategy"] == "shared_folder_path_sha1"

    def test_update_when_path_matches_but_sha1_differs(self):
        drive = [_drive("X", "x", "2026-07-01", "Granola/x.md", "bbb")]
        notion = [_notion("X", "x", "2026-07-01", shared_folder_path="Granola/x.md", sha1="aaa")]
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "update_transcript"
        assert result[0]["match_strategy"] == "shared_folder_path_changed"

    def test_shared_folder_path_takes_priority_over_title_match(self):
        # Even if title/date would also match a *different* page, the
        # feeder's own prior traceability wins.
        drive = [_drive("X", "x", "2026-07-01", "Granola/x.md", "aaa")]
        notion = [
            _notion("X", "x", "2026-07-01", page_id="title-match", fuente="granola"),
            _notion("Unrelated", "unrelated", "2026-01-01", page_id="path-match",
                    shared_folder_path="Granola/x.md", sha1="aaa"),
        ]
        result = classify_gap(drive, notion)
        assert result[0]["matched_page"]["page_id"] == "path-match"
        assert result[0]["action"] == "skip"


class TestApplyManualOverrides:
    def test_resolves_ambiguous_item_to_update_with_confirmed_title(self):
        classified = [
            {
                "relative_path": "Granola/BIM Forum 2.md",
                "title": "BIM FOurm",
                "action": "review_ambiguous",
                "match_strategy": "near_duplicate_title_exact_date",
                "matched_page": None,
                "candidates": [{"page_id": "real-page", "url": "https://notion.so/real-page", "title": "BIM Forum", "date": "2026-03-18"}],
                "notes": ["near-duplicate title with an EXACT date match"],
            }
        ]
        overrides = [
            {
                "relative_path": "Granola/BIM Forum 2.md",
                "action": "update_transcript",
                "page_id": "real-page",
                "url": "https://notion.so/real-page",
                "title": "BIM Forum",
                "reason": "confirmed duplicate, same meeting 18-mar",
            }
        ]
        result = apply_manual_overrides(classified, overrides)
        item = result[0]
        assert item["action"] == "update_transcript"
        assert item["match_strategy"] == "manual_override"
        assert item["matched_page"] == {"page_id": "real-page", "url": "https://notion.so/real-page"}
        assert item["title_override"] == "BIM Forum"
        assert any("manual override" in n for n in item["notes"])

    def test_create_override_needs_no_page_id(self):
        classified = [{"relative_path": "Granola/x.md", "action": "review_ambiguous", "notes": []}]
        overrides = [{"relative_path": "Granola/x.md", "action": "create", "reason": "no exact date match"}]
        result = apply_manual_overrides(classified, overrides)
        assert result[0]["action"] == "create"
        assert "title_override" not in result[0]

    def test_unknown_relative_path_raises(self):
        classified = [{"relative_path": "Granola/x.md", "action": "review_ambiguous", "notes": []}]
        overrides = [{"relative_path": "Granola/does-not-exist.md", "action": "create"}]
        with pytest.raises(ValueError):
            apply_manual_overrides(classified, overrides)


class TestSummarize:
    def test_counts_each_action(self):
        classified = [
            {"action": "create"},
            {"action": "create"},
            {"action": "update_transcript"},
            {"action": "skip"},
            {"action": "review_ambiguous"},
        ]
        summary = summarize(classified)
        assert summary == {"create": 2, "update_transcript": 1, "skip": 1, "review_ambiguous": 1}


class TestAlreadyIngestedLength:
    """A renamed / duplicated Drive file must not become a daily no-op rewrite.

    Drive-side renames and ``... (2).md`` copies re-enter the folder under a
    new ``shared_folder_path``, so tiers 1/2 stop recognizing them and they
    fall through to title+date. Before this tier they classified as
    ``update_transcript`` on every single run of the recurring feeder.
    """

    def _pair(self, char_count, stored_length):
        drive = [
            {
                "filename": "Sesión de seguimiento WSP (2).md",
                "relative_path": "Granola/Sesión de seguimiento WSP (2).md",
                "sha1": "new-sha",
                "parsed": {
                    "title": "Sesión de seguimiento WSP",
                    "normalized_title": "sesion de seguimiento wsp",
                    "date": "2026-06-30",
                    "char_count": char_count,
                },
            }
        ]
        notion = [
            _notion(
                "Sesión de seguimiento WSP",
                "sesion de seguimiento wsp",
                "2026-06-30",
                fuente="granola_drive_md",
                shared_folder_path="Granola/Sesión de seguimiento WSP.md",
                sha1="old-sha",
            )
        ]
        notion[0]["longitud_notion"] = stored_length
        return drive, notion

    def test_skips_when_the_page_already_stores_this_exact_transcript(self):
        drive, notion = self._pair(90481, 90558)
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "skip"
        assert result[0]["match_strategy"] == "normalized_title_date_length_match"

    def test_tolerates_the_trailing_newline_notion_trims(self):
        drive, notion = self._pair(1000, expected_notion_length(1000) - 1)
        assert classify_gap(drive, notion)[0]["action"] == "skip"

    def test_a_real_content_change_still_updates(self):
        drive, notion = self._pair(90481, 3600)
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "update_transcript"
        assert result[0]["match_strategy"] == "normalized_title_date"

    def test_a_length_just_outside_tolerance_still_updates(self):
        drive, notion = self._pair(1000, expected_notion_length(1000) + NOTION_LENGTH_TOLERANCE + 1)
        assert classify_gap(drive, notion)[0]["action"] == "update_transcript"

    def test_a_page_with_no_recorded_length_still_updates(self):
        drive, notion = self._pair(90481, 0)
        assert classify_gap(drive, notion)[0]["action"] == "update_transcript"

    def test_a_page_with_a_junk_length_still_updates(self):
        drive, notion = self._pair(90481, 0)
        notion[0]["longitud_notion"] = "n/a"
        assert classify_gap(drive, notion)[0]["action"] == "update_transcript"

    def test_a_drive_file_with_no_char_count_still_updates(self):
        drive, notion = self._pair(0, 90558)
        assert classify_gap(drive, notion)[0]["action"] == "update_transcript"

    def test_length_never_rescues_a_path_match_whose_sha_changed(self):
        # Tier 2 has a real sha1 disagreement: the file genuinely changed, and
        # length equality must not talk us out of rewriting it.
        drive = [
            {
                "filename": "x.md",
                "relative_path": "Granola/x.md",
                "sha1": "new",
                "parsed": {
                    "title": "X",
                    "normalized_title": "x",
                    "date": "2026-06-30",
                    "char_count": 1000,
                },
            }
        ]
        notion = [_notion("X", "x", "2026-06-30", shared_folder_path="Granola/x.md", sha1="old")]
        notion[0]["longitud_notion"] = expected_notion_length(1000)
        result = classify_gap(drive, notion)
        assert result[0]["action"] == "update_transcript"
        assert result[0]["match_strategy"] == "shared_folder_path_changed"
