"""Tests for github_tournament orchestration handler.

Covers:
- Phase 1: branch-based orchestration primitives.
- Phase 2 slice 1: contestant proposal artifact committed per branch.
- Phase 2 slice 2: final branch materialized via cherry-pick + push.
- Phase 2 slice 4a: opt-in single-file code change per contestant
  (sandboxed under .rick/contestants/).
- Phase 2 slice 4b: opt-in real-repo single-file code change per
  contestant, driven by a validated ``target_file`` input.
- Phase 2 slice 5: opt-in per-contestant validation via
  ``validation_mode="python_compile"`` (observational).
- Phase 2 slice 6: opt-in re-judge pass with enriched
  per-contestant evidence (``rejudge=True``).
"""

import re
import subprocess
from unittest.mock import patch

import pytest

from worker.tasks.github_tournament import (
    REJUDGE_SYSTEM,
    _artifact_rel_path,
    _branch_name,
    _build_artifact_body,
    _build_code_prompt,
    _build_rejudge_prompt,
    _cherry_pick_and_push,
    _code_prefix,
    _detect_override_attempt,
    _final_branch_name,
    _generate_and_commit_code_change,
    _generate_tournament_id,
    _parse_file_block,
    _resolve_inside_sandbox,
    _run_contestant_validation,
    _run_python_compile_validation,
    _run_rejudge,
    _summarize_code_change,
    _summarize_validation,
    _tail_log,
    _validate_target_file,
    _validate_validation_mode,
    _validate_validation_timeout,
    _winner_commit_info,
    _write_artifact_and_commit,
    handle_github_orchestrate_tournament,
)

MOD = "worker.tasks.github_tournament"


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _preflight_ok():
    return {"ok": True, "clean": True, "repo_path": "/tmp/repo", "branch": "main"}


def _preflight_dirty():
    return {"ok": True, "clean": False, "repo_path": "/tmp/repo", "branch": "main"}


def _preflight_fail():
    return {"ok": False, "error": "ssh check failed"}


def _create_branch_ok(input_data):
    return {
        "ok": True,
        "branch": input_data["branch_name"],
        "base": input_data.get("base", "main"),
    }


def _artifact_noop(**kwargs):
    """Default mock for _write_artifact_and_commit used in existing tests.

    Returns a successful-looking artifact without touching disk or git.
    New Phase-2-slice-1 tests patch the helper individually to assert
    richer behaviour.
    """
    label = kwargs.get("label", "?")
    tid = kwargs.get("tournament_id", "x")
    branch = kwargs.get("branch", "")
    return {
        "path": f".rick/tournaments/{tid}/{label}.md",
        "written": True,
        "commit": {"ok": True, "branch": branch, "commit_sha": "deadbeef"},
    }


def _cherry_pick_noop(**kwargs):
    """Default mock for _cherry_pick_and_push used in existing tests.

    Returns success without invoking any git subprocess. New
    Phase-2-slice-2 tests patch the helper individually to assert
    richer behaviour (conflicts, push failure, etc.).
    """
    return {"cherry_picked": True, "pushed": True, "error": None}


def _code_change_noop(**kwargs):
    """Default mock for _generate_and_commit_code_change used by
    slice-4 integration tests. Returns a successful-looking result
    without touching disk, git, or the LLM.
    """
    label = kwargs.get("label", "?")
    tid = kwargs.get("tournament_id", "x")
    branch = kwargs.get("branch", "")
    target_file = kwargs.get("target_file")
    path = target_file or f".rick/contestants/{tid}/{label}/change.py"
    mode = "target_file" if target_file else "sandbox"
    return {
        "attempted": True,
        "mode": mode,
        "target_file": target_file,
        "path": path,
        "written": True,
        "parse_error": None,
        "commit": {"ok": True, "branch": branch, "commit_sha": "c0dec0de"},
    }


def _tournament_result(num=3, winner_id=1, escalate=False):
    approaches = []
    for i in range(num):
        approaches.append({
            "id": i + 1,
            "approach_name": f"Approach {chr(65 + i)}",
            "proposal": f"Full proposal text for approach {chr(65 + i)}",
            "model_used": "azure_foundry",
        })

    verdict = {
        "text": f"**Winner: Contestant #{winner_id}**" if not escalate else "ESCALATE",
        "winner_id": winner_id if not escalate else None,
        "escalate": escalate,
    }
    return {
        "challenge": "test challenge",
        "approaches": approaches,
        "debate": [],
        "verdict": verdict,
        "meta": {
            "total_llm_calls": num + 2,
            "total_duration_ms": 5000,
            "models_used": ["azure_foundry"],
        },
    }


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------

class TestGenerateTournamentId:
    def test_length_and_hex(self):
        tid = _generate_tournament_id()
        assert len(tid) == 8
        assert re.fullmatch(r"[0-9a-f]{8}", tid)

    def test_unique(self):
        ids = {_generate_tournament_id() for _ in range(100)}
        assert len(ids) == 100


class TestBranchNaming:
    def test_contestant_branch(self):
        assert _branch_name("abc12345", "a") == "rick/t/abc12345/a"

    def test_final_branch(self):
        assert _final_branch_name("abc12345") == "rick/t/abc12345/final"

    def test_all_labels(self):
        for label in "abcde":
            name = _branch_name("x", label)
            assert name.startswith("rick/")
            assert name.endswith(f"/{label}")


# ---------------------------------------------------------------------------
# Orchestration handler tests
# ---------------------------------------------------------------------------

class TestOrchestrateTournament:
    """Tests for handle_github_orchestrate_tournament."""

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_basic_with_winner(self, _pre, mock_branch, mock_tourn, _chk, _art, _cp):
        mock_tourn.return_value = _tournament_result(num=3, winner_id=1)

        result = handle_github_orchestrate_tournament(
            {"challenge": "Optimize the API"},
        )

        assert result["ok"] is True
        assert len(result["tournament_id"]) == 8
        assert result["challenge"] == "Optimize the API"
        assert result["base"] == "main"
        assert len(result["contestants"]) == 3
        assert result["contestants"][0]["branch"].endswith("/a")
        assert result["contestants"][2]["branch"].endswith("/c")
        assert result["verdict"]["winner_id"] == 1
        assert result["verdict"]["escalate"] is False
        assert result["final_branch"] is not None
        assert result["final_branch"].endswith("/final")
        # 3 contestant + 1 final = 4
        assert mock_branch.call_count == 4
        assert len(result["branches_created"]) == 4

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_escalate_no_final_branch(self, _pre, mock_branch, mock_tourn, _chk, _art, _cp):
        mock_tourn.return_value = _tournament_result(num=2, escalate=True)

        result = handle_github_orchestrate_tournament(
            {"challenge": "Redesign auth"},
        )

        assert result["ok"] is True
        assert result["verdict"]["escalate"] is True
        assert result["verdict"]["winner_id"] is None
        assert result["final_branch"] is None
        # only 2 contestant branches
        assert mock_branch.call_count == 2
        assert len(result["branches_created"]) == 2

    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_dirty())
    def test_dirty_worktree_fails(self, _pre):
        result = handle_github_orchestrate_tournament(
            {"challenge": "test"},
        )
        assert result["ok"] is False
        assert "uncommitted" in result["error"]

    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_fail())
    def test_preflight_failure(self, _pre):
        result = handle_github_orchestrate_tournament(
            {"challenge": "test"},
        )
        assert result["ok"] is False
        assert "Preflight" in result["error"]

    def test_missing_challenge_raises(self):
        with pytest.raises(ValueError, match="challenge is required"):
            handle_github_orchestrate_tournament({})

    def test_empty_challenge_raises(self):
        with pytest.raises(ValueError, match="challenge is required"):
            handle_github_orchestrate_tournament({"challenge": "   "})

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_branch_failure_returns_partial(
        self, _pre, mock_branch, mock_tourn, _chk, _art, _cp,
    ):
        mock_tourn.return_value = _tournament_result(num=3)
        mock_branch.side_effect = [
            {"ok": True, "branch": "rick/t/x/a", "base": "main"},
            {"ok": False, "error": "checkout failed"},
        ]

        result = handle_github_orchestrate_tournament(
            {"challenge": "test"},
        )

        assert result["ok"] is False
        assert "Failed to create branch" in result["error"]
        assert len(result["branches_created"]) == 1

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_custom_base(self, _pre, mock_branch, mock_tourn, _chk, _art, _cp):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament(
            {"challenge": "test", "base": "develop"},
        )

        assert result["base"] == "develop"
        for call in mock_branch.call_args_list:
            assert call[0][0]["base"] == "develop"

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_predefined_approaches_forwarded(
        self, _pre, _br, mock_tourn, _chk, _art, _cp,
    ):
        mock_tourn.return_value = _tournament_result(num=2)

        handle_github_orchestrate_tournament({
            "challenge": "test",
            "approaches": ["Class-based", "Functional"],
        })

        tourn_input = mock_tourn.call_args[0][0]
        assert tourn_input["approaches"] == ["Class-based", "Functional"]

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_meta_present(self, _pre, _br, mock_tourn, _chk, _art, _cp):
        mock_tourn.return_value = _tournament_result(num=2)

        result = handle_github_orchestrate_tournament(
            {"challenge": "test"},
        )

        assert "meta" in result
        assert "total_llm_calls" in result["meta"]
        assert "total_duration_ms" in result["meta"]
        assert isinstance(result["meta"]["total_duration_ms"], int)
        assert result["meta"]["total_duration_ms"] >= 0

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_returns_to_base(self, _pre, _br, mock_tourn, mock_chk, _art, _cp):
        mock_tourn.return_value = _tournament_result(num=2)

        handle_github_orchestrate_tournament({"challenge": "test"})

        mock_chk.assert_called_once_with("main")

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_returns_to_base_on_failure(self, _pre, mock_branch, mock_tourn, mock_chk, _art, _cp):
        mock_tourn.return_value = _tournament_result(num=3)
        mock_branch.side_effect = [
            {"ok": True, "branch": "rick/t/x/a", "base": "main"},
            {"ok": False, "error": "fail"},
        ]

        handle_github_orchestrate_tournament({"challenge": "test"})

        mock_chk.assert_called_once_with("main")

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_proposal_excerpt_truncated(self, _pre, _br, mock_tourn, _chk, _art, _cp):
        tr = _tournament_result(num=2)
        # make one proposal very long
        tr["approaches"][0]["proposal"] = "x" * 1000
        mock_tourn.return_value = tr

        result = handle_github_orchestrate_tournament(
            {"challenge": "test"},
        )

        assert len(result["contestants"][0]["proposal_excerpt"]) == 500

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_tournament_id_in_all_branches(self, _pre, _br, mock_tourn, _chk, _art, _cp):
        mock_tourn.return_value = _tournament_result(num=3, winner_id=2)

        result = handle_github_orchestrate_tournament(
            {"challenge": "test"},
        )

        tid = result["tournament_id"]
        for branch in result["branches_created"]:
            assert f"rick/t/{tid}/" in branch


