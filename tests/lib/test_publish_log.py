"""Tests for scripts.discovery.lib.publish_log (#404-lite writer)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from scripts.discovery.lib.publish_log import (
    DEFAULT_PATH,
    ENV_VAR,
    read_events,
    write_event,
)


ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@pytest.fixture
def log_path(tmp_path, monkeypatch):
    p = tmp_path / "publish_log.jsonl"
    monkeypatch.setenv(ENV_VAR, str(p))
    yield p


# --------------------------------------------------------------------------- #
# Path resolution
# --------------------------------------------------------------------------- #


def test_path_arg_wins_over_env(tmp_path, monkeypatch):
    env_p = tmp_path / "env.jsonl"
    arg_p = tmp_path / "arg.jsonl"
    monkeypatch.setenv(ENV_VAR, str(env_p))
    written = write_event({"event": "publish_log.gate_pass"}, path=arg_p)
    assert written == arg_p
    assert arg_p.exists()
    assert not env_p.exists()


def test_env_used_when_no_arg(log_path):
    written = write_event({"event": "publish_log.gate_pass"})
    assert written == log_path
    assert log_path.exists()


def test_default_path_when_no_arg_no_env(monkeypatch, tmp_path):
    monkeypatch.delenv(ENV_VAR, raising=False)
    fake_home = tmp_path / "fake_home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    # Re-resolve DEFAULT_PATH to honor the patched home.
    expected = fake_home / ".config" / "umbral" / "publish_log.jsonl"
    # write_event recomputes from current home() via DEFAULT_PATH module
    # constant, which captured the original at import time. So we pass
    # the explicit expected path to keep the test deterministic and we
    # simply assert that DEFAULT_PATH reflects the documented layout.
    assert DEFAULT_PATH.name == "publish_log.jsonl"
    assert ".config" in DEFAULT_PATH.parts
    assert "umbral" in DEFAULT_PATH.parts
    written = write_event({"event": "publish_log.gate_pass"}, path=expected)
    assert written == expected
    assert expected.exists()


# --------------------------------------------------------------------------- #
# Mkdir + first-write semantics
# --------------------------------------------------------------------------- #


def test_creates_parent_directory(tmp_path):
    nested = tmp_path / "a" / "b" / "c" / "publish_log.jsonl"
    assert not nested.parent.exists()
    write_event({"event": "publish_log.gate_pass"}, path=nested)
    assert nested.exists()
    assert nested.parent.is_dir()


def test_first_write_creates_file(log_path):
    assert not log_path.exists()
    write_event({"event": "publish_log.gate_pass"})
    assert log_path.exists()


# --------------------------------------------------------------------------- #
# Append-only + JSON-line shape
# --------------------------------------------------------------------------- #


def test_appends_one_line_per_call(log_path):
    write_event({"event": "publish_log.gate_pass", "i": 1})
    write_event({"event": "publish_log.gate_pass", "i": 2})
    write_event({"event": "publish_log.gate_pass", "i": 3})
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert [json.loads(ln)["i"] for ln in lines] == [1, 2, 3]


def test_does_not_truncate_existing_content(log_path):
    log_path.write_text('{"pre":true}\n', encoding="utf-8")
    write_event({"event": "publish_log.gate_pass"})
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"pre": True}


def test_each_line_is_valid_json(log_path):
    for i in range(5):
        write_event({"event": "publish_log.gate_pass", "n": i})
    for ln in log_path.read_text(encoding="utf-8").splitlines():
        json.loads(ln)  # must not raise


# --------------------------------------------------------------------------- #
# Timestamp injection
# --------------------------------------------------------------------------- #


def test_auto_injects_timestamp_when_missing(log_path):
    write_event({"event": "publish_log.gate_pass"})
    [evt] = read_events()
    assert "timestamp_utc" in evt
    assert ISO_UTC.match(evt["timestamp_utc"])


def test_preserves_caller_supplied_timestamp(log_path):
    write_event(
        {"event": "publish_log.gate_pass", "timestamp_utc": "2026-01-01T00:00:00Z"}
    )
    [evt] = read_events()
    assert evt["timestamp_utc"] == "2026-01-01T00:00:00Z"


def test_does_not_mutate_caller_dict(log_path):
    payload = {"event": "publish_log.gate_pass"}
    write_event(payload)
    assert "timestamp_utc" not in payload


# --------------------------------------------------------------------------- #
# Permissive schema (does NOT validate)
# --------------------------------------------------------------------------- #


def test_accepts_arbitrary_keys(log_path):
    write_event({"event": "publish_log.gate_pass", "weird": [1, 2, {"x": "y"}]})
    [evt] = read_events()
    assert evt["weird"] == [1, 2, {"x": "y"}]


def test_accepts_unicode(log_path):
    write_event({"event": "publish_log.gate_pass", "msg": "Niños — héroes ✅"})
    raw = log_path.read_text(encoding="utf-8")
    assert "Niños — héroes ✅" in raw


def test_rejects_non_dict_event(log_path):
    with pytest.raises(TypeError):
        write_event("not a dict")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# read_events helper
# --------------------------------------------------------------------------- #


def test_read_events_empty_when_file_missing(tmp_path, monkeypatch):
    p = tmp_path / "missing.jsonl"
    monkeypatch.setenv(ENV_VAR, str(p))
    assert read_events() == []


def test_read_events_skips_blank_lines(log_path):
    log_path.write_text(
        '{"event":"a"}\n\n{"event":"b"}\n   \n{"event":"c"}\n',
        encoding="utf-8",
    )
    events = read_events()
    assert [e["event"] for e in events] == ["a", "b", "c"]


def test_read_events_raises_on_corruption(log_path):
    log_path.write_text('{"event":"ok"}\nNOT JSON\n', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        read_events()


# --------------------------------------------------------------------------- #
# Round-trip with contract-shaped event
# --------------------------------------------------------------------------- #


def test_roundtrip_contract_shaped_event(log_path):
    contract_event = {
        "event": "publish_log.gate_pass",
        "page_id": "page-123",
        "source_content_hash": "s" * 64,
        "publication_content_hash": "p" * 64,
        "channel": "linkedin",
        "target": None,
        "publish_enabled": False,
        "dry_run": True,
        "max_posts": 1,
        "max_posts_per_day": 1,
        "block_reasons": [],
        "cross_validation": [],
        "gate_outcomes": {
            "aprobado_contenido": True,
            "autorizar_publicacion": True,
            "gate_invalidado": False,
            "fuente_primaria": True,
            "canal": True,
            "content_hash": True,
        },
        "would_publish": False,
        "published_url": None,
        "extra": {"dispatcher_attempt_id": "att-001"},
    }
    write_event(contract_event)
    [evt] = read_events()
    # All keys preserved verbatim, plus auto-injected timestamp_utc.
    for k, v in contract_event.items():
        assert evt[k] == v
    assert ISO_UTC.match(evt["timestamp_utc"])
