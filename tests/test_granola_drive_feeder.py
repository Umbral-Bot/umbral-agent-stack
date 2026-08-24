"""
Tests for the recurring Drive->Notion Granola feeder (Q11-T1).

Covers what the one-shot P1.1b flow never needed: per-run caps, the guard that
must hold before any write, and the end-to-end ``main()`` wiring whose exit
code is the Scheduled Task's only health signal.
"""

import json

import pytest

from scripts.vm.granola_drive_feeder import (
    _redact,
    default_state_dir,
    drop_excluded,
    drop_unparsed_transcripts,
    load_notion_records,
    main,
    run_item,
    select_items,
    transcript_shrink_reason,
    unmatched_exclusions,
    worker_verdict_agrees,
)


def _item(relative_path, action="create", page_id=""):
    return {
        "relative_path": relative_path,
        "action": action,
        "match_strategy": "",
        "matched_page": {"page_id": page_id} if page_id else None,
        "payload": {"title": relative_path, "content": "x", "dry_run": True},
    }


class TestSelectItems:
    def test_caps_creates_and_defers_the_rest(self):
        batch = [_item(f"Granola/c{i}.md") for i in range(15)]
        selected, deferred = select_items(batch, max_creates=10, max_updates=10)
        assert len(selected) == 10
        assert len(deferred) == 5

    def test_creates_and_updates_have_independent_caps(self):
        batch = [_item(f"Granola/c{i}.md") for i in range(3)]
        batch += [_item(f"Granola/u{i}.md", "update_transcript") for i in range(3)]
        selected, deferred = select_items(batch, max_creates=2, max_updates=1)
        assert [i["action"] for i in selected] == ["create", "create", "update_transcript"]
        assert len(deferred) == 3

    def test_preserves_batch_order_so_the_backlog_drains_deterministically(self):
        batch = [_item(f"Granola/c{i}.md") for i in range(5)]
        selected, deferred = select_items(batch, max_creates=2, max_updates=0)
        assert [i["relative_path"] for i in selected] == ["Granola/c0.md", "Granola/c1.md"]
        assert [i["relative_path"] for i in deferred] == [
            "Granola/c2.md",
            "Granola/c3.md",
            "Granola/c4.md",
        ]

    def test_unknown_actions_are_never_selected(self):
        batch = [_item("Granola/a.md", "review_ambiguous"), _item("Granola/b.md", "skip")]
        selected, deferred = select_items(batch, max_creates=10, max_updates=10)
        assert selected == []
        assert len(deferred) == 2

    def test_zero_cap_selects_nothing(self):
        selected, deferred = select_items([_item("Granola/a.md")], max_creates=0, max_updates=0)
        assert selected == []
        assert len(deferred) == 1

    def test_a_negative_cap_is_clamped_not_read_as_unlimited(self):
        """One stray -1 must not turn a bounded daily job into a backlog drain."""
        batch = [_item(f"Granola/c{i}.md") for i in range(5)]
        selected, deferred = select_items(batch, max_creates=-1, max_updates=-5)
        assert selected == []
        assert len(deferred) == 5


class TestWorkerVerdict:
    """The guard returns "" for agreement, or a reason string that blocks the write."""

    def test_create_agrees_when_worker_matched_nothing(self):
        assert worker_verdict_agrees("create", {"matched_existing": False}) == ""

    def test_create_disagrees_when_worker_found_a_page(self):
        assert worker_verdict_agrees("create", {"matched_existing": True})

    def test_a_missing_key_blocks_a_create_instead_of_approving_it(self):
        # bool(None) is False, so reading this with .get would turn "the worker
        # never answered" into "confirmed, nothing exists" and write a duplicate.
        assert "omitted matched_existing" in worker_verdict_agrees("create", {})

    def test_a_missing_key_blocks_an_update_too(self):
        assert "omitted matched_existing" in worker_verdict_agrees("update_transcript", {})

    def test_update_agrees_only_when_worker_matched(self):
        assert worker_verdict_agrees("update_transcript", {"matched_existing": True}) == ""
        assert worker_verdict_agrees("update_transcript", {"matched_existing": False})

    def test_update_blocked_when_the_worker_resolved_a_different_page(self):
        # The worker's ladder is wider than the gap-check's (granola_document_id,
        # source_url, export_signature), so the two can land on different pages.
        reason = worker_verdict_agrees(
            "update_transcript",
            {"matched_existing": True, "page_id": "other-page"},
            expected_page_id="our-page",
        )
        assert "different page" in reason

    def test_update_agrees_when_both_resolved_the_same_page(self):
        assert (
            worker_verdict_agrees(
                "update_transcript",
                {"matched_existing": True, "page_id": "p1"},
                expected_page_id="p1",
            )
            == ""
        )

    def test_unknown_action_never_agrees(self):
        assert worker_verdict_agrees("skip", {"matched_existing": True})


