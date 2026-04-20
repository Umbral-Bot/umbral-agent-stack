"""Tests for ``notion.operation_trace`` manual regularization breadcrumb.

Covers:

- ``OpsLogger.notion_operation`` event shape, truncation, multiple targets.
- ``dry_run`` does not write to the log file.
- ``operation_id`` is auto-generated when not provided and preserved when given.
- ``details`` / transcript-like payloads are truncated aggressively and
  never allow long page body or prompt content to reach ``ops_log.jsonl``.
- ``scripts/notion_trace_operation.py`` CLI: dry-run and execute paths,
  JSON output, and the Comgrap Dynamo regression example.
"""
from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from infra.ops_logger import OpsLogger


REPO_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = REPO_ROOT / "scripts" / "notion_trace_operation.py"


# Comgrap Dynamo regression — documented in docs/78 and the Granola skill.
COMGRAP_RAW = "3485f443-fb5c-81e9-ae88-fe2fb7cd7b54"
COMGRAP_TASK = "df938460-fdee-4752-b9d4-293bede5e541"
COMGRAP_PROJECT = "3485f443-fb5c-8198-9f54-fc5882302bf2"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ops_logger(tmp_path):
    return OpsLogger(log_dir=tmp_path)


# ---------------------------------------------------------------------------
# OpsLogger.notion_operation
# ---------------------------------------------------------------------------


class TestNotionOperationEvent:
    def test_emits_notion_operation_trace_event(self, ops_logger):
        ev = ops_logger.notion_operation(
            actor="david",
            action="regularize_granola_capitalization",
            reason="task_only_capitalization_corrected_to_project_task",
            raw_page_id=COMGRAP_RAW,
            target_page_ids=[COMGRAP_TASK, COMGRAP_PROJECT],
            source="vps_curl",
            source_kind="manual_regularization",
            notion_reads=3,
            notion_writes=5,
            status="ok",
            details="created project, linked raw and task, added cross comments",
        )

        assert ev["event"] == "notion.operation_trace"
        assert ev["actor"] == "david"
        assert ev["action"] == "regularize_granola_capitalization"
        assert ev["reason"] == "task_only_capitalization_corrected_to_project_task"
        assert ev["raw_page_id"] == COMGRAP_RAW
        assert ev["target_page_ids"] == [COMGRAP_TASK, COMGRAP_PROJECT]
        assert ev["source"] == "vps_curl"
        assert ev["source_kind"] == "manual_regularization"
        assert ev["notion_reads"] == 3
        assert ev["notion_writes"] == 5
        assert ev["status"] == "ok"
        assert "details" in ev

        events = ops_logger.read_events(event_filter="notion.operation_trace")
        assert len(events) == 1
        assert events[0]["operation_id"] == ev["operation_id"]
        assert events[0]["target_page_ids"] == [COMGRAP_TASK, COMGRAP_PROJECT]
        assert "ts" in events[0]

    def test_auto_generates_operation_id_when_missing(self, ops_logger):
        ev = ops_logger.notion_operation(
            actor="copilot",
            action="example",
            reason="missing-op-id",
        )
        op_id = ev["operation_id"]
        assert op_id
        # Must be a parseable UUID when the caller does not provide one.
        parsed = uuid.UUID(op_id)
        assert str(parsed) == op_id

    def test_preserves_provided_operation_id(self, ops_logger):
        provided = "regularize-comgrap-2026-04-20"
        ev = ops_logger.notion_operation(
            actor="copilot",
            action="regularize_granola_capitalization",
            reason="task_only_capitalization_corrected_to_project_task",
            operation_id=provided,
        )
        assert ev["operation_id"] == provided

    def test_blank_operation_id_is_replaced_with_uuid(self, ops_logger):
        ev = ops_logger.notion_operation(
            actor="copilot",
            action="example",
            reason="blank",
            operation_id="   ",
        )
        assert ev["operation_id"]
        uuid.UUID(ev["operation_id"])  # must parse


class TestNotionOperationTargets:
    def test_supports_multiple_target_page_ids(self, ops_logger):
        ev = ops_logger.notion_operation(
            actor="copilot",
            action="regularize_granola_capitalization",
            reason="multi-target",
            target_page_ids=[COMGRAP_TASK, COMGRAP_PROJECT, COMGRAP_RAW],
        )
        assert ev["target_page_ids"] == [COMGRAP_TASK, COMGRAP_PROJECT, COMGRAP_RAW]

    def test_deduplicates_target_page_ids(self, ops_logger):
        ev = ops_logger.notion_operation(
            actor="copilot",
            action="example",
            reason="dedup",
            target_page_ids=[COMGRAP_TASK, COMGRAP_TASK, COMGRAP_PROJECT],
        )
        assert ev["target_page_ids"] == [COMGRAP_TASK, COMGRAP_PROJECT]

    def test_caps_target_page_ids_to_25_entries(self, ops_logger):
        many = [f"page-{i}" for i in range(200)]
        ev = ops_logger.notion_operation(
            actor="copilot",
            action="example",
            reason="cap",
            target_page_ids=many,
        )
        assert len(ev["target_page_ids"]) == 25

    def test_handles_empty_or_missing_target_page_ids(self, ops_logger):
        ev = ops_logger.notion_operation(
            actor="copilot", action="example", reason="empty",
            target_page_ids=None,
        )
        assert "target_page_ids" not in ev
        ev2 = ops_logger.notion_operation(
            actor="copilot", action="example", reason="empty2",
            target_page_ids=[],
        )
        assert "target_page_ids" not in ev2


