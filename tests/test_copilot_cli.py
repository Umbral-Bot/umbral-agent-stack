"""Tests for worker.tasks.copilot_cli — F3 skeleton.

These tests never spawn Docker or touch the host network. Real execution
coverage uses subprocess mocks so the F8A code path is verified without
leaving the test process.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from worker.tasks.copilot_cli import (
    _SENSITIVE_PATTERNS,
    _AUDIT_BASE_ENV,
    _ARTIFACT_BASE_ENV,
    _ENV_FLAG,
    handle_copilot_cli_run,
    set_allowed_repo_roots_for_test,
)
from tests._token_fixtures import (
    classic_pat,
    fine_grained_pat,
    openai_key,
    server_token,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_audit_dir(tmp_path, monkeypatch):
    """Redirect every audit write into pytest's tmp_path."""
    monkeypatch.setenv(_AUDIT_BASE_ENV, str(tmp_path / "audit"))
    monkeypatch.setenv(_ARTIFACT_BASE_ENV, str(tmp_path / "artifacts"))
    yield


@pytest.fixture(autouse=True)
def _sandbox_repo_root(tmp_path):
    """Allowlist a tmp directory as the repo root for ``repo_path``.

    F6 step 6C-4B-fixup added strict canonicalization + allowlist
    enforcement on ``repo_path``. The default value used in tests
    (``/work``) does not exist on most hosts, so we expose a
    real tmp directory and register it as the only allowed root.
    """
    sandbox = tmp_path / "work"
    sandbox.mkdir()
    set_allowed_repo_roots_for_test((sandbox,))
    try:
        yield sandbox
    finally:
        set_allowed_repo_roots_for_test(None)


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
        "repo_path": str(_DEFAULT_SANDBOX_REPO_PATH[0]) if _DEFAULT_SANDBOX_REPO_PATH else "/work",
        "dry_run": True,
        "max_wall_sec": 60,
        "metadata": {"requested_by": "rick-tech"},
    }
    base.update(overrides)
    return base


_DEFAULT_SANDBOX_REPO_PATH: list = []


@pytest.fixture(autouse=True)
def _publish_sandbox_repo_path(_sandbox_repo_root):
    _DEFAULT_SANDBOX_REPO_PATH.clear()
    _DEFAULT_SANDBOX_REPO_PATH.append(_sandbox_repo_root)
    yield
    _DEFAULT_SANDBOX_REPO_PATH.clear()


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
    # Force policy off independently of yaml (which is True since F7 rehearsal 1).
    from worker import tool_policy as tp
    monkeypatch.setattr(tp, "is_copilot_cli_policy_enabled", lambda: False)
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
    leak = classic_pat()
    bearer_secret = "Bearer abcdefghijklmnop1234567890XYZ"
    leaky_prompt = (
        f"Use this token to authenticate: {leak} "
        f"and {bearer_secret} for fallback."
    )
    res = handle_copilot_cli_run(_ok_input(prompt=leaky_prompt))
    p = Path(res["audit_log"])
    raw = p.read_text(encoding="utf-8")
    assert leak not in raw
    assert bearer_secret not in raw
    assert "[REDACTED]" in raw

    events = _read_audit(res["audit_log"])
    # Reassemble the prefix at runtime to avoid leaking it as a literal
    # in this source file.
    pat_prefix = "g" + "h" + "p" + "_"
    assert pat_prefix not in events[-1]["prompt_summary"]


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
        lambda: {"research": {"description": "test", "allowed_operations": ["read_repo"], "forbidden_operations": ["apply_patch", "git_push"]}},
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
    assert res["phase"] == "F8A.gated"
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
    leaked_token = classic_pat()
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", leaked_token)
    from worker import tool_policy as tp
    monkeypatch.setattr(tp, "is_copilot_cli_policy_enabled", lambda: True)
    monkeypatch.setattr(
        tp,
        "get_copilot_cli_missions",
        lambda: {"research": {"allowed_operations": ["read_repo"], "forbidden_operations": ["apply_patch", "git_push"]}},
    )
    monkeypatch.setattr(tp, "is_copilot_cli_mission_allowed", lambda n: n == "research")

    res = handle_copilot_cli_run(_ok_input(mission="research"))
    assert res["ok"] is True
    flat = json.dumps(res, default=str)
    assert leaked_token not in flat

    raw_audit = Path(res["audit_log"]).read_text(encoding="utf-8")
    assert leaked_token not in raw_audit


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
    classic_pat(),
    classic_pat(body_char="B"),  # was ghu_… literal, now reuses helper shape
    server_token(),
    fine_grained_pat(),
    openai_key(),
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