# ---------------------------------------------------------------------------
# Phase 2 slice 1 — contestant artifact tests
# ---------------------------------------------------------------------------


class TestArtifactRelPath:
    def test_format(self):
        assert _artifact_rel_path("abc12345", "a") == ".rick/tournaments/abc12345/a.md"

    def test_preserves_label(self):
        for label in "abcde":
            assert _artifact_rel_path("t", label).endswith(f"/{label}.md")


class TestBuildArtifactBody:
    def _approach(self, **overrides):
        base = {
            "id": 2,
            "approach_name": "Functional",
            "proposal": "Use pure functions and immutable data.",
            "model_used": "azure_foundry",
        }
        base.update(overrides)
        return base

    def test_has_frontmatter_and_sections(self):
        body = _build_artifact_body(
            tournament_id="abc12345",
            label="b",
            challenge="Refactor auth",
            approach=self._approach(),
            created_at="2026-04-16T10:00:00+00:00",
        )
        # YAML frontmatter
        assert body.startswith("---\n")
        assert 'tournament_id: "abc12345"' in body
        assert 'contestant_label: "b"' in body
        assert "approach_id: 2" in body
        assert 'approach_name: "Functional"' in body
        assert 'model_used: "azure_foundry"' in body
        assert 'created_at: "2026-04-16T10:00:00+00:00"' in body
        # Body sections
        assert "# Contestant B — Functional" in body
        assert "## Challenge" in body
        assert "Refactor auth" in body
        assert "## Proposal" in body
        assert "Use pure functions and immutable data." in body

    def test_escapes_quotes_in_frontmatter(self):
        body = _build_artifact_body(
            tournament_id="t",
            label="a",
            challenge="c",
            approach=self._approach(approach_name='Has "quotes" inside'),
        )
        assert 'approach_name: "Has \\"quotes\\" inside"' in body

    def test_handles_missing_proposal(self):
        body = _build_artifact_body(
            tournament_id="t",
            label="a",
            challenge="c",
            approach={"id": 1, "approach_name": "X", "proposal": None},
        )
        assert "## Proposal" in body

    def test_includes_full_proposal_not_truncated(self):
        long_proposal = "y" * 3000
        body = _build_artifact_body(
            tournament_id="t",
            label="a",
            challenge="c",
            approach=self._approach(proposal=long_proposal),
        )
        assert long_proposal in body


class TestWriteArtifactAndCommit:
    """Unit tests for _write_artifact_and_commit (helper)."""

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}._write_artifact_file")
    def test_happy_path(self, mock_write, mock_commit):
        mock_commit.return_value = {
            "ok": True, "branch": "rick/t/t1/a", "commit_sha": "deadbeef", "pushed": True,
        }
        result = _write_artifact_and_commit(
            tournament_id="t1",
            label="a",
            challenge="c",
            approach={"id": 1, "approach_name": "X", "proposal": "p"},
            branch="rick/t/t1/a",
        )
        assert result["path"] == ".rick/tournaments/t1/a.md"
        assert result["written"] is True
        assert result["commit"]["ok"] is True
        assert result["commit"]["commit_sha"] == "deadbeef"
        # commit was called with the rel path and the right message
        call_kwargs = mock_commit.call_args[0][0]
        assert call_kwargs["files"] == [".rick/tournaments/t1/a.md"]
        assert "tournament(t1)" in call_kwargs["message"]
        assert "contestant A" in call_kwargs["message"]
        assert call_kwargs["branch_name"] == "rick/t/t1/a"

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}._write_artifact_file", side_effect=OSError("disk full"))
    def test_write_failure_captured(self, _mock_write, mock_commit):
        result = _write_artifact_and_commit(
            tournament_id="t1",
            label="a",
            challenge="c",
            approach={"id": 1, "approach_name": "X", "proposal": "p"},
            branch="rick/t/t1/a",
        )
        assert result["written"] is False
        assert result["commit"]["ok"] is False
        assert "write failed" in result["commit"]["error"]
        mock_commit.assert_not_called()

    @patch(f"{MOD}.handle_github_commit_and_push",
           side_effect=RuntimeError("git fetch failed"))
    @patch(f"{MOD}._write_artifact_file")
    def test_commit_exception_captured(self, _mock_write, _mock_commit):
        result = _write_artifact_and_commit(
            tournament_id="t1",
            label="a",
            challenge="c",
            approach={"id": 1, "approach_name": "X", "proposal": "p"},
            branch="rick/t/t1/a",
        )
        assert result["written"] is True
        assert result["commit"]["ok"] is False
        assert "commit failed" in result["commit"]["error"]

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}._write_artifact_file")
    def test_commit_returns_failure_preserved(self, _mock_write, mock_commit):
        mock_commit.return_value = {"ok": False, "error": "No staged changes"}
        result = _write_artifact_and_commit(
            tournament_id="t1",
            label="a",
            challenge="c",
            approach={"id": 1, "approach_name": "X", "proposal": "p"},
            branch="rick/t/t1/a",
        )
        assert result["written"] is True
        assert result["commit"]["ok"] is False
        assert result["commit"]["error"] == "No staged changes"


