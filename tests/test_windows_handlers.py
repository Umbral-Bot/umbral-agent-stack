from unittest.mock import MagicMock, patch

import pytest

import worker.tasks.windows as windows


class TestWindowsInputValidation:
    def test_firewall_allow_port_rejects_unsafe_name(self, monkeypatch):
        monkeypatch.setattr(windows.sys, "platform", "win32", raising=False)
        with pytest.raises(ValueError, match="invalid characters"):
            windows.handle_windows_firewall_allow_port({"port": 8089, "name": "OpenClaw Worker 8089"})

    def test_add_interactive_worker_to_startup_rejects_unsafe_username(self, monkeypatch):
        monkeypatch.setattr(windows.sys, "platform", "win32", raising=False)
        with pytest.raises(ValueError, match="invalid characters"):
            windows.handle_windows_add_interactive_worker_to_startup({"username": "../Rick"})


class TestWindowsPasswordHandling:
    def test_open_notepad_uses_env_password_not_http_input(self, monkeypatch):
        monkeypatch.setattr(windows.sys, "platform", "win32", raising=False)
        monkeypatch.delenv("OPENCLAW_INTERACTIVE_SESSION", raising=False)
        monkeypatch.setenv("SCHTASKS_PASSWORD", "env-secret")

        with patch(
            "worker.tasks.windows.subprocess.run",
            side_effect=[
                MagicMock(returncode=0, stdout="", stderr=""),
                MagicMock(returncode=0, stdout="", stderr=""),
            ],
        ) as run_mock:
            result = windows.handle_windows_open_notepad(
                {"run_as_user": "Rick", "run_as_password": "http-secret"}
            )

        assert result["ok"] is True
        create_cmd = run_mock.call_args_list[1].args[0]
        assert "/rp" in create_cmd
        assert "env-secret" in create_cmd
        assert "http-secret" not in create_cmd


class TestWindowsOpenUrl:
    def test_open_url_requires_http_scheme(self, monkeypatch):
        monkeypatch.setattr(windows.sys, "platform", "win32", raising=False)
        with pytest.raises(ValueError, match="must start with http:// or https://"):
            windows.handle_windows_open_url({"url": "file:///tmp/test"})

    def test_open_url_uses_startfile(self, monkeypatch):
        monkeypatch.setattr(windows.sys, "platform", "win32", raising=False)
        monkeypatch.setattr(windows.os, "startfile", MagicMock(), raising=False)

        result = windows.handle_windows_open_url({"url": "https://example.com"})

        assert result["ok"] is True
        windows.os.startfile.assert_called_once_with("https://example.com")