# ---------------------------------------------------------------------------
# F4 — Mission contracts (read from real tool_policy.yaml)
# ---------------------------------------------------------------------------

_F4_MISSIONS = ("research", "lint-suggest", "test-explain", "runbook-draft")

_REQUIRED_MISSION_KEYS = {
    "description",
    "allowed_operations",
    "forbidden_operations",
    "max_wall_sec",
    "max_prompt_chars",
    "max_output_chars",
    "max_files_read",
    "max_files_touched",
    "network",
    "execution_mode",
    "requires_human_materialization",
}


def _real_missions():
    """Bypass conftest env shims and read the actual tool_policy.yaml."""
    from worker import tool_policy as tp
    # Force a fresh load (function reads YAML each call).
    return tp.get_copilot_cli_missions()


@pytest.mark.parametrize("name", _F4_MISSIONS)
def test_f4_mission_exists(name):
    missions = _real_missions()
    assert name in missions, f"F4 mission '{name}' missing from tool_policy.yaml"


@pytest.mark.parametrize("name", _F4_MISSIONS)
def test_f4_mission_has_required_keys(name):
    m = _real_missions()[name]
    missing = _REQUIRED_MISSION_KEYS - set(m.keys())
    assert not missing, f"mission {name} missing keys: {missing}"


@pytest.mark.parametrize("name", _F4_MISSIONS)
def test_f4_mission_is_read_only(name):
    m = _real_missions()[name]
    assert m["max_files_touched"] == 0, f"{name} must be read-only in F4"
    assert m["network"] == "none", f"{name} must run with network=none in F4"
    assert m["execution_mode"] == "dry_run_artifact_only"
    assert m["requires_human_materialization"] is True


@pytest.mark.parametrize("name", _F4_MISSIONS)
def test_f4_mission_limits_within_caps(name):
    m = _real_missions()[name]
    assert 5 <= m["max_wall_sec"] <= 600
    assert 1 <= m["max_prompt_chars"] <= 16000
    assert 1 <= m["max_output_chars"] <= 65536
    assert isinstance(m["allowed_operations"], list) and m["allowed_operations"]
    assert isinstance(m["forbidden_operations"], list) and m["forbidden_operations"]


def test_f4_master_switch_still_off():
    """F7 rehearsals: policy.enabled is True and L5 is now open, but
    runtime execution still depends on the operator L3 and egress L4 gates.
    """
    from worker import tool_policy as tp
    from worker.tasks import copilot_cli as mod
    # L2 policy gate: open by F7 rehearsal 1.
    assert tp.is_copilot_cli_policy_enabled() is True
    # L4 egress gate: must stay closed.
    assert tp.is_copilot_cli_egress_activated() is False
    # L5 code constant: opened by F7.5A.
    assert mod._REAL_EXECUTION_IMPLEMENTED is True


def test_f4_valid_mission_still_blocked_when_capability_disabled():
    """Even with a real mission name, gates default to disabled."""
    res = handle_copilot_cli_run(_ok_input(mission="research"))
    assert res["ok"] is False
    assert res["error"] == "capability_disabled"


def test_f4_unknown_mission_rejected_when_gates_pass(monkeypatch):
    monkeypatch.setenv(_ENV_FLAG, "true")
    from worker import tool_policy as tp
    monkeypatch.setattr(tp, "is_copilot_cli_policy_enabled", lambda: True)
    res = handle_copilot_cli_run(_ok_input(mission="nope-not-real"))
    assert res["ok"] is False
    assert res["error"] == "mission_not_allowed"
    # Allowlist surfaced is the real F4 set.
    for name in _F4_MISSIONS:
        assert name in res["missions_allowed"]


def test_f4_banned_subcommand_still_blocks_with_real_mission():
    """Deny-list runs BEFORE capability gate — even with a real mission name."""
    res = handle_copilot_cli_run(
        _ok_input(mission="research", prompt="please run git push --force now")
    )
    assert res["ok"] is False
    assert res["error"] == "banned_subcommand"


