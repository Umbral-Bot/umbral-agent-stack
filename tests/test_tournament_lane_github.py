"""Tests for tournament lane GitHub Worker tasks."""

import json
import subprocess
from unittest.mock import patch

from worker.tasks.tournament_lane_github import (
    _validate_lane_branch,
    handle_tournament_lane_commit_and_push,
    handle_tournament_lane_create_branch,
    handle_tournament_lane_open_pr,
    handle_tournament_lane_preflight,
    handle_tournament_lane_verify_pr,
)


MOD = "worker.tasks.tournament_lane_github"


def _completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class TestLaneBranchValidation:
    def test_accepts_tournament_lane_branch(self):
        branch, tid, specialty = _validate_lane_branch("tournament/d36/lane-qa")

        assert branch == "tournament/d36/lane-qa"
        assert tid == "d36"
        assert specialty == "qa"

    def test_rejects_rick_branch(self):
        try:
            _validate_lane_branch("rick/test")
        except ValueError as exc:
            assert "tournament/<tournament_id>/lane-<specialty>" in str(exc)
        else:
            raise AssertionError("Expected ValueError")

    def test_rejects_slash_in_specialty(self):
        try:
            _validate_lane_branch("tournament/d36/lane-qa/extra")
        except ValueError as exc:
            assert "Branch must match" in str(exc)
        else:
            raise AssertionError("Expected ValueError")


class TestTournamentLanePreflight:
    def test_success_checks_main_ff_only_and_gh_auth(self):
        calls = []
        branches = iter(["feature/work", "main"])

        def fake_run(args, **kwargs):
            calls.append(args)
            if args[:3] == ["git", "rev-parse", "--abbrev-ref"]:
                return _completed(stdout=f"{next(branches)}\n")
            if args == ["git", "status", "--porcelain"]:
                return _completed(stdout="")
            if args == ["gh", "auth", "status"]:
                return _completed(stderr="Logged in to github.com account UmbralBIM")
            return _completed()

        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(f"{MOD}._run", side_effect=fake_run):
            result = handle_tournament_lane_preflight({})

        assert result["ok"] is True
        assert result["initial_branch"] == "feature/work"
        assert result["branch"] == "main"
        assert result["gh_authenticated"] is True
        assert result["gh_account"] == "UmbralBIM"
        assert ["git", "fetch", "origin", "main"] in calls
        assert ["git", "checkout", "main"] in calls
        assert ["git", "pull", "--ff-only", "origin", "main"] in calls

    def test_dirty_worktree_blocks(self):
        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(f"{MOD}._current_branch", return_value="main"), \
             patch(f"{MOD}._status_porcelain", return_value="?? scratch.md"):
            result = handle_tournament_lane_preflight({})

        assert result["ok"] is False
        assert "uncommitted or untracked" in result["error"]

    def test_non_main_base_rejected(self):
        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"):
            result = handle_tournament_lane_preflight({"base": "develop"})

        assert result["ok"] is False
        assert "must target base branch 'main'" in result["error"]


class TestTournamentLaneCreateBranch:
    def test_success_creates_expected_branch_from_origin_main(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)
            if args[:4] == ["git", "show-ref", "--verify", "--quiet"]:
                return _completed(returncode=1)
            if args[:3] == ["git", "ls-remote", "--exit-code"]:
                return _completed(returncode=2)
            return _completed()

        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(f"{MOD}._status_porcelain", return_value=""), \
             patch(f"{MOD}._run", side_effect=fake_run):
            result = handle_tournament_lane_create_branch({
                "tournament_id": "d36",
                "specialty": "qa",
            })

        assert result["ok"] is True
        assert result["branch"] == "tournament/d36/lane-qa"
        assert [
            "git",
            "checkout",
            "-b",
            "tournament/d36/lane-qa",
            "origin/main",
        ] in calls

    def test_remote_branch_exists_blocks(self):
        def fake_run(args, **kwargs):
            if args[:4] == ["git", "show-ref", "--verify", "--quiet"]:
                return _completed(returncode=1)
            if args[:3] == ["git", "ls-remote", "--exit-code"]:
                return _completed(stdout="abc\trefs/heads/tournament/d36/lane-qa\n")
            return _completed()

        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(f"{MOD}._status_porcelain", return_value=""), \
             patch(f"{MOD}._run", side_effect=fake_run):
            result = handle_tournament_lane_create_branch({
                "branch_name": "tournament/d36/lane-qa",
            })

        assert result["ok"] is False
        assert "Remote branch already exists" in result["error"]

    def test_rejects_branch_outside_tournament_prefix(self):
        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"):
            result = handle_tournament_lane_create_branch({"branch_name": "rick/test"})

        assert result["ok"] is False
        assert "tournament/<tournament_id>/lane-<specialty>" in result["error"]


