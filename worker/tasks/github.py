"""
Tasks: GitHub operations for Rick.

- github.preflight: validate SSH, token, repo, and worktree readiness before work
- github.create_branch: create a rick/ feature branch from a base
- github.commit_and_push: stage explicit files, commit, push current branch
- github.open_pr: open a PR via gh CLI, route PR URL to Notion/Linear
"""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import config

logger = logging.getLogger("worker.tasks.github")

# Branches Rick must never push to or check out for work
_PROTECTED_BRANCHES = {"main", "master"}

# Required prefix for Rick's branches (convention from docs/28)
_BRANCH_PREFIX = "rick/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SENSITIVE_PATTERNS = re.compile(
    r"(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|gho_[A-Za-z0-9]{30,})",
)

_BASE_NAME_RE = re.compile(r"^[a-zA-Z0-9_./-]+$")


def _sanitize_stderr(text: str, max_len: int = 500) -> str:
    """Truncate and redact token-like patterns from subprocess stderr."""
    sanitized = _SENSITIVE_PATTERNS.sub("[REDACTED]", text)
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len] + "…(truncated)"
    return sanitized.strip()


def _validate_base_name(base: str) -> str:
    """Validate a base branch name. Raises ValueError on invalid input."""
    base = base.strip()
    if not base:
        raise ValueError("base branch name is required")
    if not _BASE_NAME_RE.match(base):
        raise ValueError(f"base branch name contains invalid characters: '{base}'")
    return base


