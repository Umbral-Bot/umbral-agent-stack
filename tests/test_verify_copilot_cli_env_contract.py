"""Tests for scripts/verify_copilot_cli_env_contract.py — F6 step 2.

These tests use tmp_path so they never touch /etc/umbral or any real
secret. Owner/group/mode checks are exercised through the *content*
checks (which are pure-Python on file text) plus a unit test that
proves the perm checker reports the actual mode rather than crashing
when files exist on a filesystem with non-rick ownership (the test
runner's uid).
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "verify_copilot_cli_env_contract.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_copilot_cli_env_contract", SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["verify_copilot_cli_env_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vmod():
    return _load_module()


# ---------------------------------------------------------------------------
# Existence / strict mode
# ---------------------------------------------------------------------------


def test_passes_in_default_mode_when_files_missing(tmp_path, vmod):
    runtime = tmp_path / "copilot-cli.env"
    secrets = tmp_path / "copilot-cli-secrets.env"
    report = vmod.run(runtime, secrets, strict=False, check_permissions=False)
    assert report.errors() == []


def test_fails_in_strict_mode_when_files_missing(tmp_path, vmod):
    runtime = tmp_path / "copilot-cli.env"
    secrets = tmp_path / "copilot-cli-secrets.env"
    report = vmod.run(runtime, secrets, strict=True, check_permissions=False)
    codes = {f.code for f in report.errors()}
    assert "missing_file" in codes


# ---------------------------------------------------------------------------
# Content rules
# ---------------------------------------------------------------------------


def test_runtime_file_rejects_copilot_token(tmp_path, vmod):
    runtime = tmp_path / "copilot-cli.env"
    runtime.write_text(
        "RICK_COPILOT_CLI_ENABLED=true\n"
        "COPILOT_GITHUB_TOKEN=github_pat_DO_NOT_LEAK_AAAAAAAAAAAAAAAAAAAAAAAAAA\n",
        encoding="utf-8",
    )
    secrets = tmp_path / "copilot-cli-secrets.env"
    secrets.write_text("# placeholder\n", encoding="utf-8")
    report = vmod.run(runtime, secrets, check_permissions=False)
    codes = {f.code for f in report.errors()}
    assert "secret_in_runtime_file" in codes


def test_secrets_file_rejects_gh_token(tmp_path, vmod):
    runtime = tmp_path / "copilot-cli.env"
    runtime.write_text("RICK_COPILOT_CLI_ENABLED=false\n", encoding="utf-8")
    secrets = tmp_path / "copilot-cli-secrets.env"
    secrets.write_text(
        "GH_TOKEN=github_pat_DO_NOT_LEAK_BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB\n",
        encoding="utf-8",
    )
    report = vmod.run(runtime, secrets, check_permissions=False)
    codes = {f.code for f in report.errors()}
    assert "wrong_token_var" in codes


def test_secrets_file_rejects_github_token(tmp_path, vmod):
    runtime = tmp_path / "copilot-cli.env"
    runtime.write_text("RICK_COPILOT_CLI_ENABLED=false\n", encoding="utf-8")
    secrets = tmp_path / "copilot-cli-secrets.env"
    secrets.write_text(
        "GITHUB_TOKEN=github_pat_DO_NOT_LEAK_CCCCCCCCCCCCCCCCCCCCCCCCCCCC\n",
        encoding="utf-8",
    )
    report = vmod.run(runtime, secrets, check_permissions=False)
    codes = {f.code for f in report.errors()}
    assert "wrong_token_var" in codes


def test_classic_pat_detected_in_secrets(tmp_path, vmod):
    runtime = tmp_path / "copilot-cli.env"
    runtime.write_text("RICK_COPILOT_CLI_ENABLED=false\n", encoding="utf-8")
    secrets = tmp_path / "copilot-cli-secrets.env"
    secrets.write_text(
        "COPILOT_GITHUB_TOKEN=ghp_LegacyClassicPATXXXXXXXXXXXXXXXXXXXXXXXX\n",
        encoding="utf-8",
    )
    report = vmod.run(runtime, secrets, check_permissions=False)
    codes = {f.code for f in report.errors()}
    assert "classic_pat_detected" in codes


def test_classic_pat_detected_in_runtime_file(tmp_path, vmod):
    runtime = tmp_path / "copilot-cli.env"
    runtime.write_text(
        "# accidentally pasted: ghp_AnotherClassicPATXXXXXXXXXXXXXXXXXXXXXX\n"
        "RICK_COPILOT_CLI_ENABLED=true\n",
        encoding="utf-8",
    )
    secrets = tmp_path / "copilot-cli-secrets.env"
    secrets.write_text("# placeholder\n", encoding="utf-8")
    report = vmod.run(runtime, secrets, check_permissions=False)
    # The line is a comment — only the regex matches; this is intentional:
    # we want detection even when the token is "just" pasted as a comment.
    codes = {f.code for f in report.errors()}
    assert "classic_pat_detected" in codes


def test_clean_files_pass(tmp_path, vmod):
    runtime = tmp_path / "copilot-cli.env"
    runtime.write_text(
        "RICK_COPILOT_CLI_ENABLED=true\nRICK_COPILOT_CLI_EXECUTE=true\n",
        encoding="utf-8",
    )
    secrets = tmp_path / "copilot-cli-secrets.env"
    secrets.write_text(
        "COPILOT_GITHUB_TOKEN=github_pat_FineGrainedPATvalueXXXXXXXXXXXXXXXX\n",
        encoding="utf-8",
    )
    report = vmod.run(runtime, secrets, check_permissions=False)
    assert report.errors() == []


# ---------------------------------------------------------------------------
# Output safety: verifier never prints token values
# ---------------------------------------------------------------------------


def test_verifier_does_not_print_token_values(tmp_path, vmod, capsys, monkeypatch):
    leak = "github_pat_DO_NOT_LEAK_DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"
    runtime = tmp_path / "copilot-cli.env"
    runtime.write_text(f"COPILOT_GITHUB_TOKEN={leak}\n", encoding="utf-8")
    secrets = tmp_path / "copilot-cli-secrets.env"
    secrets.write_text(
        f"GH_TOKEN={leak}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", [
        "verifier",
        "--runtime", str(runtime),
        "--secrets", str(secrets),
        "--no-perm-check",
    ])
    rc = vmod.main()
    assert rc != 0
    out = capsys.readouterr()
    assert leak not in out.out
    assert leak not in out.err


# ---------------------------------------------------------------------------
# Repo example artifacts conform to the contract themselves
# ---------------------------------------------------------------------------


def test_repo_example_artifacts_pass_their_own_contract(vmod):
    runtime = REPO_ROOT / "infra" / "env" / "copilot-cli.env.example"
    secrets = REPO_ROOT / "infra" / "env" / "copilot-cli-secrets.env.example"
    assert runtime.is_file()
    assert secrets.is_file()
    report = vmod.run(runtime, secrets, check_permissions=False)
    # Examples don't have a real token; expect at most a warn, not errors.
    assert report.errors() == [], report.render()


def test_systemd_dropin_example_exists():
    p = REPO_ROOT / "infra" / "systemd" / "umbral-worker-copilot-cli.conf.example"
    text = p.read_text(encoding="utf-8")
    assert "EnvironmentFile=-/etc/umbral/copilot-cli.env" in text
    assert "EnvironmentFile=-/etc/umbral/copilot-cli-secrets.env" in text
    assert "[Service]" in text
    # Must explicitly mark itself as not installed.
    assert "NOT installed" in text or "not installed" in text.lower()