def test_f4_audit_dir_default_is_under_reports_copilot_cli(monkeypatch):
    """Production audit path is reports/copilot-cli/<YYYY-MM>/<id>.jsonl."""
    monkeypatch.delenv(_AUDIT_BASE_ENV, raising=False)
    from worker.tasks import copilot_cli as mod
    p = mod._audit_log_path("test-id-only")
    try:
        assert "reports/copilot-cli" in str(p).replace(os.sep, "/")
    finally:
        if p.exists():
            p.unlink()


def test_f4_reports_copilot_cli_is_gitignored():
    """Production audit path must NOT be tracked by git."""
    repo = Path(__file__).resolve().parents[1]
    gi = (repo / ".gitignore").read_text(encoding="utf-8")
    assert "reports/copilot-cli/" in gi


# ---------------------------------------------------------------------------
# F6 step 1 — execute flag + token plumbing contract
# ---------------------------------------------------------------------------

_EXEC_FLAG = "RICK_COPILOT_CLI_EXECUTE"


def test_f6_execute_flag_default_false(monkeypatch):
    monkeypatch.delenv(_EXEC_FLAG, raising=False)
    from worker.tasks import copilot_cli as mod
    assert mod._execute_enabled() is False


def test_f6_real_execution_implemented_constant_is_true():
    """F7.5A: code gate is open; L3 remains the operator kill-switch."""
    from worker.tasks import copilot_cli as mod
    assert mod._REAL_EXECUTION_IMPLEMENTED is True


def _all_gates_open(monkeypatch, *, execute=True):
    """Open env+policy+mission for the success-path tests."""
    monkeypatch.setenv(_ENV_FLAG, "true")
    if execute:
        monkeypatch.setenv(_EXEC_FLAG, "true")
    else:
        monkeypatch.delenv(_EXEC_FLAG, raising=False)
    from worker import tool_policy as tp
    monkeypatch.setattr(tp, "is_copilot_cli_policy_enabled", lambda: True)
    monkeypatch.setattr(tp, "is_copilot_cli_egress_activated", lambda: True)
    monkeypatch.setattr(tp, "get_copilot_cli_missions", lambda: {"research": {"allowed_operations": ["read_repo"], "forbidden_operations": ["apply_patch", "git_push"]}})
    monkeypatch.setattr(tp, "is_copilot_cli_mission_allowed", lambda n: n == "research")


def test_f6_execute_flag_off_keeps_phase_blocked(monkeypatch):
    _all_gates_open(monkeypatch, execute=False)
    res = handle_copilot_cli_run(_ok_input(mission="research"))
    assert res["ok"] is True
    assert res["would_run"] is False
    assert res["phase_blocks_real_execution"] is True
    assert res["policy"]["execute_enabled"] is False
    assert res["decision"] == "execute_flag_off_dry_run"


def test_f6_execute_flag_on_reaches_dry_run_after_code_gate_open(monkeypatch):
    """With L3+L5 open, dry_run still does not launch a subprocess."""
    _all_gates_open(monkeypatch, execute=True)
    import subprocess as _sp
    def _explode(*a, **kw):
        raise AssertionError("subprocess invoked during dry_run")
    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(_sp, name, _explode)

    res = handle_copilot_cli_run(_ok_input(mission="research"))
    assert res["ok"] is True
    assert res["would_run"] is False
    assert res["phase_blocks_real_execution"] is False
    assert res["policy"]["execute_enabled"] is True
    assert res["policy"]["real_execution_implemented"] is True
    assert res["decision"] == "would_run_dry_run"


def test_f7_5a_code_gate_open_but_execute_env_gate_blocks(monkeypatch):
    """L5=True alone is insufficient; L3=false still blocks execution."""
    _all_gates_open(monkeypatch, execute=False)
    import subprocess as _sp

    def _explode(*a, **kw):
        raise AssertionError("subprocess invoked with execute flag off")

    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(_sp, name, _explode)

    res = handle_copilot_cli_run(_ok_input(mission="research"))
    assert res["ok"] is True
    assert res["would_run"] is False
    assert res["phase_blocks_real_execution"] is True
    assert res["policy"]["execute_enabled"] is False
    assert res["policy"]["real_execution_implemented"] is True
    assert res["decision"] == "execute_flag_off_dry_run"


# ---------------------------------------------------------------------------
# F8A — real execution path exists, but only behind L1-L5
# ---------------------------------------------------------------------------