def _git(
    args: List[str],
    *,
    repo_path: Optional[str] = None,
    env_extra: Optional[Dict[str, str]] = None,
    timeout: int = 60,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a git/gh command in the repo working copy."""
    cwd = repo_path or config.GITHUB_REPO_PATH
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
        env=env,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command {args} failed (rc={result.returncode}): "
            f"{_sanitize_stderr(result.stderr)}"
        )
    return result


def _github_token() -> Optional[str]:
    """Return GITHUB_TOKEN from config or os.environ."""
    key = (config.GITHUB_TOKEN or "").strip()
    if key:
        return key
    return os.environ.get("GITHUB_TOKEN", "").strip() or None


def _validate_branch_name(branch: str) -> str:
    """Validate and normalize branch name. Raises ValueError on invalid input."""
    branch = branch.strip()
    if not branch:
        raise ValueError("branch_name is required")
    if branch in _PROTECTED_BRANCHES:
        raise ValueError(f"Refusing to operate on protected branch '{branch}'")
    if not branch.startswith(_BRANCH_PREFIX):
        raise ValueError(
            f"Branch must start with '{_BRANCH_PREFIX}' (got '{branch}'). "
            f"Convention: rick/feature-description"
        )
    if not re.match(r"^[a-zA-Z0-9_./-]+$", branch):
        raise ValueError(f"Branch name contains invalid characters: '{branch}'")
    return branch


def _ensure_clean_worktree(repo_path: str) -> None:
    """Ensure there are no uncommitted changes (modified/staged) in the working copy.

    Untracked files are ignored — they are common on the VPS (local-only
    metadata, audit docs) and do not interfere with branch/commit operations.
    """
    result = _git(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        repo_path=repo_path,
    )
    if result.stdout.strip():
        raise RuntimeError(
            "Working copy has uncommitted changes. "
            "Resolve them before starting a new GitHub operation.\n"
            f"Dirty files:\n{result.stdout.strip()[:500]}"
        )


def _current_branch(repo_path: str) -> str:
    """Return the current branch name."""
    result = _git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_path=repo_path
    )
    return result.stdout.strip()


def _resolve_repo_path() -> str:
    """Return the canonical repo path from config. Input overrides are not accepted."""
    repo_path = config.GITHUB_REPO_PATH
    if not Path(repo_path).is_dir():
        raise ValueError(f"repo_path does not exist: {repo_path}")
    git_dir = Path(repo_path) / ".git"
    if not git_dir.exists():
        raise ValueError(f"repo_path is not a git repository: {repo_path}")
    return repo_path


# ---------------------------------------------------------------------------
# Handler: github.preflight
# ---------------------------------------------------------------------------


def handle_github_preflight(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate GitHub readiness: SSH, token, repo, worktree.

    Returns:
        {"ok": True, "ssh": bool, "token": True, "token_user": "...",
         "repo_path": "...", "branch": "...", "clean": bool,
         "remote_reachable": True}
    """
    errors = []
    info: Dict[str, Any] = {"ok": True}

    # --- Repo path ---
    try:
        repo_path = _resolve_repo_path()
        info["repo_path"] = repo_path
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    # --- Current branch ---
    try:
        info["branch"] = _current_branch(repo_path)
    except Exception as e:
        errors.append(f"Cannot read current branch: {e}")
        info["branch"] = None

    # --- Worktree cleanliness ---
    try:
        _ensure_clean_worktree(repo_path)
        info["clean"] = True
    except RuntimeError:
        info["clean"] = False

    # --- SSH (optional, not a hard blocker) ---
    try:
        ssh_result = _git(
            ["ssh", "-o", "ConnectTimeout=5", "-T", "git@github.com"],
            repo_path=repo_path,
            check=False,
            timeout=10,
        )
        # GitHub returns rc=1 on successful auth ("successfully authenticated")
        ssh_ok = "successfully authenticated" in ssh_result.stderr.lower()
        info["ssh"] = ssh_ok
    except Exception:
        info["ssh"] = False

    # --- Remote reachability (canonical check via git fetch) ---
    try:
        _git(["git", "fetch", "origin", "--dry-run"], repo_path=repo_path, timeout=15)
        info["remote_reachable"] = True
    except Exception as e:
        info["remote_reachable"] = False
        errors.append(f"git fetch origin failed: {e}")

    # --- Token ---
    token = _github_token()
    if token:
        try:
            gh_result = _git(
                ["gh", "auth", "status"],
                repo_path=repo_path,
                env_extra={"GH_TOKEN": token},
                check=False,
                timeout=10,
            )
            if gh_result.returncode == 0:
                info["token"] = True
                # Extract username from "Logged in to github.com account USER"
                for line in gh_result.stdout.splitlines() + gh_result.stderr.splitlines():
                    if "account" in line.lower():
                        parts = line.split("account")
                        if len(parts) > 1:
                            info["token_user"] = parts[1].strip().split()[0].strip("()")
                        break
            else:
                info["token"] = False
                errors.append(f"gh auth status failed: {gh_result.stderr.strip()}")
        except Exception as e:
            info["token"] = False
            errors.append(f"gh auth status error: {e}")
    else:
        info["token"] = False
        errors.append("GITHUB_TOKEN not configured")

    if errors:
        info["ok"] = False
        info["error"] = "; ".join(errors)

    return info


# ---------------------------------------------------------------------------
# Handler: github.create_branch
# ---------------------------------------------------------------------------


def handle_github_create_branch(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a rick/ feature branch from a base.

    Input:
        branch_name (str, required): e.g. "rick/add-github-handlers"
        base (str, optional): base branch, default "main"

    Returns:
        {"ok": True, "branch": "rick/...", "base": "main"}
    """
    try:
        repo_path = _resolve_repo_path()
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    branch_name = input_data.get("branch_name", "")
    try:
        branch_name = _validate_branch_name(branch_name)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    base = (input_data.get("base") or "main").strip()
    try:
        base = _validate_base_name(base)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    try:
        _ensure_clean_worktree(repo_path)
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}

    try:
        _git(["git", "fetch", "origin"], repo_path=repo_path, timeout=30)
        _git(
            ["git", "checkout", "-b", branch_name, f"origin/{base}"],
            repo_path=repo_path,
        )
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "branch": branch_name, "base": base, "repo_path": repo_path}


# ---------------------------------------------------------------------------
# Handler: github.commit_and_push
# ---------------------------------------------------------------------------


def handle_github_commit_and_push(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage explicit files, commit, and push the current branch.

    Input:
        message (str, required): commit message
        files (list[str], required): relative paths to stage (explicit only, no git add -A)
        branch_name (str, optional): expected branch for safety validation

    Returns:
        {"ok": True, "branch": "...", "commit_sha": "...",
         "files_changed": N, "files": [...], "pushed": True}
    """
    message = (input_data.get("message") or "").strip()
    if not message:
        return {"ok": False, "error": "message is required"}

    files = input_data.get("files")
    if not files or not isinstance(files, list) or len(files) == 0:
        return {
            "ok": False,
            "error": "files list is required — explicit staging only, no git add -A",
        }

    try:
        repo_path = _resolve_repo_path()
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    # --- Validate current branch is not protected and has rick/ prefix ---
    try:
        current = _current_branch(repo_path)
    except Exception as e:
        return {"ok": False, "error": f"Cannot read current branch: {e}"}

    if current in _PROTECTED_BRANCHES:
        return {
            "ok": False,
            "error": f"Refusing to commit on protected branch '{current}'",
        }

    if not current.startswith(_BRANCH_PREFIX):
        return {
            "ok": False,
            "error": (
                f"Current branch '{current}' does not start with '{_BRANCH_PREFIX}'. "
                f"Rick can only commit on rick/ branches."
            ),
        }

    expected = (input_data.get("branch_name") or "").strip()
    if expected and expected != current:
        return {
            "ok": False,
            "error": f"Branch mismatch: expected '{expected}', currently on '{current}'",
        }

    # --- Normalize and validate pathspecs ---
    repo_root = Path(repo_path).resolve()
    normalized: List[str] = []
    for f in files:
        f = f.strip()
        if not f:
            continue
        # Resolve relative to repo root
        full = (repo_root / f).resolve()
        # Ensure path stays inside the repo
        try:
            full.relative_to(repo_root)
        except ValueError:
            return {
                "ok": False,
                "error": f"Path escapes repo boundary: '{f}'",
            }
        rel = str(full.relative_to(repo_root))
        # For deletions, the file won't exist on disk but git knows about it.
        # For new/modified files, the file must exist.
        # We let git add handle both cases — git add surfaces the error for truly unknown paths.
        normalized.append(rel)

    if not normalized:
        return {"ok": False, "error": "files list resolved to empty after normalization"}

    try:
        # Stage files — use '--' to separate paths from flags
        _git(["git", "add", "--"] + normalized, repo_path=repo_path)

        # Verify there are actually staged changes
        diff_result = _git(
            ["git", "diff", "--cached", "--stat"], repo_path=repo_path
        )
        if not diff_result.stdout.strip():
            return {
                "ok": False,
                "error": "No staged changes after git add — files may be unchanged",
            }

        _git(["git", "commit", "-m", message], repo_path=repo_path)
        _git(
            ["git", "push", "-u", "origin", current],
            repo_path=repo_path,
            timeout=30,
        )

        sha = _git(
            ["git", "rev-parse", "HEAD"], repo_path=repo_path
        ).stdout.strip()

        # Count files in the commit
        stat = _git(
            ["git", "diff", "--stat", "HEAD~1..HEAD"], repo_path=repo_path
        )
        file_count = max(
            1,
            len([l for l in stat.stdout.strip().splitlines() if "|" in l]),
        )

    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)}

    return {
        "ok": True,
        "branch": current,
        "commit_sha": sha,
        "commit_message": message,
        "files_changed": file_count,
        "files": normalized,
        "pushed": True,
    }


