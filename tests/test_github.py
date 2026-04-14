"""Tests for GitHub task handlers."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# github.preflight
# ---------------------------------------------------------------------------


class TestGitHubPreflight:
    def test_invalid_repo_path(self):
        from worker.tasks.github import handle_github_preflight

        r = handle_github_preflight({"repo_path": "/nonexistent/path"})
        assert r["ok"] is False
        assert "repo_path" in r["error"]

    def test_success(self):
        from worker.tasks.github import handle_github_preflight

        def side_effect(args, **kwargs):
            m = _make_completed()
            if "status" in args and "--porcelain" in args:
                m = _make_completed(stdout="")
            elif "rev-parse" in args:
                m = _make_completed(stdout="rick/test\n")
            elif "ssh" in args:
                m = _make_completed(stderr="successfully authenticated", returncode=1)
            elif "fetch" in args and "--dry-run" in args:
                m = _make_completed()
            elif "gh" in args:
                m = _make_completed(stderr="Logged in to github.com account UmbralBIM")
            return m

        with patch("worker.tasks.github._git", side_effect=side_effect), \
             patch("worker.tasks.github._github_token", return_value="ghp_fake"), \
             patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"):
            r = handle_github_preflight({})
        assert r["ok"] is True
        assert r["ssh"] is True
        assert r["token"] is True
        assert r["remote_reachable"] is True

    def test_fetch_failure_is_blocking(self):
        from worker.tasks.github import handle_github_preflight

        call_count = {"n": 0}

        def side_effect(args, **kwargs):
            call_count["n"] += 1
            if "status" in args and "--porcelain" in args:
                return _make_completed(stdout="")
            elif "rev-parse" in args:
                return _make_completed(stdout="main\n")
            elif "ssh" in args:
                return _make_completed(stderr="successfully authenticated", returncode=1)
            elif "fetch" in args and "--dry-run" in args:
                raise RuntimeError("Network unreachable")
            elif "gh" in args:
                return _make_completed(stderr="Logged in to github.com account UmbralBIM")
            return _make_completed()

        with patch("worker.tasks.github._git", side_effect=side_effect), \
             patch("worker.tasks.github._github_token", return_value="ghp_fake"), \
             patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"):
            r = handle_github_preflight({})
        assert r["ok"] is False
        assert r["remote_reachable"] is False

    def test_missing_token(self):
        from worker.tasks.github import handle_github_preflight

        def side_effect(args, **kwargs):
            if "status" in args and "--porcelain" in args:
                return _make_completed(stdout="")
            elif "rev-parse" in args:
                return _make_completed(stdout="main\n")
            elif "ssh" in args:
                return _make_completed(stderr="successfully authenticated", returncode=1)
            elif "fetch" in args:
                return _make_completed()
            return _make_completed()

        with patch("worker.tasks.github._git", side_effect=side_effect), \
             patch("worker.tasks.github._github_token", return_value=None), \
             patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"):
            r = handle_github_preflight({})
        assert r["ok"] is False
        assert r["token"] is False


# ---------------------------------------------------------------------------
# github.create_branch
# ---------------------------------------------------------------------------


class TestGitHubCreateBranch:
    def test_requires_branch_name(self):
        from worker.tasks.github import handle_github_create_branch

        with patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"):
            r = handle_github_create_branch({})
        assert r["ok"] is False
        assert "branch_name" in r["error"]

    def test_rejects_main(self):
        from worker.tasks.github import handle_github_create_branch

        with patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"):
            r = handle_github_create_branch({"branch_name": "main"})
        assert r["ok"] is False
        assert "protected" in r["error"].lower()

    def test_rejects_no_prefix(self):
        from worker.tasks.github import handle_github_create_branch

        with patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"):
            r = handle_github_create_branch({"branch_name": "feature/foo"})
        assert r["ok"] is False
        assert "rick/" in r["error"]

    def test_dirty_worktree_rejected(self):
        from worker.tasks.github import handle_github_create_branch

        def side_effect(args, **kwargs):
            if "status" in args and "--porcelain" in args:
                return _make_completed(stdout="M dirty.py\n")
            return _make_completed()

        with patch("worker.tasks.github._git", side_effect=side_effect), \
             patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"):
            r = handle_github_create_branch({"branch_name": "rick/test"})
        assert r["ok"] is False
        assert "uncommitted" in r["error"].lower()

    def test_success(self):
        from worker.tasks.github import handle_github_create_branch

        def side_effect(args, **kwargs):
            if "status" in args:
                return _make_completed(stdout="")
            return _make_completed()

        with patch("worker.tasks.github._git", side_effect=side_effect) as mock_git, \
             patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"):
            r = handle_github_create_branch({"branch_name": "rick/test-feature", "base": "main"})
        assert r["ok"] is True
        assert r["branch"] == "rick/test-feature"
        assert r["base"] == "main"
        # Verify fetch + checkout were called
        calls = [str(c) for c in mock_git.call_args_list]
        assert any("fetch" in c for c in calls)
        assert any("checkout" in c for c in calls)


# ---------------------------------------------------------------------------
# github.commit_and_push
# ---------------------------------------------------------------------------


class TestGitHubCommitAndPush:
    def test_requires_message(self):
        from worker.tasks.github import handle_github_commit_and_push

        r = handle_github_commit_and_push({})
        assert r["ok"] is False
        assert "message" in r["error"].lower()

    def test_requires_files_list(self):
        from worker.tasks.github import handle_github_commit_and_push

        r = handle_github_commit_and_push({"message": "test"})
        assert r["ok"] is False
        assert "files" in r["error"].lower()
        assert "explicit" in r["error"].lower()

    def test_rejects_empty_files(self):
        from worker.tasks.github import handle_github_commit_and_push

        r = handle_github_commit_and_push({"message": "test", "files": []})
        assert r["ok"] is False

    def test_rejects_main_branch(self):
        from worker.tasks.github import handle_github_commit_and_push

        with patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"), \
             patch("worker.tasks.github._current_branch", return_value="main"):
            r = handle_github_commit_and_push({"message": "test", "files": ["a.py"]})
        assert r["ok"] is False
        assert "protected" in r["error"].lower()

    def test_branch_mismatch(self):
        from worker.tasks.github import handle_github_commit_and_push

        with patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"), \
             patch("worker.tasks.github._current_branch", return_value="rick/other"):
            r = handle_github_commit_and_push({
                "message": "test",
                "files": ["a.py"],
                "branch_name": "rick/expected",
            })
        assert r["ok"] is False
        assert "mismatch" in r["error"].lower()

    def test_path_escape_rejected(self):
        from worker.tasks.github import handle_github_commit_and_push

        with patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"), \
             patch("worker.tasks.github._current_branch", return_value="rick/test"):
            r = handle_github_commit_and_push({
                "message": "test",
                "files": ["../../etc/passwd"],
            })
        assert r["ok"] is False
        assert "escape" in r["error"].lower()

    def test_success(self):
        from worker.tasks.github import handle_github_commit_and_push

        def side_effect(args, **kwargs):
            if "diff" in args and "--cached" in args:
                return _make_completed(stdout=" file1.py | 5 +++++\n 1 file changed\n")
            elif "rev-parse" in args and "HEAD" in args:
                return _make_completed(stdout="abc1234def5678\n")
            elif "diff" in args and "--stat" in args:
                return _make_completed(stdout=" file1.py | 5 +++++\n 1 file changed\n")
            return _make_completed()

        with patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"), \
             patch("worker.tasks.github._current_branch", return_value="rick/test"), \
             patch("worker.tasks.github._git", side_effect=side_effect):
            r = handle_github_commit_and_push({
                "message": "feat: add feature",
                "files": ["file1.py"],
            })
        assert r["ok"] is True
        assert r["branch"] == "rick/test"
        assert r["commit_sha"] == "abc1234def5678"
        assert r["pushed"] is True
        assert r["files"] == ["file1.py"]

    def test_handles_deletions(self):
        """git add -- <path> works for deleted files even though they don't exist on disk."""
        from worker.tasks.github import handle_github_commit_and_push

        def side_effect(args, **kwargs):
            if "diff" in args and "--cached" in args:
                return _make_completed(stdout=" old.py | 10 ----------\n 1 file changed\n")
            elif "rev-parse" in args:
                return _make_completed(stdout="def456\n")
            elif "diff" in args and "--stat" in args:
                return _make_completed(stdout=" old.py | 10 ----------\n 1 file changed\n")
            return _make_completed()

        with patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"), \
             patch("worker.tasks.github._current_branch", return_value="rick/cleanup"), \
             patch("worker.tasks.github._git", side_effect=side_effect):
            r = handle_github_commit_and_push({
                "message": "chore: remove old file",
                "files": ["old.py"],
            })
        assert r["ok"] is True
        assert r["files"] == ["old.py"]