def test_f8a_real_run_requires_egress_gate(monkeypatch):
    _all_gates_open(monkeypatch, execute=True)
    from worker import tool_policy as tp
    monkeypatch.setattr(tp, "is_copilot_cli_egress_activated", lambda: False)

    import subprocess as _sp

    def _explode(*a, **kw):
        raise AssertionError("subprocess invoked while egress gate is closed")

    monkeypatch.setattr(_sp, "run", _explode)

    res = handle_copilot_cli_run(_ok_input(mission="research", dry_run=False))
    assert res["ok"] is False
    assert res["error"] == "egress_not_activated"
    assert res["decision"] == "egress_not_activated"
    assert res["would_run"] is False
    assert res["phase_blocks_real_execution"] is True


def test_f8a_real_run_invokes_subprocess_and_writes_artifacts(monkeypatch):
    _all_gates_open(monkeypatch, execute=True)
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "github_pat_" + "A" * 40)
    prompt = "Generate a one paragraph README for this scratch directory."

    import subprocess as _sp
    calls = []

    def _fake_run(argv, *, input, text, capture_output, timeout):
        calls.append({
            "argv": argv,
            "input": input,
            "text": text,
            "capture_output": capture_output,
            "timeout": timeout,
        })
        return _sp.CompletedProcess(argv, 0, stdout='{"summary":"ok"}\n', stderr="")

    monkeypatch.setattr(_sp, "run", _fake_run)

    res = handle_copilot_cli_run(_ok_input(
        mission="research",
        prompt=prompt,
        dry_run=False,
        metadata={"batch_id": "f8a-test", "agent_id": "agent-1"},
    ))

    assert res["ok"] is True
    assert res["executed"] is True
    assert res["decision"] == "completed"
    assert res["exit_code"] == 0
    assert calls and calls[0]["input"] == prompt
    argv = calls[0]["argv"]
    flat_argv = "\n".join(argv)
    assert "COPILOT_GITHUB_TOKEN" in argv
    assert "github_pat_" not in flat_argv
    assert prompt not in flat_argv
    assert "--network=bridge" in argv

    manifest_path = Path(res["artifact_manifest"])
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["batch_id"] == "f8a-test"
    assert manifest["agent_id"] == "agent-1"
    assert manifest["tokens"]["source"] == "not_reported_by_github_copilot_cli"
    assert manifest["cost_usd"]["source"] == "not_reported_by_github_copilot_cli"
    assert manifest["secret_scan"]["status"] == "clean"
    assert Path(manifest["stdout"]["path"]).read_text(encoding="utf-8") == '{"summary":"ok"}\n'


def test_f8a_real_run_redacts_token_patterns_from_artifacts(monkeypatch):
    _all_gates_open(monkeypatch, execute=True)

    import subprocess as _sp

    def _fake_run(argv, *, input, text, capture_output, timeout):
        return _sp.CompletedProcess(
            argv,
            0,
            stdout="accidental " + ("github_pat_" + "B" * 40),
            stderr="",
        )

    monkeypatch.setattr(_sp, "run", _fake_run)

    res = handle_copilot_cli_run(_ok_input(mission="research", dry_run=False))
    assert res["ok"] is False
    assert res["decision"] == "secret_pattern_redacted"
    manifest = json.loads(Path(res["artifact_manifest"]).read_text(encoding="utf-8"))
    stdout_text = Path(manifest["stdout"]["path"]).read_text(encoding="utf-8")
    assert "github_pat_" not in stdout_text
    assert "[REDACTED]" in stdout_text
    assert manifest["secret_scan"]["status"] == "redacted"


def test_f8a_diagnostic_mode_drops_json_stream_flags(monkeypatch):
    _all_gates_open(monkeypatch, execute=True)
    monkeypatch.setenv("COPILOT_CLI_DIAGNOSTIC_MODE", "true")

    import subprocess as _sp
    calls = []

    def _fake_run(argv, *, input, text, capture_output, timeout):
        calls.append(argv)
        return _sp.CompletedProcess(argv, 1, stdout="", stderr="")

    monkeypatch.setattr(_sp, "run", _fake_run)
    res = handle_copilot_cli_run(_ok_input(mission="research", dry_run=False))

    assert res["executed"] is True
    flat_argv = "\n".join(calls[0])
    assert "--log-level=debug" in flat_argv
    assert "--output-format=json" not in flat_argv
    assert "--stream=off" not in flat_argv


