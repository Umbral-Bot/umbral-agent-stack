"""Branch-based tournament orchestration — Phase 1 + Phase 2 slices 1–2.

Composes existing primitives (github.create_branch, tournament.run,
github.commit_and_push) into a multi-branch comparison workflow. Each
approach from the tournament gets its own ``rick/t/{id}/{label}`` branch;
the winning approach gets a ``rick/t/{id}/final`` branch.

Phase 1 created the branches as named containers and ran the LLM
tournament for textual comparison.

Phase 2 slice 1 added a structured proposal artifact per contestant:
after the branch is created, a markdown file at
``.rick/tournaments/{tid}/{label}.md`` is written and committed to the
contestant branch.

Phase 2 slice 2 materializes ``final_branch`` when there is a valid
winner: the winner's contestant commit is cherry-picked onto
``rick/t/{tid}/final`` and pushed. Degrades safely to the Phase-1
behaviour (empty ``final_branch`` from base) if no valid winning commit
exists or the cherry-pick fails. Real code generation + validation
(pytest/lint) per contestant remains a future slice.
"""

import datetime
import logging
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .. import config
from .github import (
    handle_github_commit_and_push,
    handle_github_create_branch,
    handle_github_preflight,
)
from .tournament import handle_tournament_run

logger = logging.getLogger("worker.tasks.github_tournament")

# Letters used for contestant branch labels (supports up to 5).
_LABEL_LETTERS = "abcde"

# Subdirectory where contestant proposal artifacts are written inside the
# repo working tree. Intentionally scoped to `.rick/tournaments/` so the
# paths never collide with project source code.
_ARTIFACT_SUBDIR = ".rick/tournaments"


def _generate_tournament_id() -> str:
    """Return an 8-char hex string unique per tournament run."""
    return uuid.uuid4().hex[:8]


def _branch_name(tournament_id: str, label: str) -> str:
    """Contestant branch: ``rick/t/{tournament_id}/{label}``."""
    return f"rick/t/{tournament_id}/{label}"


def _final_branch_name(tournament_id: str) -> str:
    """Final/capitalized branch: ``rick/t/{tournament_id}/final``."""
    return f"rick/t/{tournament_id}/final"