class TestOrchestrateArtifactIntegration:
    """Verify artifact helper is invoked per contestant with correct args."""

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_artifact_called_once_per_contestant(
        self, _pre, _br, mock_tourn, _chk, mock_art, _cp,
    ):
        mock_tourn.return_value = _tournament_result(num=3, winner_id=1)
        result = handle_github_orchestrate_tournament(
            {"challenge": "Optimize API"},
        )
        # 3 contestants = 3 artifact invocations (final branch does NOT
        # get an artifact in slice 1)
        assert mock_art.call_count == 3
        labels_called = [kw["label"] for _, kw in mock_art.call_args_list]
        assert labels_called == ["a", "b", "c"]
        # Challenge is forwarded
        for _, kw in mock_art.call_args_list:
            assert kw["challenge"] == "Optimize API"
            assert kw["tournament_id"] == result["tournament_id"]
            assert kw["branch"].startswith(f"rick/t/{result['tournament_id']}/")
        # Each contestant entry exposes the artifact result
        for c in result["contestants"]:
            assert "artifact" in c
            assert c["artifact"]["written"] is True
            assert c["artifact"]["commit"]["ok"] is True

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit")
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_artifact_failure_does_not_abort_tournament(
        self, _pre, _br, mock_tourn, _chk, mock_art, _cp,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_art.side_effect = [
            {
                "path": ".rick/tournaments/t/a.md",
                "written": True,
                "commit": {"ok": False, "error": "No staged changes"},
            },
            {
                "path": ".rick/tournaments/t/b.md",
                "written": True,
                "commit": {"ok": True, "commit_sha": "ab"},
            },
        ]
        result = handle_github_orchestrate_tournament({"challenge": "test"})

        assert result["ok"] is True
        assert len(result["contestants"]) == 2
        assert result["contestants"][0]["artifact"]["commit"]["ok"] is False
        assert result["contestants"][1]["artifact"]["commit"]["ok"] is True
        # final_branch still attempted because verdict had winner_id
        assert result["final_branch"] is not None

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_artifact_uses_full_proposal_not_excerpt(
        self, _pre, _br, mock_tourn, _chk, mock_art, _cp,
    ):
        tr = _tournament_result(num=1, winner_id=1)
        tr["approaches"][0]["proposal"] = "z" * 1000
        mock_tourn.return_value = tr

        handle_github_orchestrate_tournament({"challenge": "c"})

        # The approach dict forwarded to the artifact helper carries the
        # un-truncated proposal (the 500-char truncation is only for
        # proposal_excerpt in the response payload).
        forwarded_approach = mock_art.call_args_list[0][1]["approach"]
        assert len(forwarded_approach["proposal"]) == 1000


# ---------------------------------------------------------------------------
# Phase 2 slice 2 — winner commit selection + cherry-pick helper
# ---------------------------------------------------------------------------


def _contestant(cid, *, ok=True, sha="cafebabe"):
    return {
        "id": cid,
        "artifact": {
            "path": f".rick/tournaments/t/{cid}.md",
            "written": True,
            "commit": (
                {"ok": True, "commit_sha": sha} if ok
                else {"ok": False, "error": "no staged changes"}
            ),
        },
    }


class TestWinnerCommitInfo:
    def test_returns_sha_for_valid_winner(self):
        contestants = [_contestant(1, sha="abc123"), _contestant(2, sha="def456")]
        sha, cid = _winner_commit_info(contestants=contestants, winner_id=1)
        assert sha == "abc123"
        assert cid == 1

    def test_handles_string_winner_id(self):
        contestants = [_contestant(1, sha="abc123"), _contestant(2, sha="def456")]
        sha, cid = _winner_commit_info(contestants=contestants, winner_id="2")
        assert sha == "def456"
        assert cid == 2

    def test_returns_none_for_missing_winner_id(self):
        contestants = [_contestant(1)]
        assert _winner_commit_info(contestants=contestants, winner_id=None) == (
            None, None,
        )

    def test_returns_none_for_non_numeric_winner_id(self):
        contestants = [_contestant(1)]
        assert _winner_commit_info(
            contestants=contestants, winner_id="not-a-number",
        ) == (None, None)

    def test_returns_none_when_no_contestant_matches(self):
        contestants = [_contestant(1), _contestant(2)]
        assert _winner_commit_info(
            contestants=contestants, winner_id=99,
        ) == (None, None)

    def test_returns_cid_but_no_sha_when_commit_failed(self):
        contestants = [_contestant(1, ok=False), _contestant(2)]
        sha, cid = _winner_commit_info(contestants=contestants, winner_id=1)
        assert sha is None
        assert cid == 1

    def test_returns_none_sha_when_commit_sha_missing(self):
        contestants = [{
            "id": 1,
            "artifact": {"commit": {"ok": True}},  # no commit_sha field
        }]
        sha, cid = _winner_commit_info(contestants=contestants, winner_id=1)
        assert sha is None
        assert cid == 1

    def test_handles_contestant_without_artifact(self):
        contestants = [{"id": 1}]
        sha, cid = _winner_commit_info(contestants=contestants, winner_id=1)
        assert sha is None
        assert cid == 1


class TestCherryPickAndPush:
    """Unit tests for _cherry_pick_and_push (mocks subprocess)."""

    @patch(f"{MOD}.subprocess.run")
    def test_happy_path(self, mock_run):
        mock_run.side_effect = [
            # cherry-pick succeeds
            type("CP", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
            # push succeeds
            type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        ]
        result = _cherry_pick_and_push(
            final_branch="rick/t/x/final", winner_sha="abc123",
        )
        assert result == {"cherry_picked": True, "pushed": True, "error": None}
        assert mock_run.call_count == 2
        # First call is the cherry-pick
        first_cmd = mock_run.call_args_list[0][0][0]
        assert first_cmd[:2] == ["git", "cherry-pick"]
        assert first_cmd[-1] == "abc123"
        # Second call is the push
        second_cmd = mock_run.call_args_list[1][0][0]
        assert second_cmd[:4] == ["git", "push", "-u", "origin"]
        assert second_cmd[-1] == "rick/t/x/final"

    @patch(f"{MOD}.subprocess.run")
    def test_cherry_pick_conflict_aborts_and_reports(self, mock_run):
        mock_run.side_effect = [
            type("CP", (), {
                "returncode": 1, "stdout": "",
                "stderr": "CONFLICT (content): merge conflict in foo.py",
            })(),
            # abort call
            type("A", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        ]
        result = _cherry_pick_and_push(
            final_branch="rick/t/x/final", winner_sha="abc123",
        )
        assert result["cherry_picked"] is False
        assert result["pushed"] is False
        assert "cherry-pick failed" in result["error"]
        assert "CONFLICT" in result["error"]
        # Was the abort called?
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[1][0][0][:3] == [
            "git", "cherry-pick", "--abort",
        ]

    @patch(f"{MOD}.subprocess.run")
    def test_push_failure_reports_cherry_picked_true(self, mock_run):
        mock_run.side_effect = [
            # cherry-pick ok
            type("CP", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
            # push fails
            type("P", (), {
                "returncode": 1, "stdout": "",
                "stderr": "remote rejected: protected branch",
            })(),
        ]
        result = _cherry_pick_and_push(
            final_branch="rick/t/x/final", winner_sha="abc123",
        )
        assert result["cherry_picked"] is True
        assert result["pushed"] is False
        assert "push failed" in result["error"]

    @patch(f"{MOD}.subprocess.run")
    def test_cherry_pick_timeout(self, mock_run):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="git cherry-pick", timeout=60)
        result = _cherry_pick_and_push(
            final_branch="rick/t/x/final", winner_sha="abc123",
        )
        assert result["cherry_picked"] is False
        assert result["pushed"] is False
        assert result["error"] == "cherry-pick timeout"

    @patch(f"{MOD}.subprocess.run")
    def test_cherry_pick_unexpected_exception(self, mock_run):
        mock_run.side_effect = RuntimeError("git binary missing")
        result = _cherry_pick_and_push(
            final_branch="rick/t/x/final", winner_sha="abc123",
        )
        assert result["cherry_picked"] is False
        assert result["pushed"] is False
        assert "cherry-pick error" in result["error"]


class TestFinalCherryPickIntegration:
    """End-to-end orchestration behaviour for the final branch in slice 2."""

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_happy_path_cherry_picks_and_pushes(
        self, _pre, _br, mock_tourn, _chk, _art, mock_cp,
    ):
        mock_tourn.return_value = _tournament_result(num=3, winner_id=2)

        result = handle_github_orchestrate_tournament(
            {"challenge": "Optimize API"},
        )

        assert result["final_branch"] is not None
        assert result["final_branch"].endswith("/final")
        assert result["final_result"] is not None
        assert result["final_result"]["cherry_picked"] is True
        assert result["final_result"]["pushed"] is True
        assert result["final_result"]["from_commit_sha"] == "deadbeef"
        assert result["final_result"]["from_contestant_id"] == 2
        assert result["final_result"]["error"] is None

        # cherry-pick helper called exactly once with the winner's sha
        assert mock_cp.call_count == 1
        kwargs = mock_cp.call_args.kwargs
        assert kwargs["winner_sha"] == "deadbeef"
        assert kwargs["final_branch"].endswith("/final")

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_escalate_skips_cherry_pick_and_final_result(
        self, _pre, _br, mock_tourn, _chk, _art, mock_cp,
    ):
        mock_tourn.return_value = _tournament_result(num=3, escalate=True)

        result = handle_github_orchestrate_tournament({"challenge": "x"})

        assert result["final_branch"] is None
        assert result["final_result"] is None
        mock_cp.assert_not_called()

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit")
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_winner_with_failed_commit_creates_empty_final_branch(
        self, _pre, _br, mock_tourn, _chk, mock_art, mock_cp,
    ):
        # Winner is contestant 1, but its artifact commit failed in slice 1.
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_art.side_effect = [
            {
                "path": ".rick/tournaments/t/a.md",
                "written": True,
                "commit": {"ok": False, "error": "no staged changes"},
            },
            {
                "path": ".rick/tournaments/t/b.md",
                "written": True,
                "commit": {"ok": True, "commit_sha": "ab"},
            },
        ]

        result = handle_github_orchestrate_tournament({"challenge": "x"})

        # Final branch is still created (legacy Phase-1 behaviour).
        assert result["final_branch"] is not None
        assert result["final_branch"].endswith("/final")
        # But no cherry-pick was attempted.
        mock_cp.assert_not_called()
        fr = result["final_result"]
        assert fr is not None
        assert fr["cherry_picked"] is False
        assert fr["pushed"] is False
        assert fr["from_commit_sha"] is None
        assert fr["from_contestant_id"] == 1
        assert "no valid commit" in fr["error"]

    @patch(f"{MOD}._cherry_pick_and_push")
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_cherry_pick_conflict_surfaces_in_final_result(
        self, _pre, _br, mock_tourn, _chk, _art, mock_cp,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_cp.return_value = {
            "cherry_picked": False,
            "pushed": False,
            "error": "cherry-pick failed: CONFLICT",
        }

        result = handle_github_orchestrate_tournament({"challenge": "x"})

        assert result["final_branch"] is not None
        fr = result["final_result"]
        assert fr is not None
        assert fr["cherry_picked"] is False
        assert fr["pushed"] is False
        assert fr["from_commit_sha"] == "deadbeef"
        assert "CONFLICT" in fr["error"]

    @patch(f"{MOD}._cherry_pick_and_push")
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_push_failure_surfaces_in_final_result(
        self, _pre, _br, mock_tourn, _chk, _art, mock_cp,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_cp.return_value = {
            "cherry_picked": True,
            "pushed": False,
            "error": "push failed: protected branch",
        }

        result = handle_github_orchestrate_tournament({"challenge": "x"})

        fr = result["final_result"]
        assert fr["cherry_picked"] is True
        assert fr["pushed"] is False
        assert "push failed" in fr["error"]

    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_final_branch_creation_failure_leaves_final_result_none(
        self, _pre, mock_branch, mock_tourn, _chk, _art, mock_cp,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        # First two calls (contestants) succeed, final branch creation fails.
        mock_branch.side_effect = [
            {"ok": True, "branch": "rick/t/x/a", "base": "main"},
            {"ok": True, "branch": "rick/t/x/b", "base": "main"},
            {"ok": False, "error": "already exists"},
        ]

        result = handle_github_orchestrate_tournament({"challenge": "x"})

        # Same degradation path as Phase 1 when final branch can't be created.
        assert result["final_branch"] is None
        assert result["final_result"] is None
        mock_cp.assert_not_called()


# ---------------------------------------------------------------------------
# Phase 2 slice 4 — single-file code change (opt-in)
# ---------------------------------------------------------------------------


class TestCodePrefix:
    def test_format(self):
        assert _code_prefix("abc12345", "a") == ".rick/contestants/abc12345/a/"

    def test_trailing_slash(self):
        # The slash is mandatory so downstream startswith checks don't
        # accidentally match e.g. a sibling label like 'ab'.
        assert _code_prefix("t1", "a").endswith("/")


class TestBuildCodePrompt:
    def test_system_declares_file_contract(self):
        prompts = _build_code_prompt(
            tournament_id="t1",
            label="a",
            idx=1,
            approach_name="Functional",
            challenge="Do X",
            proposal="Full proposal.",
        )
        system = prompts["system"]
        assert "FILE: <relative_path>" in system
        assert "EXACTLY ONE FILE" in system
        assert ".rick/contestants/t1/a/" in system

    def test_system_forbids_unsafe_paths(self):
        prompts = _build_code_prompt(
            tournament_id="t1",
            label="a",
            idx=1,
            approach_name="X",
            challenge="c",
            proposal="p",
        )
        system = prompts["system"]
        # Key forbidden-path rules surface in the prompt.
        assert ".." in system  # "MUST NOT contain '..'"
        assert "[A-Za-z0-9._/-]" in system
        assert "diff" in system.lower()
        assert "patch" in system.lower()

    def test_user_includes_challenge_and_proposal(self):
        prompts = _build_code_prompt(
            tournament_id="t1",
            label="a",
            idx=1,
            approach_name="X",
            challenge="the challenge",
            proposal="the proposal",
        )
        assert "the challenge" in prompts["user"]
        assert "the proposal" in prompts["user"]


class TestParseFileBlock:
    PREFIX = ".rick/contestants/t1/a/"

    def _ok_response(self, *, path=".rick/contestants/t1/a/change.py",
                     content="print('hi')\n", lang="python"):
        return f"FILE: {path}\n```{lang}\n{content}```\n"

    def test_happy_path(self):
        res = _parse_file_block(
            self._ok_response(), expected_prefix=self.PREFIX,
        )
        assert res["ok"] is True
        assert res["path"] == ".rick/contestants/t1/a/change.py"
        assert res["content"] == "print('hi')\n"
        assert res["error"] is None

    def test_empty_response(self):
        res = _parse_file_block("", expected_prefix=self.PREFIX)
        assert res["ok"] is False
        assert "empty" in res["error"]

    def test_no_file_header(self):
        res = _parse_file_block(
            "Here is some code:\n```py\nx=1\n```\n",
            expected_prefix=self.PREFIX,
        )
        assert res["ok"] is False
        assert "no FILE block" in res["error"]

    def test_rejects_multiple_file_headers(self):
        text = (
            "FILE: .rick/contestants/t1/a/one.py\n```py\nprint(1)\n```\n"
            "FILE: .rick/contestants/t1/a/two.py\n```py\nprint(2)\n```\n"
        )
        res = _parse_file_block(text, expected_prefix=self.PREFIX)
        assert res["ok"] is False
        assert "multiple FILE blocks" in res["error"]

    def test_rejects_wrong_prefix(self):
        text = (
            "FILE: src/evil.py\n```py\npayload\n```\n"
        )
        res = _parse_file_block(text, expected_prefix=self.PREFIX)
        assert res["ok"] is False
        assert "must start with" in res["error"]
        assert res["path"] == "src/evil.py"

    def test_rejects_absolute_path(self):
        text = "FILE: /etc/passwd\n```sh\nroot:x:0:0\n```\n"
        res = _parse_file_block(text, expected_prefix=self.PREFIX)
        assert res["ok"] is False
        # Wrong prefix check kicks in first; that's fine — both rules
        # agree the path is invalid.
        assert "start with" in res["error"] or "absolute" in res["error"]

    def test_rejects_parent_traversal(self):
        text = (
            "FILE: .rick/contestants/t1/a/../../etc/passwd\n"
            "```sh\npayload\n```\n"
        )
        res = _parse_file_block(text, expected_prefix=self.PREFIX)
        assert res["ok"] is False
        assert ".." in res["error"]

    def test_rejects_bad_charset(self):
        text = (
            "FILE: .rick/contestants/t1/a/weird file.py\n"
            "```py\nx=1\n```\n"
        )
        res = _parse_file_block(text, expected_prefix=self.PREFIX)
        assert res["ok"] is False
        assert "forbidden characters" in res["error"]

    def test_rejects_malformed_fence(self):
        # Missing closing fence
        text = "FILE: .rick/contestants/t1/a/x.py\n```py\nprint(1)\n"
        res = _parse_file_block(text, expected_prefix=self.PREFIX)
        assert res["ok"] is False
        assert "malformed" in res["error"]

    def test_rejects_content_too_large(self):
        big = "a" * (100 * 1024 + 1)
        text = f"FILE: .rick/contestants/t1/a/big.txt\n```text\n{big}\n```"
        res = _parse_file_block(text, expected_prefix=self.PREFIX)
        assert res["ok"] is False
        assert "exceeds" in res["error"]

    def test_accepts_empty_content(self):
        text = "FILE: .rick/contestants/t1/a/empty.py\n```python\n```"
        res = _parse_file_block(text, expected_prefix=self.PREFIX)
        assert res["ok"] is True
        assert res["content"] == ""

    def test_language_tag_is_ignored(self):
        # Any language tag (or none) on the opening fence is fine.
        text = "FILE: .rick/contestants/t1/a/x.py\n```\nprint(1)\n```"
        res = _parse_file_block(text, expected_prefix=self.PREFIX)
        assert res["ok"] is True
        assert res["content"] == "print(1)\n"


class TestResolveInsideSandbox:
    PREFIX = ".rick/contestants/t1/a/"

    def test_happy_path_inside_sandbox(self, tmp_path):
        res = _resolve_inside_sandbox(
            str(tmp_path),
            ".rick/contestants/t1/a/change.py",
            self.PREFIX,
        )
        assert res["ok"] is True
        assert str(res["abs_path"]).endswith("change.py")

    def test_rejects_escape_via_symlink_target(self, tmp_path):
        # Even if somehow the rel path resolved to outside, the
        # relative_to check catches it.
        res = _resolve_inside_sandbox(
            str(tmp_path),
            ".rick/contestants/t1/a/../../../outside.py",
            self.PREFIX,
        )
        assert res["ok"] is False
        assert "escapes" in res["error"]


class TestGenerateAndCommitCodeChange:
    """Unit tests for the slice-4 orchestrator helper."""

    def _llm_ok(self, rel="", content="print('ok')\n"):
        if not rel:
            rel = ".rick/contestants/t1/a/change.py"
        return {
            "text": f"FILE: {rel}\n```python\n{content}```\n",
            "model": "azure_foundry",
        }

    def _approach(self):
        return {
            "id": 1,
            "approach_name": "Functional",
            "proposal": "Full proposal text.",
            "model_used": "azure_foundry",
        }

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}.handle_llm_generate")
    def test_happy_path_writes_and_commits(
        self, mock_llm, mock_commit, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(f"{MOD}.config.GITHUB_REPO_PATH", str(tmp_path))
        mock_llm.return_value = self._llm_ok()
        mock_commit.return_value = {
            "ok": True, "commit_sha": "c0de01", "branch": "rick/t/t1/a",
        }

        result = _generate_and_commit_code_change(
            tournament_id="t1",
            label="a",
            idx=1,
            approach=self._approach(),
            challenge="Do X",
            branch="rick/t/t1/a",
        )

        assert result["attempted"] is True
        assert result["written"] is True
        assert result["parse_error"] is None
        assert result["path"] == ".rick/contestants/t1/a/change.py"
        assert result["commit"]["ok"] is True
        # File actually landed on disk under the sandbox.
        target = tmp_path / ".rick/contestants/t1/a/change.py"
        assert target.exists()
        assert "print('ok')" in target.read_text()
        # Commit was invoked with only that file.
        commit_kwargs = mock_commit.call_args[0][0]
        assert commit_kwargs["files"] == [".rick/contestants/t1/a/change.py"]
        assert commit_kwargs["branch_name"] == "rick/t/t1/a"

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}.handle_llm_generate")
    def test_llm_exception_captured(
        self, mock_llm, mock_commit, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(f"{MOD}.config.GITHUB_REPO_PATH", str(tmp_path))
        mock_llm.side_effect = RuntimeError("boom")

        result = _generate_and_commit_code_change(
            tournament_id="t1", label="a", idx=1,
            approach=self._approach(), challenge="c", branch="b",
        )

        assert result["written"] is False
        assert result["commit"] is None
        assert "llm error" in result["parse_error"]
        mock_commit.assert_not_called()

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}.handle_llm_generate")
    def test_parse_error_captured_no_commit(
        self, mock_llm, mock_commit, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(f"{MOD}.config.GITHUB_REPO_PATH", str(tmp_path))
        mock_llm.return_value = {"text": "I cannot produce a file.", "model": "m"}

        result = _generate_and_commit_code_change(
            tournament_id="t1", label="a", idx=1,
            approach=self._approach(), challenge="c", branch="b",
        )

        assert result["written"] is False
        assert result["commit"] is None
        assert result["parse_error"] is not None
        mock_commit.assert_not_called()
        # Nothing on disk.
        assert not (tmp_path / ".rick/contestants/t1/a/change.py").exists()

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}.handle_llm_generate")
    def test_sandbox_escape_is_refused_before_write(
        self, mock_llm, mock_commit, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(f"{MOD}.config.GITHUB_REPO_PATH", str(tmp_path))
        mock_llm.return_value = {
            "text": (
                "FILE: src/injection.py\n"
                "```python\npayload()\n```\n"
            ),
            "model": "m",
        }

        result = _generate_and_commit_code_change(
            tournament_id="t1", label="a", idx=1,
            approach=self._approach(), challenge="c", branch="b",
        )

        assert result["written"] is False
        assert result["commit"] is None
        assert result["parse_error"] is not None
        mock_commit.assert_not_called()
        # Most importantly: no file written outside the sandbox.
        assert not (tmp_path / "src/injection.py").exists()

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}.handle_llm_generate")
    def test_commit_exception_captured(
        self, mock_llm, mock_commit, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(f"{MOD}.config.GITHUB_REPO_PATH", str(tmp_path))
        mock_llm.return_value = self._llm_ok()
        mock_commit.side_effect = RuntimeError("git push rejected")

        result = _generate_and_commit_code_change(
            tournament_id="t1", label="a", idx=1,
            approach=self._approach(), challenge="c", branch="b",
        )

        # File was written even though commit failed (same degradation
        # contract as _write_artifact_and_commit).
        assert result["written"] is True
        assert result["commit"]["ok"] is False
        assert "commit failed" in result["commit"]["error"]


class TestWinnerCommitInfoPrefersCodeChange:
    """Slice 4 preference: code_change.commit wins over artifact.commit."""

    def _contestant(self, cid, *, artifact_sha="art", code_sha=None,
                    code_ok=True, artifact_ok=True):
        c = {
            "id": cid,
            "artifact": {
                "commit": (
                    {"ok": True, "commit_sha": artifact_sha}
                    if artifact_ok else {"ok": False}
                ),
            },
        }
        if code_sha is not None or code_ok is False:
            c["code_change"] = {
                "commit": (
                    {"ok": True, "commit_sha": code_sha}
                    if code_ok else {"ok": False}
                ),
            }
        return c

    def test_code_change_sha_preferred_over_artifact(self):
        contestants = [self._contestant(1, artifact_sha="art1",
                                        code_sha="code1")]
        sha, cid = _winner_commit_info(contestants=contestants, winner_id=1)
        assert sha == "code1"
        assert cid == 1

    def test_falls_back_to_artifact_when_code_change_missing(self):
        # No code_change field at all — pure slice-1/2 contestant.
        contestants = [{
            "id": 1,
            "artifact": {"commit": {"ok": True, "commit_sha": "art1"}},
        }]
        sha, cid = _winner_commit_info(contestants=contestants, winner_id=1)
        assert sha == "art1"
        assert cid == 1

    def test_falls_back_to_artifact_when_code_change_failed(self):
        contestants = [self._contestant(
            1, artifact_sha="art1", code_ok=False,
        )]
        sha, cid = _winner_commit_info(contestants=contestants, winner_id=1)
        assert sha == "art1"
        assert cid == 1

    def test_returns_none_when_both_failed(self):
        contestants = [self._contestant(
            1, artifact_ok=False, code_ok=False,
        )]
        sha, cid = _winner_commit_info(contestants=contestants, winner_id=1)
        assert sha is None
        assert cid == 1


class TestOrchestrateCodeChangeIntegration:
    """End-to-end wiring of slice-4 into handle_github_orchestrate_tournament."""

    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_flag_off_skips_code_change(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, mock_code,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament(
            {"challenge": "c"},  # generate_code omitted → default False
        )

        mock_code.assert_not_called()
        for c in result["contestants"]:
            assert c["code_change"] is None

    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_flag_on_calls_code_change_once_per_contestant(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, mock_code,
    ):
        mock_tourn.return_value = _tournament_result(num=3, winner_id=1)

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
        })

        assert mock_code.call_count == 3
        for c in result["contestants"]:
            assert c["code_change"] is not None
            assert c["code_change"]["attempted"] is True
            assert c["code_change"]["commit"]["ok"] is True

    @patch(f"{MOD}._generate_and_commit_code_change")
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_code_change_failure_does_not_abort_tournament(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, mock_code,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_code.side_effect = [
            {
                "attempted": True, "path": None, "written": False,
                "parse_error": "no FILE block found", "commit": None,
            },
            _code_change_noop(label="b", tournament_id="t", branch="x"),
        ]

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
        })

        assert result["ok"] is True
        assert len(result["contestants"]) == 2
        assert result["contestants"][0]["code_change"]["written"] is False
        assert result["contestants"][1]["code_change"]["written"] is True

    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_cherry_pick_uses_code_change_sha_when_flag_on(
        self, _pre, _br, mock_tourn, _chk, _art, mock_cp, _code,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
        })

        # The cherry-pick helper must receive the code-change SHA
        # ("c0dec0de" from _code_change_noop), NOT the artifact SHA
        # ("deadbeef" from _artifact_noop).
        assert mock_cp.call_count == 1
        assert mock_cp.call_args.kwargs["winner_sha"] == "c0dec0de"
        assert result["final_result"]["from_commit_sha"] == "c0dec0de"


# ---------------------------------------------------------------------------
# Phase 2 slice 4b — target_file validation + real-repo code change
# ---------------------------------------------------------------------------


class TestValidateTargetFile:
    """Unit tests for _validate_target_file input guardrails."""

    def test_accepts_regular_py_file(self):
        r = _validate_target_file("worker/tasks/example.py")
        assert r["ok"] is True
        assert r["normalized"] == "worker/tasks/example.py"
        assert r["error"] is None

    def test_accepts_markdown(self):
        assert _validate_target_file("docs/notes.md")["ok"] is True

    def test_accepts_toml(self):
        assert _validate_target_file("pyproject.toml")["ok"] is True

    def test_rejects_none(self):
        r = _validate_target_file(None)
        assert r["ok"] is False and "required" in r["error"]

    def test_rejects_non_string(self):
        r = _validate_target_file(42)
        assert r["ok"] is False and "string" in r["error"]

    def test_rejects_empty(self):
        r = _validate_target_file("   ")
        assert r["ok"] is False and "empty" in r["error"]

    def test_rejects_absolute_path(self):
        r = _validate_target_file("/etc/passwd")
        assert r["ok"] is False and "relative" in r["error"]

    def test_rejects_parent_traversal(self):
        r = _validate_target_file("../outside.py")
        assert r["ok"] is False and ".." in r["error"]

    def test_rejects_dot_segment(self):
        r = _validate_target_file("./config.py")
        assert r["ok"] is False

    def test_rejects_double_slash(self):
        r = _validate_target_file("worker//tasks.py")
        assert r["ok"] is False

    def test_rejects_bad_charset(self):
        r = _validate_target_file("worker/tasks/bad name.py")
        assert r["ok"] is False and "forbidden" in r["error"]

    @pytest.mark.parametrize("prefix", [
        ".git/config", ".github/workflows/ci.yml",
        ".rick/tournaments/x.py", ".venv/lib/x.py",
        "venv/lib/x.py", "node_modules/pkg/index.js",
        "__pycache__/x.py",
    ])
    def test_rejects_protected_prefixes(self, prefix):
        r = _validate_target_file(prefix)
        assert r["ok"] is False
        assert "protected prefix" in r["error"]

    def test_rejects_disallowed_extension(self):
        r = _validate_target_file("malware.exe")
        assert r["ok"] is False and "extension" in r["error"]

    def test_rejects_binary_extension(self):
        r = _validate_target_file("image.png")
        assert r["ok"] is False and "extension" in r["error"]

    def test_extension_is_case_insensitive(self):
        assert _validate_target_file("README.MD")["ok"] is True


class TestParseFileBlockExactMode:
    """Slice 4b: parser must enforce byte-exact path match."""

    def test_requires_one_of_prefix_or_exact(self):
        r = _parse_file_block("FILE: x.py\n```py\nx\n```")
        assert r["ok"] is False
        assert "misconfigured" in r["error"]

    def test_rejects_both_prefix_and_exact(self):
        r = _parse_file_block(
            "FILE: x.py\n```py\nx\n```",
            expected_prefix=".rick/contestants/t/a/",
            expected_path="worker/x.py",
        )
        assert r["ok"] is False
        assert "misconfigured" in r["error"]

    def test_accepts_exact_match(self):
        text = "FILE: worker/tasks/foo.py\n```python\nprint('hi')\n```"
        r = _parse_file_block(text, expected_path="worker/tasks/foo.py")
        assert r["ok"] is True
        assert r["path"] == "worker/tasks/foo.py"
        assert "print('hi')" in r["content"]

    def test_rejects_different_path(self):
        text = "FILE: worker/tasks/other.py\n```python\nprint('hi')\n```"
        r = _parse_file_block(text, expected_path="worker/tasks/foo.py")
        assert r["ok"] is False
        assert "equal exactly" in r["error"]

    def test_rejects_extra_suffix(self):
        text = "FILE: worker/tasks/foo.py.bak\n```python\nx=1\n```"
        r = _parse_file_block(text, expected_path="worker/tasks/foo.py")
        assert r["ok"] is False

    def test_rejects_extra_subdir(self):
        text = "FILE: worker/tasks/foo.py/evil.py\n```python\nx=1\n```"
        r = _parse_file_block(text, expected_path="worker/tasks/foo.py")
        assert r["ok"] is False

    def test_rejects_case_mismatch(self):
        text = "FILE: Worker/Tasks/Foo.py\n```python\nx=1\n```"
        r = _parse_file_block(text, expected_path="worker/tasks/foo.py")
        assert r["ok"] is False

    def test_rejects_multiple_headers_in_exact_mode(self):
        text = (
            "FILE: worker/tasks/foo.py\n```python\na=1\n```\n"
            "FILE: worker/tasks/foo.py\n```python\nb=2\n```"
        )
        r = _parse_file_block(text, expected_path="worker/tasks/foo.py")
        assert r["ok"] is False
        assert "multiple" in r["error"]

    def test_exact_mode_still_enforces_size_cap(self):
        huge = "x" * (101 * 1024)
        text = f"FILE: worker/x.py\n```python\n{huge}\n```"
        r = _parse_file_block(text, expected_path="worker/x.py")
        assert r["ok"] is False
        assert "exceeds" in r["error"]


class TestBuildCodePromptTargetFile:
    """Slice 4b: prompt differentiation for target_file mode."""

    def test_prompt_requires_exact_path(self):
        p = _build_code_prompt(
            tournament_id="t1", label="a", idx=1,
            approach_name="X", challenge="c", proposal="p",
            target_file="worker/tasks/foo.py",
        )
        assert "MUST equal exactly: worker/tasks/foo.py" in p["system"]
        assert "Do NOT change the path" in p["system"]
        # sandbox hint should NOT be in the prompt
        assert "MUST start with" not in p["system"]
        assert "worker/tasks/foo.py" in p["user"]

    def test_sandbox_mode_unchanged_when_no_target(self):
        p = _build_code_prompt(
            tournament_id="t1", label="a", idx=1,
            approach_name="X", challenge="c", proposal="p",
        )
        assert "MUST start with: .rick/contestants/t1/a/" in p["system"]
        assert "MUST equal exactly" not in p["system"]


class TestResolveInsideSandboxNoPrefix:
    """Slice 4b: resolver with no prefix validates repo-scope only."""

    def test_accepts_path_inside_repo(self, tmp_path):
        (tmp_path / "worker" / "tasks").mkdir(parents=True)
        r = _resolve_inside_sandbox(str(tmp_path), "worker/tasks/x.py", None)
        assert r["ok"] is True

    def test_rejects_escape_via_symlink(self, tmp_path):
        # Canonical resolution must catch a symlink to /etc
        (tmp_path / "worker").mkdir()
        outside = tmp_path.parent / "zz_outside_slice4b"
        outside.mkdir(exist_ok=True)
        link = tmp_path / "worker" / "link"
        link.symlink_to(outside)
        r = _resolve_inside_sandbox(
            str(tmp_path), "worker/link/evil.py", None,
        )
        assert r["ok"] is False
        assert "repository" in r["error"]


class TestGenerateAndCommitCodeChangeTargetFile:
    """Slice 4b: helper end-to-end with target_file."""

    def _approach(self):
        return {
            "id": 1,
            "approach_name": "Clean",
            "proposal": "Add docstring",
            "model_used": "azure_foundry",
        }

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}.handle_llm_generate")
    @patch(f"{MOD}.config")
    def test_happy_path_writes_real_repo_file(
        self, mock_cfg, mock_llm, mock_commit, tmp_path,
    ):
        mock_cfg.GITHUB_REPO_PATH = str(tmp_path)
        mock_llm.return_value = {
            "text": (
                "FILE: worker/tasks/foo.py\n"
                "```python\n"
                "def hello():\n    return 1\n"
                "```\n"
            ),
        }
        mock_commit.return_value = {
            "ok": True, "branch": "b", "commit_sha": "abc123",
        }

        result = _generate_and_commit_code_change(
            tournament_id="t9", label="a", idx=1,
            approach=self._approach(),
            challenge="Do X",
            branch="rick/t/t9/a",
            target_file="worker/tasks/foo.py",
        )

        assert result["attempted"] is True
        assert result["mode"] == "target_file"
        assert result["target_file"] == "worker/tasks/foo.py"
        assert result["written"] is True
        assert result["parse_error"] is None
        assert result["path"] == "worker/tasks/foo.py"
        assert result["commit"]["ok"] is True

        target = tmp_path / "worker" / "tasks" / "foo.py"
        assert target.exists()
        assert "def hello" in target.read_text()

        # Commit must reference the real repo path, one file only.
        kw = mock_commit.call_args.args[0]
        assert kw["files"] == ["worker/tasks/foo.py"]
        assert "rick/t/t9/a" in kw["branch_name"]

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}.handle_llm_generate")
    @patch(f"{MOD}.config")
    def test_rejects_llm_emitting_different_path(
        self, mock_cfg, mock_llm, mock_commit, tmp_path,
    ):
        mock_cfg.GITHUB_REPO_PATH = str(tmp_path)
        mock_llm.return_value = {
            "text": (
                "FILE: worker/tasks/other.py\n"
                "```python\nx = 1\n```\n"
            ),
        }

        result = _generate_and_commit_code_change(
            tournament_id="t9", label="a", idx=1,
            approach=self._approach(),
            challenge="Do X",
            branch="rick/t/t9/a",
            target_file="worker/tasks/foo.py",
        )

        assert result["written"] is False
        assert result["parse_error"] is not None
        assert "equal exactly" in result["parse_error"]
        mock_commit.assert_not_called()
        # No file should be written anywhere under the repo.
        assert not (tmp_path / "worker" / "tasks" / "other.py").exists()
        assert not (tmp_path / "worker" / "tasks" / "foo.py").exists()

    @patch(f"{MOD}.handle_github_commit_and_push")
    @patch(f"{MOD}.handle_llm_generate")
    @patch(f"{MOD}.config")
    def test_result_mode_field_is_target_file(
        self, mock_cfg, mock_llm, mock_commit, tmp_path,
    ):
        mock_cfg.GITHUB_REPO_PATH = str(tmp_path)
        mock_llm.return_value = {"text": ""}
        result = _generate_and_commit_code_change(
            tournament_id="t9", label="a", idx=1,
            approach=self._approach(), challenge="c",
            branch="b", target_file="worker/x.py",
        )
        assert result["mode"] == "target_file"
        assert result["target_file"] == "worker/x.py"


class TestOrchestrateTargetFileIntegration:
    """Slice 4b end-to-end wiring through handle_github_orchestrate_tournament."""

    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_target_file_forwarded_to_helper(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, mock_code,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": "worker/tasks/example.py",
        })

        assert result["ok"] is True
        assert mock_code.call_count == 2
        for call in mock_code.call_args_list:
            assert call.kwargs["target_file"] == "worker/tasks/example.py"
        assert result["meta"]["generate_code"] is True
        assert result["meta"]["target_file"] == "worker/tasks/example.py"
        for c in result["contestants"]:
            assert c["code_change"]["mode"] == "target_file"
            assert c["code_change"]["target_file"] == "worker/tasks/example.py"

    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_target_file_ignored_when_generate_code_off(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, mock_code,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": False,
            "target_file": "worker/tasks/example.py",
        })

        assert result["ok"] is True
        # Helper must not have been called at all.
        mock_code.assert_not_called()
        assert result["meta"]["generate_code"] is False
        assert result["meta"]["target_file"] is None

    @patch(f"{MOD}._generate_and_commit_code_change")
    @patch(f"{MOD}._cherry_pick_and_push")
    @patch(f"{MOD}._write_artifact_and_commit")
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_invalid_target_file_aborts_before_any_branch(
        self, _pre, mock_br, mock_tourn, _chk, mock_art, mock_cp, mock_code,
    ):
        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": ".git/config",
        })

        assert result["ok"] is False
        assert "invalid target_file" in result["error"]
        assert "protected prefix" in result["error"]
        # Crucially: no branch, no tournament, no artifact, no code change,
        # no cherry-pick triggered.
        mock_br.assert_not_called()
        mock_tourn.assert_not_called()
        mock_art.assert_not_called()
        mock_code.assert_not_called()
        mock_cp.assert_not_called()

    @patch(f"{MOD}._generate_and_commit_code_change")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_absolute_target_file_rejected_early(
        self, _pre, mock_tourn, mock_br, mock_code,
    ):
        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": "/etc/passwd",
        })
        assert result["ok"] is False
        assert "relative" in result["error"]
        mock_br.assert_not_called()
        mock_tourn.assert_not_called()
        mock_code.assert_not_called()

    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_no_target_file_falls_back_to_sandbox_mode(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, mock_code,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
        })

        assert result["ok"] is True
        for call in mock_code.call_args_list:
            assert call.kwargs.get("target_file") is None
        assert result["meta"]["target_file"] is None
        for c in result["contestants"]:
            assert c["code_change"]["mode"] == "sandbox"


