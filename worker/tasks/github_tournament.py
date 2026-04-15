"""Branch-based tournament orchestration — Phase 1.

Composes existing primitives (github.create_branch, tournament.run)
into a multi-branch comparison workflow.  Each approach from the
tournament gets its own ``rick/t/{id}/{label}`` branch; the winning
approach gets a ``rick/t/{id}/final`` branch.

Phase 1 creates branches as named containers and runs the LLM
tournament for comparison.  Actual code generation on branches is
planned for Phase 2+.
"""

import subprocess
import time
import uuid
from typing import Any, Dict

from .. import config
from .github import handle_github_create_branch, handle_github_preflight
from .tournament import handle_tournament_run

# Letters used for contestant branch labels (supports up to 5).
_LABEL_LETTERS = "abcde"


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


def handle_github_orchestrate_tournament(
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Orchestrate a branch-based tournament for a development assignment.

    Flow (Phase 1):
        1. Preflight check (clean worktree, SSH, token).
        2. Run LLM tournament (discovery → develop → debate → judge).
        3. Create a contestant branch per approach.
        4. If winner identified, create a final branch.
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
        verdict, final_branch, branches_created, meta.
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
            contestants.append({
                "id": approach.get("id", i + 1),
                "approach": approach.get("approach_name", f"Approach {label.upper()}"),
                "branch": branch,
                "proposal_excerpt": (approach.get("proposal") or "")[:500],
            })

        # ---- 4. Create final branch if winner ----
        final_branch = None
        if not verdict.get("escalate") and verdict.get("winner_id") is not None:
            fb = _final_branch_name(tournament_id)
            fb_result = handle_github_create_branch(
                {"branch_name": fb, "base": base},
            )
            if fb_result.get("ok"):
                final_branch = fb
                branches_created.append(fb)

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
        "branches_created": branches_created,
        "meta": {
            "total_llm_calls": tournament.get("meta", {}).get(
                "total_llm_calls", 0,
            ),
            "total_duration_ms": int((time.time() - t0) * 1000),
            "models_used": tournament.get("meta", {}).get("models_used", []),
        },
    }
