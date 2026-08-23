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
    drop_unparsed_transcripts,
    load_notion_records,
    main,
    run_item,
    select_items,
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
