"""
Tests for scripts/vm/granola_drive_md_ingest.py (P1.1b Drive transcript feeder).
"""

import json
import textwrap
from datetime import date

import pytest

from scripts.vm.granola_drive_md_ingest import (
    FLATTENED_LINE_CHARS,
    _emit,
    build_content,
    build_inventory,
    build_payload,
    list_drive_transcript_files,
    parse_drive_transcript_md,
    parse_meeting_date_header,
    resolve_meeting_date,
    parse_participants,
    sha1_of_text,
    turn_labels_in,
    unflatten_transcript,
)


SAMPLE_MD = textwrap.dedent(
    """\
    Meeting Title: Comgrap Dynamo - Comgrap - Carcel
    Date: Apr 20
    Meeting participants: David Moreira

    Transcript:

    Me: Hola, chicos, como estan?
    Them: Hola, David.
    """
)

SAMPLE_MD_NO_PARTICIPANTS = textwrap.dedent(
    """\
    Meeting Title: BIM Forum
    Date: Mar 30

    Transcript:

    Them: primera linea de la transcripcion, con suficiente texto de relleno.
    Me: segunda linea de la transcripcion, tambien con texto de relleno.
    """
)

SAMPLE_MD_NO_TITLE_HEADER = textwrap.dedent(
    """\
    Date: Jun 4

    Transcript:
    Them: solo una linea.
    """
)


class TestDateParsing:
    def test_parses_month_day_with_default_year(self):
        assert parse_meeting_date_header("Mar 30", default_year=2026) == "2026-03-30"

    def test_parses_single_digit_day(self):
        assert parse_meeting_date_header("Jun 4", default_year=2026) == "2026-06-04"

    def test_empty_value_returns_empty(self):
        assert parse_meeting_date_header("", default_year=2026) == ""

    def test_unparsable_value_returns_empty(self):
        assert parse_meeting_date_header("sometime last week", default_year=2026) == ""

    def test_unknown_month_abbreviation_returns_empty(self):
        assert parse_meeting_date_header("Xyz 12", default_year=2026) == ""


class TestParticipants:
    def test_splits_and_trims(self):
        assert parse_participants("David Moreira, Rick, ") == ["David Moreira", "Rick"]

    def test_dedupes_preserving_order(self):
        assert parse_participants("David, Rick, David") == ["David", "Rick"]

    def test_empty_value(self):
        assert parse_participants("") == []


class TestParseDriveTranscriptMd:
    def test_extracts_title_date_participants(self):
        parsed = parse_drive_transcript_md(
            SAMPLE_MD, "Comgrap Dynamo - Comgrap - Carcel.md", default_year=2026
        )
        assert parsed["title"] == "Comgrap Dynamo - Comgrap - Carcel"
        assert parsed["date_raw"] == "Apr 20"
        assert parsed["date"] == "2026-04-20"
        assert parsed["participants"] == ["David Moreira"]

    def test_transcript_body_is_verbatim_and_trimmed(self):
        parsed = parse_drive_transcript_md(
            SAMPLE_MD, "Comgrap Dynamo - Comgrap - Carcel.md", default_year=2026
        )
        # the leading blank/space line right after "Transcript:" is dropped
        assert parsed["transcript"].startswith("Me: Hola, chicos, como estan?")
        assert parsed["transcript"].endswith("Them: Hola, David.")
        assert "Transcript:" not in parsed["transcript"]

    def test_missing_participants_yields_empty_list(self):
        parsed = parse_drive_transcript_md(
            SAMPLE_MD_NO_PARTICIPANTS, "BIM Forum 3.md", default_year=2026
        )
        assert parsed["participants"] == []
        assert parsed["date"] == "2026-03-30"

    def test_title_falls_back_to_filename_when_header_missing(self):
        parsed = parse_drive_transcript_md(
            SAMPLE_MD_NO_TITLE_HEADER, "webinar notebooklm.md", default_year=2026
        )
        assert parsed["title"] == "webinar notebooklm"

    def test_normalized_title_folds_accents_and_case(self):
        parsed = parse_drive_transcript_md(
            "Meeting Title: Máster en IA — Sesión\nDate: Jun 4\n\nTranscript:\nMe: hola\n",
            "x.md",
            default_year=2026,
        )
        assert parsed["normalized_title"] == "master en ia sesion"

    def test_empty_transcript_when_no_transcript_header(self):
        parsed = parse_drive_transcript_md(
            "Meeting Title: X\nDate: Jun 4\n", "x.md", default_year=2026
        )
        assert parsed["transcript"] == ""
        assert parsed["char_count"] == 0


