"""Tests for github_tournament orchestration handler.

Covers:
- Phase 1: branch-based orchestration primitives.
- Phase 2 slice 1: contestant proposal artifact committed per branch.
- Phase 2 slice 2: final branch materialized via cherry-pick + push.
"""

import re
from unittest.mock import patch

import pytest

from worker.tasks.github_tournament import (
    _artifact_rel_path,
    _branch_name,
    _build_artifact_body,
    _cherry_pick_and_push,
    _final_branch_name,
    _generate_tournament_id,
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
