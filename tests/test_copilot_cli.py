"""Tests for worker.tasks.copilot_cli — F3 skeleton.

These tests NEVER spawn Docker, NEVER call subprocess and NEVER touch
the host network. The capability is verified to be DISABLED by default
through multiple gates, and the audit log is verified to redact tokens.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from worker.tasks.copilot_cli import (
    _SENSITIVE_PATTERNS,
    _AUDIT_BASE_ENV,
    _ENV_FLAG,
    handle_copilot_cli_run,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_audit_dir(tmp_path, monkeypatch):
    """Redirect every audit write into pytest's tmp_path."""
    monkeypatch.setenv(_AUDIT_BASE_ENV, str(tmp_path / "audit"))
    yield


@pytest.fixture(autouse=True)
def _capability_disabled_by_default(monkeypatch):
    """Make sure no leaking env var enables the capability mid-test."""
    monkeypatch.delenv(_ENV_FLAG, raising=False)
    yield


def _read_audit(path: str):
    p = Path(path)
    assert p.is_file(), f"audit log missing: {path}"
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "audit log empty"
    return [json.loads(ln) for ln in lines]


def _ok_input(**overrides):
    base = {
        "mission": "research",
        "prompt": "Resume the failing tests in this repo.",
        "repo_path": "/work",
        "dry_run": True,
        "max_wall_sec": 60,
        "metadata": {"requested_by": "rick-tech"},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Capability disabled by env (default)
# ---------------------------------------------------------------------------


def test_capability_disabled_when_env_flag_unset():
    res = handle_copilot_cli_run(_ok_input())
    assert res["ok"] is False
    assert res["error"] == "capability_disabled"
    assert res["capability"] == "copilot_cli"
    assert res["reason"] == "env_flag_off"
    assert res["would_run"] is False
    assert res["policy"]["env_enabled"] is False

    events = _read_audit(res["audit_log"])
    assert events[-1]["decision"] == "capability_disabled_env"
    assert events[-1]["policy"]["env_enabled"] is False


# ---------------------------------------------------------------------------
# 2. Capability disabled by policy (env on, policy off)
# ---------------------------------------------------------------------------


def test_capability_disabled_when_policy_off(monkeypatch):
    monkeypatch.setenv(_ENV_FLAG, "true")
    res = handle_copilot_cli_run(_ok_input())
    assert res["ok"] is False
    assert res["error"] == "capability_disabled"
    assert res["reason"] == "policy_off"
    assert res["would_run"] is False
    assert res["policy"]["env_enabled"] is True
    assert res["policy"]["policy_enabled"] is False


# ---------------------------------------------------------------------------
# 3. Mission allowlist empty rejects (simulated by patching policy module)
# ---------------------------------------------------------------------------


def test_mission_not_allowed_when_allowlist_empty(monkeypatch):
    monkeypatch.setenv(_ENV_FLAG, "true")
    from worker import tool_policy as tp
    monkeypatch.setattr(tp, "is_copilot_cli_policy_enabled", lambda: True)
    monkeypatch.setattr(tp, "get_copilot_cli_missions", lambda: {})
    monkeypatch.setattr(tp, "is_copilot_cli_mission_allowed", lambda n: False)

    res = handle_copilot_cli_run(_ok_input(mission="research"))
    assert res["ok"] is False
    assert res["error"] == "mission_not_allowed"
    assert res["mission"] == "research"
    assert res["missions_allowed"] == []
    assert res["would_run"] is False


# ---------------------------------------------------------------------------
# 4. Banned subcommand: git push --force
# ---------------------------------------------------------------------------


def test_banned_subcommand_git_push_force():
    res = handle_copilot_cli_run(
        _ok_input(prompt="Please run git push --force to publish changes.")
    )
    assert res["ok"] is False
    assert res["error"] == "banned_subcommand"
    assert "git push" in res["matched"]
    assert res["field"] == "prompt"
    assert res["would_run"] is False

    events = _read_audit(res["audit_log"])
    assert events[-1]["decision"] == "banned_subcommand"
    assert events[-1]["matched_in_field"] == "prompt"


# ---------------------------------------------------------------------------
# 5. Banned subcommand: gh pr create
# ---------------------------------------------------------------------------


def test_banned_subcommand_gh_pr_create():
    res = handle_copilot_cli_run(
        _ok_input(prompt="Use 'gh pr create' to open the PR for me please.")
    )
    assert res["ok"] is False
    assert res["error"] == "banned_subcommand"
    assert "gh pr create" in res["matched"]


# ---------------------------------------------------------------------------
# 6. Allowed prompt → still capability_disabled (no banned match leaks)
# ---------------------------------------------------------------------------


def test_allowed_prompt_still_blocked_by_capability_gate():
    res = handle_copilot_cli_run(
        _ok_input(prompt="Summarize the README in three bullet points.")
    )
    assert res["ok"] is False
    assert res["error"] == "capability_disabled"
    assert res["error"] != "banned_subcommand"


# ---------------------------------------------------------------------------
# 7. Audit log JSONL written and redacts secrets
# ---------------------------------------------------------------------------


def test_audit_log_redacts_tokens():
    leaky_prompt = (
        "Use this token to authenticate: ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA "
        "and Bearer abcdefghijklmnop1234567890XYZ for fallback."
    )
    res = handle_copilot_cli_run(_ok_input(prompt=leaky_prompt))
    p = Path(res["audit_log"])
    raw = p.read_text(encoding="utf-8")
    assert "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" not in raw
    assert "Bearer abcdefghijklmnop1234567890XYZ" not in raw
    assert "[REDACTED]" in raw

    events = _read_audit(res["audit_log"])
    assert "ghp_" not in events[-1]["prompt_summary"]


# ---------------------------------------------------------------------------
# 8. Docker argv constructed in dry-run but never executed
# ---------------------------------------------------------------------------


def test_docker_argv_built_dry_run_no_subprocess(monkeypatch):
    monkeypatch.setenv(_ENV_FLAG, "true")
    from worker import tool_policy as tp
    monkeypatch.setattr(tp, "is_copilot_cli_policy_enabled", lambda: True)
    monkeypatch.setattr(
        tp,
        "get_copilot_cli_missions",
        lambda: {"research": {"description": "test"}},
    )
    monkeypatch.setattr(tp, "is_copilot_cli_mission_allowed", lambda n: n == "research")

    # Subprocess sentinel: any call must blow up the test.
    import subprocess as _sp
    def _explode(*a, **kw):
        raise AssertionError("subprocess invoked in F3")
    monkeypatch.setattr(_sp, "run", _explode)
    monkeypatch.setattr(_sp, "Popen", _explode)
    monkeypatch.setattr(_sp, "call", _explode)
    monkeypatch.setattr(_sp, "check_call", _explode)
    monkeypatch.setattr(_sp, "check_output", _explode)

    res = handle_copilot_cli_run(_ok_input(mission="research"))
    assert res["ok"] is True
    assert res["would_run"] is False
    assert res["phase"] == "F3"
    assert res["phase_blocks_real_execution"] is True
    assert isinstance(res["docker_argv"], list)
    argv = res["docker_argv"]
    assert "docker" in argv
    assert "run" in argv
    assert "--network=none" in argv
    assert "--read-only" in argv
    assert "--cap-drop=ALL" in argv
    assert "no-new-privileges" in argv
    assert any(a.startswith("--user") or a == "--user" for a in argv)
    assert "10001:10001" in argv
    assert any(a.endswith("/copilot-cli-smoke") for a in argv)


# ---------------------------------------------------------------------------
# 9. Tokens never leak in input/env or returned argv
# ---------------------------------------------------------------------------


def test_tokens_not_leaked_in_returned_argv(monkeypatch):
    monkeypatch.setenv(_ENV_FLAG, "true")
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    from worker import tool_policy as tp
    monkeypatch.setattr(tp, "is_copilot_cli_policy_enabled", lambda: True)
    monkeypatch.setattr(
        tp,
        "get_copilot_cli_missions",
        lambda: {"research": {}},
    )
    monkeypatch.setattr(tp, "is_copilot_cli_mission_allowed", lambda n: n == "research")

    res = handle_copilot_cli_run(_ok_input(mission="research"))
    assert res["ok"] is True
    flat = json.dumps(res, default=str)
    assert "ghp_AAAA" not in flat

    raw_audit = Path(res["audit_log"]).read_text(encoding="utf-8")
    assert "ghp_AAAA" not in raw_audit


# ---------------------------------------------------------------------------
# 10. Schema validation — invalid mission name
# ---------------------------------------------------------------------------


def test_invalid_mission_name_rejected():
    res = handle_copilot_cli_run(_ok_input(mission="Research_With_CAPS"))
    assert res["ok"] is False
    assert res["error"] == "invalid_input"
    assert res["would_run"] is False


def test_unknown_input_keys_rejected():
    payload = _ok_input()
    payload["__attempted_bypass"] = True
    res = handle_copilot_cli_run(payload)
    assert res["ok"] is False
    assert res["error"] == "invalid_input"


# ---------------------------------------------------------------------------
# 11. Sensitive pattern regex sanity (defensive)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", [
    "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "ghu_BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    "ghs_CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
    "github_pat_DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
    "sk-EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE",
])
def test_sensitive_patterns_match(token):
    assert _SENSITIVE_PATTERNS.search(token) is not None


# ---------------------------------------------------------------------------
# 12. Task is registered in TASK_HANDLERS
# ---------------------------------------------------------------------------


def test_task_registered():
    from worker.tasks import TASK_HANDLERS
    assert "copilot_cli.run" in TASK_HANDLERS
    assert TASK_HANDLERS["copilot_cli.run"] is handle_copilot_cli_run