class _FakeWorker:
    """Records every call so a test can assert no second (write) call happened."""

    def __init__(self, dry_result, execute_result=None, raise_on=None):
        self.dry_result = dry_result
        self.execute_result = execute_result or {}
        self.raise_on = raise_on
        self.calls = []

    def __call__(self, url, token, payload):
        self.calls.append(dict(payload))
        if self.raise_on == len(self.calls):
            raise RuntimeError("boom")
        if payload.get("dry_run"):
            return {"result": self.dry_result}
        return {"result": self.execute_result}


def _dry(**overrides):
    base = {"matched_existing": False, "reconciliation_action": "create", "dry_run": True}
    base.update(overrides)
    return base


class TestRunItem:
    def test_dry_run_mode_never_sends_a_write(self, monkeypatch):
        fake = _FakeWorker(_dry())
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=False)
        assert row["error"] == ""
        assert row["executed"] is False
        assert [c["dry_run"] for c in fake.calls] == [True]

    def test_execute_writes_after_a_matching_dry_run(self, monkeypatch):
        fake = _FakeWorker(
            _dry(),
            {"page_id": "p1", "url": "https://notion.so/p1", "reconciliation_action": "create"},
        )
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert row["executed"] is True
        assert row["written"] is True
        assert row["page_id"] == "p1"
        assert [c["dry_run"] for c in fake.calls] == [True, False]

    def test_create_whose_dry_run_matched_an_existing_page_is_not_written(self, monkeypatch):
        fake = _FakeWorker(_dry(matched_existing=True, reconciliation_action="reconcile"))
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert row["declined"]
        assert row["executed"] is False
        # The guard has to stop BEFORE the write, not report it afterwards.
        assert len(fake.calls) == 1

    def test_a_noop_verdict_skips_the_pointless_second_round_trip(self, monkeypatch):
        fake = _FakeWorker(_dry(matched_existing=True, reconciliation_action="noop"))
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(
            _item("Granola/a.md", "update_transcript", page_id="p1"),
            worker_url="u",
            worker_token="t",
            execute=True,
        )
        assert "noop" in row["declined"]
        assert len(fake.calls) == 1

    def test_refuses_to_continue_if_the_worker_did_not_honour_dry_run(self, monkeypatch):
        # If POST #1 was not a dry run it may already have written; POST #2
        # would then be a second write.
        fake = _FakeWorker(_dry(dry_run=False))
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert "dry_run" in row["error"]
        assert len(fake.calls) == 1

    def test_a_worker_noop_on_execute_is_not_counted_as_written(self, monkeypatch):
        fake = _FakeWorker(_dry(), {"page_id": "p1", "reconciliation_action": "noop"})
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert row["executed"] is True
        assert row["written"] is False

    def test_a_failing_dry_run_is_reported_not_raised(self, monkeypatch):
        fake = _FakeWorker({}, raise_on=1)
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert "dry-run failed" in row["error"]

    def test_a_failing_write_is_reported_not_raised(self, monkeypatch):
        fake = _FakeWorker(_dry(), raise_on=2)
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert "execute failed" in row["error"]
        assert row["executed"] is False


def _recon(previous_chars, new_chars):
    """A dry-run reconciliation block carrying the two lengths that matter."""
    return {
        "previous_metrics": {"char_count": previous_chars},
        "new_metrics": {"char_count": new_chars},
    }