class TestTitleEdgeCases:
    def test_title_wraps_onto_continuation_line(self):
        text = (
            "Meeting Title: BIM Forum - \n"
            "MT: Estandar BIM para Proyectos Publicos\n"
            "Date: May 7\n"
            "Meeting participants: David Moreira\n"
            "\n"
            "Transcript:\n"
            "Them: hola\n"
        )
        parsed = parse_drive_transcript_md(text, "x.md", default_year=2026)
        assert parsed["title"] == "BIM Forum - MT: Estandar BIM para Proyectos Publicos"
        assert parsed["date"] == "2026-05-07"
        assert parsed["participants"] == ["David Moreira"]

    def test_title_continuation_stops_at_transcript_header_with_no_date(self):
        text = (
            "Meeting Title: Some Long Title\n"
            "continued part\n"
            "Transcript:\n"
            "Them: hola\n"
        )
        parsed = parse_drive_transcript_md(text, "x.md", default_year=2026)
        assert parsed["title"] == "Some Long Title continued part"
        assert parsed["transcript"] == "Them: hola"

    def test_leading_bom_does_not_break_title_parsing(self):
        text = "﻿Meeting Title: David Barco- Gest Project\nDate: May 15\n\nTranscript:\nMe: hola\n"
        parsed = parse_drive_transcript_md(text, "David Barco- Gest Project.md", default_year=2026)
        assert parsed["title"] == "David Barco- Gest Project"
        assert parsed["date"] == "2026-05-15"

    def test_single_line_title_unaffected_by_wrap_logic(self):
        parsed = parse_drive_transcript_md(SAMPLE_MD, "x.md", default_year=2026)
        assert parsed["title"] == "Comgrap Dynamo - Comgrap - Carcel"


class TestBuildContent:
    def test_includes_header_and_transcript(self):
        parsed = {"transcript": "Me: hola"}
        content = build_content(parsed)
        assert "Me: hola" in content
        assert content.startswith(">")

    def test_header_only_when_transcript_empty(self):
        content = build_content({"transcript": ""})
        assert "Me:" not in content
        assert content.startswith(">")


class TestBuildPayload:
    def test_requires_title(self):
        with pytest.raises(ValueError):
            build_payload({"title": "", "transcript": ""}, relative_path="Granola/x.md", file_sha1="abc")

    def test_maps_fields(self):
        parsed = parse_drive_transcript_md(SAMPLE_MD, "x.md", default_year=2026)
        payload = build_payload(
            parsed, relative_path="Granola/Comgrap Dynamo - Comgrap - Carcel.md", file_sha1="deadbeef"
        )
        assert payload["title"] == "Comgrap Dynamo - Comgrap - Carcel"
        assert payload["source"] == "granola_drive_md"
        assert payload["date"] == "2026-04-20"
        assert payload["attendees"] == ["David Moreira"]
        assert payload["shared_folder_path"] == "Granola/Comgrap Dynamo - Comgrap - Carcel.md"
        assert payload["sha1"] == "deadbeef"
        assert payload["metadata"]["shared_folder_path"] == "Granola/Comgrap Dynamo - Comgrap - Carcel.md"
        assert payload["metadata"]["sha1"] == "deadbeef"
        assert payload["notify_enlace"] is False
        assert payload["allow_legacy_raw_task_writes"] is False
        assert "Me: Hola, chicos" in payload["content"]

    def test_omits_date_and_attendees_when_absent(self):
        parsed = parse_drive_transcript_md(SAMPLE_MD_NO_TITLE_HEADER, "x.md", default_year=2026)
        payload = build_payload(parsed, relative_path="Granola/x.md", file_sha1="abc")
        assert "attendees" not in payload
        assert payload["date"] == "2026-06-04"


class TestListDriveTranscriptFiles:
    def test_excludes_index_files(self, tmp_path):
        (tmp_path / "Indice_Transcripciones_Locales_2026-05-21.md").write_text(
            "x" * 200, encoding="utf-8"
        )
        (tmp_path / "Real Meeting.md").write_text("y" * 200, encoding="utf-8")
        files = list_drive_transcript_files(tmp_path)
        assert [f.name for f in files] == ["Real Meeting.md"]

    def test_excludes_empty_and_near_empty_files(self, tmp_path):
        (tmp_path / "Empty.md").write_text("", encoding="utf-8")
        (tmp_path / "TooSmall.md").write_text("short", encoding="utf-8")
        (tmp_path / "BigEnough.md").write_text("z" * 150, encoding="utf-8")
        files = list_drive_transcript_files(tmp_path)
        assert [f.name for f in files] == ["BigEnough.md"]

    def test_missing_root_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            list_drive_transcript_files(tmp_path / "does-not-exist")