# ---------------------------------------------------------------------------
# Phase 2 slice 5 — per-contestant validation
# ---------------------------------------------------------------------------


class TestValidateValidationMode:
    def test_accepts_none_as_default(self):
        r = _validate_validation_mode(None)
        assert r["ok"] is True
        assert r["normalized"] == "none"

    def test_accepts_empty_string_as_default(self):
        assert _validate_validation_mode("")["normalized"] == "none"

    def test_accepts_none_literal(self):
        assert _validate_validation_mode("none")["normalized"] == "none"

    def test_accepts_python_compile(self):
        assert _validate_validation_mode("python_compile")["normalized"] == "python_compile"

    def test_is_case_insensitive(self):
        assert _validate_validation_mode("Python_Compile")["normalized"] == "python_compile"

    def test_trims_whitespace(self):
        assert _validate_validation_mode("  python_compile  ")["normalized"] == "python_compile"

    def test_rejects_unknown_mode(self):
        r = _validate_validation_mode("pytest_target")
        assert r["ok"] is False
        assert "invalid validation_mode" in r["error"]
        assert "python_compile" in r["error"]

    def test_rejects_non_string(self):
        r = _validate_validation_mode(42)
        assert r["ok"] is False
        assert "string" in r["error"]

    def test_rejects_arbitrary_command(self):
        r = _validate_validation_mode("; rm -rf /")
        assert r["ok"] is False


