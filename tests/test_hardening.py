"""
Tests for S7 hardening: SecretStore, Tailscale ACL, sanitize, rate limit.
"""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSecretStore:
    def test_get_from_env(self, monkeypatch):
        monkeypatch.setenv("WORKER_TOKEN", "env-token-123")
        from infra.secrets import SecretStore
        store = SecretStore(secrets_dir=Path("/nonexistent"))
        assert store.get("WORKER_TOKEN") == "env-token-123"

    def test_get_from_plain_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("WORKER_TOKEN", raising=False)
        secrets_file = tmp_path / "secrets.json"
        secrets_file.write_text(json.dumps({"WORKER_TOKEN": "file-token-456"}))
        store = __import__("infra.secrets", fromlist=["SecretStore"]).SecretStore(secrets_dir=tmp_path)
        assert store.get("WORKER_TOKEN") == "file-token-456"

    def test_env_takes_precedence_over_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WORKER_TOKEN", "env-wins")
        secrets_file = tmp_path / "secrets.json"
        secrets_file.write_text(json.dumps({"WORKER_TOKEN": "file-loses"}))
        from infra.secrets import SecretStore
        store = SecretStore(secrets_dir=tmp_path)
        assert store.get("WORKER_TOKEN") == "env-wins"

    def test_require_raises_if_missing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_SECRET_XYZ", raising=False)
        from infra.secrets import SecretStore
        store = SecretStore(secrets_dir=tmp_path)
        with pytest.raises(RuntimeError, match="not found"):
            store.require("NONEXISTENT_SECRET_XYZ")

    def test_get_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MISSING_KEY", raising=False)
        from infra.secrets import SecretStore
        store = SecretStore(secrets_dir=tmp_path)
        assert store.get("MISSING_KEY", "default-val") == "default-val"

    def test_encrypt_and_decrypt(self, tmp_path, monkeypatch):
        pytest.importorskip("cryptography")
        from infra.secrets import SecretStore
        store = SecretStore(secrets_dir=tmp_path)

        key = store.generate_key()
        data = {"WORKER_TOKEN": "encrypted-token", "NOTION_API_KEY": "ntn-xxx"}
        store.encrypt_to_file(data, key)

        monkeypatch.setenv("UMBRAL_SECRETS_KEY", key)
        monkeypatch.delenv("WORKER_TOKEN", raising=False)
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        store2 = SecretStore(secrets_dir=tmp_path)
        assert store2.get("WORKER_TOKEN") == "encrypted-token"
        assert store2.get("NOTION_API_KEY") == "ntn-xxx"

    def test_list_keys(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WORKER_TOKEN", "x")
        secrets_file = tmp_path / "secrets.json"
        secrets_file.write_text(json.dumps({"NOTION_API_KEY": "y"}))
        from infra.secrets import SecretStore
        store = SecretStore(secrets_dir=tmp_path)
        keys = store.list_keys()
        assert "WORKER_TOKEN" in keys
        assert "NOTION_API_KEY" in keys

    def test_audit(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WORKER_TOKEN", "x")
        from infra.secrets import SecretStore
        store = SecretStore(secrets_dir=tmp_path)
        result = store.audit()
        assert "environment" in result["sources"]
        assert result["keys"]["WORKER_TOKEN"]["source"] == "env"


class TestTailscaleACL:
    def test_generate_acl_valid_json(self):
        from infra.tailscale_acl import generate_acl
        acl = generate_acl()
        parsed = json.loads(acl)
        assert "acls" in parsed
        assert "tagOwners" in parsed
        assert len(parsed["acls"]) >= 2

    def test_generate_acl_has_required_tags(self):
        from infra.tailscale_acl import generate_acl
        parsed = json.loads(generate_acl())
        assert "tag:umbral-vps" in parsed["tagOwners"]
        assert "tag:umbral-vm" in parsed["tagOwners"]

    def test_validate_nodes_no_tailscale(self):
        from infra.tailscale_acl import validate_nodes
        with patch("infra.tailscale_acl.get_tailscale_status", return_value=None):
            result = validate_nodes()
            assert result["ok"] is False
            assert "Cannot get" in result["error"]

    def test_validate_nodes_with_mock_status(self):
        from infra.tailscale_acl import validate_nodes
        mock_status = {
            "Self": {
                "HostName": "srv-vps",
                "TailscaleIPs": ["100.113.249.25"],
                "Online": True,
                "OS": "linux",
                "Tags": ["tag:umbral-vps"],
            },
            "Peer": {
                "peer1": {
                    "HostName": "PCRick",
                    "TailscaleIPs": ["100.109.16.40"],
                    "Online": True,
                    "OS": "windows",
                    "Tags": ["tag:umbral-vm"],
                }
            },
        }
        with patch("infra.tailscale_acl.get_tailscale_status", return_value=mock_status):
            result = validate_nodes()
            assert result["ok"] is True
            assert result["total"] == 2
            assert result["online"] == 2

    def test_validate_nodes_missing_tags(self):
        from infra.tailscale_acl import validate_nodes
        mock_status = {
            "Self": {"HostName": "srv", "TailscaleIPs": ["100.1.1.1"], "Online": True, "OS": "linux", "Tags": []},
            "Peer": {},
        }
        with patch("infra.tailscale_acl.get_tailscale_status", return_value=mock_status):
            result = validate_nodes()
            assert result["ok"] is False
            assert len(result["issues"]) >= 2


class TestSanitize:
    def test_valid_task_name(self):
        from worker.sanitize import sanitize_task_name
        assert sanitize_task_name("ping") == "ping"
        assert sanitize_task_name("notion.poll_comments") == "notion.poll_comments"
        assert sanitize_task_name("windows.pad.run_flow") == "windows.pad.run_flow"

    def test_invalid_task_name(self):
        from worker.sanitize import sanitize_task_name
        with pytest.raises(ValueError):
            sanitize_task_name("rm -rf /")
        with pytest.raises(ValueError):
            sanitize_task_name("")
        with pytest.raises(ValueError):
            sanitize_task_name("a" * 200)

    def test_sanitize_input_size(self):
        from worker.sanitize import sanitize_input
        with pytest.raises(ValueError, match="too large"):
            sanitize_input({"data": "x" * 300_000})

    def test_truncates_long_fields(self):
        from worker.sanitize import sanitize_input, MAX_STRING_VALUE_LEN
        result = sanitize_input({"data": "x" * 20_000})
        assert len(result["data"]) == MAX_STRING_VALUE_LEN

    def test_injection_detection_raises_value_error(self, caplog):
        import logging
        from worker.sanitize import sanitize_input
        with caplog.at_level(logging.WARNING, logger="worker.sanitize"):
            with pytest.raises(ValueError, match="Potentially unsafe input"):
                sanitize_input({"cmd": "; rm -rf /"})
        assert "injection" in caplog.text.lower()

    def test_xss_detection(self, caplog):
        import logging
        from worker.sanitize import sanitize_input
        with caplog.at_level(logging.WARNING, logger="worker.sanitize"):
            with pytest.raises(ValueError, match="Potentially unsafe input"):
                sanitize_input({"html": "<script>alert('xss')</script>"})
        assert "injection" in caplog.text.lower()

    def test_sql_injection_detection(self, caplog):
        import logging
        from worker.sanitize import sanitize_input
        with caplog.at_level(logging.WARNING, logger="worker.sanitize"):
            with pytest.raises(ValueError, match="Potentially unsafe input"):
                sanitize_input({"q": "1 UNION SELECT * FROM users"})
        assert "injection" in caplog.text.lower()

    def test_deep_sanitization(self):
        from worker.sanitize import sanitize_input, MAX_STRING_VALUE_LEN
        data = {"nested": {"deep": {"val": "y" * 20_000}}, "list": ["z" * 20_000]}
        result = sanitize_input(data)
        assert len(result["nested"]["deep"]["val"]) == MAX_STRING_VALUE_LEN
        assert len(result["list"][0]) == MAX_STRING_VALUE_LEN

    def test_primitives_pass_through(self):
        from worker.sanitize import sanitize_input
        result = sanitize_input({"num": 42, "flag": True, "empty": None})
        assert result == {"num": 42, "flag": True, "empty": None}


class TestSecretsAudit:
    def test_scan_file_detects_aws_key(self, tmp_path):
        from scripts.secrets_audit import scan_file
        f = tmp_path / "bad.py"
        f.write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
        findings = scan_file(f)
        assert len(findings) >= 1
        assert any("AWS" in name for _, name, _ in findings)

    def test_scan_file_detects_github_pat(self, tmp_path):
        from scripts.secrets_audit import scan_file
        f = tmp_path / "bad.py"
        f.write_text('TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"\n')
        findings = scan_file(f)
        assert len(findings) >= 1

    def test_scan_file_clean(self, tmp_path):
        from scripts.secrets_audit import scan_file
        f = tmp_path / "clean.py"
        f.write_text('x = 42\nprint("hello")\n')
        findings = scan_file(f)
        assert len(findings) == 0

    def test_scan_repo_runs(self):
        from scripts.secrets_audit import scan_repo, REPO_ROOT
        result = scan_repo(REPO_ROOT)
        assert "files_scanned" in result
        assert result["files_scanned"] > 0


class TestRateLimit:
    def test_allows_within_limit(self):
        from worker.rate_limiter import RateLimiter
        limiter = RateLimiter(max_requests=60, window_seconds=60)
        allowed, remaining = limiter.is_allowed("test-client")
        assert allowed is True
        assert remaining == 59

    def test_blocks_over_limit(self):
        from worker.rate_limiter import RateLimiter
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        for _ in range(3):
            allowed, _ = limiter.is_allowed("flood-client")
            assert allowed is True
            
        allowed, remaining = limiter.is_allowed("flood-client")
        assert allowed is False
        assert remaining == 0

    def test_separate_clients(self):
        from worker.rate_limiter import RateLimiter
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("client-a")
        limiter.is_allowed("client-a")
        allowed_a, _ = limiter.is_allowed("client-a")
        allowed_b, _ = limiter.is_allowed("client-b")
        assert allowed_a is False
        assert allowed_b is True