def test_f6_audit_records_all_three_flags(monkeypatch):
    _all_gates_open(monkeypatch, execute=True)
    res = handle_copilot_cli_run(_ok_input(mission="research"))
    events = _read_audit(res["audit_log"])
    p = events[-1]["policy"]
    for key in (
        "env_enabled",
        "policy_enabled",
        "execute_enabled",
        "real_execution_implemented",
        "phase_blocks_real_execution",
    ):
        assert key in p, f"audit policy missing {key}"


# ---------------------------------------------------------------------------
# F7 rehearsal 1 — policy gate open, all deeper gates remain closed
# ---------------------------------------------------------------------------


def test_f7_rehearsal_yaml_policy_enabled_true():
    """F7 rehearsal 1: yaml-loaded policy gate must report True."""
    from worker import tool_policy as tp
    assert tp.is_copilot_cli_policy_enabled() is True


def test_f7_rehearsal_yaml_egress_still_inactive():
    """F7 rehearsal 1 must NOT touch egress activation."""
    from worker import tool_policy as tp
    assert tp.is_copilot_cli_egress_activated() is False


def test_f7_rehearsal_real_execution_constant_now_true():
    """F7.5A opened L5; L3 still controls actual execution."""
    from worker.tasks import copilot_cli as mod
    assert mod._REAL_EXECUTION_IMPLEMENTED is True


def test_f7_rehearsal_env_on_policy_on_execute_off_returns_dry_run(monkeypatch):
    """End-to-end behavioural contract for rehearsal 1.

    With RICK_COPILOT_CLI_ENABLED=true and the yaml policy gate open
    (NOT monkeypatched), but RICK_COPILOT_CLI_EXECUTE absent/false,
    the handler must:
      - return ok=true, would_run=false
      - report decision="execute_flag_off_dry_run"
      - keep phase_blocks_real_execution=true
      - keep policy.real_execution_implemented=true
      - never invoke subprocess
    """
    monkeypatch.setenv(_ENV_FLAG, "true")
    monkeypatch.delenv(_EXEC_FLAG, raising=False)

    # Subprocess explosion guard.
    import subprocess as _sp

    def _explode(*a, **kw):
        raise AssertionError("subprocess invoked during F7 rehearsal 1")

    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(_sp, name, _explode)

    res = handle_copilot_cli_run(_ok_input(mission="research"))

    assert res["ok"] is True
    assert res["would_run"] is False
    assert res["phase_blocks_real_execution"] is True
    assert res["decision"] == "execute_flag_off_dry_run"
    assert res["policy"]["env_enabled"] is True
    assert res["policy"]["policy_enabled"] is True
    assert res["policy"]["execute_enabled"] is False
    assert res["policy"]["real_execution_implemented"] is True


def test_f6_gh_token_and_github_token_not_in_argv(monkeypatch):
    """Even if GH_TOKEN/GITHUB_TOKEN are present in env, they must not
    appear in the constructed docker argv (we use COPILOT_GITHUB_TOKEN)."""
    monkeypatch.setenv("GH_TOKEN", "ghp_DO_NOT_LEAK_GH_TOKEN_AAAAAAAAAAAAA")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_DO_NOT_LEAK_GITHUB_TOKEN_BBBBBBB")
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "github_pat_DO_NOT_LEAK_CCCCCCCCCC")
    _all_gates_open(monkeypatch, execute=True)
    res = handle_copilot_cli_run(_ok_input(mission="research"))
    flat = json.dumps(res, default=str)
    raw_audit = Path(res["audit_log"]).read_text(encoding="utf-8")
    for needle in ("DO_NOT_LEAK_GH_TOKEN", "DO_NOT_LEAK_GITHUB_TOKEN", "DO_NOT_LEAK_C"):
        assert needle not in flat, f"token leaked in response: {needle}"
        assert needle not in raw_audit, f"token leaked in audit: {needle}"


def test_f6_env_example_declares_execute_flag():
    repo = Path(__file__).resolve().parents[1]
    text = (repo / ".env.example").read_text(encoding="utf-8")
    assert "RICK_COPILOT_CLI_EXECUTE=false" in text
    assert "RICK_COPILOT_CLI_ENABLED=false" in text


def test_f6_design_doc_documents_envfile_layout():
    repo = Path(__file__).resolve().parents[1]
    ev = (repo / "docs" / "copilot-cli-f6-step1-token-plumbing-evidence.md").read_text(encoding="utf-8")
    assert "/etc/umbral/copilot-cli.env" in ev
    assert "/etc/umbral/copilot-cli-secrets.env" in ev
    assert "0600" in ev
    assert "COPILOT_GITHUB_TOKEN" in ev
    # Hard "no classic PAT" assertion.
    assert "ghp_" in ev or "classic PAT" in ev.lower()
    assert "no classic" in ev.lower() or "not supported" in ev.lower() or "NO usar classic" in ev or "no usar classic" in ev.lower()