# ---------------------------------------------------------------------------
# Handler: github.open_pr
# ---------------------------------------------------------------------------


def handle_github_open_pr(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Open a Pull Request from the current branch to base.

    PRs and comments appear as UmbralBIM (PAT owner), not as Rick.
    Only git commits carry Rick's identity.

    Input:
        title (str, required): PR title
        body (str, optional): PR description in markdown
        branch_name (str, optional): head branch, defaults to current
        base (str, optional): target branch, default "main"
        bridge_item_name (str, optional): if set, upserts Notion bridge item with PR URL
        linear_issue_id (str, optional): if set, posts PR URL as comment on Linear issue

    Returns:
        {"ok": True, "pr_url": "...", "pr_number": N,
         "branch": "...", "base": "...", "title": "...",
         "traceability": {"notion": ..., "linear": ...}}
    """
    title = (input_data.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "title is required"}

    token = _github_token()
    if not token:
        return {"ok": False, "error": "GITHUB_TOKEN not configured"}

    try:
        repo_path = _resolve_repo_path()
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    # --- Resolve branch ---
    branch = (input_data.get("branch_name") or "").strip()
    if not branch:
        try:
            branch = _current_branch(repo_path)
        except Exception as e:
            return {"ok": False, "error": f"Cannot read current branch: {e}"}

    if branch in _PROTECTED_BRANCHES:
        return {
            "ok": False,
            "error": f"Refusing to open PR from protected branch '{branch}'",
        }

    if not branch.startswith(_BRANCH_PREFIX):
        return {
            "ok": False,
            "error": (
                f"Branch '{branch}' does not start with '{_BRANCH_PREFIX}'. "
                f"Rick can only open PRs from rick/ branches."
            ),
        }

    base = (input_data.get("base") or "main").strip()
    try:
        base = _validate_base_name(base)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    body = (input_data.get("body") or "").strip()

    # --- Create PR via gh CLI ---
    cmd = [
        "gh", "pr", "create",
        "--head", branch,
        "--base", base,
        "--title", title,
    ]
    if body:
        cmd += ["--body", body]
    else:
        cmd += ["--body", ""]

    try:
        pr_result = _git(
            cmd,
            repo_path=repo_path,
            env_extra={"GH_TOKEN": token},
            timeout=30,
        )
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)}

    pr_url = pr_result.stdout.strip()
    pr_number = None
    match = re.search(r"/pull/(\d+)", pr_url)
    if match:
        pr_number = int(match.group(1))

    result: Dict[str, Any] = {
        "ok": True,
        "pr_url": pr_url,
        "pr_number": pr_number,
        "branch": branch,
        "base": base,
        "title": title,
        "traceability": {},
    }

    # --- Explicit traceability: Notion bridge item ---
    bridge_item_name = (input_data.get("bridge_item_name") or "").strip()
    if bridge_item_name and pr_url:
        try:
            from .notion import handle_notion_upsert_bridge_item

            bridge_result = handle_notion_upsert_bridge_item({
                "name": bridge_item_name,
                "link": pr_url,
                "status": "En curso",
                "source": "Rick",
                "notes": f"PR #{pr_number}: {title}" if pr_number else title,
            })
            result["traceability"]["notion"] = bridge_result
        except Exception as e:
            logger.warning("Failed to upsert Notion bridge item: %s", e)
            result["traceability"]["notion"] = {"ok": False, "error": str(e)}

    # --- Explicit traceability: Linear issue comment ---
    linear_issue_id = (input_data.get("linear_issue_id") or "").strip()
    if linear_issue_id and pr_url:
        try:
            from .linear import handle_linear_update_issue_status

            linear_result = handle_linear_update_issue_status({
                "issue_id": linear_issue_id,
                "comment": f"PR abierto: {pr_url}",
            })
            result["traceability"]["linear"] = linear_result
        except Exception as e:
            logger.warning("Failed to post Linear comment: %s", e)
            result["traceability"]["linear"] = {"ok": False, "error": str(e)}

    return result
