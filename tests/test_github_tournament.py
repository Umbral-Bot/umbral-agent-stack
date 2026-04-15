"""Tests for github_tournament orchestration handler (Phase 1)."""

import re
from unittest.mock import patch

import pytest

from worker.tasks.github_tournament import (
    _branch_name,
    _final_branch_name,
    _generate_tournament_id,
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

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_basic_with_winner(self, _pre, mock_branch, mock_tourn, _chk):
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

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_escalate_no_final_branch(self, _pre, mock_branch, mock_tourn, _chk):
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

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_branch_failure_returns_partial(
        self, _pre, mock_branch, mock_tourn, _chk,
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

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_custom_base(self, _pre, mock_branch, mock_tourn, _chk):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1)

        result = handle_github_orchestrate_tournament(
            {"challenge": "test", "base": "develop"},
        )

        assert result["base"] == "develop"
        for call in mock_branch.call_args_list:
            assert call[0][0]["base"] == "develop"

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_predefined_approaches_forwarded(
        self, _pre, _br, mock_tourn, _chk,
    ):
        mock_tourn.return_value = _tournament_result(num=2)

        handle_github_orchestrate_tournament({
            "challenge": "test",
            "approaches": ["Class-based", "Functional"],
        })

        tourn_input = mock_tourn.call_args[0][0]
        assert tourn_input["approaches"] == ["Class-based", "Functional"]

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_meta_present(self, _pre, _br, mock_tourn, _chk):
        mock_tourn.return_value = _tournament_result(num=2)

        result = handle_github_orchestrate_tournament(
            {"challenge": "test"},
        )

        assert "meta" in result
        assert "total_llm_calls" in result["meta"]
        assert "total_duration_ms" in result["meta"]
        assert isinstance(result["meta"]["total_duration_ms"], int)
        assert result["meta"]["total_duration_ms"] >= 0

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_returns_to_base(self, _pre, _br, mock_tourn, mock_chk):
        mock_tourn.return_value = _tournament_result(num=2)

        handle_github_orchestrate_tournament({"challenge": "test"})

        mock_chk.assert_called_once_with("main")

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_returns_to_base_on_failure(self, _pre, mock_branch, mock_tourn, mock_chk):
        mock_tourn.return_value = _tournament_result(num=3)
        mock_branch.side_effect = [
            {"ok": True, "branch": "rick/t/x/a", "base": "main"},
            {"ok": False, "error": "fail"},
        ]

        handle_github_orchestrate_tournament({"challenge": "test"})

        mock_chk.assert_called_once_with("main")

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_proposal_excerpt_truncated(self, _pre, _br, mock_tourn, _chk):
        tr = _tournament_result(num=2)
        # make one proposal very long
        tr["approaches"][0]["proposal"] = "x" * 1000
        mock_tourn.return_value = tr

        result = handle_github_orchestrate_tournament(
            {"challenge": "test"},
        )

        assert len(result["contestants"][0]["proposal_excerpt"]) == 500

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_tournament_id_in_all_branches(self, _pre, _br, mock_tourn, _chk):
        mock_tourn.return_value = _tournament_result(num=3, winner_id=2)

        result = handle_github_orchestrate_tournament(
            {"challenge": "test"},
        )

        tid = result["tournament_id"]
        for branch in result["branches_created"]:
            assert f"rick/t/{tid}/" in branch

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch")
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_final_branch_failure_is_non_blocking(
        self, _pre, mock_branch, mock_tourn, mock_chk,
    ):
        mock_tourn.return_value = _tournament_result(num=2, winner_id=1, escalate=False)
        mock_branch.side_effect = [
            {"ok": True, "branch": "rick/t/x/a", "base": "main"},
            {"ok": True, "branch": "rick/t/x/b", "base": "main"},
            {"ok": False, "error": "remote rejected"},
        ]

        result = handle_github_orchestrate_tournament({"challenge": "test"})

        assert result["ok"] is True
        assert result["verdict"]["winner_id"] == 1
        assert result["final_branch"] is None
        assert len(result["branches_created"]) == 2
        assert mock_branch.call_count == 3
        mock_chk.assert_called_once_with("main")

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_missing_approach_fields_use_fallbacks(
        self, _pre, _br, mock_tourn, _chk,
    ):
        tr = _tournament_result(num=2, winner_id=1)
        tr["approaches"] = [
            {},
            {"approach_name": "Named approach only"},
        ]
        mock_tourn.return_value = tr

        result = handle_github_orchestrate_tournament({"challenge": "test"})

        first = result["contestants"][0]
        second = result["contestants"][1]
        assert first["id"] == 1
        assert first["approach"] == "Approach A"
        assert first["proposal_excerpt"] == ""
        assert first["branch"].endswith("/a")
        assert second["id"] == 2
        assert second["approach"] == "Named approach only"
        assert second["proposal_excerpt"] == ""
        assert second["branch"].endswith("/b")

    @patch(f"{MOD}._checkout_base")
    @patch(f"{MOD}.handle_tournament_run")
    @patch(f"{MOD}.handle_github_create_branch", side_effect=_create_branch_ok)
    @patch(f"{MOD}.handle_github_preflight", return_value=_preflight_ok())
    def test_more_than_five_approaches_use_numeric_labels(
        self, _pre, _br, mock_tourn, _chk,
    ):
        mock_tourn.return_value = _tournament_result(num=6, escalate=True)

        result = handle_github_orchestrate_tournament({"challenge": "test"})

        labels = [c["branch"].split("/")[-1] for c in result["contestants"]]
        assert labels[:5] == ["a", "b", "c", "d", "e"]
        assert labels[5] == "5"
        assert len(set(result["branches_created"])) == len(result["branches_created"])