class TestTranscriptShrinkReason:
    """An update may grow a page or leave it alone. It may not gut it.

    ``replace_blocks_in_page`` deletes every existing block before writing the
    new ones, and ``decide_reconciliation`` calls any metric difference
    "reconcile" -- shorter or longer alike. Nothing under this function refuses
    a shrink, so this is where a summary landing on a full transcript stops.
    """

    def test_a_create_is_never_blocked(self):
        # A create has no page to overwrite, whatever the metrics say.
        assert transcript_shrink_reason("create", {"reconciliation": _recon(30000, 500)}) == ""

    def test_growth_passes(self):
        # The one real update in the Q11 backlog: an AI summary page (3,600
        # chars) replaced by the 29,877-char verbatim transcript.
        assert transcript_shrink_reason("update_transcript", {"reconciliation": _recon(3600, 29877)}) == ""

    def test_an_identical_length_passes(self):
        assert transcript_shrink_reason("update_transcript", {"reconciliation": _recon(29877, 29877)}) == ""

    def test_a_small_shrink_inside_the_tolerance_passes(self):
        # A re-paste that normalizes whitespace must not need a human.
        assert transcript_shrink_reason("update_transcript", {"reconciliation": _recon(10000, 9500)}) == ""

    def test_a_summary_replacing_a_transcript_is_blocked(self):
        reason = transcript_shrink_reason("update_transcript", {"reconciliation": _recon(29877, 3600)})
        assert "29877" in reason and "3600" in reason

    def test_a_shrink_just_past_the_tolerance_is_blocked(self):
        assert transcript_shrink_reason("update_transcript", {"reconciliation": _recon(10000, 8999)})

    def test_missing_reconciliation_is_a_refusal_not_a_pass(self):
        # Fail-open here loses a transcript, so an absent block blocks.
        assert transcript_shrink_reason("update_transcript", {})

    def test_missing_metrics_are_a_refusal_not_a_pass(self):
        assert transcript_shrink_reason("update_transcript", {"reconciliation": {}})

    def test_a_non_numeric_char_count_is_a_refusal(self):
        result = {"reconciliation": {"previous_metrics": {"char_count": "many"}, "new_metrics": {"char_count": 10}}}
        assert transcript_shrink_reason("update_transcript", result)

    def test_a_page_with_no_recorded_length_cannot_shrink(self):
        # previous=0 means there is nothing to lose, not "shrink to zero".
        assert transcript_shrink_reason("update_transcript", {"reconciliation": _recon(0, 500)}) == ""

    def test_the_tolerance_is_configurable(self):
        result = {"reconciliation": _recon(10000, 7000)}
        assert transcript_shrink_reason("update_transcript", result, tolerance=0.5) == ""
        assert transcript_shrink_reason("update_transcript", result, tolerance=0.0)


class TestShrinkGuardContractWithTheWorker:
    """The guard reads a shape the worker owns. Pin the seam, not a mock of it.

    ``transcript_shrink_reason`` reaches into
    ``reconciliation.previous_metrics.char_count`` -- keys produced by
    ``worker.tasks.granola_finality.decide_reconciliation`` and forwarded
    verbatim by ``granola.process_transcript``'s dry-run branch. If those keys
    are ever renamed, every hand-written ``_recon()`` above keeps passing while
    the live guard starts declining every update as "omitted metrics". So this
    test builds the dict with the worker's own function.
    """

    def _decision(self, previous_chars, new_content):
        from worker.tasks.granola_finality import decide_reconciliation

        return decide_reconciliation(
            existing={"char_count": previous_chars, "content_hash": "old"},
            new_content=new_content,
            source_updated_at="",
        ).as_dict()

    def test_a_real_decision_blocks_a_real_shrink(self):
        decision = self._decision(30000, "Them: resumen corto.")
        reason = transcript_shrink_reason("update_transcript", {"reconciliation": decision})
        assert "30000" in reason

    def test_a_real_decision_lets_a_real_growth_through(self):
        decision = self._decision(3600, "Them: " + "palabra " * 5000)
        assert transcript_shrink_reason("update_transcript", {"reconciliation": decision}) == ""


