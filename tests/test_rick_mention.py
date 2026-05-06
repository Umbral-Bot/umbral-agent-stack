"""Tests for dispatcher.rick_mention adapter (Ola 1b ADR 05 §2.1, §2.2)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dispatcher import rick_mention


UID_DAVID = "1e3d872b-594c-81b1-9b96-000230c0b088"
UID_OTHER = "0000ffff-1111-2222-3333-444455556666"


@pytest.fixture
def trace_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p = tmp_path / "delegations.jsonl"
    monkeypatch.setenv("UMBRAL_DELEGATIONS_LOG", str(p))
    return p


def test_is_rick_mention_basic_match() -> None:
    assert rick_mention.is_rick_mention(
        "hola @rick haz X", UID_DAVID, {UID_DAVID}
    ) is True


def test_is_rick_mention_orchestrator_alias() -> None:
    assert rick_mention.is_rick_mention(
        "hola @rick-orchestrator", UID_DAVID, {UID_DAVID}
    ) is True


def test_is_rick_mention_rejects_non_allowlisted_author() -> None:
    assert rick_mention.is_rick_mention(
        "hola @rick", UID_OTHER, {UID_DAVID}
    ) is False


def test_is_rick_mention_no_mention_returns_false() -> None:
    assert rick_mention.is_rick_mention(
        "hola sin mention", UID_DAVID, {UID_DAVID}
    ) is False


def test_is_rick_mention_case_insensitive() -> None:
    assert rick_mention.is_rick_mention(
        "@RICK hola", UID_DAVID, {UID_DAVID}
    ) is True


def test_handle_rick_mention_enqueues_triage_envelope(trace_log: Path) -> None:
    queue = MagicMock()
    rick_mention.handle_rick_mention(
        text="hola @rick test",
        comment_id="cmt-123abcdef",
        page_id="page-456abcdef",
        page_kind="control_room",
        author=UID_DAVID,
        wc=MagicMock(),
        queue=queue,
        scheduler=MagicMock(),
    )
    assert queue.enqueue.call_count == 1
    envelope = queue.enqueue.call_args[0][0]
    assert envelope["task"] == "rick.orchestrator.triage"
    assert envelope["team"] == "rick-orchestrator"
    assert envelope["task_type"] == "triage"
    assert envelope["source"] == "notion-poller"
    assert envelope["source_kind"] == "notion.comment.mention"
    assert envelope["trace_id"]
    assert envelope["task_id"]
    inp = envelope["input"]
    assert inp["kind"] == "notion.comment.mention"
    assert inp["comment_id"] == "cmt-123abcdef"
    assert inp["page_id"] == "page-456abcdef"
    assert inp["page_kind"] == "control_room"
    assert inp["author"] == UID_DAVID
    assert inp["text"] == "hola @rick test"
    assert "received_at" in inp


def test_handle_rick_mention_writes_delegation_trace(trace_log: Path) -> None:
    rick_mention.handle_rick_mention(
        text="hola @rick test",
        comment_id="cmt-abc",
        page_id="page-xyz",
        page_kind="deliverable",
        author=UID_DAVID,
        wc=MagicMock(),
        queue=MagicMock(),
        scheduler=MagicMock(),
    )
    assert trace_log.exists()
    rec = json.loads(trace_log.read_text().splitlines()[-1])
    assert rec["from"] == "channel-adapter:notion-poller"
    assert rec["to"] == "rick-orchestrator"
    assert rec["intent"] == "triage"
    assert rec["ref"]["comment_id"] == "cmt-abc"
    assert rec["ref"]["page_id"] == "page-xyz"
    assert "trace_id" in rec
    assert "ts" in rec
    # secret-output-guard: no raw text or author UUID full in summary
    assert "hola @rick test" not in rec["summary"]
    assert UID_DAVID not in rec["summary"]