# ---------------------------------------------------------------------------
# F6 step 5 — operation scoping enforcement
# ---------------------------------------------------------------------------


def _all_gates_open_with_ops(monkeypatch, *, mission, allowed, forbidden,
                             execute=False):
    """Open every gate and stub the mission policy with the given ops."""
    monkeypatch.setenv(_ENV_FLAG, "true")
    if execute:
        monkeypatch.setenv(_EXEC_FLAG, "true")
    else:
        monkeypatch.delenv(_EXEC_FLAG, raising=False)
    from worker import tool_policy as tp
    monkeypatch.setattr(tp, "is_copilot_cli_policy_enabled", lambda: True)
    monkeypatch.setattr(tp, "is_copilot_cli_egress_activated", lambda: True)
    spec = {
        "description": "test",
        "allowed_operations": list(allowed),
        "forbidden_operations": list(forbidden),
    }
    monkeypatch.setattr(tp, "get_copilot_cli_missions", lambda: {mission: spec})
    monkeypatch.setattr(tp, "is_copilot_cli_mission_allowed",
                        lambda n: n == mission)


def test_f6step5_allowed_operation_passes_to_dry_run(monkeypatch):
    _all_gates_open_with_ops(
        monkeypatch, mission="research",
        allowed=["read_repo", "summarize"],
        forbidden=["apply_patch", "git_push"],
    )
    res = handle_copilot_cli_run(_ok_input(
        mission="research", requested_operations=["read_repo"],
    ))
    assert res["ok"] is True
    assert res["operations"]["decision"] == "allowed"
    assert res["operations"]["requested"] == ["read_repo"]
    assert "read_repo" in res["operations"]["allowed"]
    events = _read_audit(res["audit_log"])
    assert events[-1]["operation_decision"] == "allowed"


def test_f6step5_forbidden_operation_rejects_before_docker_argv(monkeypatch):
    _all_gates_open_with_ops(
        monkeypatch, mission="lint-suggest",
        allowed=["read_repo", "propose_patch_text"],
        forbidden=["apply_patch", "write_files"],
    )
    res = handle_copilot_cli_run(_ok_input(
        mission="lint-suggest",
        requested_operations=["read_repo", "apply_patch"],
    ))
    assert res["ok"] is False
    assert res["error"] == "operation_forbidden"
    assert res["operation"] == "apply_patch"
    assert res["operation_violation"] in (
        "global_hard_deny", "mission_forbidden",
    )
    assert "docker_argv" not in res
    events = _read_audit(res["audit_log"])
    assert events[-1]["decision"] == "operation_forbidden"
    assert events[-1]["operation_violation"] in (
        "global_hard_deny", "mission_forbidden",
    )


def test_f6step5_unknown_operation_rejects(monkeypatch):
    _all_gates_open_with_ops(
        monkeypatch, mission="research",
        allowed=["read_repo", "summarize"],
        forbidden=["apply_patch"],
    )
    res = handle_copilot_cli_run(_ok_input(
        mission="research",
        requested_operations=["read_repo", "make_coffee"],
    ))
    assert res["ok"] is False
    assert res["error"] == "unknown_operation"
    assert res["operation"] == "make_coffee"
    assert "docker_argv" not in res


def test_f6step5_operation_not_in_allowed_list_rejects(monkeypatch):
    _all_gates_open_with_ops(
        monkeypatch, mission="research",
        allowed=["read_repo"],
        forbidden=["read_test_output"],   # declared somewhere in policy
    )
    # 'read_test_output' is declared (in forbidden) so it's "known",
    # and falls into mission_forbidden.
    res = handle_copilot_cli_run(_ok_input(
        mission="research",
        requested_operations=["read_test_output"],
    ))
    assert res["ok"] is False
    assert res["error"] == "operation_forbidden"
    assert res["operation_violation"] == "mission_forbidden"