class TestRunItemShrinkGuard:
    def _shrinking_update(self):
        return _item("Granola/a.md", "update_transcript", page_id="p1")

    def _dry_shrink(self):
        return _dry(
            matched_existing=True,
            reconciliation_action="reconcile",
            reconciliation=_recon(29877, 3600),
        )

    def test_a_shrinking_update_is_declined_before_the_write(self, monkeypatch):
        fake = _FakeWorker(self._dry_shrink())
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(self._shrinking_update(), worker_url="u", worker_token="t", execute=True)
        assert "shrink" in row["declined"]
        assert row["written"] is False
        # The guard has to stop BEFORE the write, not report it afterwards.
        assert len(fake.calls) == 1

    def test_allow_shrink_lets_an_operator_override_it(self, monkeypatch):
        fake = _FakeWorker(
            self._dry_shrink(),
            {"page_id": "p1", "reconciliation_action": "reconcile"},
        )
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(
            self._shrinking_update(),
            worker_url="u",
            worker_token="t",
            execute=True,
            allow_shrink=True,
        )
        assert row["declined"] == ""
        assert row["written"] is True
        assert len(fake.calls) == 2

    def test_a_growing_update_still_writes(self, monkeypatch):
        fake = _FakeWorker(
            _dry(
                matched_existing=True,
                reconciliation_action="reconcile",
                reconciliation=_recon(3600, 29877),
            ),
            {"page_id": "p1", "reconciliation_action": "reconcile"},
        )
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(self._shrinking_update(), worker_url="u", worker_token="t", execute=True)
        assert row["declined"] == ""
        assert row["written"] is True

    def test_a_create_is_unaffected_by_the_guard(self, monkeypatch):
        fake = _FakeWorker(
            _dry(reconciliation=_recon(99999, 10)),
            {"page_id": "p1", "reconciliation_action": "create"},
        )
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(_item("Granola/a.md"), worker_url="u", worker_token="t", execute=True)
        assert row["declined"] == ""
        assert row["written"] is True

    def test_the_compared_lengths_land_on_the_row(self, monkeypatch):
        fake = _FakeWorker(
            _dry(matched_existing=True, reconciliation_action="reconcile", reconciliation=_recon(3600, 29877)),
            {"page_id": "p1", "reconciliation_action": "reconcile"},
        )
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(self._shrinking_update(), worker_url="u", worker_token="t", execute=True)
        assert row["dry_run_previous_chars"] == 3600
        assert row["dry_run_new_chars"] == 29877

    def test_an_unverifiable_comparison_is_visible_in_the_row(self, monkeypatch):
        """A legacy page with no Trazabilidad reports 0, and the write proceeds.

        Refusing it would block the pipeline's whole purpose -- attaching a
        verbatim transcript to a page that only holds an AI summary -- so the
        run report has to show the 0 instead of the guard hiding it.
        """
        fake = _FakeWorker(
            _dry(matched_existing=True, reconciliation_action="reconcile", reconciliation=_recon(0, 29877)),
            {"page_id": "p1", "reconciliation_action": "reconcile"},
        )
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(self._shrinking_update(), worker_url="u", worker_token="t", execute=True)
        assert row["declined"] == ""
        assert row["written"] is True
        assert row["dry_run_previous_chars"] == 0

    def test_a_dry_run_pass_is_also_blocked_so_the_report_shows_it(self, monkeypatch):
        # Without --execute the item would never be written anyway, but the run
        # report is the only place David sees WHY -- so it must say "shrink",
        # not stay silent until the day someone passes --execute.
        fake = _FakeWorker(self._dry_shrink())
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        row = run_item(self._shrinking_update(), worker_url="u", worker_token="t", execute=False)
        assert "shrink" in row["declined"]


