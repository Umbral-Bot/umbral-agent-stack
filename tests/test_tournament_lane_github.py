"""Tests for tournament lane GitHub Worker tasks."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.tournament_lane_github import (
    _parse_worktree_output,
    _validate_lane_branch,
    handle_tournament_lane_commit_and_push,
    handle_tournament_lane_create_branch,
    handle_tournament_lane_open_pr,
    handle_tournament_lane_preflight,
    handle_tournament_lane_verify_pr,
)


MOD = "worker.tasks.tournament_lane_github"

_BASH = shutil.which("bash")
_GIT = shutil.which("git")
_WORKTREE_HELPER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "openclaw"
    / "tournament-lane-worktree.sh"
)


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


class TestParseWorktreeOutput:
    def test_parses_known_keys_and_ignores_noise(self):
        stdout = (
            "Preparing worktree (new branch ...)\n"
            "WORKTREE_PATH=/wt/d36/lane-qa\n"
            "BRANCH=tournament/d36/lane-qa\n"
            "WORKTREE_VERDICT=CREATED\n"
            "unrelated=line\n"
        )
        parsed = _parse_worktree_output(stdout)
        assert parsed["WORKTREE_PATH"] == "/wt/d36/lane-qa"
        assert parsed["WORKTREE_VERDICT"] == "CREATED"
        assert "unrelated" not in parsed


class TestTournamentLaneCreateBranchWorktree:
    def test_use_worktree_delegates_to_helper_and_skips_checkout(self):
        calls = []
        helper = MagicMock()
        helper.is_file.return_value = True

        def fake_run(args, **kwargs):
            calls.append(args)
            return _completed(
                stdout=(
                    "WORKTREE_PATH=/wt/d36/lane-qa\n"
                    "BRANCH=tournament/d36/lane-qa\n"
                    "WORKTREE_VERDICT=CREATED\n"
                )
            )

        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(f"{MOD}._status_porcelain", return_value=""), \
             patch(f"{MOD}._worktree_helper_path", return_value=helper), \
             patch(f"{MOD}._run", side_effect=fake_run):
            result = handle_tournament_lane_create_branch({
                "tournament_id": "d36",
                "specialty": "qa",
                "use_worktree": True,
            })

        assert result["ok"] is True
        assert result["use_worktree"] is True
        assert result["worktree_path"] == "/wt/d36/lane-qa"
        assert result["worktree_verdict"] == "CREATED"
        assert result["branch"] == "tournament/d36/lane-qa"
        # Helper was invoked with the create action...
        assert any(a[:2] == ["bash", str(helper)] and "create" in a for a in calls)
        # ...and the shared-checkout path was never taken.
        assert all(a[:2] != ["git", "checkout"] for a in calls)

    def test_use_worktree_accepts_string_flag(self):
        helper = MagicMock()
        helper.is_file.return_value = True

        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(f"{MOD}._status_porcelain", return_value=""), \
             patch(f"{MOD}._worktree_helper_path", return_value=helper), \
             patch(
                 f"{MOD}._run",
                 return_value=_completed(
                     stdout="WORKTREE_PATH=/wt/d36/lane-qa\nWORKTREE_VERDICT=EXISTS\n"
                 ),
             ):
            result = handle_tournament_lane_create_branch({
                "tournament_id": "d36",
                "specialty": "qa",
                "use_worktree": "true",
            })

        assert result["ok"] is True
        assert result["worktree_verdict"] == "EXISTS"

    def test_use_worktree_missing_helper_errors(self):
        helper = MagicMock()
        helper.is_file.return_value = False

        with patch(f"{MOD}._resolve_repo_path", return_value="/tmp/repo"), \
             patch(f"{MOD}._status_porcelain", return_value=""), \
             patch(f"{MOD}._worktree_helper_path", return_value=helper):
            result = handle_tournament_lane_create_branch({
                "tournament_id": "d36",
                "specialty": "qa",
                "use_worktree": True,
            })

        assert result["ok"] is False
        assert "worktree helper not found" in result["error"]

    def test_default_path_reports_no_worktree(self):
        def fake_run(args, **kwargs):
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
        assert result["use_worktree"] is False
        assert result["worktree_path"] is None


@pytest.mark.skipif(
    not _BASH or not _GIT or not _WORKTREE_HELPER.is_file(),
    reason="requires bash, git, and the worktree helper script",
)
class TestWorktreeHelperScript:
    def _init_repo(self, repo: Path):
        def git(*args):
            subprocess.run(
                [_GIT, *args],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )

        git("init", "-q")
        git("config", "user.email", "lane@test.local")
        git("config", "user.name", "lane")
        git("commit", "-q", "--allow-empty", "-m", "init")
        git("branch", "-M", "main")

    def _run_helper(self, repo: Path, wt_root: Path, action: str):
        env = dict(os.environ, TOURNAMENT_WORKTREE_ROOT=str(wt_root).replace("\\", "/"))
        return subprocess.run(
            [
                _BASH,
                str(_WORKTREE_HELPER).replace("\\", "/"),
                action,
                str(repo).replace("\\", "/"),
                "tourz",
                "qa",
                "main",
            ],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
        )

    def _branch_exists(self, repo: Path) -> bool:
        return subprocess.run(
            [_GIT, "show-ref", "--verify", "--quiet", "refs/heads/tournament/tourz/lane-qa"],
            cwd=repo,
            capture_output=True,
            text=True,
        ).returncode == 0

    def test_create_remove_idempotent_keeps_branch(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        wt_root = tmp_path / "wt"
        self._init_repo(repo)
        expected = wt_root / "tourz" / "lane-qa"

        created = self._run_helper(repo, wt_root, "create")
        assert created.returncode == 0, created.stderr
        assert "WORKTREE_VERDICT=CREATED" in created.stdout
        assert expected.is_dir()
        assert self._branch_exists(repo)

        again = self._run_helper(repo, wt_root, "create")
        assert again.returncode == 0, again.stderr
        assert "WORKTREE_VERDICT=EXISTS" in again.stdout

        removed = self._run_helper(repo, wt_root, "remove")
        assert removed.returncode == 0, removed.stderr
        assert "WORKTREE_VERDICT=REMOVED" in removed.stdout
        assert not expected.exists()
        # keep-losers: branch must survive worktree removal
        assert self._branch_exists(repo)

        absent = self._run_helper(repo, wt_root, "remove")
        assert absent.returncode == 0, absent.stderr
        assert "WORKTREE_VERDICT=ABSENT" in absent.stdout

    def test_rejects_invalid_specialty(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        self._init_repo(repo)
        env = dict(os.environ, TOURNAMENT_WORKTREE_ROOT=str(tmp_path / "wt"))
        result = subprocess.run(
            [
                _BASH,
                str(_WORKTREE_HELPER).replace("\\", "/"),
                "create",
                str(repo).replace("\\", "/"),
                "tourz",
                "bad/specialty",
            ],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "invalid specialty" in result.stderr