def test_f6step5_apply_patch_rejected_for_all_four_missions(monkeypatch):
    for mission, allowed, forbidden in [
        ("research", ["read_repo", "summarize"],
         ["write_files", "run_subprocess"]),
        ("lint-suggest", ["read_repo", "propose_patch_text"],
         ["apply_patch", "write_files"]),
        ("test-explain", ["read_repo", "explain_failure"],
         ["run_subprocess", "run_tests_directly"]),
        ("runbook-draft", ["read_repo", "generate_markdown_artifact"],
         ["write_to_docs_dir", "write_to_runbooks_dir"]),
    ]:
        _all_gates_open_with_ops(
            monkeypatch, mission=mission, allowed=allowed,
            forbidden=forbidden,
        )
        res = handle_copilot_cli_run(_ok_input(
            mission=mission, requested_operations=["apply_patch"],
        ))
        assert res["ok"] is False, f"mission={mission} accepted apply_patch"
        assert res["error"] == "operation_forbidden", mission
        assert res["operation"] == "apply_patch", mission


def test_f6step5_global_hard_deny_blocks_git_push_open_pr_notion_write(monkeypatch):
    _all_gates_open_with_ops(
        monkeypatch, mission="research",
        # Operator accidentally adds dangerous ops to allowed_operations.
        allowed=["read_repo", "git_push", "gh_pr_create",
                 "notion_write", "publish"],
        forbidden=[],
    )
    for dangerous in ("git_push", "gh_pr_create", "notion_write", "publish"):
        res = handle_copilot_cli_run(_ok_input(
            mission="research", requested_operations=[dangerous],
        ))
        assert res["ok"] is False, dangerous
        assert res["error"] == "operation_forbidden", dangerous
        assert res["operation_violation"] == "global_hard_deny", dangerous
        assert res["operation"] == dangerous


def test_f6step5_audit_records_operation_lists(monkeypatch):
    _all_gates_open_with_ops(
        monkeypatch, mission="research",
        allowed=["read_repo", "summarize"],
        forbidden=["apply_patch"],
    )
    res = handle_copilot_cli_run(_ok_input(
        mission="research", requested_operations=["read_repo"],
    ))
    assert res["ok"] is True
    events = _read_audit(res["audit_log"])
    last = events[-1]
    assert last["requested_operations"] == ["read_repo"]
    assert "read_repo" in last["allowed_operations"]
    assert "apply_patch" in last["forbidden_operations"]
    assert last["operation_decision"] == "allowed"


def test_f6step5_no_subprocess_called_during_operation_enforcement(monkeypatch):
    _all_gates_open_with_ops(
        monkeypatch, mission="research",
        allowed=["read_repo"],
        forbidden=["apply_patch"],
    )
    import subprocess as _sp
    def _explode(*a, **kw):
        raise AssertionError("subprocess invoked during operation enforcement")
    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(_sp, name, _explode)
    # Both rejection paths and the success path must not call subprocess.
    handle_copilot_cli_run(_ok_input(
        mission="research", requested_operations=["read_repo"],
    ))
    handle_copilot_cli_run(_ok_input(
        mission="research", requested_operations=["apply_patch"],
    ))
    handle_copilot_cli_run(_ok_input(
        mission="research", requested_operations=["make_coffee"],
    ))


def test_f6step5_backward_compat_no_requested_operations(monkeypatch):
    """Old payloads (pre F6 step 5) must still work."""
    _all_gates_open_with_ops(
        monkeypatch, mission="research",
        allowed=["read_repo", "summarize"],
        forbidden=["apply_patch"],
    )
    payload = _ok_input(mission="research")
    assert "requested_operations" not in payload
    res = handle_copilot_cli_run(payload)
    assert res["ok"] is True
    # Default inferred operation for `research` is `read_repo`.
    assert res["operations"]["requested"] == ["read_repo"]
    assert res["operations"]["decision"] == "allowed"


def test_f6step5_empty_requested_operations_rejected(monkeypatch):
    _all_gates_open_with_ops(
        monkeypatch, mission="research",
        allowed=["read_repo"],
        forbidden=[],
    )
    res = handle_copilot_cli_run(_ok_input(
        mission="research", requested_operations=[],
    ))
    assert res["ok"] is False
    assert res["error"] == "operation_not_allowed"
    assert res["operation_violation"] == "no_operation_requested"


def test_f6step5_invalid_operation_name_rejects_at_schema(monkeypatch):
    _all_gates_open_with_ops(
        monkeypatch, mission="research",
        allowed=["read_repo"],
        forbidden=[],
    )
    res = handle_copilot_cli_run(_ok_input(
        mission="research", requested_operations=["BadName!"],
    ))
    assert res["ok"] is False
    assert res["error"] == "invalid_input"