# ---------------------------------------------------------------------------
# github.open_pr
# ---------------------------------------------------------------------------


class TestGitHubOpenPr:
    def test_requires_title(self):
        from worker.tasks.github import handle_github_open_pr

        r = handle_github_open_pr({})
        assert r["ok"] is False
        assert "title" in r["error"]

    def test_missing_token(self):
        from worker.tasks.github import handle_github_open_pr

        with patch("worker.tasks.github._github_token", return_value=None):
            r = handle_github_open_pr({"title": "test"})
        assert r["ok"] is False
        assert "GITHUB_TOKEN" in r["error"]

    def test_rejects_protected_branch(self):
        from worker.tasks.github import handle_github_open_pr

        with patch("worker.tasks.github._github_token", return_value="ghp_fake"), \
             patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"), \
             patch("worker.tasks.github._current_branch", return_value="main"):
            r = handle_github_open_pr({"title": "test"})
        assert r["ok"] is False
        assert "protected" in r["error"].lower()

    def test_success_with_pr_url(self):
        from worker.tasks.github import handle_github_open_pr

        def side_effect(args, **kwargs):
            if "gh" in args and "pr" in args:
                return _make_completed(
                    stdout="https://github.com/Umbral-Bot/umbral-agent-stack/pull/42\n"
                )
            return _make_completed()

        with patch("worker.tasks.github._github_token", return_value="ghp_fake"), \
             patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"), \
             patch("worker.tasks.github._current_branch", return_value="rick/test"), \
             patch("worker.tasks.github._git", side_effect=side_effect):
            r = handle_github_open_pr({"title": "Add GitHub handlers", "body": "MVP"})
        assert r["ok"] is True
        assert r["pr_url"] == "https://github.com/Umbral-Bot/umbral-agent-stack/pull/42"
        assert r["pr_number"] == 42
        assert r["branch"] == "rick/test"

    def test_traceability_notion_bridge(self):
        from worker.tasks.github import handle_github_open_pr

        def side_effect(args, **kwargs):
            if "gh" in args:
                return _make_completed(
                    stdout="https://github.com/Umbral-Bot/umbral-agent-stack/pull/99\n"
                )
            return _make_completed()

        mock_bridge = MagicMock(return_value={"ok": True, "page_id": "pg-1", "url": "https://notion.so/pg-1"})

        with patch("worker.tasks.github._github_token", return_value="ghp_fake"), \
             patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"), \
             patch("worker.tasks.github._current_branch", return_value="rick/test"), \
             patch("worker.tasks.github._git", side_effect=side_effect), \
             patch("worker.tasks.notion.handle_notion_upsert_bridge_item", mock_bridge):
            r = handle_github_open_pr({
                "title": "Feature X",
                "bridge_item_name": "PR: Feature X",
            })
        assert r["ok"] is True
        assert r["traceability"]["notion"]["ok"] is True
        mock_bridge.assert_called_once()
        call_input = mock_bridge.call_args[0][0]
        assert call_input["link"] == "https://github.com/Umbral-Bot/umbral-agent-stack/pull/99"

    def test_traceability_linear_comment(self):
        from worker.tasks.github import handle_github_open_pr

        def side_effect(args, **kwargs):
            if "gh" in args:
                return _make_completed(
                    stdout="https://github.com/Umbral-Bot/umbral-agent-stack/pull/77\n"
                )
            return _make_completed()

        mock_linear = MagicMock(return_value={"ok": True})

        with patch("worker.tasks.github._github_token", return_value="ghp_fake"), \
             patch("worker.tasks.github._resolve_repo_path", return_value="/tmp/repo"), \
             patch("worker.tasks.github._current_branch", return_value="rick/test"), \
             patch("worker.tasks.github._git", side_effect=side_effect), \
             patch("worker.tasks.linear.handle_linear_update_issue_status", mock_linear):
            r = handle_github_open_pr({
                "title": "Feature Y",
                "linear_issue_id": "lin-uuid-123",
            })
        assert r["ok"] is True
        assert r["traceability"]["linear"]["ok"] is True
        mock_linear.assert_called_once()
        call_input = mock_linear.call_args[0][0]
        assert "pull/77" in call_input["comment"]
        assert call_input["issue_id"] == "lin-uuid-123"