class TestTournamentLaneCommitAndPush:
    def test_requires_explicit_files(self, tmp_path):
        with patch(f"{MOD}._resolve_repo_path", return_value=str(tmp_path)), \
             patch(
                 f"{MOD}._current_branch",
                 return_value="tournament/d36/lane-qa",
             ):
            result = handle_tournament_lane_commit_and_push({
                "tournament_id": "d36",
                "specialty": "qa",
                "message": "test",
            })

        assert result["ok"] is False
        assert "explicit staging" in result["error"]

    def test_rejects_current_branch_mismatch(self, tmp_path):
        with patch(f"{MOD}._resolve_repo_path", return_value=str(tmp_path)), \
             patch(f"{MOD}._current_branch", return_value="main"):
            result = handle_tournament_lane_commit_and_push({
                "tournament_id": "d36",
                "specialty": "qa",
                "message": "test",
                "files": ["worker/a.py"],
            })

        assert result["ok"] is False
        assert "Branch mismatch" in result["error"]

    def test_rejects_path_escape(self, tmp_path):
        with patch(f"{MOD}._resolve_repo_path", return_value=str(tmp_path)), \
             patch(
                 f"{MOD}._current_branch",
                 return_value="tournament/d36/lane-qa",
             ):
            result = handle_tournament_lane_commit_and_push({
                "tournament_id": "d36",
                "specialty": "qa",
                "message": "test",
                "files": ["../outside.py"],
            })

        assert result["ok"] is False
        assert "escapes repo boundary" in result["error"]

    def test_success_stages_only_explicit_files_and_pushes_branch(self, tmp_path):
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)
            if args == ["git", "diff", "--cached", "--name-only"]:
                if calls.count(args) == 1:
                    return _completed(stdout="")
                return _completed(stdout="worker/a.py\n")
            if args == ["git", "rev-parse", "HEAD"]:
                return _completed(stdout="abc123\n")
            return _completed()

        with patch(f"{MOD}._resolve_repo_path", return_value=str(tmp_path)), \
             patch(
                 f"{MOD}._current_branch",
                 return_value="tournament/d36/lane-qa",
             ), \
             patch(f"{MOD}._run", side_effect=fake_run):
            result = handle_tournament_lane_commit_and_push({
                "tournament_id": "d36",
                "specialty": "qa",
                "message": "feat: lane work",
                "files": ["worker/a.py"],
            })

        assert result["ok"] is True
        assert result["commit_sha"] == "abc123"
        assert ["git", "add", "--", "worker/a.py"] in calls
        assert ["git", "push", "-u", "origin", "tournament/d36/lane-qa"] in calls
        assert ["git", "add", "-A"] not in calls


class TestTournamentLaneOpenPr:
    def test_builds_prefixed_title_from_issue_title_and_returns_pr_url(self):
        captured = {}

        def fake_run(args, **kwargs):
            captured["args"] = args
            return _completed(
                stdout="https://github.com/Umbral-Bot/umbral-agent-stack/pull/501\n"
            )

        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(
                 f"{MOD}._current_branch",
                 return_value="tournament/d36/lane-qa",
             ), \
             patch(f"{MOD}._run", side_effect=fake_run):
            result = handle_tournament_lane_open_pr({
                "tournament_id": "d36",
                "specialty": "qa",
                "issue_title": "fix tournament PR gate",
                "tests": "pytest tests/test_tournament_lane_github.py -q",
            })

        assert result["ok"] is True
        assert result["pr_number"] == 501
        assert result["pr_url"].endswith("/pull/501")
        assert captured["args"][captured["args"].index("--title") + 1] == (
            "[tournament:d36:qa] fix tournament PR gate"
        )
        body = captured["args"][captured["args"].index("--body") + 1]
        assert "I did not merge this PR" in body

    def test_rejects_title_without_required_prefix(self):
        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"):
            result = handle_tournament_lane_open_pr({
                "tournament_id": "d36",
                "specialty": "qa",
                "title": "plain title",
            })

        assert result["ok"] is False
        assert "PR title must start" in result["error"]


class TestTournamentLaneVerifyPr:
    def test_success_returns_collect_ready_json(self):
        payload = {
            "url": "https://github.com/Umbral-Bot/umbral-agent-stack/pull/501",
            "number": 501,
            "headRefName": "tournament/d36/lane-qa",
            "baseRefName": "main",
            "title": "[tournament:d36:qa] fix tournament PR gate",
            "mergeable": "MERGEABLE",
            "statusCheckRollup": [
                {"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"},
                {"name": "ci", "status": "QUEUED", "conclusion": None},
            ],
            "additions": 10,
            "deletions": 2,
            "state": "OPEN",
            "isDraft": False,
        }

        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(f"{MOD}._run", return_value=_completed(stdout=json.dumps(payload))):
            result = handle_tournament_lane_verify_pr({
                "tournament_id": "d36",
                "specialty": "qa",
                "pr_url": payload["url"],
            })

        assert result["ok"] is True
        assert result["pr_url"] == payload["url"]
        assert result["head_ref"] == "tournament/d36/lane-qa"
        assert result["checks"]["status"] == "pending"
        assert result["additions"] == 10
        assert result["deletions"] == 2

    def test_head_ref_mismatch_fails(self):
        payload = {
            "url": "https://github.com/Umbral-Bot/umbral-agent-stack/pull/501",
            "number": 501,
            "headRefName": "feature/not-a-lane",
            "baseRefName": "main",
            "title": "[tournament:d36:qa] fix tournament PR gate",
            "statusCheckRollup": [],
        }

        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(f"{MOD}._run", return_value=_completed(stdout=json.dumps(payload))):
            result = handle_tournament_lane_verify_pr({
                "tournament_id": "d36",
                "specialty": "qa",
                "pr_url": payload["url"],
            })

        assert result["ok"] is False
        assert "headRefName mismatch" in result["error"]


def test_worker_registry_exposes_tournament_lane_tasks():
    from worker.tasks import TASK_HANDLERS

    for task in [
        "tournament_lane.preflight",
        "tournament_lane.create_branch",
        "tournament_lane.commit_and_push",
        "tournament_lane.open_pr",
        "tournament_lane.verify_pr",
    ]:
        assert task in TASK_HANDLERS