class TestDropExcluded:
    """An operator holding one file back for one run -- listed, never silent."""

    def test_matches_a_bare_filename(self):
        selected = [_item("Granola/a.md"), _item("Granola/b.md")]
        ok, held = drop_excluded(selected, {"a.md"})
        assert [i["relative_path"] for i in ok] == ["Granola/b.md"]
        assert [i["relative_path"] for i in held] == ["Granola/a.md"]

    def test_matches_the_full_relative_path(self):
        ok, held = drop_excluded([_item("Granola/a.md")], {"Granola/a.md"})
        assert ok == []
        assert len(held) == 1

    def test_an_empty_exclusion_set_changes_nothing(self):
        selected = [_item("Granola/a.md"), _item("Granola/b.md")]
        ok, held = drop_excluded(selected, set())
        assert len(ok) == 2
        assert held == []

    def test_an_exclusion_that_matches_nothing_leaves_the_item_in(self):
        # drop_excluded itself stays a pure filter; catching the typo is
        # unmatched_exclusions' job, and main() aborts on it.
        ok, held = drop_excluded([_item("Granola/a.md")], {"ghost.md"})
        assert len(ok) == 1
        assert held == []

    def test_an_excluded_item_does_not_spend_a_cap_slot(self):
        """Order matters: filter, then cap.

        Capping first would let a held-back file consume one of the run's ten
        create slots and push a perfectly good transcript into tomorrow.
        """
        batch = [_item(f"Granola/c{i}.md") for i in range(11)]
        batch, held = drop_excluded(batch, {"c3.md"})
        selected, deferred = select_items(batch, max_creates=10, max_updates=10)
        assert len(held) == 1
        assert len(selected) == 10
        assert deferred == []
        assert "Granola/c3.md" not in [i["relative_path"] for i in selected]

    def test_a_name_with_accents_and_spaces_matches(self):
        # Every real Granola filename looks like this.
        name = "Granola/Reunión Post konstruedu con Rolando.md"
        ok, held = drop_excluded([_item(name)], {"Reunión Post konstruedu con Rolando.md"})
        assert ok == []
        assert len(held) == 1


def _drive(filename):
    """One inventory record, the shape build_inventory emits."""
    return {"filename": filename, "relative_path": "Granola/" + filename}


class TestUnmatchedExclusions:
    """A mistyped --exclude fails OPEN: the file it was meant to hold back gets
    written. Real Granola filenames make the typo likely -- accents, double
    spaces, and at least one comma."""

    def test_a_matching_exclusion_reports_nothing_missing(self):
        assert unmatched_exclusions([_drive("a.md")], {"a.md"}) == []

    def test_the_full_relative_path_also_counts_as_matched(self):
        assert unmatched_exclusions([_drive("a.md")], {"Granola/a.md"}) == []

    def test_a_typo_is_reported(self):
        assert unmatched_exclusions([_drive("a.md")], {"ghost.md"}) == ["ghost.md"]

    def test_reports_every_miss_not_just_the_first(self):
        missing = unmatched_exclusions([_drive("a.md")], {"x.md", "y.md", "a.md"})
        assert missing == ["x.md", "y.md"]

    def test_no_exclusions_requested_reports_nothing(self):
        assert unmatched_exclusions([_drive("a.md")], set()) == []

    def test_an_exclusion_for_an_already_ingested_file_is_redundant_not_a_typo(self):
        """The Scheduled Task's standing --exclude has to survive its own success.

        Checking against the batch instead of the inventory would fail the task
        every morning from the day the held-back file is finally ingested, moves
        to ``skip``, and leaves the batch.
        """
        assert unmatched_exclusions([_drive("a.md")], {"a.md"}) == []

    def test_a_name_that_matches_no_drive_file_at_all_is_a_typo(self):
        assert unmatched_exclusions([], {"a.md"}) == ["a.md"]

    def test_a_real_granola_filename_with_a_comma_matches(self):
        # The name that exposed this: a comma-splitting filter silently
        # dropped it, so it was audited as if it did not exist.
        name = "BIM Forum - GT política, regulación y mandantes.md"
        assert unmatched_exclusions([_drive(name)], {name}) == []


class TestRedact:
    def test_masks_a_bearer_token(self):
        assert "secretvalue" not in _redact("Authorization: Bearer secretvalue123")

    def test_masks_a_labelled_token(self):
        assert "abcdefgh12345" not in _redact('{"token": "abcdefgh12345"}')

    def test_leaves_an_ordinary_error_message_intact(self):
        message = "Notion API error (401) API token is invalid."
        assert _redact(message) == message

    def test_handles_empty_input(self):
        assert _redact("") == ""


