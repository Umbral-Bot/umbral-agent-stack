"""
Tests for the Drive transcript completeness audit (Q11-T2).

The audit exists to answer one question with evidence: is the body the feeder
hands to Notion the full verbatim transcript, or Granola's AI summary? Two
properties carry that weight and are pinned here.

1. A flattened transcript -- a real meeting whose paste lost its newlines --
   must NOT be called a summary. Seven of the 108 files in the live folder are
   flattened, one of them 84,843 characters on a single line; a turn-count rule
   alone would reject every one of them.
2. The output must carry no meeting content. It is written to be pasted into an
   acta.
"""

import json

import pytest

from scripts.vm.granola_drive_transcript_audit import (
    EMPTY,
    EXECUTABLE_CLASSES,
    SUMMARY_ONLY,
    UNCERTAIN,
    VERBATIM,
    VERBATIM_FLATTENED,
    audit_record,
    audit_root,
    classify,
    exclude_hint,
    format_table,
    main,
    not_executable,
    summarize,
)

SECRET = "clausula de confidencialidad numero 4815162342"


def _turns(n, *, chars_per_turn=200):
    """A transcript body shaped like Granola's export: one turn per line."""
    lines = []
    for i in range(n):
        speaker = "Me" if i % 2 else "Them"
        lines.append(f"{speaker}: " + "palabra " * (chars_per_turn // 8))
    return "\n".join(lines)


def _record(body, *, filename="a.md", size_bytes=None, title="Reunion"):
    return {
        "filename": filename,
        "relative_path": f"Granola/{filename}",
        "size_bytes": size_bytes if size_bytes is not None else len(body) + 80,
        "parsed": {"title": title, "date": "2026-08-01", "transcript": body},
    }


class TestClassify:
    def test_a_normal_transcript_is_verbatim(self):
        assert classify(has_header=True, turns=40, body_chars=20000, longest_line_chars=300) == VERBATIM

    def test_an_empty_body_is_vacio(self):
        assert classify(has_header=True, turns=0, body_chars=0, longest_line_chars=0) == EMPTY

    def test_a_short_body_without_turns_is_a_summary(self):
        assert classify(has_header=True, turns=1, body_chars=1163, longest_line_chars=1103) == SUMMARY_ONLY

    def test_a_large_body_on_one_line_is_a_flattened_transcript_not_a_summary(self):
        # `workshop embudo inteligente.md`: 84,843 chars, one line, one turn
        # marker. Calling that a summary would reject a whole real meeting.
        assert (
            classify(has_header=True, turns=1, body_chars=84843, longest_line_chars=84843)
            == VERBATIM_FLATTENED
        )

    def test_a_missing_transcript_header_is_never_auto_approved(self):
        assert classify(has_header=False, turns=40, body_chars=20000, longest_line_chars=300) == UNCERTAIN

    def test_a_large_body_with_few_turns_and_no_long_line_is_uncertain(self):
        # Neither dialogue-shaped nor flattened: a human decides.
        assert classify(has_header=True, turns=2, body_chars=20000, longest_line_chars=400) == UNCERTAIN

    def test_a_body_below_the_length_floor_is_not_verbatim(self):
        assert classify(has_header=True, turns=30, body_chars=900, longest_line_chars=40) != VERBATIM

    def test_only_verbatim_is_executable(self):
        assert VERBATIM in EXECUTABLE_CLASSES
        for other in (VERBATIM_FLATTENED, SUMMARY_ONLY, EMPTY, UNCERTAIN):
            assert other not in EXECUTABLE_CLASSES


class TestAuditRecord:
    def test_counts_me_and_them_turns(self):
        body = "Them: hola\nMe: que tal\nThem: bien\nMe: dale"
        row = audit_record(_record(body), "Transcript:\n" + body)
        assert row["turns_me"] == 2
        assert row["turns_them"] == 2
        assert row["turns_total"] == 4

    def test_detects_the_transcript_header_in_the_raw_file(self):
        body = _turns(10)
        assert audit_record(_record(body), "Meeting Title: x\nTranscript:\n" + body)["has_transcript_header"]
        assert not audit_record(_record(body), "Meeting Title: x\n" + body)["has_transcript_header"]

    def test_body_ratio_exposes_a_file_whose_bulk_sits_before_the_header(self):
        # A low ratio means most of the file is being dropped by the parser --
        # the summary-above-transcript shape.
        body = "Them: hola\nMe: ok"
        raw = ("resumen " * 500) + "\nTranscript:\n" + body
        assert audit_record(_record(body), raw)["body_ratio"] < 0.1

    def test_reports_the_longest_line_so_flattening_is_visible(self):
        body = "Them: " + "x" * 60000
        row = audit_record(_record(body), "Transcript:\n" + body)
        assert row["longest_line_chars"] >= 60000
        assert row["class"] == VERBATIM_FLATTENED

    def test_blank_lines_do_not_count_as_turns(self):
        body = "Them: hola\n\n\nMe: ok\n\n"
        row = audit_record(_record(body), "Transcript:\n" + body)
        assert row["lines"] == 2

    def test_the_output_carries_no_meeting_content(self):
        body = f"Them: {SECRET}\nMe: entendido"
        row = audit_record(_record(body), "Transcript:\n" + body)
        assert SECRET not in json.dumps(row, ensure_ascii=False)

    def test_a_transcript_using_real_names_still_counts_turns(self):
        body = "Rolando: hola\nDavid: que tal\nRolando: bien\nDavid: dale"
        row = audit_record(_record(body), "Transcript:\n" + body)
        assert row["turns_total"] == 4
        assert row["distinct_labels"] == 2
        # ...but the Me:/Them: columns stay honest about what they saw.
        assert row["turns_me"] == 0


class TestAuditRoot:
    def _write(self, root, name, body, *, header=True):
        text = "Meeting Title: Reunion\nDate: Aug 1\n"
        if header:
            text += "\nTranscript:\n\n"
        text += body
        (root / name).write_text(text, encoding="utf-8")

    def test_classifies_a_real_folder(self, tmp_path):
        self._write(tmp_path, "full.md", _turns(30))
        self._write(tmp_path, "flat.md", "Them: " + "x" * 60000)
        rows = audit_root(tmp_path, default_year=2026)
        by_name = {row["filename"]: row["class"] for row in rows}
        assert by_name["full.md"] == VERBATIM
        assert by_name["flat.md"] == VERBATIM_FLATTENED

    def test_skips_the_files_the_feeder_skips(self, tmp_path):
        # Same eligibility rules as the ingest, so the audit and the feeder
        # cannot disagree about which files are even in play.
        self._write(tmp_path, "full.md", _turns(30))
        (tmp_path / "tiny.md").write_text("x", encoding="utf-8")
        (tmp_path / "Indice_Transcripciones_Locales_2026.md").write_text(
            "Meeting Title: idx\nTranscript:\n" + _turns(30), encoding="utf-8"
        )
        assert {row["filename"] for row in audit_root(tmp_path, default_year=2026)} == {"full.md"}

    def test_summarize_counts_by_class(self, tmp_path):
        self._write(tmp_path, "a.md", _turns(30))
        self._write(tmp_path, "b.md", _turns(30))
        assert summarize(audit_root(tmp_path, default_year=2026)) == {VERBATIM: 2}

    def test_a_missing_root_raises_instead_of_reporting_zero_files(self, tmp_path):
        # "0 files audited" would read as "nothing to worry about".
        with pytest.raises(FileNotFoundError):
            audit_root(tmp_path / "nope", default_year=2026)


class TestNotExecutable:
    """The audit's actionable output: names that go straight into --exclude."""

    def _row(self, filename, klass):
        return {"filename": filename, "class": klass}

    def test_lists_everything_that_is_not_clean_verbatim(self):
        rows = [
            self._row("ok.md", VERBATIM),
            self._row("flat.md", VERBATIM_FLATTENED),
            self._row("short.md", SUMMARY_ONLY),
        ]
        assert not_executable(rows) == ["flat.md", "short.md"]

    def test_an_all_verbatim_folder_holds_nothing_back(self):
        assert not_executable([self._row("ok.md", VERBATIM)]) == []
        assert exclude_hint([self._row("ok.md", VERBATIM)]) == ""

    def test_the_hint_quotes_names_with_spaces_and_accents(self):
        # Every real Granola filename has both; an unquoted hint would be
        # useless to paste.
        rows = [self._row("Conecta 3 -USM.md", VERBATIM_FLATTENED)]
        assert exclude_hint(rows) == '--exclude "Conecta 3 -USM.md"'


class TestCli:
    def _write(self, root, name, body):
        (root / name).write_text(
            "Meeting Title: Reunion\nDate: Aug 1\n\nTranscript:\n\n" + body, encoding="utf-8"
        )

    def test_json_output_to_a_file(self, tmp_path, monkeypatch, capsys):
        self._write(tmp_path, "a.md", _turns(30))
        out = tmp_path / "audit.json"
        monkeypatch.setattr(
            "sys.argv",
            ["audit", "--root", str(tmp_path), "--json", "--output", str(out), "--default-year", "2026"],
        )
        assert main() == 0
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["count"] == 1
        assert doc["by_class"] == {VERBATIM: 1}
        # The summary line on stdout must not carry content either.
        assert "palabra" not in capsys.readouterr().out

    def test_only_filters_to_the_files_a_gap_report_selected(self, tmp_path, monkeypatch, capsys):
        self._write(tmp_path, "a.md", _turns(30))
        self._write(tmp_path, "b.md", _turns(30))
        monkeypatch.setattr(
            "sys.argv",
            ["audit", "--root", str(tmp_path), "--json", "--only", "b.md", "--default-year", "2026"],
        )
        assert main() == 0
        doc = json.loads(capsys.readouterr().out)
        assert [row["filename"] for row in doc["rows"]] == ["b.md"]

    def test_only_is_repeatable_and_never_split_on_commas(self, tmp_path, monkeypatch, capsys):
        """The bug this replaces: `--only "a,b.md,c.md"` split a real filename.

        `BIM Forum - GT política, regulación y mandantes.md` contains a comma,
        so a comma-separated --only silently audited 10 of 11 requested files
        and reported the result as if it were complete.
        """
        comma_name = "BIM Forum - GT política, regulación y mandantes.md"
        self._write(tmp_path, comma_name, _turns(30))
        self._write(tmp_path, "otra.md", _turns(30))
        monkeypatch.setattr(
            "sys.argv",
            [
                "audit", "--root", str(tmp_path), "--json", "--default-year", "2026",
                "--only", comma_name,
                "--only", "otra.md",
            ],
        )
        assert main() == 0
        doc = json.loads(capsys.readouterr().out)
        assert sorted(row["filename"] for row in doc["rows"]) == sorted([comma_name, "otra.md"])

    def test_an_only_that_matches_nothing_aborts(self, tmp_path, monkeypatch, capsys):
        # Reporting on fewer files than asked, silently, is worse than no audit.
        self._write(tmp_path, "a.md", _turns(30))
        monkeypatch.setattr(
            "sys.argv",
            ["audit", "--root", str(tmp_path), "--json", "--only", "ghost.md", "--default-year", "2026"],
        )
        assert main() == 1
        assert "matched nothing" in capsys.readouterr().err

    def test_the_table_renders_without_content(self, tmp_path):
        body = f"Them: {SECRET}\nMe: ok"
        rows = [audit_record(_record(body), "Transcript:\n" + body)]
        table = format_table(rows)
        assert SECRET not in table
        assert "a.md" in table