def _checkout_base(branch: str) -> None:
    """Best-effort checkout back to *branch*.  Never raises."""
    try:
        subprocess.run(
            ["git", "checkout", branch],
            cwd=config.GITHUB_REPO_PATH,
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Phase 2 slice 1 — contestant artifact helpers
# ---------------------------------------------------------------------------


def _artifact_rel_path(tournament_id: str, label: str) -> str:
    """Relative path of the proposal artifact inside the repo working tree."""
    return f"{_ARTIFACT_SUBDIR}/{tournament_id}/{label}.md"


def _yaml_quote(value: Any) -> str:
    """Quote a value for safe inclusion in YAML frontmatter.

    Only used for short header fields (names, ids). Not a general-purpose
    YAML serializer — we control the call sites.
    """
    s = str(value if value is not None else "")
    escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def _build_artifact_body(
    *,
    tournament_id: str,
    label: str,
    challenge: str,
    approach: Dict[str, Any],
    created_at: Optional[str] = None,
) -> str:
    """Build the markdown body for a contestant's proposal artifact.

    Includes a YAML frontmatter block with traceability metadata plus a
    human-readable body (challenge + full proposal text, no truncation).
    """
    now = created_at or (
        datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    )
    approach_id = approach.get("id", 0)
    approach_name = approach.get("approach_name", f"Approach {label.upper()}")
    model_used = approach.get("model_used", "")
    proposal = approach.get("proposal", "") or ""

    frontmatter = (
        "---\n"
        f"tournament_id: {_yaml_quote(tournament_id)}\n"
        f"contestant_label: {_yaml_quote(label)}\n"
        f"approach_id: {int(approach_id) if str(approach_id).isdigit() else 0}\n"
        f"approach_name: {_yaml_quote(approach_name)}\n"
        f"model_used: {_yaml_quote(model_used)}\n"
        f"created_at: {_yaml_quote(now)}\n"
        "---\n\n"
    )
    body = (
        f"# Contestant {label.upper()} — {approach_name}\n\n"
        f"## Challenge\n\n{challenge}\n\n"
        f"## Proposal\n\n{proposal}\n"
    )
    return frontmatter + body


def _write_artifact_file(repo_path: str, rel_path: str, body: str) -> None:
    """Write the artifact file in the working tree, creating parent dirs."""
    full = Path(repo_path) / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(body, encoding="utf-8")


def _write_artifact_and_commit(
    *,
    tournament_id: str,
    label: str,
    challenge: str,
    approach: Dict[str, Any],
    branch: str,
) -> Dict[str, Any]:
    """Write the contestant's proposal artifact and commit it on the branch.

    Never raises: any write/commit failure is captured in the returned
    dict so the tournament flow can continue with other contestants.

    Returns:
        {
          "path": "rel/path.md",
          "written": bool,
          "commit": {...}  # result of handle_github_commit_and_push, or
                           # {"ok": False, "error": "..."} on local failure
        }
    """
    rel_path = _artifact_rel_path(tournament_id, label)
    result: Dict[str, Any] = {
        "path": rel_path,
        "written": False,
        "commit": None,
    }

    try:
        body = _build_artifact_body(
            tournament_id=tournament_id,
            label=label,
            challenge=challenge,
            approach=approach,
        )
        _write_artifact_file(config.GITHUB_REPO_PATH, rel_path, body)
        result["written"] = True
    except Exception as exc:
        logger.warning(
            "Artifact write failed for tournament=%s label=%s: %s",
            tournament_id, label, exc,
        )
        result["commit"] = {"ok": False, "error": f"write failed: {str(exc)[:200]}"}
        return result

    try:
        commit_result = handle_github_commit_and_push({
            "message": (
                f"tournament({tournament_id}): contestant {label.upper()} proposal"
            ),
            "files": [rel_path],
            "branch_name": branch,
        })
        result["commit"] = commit_result
    except Exception as exc:
        logger.warning(
            "Artifact commit failed for tournament=%s label=%s: %s",
            tournament_id, label, exc,
        )
        result["commit"] = {"ok": False, "error": f"commit failed: {str(exc)[:200]}"}

    return result


# ---------------------------------------------------------------------------
# Phase 2 slice 2 — final branch materialization (cherry-pick + push)
# ---------------------------------------------------------------------------


def _winner_commit_info(
    *,
    contestants: list,
    winner_id: Any,
) -> tuple[Optional[str], Optional[int]]:
    """Locate the winning contestant's usable commit SHA.

    Args:
        contestants: list of contestant dicts as produced by the
            orchestration loop (each with ``id`` and ``artifact.commit``).
        winner_id: verdict's winner id; accepts int or numeric string.

    Returns:
        A tuple ``(commit_sha, contestant_id)``:
        - ``(sha, cid)`` if the contestant has a successful commit.
        - ``(None, cid)`` if the contestant was found but its commit
          failed (artifact.commit.ok is False or no sha).
        - ``(None, None)`` if ``winner_id`` is missing, non-numeric, or
          no contestant matches.
    """
    if winner_id is None:
        return None, None
    try:
        wid = int(winner_id)
    except (TypeError, ValueError):
        return None, None

    for c in contestants:
        if c.get("id") != wid:
            continue
        artifact = c.get("artifact") or {}
        commit = artifact.get("commit") or {}
        if commit.get("ok"):
            sha = commit.get("commit_sha")
            if sha:
                return sha, wid
        return None, wid
    return None, None


def _cherry_pick_and_push(
    *,
    final_branch: str,
    winner_sha: str,
) -> Dict[str, Any]:
    """Cherry-pick ``winner_sha`` onto the currently checked-out branch
    and push it upstream.

    Assumes ``handle_github_create_branch`` already checked out
    ``final_branch`` in the worktree. Never raises: any failure is
    captured in the returned dict and the worktree is left clean
    (aborts an in-progress cherry-pick on conflict).

    Returns:
        {
          "cherry_picked": bool,
          "pushed": bool,
          "error": str | None,
        }
    """
    try:
        cp = subprocess.run(
            ["git", "cherry-pick", winner_sha],
            cwd=config.GITHUB_REPO_PATH,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return {
            "cherry_picked": False,
            "pushed": False,
            "error": "cherry-pick timeout",
        }
    except Exception as exc:
        return {
            "cherry_picked": False,
            "pushed": False,
            "error": f"cherry-pick error: {str(exc)[:200]}",
        }

    if cp.returncode != 0:
        try:
            subprocess.run(
                ["git", "cherry-pick", "--abort"],
                cwd=config.GITHUB_REPO_PATH,
                capture_output=True,
                timeout=30,
            )
        except Exception:
            pass
        return {
            "cherry_picked": False,
            "pushed": False,
            "error": f"cherry-pick failed: {cp.stderr.strip()[:200]}",
        }

    try:
        push = subprocess.run(
            ["git", "push", "-u", "origin", final_branch],
            cwd=config.GITHUB_REPO_PATH,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {
            "cherry_picked": True,
            "pushed": False,
            "error": "push timeout",
        }
    except Exception as exc:
        return {
            "cherry_picked": True,
            "pushed": False,
            "error": f"push error: {str(exc)[:200]}",
        }

    if push.returncode != 0:
        return {
            "cherry_picked": True,
            "pushed": False,
            "error": f"push failed: {push.stderr.strip()[:200]}",
        }

    return {"cherry_picked": True, "pushed": True, "error": None}


def handle_github_orchestrate_tournament(
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Orchestrate a branch-based tournament for a development assignment.

    Flow:
        1. Preflight check (clean worktree, SSH, token).
        2. Run LLM tournament (discovery → develop → debate → judge).
        3. For each approach: create contestant branch + persist
           proposal artifact + commit (Phase 2 slice 1).
        4. If there is a valid winner (not ESCALATE, winner_id set):
           create final branch, cherry-pick the winner's commit onto
           it, push upstream (Phase 2 slice 2). Degrades to an empty
           final branch with an explicit error if the cherry-pick
           preconditions are not met.
        5. Return to base branch.
        6. Return structured result.

    Args (via *input_data*):
        challenge (str, required): development assignment description.
        base (str): base branch, default ``"main"``.
        num_approaches (int): contestants (2-5), default 3.
        approaches (list[str]): predefined names (skips LLM discovery).
        models (list[str]): LLM models for contestants.
        judge_model (str): model for judge consolidation.
        debate_rounds (int): default 1.
        temperature (float): default 0.9.
        max_tokens (int): default 2048.

    Returns:
        ok, tournament_id, challenge, base, contestants,
        verdict, final_branch, final_result, branches_created, meta.
    """
    t0 = time.time()

    challenge = (input_data.get("challenge") or "").strip()
    if not challenge:
        raise ValueError("challenge is required")

    base = input_data.get("base", "main").strip()
    tournament_id = _generate_tournament_id()

    # ---- 1. Preflight ----
    preflight = handle_github_preflight({})
    if not preflight.get("ok"):
        return {
            "ok": False,
            "error": "Preflight failed",
            "tournament_id": tournament_id,
            "preflight": preflight,
        }
    if not preflight.get("clean"):
        return {
            "ok": False,
            "error": "Working copy has uncommitted changes",
            "tournament_id": tournament_id,
        }

    # ---- 2. Run tournament (pure LLM, no git) ----
    tourn_input: Dict[str, Any] = {
        "challenge": challenge,
        "num_approaches": input_data.get("num_approaches", 3),
        "debate_rounds": input_data.get("debate_rounds", 1),
        "temperature": input_data.get("temperature", 0.9),
        "max_tokens": input_data.get("max_tokens", 2048),
    }
    for key in ("approaches", "models", "judge_model"):
        if key in input_data:
            tourn_input[key] = input_data[key]

    tournament = handle_tournament_run(tourn_input)

    approaches = tournament.get("approaches", [])
    verdict = tournament.get("verdict", {})

    # ---- 3. Create contestant branches ----
    contestants = []
    branches_created: list[str] = []

    try:
        for i, approach in enumerate(approaches):
            label = _LABEL_LETTERS[i] if i < len(_LABEL_LETTERS) else str(i)
            branch = _branch_name(tournament_id, label)

            br_result = handle_github_create_branch(
                {"branch_name": branch, "base": base},
            )

            if not br_result.get("ok"):
                return {
                    "ok": False,
                    "error": (
                        f"Failed to create branch {branch}: "
                        f"{br_result.get('error')}"
                    ),
                    "tournament_id": tournament_id,
                    "branches_created": branches_created,
                }

            branches_created.append(branch)

            # Phase 2 slice 1: persist a structured proposal artifact per
            # contestant on its branch. Failures here do NOT abort the
            # tournament — the contestant is reported with artifact.commit.ok
            # = False so downstream consumers can see what happened.
            artifact = _write_artifact_and_commit(
                tournament_id=tournament_id,
                label=label,
                challenge=challenge,
                approach=approach,
                branch=branch,
            )

            contestants.append({
                "id": approach.get("id", i + 1),
                "approach": approach.get("approach_name", f"Approach {label.upper()}"),
                "branch": branch,
                "proposal_excerpt": (approach.get("proposal") or "")[:500],
                "artifact": artifact,
            })

        # ---- 4. Create final branch + cherry-pick the winner ----
        # (Phase 2 slice 2)
        #
        # Safe preconditions for cherry-pick:
        #   - verdict has a winner_id
        #   - verdict is not ESCALATE
        #   - the winning contestant has a successful commit from slice 1
        #   - the final branch was created cleanly
        #
        # Any missing precondition degrades to the Phase-1 behaviour
        # (final branch created from base with no commits), with an
        # explicit reason surfaced via `final_result.error`.
        final_branch = None
        final_result: Optional[Dict[str, Any]] = None
        if not verdict.get("escalate") and verdict.get("winner_id") is not None:
            winner_sha, winner_cid = _winner_commit_info(
                contestants=contestants,
                winner_id=verdict.get("winner_id"),
            )
            fb = _final_branch_name(tournament_id)
            fb_result = handle_github_create_branch(
                {"branch_name": fb, "base": base},
            )
            if fb_result.get("ok"):
                final_branch = fb
                branches_created.append(fb)

                final_result = {
                    "cherry_picked": False,
                    "pushed": False,
                    "from_commit_sha": winner_sha,
                    "from_contestant_id": winner_cid,
                    "error": None,
                }
                if not winner_sha:
                    final_result["error"] = (
                        "winner has no valid commit to cherry-pick"
                    )
                else:
                    cp = _cherry_pick_and_push(
                        final_branch=fb,
                        winner_sha=winner_sha,
                    )
                    final_result["cherry_picked"] = cp["cherry_picked"]
                    final_result["pushed"] = cp["pushed"]
                    final_result["error"] = cp.get("error")

    finally:
        _checkout_base(base)

    return {
        "ok": True,
        "tournament_id": tournament_id,
        "challenge": challenge,
        "base": base,
        "contestants": contestants,
        "verdict": {
            "text": verdict.get("text", ""),
            "winner_id": verdict.get("winner_id"),
            "escalate": verdict.get("escalate", False),
        },
        "final_branch": final_branch,
        "final_result": final_result,
        "branches_created": branches_created,
        "meta": {
            "total_llm_calls": tournament.get("meta", {}).get(
                "total_llm_calls", 0,
            ),
            "total_duration_ms": int((time.time() - t0) * 1000),
            "models_used": tournament.get("meta", {}).get("models_used", []),
        },
    }