class TestUnparsedTranscriptGuard:
    """An empty transcript must never be sent as an update.

    The parser only recognizes a line that is exactly ``Transcript:``. If
    Granola relabels its export, a large .md parses to an empty body and the
    payload becomes a single 76-char header -- which, sent as an update the
    worker matches, replaces a full meeting page with that header.
    """

    def test_drops_an_item_whose_transcript_did_not_parse(self):
        selected = [_item("Granola/a.md", "update_transcript")]
        drive = {"Granola/a.md": {"parsed": {"char_count": 0}}}
        ok, unparsed = drop_unparsed_transcripts(selected, drive)
        assert ok == []
        assert len(unparsed) == 1

    def test_keeps_an_item_with_a_real_transcript(self):
        selected = [_item("Granola/a.md", "update_transcript")]
        drive = {"Granola/a.md": {"parsed": {"char_count": 4200}}}
        ok, unparsed = drop_unparsed_transcripts(selected, drive)
        assert len(ok) == 1
        assert unparsed == []

    def test_an_item_missing_from_the_inventory_is_dropped_not_sent(self):
        ok, unparsed = drop_unparsed_transcripts([_item("Granola/ghost.md")], {})
        assert ok == []
        assert len(unparsed) == 1


class TestLoadNotionRecords:
    def test_reads_a_valid_snapshot(self, tmp_path):
        path = tmp_path / "snap.json"
        path.write_text(json.dumps({"records": [{"page_id": "p1"}]}), encoding="utf-8")
        assert load_notion_records(str(path)) == [{"page_id": "p1"}]

    def test_tolerates_a_utf8_bom(self, tmp_path):
        # PowerShell 5.1's Out-File -Encoding utf8 writes one.
        path = tmp_path / "snap.json"
        path.write_text(json.dumps({"records": [{"page_id": "p1"}]}), encoding="utf-8-sig")
        assert load_notion_records(str(path)) == [{"page_id": "p1"}]

    def test_an_empty_snapshot_is_refused_not_read_as_create_everything(self, tmp_path):
        path = tmp_path / "snap.json"
        path.write_text(json.dumps({"records": []}), encoding="utf-8")
        with pytest.raises(RuntimeError, match="no records"):
            load_notion_records(str(path))

    def test_a_wrong_shaped_file_is_refused(self, tmp_path):
        path = tmp_path / "snap.json"
        path.write_text(json.dumps({"pages": [{"page_id": "p1"}]}), encoding="utf-8")
        with pytest.raises(RuntimeError, match="not a snapshot"):
            load_notion_records(str(path))

    def test_a_bare_list_is_refused_rather_than_crashing(self, tmp_path):
        path = tmp_path / "snap.json"
        path.write_text(json.dumps([{"page_id": "p1"}]), encoding="utf-8")
        with pytest.raises(RuntimeError, match="not a snapshot"):
            load_notion_records(str(path))