class TestValidateValidationTimeout:
    def test_accepts_none_as_default(self):
        r = _validate_validation_timeout(None)
        assert r["ok"] is True and r["normalized"] == 20

    def test_accepts_int(self):
        assert _validate_validation_timeout(5)["normalized"] == 5

    def test_accepts_float(self):
        assert _validate_validation_timeout(2.5)["normalized"] == 2.5

    def test_caps_at_max(self):
        r = _validate_validation_timeout(9999)
        assert r["ok"] is True
        assert r["normalized"] == 60.0

    def test_rejects_zero(self):
        r = _validate_validation_timeout(0)
        assert r["ok"] is False

    def test_rejects_negative(self):
        r = _validate_validation_timeout(-1)
        assert r["ok"] is False

    def test_rejects_string(self):
        r = _validate_validation_timeout("20")
        assert r["ok"] is False
        assert "number" in r["error"]

    def test_rejects_bool(self):
        r = _validate_validation_timeout(True)
        assert r["ok"] is False


class TestTailLog:
    def test_empty_returns_empty(self):
        assert _tail_log("") == ""
        assert _tail_log(None) == ""

    def test_keeps_last_lines(self):
        text = "\n".join(f"line {i}" for i in range(100))
        tail = _tail_log(text)
        assert "line 99" in tail
        assert "line 0" not in tail
        assert "line 80" in tail or "line 81" in tail  # last 20

    def test_caps_char_count(self):
        text = "x" * 5000
        tail = _tail_log(text)
        assert len(tail) <= 2000