class TestBuildInventory:
    def test_end_to_end_over_tmp_dir(self, tmp_path):
        (tmp_path / "Indice_Transcripciones_Locales_2026-05-21.md").write_text(
            "x" * 200, encoding="utf-8"
        )
        # Named "Granola" on purpose: the relative_path prefix now follows the
        # folder name, and "Granola/" is what the production pages carry.
        root = tmp_path / "Granola"
        root.mkdir()
        (root / "Comgrap Dynamo - Comgrap - Carcel.md").write_text(
            SAMPLE_MD, encoding="utf-8"
        )
        (root / "BIM Forum 3.md").write_text(SAMPLE_MD_NO_PARTICIPANTS, encoding="utf-8")

        records = build_inventory(root, default_year=2026)

        assert len(records) == 2
        by_filename = {r["filename"]: r for r in records}
        comgrap = by_filename["Comgrap Dynamo - Comgrap - Carcel.md"]
        assert comgrap["relative_path"] == "Granola/Comgrap Dynamo - Comgrap - Carcel.md"
        assert comgrap["payload"]["source"] == "granola_drive_md"
        assert comgrap["sha1"] == sha1_of_text(SAMPLE_MD)
        assert comgrap["payload"]["sha1"] == comgrap["sha1"]

        bim_forum = by_filename["BIM Forum 3.md"]
        assert bim_forum["parsed"]["date"] == "2026-03-30"
        assert "attendees" not in bim_forum["payload"]


class TestSha1:
    def test_deterministic(self):
        assert sha1_of_text("abc") == sha1_of_text("abc")

    def test_differs_for_different_content(self):
        assert sha1_of_text("abc") != sha1_of_text("abd")


class TestEmit:
    def test_writes_utf8_to_a_file(self, tmp_path):
        # Windows' console default (cp1252) cannot encode this; writing the
        # file explicitly as UTF-8 is what keeps a scheduled run from dying
        # mid-dump on a transcript that contains an emoji.
        out = tmp_path / "inv.json"
        _emit({"records": ["reunión 📌 会議"]}, str(out))
        assert json.loads(out.read_text(encoding="utf-8"))["records"] == ["reunión 📌 会議"]

    def test_falls_back_to_stdout_when_no_output_given(self, capsys):
        _emit({"count": 1}, None)
        assert json.loads(capsys.readouterr().out)["count"] == 1


class TestResolveMeetingDate:
    """A recurring feeder cannot carry a hardcoded year.

    Granola omits the year from its ``Date:`` header. P1.1b hardcoded 2026
    because every file it touched was from 2026; a job that runs every day
    stamps a stale year onto every transcript the moment the calendar rolls
    over, and title+date matching then resolves to LAST year's page for the
    same recurring meeting -- an overwrite, not a create.
    """

    def test_uses_the_year_the_file_was_pasted(self):
        assert resolve_meeting_date("Mar 30", pasted_on=date(2027, 4, 2)) == "2027-03-30"

    def test_rolls_back_a_december_meeting_pasted_in_january(self):
        assert resolve_meeting_date("Dec 28", pasted_on=date(2027, 1, 4)) == "2026-12-28"

    def test_tolerates_drive_sync_lag_of_a_few_days(self):
        # Sync can stamp the file slightly before the header's own date.
        assert resolve_meeting_date("Mar 30", pasted_on=date(2027, 3, 28)) == "2027-03-30"

    def test_unparseable_header_stays_empty(self):
        assert resolve_meeting_date("sometime last week", pasted_on=date(2027, 1, 4)) == ""

    def test_empty_header_stays_empty(self):
        assert resolve_meeting_date("", pasted_on=date(2027, 1, 4)) == ""


class TestInventoryPathPrefix:
    def test_prefix_comes_from_the_folder_not_a_constant(self, tmp_path):
        # Pointing --root at a copy must not mint dedup keys that collide with
        # the production pages' stored shared_folder_path.
        backup = tmp_path / "Granola-backup"
        backup.mkdir()
        (backup / "BIM Forum 3.md").write_text(SAMPLE_MD_NO_PARTICIPANTS, encoding="utf-8")
        record = build_inventory(backup, default_year=2026)[0]
        assert record["relative_path"] == "Granola-backup/BIM Forum 3.md"
        assert record["payload"]["shared_folder_path"] == "Granola-backup/BIM Forum 3.md"

    def test_production_folder_keeps_the_historical_prefix(self, tmp_path):
        prod = tmp_path / "Granola"
        prod.mkdir()
        (prod / "BIM Forum 3.md").write_text(SAMPLE_MD_NO_PARTICIPANTS, encoding="utf-8")
        assert build_inventory(prod)[0]["relative_path"] == "Granola/BIM Forum 3.md"


def _long(words):
    """Filler long enough to push a line past the flattening threshold."""
    return "palabra " * words


