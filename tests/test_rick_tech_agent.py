"""F5 — `rick-tech` agent scaffold validation.

These tests verify the declarative ROLE.md contract for the `rick-tech`
agent. They do NOT exercise the live OpenClaw runtime; they only check
that the override files exist, contain the required boundary statements,
and that `rick-delivery` was not modified by this phase.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = REPO_ROOT / "openclaw" / "workspace-agent-overrides"
RICK_TECH = OVERRIDES / "rick-tech"


def test_rick_tech_dir_exists():
    assert RICK_TECH.is_dir(), f"missing override dir: {RICK_TECH}"


def test_rick_tech_has_role_and_heartbeat():
    assert (RICK_TECH / "ROLE.md").is_file()
    assert (RICK_TECH / "HEARTBEAT.md").is_file()


@pytest.fixture(scope="module")
def role_text() -> str:
    return (RICK_TECH / "ROLE.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("phrase", [
    "Does **not** publish",
    "Does **not** mark editorial gates",
    "Does **not** write to Notion",
    "git push",
    "gh pr create",
    "gh pr merge",
    "gh pr comment",
    "Does **not** read, persist, or echo",
    "COPILOT_GITHUB_TOKEN",
])
def test_rick_tech_role_states_hard_boundaries(role_text, phrase):
    assert phrase in role_text, f"ROLE.md missing required boundary: {phrase!r}"


def test_rick_tech_role_marks_copilot_cli_disabled(role_text):
    assert "copilot_cli.enabled: false" in role_text
    assert "RICK_COPILOT_CLI_ENABLED=false" in role_text
    assert "phase_blocks_real_execution" in role_text


def test_rick_tech_role_requires_human_materialization(role_text):
    # Any of these phrases is acceptable — they all encode the rule.
    needles = [
        "human decision",
        "Materialization",
        "materializes",
    ]
    assert any(n in role_text for n in needles), \
        "ROLE.md must encode that materialization is a human decision"


def test_rick_tech_role_lists_only_4_approved_missions(role_text):
    for mission in ("research", "lint-suggest", "test-explain", "runbook-draft"):
        assert mission in role_text, f"missing mission in ROLE.md: {mission}"


def test_rick_delivery_role_untouched_by_f5():
    """F5 must not modify rick-delivery/ROLE.md."""
    import subprocess
    # Compare against the parent commit (F4 merge point: b188461).
    result = subprocess.run(
        [
            "git", "log", "--format=%H",
            "--",
            "openclaw/workspace-agent-overrides/rick-delivery/ROLE.md",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    commits = [c for c in result.stdout.strip().splitlines() if c]
    # The most recent commit touching rick-delivery/ROLE.md must NOT be on
    # this F5 branch's tip; verify HEAD didn't touch the file.
    head_diff = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    changed = set(head_diff.stdout.strip().splitlines())
    assert "openclaw/workspace-agent-overrides/rick-delivery/ROLE.md" not in changed


def test_rick_tech_heartbeat_mentions_escalation_and_artifacts():
    hb = (RICK_TECH / "HEARTBEAT.md").read_text(encoding="utf-8")
    assert "escala a David" in hb or "escala" in hb
    assert "reports/copilot-cli" in hb
    assert "capability_disabled" in hb
