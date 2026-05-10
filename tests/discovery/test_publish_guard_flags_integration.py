"""Integration test for ``publish_guard`` × ``PublishFlags`` (#405).

Verifies:
* When ``flags.allows_real_publish() is False`` (the fail-closed default),
  ``assert_can_publish`` returns ``None`` AND emits a
  ``publish_guard.dry_run`` marker AND a ``publish_guard.pass`` line.
  Crucially, no real publish path is invoked: the guard never receives a
  publisher to call.
* When ``flags.allows_real_publish() is True``, ``assert_can_publish``
  returns ``None`` (gates passed) and emits ``publish_guard.pass`` only.
* The integration does NOT change the contract for callers that pass no
  ``flags`` argument (covered by ``test_publish_guard.py`` already).

In Wave 2.A there is no real publisher wired through the guard, so this
test only verifies the boundary the guard exposes via ops_log.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from scripts.discovery.lib.publish_flags import PublishFlags
from scripts.discovery.lib.publish_guard import assert_can_publish


def _all_ok_page(content_hash: str = "h" * 64) -> dict:
    return {
        "id": "page-405",
        "properties": {
            "aprobado_contenido": {"checkbox": True},
            "autorizar_publicacion": {"checkbox": True},
            "gate_invalidado": {"checkbox": False},
            "Fuente primaria": {"url": "https://example.com/source"},
            "Canal": {"select": {"name": "linkedin"}},
            "content_hash": content_hash,
        },
    }


def _read_log(path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln]


def _open_db(tmp_path):
    return sqlite3.connect(tmp_path / "state.sqlite")


# --------------------------------------------------------------------------- #
# Fail-closed flags → marker emitted, no real-write path reached
# --------------------------------------------------------------------------- #

def test_failclosed_flags_emit_dry_run_marker_and_block_real_publish(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    flags = PublishFlags(
        publish_enabled=False,
        dry_run=True,
        max_posts=1,
        max_posts_per_day=1,
    )
    assert flags.allows_real_publish() is False

    db = _open_db(tmp_path)
    try:
        result = assert_can_publish(_all_ok_page(), "h" * 64, db, flags=flags)
    finally:
        db.close()

    assert result is None
    entries = _read_log(isolate_ops_log)
    events = [e["event"] for e in entries]
    assert "publish_guard.dry_run" in events
    assert "publish_guard.pass" in events

    dry_rec = next(e for e in entries if e["event"] == "publish_guard.dry_run")
    assert dry_rec["publish_enabled"] is False
    assert dry_rec["dry_run"] is True
    assert dry_rec["max_posts"] == 1
    assert dry_rec["max_posts_per_day"] == 1
    assert dry_rec["page_id"] == "page-405"


def test_default_env_is_failclosed(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    """The defaults that ship with the contract block real writes."""
    flags = PublishFlags.from_env({})
    assert flags.allows_real_publish() is False

    db = _open_db(tmp_path)
    try:
        assert_can_publish(_all_ok_page(), "h" * 64, db, flags=flags) is None
    finally:
        db.close()

    events = [e["event"] for e in _read_log(isolate_ops_log)]
    assert events.count("publish_guard.dry_run") == 1


# --------------------------------------------------------------------------- #
# All-on flags → no marker, only the pass line
# --------------------------------------------------------------------------- #

def test_allon_flags_skip_dry_run_marker(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    flags = PublishFlags(
        publish_enabled=True,
        dry_run=False,
        max_posts=1,
        max_posts_per_day=1,
    )
    assert flags.allows_real_publish() is True

    db = _open_db(tmp_path)
    try:
        result = assert_can_publish(_all_ok_page(), "h" * 64, db, flags=flags)
    finally:
        db.close()

    assert result is None
    entries = _read_log(isolate_ops_log)
    events = [e["event"] for e in entries]
    assert events == ["publish_guard.pass"]


# --------------------------------------------------------------------------- #
# Backward compatibility — no ``flags`` argument
# --------------------------------------------------------------------------- #

def test_call_without_flags_preserves_legacy_behavior(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    """When ``flags`` is omitted, behaviour is byte-identical to pre-#405."""
    db = _open_db(tmp_path)
    try:
        result = assert_can_publish(_all_ok_page(), "h" * 64, db)
    finally:
        db.close()

    assert result is None
    entries = _read_log(isolate_ops_log)
    assert len(entries) == 1
    assert entries[0]["event"] == "publish_guard.pass"
