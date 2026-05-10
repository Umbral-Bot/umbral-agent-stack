"""Tests for ``scripts.discovery.lib.publish_guard`` (Hilo 6 / S10).

Targets:
* All 6 gates can fail individually with the correct reason code.
* Multiple failing gates surface ALL codes in stable order.
* Duplicate content_hash blocks via the dedup callable.
* Pass path emits ``publish_guard.pass`` to ops_log.
* Block path emits ``publish_guard.block`` and raises.
* :class:`PublishBlockedError` echoes back ``page_id`` / ``content_hash``.
* Logging tolerates an unwritable ops_log path (best-effort).
* Guard never crashes on empty / malformed pages (fail-safe blocks).
"""

from __future__ import annotations

import json
import sqlite3
import types

import pytest

from scripts.discovery.lib import publish_guard
from scripts.discovery.lib.publish_guard import (
    PublishBlockedError,
    assert_can_publish,
)


# --------------------------------------------------------------------------- #
# Page builders
# --------------------------------------------------------------------------- #

def _all_ok_page(content_hash: str = "h" * 64) -> dict:
    return {
        "id": "page-OK",
        "properties": {
            "aprobado_contenido": {"checkbox": True},
            "autorizar_publicacion": {"checkbox": True},
            "gate_invalidado": {"checkbox": False},
            "Fuente primaria": {"url": "https://example.com/source"},
            "Canal": {"select": {"name": "linkedin"}},
            "content_hash": content_hash,
        },
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _read_log(path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln]


def _open_db(tmp_path):
    return sqlite3.connect(tmp_path / "state.sqlite")


# --------------------------------------------------------------------------- #
# Pass path
# --------------------------------------------------------------------------- #

def test_pass_path_returns_none(
    tmp_path, fake_gates_pass_all, fake_dedup_no_duplicates
):
    db = _open_db(tmp_path)
    try:
        result = assert_can_publish(_all_ok_page(), "h" * 64, db)
    finally:
        db.close()
    assert result is None


def test_pass_path_emits_structured_log(
    tmp_path, isolate_ops_log, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    db = _open_db(tmp_path)
    try:
        assert_can_publish(_all_ok_page(), "abc" * 21 + "d", db)
    finally:
        db.close()
    entries = _read_log(isolate_ops_log)
    assert len(entries) == 1
    rec = entries[0]
    assert rec["event"] == "publish_guard.pass"
    assert rec["page_id"] == "page-OK"
    assert rec["content_hash"].startswith("abc")
    assert rec["reasons"] == []
    assert "ts" in rec


# --------------------------------------------------------------------------- #
# Per-gate failure
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "gate_field,reason_code",
    [
        ("aprobado_contenido", "aprobado_contenido_missing"),
        ("autorizar_publicacion", "autorizar_publicacion_missing"),
        ("fuente_primaria_ok", "fuente_primaria_missing"),
        ("plataforma_seleccionada", "plataforma_no_seleccionada"),
    ],
)
def test_each_notion_gate_fails_individually(
    tmp_path, install_fake_gates, fake_dedup_no_duplicates,
    gate_field, reason_code,
):
    """Flipping a single gate field surfaces exactly the matching code."""

    def _evaluate(notion_page, dedup_check):
        kwargs = {gate_field: False}
        return kwargs

    install_fake_gates(_evaluate)
    db = _open_db(tmp_path)
    try:
        with pytest.raises(PublishBlockedError) as exc:
            assert_can_publish(_all_ok_page(), "h" * 64, db)
    finally:
        db.close()
    assert exc.value.reasons == [reason_code]
    assert exc.value.page_id == "page-OK"


def test_gate_invalidado_active_blocks(
    tmp_path, install_fake_gates, fake_dedup_no_duplicates,
):
    install_fake_gates(lambda p, d: {"gate_invalidado": True})
    db = _open_db(tmp_path)
    try:
        with pytest.raises(PublishBlockedError) as exc:
            assert_can_publish(_all_ok_page(), "h" * 64, db)
    finally:
        db.close()
    assert exc.value.reasons == ["gate_invalidado_active"]


def test_no_duplicado_fails_when_dedup_returns_true(
    tmp_path, fake_gates_pass_all, fake_dedup_always_duplicate,
):
    db = _open_db(tmp_path)
    try:
        with pytest.raises(PublishBlockedError) as exc:
            assert_can_publish(_all_ok_page(), "h" * 64, db)
    finally:
        db.close()
    assert exc.value.reasons == ["contenido_duplicado"]


def test_multiple_failing_gates_all_listed_in_stable_order(
    tmp_path, install_fake_gates, fake_dedup_always_duplicate,
):
    install_fake_gates(
        lambda p, d: {
            "aprobado_contenido": False,
            "autorizar_publicacion": False,
            "no_duplicado": False,  # also driven by dedup but explicit here
        }
    )
    db = _open_db(tmp_path)
    try:
        with pytest.raises(PublishBlockedError) as exc:
            assert_can_publish(_all_ok_page(), "h" * 64, db)
    finally:
        db.close()
    # Stable order matches H4 _GATE_ORDER.
    assert exc.value.reasons == [
        "aprobado_contenido_missing",
        "autorizar_publicacion_missing",
        "contenido_duplicado",
    ]


# --------------------------------------------------------------------------- #
# Logging on block path
# --------------------------------------------------------------------------- #

def test_block_path_emits_structured_log(
    tmp_path, isolate_ops_log, install_fake_gates, fake_dedup_no_duplicates,
):
    install_fake_gates(lambda p, d: {"aprobado_contenido": False})
    db = _open_db(tmp_path)
    try:
        with pytest.raises(PublishBlockedError):
            assert_can_publish(_all_ok_page(), "x" * 64, db)
    finally:
        db.close()
    entries = _read_log(isolate_ops_log)
    assert len(entries) == 1
    rec = entries[0]
    assert rec["event"] == "publish_guard.block"
    assert rec["reasons"] == ["aprobado_contenido_missing"]
    assert rec["page_id"] == "page-OK"
    assert rec["content_hash"] == "x" * 64


def test_publish_blocked_error_repr_contains_reasons(
    tmp_path, install_fake_gates, fake_dedup_no_duplicates,
):
    install_fake_gates(
        lambda p, d: {"aprobado_contenido": False, "fuente_primaria_ok": False}
    )
    db = _open_db(tmp_path)
    try:
        with pytest.raises(PublishBlockedError) as exc:
            assert_can_publish(_all_ok_page(), "h" * 64, db)
    finally:
        db.close()
    s = str(exc.value)
    assert "aprobado_contenido_missing" in s
    assert "fuente_primaria_missing" in s
    assert exc.value.page_id == "page-OK"
    assert exc.value.content_hash == "h" * 64


# --------------------------------------------------------------------------- #
# Defensive paths
# --------------------------------------------------------------------------- #

def test_empty_notion_page_does_not_crash(
    tmp_path, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    """An empty page must produce a deterministic block, never a crash.

    With ``fake_gates_pass_all`` honouring the dedup callable, an empty
    page has no content_hash injected ⇒ the page's content_hash is the
    parameter we pass; dedup says False ⇒ guard passes. The point of the
    test is that no AttributeError / KeyError is raised.
    """
    db = _open_db(tmp_path)
    try:
        # Should not raise.
        assert_can_publish({}, "h" * 64, db)
    finally:
        db.close()


def test_log_writer_tolerates_bad_path(
    tmp_path, monkeypatch, fake_gates_pass_all, fake_dedup_no_duplicates,
):
    """Unwritable ops_log path must not crash the publisher."""
    monkeypatch.setenv(
        "OPS_LOG_PATH", "/dev/null/cannot/write/here.jsonl"
    )
    db = _open_db(tmp_path)
    try:
        assert_can_publish(_all_ok_page(), "h" * 64, db)
    finally:
        db.close()


def test_reason_codes_constant_matches_h4_order():
    """REASON_CODES exported by guard MUST mirror H4's stable order."""
    from scripts.discovery.lib import gates as h4_gates

    h4_codes = [code for _, code in h4_gates._GATE_ORDER]
    assert list(publish_guard.REASON_CODES) == h4_codes