class TestNotionOperationSanitization:
    def test_details_is_truncated(self, ops_logger):
        huge = "x" * 10_000
        ev = ops_logger.notion_operation(
            actor="copilot",
            action="example",
            reason="truncate-details",
            details=huge,
        )
        # Must be much smaller than the raw payload.
        assert len(ev["details"]) <= 500
        assert ev["details"].startswith("x")

    def test_does_not_persist_raw_transcript_like_payload(self, ops_logger):
        # Simulate a caller that mistakenly tries to dump a whole transcript
        # into "details". The logger must NOT store it fully on disk.
        fake_transcript = ("\n".join([f"[00:{i:02d}] David: bla bla bla" for i in range(2000)]))
        assert len(fake_transcript) > 10_000

        ops_logger.notion_operation(
            actor="copilot",
            action="example",
            reason="truncate-raw",
            details=fake_transcript,
        )

        raw_text = ops_logger.path.read_text(encoding="utf-8")
        # The stored line must stay bounded; the original transcript must not
        # be persisted verbatim.
        for line in raw_text.splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") == "notion.operation_trace":
                assert len(event.get("details", "")) <= 500
        assert fake_transcript not in raw_text

    def test_reason_and_action_and_actor_are_truncated(self, ops_logger):
        ev = ops_logger.notion_operation(
            actor="a" * 5_000,
            action="b" * 5_000,
            reason="c" * 5_000,
            status="d" * 5_000,
        )
        assert len(ev["actor"]) <= 120
        assert len(ev["action"]) <= 120
        assert len(ev["reason"]) <= 300
        assert len(ev["status"]) <= 60

    def test_invalid_notion_reads_writes_are_dropped(self, ops_logger):
        ev = ops_logger.notion_operation(
            actor="copilot",
            action="example",
            reason="bad-counts",
            notion_reads="not-a-number",  # type: ignore[arg-type]
            notion_writes=None,
        )
        assert "notion_reads" not in ev
        assert "notion_writes" not in ev


class TestNotionOperationDryRun:
    def test_dry_run_returns_event_without_writing(self, ops_logger):
        ev = ops_logger.notion_operation(
            actor="david",
            action="regularize_granola_capitalization",
            reason="dry-run",
            dry_run=True,
        )
        assert ev["dry_run"] is True
        assert ev["event"] == "notion.operation_trace"
        assert not ops_logger.path.exists() or ops_logger.path.read_text(encoding="utf-8") == ""
        assert ops_logger.read_events(event_filter="notion.operation_trace") == []


# ---------------------------------------------------------------------------
# scripts/notion_trace_operation.py CLI
# ---------------------------------------------------------------------------


def _run_cli(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(CLI_PATH), *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
        check=False,
    )


class TestNotionTraceOperationCLI:
    def test_dry_run_does_not_touch_log(self, tmp_path):
        proc = _run_cli([
            "--dry-run",
            "--actor", "copilot",
            "--action", "regularize_granola_capitalization",
            "--reason", "task_only_capitalization_corrected_to_project_task",
            "--raw-page-id", COMGRAP_RAW,
            "--target-page-id", COMGRAP_TASK,
            "--target-page-id", COMGRAP_PROJECT,
            "--log-dir", str(tmp_path),
        ])
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout.strip())
        assert payload["event"] == "notion.operation_trace"
        assert payload["dry_run"] is True
        assert payload["raw_page_id"] == COMGRAP_RAW
        assert payload["target_page_ids"] == [COMGRAP_TASK, COMGRAP_PROJECT]
        assert not (tmp_path / "ops_log.jsonl").exists()

    def test_execute_writes_event_to_log(self, tmp_path):
        proc = _run_cli([
            "--actor", "copilot",
            "--action", "regularize_granola_capitalization",
            "--reason", "task_only_capitalization_corrected_to_project_task",
            "--raw-page-id", COMGRAP_RAW,
            "--target-page-id", COMGRAP_TASK,
            "--target-page-id", COMGRAP_PROJECT,
            "--notion-reads", "3",
            "--notion-writes", "5",
            "--status", "ok",
            "--details", "created project, linked raw and task, added cross comments",
            "--log-dir", str(tmp_path),
        ])
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout.strip())
        assert payload["event"] == "notion.operation_trace"
        assert payload["operation_id"]
        assert payload["ops_log_path"].endswith("ops_log.jsonl")

        log_file = tmp_path / "ops_log.jsonl"
        assert log_file.exists()
        lines = [l for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 1
        stored = json.loads(lines[0])
        assert stored["event"] == "notion.operation_trace"
        assert stored["operation_id"] == payload["operation_id"]
        assert stored["target_page_ids"] == [COMGRAP_TASK, COMGRAP_PROJECT]
        assert stored["notion_reads"] == 3
        assert stored["notion_writes"] == 5

    def test_preserves_explicit_operation_id(self, tmp_path):
        proc = _run_cli([
            "--actor", "copilot",
            "--action", "regularize_granola_capitalization",
            "--reason", "with-explicit-op-id",
            "--operation-id", "regularize-comgrap-2026-04-20",
            "--log-dir", str(tmp_path),
        ])
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout.strip())
        assert payload["operation_id"] == "regularize-comgrap-2026-04-20"

    def test_required_args_missing(self, tmp_path):
        proc = _run_cli([
            "--actor", "copilot",
            "--log-dir", str(tmp_path),
        ])
        assert proc.returncode != 0
        assert "--action" in proc.stderr or "required" in proc.stderr.lower()
