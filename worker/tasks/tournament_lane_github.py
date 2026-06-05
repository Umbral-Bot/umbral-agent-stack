"""GitHub operations for OpenClaw-native tournament lanes.

This module is deliberately separate from ``worker.tasks.github`` because
tournament lanes use a different branch contract:
``tournament/<tournament_id>/lane-<specialty>``.  The daily Rick GitHub
handler remains scoped to ``rick/`` branches.
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .. import config

logger = logging.getLogger("worker.tasks.tournament_lane_github")

_PROTECTED_BRANCHES = {"main", "master"}
_BASE_BRANCH = "main"
_DEFAULT_REPO = "Umbral-Bot/umbral-agent-stack"

_LANE_BRANCH_RE = re.compile(
    r"^tournament/"
    r"(?P<tournament_id>[A-Za-z0-9][A-Za-z0-9._-]{0,63})/"
    r"lane-(?P<specialty>[A-Za-z0-9][A-Za-z0-9._-]{0,63})$"
)
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_BASE_NAME_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
_SENSITIVE_PATTERNS = re.compile(
    r"(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|gho_[A-Za-z0-9]{30,})",
)


def _sanitize_output(text: str, max_len: int = 800) -> str:
    sanitized = _SENSITIVE_PATTERNS.sub("[REDACTED]", text or "")
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len] + "...(truncated)"
    return sanitized.strip()


def _github_token() -> Optional[str]:
    token = (config.GITHUB_TOKEN or "").strip()
    if token:
        return token
    return os.environ.get("GITHUB_TOKEN", "").strip() or None


def _gh_env() -> Optional[Dict[str, str]]:
    token = _github_token()
    if not token:
        return None
    return {"GH_TOKEN": token}


def _run(
    args: List[str],
    *,
    repo_path: str,
    env_extra: Optional[Dict[str, str]] = None,
    timeout: int = 60,
    check: bool = True,
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    try:
        result = subprocess.run(
            args,
            cwd=repo_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command {args} timed out after {timeout}s") from exc

    if check and result.returncode != 0:
        detail = _sanitize_output(result.stderr or result.stdout)
        raise RuntimeError(
            f"Command {args} failed (rc={result.returncode}): {detail}"
        )
    return result


def _resolve_repo_path(input_data: Dict[str, Any]) -> str:
    raw = (input_data.get("repo_path") or config.GITHUB_REPO_PATH or "").strip()
    if not raw:
        raise ValueError("repo_path is required")
    repo_path = str(Path(raw).expanduser())
    path = Path(repo_path)
    if not path.is_dir():
        raise ValueError(f"repo_path does not exist: {repo_path}")
    if not (path / ".git").exists():
        raise ValueError(f"repo_path is not a git repository: {repo_path}")
    return repo_path


def _validate_base(base: Any) -> str:
    value = (base or _BASE_BRANCH).strip() if isinstance(base, str) else _BASE_BRANCH
    if not value:
        raise ValueError("base branch name is required")
    if not _BASE_NAME_RE.match(value):
        raise ValueError(f"base branch name contains invalid characters: '{value}'")
    if value != _BASE_BRANCH:
        raise ValueError("Tournament lane PRs must target base branch 'main'")
    return value


def _validate_segment(value: Any, name: str) -> str:
    segment = (value or "").strip() if isinstance(value, str) else ""
    if not segment:
        raise ValueError(f"{name} is required")
    if not _SEGMENT_RE.match(segment):
        raise ValueError(
            f"{name} contains invalid characters: '{segment}'. "
            "Use letters, digits, dot, underscore, or hyphen; no slashes."
        )
    return segment


def _lane_branch_name(tournament_id: str, specialty: str) -> str:
    return f"tournament/{tournament_id}/lane-{specialty}"


def _validate_lane_branch(branch: Any) -> Tuple[str, str, str]:
    branch_name = (branch or "").strip() if isinstance(branch, str) else ""
    if not branch_name:
        raise ValueError("branch_name is required")
    if branch_name in _PROTECTED_BRANCHES:
        raise ValueError(f"Refusing to operate on protected branch '{branch_name}'")
    match = _LANE_BRANCH_RE.fullmatch(branch_name)
    if not match:
        raise ValueError(
            "Branch must match 'tournament/<tournament_id>/lane-<specialty>' "
            f"(got '{branch_name}')"
        )
    return branch_name, match.group("tournament_id"), match.group("specialty")


def _branch_from_input(input_data: Dict[str, Any]) -> Tuple[str, str, str]:
    explicit = (input_data.get("branch_name") or "").strip()
    tournament_id = (input_data.get("tournament_id") or "").strip()
    specialty = (input_data.get("specialty") or "").strip()

    if explicit:
        branch, parsed_tid, parsed_specialty = _validate_lane_branch(explicit)
        if tournament_id and tournament_id != parsed_tid:
            raise ValueError(
                f"branch_name tournament_id mismatch: '{parsed_tid}' != '{tournament_id}'"
            )
        if specialty and specialty != parsed_specialty:
            raise ValueError(
                f"branch_name specialty mismatch: '{parsed_specialty}' != '{specialty}'"
            )
        return branch, parsed_tid, parsed_specialty

    tid = _validate_segment(tournament_id, "tournament_id")
    spec = _validate_segment(specialty, "specialty")
    return _lane_branch_name(tid, spec), tid, spec


def _current_branch(repo_path: str) -> str:
    result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_path=repo_path)
    return result.stdout.strip()


def _status_porcelain(repo_path: str) -> str:
    result = _run(["git", "status", "--porcelain"], repo_path=repo_path)
    return result.stdout.strip()


def _ensure_clean_worktree(repo_path: str) -> None:
    status = _status_porcelain(repo_path)
    if status:
        raise RuntimeError(
            "Working copy has uncommitted or untracked changes. "
            "Resolve them before tournament lane GitHub operations.\n"
            f"Dirty files:\n{status[:500]}"
        )


def _extract_gh_account(output: str) -> Optional[str]:
    for line in output.splitlines():
        lowered = line.lower()
        if "logged in to github.com account" in lowered:
            return line.split("account", 1)[1].strip().split()[0].strip("()")
    return None


def _normalize_files(repo_path: str, files: Any) -> List[str]:
    if not isinstance(files, list) or not files:
        raise ValueError("files list is required: explicit staging only, no git add -A")

    repo_root = Path(repo_path).resolve()
    normalized: List[str] = []
    for raw in files:
        if not isinstance(raw, str):
            raise ValueError("files must be a list of relative path strings")
        rel = raw.strip().replace("\\", "/")
        if not rel:
            continue
        if rel.startswith("/") or rel.startswith("~"):
            raise ValueError(f"Path must be relative to repo: '{raw}'")
        full = (repo_root / rel).resolve()
        try:
            full.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError(f"Path escapes repo boundary: '{raw}'") from exc
        normalized.append(full.relative_to(repo_root).as_posix())

    if not normalized:
        raise ValueError("files list resolved to empty after normalization")
    return normalized


def _validate_pr_title(title: str, tournament_id: str, specialty: str) -> str:
    value = title.strip()
    prefix = f"[tournament:{tournament_id}:{specialty}] "
    if not value:
        raise ValueError("title is required")
    if not value.startswith(prefix) or len(value) <= len(prefix):
        raise ValueError(
            f"PR title must start with '{prefix}' followed by a short description"
        )
    return value


def _resolve_pr_title(input_data: Dict[str, Any], tournament_id: str, specialty: str) -> str:
    title = (input_data.get("title") or "").strip()
    if not title:
        issue_title = (input_data.get("issue_title") or "").strip()
        if not issue_title:
            raise ValueError("title or issue_title is required")
        title = f"[tournament:{tournament_id}:{specialty}] {issue_title}"
    return _validate_pr_title(title, tournament_id, specialty)


def _repo_arg(input_data: Dict[str, Any]) -> str:
    repo = (input_data.get("repo") or _DEFAULT_REPO).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError(f"repo must be owner/name (got '{repo}')")
    return repo


def _build_pr_body(
    input_data: Dict[str, Any],
    *,
    tournament_id: str,
    specialty: str,
    branch: str,
) -> str:
    sections: List[str] = []
    custom = (input_data.get("body") or "").strip()
    if custom:
        sections.append(custom)

    issue_url = (input_data.get("issue_url") or "").strip()
    tests = (input_data.get("tests") or input_data.get("test_command") or "").strip()
    if not tests:
        tests = "Not reported by lane."

    lane_section = [
        "## Tournament lane",
        f"- Tournament: `{tournament_id}`",
        f"- Specialty: `{specialty}`",
        f"- Head branch: `{branch}`",
    ]
    if issue_url:
        lane_section.append(f"- Issue: {issue_url}")
    lane_section.extend([
        f"- Tests: `{tests}`",
        "",
        "## Checklist",
        "- [x] I did not merge this PR.",
        "- [x] Branch follows `tournament/<tournament_id>/lane-<specialty>`.",
        "- [x] Title follows `[tournament:<id>:<specialty>] ...`.",
    ])
    sections.append("\n".join(lane_section))
    return "\n\n".join(sections).strip()


def _parse_pr_url(stdout: str) -> Tuple[str, Optional[int]]:
    pr_url = stdout.strip().splitlines()[-1].strip() if stdout.strip() else ""
    match = re.search(r"/pull/(\d+)", pr_url)
    return pr_url, int(match.group(1)) if match else None


def _summarize_checks(rollup: Any) -> Dict[str, Any]:
    if not isinstance(rollup, list) or not rollup:
        return {"status": "none", "total": 0, "success": 0, "failure": 0, "pending": 0}

    success = failure = pending = 0
    failure_conclusions = {
        "FAILURE",
        "CANCELLED",
        "TIMED_OUT",
        "ACTION_REQUIRED",
        "STARTUP_FAILURE",
    }
    success_conclusions = {"SUCCESS", "SKIPPED", "NEUTRAL"}

    for item in rollup:
        conclusion = None
        status = None
        if isinstance(item, dict):
            raw_conclusion = item.get("conclusion")
            raw_status = item.get("status")
            conclusion = str(raw_conclusion).upper() if raw_conclusion else None
            status = str(raw_status).upper() if raw_status else None
        if conclusion in success_conclusions:
            success += 1
        elif conclusion in failure_conclusions:
            failure += 1
        elif status == "COMPLETED" and conclusion is None:
            pending += 1
        else:
            pending += 1

    overall = "failure" if failure else "pending" if pending else "success"
    return {
        "status": overall,
        "total": len(rollup),
        "success": success,
        "failure": failure,
        "pending": pending,
    }


def handle_tournament_lane_preflight(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate gh auth, repo path, clean worktree, and main ff-only readiness."""
    try:
        repo_path = _resolve_repo_path(input_data)
        base = _validate_base(input_data.get("base"))
        initial_branch = _current_branch(repo_path)
        _ensure_clean_worktree(repo_path)

        _run(["git", "fetch", "origin", base], repo_path=repo_path, timeout=30)
        _run(["git", "checkout", base], repo_path=repo_path, timeout=30)
        _run(["git", "pull", "--ff-only", "origin", base], repo_path=repo_path, timeout=60)

        gh = _run(
            ["gh", "auth", "status"],
            repo_path=repo_path,
            env_extra=_gh_env(),
            check=False,
            timeout=15,
        )
        if gh.returncode != 0:
            return {
                "ok": False,
                "error": f"gh auth status failed: {_sanitize_output(gh.stderr or gh.stdout)}",
                "repo_path": repo_path,
                "base": base,
            }

        return {
            "ok": True,
            "repo_path": repo_path,
            "base": base,
            "initial_branch": initial_branch,
            "branch": _current_branch(repo_path),
            "clean": True,
            "gh_authenticated": True,
            "gh_account": _extract_gh_account(gh.stdout + "\n" + gh.stderr),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def handle_tournament_lane_create_branch(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create ``tournament/<id>/lane-<specialty>`` from ``origin/main``."""
    try:
        repo_path = _resolve_repo_path(input_data)
        branch, tournament_id, specialty = _branch_from_input(input_data)
        base = _validate_base(input_data.get("base"))
        _ensure_clean_worktree(repo_path)

        local = _run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            repo_path=repo_path,
            check=False,
        )
        if local.returncode == 0:
            return {"ok": False, "error": f"Local branch already exists: {branch}"}

        remote = _run(
            ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
            repo_path=repo_path,
            check=False,
            timeout=30,
        )
        if remote.returncode == 0:
            return {"ok": False, "error": f"Remote branch already exists: {branch}"}

        _run(["git", "fetch", "origin", base], repo_path=repo_path, timeout=30)
        _run(
            ["git", "checkout", "-b", branch, f"origin/{base}"],
            repo_path=repo_path,
            timeout=30,
        )
        return {
            "ok": True,
            "repo_path": repo_path,
            "branch": branch,
            "tournament_id": tournament_id,
            "specialty": specialty,
            "base": base,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def handle_tournament_lane_commit_and_push(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Stage an explicit file list, commit, and push the current lane branch."""
    try:
        message = (input_data.get("message") or input_data.get("commit_message") or "").strip()
        if not message:
            return {"ok": False, "error": "message is required"}

        repo_path = _resolve_repo_path(input_data)
        branch, tournament_id, specialty = _branch_from_input(input_data)
        current = _current_branch(repo_path)
        if current != branch:
            return {
                "ok": False,
                "error": f"Branch mismatch: expected '{branch}', currently on '{current}'",
            }

        files = _normalize_files(repo_path, input_data.get("files"))

        staged_before = _run(
            ["git", "diff", "--cached", "--name-only"],
            repo_path=repo_path,
        ).stdout.strip()
        if staged_before:
            return {
                "ok": False,
                "error": f"Refusing to continue with pre-existing staged changes: {staged_before}",
            }

        _run(["git", "add", "--"] + files, repo_path=repo_path)
        staged = _run(
            ["git", "diff", "--cached", "--name-only"],
            repo_path=repo_path,
        ).stdout.strip().splitlines()
        if not staged:
            return {"ok": False, "error": "No staged changes after explicit git add"}
        staged_set = {path.replace("\\", "/") for path in staged}
        files_set = set(files)
        if not staged_set.issubset(files_set):
            return {
                "ok": False,
                "error": (
                    "Staged changes include files outside explicit list: "
                    f"{sorted(staged_set - files_set)}"
                ),
            }

        _run(["git", "commit", "-m", message], repo_path=repo_path, timeout=60)
        _run(["git", "push", "-u", "origin", branch], repo_path=repo_path, timeout=60)
        sha = _run(["git", "rev-parse", "HEAD"], repo_path=repo_path).stdout.strip()
        return {
            "ok": True,
            "repo_path": repo_path,
            "branch": branch,
            "tournament_id": tournament_id,
            "specialty": specialty,
            "commit_sha": sha,
            "files": files,
            "pushed": True,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def handle_tournament_lane_open_pr(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Open a PR from a tournament lane branch to main. Never merges."""
    try:
        repo_path = _resolve_repo_path(input_data)
        branch, tournament_id, specialty = _branch_from_input(input_data)
        base = _validate_base(input_data.get("base"))
        title = _resolve_pr_title(input_data, tournament_id, specialty)
        repo = _repo_arg(input_data)

        current = _current_branch(repo_path)
        if current != branch:
            return {
                "ok": False,
                "error": f"Branch mismatch: expected '{branch}', currently on '{current}'",
            }

        body = _build_pr_body(
            input_data,
            tournament_id=tournament_id,
            specialty=specialty,
            branch=branch,
        )
        result = _run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--head",
                branch,
                "--base",
                base,
                "--title",
                title,
                "--body",
                body,
            ],
            repo_path=repo_path,
            env_extra=_gh_env(),
            timeout=60,
        )
        pr_url, pr_number = _parse_pr_url(result.stdout)
        if not pr_url:
            return {"ok": False, "error": "gh pr create did not return a PR URL"}

        return {
            "ok": True,
            "repo_path": repo_path,
            "repo": repo,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "branch": branch,
            "base": base,
            "title": title,
            "tournament_id": tournament_id,
            "specialty": specialty,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def handle_tournament_lane_verify_pr(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify PR metadata for orchestrator collect."""
    try:
        repo_path = _resolve_repo_path(input_data)
        branch, tournament_id, specialty = _branch_from_input(input_data)
        repo = _repo_arg(input_data)
        pr_ref = (
            str(input_data.get("pr_url") or "").strip()
            or str(input_data.get("pr_number") or "").strip()
            or branch
        )
        if not pr_ref:
            return {"ok": False, "error": "pr_url, pr_number, or branch_name is required"}

        result = _run(
            [
                "gh",
                "pr",
                "view",
                pr_ref,
                "--repo",
                repo,
                "--json",
                "url,number,headRefName,baseRefName,title,mergeable,statusCheckRollup,additions,deletions,state,isDraft",
            ],
            repo_path=repo_path,
            env_extra=_gh_env(),
            timeout=30,
        )
        payload = json.loads(result.stdout or "{}")
        title = str(payload.get("title") or "")
        head = str(payload.get("headRefName") or "")
        expected_prefix = f"[tournament:{tournament_id}:{specialty}] "
        checks = _summarize_checks(payload.get("statusCheckRollup"))

        errors = []
        if head != branch:
            errors.append(f"headRefName mismatch: expected '{branch}', got '{head}'")
        if not title.startswith(expected_prefix):
            errors.append(f"title missing expected prefix '{expected_prefix}'")
        if payload.get("baseRefName") != _BASE_BRANCH:
            errors.append("baseRefName must be 'main'")

        ok = not errors
        return {
            "ok": ok,
            "error": "; ".join(errors) if errors else None,
            "repo_path": repo_path,
            "repo": repo,
            "pr_url": payload.get("url"),
            "pr_number": payload.get("number"),
            "head_ref": head,
            "base_ref": payload.get("baseRefName"),
            "title": title,
            "state": payload.get("state"),
            "is_draft": payload.get("isDraft"),
            "mergeable": payload.get("mergeable"),
            "additions": payload.get("additions"),
            "deletions": payload.get("deletions"),
            "checks": checks,
            "tournament_id": tournament_id,
            "specialty": specialty,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