class TestRunPythonCompileValidation:
    """Real subprocess exercise — py_compile is safe (no import, just parse)."""

    def test_passes_on_valid_python(self, tmp_path):
        f = tmp_path / "good.py"
        f.write_text("def add(a, b):\n    return a + b\n")
        r = _run_python_compile_validation(
            repo_path=str(tmp_path), rel_path="good.py", timeout_s=10,
        )
        assert r["ran"] is True
        assert r["mode"] == "python_compile"
        assert r["passed"] is True
        assert r["error"] is None
        assert isinstance(r["duration_ms"], int)

    def test_fails_on_syntax_error(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def oops(:\n")
        r = _run_python_compile_validation(
            repo_path=str(tmp_path), rel_path="bad.py", timeout_s=10,
        )
        assert r["ran"] is True
        assert r["passed"] is False
        assert r["error"] is None
        assert "SyntaxError" in r["log_tail"] or "syntax" in r["log_tail"].lower()

    def test_fails_when_file_missing(self, tmp_path):
        r = _run_python_compile_validation(
            repo_path=str(tmp_path),
            rel_path="ghost.py",
            timeout_s=10,
        )
        assert r["ran"] is True
        assert r["passed"] is False

    @patch(f"{MOD}.subprocess.run",
           side_effect=subprocess.TimeoutExpired(cmd="x", timeout=1))
    def test_handles_timeout(self, _mock_run, tmp_path):
        r = _run_python_compile_validation(
            repo_path=str(tmp_path), rel_path="x.py", timeout_s=1,
        )
        assert r["ran"] is True
        assert r["passed"] is False
        assert "timeout" in r["error"]

    @patch(f"{MOD}.subprocess.run", side_effect=OSError("boom"))
    def test_handles_process_error(self, _mock_run, tmp_path):
        r = _run_python_compile_validation(
            repo_path=str(tmp_path), rel_path="x.py", timeout_s=1,
        )
        assert r["ran"] is True
        assert r["passed"] is False
        assert "process error" in r["error"]

    @patch(f"{MOD}.subprocess.run")
    def test_uses_fixed_argv_no_shell(self, mock_run, tmp_path):
        mock_run.return_value = type(
            "P", (), {"returncode": 0, "stderr": "", "stdout": ""},
        )()
        _run_python_compile_validation(
            repo_path=str(tmp_path),
            rel_path="worker/tasks/foo.py",
            timeout_s=5,
        )
        assert mock_run.called
        args, kwargs = mock_run.call_args
        argv = args[0]
        assert isinstance(argv, list)
        assert argv[1:] == ["-m", "py_compile", "worker/tasks/foo.py"]
        assert kwargs.get("shell") in (None, False)
        assert kwargs["capture_output"] is True
        assert kwargs["cwd"] == str(tmp_path)


class TestRunContestantValidationDispatcher:
    """_run_contestant_validation should enforce applicability rules."""

    def test_none_mode_skips_everything(self):
        r = _run_contestant_validation(
            mode="none", code_change=None, target_file=None, timeout_s=10,
        )
        assert r["ran"] is False
        assert r["passed"] is None
        assert r["mode"] is None

    def test_python_compile_without_target_file(self):
        r = _run_contestant_validation(
            mode="python_compile",
            code_change={"written": True, "path": ".rick/contestants/t/a/x.py"},
            target_file=None, timeout_s=10,
        )
        assert r["ran"] is False
        assert "target_file" in r["error"]

    def test_python_compile_wrong_extension(self):
        r = _run_contestant_validation(
            mode="python_compile",
            code_change={"written": True, "path": "docs/notes.md"},
            target_file="docs/notes.md", timeout_s=10,
        )
        assert r["ran"] is False
        assert ".py" in r["error"]

    def test_python_compile_no_code_change(self):
        r = _run_contestant_validation(
            mode="python_compile",
            code_change=None,
            target_file="worker/tasks/x.py", timeout_s=10,
        )
        assert r["ran"] is False
        assert "no code change" in r["error"]

    def test_python_compile_code_change_not_written(self):
        r = _run_contestant_validation(
            mode="python_compile",
            code_change={"written": False, "parse_error": "bad"},
            target_file="worker/tasks/x.py", timeout_s=10,
        )
        assert r["ran"] is False

    @patch(f"{MOD}._run_python_compile_validation")
    def test_python_compile_invokes_runner(self, mock_runner):
        mock_runner.return_value = {
            "ran": True, "mode": "python_compile", "passed": True,
            "duration_ms": 50, "log_tail": "", "error": None,
        }
        r = _run_contestant_validation(
            mode="python_compile",
            code_change={"written": True},
            target_file="worker/tasks/x.py", timeout_s=10,
        )
        assert r["passed"] is True
        assert mock_runner.call_args.kwargs["rel_path"] == "worker/tasks/x.py"
        assert mock_runner.call_args.kwargs["timeout_s"] == 10

    def test_unknown_mode_returns_error_stub(self):
        r = _run_contestant_validation(
            mode="pytest_target", code_change=None,
            target_file=None, timeout_s=10,
        )
        assert r["ran"] is False
        assert "unsupported" in r["error"]


class TestOrchestrateValidationIntegration:
    """End-to-end wiring through handle_github_orchestrate_tournament."""

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_python_compile_runs_per_contestant(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, _code, mock_pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=3, winner_id=1)
        mock_pyc.return_value = {
            "ran": True, "mode": "python_compile", "passed": True,
            "duration_ms": 42, "log_tail": "", "error": None,
        }

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": "worker/tasks/example.py",
            "validation_mode": "python_compile",
        })

        assert result["ok"] is True
        assert mock_pyc.call_count == 3
        for c in result["contestants"]:
            assert c["validation"]["ran"] is True
            assert c["validation"]["passed"] is True
            assert c["validation"]["mode"] == "python_compile"
        assert result["meta"]["validation_mode"] == "python_compile"
        assert result["meta"]["validation_timeout_s"] == 20

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_default_mode_does_not_run_validation(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, _code, mock_pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": "worker/tasks/example.py",
            # no validation_mode
        })

        assert result["ok"] is True
        mock_pyc.assert_not_called()
        for c in result["contestants"]:
            assert c["validation"]["ran"] is False
            assert c["validation"]["mode"] is None
        assert result["meta"]["validation_mode"] == "none"

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_python_compile_without_target_file_marks_not_applicable(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, _code, mock_pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            # no target_file -> sandbox mode
            "validation_mode": "python_compile",
        })

        assert result["ok"] is True
        mock_pyc.assert_not_called()
        for c in result["contestants"]:
            assert c["validation"]["ran"] is False
            assert "target_file" in c["validation"]["error"]

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_failing_contestant_is_marked_not_disqualified(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, _code, mock_pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_pyc.side_effect = [
            {"ran": True, "mode": "python_compile", "passed": False,
             "duration_ms": 12, "log_tail": "SyntaxError: bad", "error": None},
            {"ran": True, "mode": "python_compile", "passed": True,
             "duration_ms": 8, "log_tail": "", "error": None},
        ]

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": "worker/tasks/example.py",
            "validation_mode": "python_compile",
        })

        assert result["ok"] is True
        assert result["contestants"][0]["validation"]["passed"] is False
        assert "SyntaxError" in result["contestants"][0]["validation"]["log_tail"]
        assert result["contestants"][1]["validation"]["passed"] is True
        # Winner selection is untouched — the judge already ran before
        # validation. The failing contestant is NOT disqualified.
        assert result["verdict"]["winner_id"] == 1
        assert result["final_result"] is not None

    @patch(f"{MOD}._generate_and_commit_code_change")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_invalid_validation_mode_aborts_early(
        self, _pre, mock_tourn, mock_br, mock_code,
    ):
        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "validation_mode": "pytest_target",
        })
        assert result["ok"] is False
        assert "invalid validation_mode" in result["error"]
        mock_br.assert_not_called()
        mock_tourn.assert_not_called()
        mock_code.assert_not_called()

    @patch(f"{MOD}._generate_and_commit_code_change")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_invalid_timeout_aborts_early(
        self, _pre, mock_tourn, mock_br, mock_code,
    ):
        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "validation_mode": "python_compile",
            "validation_timeout_s": -5,
        })
        assert result["ok"] is False
        assert "validation_timeout_s" in result["error"]
        mock_br.assert_not_called()
        mock_tourn.assert_not_called()

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_timeout_is_forwarded_to_runner(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, _code, mock_pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=1, winner_id=1)
        mock_pyc.return_value = {
            "ran": True, "mode": "python_compile", "passed": True,
            "duration_ms": 1, "log_tail": "", "error": None,
        }

        handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": "worker/tasks/example.py",
            "validation_mode": "python_compile",
            "validation_timeout_s": 7,
        })

        assert mock_pyc.call_args.kwargs["timeout_s"] == 7.0

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_timeout_is_capped(
        self, _pre, _br, mock_tourn, _chk, _art, _cp, _code, mock_pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=1, winner_id=1)
        mock_pyc.return_value = {
            "ran": True, "mode": "python_compile", "passed": True,
            "duration_ms": 1, "log_tail": "", "error": None,
        }
        handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": "worker/tasks/example.py",
            "validation_mode": "python_compile",
            "validation_timeout_s": 9999,
        })
        assert mock_pyc.call_args.kwargs["timeout_s"] == 60.0


