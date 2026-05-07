"""Unit tests for worker.sandbox.workspace — slice 7b-infra.

These tests never spawn Docker, never call subprocess and never
touch the host repo. Every filesystem mutation lives under pytest's
``tmp_path``. They exist to pin down:

  * the exact allowlist file shape we expect,
  * the mapping from ``target_file`` to a conventional pytest target,
  * the copy/exclusion rules for the ephemeral workspace,
  * the refusal of path-traversal writes,
  * the defensive cleanup that refuses to wipe anything outside /tmp
    or without the workspace prefix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from worker.sandbox import workspace as ws_mod
from worker.sandbox.workspace import (
    ALLOWLIST_PATH,
    TOP_LEVEL_ALLOWLIST,
    TOP_LEVEL_FILES_ALLOWLIST,
    WORKSPACE_PREFIX,
    build_workspace,
    cleanup_workspace,
    derive_candidate_test_targets,
    load_test_allowlist,
    overwrite_file_in_workspace,
    resolve_validation_target,
)


def _symlink_or_skip(link: Path, target: Path, *, target_is_directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable on this platform: {exc}")


# ---------------------------------------------------------------------------
# load_test_allowlist
# ---------------------------------------------------------------------------

class TestLoadTestAllowlist:
    def test_real_allowlist_file_loads(self):
        r = load_test_allowlist()
        assert r["ok"] is True
        assert r["error"] is None
        assert len(r["tests"]) >= 1
        for t in r["tests"]:
            assert t.startswith("tests/")
            assert t.endswith(".py")

    def test_real_allowlist_entries_are_real_files(self, tmp_path):
        r = load_test_allowlist()
        assert r["ok"] is True
        repo_root = Path(__file__).resolve().parent.parent
        missing = [t for t in r["tests"] if not (repo_root / t).is_file()]
        assert not missing, f"allowlist references missing files: {missing}"

    def test_accepts_comments_and_blank_lines(self, tmp_path):
        f = tmp_path / "allow.txt"
        f.write_text(
            "# top comment\n"
            "\n"
            "tests/test_a.py\n"
            "   \n"
            "# mid comment\n"
            "tests/test_b.py\n"
        )
        r = load_test_allowlist(f)
        assert r["ok"] is True
        assert r["tests"] == ["tests/test_a.py", "tests/test_b.py"]

    def test_rejects_path_without_tests_prefix(self, tmp_path):
        f = tmp_path / "allow.txt"
        f.write_text("worker/tasks/foo.py\n")
        r = load_test_allowlist(f)
        assert r["ok"] is False
        assert "tests/" in r["error"]

    def test_rejects_non_py_extension(self, tmp_path):
        f = tmp_path / "allow.txt"
        f.write_text("tests/test_x.txt\n")
        r = load_test_allowlist(f)
        assert r["ok"] is False

    def test_rejects_traversal(self, tmp_path):
        f = tmp_path / "allow.txt"
        f.write_text("tests/../etc/passwd\n")
        r = load_test_allowlist(f)
        assert r["ok"] is False
        assert "traversal" in r["error"] or "tests/" in r["error"]

    def test_rejects_weird_charset(self, tmp_path):
        f = tmp_path / "allow.txt"
        f.write_text("tests/test $x.py\n")
        r = load_test_allowlist(f)
        assert r["ok"] is False

    def test_rejects_duplicate_entries(self, tmp_path):
        f = tmp_path / "allow.txt"
        f.write_text("tests/test_a.py\ntests/test_a.py\n")
        r = load_test_allowlist(f)
        assert r["ok"] is False
        assert "duplicate" in r["error"]

    def test_rejects_empty_allowlist(self, tmp_path):
        f = tmp_path / "allow.txt"
        f.write_text("# only comments\n\n")
        r = load_test_allowlist(f)
        assert r["ok"] is False
        assert "empty" in r["error"]

    def test_missing_file_is_graceful(self, tmp_path):
        r = load_test_allowlist(tmp_path / "does-not-exist.txt")
        assert r["ok"] is False
        assert "cannot read" in r["error"]


# ---------------------------------------------------------------------------
# derive_candidate_test_targets
# ---------------------------------------------------------------------------

class TestDeriveCandidateTestTargets:
    def test_direct_convention(self):
        assert "tests/test_github_tournament.py" in (
            derive_candidate_test_targets("worker/tasks/github_tournament.py")
        )

    def test_handler_convention(self):
        cands = derive_candidate_test_targets("worker/tasks/tournament.py")
        assert "tests/test_tournament.py" in cands
        assert "tests/test_tournament_handler.py" in cands

    def test_parent_basename_convention(self):
        cands = derive_candidate_test_targets("worker/tasks/llm.py")
        assert "tests/test_llm.py" in cands
        assert "tests/test_tasks_llm.py" in cands

    def test_ordering_is_stable(self):
        a = derive_candidate_test_targets("worker/tasks/foo.py")
        b = derive_candidate_test_targets("worker/tasks/foo.py")
        assert a == b

    def test_dedupes_when_conventions_collide(self):
        cands = derive_candidate_test_targets("foo.py")
        assert len(cands) == len(set(cands))

    def test_non_py_returns_empty(self):
        assert derive_candidate_test_targets("worker/tasks/foo.md") == []

    def test_empty_input_returns_empty(self):
        assert derive_candidate_test_targets("") == []
        assert derive_candidate_test_targets(None) == []  # type: ignore[arg-type]

    def test_non_string_returns_empty(self):
        assert derive_candidate_test_targets(42) == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# resolve_validation_target
# ---------------------------------------------------------------------------

class TestResolveValidationTarget:
    def _fake_repo(self, tmp_path: Path, tests):
        (tmp_path / "tests").mkdir()
        for t in tests:
            (tmp_path / t).write_text("")
        return tmp_path

    def test_resolves_direct_match(self, tmp_path):
        repo = self._fake_repo(tmp_path, ["tests/test_foo.py"])
        r = resolve_validation_target(
            "worker/tasks/foo.py", repo, ["tests/test_foo.py"],
        )
        assert r["ok"] is True
        assert r["resolved"] == "tests/test_foo.py"
        assert r["candidates_tried"][0] == "tests/test_foo.py"

    def test_resolves_handler_convention(self, tmp_path):
        repo = self._fake_repo(tmp_path, ["tests/test_foo_handler.py"])
        r = resolve_validation_target(
            "worker/tasks/foo.py", repo,
            ["tests/test_foo_handler.py", "tests/test_foo.py"],
        )
        assert r["ok"] is True
        assert r["resolved"] == "tests/test_foo_handler.py"

    def test_fails_when_candidate_missing_from_disk(self, tmp_path):
        repo = self._fake_repo(tmp_path, [])
        r = resolve_validation_target(
            "worker/tasks/foo.py", repo, ["tests/test_foo.py"],
        )
        assert r["ok"] is False
        assert r["resolved"] is None

    def test_fails_when_candidate_not_in_allowlist(self, tmp_path):
        repo = self._fake_repo(tmp_path, ["tests/test_foo.py"])
        r = resolve_validation_target(
            "worker/tasks/foo.py", repo, ["tests/test_unrelated.py"],
        )
        assert r["ok"] is False
        assert "no candidate" in r["error"]
        assert "tests/test_foo.py" in r["candidates_tried"]

    def test_rejects_empty_allowlist(self, tmp_path):
        r = resolve_validation_target("worker/tasks/foo.py", tmp_path, [])
        assert r["ok"] is False
        assert "allowlist" in r["error"]

    def test_rejects_empty_target_file(self, tmp_path):
        r = resolve_validation_target("", tmp_path, ["tests/test_x.py"])
        assert r["ok"] is False

    def test_rejects_non_path_repo_root(self):
        r = resolve_validation_target(
            "worker/tasks/foo.py", "/tmp/whatever",  # type: ignore[arg-type]
            ["tests/test_foo.py"],
        )
        assert r["ok"] is False


# ---------------------------------------------------------------------------
# build_workspace
# ---------------------------------------------------------------------------

class TestBuildWorkspace:
    def _fake_repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        repo.mkdir()
        # Allowlisted content
        (repo / "worker").mkdir()
        (repo / "worker" / "__init__.py").write_text("")
        (repo / "worker" / "app.py").write_text("print('no-op')\n")
        (repo / "worker" / "tasks").mkdir()
        (repo / "worker" / "tasks" / "foo.py").write_text("X = 1\n")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_foo.py").write_text("def test_ok(): assert 1\n")
        (repo / "dispatcher").mkdir()
        (repo / "dispatcher" / "mod.py").write_text("")
        (repo / "pyproject.toml").write_text('[project]\nname = "x"\n')
        # Forbidden content
        (repo / ".git").mkdir()
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        (repo / ".rick").mkdir()
        (repo / ".rick" / "secret.md").write_text("top secret")
        (repo / ".venv").mkdir()
        (repo / ".venv" / "pyvenv.cfg").write_text("home=x")
        (repo / ".env").write_text("SECRET=abc\n")
        (repo / ".env.local").write_text("SECRET=def\n")
        (repo / "node_modules").mkdir()
        (repo / "node_modules" / "some.js").write_text("")
        (repo / "__pycache__").mkdir()
        (repo / "__pycache__" / "x.pyc").write_text("")
        (repo / "worker" / "__pycache__").mkdir()
        (repo / "worker" / "__pycache__" / "app.cpython-311.pyc").write_text("")
        (repo / "worker" / "tasks" / "compiled.pyc").write_text("")
        # Non-allowlisted top-level file and dir
        (repo / "README.md").write_text("hello")
        (repo / "scripts").mkdir()
        (repo / "scripts" / "deploy.sh").write_text("#!/bin/sh\n")
        return repo

    def test_copies_only_allowlisted_tops(self, tmp_path):
        repo = self._fake_repo(tmp_path)
        r = build_workspace(repo, "test-abc", parent_dir=tmp_path / "wsroot")
        assert r["ok"] is True, r["error"]
        ws = r["path"]
        assert ws.is_dir()
        # Copied
        for name in list(TOP_LEVEL_ALLOWLIST) + list(TOP_LEVEL_FILES_ALLOWLIST):
            assert (ws / name).exists(), f"expected {name} in workspace"
        # Not copied
        for name in [".git", ".rick", ".venv", ".env", ".env.local",
                     "node_modules", "__pycache__", "README.md", "scripts"]:
            assert not (ws / name).exists(), f"unexpected {name} in workspace"

    def test_strips_nested_pycache(self, tmp_path):
        repo = self._fake_repo(tmp_path)
        r = build_workspace(repo, "test-abc", parent_dir=tmp_path / "wsroot")
        ws = r["path"]
        assert (ws / "worker" / "__init__.py").exists()
        assert not (ws / "worker" / "__pycache__").exists()
        # .pyc files are dropped even if their parent is allowlisted
        assert not (ws / "worker" / "tasks" / "compiled.pyc").exists()
        assert (ws / "worker" / "tasks" / "foo.py").exists()

    def test_returns_copied_manifest(self, tmp_path):
        repo = self._fake_repo(tmp_path)
        r = build_workspace(repo, "test-xyz", parent_dir=tmp_path / "wsroot")
        assert r["ok"] is True
        names = set(r["copied"])
        assert "worker/" in names
        assert "tests/" in names
        assert "dispatcher/" in names
        assert "pyproject.toml" in names
        assert ".git/" not in names
        assert "README.md" not in names

    def test_workspace_name_has_prefix(self, tmp_path):
        repo = self._fake_repo(tmp_path)
        r = build_workspace(repo, "tid", parent_dir=tmp_path / "wsroot")
        assert r["path"].name.startswith(WORKSPACE_PREFIX)
        assert "tid" in r["path"].name

    def test_rejects_non_path_repo_root(self):
        r = build_workspace("/tmp", "tid")  # type: ignore[arg-type]
        assert r["ok"] is False

    def test_rejects_missing_repo_root(self, tmp_path):
        r = build_workspace(tmp_path / "ghost", "tid",
                            parent_dir=tmp_path / "wsroot")
        assert r["ok"] is False
        assert "does not exist" in r["error"]

    def test_rejects_bad_tournament_id_charset(self, tmp_path):
        repo = self._fake_repo(tmp_path)
        for bad in ["tid with space", "tid/slash", "tid;rm", "tid\n"]:
            r = build_workspace(repo, bad, parent_dir=tmp_path / "wsroot")
            assert r["ok"] is False, bad
            assert "charset" in r["error"]

    def test_rejects_empty_tournament_id(self, tmp_path):
        repo = self._fake_repo(tmp_path)
        r = build_workspace(repo, "", parent_dir=tmp_path / "wsroot")
        assert r["ok"] is False

    def test_does_not_follow_top_level_symlink(self, tmp_path):
        repo = self._fake_repo(tmp_path)
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "leak.txt").write_text("should not be copied")
        _symlink_or_skip(repo / "worker_link", outside, target_is_directory=True)
        r = build_workspace(repo, "tid", parent_dir=tmp_path / "wsroot")
        assert r["ok"] is True
        assert not (r["path"] / "worker_link").exists()
        assert not (r["path"] / "worker_link" / "leak.txt").exists()

    def test_does_not_follow_nested_symlink(self, tmp_path):
        repo = self._fake_repo(tmp_path)
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "leak.txt").write_text("should not be copied")
        _symlink_or_skip(repo / "worker" / "link", outside, target_is_directory=True)
        r = build_workspace(repo, "tid", parent_dir=tmp_path / "wsroot")
        assert r["ok"] is True
        assert not (r["path"] / "worker" / "link").exists()


# ---------------------------------------------------------------------------
# overwrite_file_in_workspace
# ---------------------------------------------------------------------------

class TestOverwriteFileInWorkspace:
    def _ws(self, tmp_path: Path) -> Path:
        p = tmp_path / f"{WORKSPACE_PREFIX}t-0001"
        p.mkdir()
        (p / "worker" / "tasks").mkdir(parents=True)
        (p / "worker" / "tasks" / "foo.py").write_text("original\n")
        return p

    def test_overwrites_existing_file(self, tmp_path):
        ws = self._ws(tmp_path)
        r = overwrite_file_in_workspace(ws, "worker/tasks/foo.py", "new\n")
        assert r["ok"] is True
        assert (ws / "worker" / "tasks" / "foo.py").read_text() == "new\n"

    def test_creates_missing_parents(self, tmp_path):
        ws = self._ws(tmp_path)
        r = overwrite_file_in_workspace(
            ws, "worker/tasks/new/deep/mod.py", "hello\n",
        )
        assert r["ok"] is True
        assert (ws / "worker" / "tasks" / "new" / "deep" / "mod.py").exists()

    def test_rejects_absolute_path(self, tmp_path):
        ws = self._ws(tmp_path)
        r = overwrite_file_in_workspace(ws, "/etc/passwd", "bad")
        assert r["ok"] is False
        assert "relative" in r["error"]

    def test_rejects_traversal(self, tmp_path):
        ws = self._ws(tmp_path)
        r = overwrite_file_in_workspace(
            ws, "../outside.py", "bad",
        )
        assert r["ok"] is False
        assert ".." in r["error"]

    def test_rejects_traversal_via_nested_segments(self, tmp_path):
        ws = self._ws(tmp_path)
        r = overwrite_file_in_workspace(
            ws, "worker/tasks/../../../outside.py", "bad",
        )
        assert r["ok"] is False

    def test_rejects_non_string_content(self, tmp_path):
        ws = self._ws(tmp_path)
        r = overwrite_file_in_workspace(
            ws, "worker/tasks/foo.py", b"bytes",  # type: ignore[arg-type]
        )
        assert r["ok"] is False

    def test_rejects_missing_workspace(self, tmp_path):
        r = overwrite_file_in_workspace(
            tmp_path / "ghost", "foo.py", "x",
        )
        assert r["ok"] is False


# ---------------------------------------------------------------------------
# cleanup_workspace
# ---------------------------------------------------------------------------

class TestCleanupWorkspace:
    def test_removes_workspace(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            ws_mod.tempfile, "gettempdir", lambda: str(tmp_path),
        )
        ws = tmp_path / f"{WORKSPACE_PREFIX}rm-1"
        ws.mkdir()
        (ws / "file.txt").write_text("x")
        r = cleanup_workspace(ws)
        assert r["ok"] is True
        assert r["removed"] is True
        assert not ws.exists()

    def test_noop_when_already_gone(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            ws_mod.tempfile, "gettempdir", lambda: str(tmp_path),
        )
        ws = tmp_path / f"{WORKSPACE_PREFIX}rm-2"
        r = cleanup_workspace(ws)
        assert r["ok"] is True
        assert r["removed"] is False

    def test_refuses_path_without_prefix(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            ws_mod.tempfile, "gettempdir", lambda: str(tmp_path),
        )
        ws = tmp_path / "not-a-sandbox"
        ws.mkdir()
        (ws / "keep.txt").write_text("keep")
        r = cleanup_workspace(ws)
        assert r["ok"] is False
        assert WORKSPACE_PREFIX in r["error"]
        assert ws.exists()
        assert (ws / "keep.txt").exists()

    def test_refuses_path_outside_tmp_root(self, tmp_path, monkeypatch):
        safe_tmp = tmp_path / "sys-tmp"
        safe_tmp.mkdir()
        monkeypatch.setattr(
            ws_mod.tempfile, "gettempdir", lambda: str(safe_tmp),
        )
        elsewhere = tmp_path / "other" / f"{WORKSPACE_PREFIX}rm-3"
        elsewhere.mkdir(parents=True)
        (elsewhere / "file.txt").write_text("x")
        r = cleanup_workspace(elsewhere)
        assert r["ok"] is False
        assert "tmp" in r["error"]
        assert elsewhere.exists()

    def test_rejects_non_path(self):
        r = cleanup_workspace("/tmp/whatever")  # type: ignore[arg-type]
        assert r["ok"] is False


# ---------------------------------------------------------------------------
# Integration smoke — build + overwrite + resolve + cleanup chain
# ---------------------------------------------------------------------------

class TestBuildOverwriteResolveCleanupChain:
    def test_chain_on_mini_repo(self, tmp_path):
        # Build a mini repo mirroring the real layout enough to
        # exercise the chain end-to-end, without touching the host
        # repo at all.
        repo = tmp_path / "mini_repo"
        (repo / "worker" / "tasks").mkdir(parents=True)
        (repo / "worker" / "__init__.py").write_text("")
        (repo / "worker" / "tasks" / "__init__.py").write_text("")
        (repo / "worker" / "tasks" / "foo.py").write_text("X = 1\n")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_foo.py").write_text("def test_ok(): assert 1\n")
        (repo / "pyproject.toml").write_text('[project]\nname="mini"\n')

        wsroot = tmp_path / "tmp"
        bw = build_workspace(repo, "mini-chain", parent_dir=wsroot)
        assert bw["ok"] is True
        ws = bw["path"]

        allow = ["tests/test_foo.py"]
        rv = resolve_validation_target("worker/tasks/foo.py", ws, allow)
        assert rv["ok"] is True
        assert rv["resolved"] == "tests/test_foo.py"

        ov = overwrite_file_in_workspace(
            ws, "worker/tasks/foo.py", "X = 42\n",
        )
        assert ov["ok"] is True
        assert (ws / "worker" / "tasks" / "foo.py").read_text() == "X = 42\n"
        # Test file was NOT touched — only target_file was overwritten.
        assert (ws / "tests" / "test_foo.py").read_text().strip() == (
            "def test_ok(): assert 1"
        )

        import tempfile as _tf
        orig_gettempdir = _tf.gettempdir
        try:
            _tf.gettempdir = lambda: str(wsroot)  # type: ignore[assignment]
            cu = cleanup_workspace(ws)
        finally:
            _tf.gettempdir = orig_gettempdir  # type: ignore[assignment]
        assert cu["ok"] is True
        assert cu["removed"] is True
        assert not ws.exists()


# ---------------------------------------------------------------------------
# Allowlist file exists next to the Dockerfile
# ---------------------------------------------------------------------------

class TestAllowlistFileLocation:
    def test_default_path_is_next_to_module(self):
        assert ALLOWLIST_PATH.parent == Path(ws_mod.__file__).parent
        assert ALLOWLIST_PATH.name == "test_allowlist.txt"

    def test_dockerfile_is_in_same_dir(self):
        assert (ALLOWLIST_PATH.parent / "Dockerfile").is_file()

    def test_refresh_script_is_in_same_dir_and_executable(self):
        script = ALLOWLIST_PATH.parent / "refresh.sh"
        assert script.is_file()
        import os
        assert os.access(script, os.X_OK)
