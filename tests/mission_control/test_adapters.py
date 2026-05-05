"""Tests de adapters: best-effort, no levantan excepción ante fuentes ausentes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mission_control.adapters import openclaw, quota


def test_openclaw_missing_file(tmp_path):
    snap = openclaw.read_snapshot(tmp_path / "nope.json")
    assert snap.available is False
    assert snap.error and "file not found" in snap.error
    assert snap.agents == []
    assert snap.channels == []


def test_openclaw_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    snap = openclaw.read_snapshot(p)
    assert snap.available is False
    assert "JSONDecodeError" in (snap.error or "")


def test_openclaw_valid_with_list(tmp_path):
    p = tmp_path / "good.json"
    p.write_text(
        json.dumps(
            {
                "agents": [
                    {"name": "alpha", "role": "writer"},
                    {"name": "beta", "role": "reviewer"},
                ],
                "channels": [{"name": "chan-1"}],
            }
        ),
        encoding="utf-8",
    )
    snap = openclaw.read_snapshot(p)
    assert snap.available is True
    assert len(snap.agents) == 2
    assert snap.agents[0]["name"] == "alpha"
    assert snap.channels[0]["name"] == "chan-1"


def test_openclaw_valid_with_dict(tmp_path):
    p = tmp_path / "dict.json"
    p.write_text(
        json.dumps({"agents": {"alpha": {"role": "writer"}}, "channels": {}}),
        encoding="utf-8",
    )
    snap = openclaw.read_snapshot(p)
    assert snap.available is True
    assert snap.agents == [{"name": "alpha", "role": "writer"}]


def test_quota_missing_file(tmp_path):
    state = quota.read_state(tmp_path / "nope.json")
    assert state["available"] is False
    assert "not found" in state["error"]


def test_quota_valid_file(tmp_path):
    p = tmp_path / "q.json"
    payload = {"window_start": "2026-05-05T00:00:00Z", "tokens_used": 1234}
    p.write_text(json.dumps(payload), encoding="utf-8")
    state = quota.read_state(p)
    assert state["available"] is True
    assert state["state"] == payload