class TestTurnLabelsIn:
    def test_granolas_two_labels_are_always_present(self):
        # A body flattened onto ONE line offers at most one line-start label to
        # learn from, so the canonical pair cannot be learned -- only assumed.
        assert {"Me", "Them"} <= turn_labels_in("")
        assert {"Me", "Them"} <= turn_labels_in("Them: todo en una sola linea")

    def test_learns_real_names_used_as_labels(self):
        labels = turn_labels_in("Rolando: hola\nDavid: que tal")
        assert {"Rolando", "David"} <= labels

    def test_ignores_a_colon_that_is_not_at_line_start(self):
        assert "Entonces" not in turn_labels_in("Me: mira, Entonces: no es etiqueta")


class TestUnflattenTranscript:
    def test_a_single_giant_line_becomes_one_line_per_turn(self):
        flat = "Them: " + _long(900) + " Me: " + _long(900) + " Them: " + _long(900)
        assert len(flat) >= FLATTENED_LINE_CHARS
        out = unflatten_transcript(flat)
        starts = [ln.split(":")[0] for ln in out.splitlines() if ln.strip()]
        assert starts == ["Them", "Me", "Them"]

    def test_the_split_only_moves_whitespace(self):
        """No transcript may lose a character to the repair."""
        flat = "Them: " + _long(700) + " Me: " + _long(700)
        out = unflatten_transcript(flat)
        assert "".join(out.split()) == "".join(flat.split())

    def test_an_already_multiline_paste_comes_back_identical(self):
        already = "Them: hola\nMe: que tal\nThem: bien"
        assert unflatten_transcript(already) == already

    def test_a_long_line_without_labels_comes_back_unchanged(self):
        """A webinar Granola recorded as one long turn has nothing to split on.

        This is the shape of the four files that were stranded: complete
        bodies, one speaker, no interior labels. The repair must not pretend
        otherwise.
        """
        monologue = "Them: " + _long(4000)
        assert len(monologue) >= FLATTENED_LINE_CHARS
        assert unflatten_transcript(monologue) == monologue

    def test_a_short_summary_is_never_touched(self):
        # Below the threshold nothing is inspected at all, so a summary cannot
        # be dressed up as a multi-turn transcript.
        short = "Them: resumen breve. Me: otro fragmento. Them: y otro."
        assert unflatten_transcript(short) == short

    def test_prose_colons_inside_a_giant_line_are_not_split_on(self):
        flat = (
            "Them: " + _long(500) + " Entonces: mira esto " + _long(500)
            + " https://ejemplo.cl/x " + _long(500)
        )
        out = unflatten_transcript(flat)
        assert out.count("\n") == 0

    def test_a_learned_label_is_recovered_mid_line(self):
        flat = "Rolando: hola\nDavid: " + _long(900) + " Rolando: " + _long(900)
        out = unflatten_transcript(flat)
        starts = [ln.split(":")[0] for ln in out.splitlines() if ln.strip()]
        assert starts == ["Rolando", "David", "Rolando"]

    def test_only_the_long_lines_are_rewritten(self):
        short_line = "Me: corto Them: tambien corto"
        flat = "Them: " + _long(900) + " Me: " + _long(900)
        out = unflatten_transcript(short_line + "\n" + flat)
        assert out.splitlines()[0] == short_line

    def test_an_empty_body_is_returned_as_is(self):
        assert unflatten_transcript("") == ""

    def test_an_indented_line_does_not_gain_a_leading_blank_line(self):
        # The whitespace run this consumes has to be BETWEEN turns. A line's own
        # leading indentation is not a turn boundary.
        flat = "  Me: " + _long(900) + " Them: " + _long(900)
        out = unflatten_transcript(flat)
        assert not out.startswith(chr(10))
        assert out.splitlines()[0].startswith("  Me:")
        assert len(out.splitlines()) == 2

    def test_repairing_twice_changes_nothing_the_second_time(self):
        flat = "Them: " + _long(900) + " Me: " + _long(900) + " Them: " + _long(900)
        once = unflatten_transcript(flat)
        assert unflatten_transcript(once) == once

    def test_the_threshold_is_configurable(self):
        text = "Them: hola Me: que tal"
        assert unflatten_transcript(text, threshold=10) == "Them: hola\nMe: que tal"


class TestParseAppliesTheRepair:
    def test_a_flattened_paste_parses_into_turns(self):
        flat = "Them: " + _long(900) + " Me: " + _long(900)
        text = "Meeting Title: Reunion\nDate: Aug 1\n\nTranscript:\n\n" + flat
        parsed = parse_drive_transcript_md(text, "x.md", default_year=2026)
        assert len(parsed["transcript"].splitlines()) == 2
        # char_count follows the repaired body, since that is what gets written.
        assert parsed["char_count"] == len(parsed["transcript"])

    def test_an_ordinary_paste_is_unaffected(self):
        parsed = parse_drive_transcript_md(SAMPLE_MD, "x.md", default_year=2026)
        assert parsed["transcript"].splitlines()[0].startswith("Me:")
        assert len(parsed["transcript"].splitlines()) == 2