# ---------------------------------------------------------------------------
# Phase 2 slice 6 — re-judge with validation evidence
# ---------------------------------------------------------------------------

def _rj_contestant(
    cid=1, name="Alpha", branch=None, proposal="Solid approach",
    code_written=True, code_path="worker/tasks/x.py",
    code_mode="target_file", code_commit_ok=True, code_parse_error=None,
    val_ran=True, val_passed=True, val_mode="python_compile",
    val_log="", val_err=None, val_duration=42,
):
    """Build a contestants[i]-shaped dict for rejudge tests."""
    return {
        "id": cid,
        "approach": name,
        "branch": branch or f"rick/t/tid/{chr(96 + cid)}",
        "proposal_excerpt": proposal,
        "artifact": {
            "path": f".rick/tournaments/tid/{chr(96 + cid)}.md",
            "written": True,
            "commit": {"ok": True, "commit_sha": "deadbeef", "branch": "x"},
        },
        "code_change": {
            "attempted": True,
            "mode": code_mode,
            "target_file": code_path if code_mode == "target_file" else None,
            "path": code_path,
            "written": code_written,
            "parse_error": code_parse_error,
            "commit": (
                {"ok": code_commit_ok, "commit_sha": "c0dec0de", "branch": "x"}
                if code_written else None
            ),
        },
        "validation": {
            "ran": val_ran,
            "mode": val_mode if val_ran else None,
            "passed": val_passed if val_ran else None,
            "duration_ms": val_duration if val_ran else None,
            "log_tail": val_log if val_ran else None,
            "error": val_err,
        },
    }


class TestSummarizeCodeChange:
    def test_none_is_handled(self):
        assert "no code change" in _summarize_code_change(None)

    def test_not_attempted(self):
        assert "no code change" in _summarize_code_change({"attempted": False})

    def test_happy_path_target_file(self):
        s = _summarize_code_change({
            "attempted": True, "written": True, "path": "worker/x.py",
            "mode": "target_file",
            "commit": {"ok": True, "commit_sha": "abc"},
        })
        assert "wrote" in s
        assert "worker/x.py" in s
        assert "target_file" in s

    def test_parse_error(self):
        s = _summarize_code_change({
            "attempted": True, "written": False,
            "parse_error": "no FILE block found", "mode": "target_file",
        })
        assert "FAILED" in s
        assert "no FILE block found" in s

    def test_write_failed(self):
        s = _summarize_code_change({
            "attempted": True, "written": False, "parse_error": None,
            "mode": "target_file",
        })
        assert "FAILED" in s
        assert "not written" in s

    def test_commit_failed(self):
        s = _summarize_code_change({
            "attempted": True, "written": True, "path": "worker/x.py",
            "mode": "target_file",
            "commit": {"ok": False, "error": "remote rejected"},
        })
        assert "commit FAILED" in s
        assert "remote rejected" in s


class TestSummarizeValidation:
    def test_none_is_not_run(self):
        assert _summarize_validation(None) == "not run"

    def test_not_run_with_reason(self):
        s = _summarize_validation({
            "ran": False, "error": "python_compile requires target_file",
        })
        assert "not run" in s
        assert "target_file" in s

    def test_passed(self):
        s = _summarize_validation({
            "ran": True, "mode": "python_compile", "passed": True,
            "duration_ms": 42, "log_tail": "", "error": None,
        })
        assert "PASSED" in s
        assert "42" in s

    def test_failed_with_log_tail(self):
        s = _summarize_validation({
            "ran": True, "mode": "python_compile", "passed": False,
            "duration_ms": 10, "log_tail": "SyntaxError: invalid syntax\n",
            "error": None,
        })
        assert "FAILED" in s
        assert "SyntaxError" in s

    def test_failed_with_timeout_error(self):
        s = _summarize_validation({
            "ran": True, "mode": "python_compile", "passed": False,
            "duration_ms": 20000, "log_tail": "", "error": "timeout after 20s",
        })
        assert "FAILED" in s
        assert "timeout" in s

    def test_failed_truncates_long_log(self):
        huge = "x" * 5000
        s = _summarize_validation({
            "ran": True, "mode": "python_compile", "passed": False,
            "duration_ms": 1, "log_tail": huge, "error": None,
        })
        # _REJUDGE_LOG_TAIL_EXCERPT = 200
        assert len(s) < 350


class TestBuildRejudgePrompt:
    def test_system_contains_final_line_contract(self):
        p = _build_rejudge_prompt(
            challenge="Do X",
            contestants=[_rj_contestant(cid=1), _rj_contestant(cid=2)],
        )
        assert "FINAL LINE CONTRACT" in p["system"]
        assert "Winner: Contestant #N" in p["system"]
        assert "ESCALATE" in p["system"]

    def test_system_includes_per_contestant_block(self):
        p = _build_rejudge_prompt(
            challenge="Do X",
            contestants=[
                _rj_contestant(cid=1, name="Alpha"),
                _rj_contestant(cid=2, name="Beta", val_passed=False,
                            val_log="SyntaxError: bad"),
            ],
        )
        sys = p["system"]
        assert "Contestant #1" in sys and "Alpha" in sys
        assert "Contestant #2" in sys and "Beta" in sys
        assert "PASSED" in sys
        assert "FAILED" in sys
        assert "SyntaxError" in sys

    def test_user_is_challenge(self):
        p = _build_rejudge_prompt(
            challenge="Fix the parser bug",
            contestants=[_rj_contestant()],
        )
        assert p["user"] == "Fix the parser bug"

    def test_prompt_truncates_long_proposals(self):
        long_prop = "x" * 5000
        p = _build_rejudge_prompt(
            challenge="c",
            contestants=[_rj_contestant(cid=1, proposal=long_prop)],
        )
        # _REJUDGE_PROPOSAL_EXCERPT = 800; truncation adds " [...]"
        assert "[...]" in p["system"]
        assert p["system"].count("x") < 900

    def test_bias_against_failures(self):
        p = _build_rejudge_prompt(
            challenge="c", contestants=[_rj_contestant()],
        )
        low = p["system"].lower()
        assert "passed" in low
        assert "avoid" in low or "fail" in low


class TestDetectOverrideAttempt:
    def test_returns_false_when_winner_passed(self):
        c = [
            _rj_contestant(cid=1, val_passed=True),
            _rj_contestant(cid=2, val_passed=False),
        ]
        assert _detect_override_attempt(c, 1) is False

    def test_returns_true_when_winner_failed_and_other_passed(self):
        c = [
            _rj_contestant(cid=1, val_passed=False, val_log="bad"),
            _rj_contestant(cid=2, val_passed=True),
        ]
        assert _detect_override_attempt(c, 1) is True

    def test_returns_false_when_all_failed(self):
        c = [
            _rj_contestant(cid=1, val_passed=False),
            _rj_contestant(cid=2, val_passed=False),
        ]
        assert _detect_override_attempt(c, 1) is False

    def test_returns_false_when_none_ran(self):
        c = [
            _rj_contestant(cid=1, val_ran=False, val_passed=None),
            _rj_contestant(cid=2, val_ran=False, val_passed=None),
        ]
        assert _detect_override_attempt(c, 1) is False

    def test_returns_false_when_winner_id_none(self):
        c = [_rj_contestant(cid=1, val_passed=False), _rj_contestant(cid=2)]
        assert _detect_override_attempt(c, None) is False

    def test_returns_false_when_winner_not_in_list(self):
        c = [_rj_contestant(cid=1, val_passed=True)]
        assert _detect_override_attempt(c, 99) is False

    def test_winner_passed_is_not_override_even_if_others_failed(self):
        c = [
            _rj_contestant(cid=1, val_passed=True),
            _rj_contestant(cid=2, val_passed=False),
            _rj_contestant(cid=3, val_passed=False),
        ]
        assert _detect_override_attempt(c, 1) is False


