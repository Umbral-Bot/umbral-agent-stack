"""Tests for worker.tasks._trace.append_delegation (Ola 1b ADR 05 §2.3)."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from worker.tasks import _trace


@pytest.fixture
def log_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p = tmp_path / "state" / "delegations.jsonl"
    monkeypatch.setenv("UMBRAL_DELEGATIONS_LOG", str(p))
    return p


def test_creates_file_with_mode_600(log_path: Path) -> None:
    _trace.append_delegation({"from": "a", "to": "b", "intent": "triage"})
    assert log_path.exists()
    assert (log_path.stat().st_mode & 0o777) == 0o600


def test_writes_valid_json_with_auto_ts_and_trace_id(log_path: Path) -> None:
    _trace.append_delegation({"from": "a", "to": "b", "intent": "triage"})
    line = log_path.read_text().strip()
    rec = json.loads(line)
    assert rec["from"] == "a"
    assert rec["to"] == "b"
    assert rec["intent"] == "triage"
    assert "ts" in rec and "T" in rec["ts"]
    assert "trace_id" in rec and len(rec["trace_id"]) == 32


def test_respects_provided_trace_id(log_path: Path) -> None:
    _trace.append_delegation({
        "from": "a", "to": "b", "intent": "triage",
        "trace_id": "deadbeef" * 4,
    })
    rec = json.loads(log_path.read_text().strip())
    assert rec["trace_id"] == "deadbeef" * 4


def test_truncates_summary_to_200_chars(log_path: Path) -> None:
    long_summary = "x" * 500
    _trace.append_delegation({
        "from": "a", "to": "b", "intent": "triage",
        "summary": long_summary,
    })
    rec = json.loads(log_path.read_text().strip())
    assert len(rec["summary"]) == 200


@pytest.mark.parametrize("bad_key", ["text", "secret", "token", "api_key", "password"])
def test_rejects_forbidden_keys(log_path: Path, bad_key: str) -> None:
    with pytest.raises(ValueError, match="forbidden key"):
        _trace.append_delegation({
            "from": "a", "to": "b", "intent": "triage",
            bad_key: "leaked-value",
        })
    assert not log_path.exists()


def test_concurrent_writes_no_corruption(log_path: Path) -> None:
    n_threads = 10
    n_per_thread = 10

    def writer(tid: int) -> None:
        for i in range(n_per_thread):
            _trace.append_delegation({
                "from": f"thread-{tid}", "to": "b", "intent": "triage",
                "summary": f"msg-{tid}-{i}",
            })

    threads = [threading.Thread(target=writer, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = log_path.read_text().splitlines()
    assert len(lines) == n_threads * n_per_thread
    for line in lines:
        rec = json.loads(line)
        assert rec["to"] == "b"
        assert rec["intent"] == "triage"
