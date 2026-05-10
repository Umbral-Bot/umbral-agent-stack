"""Integration test for ``publish_guard`` × ``PublishFlags`` (#405).

Wave 2.A semantics (post-hardening):

* When ``flags.allows_real_publish() is False`` and ``flags`` is passed
  explicitly, ``assert_can_publish`` RAISES :class:`PublishBlockedError`
  BEFORE evaluating editorial gates or touching the DB. It emits exactly
  one ``publish_guard.runtime_block`` ops_log entry. The error reasons
  match :meth:`PublishFlags.block_reasons`.
* When ``flags.allows_real_publish() is True``, behaviour matches the
  legacy gate-only path: emits a single ``publish_guard.pass`` and
  returns ``None``.
* When ``flags`` is omitted, behaviour is byte-identical to the pre-#405
  version (covered by ``test_publish_guard.py``).
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from scripts.discovery.lib.publish_flags import PublishFlags
from scripts.discovery.lib.publish_guard import (
    PublishBlockedError,
    assert_can_publish,
)


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
# Fail-closed flags → BLOCK (raise) before gates / DB
# --------------------------------------------------------------------------- #

def test_failclosed_flags_block_real_publish_with_runtime_block_event(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    """Default-shaped flags must raise PublishBlockedError before gates run."""
    flags = PublishFlags(
        publish_enabled=False,
        dry_run=True,
        max_posts=1,
        max_posts_per_day=1,
    )
    assert flags.allows_real_publish() is False

    db = _open_db(tmp_path)
    try:
        with pytest.raises(PublishBlockedError) as exc:
            assert_can_publish(_all_ok_page(), "h" * 64, db, flags=flags)
    finally:
        db.close()

    # Reason codes must mirror block_reasons() exactly.
    assert exc.value.reasons == flags.block_reasons()
    assert "publish_disabled" in exc.value.reasons
    assert "dry_run_enabled" in exc.value.reasons
    assert exc.value.page_id == "page-405"

    entries = _read_log(isolate_ops_log)
    events = [e["event"] for e in entries]
    # Exactly one runtime_block, no gate.pass / gate.block.
    assert events == ["publish_guard.runtime_block"]
    rec = entries[0]
    assert rec["publish_enabled"] is False
    assert rec["dry_run"] is True
    assert rec["max_posts"] == 1
    assert rec["max_posts_per_day"] == 1
    assert rec["reasons"] == flags.block_reasons()
    assert "cross_validation" in rec  # informational warnings echoed


def test_default_env_is_failclosed_and_raises(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    """The defaults that ship with the contract block real writes."""
    flags = PublishFlags.from_env({})
    assert flags.allows_real_publish() is False

    db = _open_db(tmp_path)
    try:
        with pytest.raises(PublishBlockedError):
            assert_can_publish(_all_ok_page(), "h" * 64, db, flags=flags)
    finally:
        db.close()

    events = [e["event"] for e in _read_log(isolate_ops_log)]
    assert events == ["publish_guard.runtime_block"]


def test_max_posts_zero_is_a_runtime_block_reason(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    flags = PublishFlags(
        publish_enabled=True,
        dry_run=False,
        max_posts=0,
        max_posts_per_day=1,
    )
    assert flags.allows_real_publish() is False

    db = _open_db(tmp_path)
    try:
        with pytest.raises(PublishBlockedError) as exc:
            assert_can_publish(_all_ok_page(), "h" * 64, db, flags=flags)
    finally:
        db.close()

    assert "max_posts_zero" in exc.value.reasons


# --------------------------------------------------------------------------- #
# All-on flags → no runtime block, only the gate pass line
# --------------------------------------------------------------------------- #

def test_allon_flags_pass_through_to_gates(
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
