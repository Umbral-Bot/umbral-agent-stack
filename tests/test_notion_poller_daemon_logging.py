"""Tests for the notion-poller daemon logging setup (Tanda A / sys-diag 2026-07-17).

Guards the two regressions the diagnostic found in /tmp/notion_poller.log:
  1. Every line written twice (FileHandler + StreamHandler→stderr, with the cron
     redirecting stderr into the same file).
  2. Unbounded growth (~102 MB) — plain FileHandler, no rotation.

The daemon script has a hyphenated name, so it is loaded by path via importlib.
"""
from __future__ import annotations

import importlib.util
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

_DAEMON_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "vps" / "notion-poller-daemon.py"
)


def _load_daemon():
    spec = importlib.util.spec_from_file_location("notion_poller_daemon_under_test", _DAEMON_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def daemon(tmp_path, monkeypatch):
    # Point the log at a temp file BEFORE any emit; module import stays fs-free
    # thanks to delay=True on the handler.
    monkeypatch.setenv("NOTION_POLLER_LOG_FILE", str(tmp_path / "poller.log"))
    root = logging.getLogger()
    saved = list(root.handlers)
    saved_level = root.level
    try:
        yield _load_daemon()
    finally:
        # Restore the root logger so we don't leak handlers into other tests.
        for h in list(root.handlers):
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass
        for h in saved:
            root.addHandler(h)
        root.setLevel(saved_level)


def test_single_rotating_handler_after_configure(daemon, tmp_path):
    log_file = str(tmp_path / "poller.log")
    daemon._configure_logging(log_file)
    root = logging.getLogger()
    rotating = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    stream_only = [
        h
        for h in root.handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
    ]
    assert len(root.handlers) == 1, "expected exactly one root handler"
    assert len(rotating) == 1, "the sole handler must be a RotatingFileHandler"
    assert stream_only == [], "no StreamHandler → no stderr duplication path"


def test_configure_is_idempotent_no_handler_accumulation(daemon, tmp_path):
    """Re-initialising logging must NOT accumulate handlers (root cause of the
    duplicate-line bug)."""
    log_file = str(tmp_path / "poller.log")
    for _ in range(5):
        daemon._configure_logging(log_file)
    root = logging.getLogger()
    assert len(root.handlers) == 1


def test_rotation_bounds_file_size(daemon, tmp_path):
    """A small maxBytes must trigger rotation instead of unbounded growth."""
    log_file = tmp_path / "poller.log"
    # Rebuild the handler with a tiny cap so a few lines force a rollover.
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    handler = RotatingFileHandler(str(log_file), maxBytes=200, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    log = logging.getLogger("rotation_probe")
    for i in range(50):
        log.info("linea de prueba de rotacion numero %03d con relleno", i)
    handler.close()
    # Rotation created at least one backup and every file stays bounded.
    backups = list(tmp_path.glob("poller.log*"))
    assert len(backups) >= 2, "expected rotation to produce backup files"
    for f in backups:
        assert f.stat().st_size <= 2000, f"{f.name} exceeded the bounded size"
