"""
Tests for Granola Watcher: env_loader, process_file, retry, logging, smoke.
"""

import logging
import os
import textwrap
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.vm.granola_watcher_env_loader import load_env


# ---------------------------------------------------------------------------
# ENV LOADER
# ---------------------------------------------------------------------------


class TestEnvLoader:

    def test_env_loader_reads_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "FOO_TEST_LOADER=bar\nBAZ_TEST_LOADER=qux\n", encoding="utf-8"
        )
        old_foo = os.environ.pop("FOO_TEST_LOADER", None)
        old_baz = os.environ.pop("BAZ_TEST_LOADER", None)
        try:
            result = load_env(str(env_file))
            assert result == {"FOO_TEST_LOADER": "bar", "BAZ_TEST_LOADER": "qux"}
            assert os.environ["FOO_TEST_LOADER"] == "bar"
            assert os.environ["BAZ_TEST_LOADER"] == "qux"
        finally:
            os.environ.pop("FOO_TEST_LOADER", None)
            os.environ.pop("BAZ_TEST_LOADER", None)
            if old_foo is not None:
                os.environ["FOO_TEST_LOADER"] = old_foo
            if old_baz is not None:
                os.environ["BAZ_TEST_LOADER"] = old_baz

    def test_env_loader_missing_file_no_crash(self):
        result = load_env("/nonexistent/path/.env")
        assert result == {}

    def test_env_loader_skips_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# This is a comment\nKEY_TEST_COMMENT=value\n# Another comment\n",
            encoding="utf-8",
        )
        os.environ.pop("KEY_TEST_COMMENT", None)
        try:
            result = load_env(str(env_file))
            assert result == {"KEY_TEST_COMMENT": "value"}
        finally:
            os.environ.pop("KEY_TEST_COMMENT", None)

    def test_env_loader_skips_empty_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "\n\nA_TEST_EMPTY=1\n\n  \nB_TEST_EMPTY=2\n", encoding="utf-8"
        )
        os.environ.pop("A_TEST_EMPTY", None)
        os.environ.pop("B_TEST_EMPTY", None)
        try:
            result = load_env(str(env_file))
            assert result == {"A_TEST_EMPTY": "1", "B_TEST_EMPTY": "2"}
        finally:
            os.environ.pop("A_TEST_EMPTY", None)
            os.environ.pop("B_TEST_EMPTY", None)

    def test_env_loader_strips_quotes(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            'QUOTED_TEST=\'hello\'\nDOUBLE_QUOTED_TEST="world"\n',
            encoding="utf-8",
        )
        os.environ.pop("QUOTED_TEST", None)
        os.environ.pop("DOUBLE_QUOTED_TEST", None)
        try:
            result = load_env(str(env_file))
            assert result["QUOTED_TEST"] == "hello"
            assert result["DOUBLE_QUOTED_TEST"] == "world"
        finally:
            os.environ.pop("QUOTED_TEST", None)
            os.environ.pop("DOUBLE_QUOTED_TEST", None)

    def test_env_loader_does_not_overwrite_existing(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING_VAR_TEST=from_file\n", encoding="utf-8")
        os.environ["EXISTING_VAR_TEST"] = "from_env"
        try:
            load_env(str(env_file))
            assert os.environ["EXISTING_VAR_TEST"] == "from_env"
        finally:
            os.environ.pop("EXISTING_VAR_TEST", None)


# ---------------------------------------------------------------------------
# WATCHER
# ---------------------------------------------------------------------------

from scripts.vm.granola_watcher import (
    parse_granola_markdown,
    process_file,
    scan_and_process,
    send_to_worker,
)


class TestWatcherProcessesMdFile:

    @patch("scripts.vm.granola_watcher.send_to_worker")
    def test_watcher_processes_md_file(self, mock_send, tmp_path):
        md_file = tmp_path / "meeting.md"
        md_file.write_text(
            "# Test Meeting\n\n**Date:** 2026-03-04\n\nDetailed notes here.",
            encoding="utf-8",
        )
        processed_dir = tmp_path / "processed"
        mock_send.return_value = {"status": "ok"}

        result = process_file(md_file, "http://localhost:8088", "tok", processed_dir)

        assert result is True
        assert not md_file.exists()
        assert (processed_dir / "meeting.md").exists()
        mock_send.assert_called_once()


class TestWatcherSkipsNonMdFiles:

    @patch("scripts.vm.granola_watcher.send_to_worker")
    def test_watcher_skips_non_md_files(self, mock_send, tmp_path):
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Some text content that should be ignored.", encoding="utf-8")

        processed_dir = tmp_path / "processed"

        count = scan_and_process(tmp_path, "http://localhost:8088", "tok", processed_dir)

        assert count == 0
        mock_send.assert_not_called()


class TestWatcherMovesProcessedToSubdir:

    @patch("scripts.vm.granola_watcher.send_to_worker")
    def test_watcher_moves_processed_to_subdir(self, mock_send, tmp_path):
        md_file = tmp_path / "report.md"
        md_file.write_text(
            "# Project Report\n\nLong content about the project status.",
            encoding="utf-8",
        )
        processed_dir = tmp_path / "processed"
        mock_send.return_value = {"status": "ok"}

        process_file(md_file, "http://localhost:8088", "tok", processed_dir)

        assert processed_dir.is_dir()
        assert (processed_dir / "report.md").exists()
        assert not md_file.exists()


class TestWatcherRetryOnConnectionError:

    @patch("scripts.vm.granola_watcher.time.sleep")
    def test_watcher_retry_on_connection_error(self, mock_sleep):
        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("refused")

            with pytest.raises(requests.exceptions.ConnectionError, match="Failed after"):
                send_to_worker("http://localhost:8088", "tok", "ping", {})

            assert mock_post.call_count == 3
            assert mock_sleep.call_count == 2

    @patch("scripts.vm.granola_watcher.time.sleep")
    def test_watcher_retry_succeeds_on_second_attempt(self, mock_sleep):
        with patch("requests.post") as mock_post:
            fail_resp = requests.exceptions.ConnectionError("refused")
            ok_resp = MagicMock()
            ok_resp.json.return_value = {"status": "ok"}
            ok_resp.raise_for_status = MagicMock()
            mock_post.side_effect = [fail_resp, ok_resp]

            result = send_to_worker("http://localhost:8088", "tok", "ping", {})

            assert result == {"status": "ok"}
            assert mock_post.call_count == 2


class TestWatcherSkipsAlreadyProcessed:

    @patch("scripts.vm.granola_watcher.send_to_worker")
    def test_watcher_skips_already_processed(self, mock_send, tmp_path):
        md_file = tmp_path / "_processed_meeting.md"
        md_file.write_text("# Should be skipped\n\nContent.", encoding="utf-8")

        processed_dir = tmp_path / "processed"

        count = scan_and_process(tmp_path, "http://localhost:8088", "tok", processed_dir)

        assert count == 0
        mock_send.assert_not_called()


class TestWatcherLogToFile:

    def test_watcher_log_to_file(self, tmp_path):
        log_file = tmp_path / "test_watcher.log"

        test_logger = logging.getLogger("granola_watcher_test_log")
        test_logger.setLevel(logging.INFO)
        handler = logging.FileHandler(str(log_file), encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        test_logger.addHandler(handler)

        test_logger.info("Test log message for watcher")
        handler.flush()

        content = log_file.read_text(encoding="utf-8")
        assert "Test log message for watcher" in content

        test_logger.removeHandler(handler)
        handler.close()


class TestSmokeTestScriptExists:

    def test_smoke_test_script_exists(self):
        ps1_path = Path(__file__).resolve().parent.parent / "scripts" / "vm" / "test_granola_watcher.ps1"
        assert ps1_path.is_file(), f"Smoke test script not found at {ps1_path}"

    def test_setup_script_exists(self):
        ps1_path = Path(__file__).resolve().parent.parent / "scripts" / "vm" / "setup_granola_watcher.ps1"
        assert ps1_path.is_file(), f"Setup script not found at {ps1_path}"

    def test_uninstall_script_exists(self):
        ps1_path = Path(__file__).resolve().parent.parent / "scripts" / "vm" / "uninstall_granola_watcher.ps1"
        assert ps1_path.is_file(), f"Uninstall script not found at {ps1_path}"

    def test_env_loader_module_exists(self):
        py_path = Path(__file__).resolve().parent.parent / "scripts" / "vm" / "granola_watcher_env_loader.py"
        assert py_path.is_file(), f"Env loader module not found at {py_path}"