class TestRunRejudge:
    """Unit tests for _run_rejudge — all mock handle_llm_generate."""

    @patch(f"{MOD}.handle_llm_generate")
    def test_parses_clean_winner(self, mock_llm):
        mock_llm.return_value = {
            "text": (
                "Contestant #2 has strongest evidence: validation passed.\n"
                "Winner: Contestant #2"
            ),
            "model": "azure_foundry",
        }
        c = [_rj_contestant(cid=1), _rj_contestant(cid=2)]
        r = _run_rejudge(
            challenge="c", contestants=c,
            judge_model="azure_foundry", max_tokens=2048,
        )
        assert r["ran"] is True
        assert r["winner_id"] == 2
        assert r["escalate"] is False
        assert r["override_attempt"] is False
        assert r["error"] is None

    @patch(f"{MOD}.handle_llm_generate")
    def test_parses_escalate(self, mock_llm):
        mock_llm.return_value = {
            "text": "Too close. ESCALATE",
            "model": "azure_foundry",
        }
        r = _run_rejudge(
            challenge="c", contestants=[_rj_contestant()],
            judge_model="azure_foundry", max_tokens=2048,
        )
        assert r["escalate"] is True
        assert r["winner_id"] is None
        assert r["error"] is None

    @patch(f"{MOD}.handle_llm_generate")
    def test_marks_override_attempt(self, mock_llm):
        mock_llm.return_value = {
            "text": "Winner: Contestant #1",
            "model": "azure_foundry",
        }
        c = [
            _rj_contestant(cid=1, val_passed=False, val_log="SyntaxError"),
            _rj_contestant(cid=2, val_passed=True),
        ]
        r = _run_rejudge(
            challenge="c", contestants=c,
            judge_model="azure_foundry", max_tokens=2048,
        )
        assert r["winner_id"] == 1
        assert r["override_attempt"] is True

    @patch(f"{MOD}.handle_llm_generate")
    def test_captures_llm_exception(self, mock_llm):
        mock_llm.side_effect = RuntimeError("boom")
        r = _run_rejudge(
            challenge="c", contestants=[_rj_contestant()],
            judge_model="azure_foundry", max_tokens=2048,
        )
        assert r["ran"] is True
        assert r["winner_id"] is None
        assert r["escalate"] is False
        assert r["error"] is not None
        assert "llm error" in r["error"]

    @patch(f"{MOD}.handle_llm_generate")
    def test_handles_empty_response(self, mock_llm):
        mock_llm.return_value = {"text": "", "model": "azure_foundry"}
        r = _run_rejudge(
            challenge="c", contestants=[_rj_contestant()],
            judge_model="azure_foundry", max_tokens=2048,
        )
        assert r["ran"] is True
        assert r["winner_id"] is None
        assert "empty" in r["error"]

    def test_empty_contestants(self):
        r = _run_rejudge(
            challenge="c", contestants=[],
            judge_model="azure_foundry", max_tokens=2048,
        )
        assert r["ran"] is True
        assert r["winner_id"] is None
        assert "no contestants" in r["error"]

    @patch(f"{MOD}.handle_llm_generate")
    def test_records_duration(self, mock_llm):
        mock_llm.return_value = {
            "text": "Winner: Contestant #1", "model": "azure_foundry",
        }
        r = _run_rejudge(
            challenge="c", contestants=[_rj_contestant()],
            judge_model="azure_foundry", max_tokens=2048,
        )
        assert isinstance(r["duration_ms"], int)
        assert r["duration_ms"] >= 0

    @patch(f"{MOD}.handle_llm_generate")
    def test_forwards_model_from_llm(self, mock_llm):
        mock_llm.return_value = {
            "text": "Winner: Contestant #1", "model": "gpt-5.4",
        }
        r = _run_rejudge(
            challenge="c", contestants=[_rj_contestant()],
            judge_model="azure_foundry", max_tokens=2048,
        )
        assert r["model_used"] == "gpt-5.4"

    @patch(f"{MOD}.handle_llm_generate")
    def test_invalid_winner_id_is_rejected(self, mock_llm):
        mock_llm.return_value = {
            "text": "Winner: Contestant #99",
            "model": "azure_foundry",
        }
        c = [_rj_contestant(cid=1), _rj_contestant(cid=2)]
        r = _run_rejudge(
            challenge="c", contestants=c,
            judge_model="azure_foundry", max_tokens=2048,
        )
        # _extract_winner_id rejects ids not in the proposal set.
        assert r["winner_id"] is None
        assert r["escalate"] is False


class TestOrchestrateRejudgeIntegration:
    """End-to-end wiring through handle_github_orchestrate_tournament."""

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    @patch(f"{MOD}.handle_llm_generate")
    def test_rejudge_off_keeps_initial_verdict(
        self, mock_llm, _pre, _br, mock_tourn, _chk, _art, _cp, _code, _pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
        })

        assert result["ok"] is True
        mock_llm.assert_not_called()
        assert result["verdict"]["winner_id"] == 1
        assert result["verdict_initial"] is None
        assert result["rejudge"]["ran"] is False
        assert result["meta"]["rejudge"] is False

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    @patch(f"{MOD}.handle_llm_generate")
    def test_rejudge_can_override_initial_winner(
        self, mock_llm, _pre, _br, mock_tourn, _chk, _art, mock_cp, _cc, _pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_llm.return_value = {
            "text": (
                "Based on real evidence Contestant #2 delivered validation PASS.\n"
                "Winner: Contestant #2"
            ),
            "model": "azure_foundry",
        }

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "rejudge": True,
        })

        assert result["ok"] is True
        assert result["rejudge"]["ran"] is True
        assert result["rejudge"]["winner_id"] == 2
        assert result["verdict"]["winner_id"] == 2
        assert result["verdict_initial"] is not None
        assert result["verdict_initial"]["winner_id"] == 1
        # The cherry-pick must use contestant #2 (rejudge winner), not #1.
        assert mock_cp.call_count == 1

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    @patch(f"{MOD}.handle_llm_generate")
    def test_rejudge_failure_falls_back_to_initial(
        self, mock_llm, _pre, _br, mock_tourn, _chk, _art, _cp, _mcp, _pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_llm.side_effect = RuntimeError("llm offline")

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "rejudge": True,
        })

        assert result["ok"] is True
        assert result["rejudge"]["ran"] is True
        assert result["rejudge"]["error"] is not None
        assert result["rejudge"]["winner_id"] is None
        # Fallback to initial verdict for cherry-pick.
        assert result["verdict"]["winner_id"] == 1
        # And initial verdict is not duplicated in verdict_initial when the
        # rejudge errored — verdict_initial only surfaces when rejudge ran
        # cleanly and changed the answer.
        assert result["verdict_initial"] is None

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    @patch(f"{MOD}.handle_llm_generate")
    def test_rejudge_escalate_blocks_cherry_pick(
        self, mock_llm, _pre, _br, mock_tourn, _chk, _art, mock_cp, _cc, _pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_llm.return_value = {
            "text": "All failed validation. ESCALATE",
            "model": "azure_foundry",
        }

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "rejudge": True,
        })

        assert result["ok"] is True
        assert result["rejudge"]["escalate"] is True
        assert result["verdict"]["escalate"] is True
        assert result["verdict"]["winner_id"] is None
        # Cherry-pick MUST NOT run on escalate, even though the initial
        # verdict did pick a winner.
        mock_cp.assert_not_called()
        assert result["final_branch"] is None

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    @patch(f"{MOD}.handle_llm_generate")
    def test_rejudge_prompt_includes_validation_evidence(
        self, mock_llm, _pre, _br, mock_tourn, _chk, _art, _cp, _mcp, mock_pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        mock_pyc.side_effect = [
            {"ran": True, "mode": "python_compile", "passed": True,
             "duration_ms": 12, "log_tail": "", "error": None},
            {"ran": True, "mode": "python_compile", "passed": False,
             "duration_ms": 7, "log_tail": "SyntaxError: bad token",
             "error": None},
        ]
        mock_llm.return_value = {
            "text": "Winner: Contestant #1", "model": "azure_foundry",
        }

        handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": "worker/tasks/example.py",
            "validation_mode": "python_compile",
            "rejudge": True,
        })

        # The re-judge LLM call must have received a system prompt
        # containing both PASSED and FAILED evidence plus the syntax
        # error text, so the judge is actually seeing validation.
        assert mock_llm.called
        sent_system = mock_llm.call_args.args[0]["system"]
        assert "PASSED" in sent_system
        assert "FAILED" in sent_system
        assert "SyntaxError" in sent_system
        assert "Contestant #1" in sent_system
        assert "Contestant #2" in sent_system

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    @patch(f"{MOD}.handle_llm_generate")
    def test_meta_counts_rejudge_call(
        self, mock_llm, _pre, _br, mock_tourn, _chk, _art, _cp, _mcp, _pyc,
    ):
        base = _tournament_result(num=2, winner_id=1)
        base["meta"] = {"total_llm_calls": 5,
                        "total_duration_ms": 100,
                        "models_used": ["azure_foundry"]}
        mock_tourn.return_value = base
        mock_llm.return_value = {
            "text": "Winner: Contestant #1", "model": "azure_foundry",
        }

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "rejudge": True,
        })

        # base tourney did 5 calls, rejudge adds exactly 1.
        assert result["meta"]["total_llm_calls"] == 6
        assert result["meta"]["rejudge"] is True

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    @patch(f"{MOD}.handle_llm_generate")
    def test_rejudge_overrides_initial_escalate(
        self, mock_llm, _pre, _br, mock_tourn, _chk, _art, mock_cp, _cc, _pyc,
    ):
        mock_tourn.return_value = _tournament_result(
            num=2, winner_id=None, escalate=True,
        )
        mock_llm.return_value = {
            "text": (
                "Real evidence is decisive: Contestant #2 delivered a "
                "passing validation while #1 failed.\n"
                "Winner: Contestant #2"
            ),
            "model": "azure_foundry",
        }

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "rejudge": True,
        })

        assert result["ok"] is True
        # Initial was ESCALATE, rejudge picked a winner.
        assert result["verdict_initial"]["escalate"] is True
        assert result["verdict"]["escalate"] is False
        assert result["verdict"]["winner_id"] == 2
        # Cherry-pick must actually run, because rejudge rescued the
        # escalated decision.
        assert mock_cp.call_count == 1

    @patch(f"{MOD}._run_python_compile_validation")
    @patch(f"{MOD}._generate_and_commit_code_change",
           side_effect=_code_change_noop)
    @patch(f"{MOD}._cherry_pick_and_push", side_effect=_cherry_pick_noop)
    @patch(f"{MOD}._write_artifact_and_commit", side_effect=_artifact_noop)
    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    @patch(f"{MOD}.handle_llm_generate")
    def test_override_attempt_is_surfaced(
        self, mock_llm, _pre, _br, mock_tourn, _chk, _art, _cp, _mcp, mock_pyc,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)
        # Contestant 1 FAILS validation, contestant 2 PASSES.
        mock_pyc.side_effect = [
            {"ran": True, "mode": "python_compile", "passed": False,
             "duration_ms": 7, "log_tail": "SyntaxError", "error": None},
            {"ran": True, "mode": "python_compile", "passed": True,
             "duration_ms": 12, "log_tail": "", "error": None},
        ]
        # The re-judge ignores the bias and picks contestant #1 anyway.
        mock_llm.return_value = {
            "text": "Winner: Contestant #1", "model": "azure_foundry",
        }

        result = handle_github_orchestrate_tournament({
            "challenge": "c",
            "generate_code": True,
            "target_file": "worker/tasks/example.py",
            "validation_mode": "python_compile",
            "rejudge": True,
        })

        # The judge's decision is honoured, but the override_attempt
        # flag surfaces the suspicious pick.
        assert result["verdict"]["winner_id"] == 1
        assert result["rejudge"]["override_attempt"] is True