def test_f6step5_shipped_policy_missions_still_have_all_required_keys():
    """Sanity: every shipped mission keeps allowed_operations + forbidden."""
    from worker import tool_policy as tp
    missions = tp.get_copilot_cli_missions()
    assert set(missions.keys()) == {
        "research", "lint-suggest", "test-explain", "runbook-draft",
    }
    for name, spec in missions.items():
        assert isinstance(spec.get("allowed_operations"), list), name
        assert isinstance(spec.get("forbidden_operations"), list), name
        assert spec["allowed_operations"], name


# ---------------------------------------------------------------------------
# F6 step 6C-4B-fixup: repo_path canonicalization + allowlist
# ---------------------------------------------------------------------------


from worker.tasks.copilot_cli import _validate_repo_path, _ValidationError  # noqa: E402


def test_repo_path_accepts_allowlisted_root(_sandbox_repo_root):
    out = _validate_repo_path(str(_sandbox_repo_root))
    assert out == _sandbox_repo_root.resolve()


def test_repo_path_accepts_descendant_of_allowlisted_root(_sandbox_repo_root):
    sub = _sandbox_repo_root / "src" / "pkg"
    sub.mkdir(parents=True)
    out = _validate_repo_path(str(sub))
    assert out == sub.resolve()


def test_repo_path_rejects_root_filesystem():
    with pytest.raises(_ValidationError) as exc:
        _validate_repo_path("/")
    assert exc.value.code == "repo_path_not_allowed"


def test_repo_path_rejects_existing_dir_outside_allowlist(tmp_path):
    """Reject a real existing directory that is not inside the allowlist.

    Uses tmp_path so the test is hermetic on CI runners (GitHub Actions
    has no /home/rick). The autouse ``_sandbox_repo_root`` fixture
    allowlists ``tmp_path/work``; this test passes its parent
    (``tmp_path``) which exists but is not inside the allowlist.
    """
    with pytest.raises(_ValidationError) as exc:
        _validate_repo_path(str(tmp_path))
    assert exc.value.code == "repo_path_not_allowed"


def test_repo_path_rejects_home_dir():
    """Whichever of repo_path_not_allowed / repo_path_not_found is correct.

    On the live VPS ``/home/rick`` exists but is outside the allowlist
    → ``repo_path_not_allowed``. On hermetic CI runners (GitHub
    Actions) ``/home/rick`` does not exist → ``repo_path_not_found``.
    Both outcomes prove the path cannot be used as a repo root.
    """
    with pytest.raises(_ValidationError) as exc:
        _validate_repo_path("/home/rick")
    assert exc.value.code in {"repo_path_not_allowed", "repo_path_not_found"}


def test_repo_path_rejects_nonexistent(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(_ValidationError) as exc:
        _validate_repo_path(str(missing))
    assert exc.value.code == "repo_path_not_found"


def test_repo_path_rejects_regular_file(_sandbox_repo_root):
    f = _sandbox_repo_root / "README.md"
    f.write_text("not a dir", encoding="utf-8")
    with pytest.raises(_ValidationError) as exc:
        _validate_repo_path(str(f))
    assert exc.value.code == "repo_path_not_directory"


def test_repo_path_rejects_dotdot_traversal_outside_allowlist(_sandbox_repo_root, tmp_path):
    # tmp_path is parent of _sandbox_repo_root; using ".." escapes allowlist.
    escape = _sandbox_repo_root / ".." / ".."
    with pytest.raises(_ValidationError) as exc:
        _validate_repo_path(str(escape))
    assert exc.value.code == "repo_path_not_allowed"


def test_repo_path_rejects_symlink_escape(_sandbox_repo_root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = _sandbox_repo_root / "escape"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this filesystem")
    with pytest.raises(_ValidationError) as exc:
        _validate_repo_path(str(link))
    assert exc.value.code == "repo_path_not_allowed"


def test_repo_path_rejection_returns_structured_error_via_handler(tmp_path):
    # Use an existing-but-not-allowlisted dir so this test passes on
    # both the VPS and on hermetic CI runners.
    outside = tmp_path / "outside-allowlist"
    outside.mkdir()
    payload = _ok_input(repo_path=str(outside))
    res = handle_copilot_cli_run(payload)
    assert res["ok"] is False
    assert res["error"] == "repo_path_not_allowed"
    assert res["would_run"] is False
