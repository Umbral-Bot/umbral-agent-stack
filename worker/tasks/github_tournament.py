"""Branch-based tournament orchestration — Phase 1 + Phase 2 slice 1.

Composes existing primitives (github.create_branch, tournament.run,
github.commit_and_push) into a multi-branch comparison workflow. Each
approach from the tournament gets its own ``rick/t/{id}/{label}`` branch;
the winning approach gets a ``rick/t/{id}/final`` branch.

Phase 1 created the branches as named containers and ran the LLM
tournament for textual comparison.

Phase 2 slice 1 adds a structured proposal artifact per contestant:
after the branch is created, a markdown file at
``.rick/tournaments/{tid}/{label}.md`` is written and committed to the
contestant branch. This gives reviewers a persistent, diffable record
per branch. Real code generation + validation (pytest/lint) per
contestant remains a future slice.
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
