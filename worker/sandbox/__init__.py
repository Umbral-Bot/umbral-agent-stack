"""Sandbox infrastructure for the (future) ``pytest_target`` validation
mode — Phase 2 slice 7b-infra.

This package contains only the primitives needed to isolate a pytest run
inside an ephemeral Docker container:

* a ``Dockerfile`` for the pre-built sandbox image,
* a ``refresh.sh`` helper that rebuilds the image deterministically
  when ``pyproject.toml`` changes,
* a ``test_allowlist.txt`` file listing the tests that are allowed to
  run inside the sandbox, and
* :mod:`worker.sandbox.workspace` with pure helpers that build an
  ephemeral workspace, overwrite the contestant's target file in it,
  resolve a safe validation target from an input ``target_file`` and
  clean up afterwards.

Slice 7b-infra intentionally does NOT wire any of this into
``handle_github_orchestrate_tournament`` or ``_run_contestant_validation``.
Runtime behaviour is unchanged. A follow-up slice (7b-runner) will
consume these primitives to add the real ``pytest_target`` mode.
"""

from .workspace import (
    ALLOWLIST_PATH,
    TOP_LEVEL_ALLOWLIST,
    WORKSPACE_PREFIX,
    build_workspace,
    cleanup_workspace,
    derive_candidate_test_targets,
    load_test_allowlist,
    overwrite_file_in_workspace,
    resolve_validation_target,
)

__all__ = [
    "ALLOWLIST_PATH",
    "TOP_LEVEL_ALLOWLIST",
    "WORKSPACE_PREFIX",
    "build_workspace",
    "cleanup_workspace",
    "derive_candidate_test_targets",
    "load_test_allowlist",
    "overwrite_file_in_workspace",
    "resolve_validation_target",
]