class TestDefaultStateDir:
    def test_prefers_localappdata(self, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\x\AppData\Local")
        assert "AppData" in str(default_state_dir())

    def test_falls_back_to_the_windows_temp_names_not_posix_tmpdir(self, monkeypatch):
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.delenv("TMPDIR", raising=False)
        monkeypatch.setenv("TEMP", r"C:\Temp")
        # Falling through to "." would drop run reports into the process CWD,
        # which the Scheduled Task sets to the repo checkout.
        assert str(default_state_dir()).startswith(r"C:\Temp")


SAMPLE_MD = """Meeting Title: Reunion de prueba
Date: Mar 30
Meeting participants: David, Otro

Transcript:

Them: hola
Me: chau
"""


def _write_drive(tmp_path):
    root = tmp_path / "Granola"
    root.mkdir()
    (root / "Reunion de prueba.md").write_text(SAMPLE_MD + "x" * 200, encoding="utf-8")
    return root


class TestMain:
    """``main()``'s exit code is the Scheduled Task's only health signal."""

    def _argv(self, monkeypatch, *args):
        monkeypatch.setattr("sys.argv", ["granola_drive_feeder.py", *args])

    def test_offline_run_reports_the_gap_and_exits_clean(self, tmp_path, monkeypatch):
        root = _write_drive(tmp_path)
        snap = tmp_path / "snap.json"
        snap.write_text(
            json.dumps({"records": [{"page_id": "p1", "normalized_title": "otra", "date": "2020-01-01"}]}),
            encoding="utf-8",
        )
        state = tmp_path / "state"
        self._argv(
            monkeypatch,
            "--root", str(root),
            "--notion-pages", str(snap),
            "--skip-worker",
            "--state-dir", str(state),
        )
        assert main() == 0
        reports = list(state.glob("run-*.json"))
        assert len(reports) == 1
        report = json.loads(reports[0].read_text(encoding="utf-8"))
        assert report["drive_files"] == 1
        assert report["summary"]["create"] == 1
        assert report["fatal_error"] == ""

    def test_a_missing_drive_root_still_leaves_a_run_report(self, tmp_path, monkeypatch):
        # Google Drive mounts G:\ lazily; a task firing at logon can beat it.
        # Without a report the operator sees only Task Scheduler's 0x1.
        state = tmp_path / "state"
        self._argv(
            monkeypatch,
            "--root", str(tmp_path / "does-not-exist"),
            "--skip-worker",
            "--state-dir", str(state),
        )
        assert main() == 1
        report = json.loads(next(state.glob("run-*.json")).read_text(encoding="utf-8"))
        assert "FileNotFoundError" in report["fatal_error"]

    def test_an_empty_snapshot_aborts_instead_of_creating_everything(self, tmp_path, monkeypatch):
        root = _write_drive(tmp_path)
        snap = tmp_path / "snap.json"
        snap.write_text(json.dumps({"records": []}), encoding="utf-8")
        state = tmp_path / "state"
        self._argv(
            monkeypatch,
            "--root", str(root),
            "--notion-pages", str(snap),
            "--skip-worker",
            "--state-dir", str(state),
        )
        assert main() == 1
        report = json.loads(next(state.glob("run-*.json")).read_text(encoding="utf-8"))
        assert "no records" in report["fatal_error"]

    def test_a_mistyped_exclusion_aborts_before_any_worker_call(self, tmp_path, monkeypatch):
        """Fail closed. A typo here writes the file it was meant to hold back."""
        root = _write_drive(tmp_path)
        snap = tmp_path / "snap.json"
        snap.write_text(
            json.dumps({"records": [{"page_id": "p1", "normalized_title": "otra", "date": "2020-01-01"}]}),
            encoding="utf-8",
        )
        state = tmp_path / "state"
        calls = []
        monkeypatch.setattr(
            "scripts.vm.granola_drive_feeder.post_task",
            lambda *a, **k: calls.append(a) or {"result": {}},
        )
        self._argv(
            monkeypatch,
            "--root", str(root),
            "--notion-pages", str(snap),
            "--state-dir", str(state),
            "--exclude", "no-existe.md",
            "--execute",
        )
        assert main() == 1
        report = json.loads(next(state.glob("run-*.json")).read_text(encoding="utf-8"))
        assert "--exclude matched nothing" in report["fatal_error"]
        assert "no-existe.md" in report["fatal_error"]
        assert calls == []

    def test_an_exclusion_for_a_file_already_in_notion_does_not_fail_the_task(
        self, tmp_path, monkeypatch
    ):
        """The standing --exclude on the daily task must survive its own success.

        Once the held-back file is finally ingested it becomes a ``skip`` and
        leaves the batch. A batch-scoped check would then fail the Scheduled
        Task every morning; the check is inventory-scoped so it does not.
        """
        root = _write_drive(tmp_path)
        name = next(root.glob("*.md")).name
        snap = tmp_path / "snap.json"
        # A Notion page that already matches the one Drive file -> skip, so the
        # batch is empty while the file is still very much on disk.
        snap.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "page_id": "p1",
                            "normalized_title": "x",
                            "date": "2020-01-01",
                            "shared_folder_path": "Granola/" + name,
                            "sha1": "does-not-match",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        state = tmp_path / "state"
        self._argv(
            monkeypatch,
            "--root", str(root),
            "--notion-pages", str(snap),
            "--skip-worker",
            "--state-dir", str(state),
            "--exclude", name,
        )
        assert main() == 0
        report = json.loads(next(state.glob("run-*.json")).read_text(encoding="utf-8"))
        assert report["fatal_error"] == ""

    def test_an_exclusion_pasted_with_a_trailing_cr_still_matches(self, tmp_path, monkeypatch):
        """These arrive pasted out of a CRLF file or an acta. Not a typo."""
        root = _write_drive(tmp_path)
        snap = tmp_path / "snap.json"
        snap.write_text(
            json.dumps({"records": [{"page_id": "p1", "normalized_title": "otra", "date": "2020-01-01"}]}),
            encoding="utf-8",
        )
        state = tmp_path / "state"
        name = next(root.glob("*.md")).name
        self._argv(
            monkeypatch,
            "--root", str(root),
            "--notion-pages", str(snap),
            "--skip-worker",
            "--state-dir", str(state),
            "--exclude", name + chr(13),
        )
        assert main() == 0
        report = json.loads(next(state.glob("run-*.json")).read_text(encoding="utf-8"))
        assert report["fatal_error"] == ""
        assert [i["relative_path"] for i in report["excluded"]] == ["Granola/" + name]

    def test_an_exclusion_that_matches_lets_the_run_proceed(self, tmp_path, monkeypatch):
        root = _write_drive(tmp_path)
        snap = tmp_path / "snap.json"
        snap.write_text(
            json.dumps({"records": [{"page_id": "p1", "normalized_title": "otra", "date": "2020-01-01"}]}),
            encoding="utf-8",
        )
        state = tmp_path / "state"
        name = next(root.glob("*.md")).name
        self._argv(
            monkeypatch,
            "--root", str(root),
            "--notion-pages", str(snap),
            "--skip-worker",
            "--state-dir", str(state),
            "--exclude", name,
        )
        assert main() == 0
        report = json.loads(next(state.glob("run-*.json")).read_text(encoding="utf-8"))
        assert report["fatal_error"] == ""
        assert [i["relative_path"] for i in report["excluded"]] == ["Granola/" + name]
        assert report["selected"] == []

    def test_a_declined_item_does_not_fail_the_run(self, tmp_path, monkeypatch):
        # A permanently red Scheduled Task trains its operator to ignore it.
        root = _write_drive(tmp_path)
        snap = tmp_path / "snap.json"
        snap.write_text(json.dumps({"records": [{"page_id": "p1"}]}), encoding="utf-8")
        state = tmp_path / "state"
        fake = _FakeWorker(_dry(matched_existing=True, reconciliation_action="reconcile"))
        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", fake)
        monkeypatch.setenv("WORKER_URL", "http://worker")
        monkeypatch.setenv("WORKER_TOKEN", "t")
        self._argv(
            monkeypatch,
            "--root", str(root),
            "--notion-pages", str(snap),
            "--state-dir", str(state),
        )
        assert main() == 0
        report = json.loads(next(state.glob("run-*.json")).read_text(encoding="utf-8"))
        assert report["results"][0]["declined"]
        assert report["results"][0]["executed"] is False

    def test_a_worker_error_fails_the_run(self, tmp_path, monkeypatch):
        root = _write_drive(tmp_path)
        snap = tmp_path / "snap.json"
        snap.write_text(json.dumps({"records": [{"page_id": "p1"}]}), encoding="utf-8")
        state = tmp_path / "state"
        monkeypatch.setattr(
            "scripts.vm.granola_drive_feeder.post_task", _FakeWorker({}, raise_on=1)
        )
        monkeypatch.setenv("WORKER_URL", "http://worker")
        monkeypatch.setenv("WORKER_TOKEN", "t")
        self._argv(
            monkeypatch,
            "--root", str(root),
            "--notion-pages", str(snap),
            "--state-dir", str(state),
        )
        assert main() == 1

    def test_report_is_flushed_before_the_worker_loop(self, tmp_path, monkeypatch):
        """A run killed mid-loop must not take the classification with it."""
        root = _write_drive(tmp_path)
        snap = tmp_path / "snap.json"
        snap.write_text(json.dumps({"records": [{"page_id": "p1"}]}), encoding="utf-8")
        state = tmp_path / "state"

        seen = {}

        def explode(url, token, payload):
            seen["report_existed"] = any(state.glob("run-*.json"))
            raise RuntimeError("killed")

        monkeypatch.setattr("scripts.vm.granola_drive_feeder.post_task", explode)
        monkeypatch.setenv("WORKER_URL", "http://worker")
        monkeypatch.setenv("WORKER_TOKEN", "t")
        self._argv(
            monkeypatch,
            "--root", str(root),
            "--notion-pages", str(snap),
            "--state-dir", str(state),
        )
        main()
        assert seen["report_existed"] is True
