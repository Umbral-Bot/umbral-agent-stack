"""Branch-based tournament orchestration — Phase 1 + Phase 2 slices 1–7a.

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
exists or the cherry-pick fails.

Phase 2 slice 3 hardened the judge output contract (final-line winner
or ``ESCALATE``).

Phase 2 slice 4 adds an OPT-IN first step towards real code changes per
contestant. When ``input_data["generate_code"]`` is ``True``:
 - after the markdown artifact is committed, each contestant is asked
   to emit exactly one file block (FILE: <rel_path>\\n```lang\\n...\\n```),
 - the file path is constrained to
   ``.rick/contestants/{tid}/{label}/...`` (sandboxed),
 - the file is written and committed on the contestant branch,
 - ``_winner_commit_info`` prefers the code-change commit over the
   markdown artifact commit when picking what to cherry-pick.

When the flag is absent or ``False`` the behaviour is byte-identical to
slices 1–3. Real pytest-per-contestant, multi-file changes and
execution sandboxes are intentionally out of scope for slice 4.

Phase 2 slice 4b extends slice 4a with an OPT-IN ``target_file`` field
in the input. When ``generate_code=True`` AND ``target_file`` is set,
each contestant is asked to modify THAT specific real-repo path
instead of emitting a sandboxed file. The LLM must emit a FILE block
whose path equals ``target_file`` byte-for-byte; anything else is
rejected. ``target_file`` is validated up front against a denylist of
protected prefixes (``.git/``, ``.github/``, ``.rick/``, ...) and an
allowlist of extensions so a single invalid input can't produce bad
branches. Multi-file changes, pytest-per-contestant and execution
sandboxes remain out of scope.

Phase 2 slice 5 adds OPT-IN per-contestant validation. When
``validation_mode="python_compile"`` is set AND the contestant actually
emitted a real ``.py`` file (slice 4b), the tournament runs
``python3 -m py_compile <target_file>`` with a bounded timeout and
records pass/fail, duration and a short stderr tail per contestant.
The command is hardcoded (no free command, no shell, argv list) and
the rel_path has already passed slice-4b validation. Validation is
observational in this slice: the judge itself is NOT re-run; failing
contestants are marked in the output but not disqualified. Real
pytest per contestant and general execution sandboxing remain out of
scope.

Phase 2 slice 6 adds OPT-IN re-judging AFTER validation. When
``rejudge=True`` is set, the handler runs a second judge pass that
sees the enriched per-contestant evidence (proposal + branch +
code_change status + validation status) instead of deciding only on
textual proposals. The same machine-parsed final-line contract from
slice 3 is enforced, so ``_extract_winner_id`` is reused without
modification. The initial verdict from ``tournament.run`` is kept as
shadow info in ``verdict_initial`` for traceability; the re-judge
verdict drives the cherry-pick. Failing contestants are biased
against in the prompt but not filtered out — if the re-judge picks a
contestant that failed validation while others passed, the output
marks ``rejudge.override_attempt=True`` for human review without
silently overriding the judge. ``tournament.py`` is intentionally
NOT modified; the re-judge lives entirely inside
``github_tournament.py`` so slice 6 is additive and its blast radius
is scoped to a single module. Automatic disqualification, pytest
per contestant and execution sandboxing remain out of scope.

Phase 2 slice 7a adds a third OPT-IN validation mode,
``python_ast_lint``, that sits between ``python_compile`` and a real
``pytest_target`` (deferred until sandbox infra exists). It runs a
fixed static analyzer over the target file via
``python3 -I -c <fixed script> <target_file>``: the script is a
literal constant, uses only ``ast.parse`` + an ``ast.NodeVisitor``,
and NEVER imports nor executes the target. On top of catching
``SyntaxError`` it also flags duplicate top-level functions/classes
(excluding ``@overload``) and stray ``return``/``yield``/``await``
outside function scope. It keeps the same input contract
(``validation_mode`` + ``validation_timeout_s``), the same
``validation`` output shape, the same never-raises discipline and the
same observational policy (failing contestants are reported but not
disqualified).

Phase 2 slice 7b adds the fourth OPT-IN validation mode,
``pytest_target``, which actually runs pytest against a conventional
test file for the contestant's target_file. It reuses the sandbox
infrastructure landed in slice 7b-infra (``worker/sandbox/``):

  * a deterministic Docker image tag derived from
    ``sha256(pyproject.toml)[:12]``,
  * a versioned allowlist of tests that may be used as a
    ``validation_target``,
  * an ephemeral per-tournament workspace under ``tempfile.gettempdir()``
    built via selective copy (no ``.git``, no ``.rick``, no
    ``.venv``, no ``.env*``, no ``__pycache__``, no symlinks),
  * a single fixed ``docker run`` argv (``--network=none``,
    ``--read-only``, ``--cap-drop=ALL``,
    ``--security-opt=no-new-privileges``, ``--user 10001:10001``,
    ``--memory=512m``, ``--cpus=1.0``, ``--pids-limit=256``,
    ``--ipc=none``, a single writable ``/tmp`` tmpfs, stripped env).

Per contestant the handler derives ``tests/test_<stem>.py`` (or its
``_handler`` variant) from ``target_file``, looks it up in the
allowlist, reads the contestant's modified file via
``git show <contestant_sha>:<target_file>``, overwrites it in the
workspace, and invokes pytest inside the container. Everything
stays observational for this slice: failing contestants are marked
in ``validation.passed`` but NOT disqualified; the rejudge pass
from slice 6 consumes the same ``validation.*`` schema, so it
automatically picks up pytest evidence without any prompt changes.
Prerequisite failures (docker missing, image missing, allowlist
empty, no resolvable target, workspace build failure) degrade
gracefully to ``validation.ran=False`` with a descriptive error
per contestant — the tournament itself never aborts. Automatic
disqualification is deliberately deferred to a later slice.
"""

import datetime
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .. import config
from ..sandbox import (
    build_workspace,
    cleanup_workspace,
    load_test_allowlist,
    overwrite_file_in_workspace,
    resolve_validation_target,
)
from .github import (
    handle_github_commit_and_push,
    handle_github_create_branch,
    handle_github_preflight,
)
from .llm import handle_llm_generate
from .tournament import _extract_winner_id, handle_tournament_run

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
# Phase 2 slice 4 — single-file code-change helpers (opt-in)
# ---------------------------------------------------------------------------

# Sandbox directory for contestant-generated code. Paths MUST start with
# ``.rick/contestants/{tid}/{label}/`` — this keeps slice-4 output well
# away from real project source code until later slices relax it.
_CODE_SUBDIR = ".rick/contestants"

# Hard cap on the size of the file a contestant can emit. Prevents
# accidental token dumps from bloating the branch.
_CODE_MAX_BYTES = 100 * 1024

# Characters allowed in the relative path emitted by the LLM. Nothing
# exotic — only the subset needed for typical source file names.
_PATH_CHARSET_RE = re.compile(r"^[A-Za-z0-9._/-]+$")

# Slice 4b: path prefixes that a ``target_file`` is NEVER allowed to
# touch. Keeps the tournament subsystem, git metadata, CI config and
# environment/virtualenv directories safe by construction.
_TARGET_FILE_DENY_PREFIXES = (
    ".git/",
    ".github/",
    ".rick/",
    ".venv/",
    "venv/",
    "node_modules/",
    "__pycache__/",
)

# Slice 4b: conservative extension allowlist for ``target_file``.
# Intentionally narrow; can be relaxed in later slices once we have
# pytest-per-contestant and execution sandboxing.
_TARGET_FILE_ALLOWED_EXTS = (
    ".py", ".md", ".txt", ".json",
    ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".sh",
)

# Parser for the single ``FILE: <path>\n```lang\n<content>\n``` `` block.
# The path is captured up to end-of-line (non-greedy, ignoring trailing
# spaces) so that malformed paths — including ones with spaces — still
# reach the charset / sandbox validators below and get a meaningful
# error message instead of a generic "malformed".
_FILE_BLOCK_RE = re.compile(
    r"(?s)^FILE:[ \t]+(?P<path>[^\n]+?)[ \t]*\n"
    r"```[^\n]*\n"
    r"(?P<content>.*?)"
    r"```"
)


def _code_prefix(tournament_id: str, label: str) -> str:
    """Mandatory path prefix for a contestant's code artifact."""
    return f"{_CODE_SUBDIR}/{tournament_id}/{label}/"


def _validate_target_file(target_file: Any) -> Dict[str, Any]:
    """Validate a slice-4b ``target_file`` input value.

    Applies the same path rules as slice 4a (no absolute, no ``..``,
    charset allowlist) plus two extra layers:

      * Denylist of protected prefixes (``.git/``, ``.github/``,
        ``.rick/``, ``.venv/``, ``venv/``, ``node_modules/``,
        ``__pycache__/``).
      * Extension allowlist (``.py``, ``.md``, ``.txt``, ``.json``,
        ``.yaml``, ``.yml``, ``.toml``, ``.ini``, ``.cfg``, ``.sh``).

    Returns ``{"ok": bool, "normalized": str | None, "error": str | None}``.
    Never raises.
    """
    if target_file is None:
        return {"ok": False, "normalized": None,
                "error": "target_file is required for slice 4b"}
    if not isinstance(target_file, str):
        return {"ok": False, "normalized": None,
                "error": "target_file must be a string"}

    tf = target_file.strip()
    if not tf:
        return {"ok": False, "normalized": None,
                "error": "target_file must not be empty"}

    if tf.startswith("/"):
        return {"ok": False, "normalized": None,
                "error": "target_file must be a relative path"}

    parts = tf.split("/")
    if any(p in ("", "..", ".") for p in parts):
        return {"ok": False, "normalized": None,
                "error": "target_file must not contain '..', '.' or empty segments"}

    if not _PATH_CHARSET_RE.match(tf):
        return {"ok": False, "normalized": None,
                "error": "target_file contains forbidden characters"}

    for deny in _TARGET_FILE_DENY_PREFIXES:
        if tf.startswith(deny):
            return {"ok": False, "normalized": None,
                    "error": f"target_file is under a protected prefix: '{deny}'"}

    lower = tf.lower()
    if not any(lower.endswith(ext) for ext in _TARGET_FILE_ALLOWED_EXTS):
        return {
            "ok": False,
            "normalized": None,
            "error": (
                "target_file extension not allowed "
                f"(allowed: {', '.join(_TARGET_FILE_ALLOWED_EXTS)})"
            ),
        }

    return {"ok": True, "normalized": tf, "error": None}


def _build_code_prompt(
    *,
    tournament_id: str,
    label: str,
    idx: int,
    approach_name: str,
    challenge: str,
    proposal: str,
    target_file: Optional[str] = None,
) -> Dict[str, str]:
    """Build (system, user) prompts instructing the LLM to emit exactly
    one FILE block.

    If ``target_file`` is given (slice 4b), the prompt forces the path
    to equal that value byte-for-byte. Otherwise (slice 4a) the prompt
    forces the path to live under the contestant's sandbox prefix.
    """
    if target_file:
        path_rule = (
            f"- <relative_path> MUST equal exactly: {target_file}\n"
            "- Do NOT change the path, do NOT add suffixes or subdirs.\n"
        )
        task_tail = (
            f"Now produce the single-file code change to `{target_file}` that "
            "implements this proposal, following the FILE block format exactly."
        )
    else:
        prefix = _code_prefix(tournament_id, label)
        path_rule = (
            f"- <relative_path> MUST start with: {prefix}\n"
        )
        task_tail = (
            "Now produce the single-file code change that implements this "
            "proposal, following the FILE block format exactly."
        )

    system = (
        f"You are Contestant #{idx} implementing your approved approach.\n"
        f"Approach: {approach_name}\n\n"
        "You must deliver your change as EXACTLY ONE FILE, emitted in\n"
        "the following literal format and NOTHING ELSE:\n\n"
        "FILE: <relative_path>\n"
        "```<language>\n"
        "<full file content>\n"
        "```\n\n"
        "STRICT RULES (machine-parsed):\n"
        + path_rule +
        "- <relative_path> MUST NOT contain '..' components.\n"
        "- <relative_path> MUST NOT start with '/'.\n"
        "- Use only characters [A-Za-z0-9._/-] in the path.\n"
        "- Emit the COMPLETE content of the file (not a diff, not a patch).\n"
        "- Emit EXACTLY ONE FILE block. No prose before or after. No second\n"
        "  FILE block. No commentary outside the code fence.\n"
        "- Keep the file under 100 KB.\n"
    )
    user = (
        f"Challenge:\n{challenge}\n\n"
        f"Your previous textual proposal (for context):\n{proposal}\n\n"
        + task_tail
    )
    return {"system": system, "user": user}


def _parse_file_block(
    text: str,
    *,
    expected_prefix: Optional[str] = None,
    expected_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse the single FILE block from a slice-4 LLM response.

    Exactly one of ``expected_prefix`` (slice 4a — path must start with
    prefix) or ``expected_path`` (slice 4b — path must equal target
    byte-for-byte) must be provided.

    Returns a dict with shape:
      {"ok": bool, "path": str | None, "content": str | None,
       "error": str | None}

    Rejects the response if:
      - no FILE block is found,
      - more than one ``FILE:`` header appears,
      - path fails the prefix/exact match, absolute/traversal or
        charset checks,
      - content exceeds the size cap.

    Never raises.
    """
    if expected_prefix is None and expected_path is None:
        return {"ok": False, "path": None, "content": None,
                "error": "parser misconfigured: need prefix or exact path"}
    if expected_prefix is not None and expected_path is not None:
        return {"ok": False, "path": None, "content": None,
                "error": "parser misconfigured: pass only one of prefix/exact"}

    if not isinstance(text, str) or not text.strip():
        return {"ok": False, "path": None, "content": None,
                "error": "empty response"}

    # Reject multiple FILE headers outright — contract says exactly one.
    header_count = len(re.findall(r"(?m)^FILE:\s*\S+", text))
    if header_count == 0:
        return {"ok": False, "path": None, "content": None,
                "error": "no FILE block found"}
    if header_count > 1:
        return {"ok": False, "path": None, "content": None,
                "error": "multiple FILE blocks not allowed"}

    m = _FILE_BLOCK_RE.search(text)
    if m is None:
        return {"ok": False, "path": None, "content": None,
                "error": "FILE block malformed"}

    rel_path = m.group("path").strip()
    content = m.group("content")

    # Path validation — prefix (slice 4a) or exact (slice 4b).
    if expected_path is not None:
        if rel_path != expected_path:
            return {"ok": False, "path": rel_path, "content": None,
                    "error": f"path must equal exactly '{expected_path}'"}
    else:
        if not rel_path.startswith(expected_prefix):
            return {"ok": False, "path": rel_path, "content": None,
                    "error": f"path must start with '{expected_prefix}'"}

    if rel_path.startswith("/"):
        return {"ok": False, "path": rel_path, "content": None,
                "error": "absolute path not allowed"}
    parts = rel_path.split("/")
    if any(p in ("", "..", ".") for p in parts):
        return {"ok": False, "path": rel_path, "content": None,
                "error": "path must not contain '..' or '.' or empty segments"}
    if not _PATH_CHARSET_RE.match(rel_path):
        return {"ok": False, "path": rel_path, "content": None,
                "error": "path contains forbidden characters"}

    # Size cap
    try:
        size = len(content.encode("utf-8"))
    except Exception:
        size = len(content)
    if size > _CODE_MAX_BYTES:
        return {"ok": False, "path": rel_path, "content": None,
                "error": f"content exceeds {_CODE_MAX_BYTES} bytes"}

    return {"ok": True, "path": rel_path, "content": content, "error": None}


def _resolve_inside_sandbox(
    repo_path: str,
    rel_path: str,
    expected_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    """Defense-in-depth: canonical-resolve the target path and confirm
    it lives inside ``<repo>`` (and, if ``expected_prefix`` is given,
    inside ``<repo>/<expected_prefix>``).

    In slice 4a the prefix is a contestant sandbox subdir. In slice 4b
    the contestant is allowed to touch a real repo file, so
    ``expected_prefix`` is ``None`` and the only constraint is that
    the resolved target stays inside the repo root.

    Returns ``{"ok": True, "abs_path": Path}`` on success or
    ``{"ok": False, "error": str}`` on failure. Never raises.
    """
    try:
        repo = Path(repo_path).resolve()
        target = (repo / rel_path).resolve()
        if expected_prefix is not None:
            sandbox_root = (repo / expected_prefix).resolve()
        else:
            sandbox_root = repo
    except Exception as exc:
        return {"ok": False,
                "error": f"path resolution failed: {str(exc)[:120]}"}

    try:
        target.relative_to(sandbox_root)
    except ValueError:
        scope = "sandbox" if expected_prefix is not None else "repository"
        return {"ok": False,
                "error": f"resolved path escapes the {scope}"}
    return {"ok": True, "abs_path": target}


def _generate_and_commit_code_change(
    *,
    tournament_id: str,
    label: str,
    idx: int,
    approach: Dict[str, Any],
    challenge: str,
    branch: str,
    judge_model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    target_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Ask the LLM for a single-file code change, validate it, write it
    and commit it on the contestant branch.

    If ``target_file`` is None (slice 4a), the contestant must emit a
    file under ``.rick/contestants/{tid}/{label}/``. If ``target_file``
    is set (slice 4b), the contestant must emit a FILE block whose
    path equals ``target_file`` byte-for-byte; the file is written as
    an overwrite / creation on that real repo path.

    Never raises: any failure (LLM error, parse error, sandbox escape,
    write error, commit error) is captured in the returned dict. On
    failure the working tree is left untouched (the file is only
    written after all validations pass, and the commit step is the
    project's own ``handle_github_commit_and_push``).

    Returns a dict shaped:
      {
        "attempted": True,
        "mode": "target_file" | "sandbox",
        "target_file": str | None,
        "path": str | None,
        "written": bool,
        "parse_error": str | None,
        "commit": dict | None,
      }
    """
    mode = "target_file" if target_file else "sandbox"
    result: Dict[str, Any] = {
        "attempted": True,
        "mode": mode,
        "target_file": target_file,
        "path": None,
        "written": False,
        "parse_error": None,
        "commit": None,
    }

    approach_name = approach.get("approach_name", f"Approach {label.upper()}")
    proposal = approach.get("proposal", "") or ""
    model = (
        approach.get("model_used")
        or judge_model
        or "azure_foundry"
    )

    prompts = _build_code_prompt(
        tournament_id=tournament_id,
        label=label,
        idx=idx,
        approach_name=approach_name,
        challenge=challenge,
        proposal=proposal,
        target_file=target_file,
    )

    # --- LLM call ---
    try:
        llm_out = handle_llm_generate({
            "prompt": prompts["user"],
            "system": prompts["system"],
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
    except Exception as exc:
        logger.warning(
            "Code generation LLM call failed tid=%s label=%s: %s",
            tournament_id, label, exc,
        )
        result["parse_error"] = f"llm error: {str(exc)[:200]}"
        return result

    text = llm_out.get("text", "") if isinstance(llm_out, dict) else ""

    # --- Parse ---
    if target_file:
        parsed = _parse_file_block(text, expected_path=target_file)
        resolve_prefix = None
    else:
        prefix = _code_prefix(tournament_id, label)
        parsed = _parse_file_block(text, expected_prefix=prefix)
        resolve_prefix = prefix
    if not parsed["ok"]:
        result["parse_error"] = parsed["error"]
        result["path"] = parsed.get("path")
        return result

    # --- Defense-in-depth sandbox / repo-scope check ---
    sandbox = _resolve_inside_sandbox(
        config.GITHUB_REPO_PATH, parsed["path"], resolve_prefix,
    )
    if not sandbox["ok"]:
        result["parse_error"] = sandbox["error"]
        result["path"] = parsed["path"]
        return result

    # --- Write file ---
    abs_path: Path = sandbox["abs_path"]
    try:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(parsed["content"], encoding="utf-8")
        result["written"] = True
        result["path"] = parsed["path"]
    except Exception as exc:
        logger.warning(
            "Code-change write failed tid=%s label=%s: %s",
            tournament_id, label, exc,
        )
        result["parse_error"] = f"write failed: {str(exc)[:200]}"
        result["path"] = parsed["path"]
        return result

    # --- Commit ---
    try:
        commit = handle_github_commit_and_push({
            "message": (
                f"tournament({tournament_id}): contestant {label.upper()} code change"
            ),
            "files": [parsed["path"]],
            "branch_name": branch,
        })
        result["commit"] = commit
    except Exception as exc:
        logger.warning(
            "Code-change commit failed tid=%s label=%s: %s",
            tournament_id, label, exc,
        )
        result["commit"] = {"ok": False,
                            "error": f"commit failed: {str(exc)[:200]}"}

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
            orchestration loop.  Each may carry an ``artifact.commit``
            (slice 1) and/or a ``code_change.commit`` (slice 4).
        winner_id: verdict's winner id; accepts int or numeric string.

    Preference order:
      1. ``code_change.commit.commit_sha`` if present and ``ok``.
      2. ``artifact.commit.commit_sha`` if present and ``ok``.
      3. ``(None, cid)`` if the contestant exists but has no usable
         commit.
      4. ``(None, None)`` if ``winner_id`` is missing, non-numeric, or
         no contestant matches.

    This preference was introduced by slice 4 so that when a contestant
    produced a real code change, the final branch cherry-picks that
    change instead of the markdown artifact. When ``generate_code`` is
    off (the default), ``code_change`` is absent and the behaviour is
    identical to slice 2.
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

        code_change = c.get("code_change") or {}
        code_commit = code_change.get("commit") or {}
        if code_commit.get("ok"):
            sha = code_commit.get("commit_sha")
            if sha:
                return sha, wid

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


# ---------------------------------------------------------------------------
# Phase 2 slice 5 — per-contestant validation (opt-in, observational)
# ---------------------------------------------------------------------------

# Narrow allowlist. `none` is the retrocompat default; `python_compile`
# runs a fixed `python3 -m py_compile <target_file>` per contestant;
# `python_ast_lint` runs a fixed static analyzer (no imports, no
# execution of contestant code) on top of `ast.parse`.
_VALIDATION_MODES = (
    "none", "python_compile", "python_ast_lint", "pytest_target",
)

# Phase 2 slice 7b — pytest_target specifics.
# The image ref is computed on the fly from sha256(pyproject.toml),
# matching ``worker/sandbox/refresh.sh``.
_SANDBOX_IMAGE_NAME = "umbral-sandbox-pytest"
# Per-contestant budget specifically for pytest_target. Applied only
# when the caller did NOT pass ``validation_timeout_s`` explicitly.
# Capped by the global ``_VALIDATION_MAX_TIMEOUT_S`` just like every
# other mode.
_PYTEST_TARGET_DEFAULT_TIMEOUT_S = 45
# Timeout for the one-shot ``git show <ref>:<path>`` step used to
# read the contestant's version of ``target_file``. Always small.
_GIT_SHOW_TIMEOUT_S = 15
# Timeout for ``docker image inspect`` called during preparation.
_DOCKER_INSPECT_TIMEOUT_S = 10

# Default timeout for a single contestant's validation run.
_VALIDATION_DEFAULT_TIMEOUT_S = 20

# Hard cap so a misconfigured input can never stall the worker.
_VALIDATION_MAX_TIMEOUT_S = 60

# Log tail budget — enough to see one SyntaxError + context, not more.
_VALIDATION_LOG_TAIL_LINES = 20
_VALIDATION_LOG_TAIL_MAX_CHARS = 2000


def _validate_validation_mode(value: Any) -> Dict[str, Any]:
    """Validate the ``validation_mode`` input.

    Returns ``{"ok": True, "normalized": "none"|"python_compile"|
    "python_ast_lint"}`` or ``{"ok": False, "error": str}``. Treats
    absent/empty/None as ``"none"``. Never raises.
    """
    if value is None or value == "":
        return {"ok": True, "normalized": "none", "error": None}
    if not isinstance(value, str):
        return {"ok": False, "normalized": None,
                "error": "validation_mode must be a string"}
    v = value.strip().lower()
    if v not in _VALIDATION_MODES:
        return {
            "ok": False,
            "normalized": None,
            "error": (
                f"invalid validation_mode '{value}' "
                f"(allowed: {', '.join(_VALIDATION_MODES)})"
            ),
        }
    return {"ok": True, "normalized": v, "error": None}


def _validate_validation_timeout(value: Any) -> Dict[str, Any]:
    """Validate ``validation_timeout_s`` input.

    Accepts positive int/float up to ``_VALIDATION_MAX_TIMEOUT_S``.
    Absent value resolves to ``_VALIDATION_DEFAULT_TIMEOUT_S``. Never
    raises.
    """
    if value is None:
        return {"ok": True, "normalized": _VALIDATION_DEFAULT_TIMEOUT_S,
                "error": None}
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return {"ok": False, "normalized": None,
                "error": "validation_timeout_s must be a number"}
    if value <= 0:
        return {"ok": False, "normalized": None,
                "error": "validation_timeout_s must be positive"}
    normalized = min(float(value), float(_VALIDATION_MAX_TIMEOUT_S))
    return {"ok": True, "normalized": normalized, "error": None}


def _tail_log(text: str) -> str:
    """Return the last ``_VALIDATION_LOG_TAIL_LINES`` lines of ``text``,
    capped to ``_VALIDATION_LOG_TAIL_MAX_CHARS`` characters.
    """
    if not text:
        return ""
    lines = text.splitlines()
    tail = "\n".join(lines[-_VALIDATION_LOG_TAIL_LINES:])
    if len(tail) > _VALIDATION_LOG_TAIL_MAX_CHARS:
        tail = tail[-_VALIDATION_LOG_TAIL_MAX_CHARS:]
    return tail


def _run_python_compile_validation(
    *,
    repo_path: str,
    rel_path: str,
    timeout_s: float,
) -> Dict[str, Any]:
    """Run ``python3 -m py_compile <rel_path>`` inside ``repo_path``.

    The command is fixed — argv list, no shell, no string interpolation
    into the command. ``rel_path`` has already passed slice-4b input
    validation (charset, denylist, no traversal, resolves inside the
    repo) before a single byte was written. This helper never raises:
    timeout, process errors and non-zero exit codes are all captured
    in the returned dict.

    Returns:
        {
          "ran": True,
          "mode": "python_compile",
          "passed": bool,
          "duration_ms": int,
          "log_tail": str,
          "error": str | None,
        }
    """
    argv = [sys.executable, "-m", "py_compile", rel_path]
    t0 = time.time()
    try:
        proc = subprocess.run(
            argv,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        dur = int((time.time() - t0) * 1000)
        log = _tail_log(
            (exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes)
             else (exc.stderr or "")) if exc.stderr else ""
        )
        return {
            "ran": True,
            "mode": "python_compile",
            "passed": False,
            "duration_ms": dur,
            "log_tail": log,
            "error": f"timeout after {timeout_s}s",
        }
    except Exception as exc:
        dur = int((time.time() - t0) * 1000)
        return {
            "ran": True,
            "mode": "python_compile",
            "passed": False,
            "duration_ms": dur,
            "log_tail": "",
            "error": f"process error: {str(exc)[:200]}",
        }

    dur = int((time.time() - t0) * 1000)
    combined = (proc.stderr or "") + (
        ("\n" + proc.stdout) if proc.stdout else ""
    )
    return {
        "ran": True,
        "mode": "python_compile",
        "passed": proc.returncode == 0,
        "duration_ms": dur,
        "log_tail": _tail_log(combined),
        "error": None,
    }


# Static analyzer script run as ``python3 -c _AST_LINT_SCRIPT <rel>``.
#
# IMPORTANT: This script MUST NEVER import or execute the target file.
# It only reads its source and runs ``ast.parse`` + an ``ast.NodeVisitor``
# over the AST. No code from the target is ever evaluated.
#
# Exit codes:
#   0  clean
#   1  issues found (SyntaxError or static-lint findings)
#   2  internal script error (unreadable file, etc.)
_AST_LINT_SCRIPT = r"""
import ast, sys

def main(argv):
    if len(argv) != 2:
        print("ast_lint: expected exactly one path argument", file=sys.stderr)
        return 2
    path = argv[1]
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as exc:
        print("ast_lint: cannot read {}: {}".format(path, exc), file=sys.stderr)
        return 2
    try:
        src = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        print("ast_lint: non-utf8 source ({}): {}".format(path, exc),
              file=sys.stderr)
        return 1
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as exc:
        loc = "line {}".format(exc.lineno) if exc.lineno else "?"
        print("ast_lint: SyntaxError at {}: {}".format(loc, exc.msg),
              file=sys.stderr)
        return 1

    issues = []

    def _is_overload(deco):
        # Accept @overload and @typing.overload (common shapes only).
        if isinstance(deco, ast.Name):
            return deco.id == "overload"
        if isinstance(deco, ast.Attribute):
            return deco.attr == "overload"
        return False

    # --- Top-level duplicate functions/classes (excluding @overload). ---
    seen_funcs = {}
    seen_classes = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(_is_overload(d) for d in (node.decorator_list or [])):
                continue
            first = seen_funcs.get(node.name)
            if first is None:
                seen_funcs[node.name] = node.lineno
            else:
                issues.append(
                    "duplicate top-level function '{}' at line {} "
                    "(first defined at line {})".format(
                        node.name, node.lineno, first))
        elif isinstance(node, ast.ClassDef):
            first = seen_classes.get(node.name)
            if first is None:
                seen_classes[node.name] = node.lineno
            else:
                issues.append(
                    "duplicate top-level class '{}' at line {} "
                    "(first defined at line {})".format(
                        node.name, node.lineno, first))

    # --- return/yield/yield from/await outside any function scope. ---
    # ast.parse already rejects these as SyntaxError in CPython today,
    # but we keep an explicit pass as a defensive net.
    class _ScopeVisitor(ast.NodeVisitor):
        def __init__(self):
            self.depth = 0
        def _enter(self, node):
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1
        def visit_FunctionDef(self, node):
            self._enter(node)
        def visit_AsyncFunctionDef(self, node):
            self._enter(node)
        def visit_Lambda(self, node):
            self._enter(node)
        def _flag(self, node, kind):
            if self.depth == 0:
                issues.append(
                    "'{}' outside function at line {}".format(
                        kind, getattr(node, "lineno", "?")))
        def visit_Return(self, node):
            self._flag(node, "return")
            self.generic_visit(node)
        def visit_Yield(self, node):
            self._flag(node, "yield")
            self.generic_visit(node)
        def visit_YieldFrom(self, node):
            self._flag(node, "yield from")
            self.generic_visit(node)
        def visit_Await(self, node):
            self._flag(node, "await")
            self.generic_visit(node)

    _ScopeVisitor().visit(tree)

    if issues:
        for msg in issues:
            print("ast_lint: " + msg, file=sys.stderr)
        return 1
    print("ast_lint: clean ({} bytes)".format(len(raw)))
    return 0

sys.exit(main(sys.argv))
"""


def _run_python_ast_lint_validation(
    *,
    repo_path: str,
    rel_path: str,
    timeout_s: float,
) -> Dict[str, Any]:
    """Run the static AST lint script against ``rel_path``.

    Uses a fixed argv list, no shell, no string interpolation into the
    command. ``rel_path`` has already passed slice-4b input validation
    before reaching here. The analyzer in ``_AST_LINT_SCRIPT`` never
    imports nor executes the target file; it only parses its source.
    Never raises: timeout, process errors and non-zero exit codes are
    all captured in the returned dict.

    Returns:
        {
          "ran": True,
          "mode": "python_ast_lint",
          "passed": bool,
          "duration_ms": int,
          "log_tail": str,
          "error": str | None,
        }
    """
    argv = [sys.executable, "-I", "-c", _AST_LINT_SCRIPT, rel_path]
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    t0 = time.time()
    try:
        proc = subprocess.run(
            argv,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        dur = int((time.time() - t0) * 1000)
        log = _tail_log(
            (exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes)
             else (exc.stderr or "")) if exc.stderr else ""
        )
        return {
            "ran": True,
            "mode": "python_ast_lint",
            "passed": False,
            "duration_ms": dur,
            "log_tail": log,
            "error": f"timeout after {timeout_s}s",
        }
    except Exception as exc:
        dur = int((time.time() - t0) * 1000)
        return {
            "ran": True,
            "mode": "python_ast_lint",
            "passed": False,
            "duration_ms": dur,
            "log_tail": "",
            "error": f"process error: {str(exc)[:200]}",
        }

    dur = int((time.time() - t0) * 1000)
    combined = (proc.stderr or "") + (
        ("\n" + proc.stdout) if proc.stdout else ""
    )
    # Exit code 2 means the script itself had an internal problem (e.g.
    # unreadable file) — surface it as an error rather than a fail.
    err: Optional[str] = None
    if proc.returncode == 2:
        err = "ast_lint internal error"
    return {
        "ran": True,
        "mode": "python_ast_lint",
        "passed": proc.returncode == 0,
        "duration_ms": dur,
        "log_tail": _tail_log(combined),
        "error": err,
    }


# ---------------------------------------------------------------------------
# Phase 2 slice 7b — pytest_target (Docker-isolated) helpers
# ---------------------------------------------------------------------------

def _compute_sandbox_image_ref(repo_path: str) -> Dict[str, Any]:
    """Compute the expected sandbox image ref for ``repo_path``.

    The tag is ``sha256(pyproject.toml)[:12]``, matching the algorithm
    in ``worker/sandbox/refresh.sh``. Never raises.
    """
    try:
        pyproject = Path(repo_path) / "pyproject.toml"
        raw = pyproject.read_bytes()
    except OSError as exc:
        return {"ok": False, "ref": None, "tag": None,
                "error": f"cannot read pyproject.toml: {exc}"}
    tag = hashlib.sha256(raw).hexdigest()[:12]
    return {"ok": True, "ref": f"{_SANDBOX_IMAGE_NAME}:{tag}",
            "tag": tag, "error": None}


def _read_file_at_ref(
    *,
    repo_path: str,
    ref: str,
    rel_path: str,
    timeout_s: float = _GIT_SHOW_TIMEOUT_S,
) -> Dict[str, Any]:
    """Read ``rel_path`` at ``ref`` via ``git show <ref>:<path>``.

    Pure argv (no shell, no string interpolation into the command).
    ``ref`` and ``rel_path`` are passed as ONE argument joined with
    ``:`` — any colon already inside them is fine because git handles
    that shape. Never raises.
    """
    if not ref or not isinstance(ref, str):
        return {"ok": False, "content": None, "error": "ref must be a non-empty string"}
    if not rel_path or not isinstance(rel_path, str):
        return {"ok": False, "content": None, "error": "rel_path must be a non-empty string"}
    argv = ["git", "show", f"{ref}:{rel_path}"]
    try:
        proc = subprocess.run(
            argv,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "content": None,
                "error": f"git show timeout after {timeout_s}s"}
    except Exception as exc:
        return {"ok": False, "content": None,
                "error": f"git show error: {str(exc)[:200]}"}
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()[-1:] or [""]
        return {"ok": False, "content": None,
                "error": f"git show rc={proc.returncode}: {err[0][:200]}"}
    return {"ok": True, "content": proc.stdout, "error": None}


def _docker_available() -> Dict[str, Any]:
    """Return ``{"ok": True}`` if ``docker`` is on PATH.

    Never raises. Distinguishes "docker not installed" from "docker
    present" without actually executing it.
    """
    path = shutil.which("docker")
    if not path:
        return {"ok": False, "error": "docker is not installed or not in PATH"}
    return {"ok": True, "path": path, "error": None}


def _docker_image_available(
    *, image_ref: str, timeout_s: float = _DOCKER_INSPECT_TIMEOUT_S,
) -> Dict[str, Any]:
    """Return ``{"ok": True}`` if the local daemon has ``image_ref``.

    Uses ``docker image inspect`` (exit 0 iff present). Never raises.
    """
    if not image_ref or not isinstance(image_ref, str):
        return {"ok": False, "error": "image_ref must be a non-empty string"}
    argv = ["docker", "image", "inspect", image_ref]
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False,
                "error": f"docker image inspect timeout after {timeout_s}s"}
    except Exception as exc:
        return {"ok": False,
                "error": f"docker image inspect error: {str(exc)[:200]}"}
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()[-1:] or [""]
        return {"ok": False,
                "error": (f"sandbox image {image_ref} is not available "
                          f"locally (rc={proc.returncode}: {err[0][:200]}). "
                          "Run worker/sandbox/refresh.sh to build it.")}
    return {"ok": True, "error": None}


def _prepare_pytest_target_context(
    *,
    repo_path: str,
    target_file: Optional[str],
    tournament_id: str,
) -> Dict[str, Any]:
    """Prepare everything the per-contestant runner will need.

    Called once per tournament when ``validation_mode=="pytest_target"``.
    Returns a dict with ``ok``, ``ws_path``, ``resolved_target``,
    ``image_ref``, ``error``. Never raises.

    On failure, ``ok`` is ``False``, ``ws_path`` is ``None`` and
    ``error`` is set; the caller MUST still invoke ``cleanup_workspace``
    on ``ws_path`` if it is not ``None`` (defensive).
    """
    ctx: Dict[str, Any] = {
        "ok": False, "ws_path": None, "resolved_target": None,
        "image_ref": None, "allowlist_size": 0, "error": None,
    }
    if not target_file:
        ctx["error"] = "pytest_target requires target_file"
        return ctx
    if not target_file.lower().endswith(".py"):
        ctx["error"] = "pytest_target only supports .py target files"
        return ctx

    img = _compute_sandbox_image_ref(repo_path)
    if not img["ok"]:
        ctx["error"] = img["error"]
        return ctx
    ctx["image_ref"] = img["ref"]

    dk = _docker_available()
    if not dk["ok"]:
        ctx["error"] = dk["error"]
        return ctx

    dim = _docker_image_available(image_ref=img["ref"])
    if not dim["ok"]:
        ctx["error"] = dim["error"]
        return ctx

    al = load_test_allowlist()
    if not al["ok"]:
        ctx["error"] = f"test allowlist load failed: {al['error']}"
        return ctx
    ctx["allowlist_size"] = len(al["tests"])

    rv = resolve_validation_target(
        target_file=target_file,
        repo_root=Path(repo_path),
        allowlist=al["tests"],
    )
    if not rv["ok"]:
        ctx["error"] = (
            f"no allowlisted pytest target for {target_file!r}: "
            f"{rv['error']} (tried: {', '.join(rv.get('candidates_tried') or []) or '-'})"
        )
        return ctx
    ctx["resolved_target"] = rv["resolved"]

    bw = build_workspace(Path(repo_path), tournament_id)
    if not bw["ok"]:
        ctx["error"] = f"workspace build failed: {bw['error']}"
        return ctx
    ctx["ws_path"] = bw["path"]

    ctx["ok"] = True
    return ctx


def _pytest_target_docker_argv(
    *,
    ws_path: Path,
    validation_target: str,
    image_ref: str,
) -> List[str]:
    """Build the fixed ``docker run`` argv for a pytest_target run.

    Pure helper for testing. All flags are literals; only ``ws_path``,
    ``image_ref`` and ``validation_target`` come from the runtime and
    they are each passed as their own argv item (no shell, no string
    interpolation into a command line).
    """
    # NOTE: only ``/tmp`` is a writable tmpfs. ``/work`` is a read-only
    # bind mount, so we cannot (and must not) layer tmpfs under it —
    # Docker rejects that at container launch with rc=125. pytest cache
    # is already disabled via ``-p no:cacheprovider`` and ``.pyc``
    # writes via ``PYTHONDONTWRITEBYTECODE=1`` below, so no writable
    # spot under ``/work`` is needed.
    return [
        "docker", "run", "--rm",
        "--network=none",
        "--read-only",
        "--tmpfs", "/tmp:size=64m,mode=1777,exec,nosuid,nodev",
        "--memory=512m", "--memory-swap=512m",
        "--cpus=1.0",
        "--pids-limit=256",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user", "10001:10001",
        "--ipc=none",
        "--mount", f"type=bind,source={ws_path},target=/work,readonly",
        "--workdir", "/work",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--env", "PYTHONUNBUFFERED=1",
        "--env", "WORKER_TOKEN=sandbox-stub",
        "--env", "UMBRAL_DISABLE_CLAUDE=1",
        image_ref,
        "python", "-m", "pytest",
        validation_target,
        "-x", "-q", "--no-header",
        "--disable-warnings",
        "-p", "no:cacheprovider",
        "--rootdir=/work",
    ]


def _run_pytest_target_validation(
    *,
    ws_path: Path,
    validation_target: str,
    image_ref: str,
    timeout_s: float,
) -> Dict[str, Any]:
    """Execute pytest inside the sandbox container for a single target.

    Returns the canonical ``validation`` dict shape:

        {
          "ran": True,
          "mode": "pytest_target",
          "passed": bool,
          "duration_ms": int,
          "log_tail": str,
          "error": str | None,
        }

    Never raises. Timeout, ``OSError`` and non-zero exit codes are all
    captured in the returned dict.
    """
    argv = _pytest_target_docker_argv(
        ws_path=ws_path,
        validation_target=validation_target,
        image_ref=image_ref,
    )
    t0 = time.time()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        dur = int((time.time() - t0) * 1000)
        partial = ""
        if exc.stderr:
            partial = exc.stderr.decode("utf-8", "replace") if isinstance(
                exc.stderr, bytes) else exc.stderr
        if exc.stdout and not partial:
            partial = exc.stdout.decode("utf-8", "replace") if isinstance(
                exc.stdout, bytes) else exc.stdout
        return {
            "ran": True,
            "mode": "pytest_target",
            "passed": False,
            "duration_ms": dur,
            "log_tail": _tail_log(partial or ""),
            "error": f"timeout after {timeout_s}s",
        }
    except Exception as exc:
        dur = int((time.time() - t0) * 1000)
        return {
            "ran": True,
            "mode": "pytest_target",
            "passed": False,
            "duration_ms": dur,
            "log_tail": "",
            "error": f"docker run error: {str(exc)[:200]}",
        }

    dur = int((time.time() - t0) * 1000)
    combined = (proc.stdout or "") + (
        ("\n" + proc.stderr) if proc.stderr else ""
    )
    # Exit codes: 0 = pytest success, 1-4 = pytest failures / internal,
    # 125-127 = docker problems (daemon, image, exec). Keep "passed"
    # strictly rc==0 but surface docker-level errors separately so the
    # re-judge can tell "tests actually failed" from "container refused
    # to start".
    docker_err: Optional[str] = None
    if proc.returncode in (125, 126, 127):
        docker_err = (
            f"docker/container launch failure (rc={proc.returncode}); "
            "image/deps may be stale or docker daemon unreachable"
        )
    return {
        "ran": True,
        "mode": "pytest_target",
        "passed": proc.returncode == 0,
        "duration_ms": dur,
        "log_tail": _tail_log(combined),
        "error": docker_err,
    }


def _contestant_ref_for_validation(
    code_change: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Best-effort commit ref for reading the contestant's target_file.

    Prefers the code_change commit SHA (slice 4b) when present and
    successful. Falls back to ``None`` (caller will mark
    ``validation.ran=False`` with a clear error).
    """
    if not code_change:
        return None
    commit = code_change.get("commit") or {}
    sha = commit.get("commit_sha")
    if commit.get("ok") and isinstance(sha, str) and sha:
        return sha
    return None


def _run_contestant_validation(
    *,
    mode: str,
    code_change: Optional[Dict[str, Any]],
    target_file: Optional[str],
    timeout_s: float,
    pytest_ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Decide whether to run validation for one contestant and run it.

    Returns the canonical ``validation`` dict shape. Does NOT raise.

    The ``pytest_ctx`` kwarg is only consulted when ``mode`` is
    ``"pytest_target"``; other modes ignore it entirely.
    """
    empty_stub = lambda err=None, ran=False: {  # noqa: E731
        "ran": ran,
        "mode": mode if mode != "none" else None,
        "passed": None,
        "duration_ms": None,
        "log_tail": None,
        "error": err,
    }

    if mode == "none":
        return empty_stub()

    if mode == "python_compile":
        if not target_file:
            return empty_stub("python_compile requires target_file")
        if not target_file.lower().endswith(".py"):
            return empty_stub("python_compile only supports .py files")
        if not code_change or not code_change.get("written"):
            return empty_stub("no code change to validate")
        return _run_python_compile_validation(
            repo_path=config.GITHUB_REPO_PATH,
            rel_path=target_file,
            timeout_s=timeout_s,
        )

    if mode == "python_ast_lint":
        if not target_file:
            return empty_stub("python_ast_lint requires target_file")
        if not target_file.lower().endswith(".py"):
            return empty_stub("python_ast_lint only supports .py files")
        if not code_change or not code_change.get("written"):
            return empty_stub("no code change to validate")
        return _run_python_ast_lint_validation(
            repo_path=config.GITHUB_REPO_PATH,
            rel_path=target_file,
            timeout_s=timeout_s,
        )

    if mode == "pytest_target":
        if not target_file:
            return empty_stub("pytest_target requires target_file")
        if not target_file.lower().endswith(".py"):
            return empty_stub("pytest_target only supports .py target files")
        if not code_change or not code_change.get("written"):
            return empty_stub("no code change to validate")
        if pytest_ctx is None:
            return empty_stub("pytest_target context not initialized")
        if not pytest_ctx.get("ok"):
            return empty_stub(
                pytest_ctx.get("error") or "pytest_target context unavailable",
            )
        ref = _contestant_ref_for_validation(code_change)
        if not ref:
            return empty_stub("no contestant commit to validate")
        # Read the contestant's version of target_file from their
        # commit and overwrite it in the shared workspace. Both steps
        # are never-raises.
        rf = _read_file_at_ref(
            repo_path=config.GITHUB_REPO_PATH,
            ref=ref, rel_path=target_file,
        )
        if not rf["ok"]:
            return empty_stub(
                f"cannot read {target_file}@{ref[:8]}: {rf['error']}",
            )
        ow = overwrite_file_in_workspace(
            ws_path=pytest_ctx["ws_path"],
            rel_path=target_file,
            content=rf["content"],
        )
        if not ow["ok"]:
            return empty_stub(f"workspace overwrite failed: {ow['error']}")
        return _run_pytest_target_validation(
            ws_path=pytest_ctx["ws_path"],
            validation_target=pytest_ctx["resolved_target"],
            image_ref=pytest_ctx["image_ref"],
            timeout_s=timeout_s,
        )

    return empty_stub(f"unsupported validation_mode: {mode}")


# ---------------------------------------------------------------------------
# Phase 2 slice 6 — re-judge with validation evidence
# ---------------------------------------------------------------------------

# Token-budget knobs for the enriched judge prompt. Kept small so that
# even 5 contestants with long proposals fit comfortably; the re-judge
# doesn't need the full proposal — it needs enough to recognise each
# approach plus the hard evidence (code_change, validation).
_REJUDGE_PROPOSAL_EXCERPT = 800
_REJUDGE_LOG_TAIL_EXCERPT = 200

# System prompt used for the re-judge pass. The final-line contract
# is identical to slice 3's JUDGE_SYSTEM (verbatim) so the same
# _extract_winner_id parser works without drift. The body instructs
# the judge to consider the actual per-contestant evidence and bias
# against validation failures, without hiding failing contestants.
REJUDGE_SYSTEM = (
    "You are the Tournament Re-Judge.\n"
    "An earlier judge already compared textual proposals. You now re-decide\n"
    "the winner using the ACTUAL evidence each contestant produced on its\n"
    "own branch: whether a code change was written, which file was touched,\n"
    "and whether a minimal validation passed.\n\n"
    "Your job:\n"
    "1. For each contestant, briefly weigh: proposal quality, whether a\n"
    "   real code change was committed, and the validation result.\n"
    "2. Prefer contestants whose validation PASSED. Avoid choosing\n"
    "   contestants whose validation FAILED unless they are clearly and\n"
    "   decisively better than every other option, and state why.\n"
    "3. If no contestant produced usable evidence, or if the trade-offs\n"
    "   among the remaining candidates are genuinely close, emit ESCALATE.\n"
    "4. State your final recommendation in 2-3 sentences.\n"
    "5. Write items 1-4 in the same language as the challenge.\n\n"
    "FINAL LINE CONTRACT (strict, machine-parsed):\n"
    "After your recommendation, finish the ENTIRE output with EXACTLY ONE\n"
    "of these two lines, on its own line, with no other text after it:\n"
    "  Winner: Contestant #N     (where N is the id of the contestant you chose)\n"
    "  ESCALATE                  (only if trade-offs are genuine and close)\n"
    "This final line MUST be in English and match the format above exactly.\n"
    "Do not add quotes, bullets, punctuation, markdown, translations, emojis,\n"
    "or explanatory text after it. Do not wrap it in a code block.\n\n"
    "Contestants:\n{contestants_block}"
)


def _summarize_code_change(code_change: Optional[Dict[str, Any]]) -> str:
    """Return a one-line summary of a contestant's code_change for the
    re-judge prompt. Never raises.
    """
    if not code_change:
        return "no code change (generate_code was disabled)"
    if not code_change.get("attempted"):
        return "no code change"
    written = code_change.get("written", False)
    path = code_change.get("path") or "<unknown>"
    mode = code_change.get("mode", "sandbox")
    parse_error = code_change.get("parse_error")
    commit = code_change.get("commit") or {}
    commit_ok = bool(commit.get("ok"))
    if parse_error:
        return f"code change FAILED ({mode}): parse_error: {parse_error}"
    if not written:
        return f"code change FAILED ({mode}): file was not written"
    if not commit_ok:
        err = commit.get("error") or "commit did not succeed"
        return f"code change written at {path} but commit FAILED: {err}"
    return f"wrote {mode} file {path} and committed successfully"


def _summarize_validation(validation: Optional[Dict[str, Any]]) -> str:
    """Return a short summary of a contestant's validation result for
    the re-judge prompt. Includes a trimmed tail on failure so the
    judge has actionable evidence. Never raises.
    """
    if not validation:
        return "not run"
    if not validation.get("ran"):
        err = validation.get("error")
        return f"not run ({err})" if err else "not run"
    mode = validation.get("mode", "?")
    duration = validation.get("duration_ms")
    passed = validation.get("passed")
    err = validation.get("error")
    if passed is True:
        tail = f" in {duration}ms" if duration is not None else ""
        return f"{mode} PASSED{tail}"
    log = validation.get("log_tail") or ""
    if len(log) > _REJUDGE_LOG_TAIL_EXCERPT:
        log = log[-_REJUDGE_LOG_TAIL_EXCERPT:]
    log = log.strip().replace("\n", " | ")
    reason = err or log or "no output"
    tail = f" in {duration}ms" if duration is not None else ""
    return f"{mode} FAILED{tail}: {reason}"


def _build_rejudge_prompt(
    *,
    challenge: str,
    contestants: list,
) -> Dict[str, str]:
    """Build (system, user) prompts for the re-judge LLM call.

    Truncates per-contestant proposal excerpts and validation log tails
    so the prompt stays manageable even with five contestants.
    """
    parts = []
    for c in contestants:
        cid = c.get("id", "?")
        name = c.get("approach", f"Approach {cid}")
        branch = c.get("branch", "?")
        proposal = c.get("proposal_excerpt") or ""
        if len(proposal) > _REJUDGE_PROPOSAL_EXCERPT:
            proposal = proposal[:_REJUDGE_PROPOSAL_EXCERPT] + " [...]"
        code_summary = _summarize_code_change(c.get("code_change"))
        val_summary = _summarize_validation(c.get("validation"))
        parts.append(
            f"### Contestant #{cid} — {name}\n"
            f"Branch: {branch}\n"
            f"Code change: {code_summary}\n"
            f"Validation: {val_summary}\n"
            f"Proposal excerpt:\n{proposal}"
        )
    contestants_block = "\n\n".join(parts)

    system = REJUDGE_SYSTEM.format(contestants_block=contestants_block)
    user = challenge
    return {"system": system, "user": user}


def _proposals_for_parser(contestants: list) -> list:
    """Adapt the orchestrator's contestants list into the shape that
    ``_extract_winner_id`` expects (list of {"id", "approach_name"}).
    """
    result = []
    for c in contestants:
        result.append({
            "id": c.get("id"),
            "approach_name": c.get("approach", ""),
        })
    return result


def _detect_override_attempt(contestants: list, winner_id: Any) -> bool:
    """Return True when the re-judge picked a contestant whose
    validation failed while at least one other contestant's validation
    passed. Used for output traceability only — we do NOT silently
    override the judge.
    """
    if winner_id is None:
        return False
    winner = next(
        (c for c in contestants if c.get("id") == winner_id), None,
    )
    if not winner:
        return False
    wv = winner.get("validation") or {}
    if not wv.get("ran") or wv.get("passed") is not False:
        return False
    for c in contestants:
        if c.get("id") == winner_id:
            continue
        v = c.get("validation") or {}
        if v.get("ran") and v.get("passed") is True:
            return True
    return False


def _run_rejudge(
    *,
    challenge: str,
    contestants: list,
    judge_model: str,
    max_tokens: int,
) -> Dict[str, Any]:
    """Run the enriched re-judge LLM call, parse the verdict with
    ``_extract_winner_id`` and return a structured result.

    Never raises. On any failure (empty contestants, LLM exception,
    empty LLM output) returns ``ran=True`` with ``error`` filled,
    ``winner_id=None`` and ``escalate=False`` so the caller can fall
    back to the initial verdict.
    """
    result: Dict[str, Any] = {
        "ran": True,
        "text": "",
        "winner_id": None,
        "escalate": False,
        "override_attempt": False,
        "duration_ms": 0,
        "model_used": judge_model,
        "error": None,
    }
    if not contestants:
        result["error"] = "no contestants to re-judge"
        return result

    prompts = _build_rejudge_prompt(
        challenge=challenge, contestants=contestants,
    )

    t0 = time.time()
    try:
        llm_out = handle_llm_generate({
            "prompt": prompts["user"],
            "system": prompts["system"],
            "model": judge_model,
            "temperature": 0.3,
            "max_tokens": max_tokens,
        })
    except Exception as exc:
        result["duration_ms"] = int((time.time() - t0) * 1000)
        result["error"] = f"llm error: {str(exc)[:200]}"
        logger.warning("Re-judge LLM call failed: %s", exc)
        return result

    result["duration_ms"] = int((time.time() - t0) * 1000)
    text = llm_out.get("text", "") if isinstance(llm_out, dict) else ""
    model_used = llm_out.get("model", judge_model) if isinstance(llm_out, dict) else judge_model
    result["text"] = text
    result["model_used"] = model_used
    if not text or not text.strip():
        result["error"] = "empty re-judge response"
        return result

    escalate = "ESCALATE" in text.upper()
    result["escalate"] = escalate
    if not escalate:
        try:
            winner_id = _extract_winner_id(
                text, _proposals_for_parser(contestants),
            )
        except Exception as exc:
            winner_id = None
            result["error"] = f"parser error: {str(exc)[:200]}"
        result["winner_id"] = winner_id
        if winner_id is not None:
            result["override_attempt"] = _detect_override_attempt(
                contestants, winner_id,
            )

    return result


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
        generate_code (bool): opt-in, slice 4a+4b. When True, each
            contestant also produces one FILE block that is written
            and committed on its branch.
        target_file (str): slice 4b. Optional real-repo path that
            every contestant must modify. Requires ``generate_code=True``.
            Validated up front against a denylist of protected prefixes
            and an extension allowlist; if invalid the handler returns
            ``ok: False`` before creating any branch.
        validation_mode (str): slice 5. One of ``"none"`` (default,
            retrocompat) or ``"python_compile"``. When set to
            ``"python_compile"`` AND a contestant actually wrote a
            ``.py`` file (slice 4b), ``python3 -m py_compile`` is run
            per contestant with a bounded timeout. Observational in
            this slice — the judge is not re-run.
        validation_timeout_s (int|float): slice 5. Per-contestant
            validation timeout in seconds. Default 20, hard-capped at
            60.
        rejudge (bool): slice 6. When True, run a second judge pass
            with enriched per-contestant evidence (code_change +
            validation) after the loop. The re-judge verdict
            supersedes the initial verdict for the cherry-pick. The
            initial verdict is preserved in ``verdict_initial`` for
            traceability. Re-judge never raises: on any failure the
            flow falls back to the initial verdict.

    Returns:
        ok, tournament_id, challenge, base, contestants,
        verdict, final_branch, final_result, branches_created, meta.
    """
    t0 = time.time()

    challenge = (input_data.get("challenge") or "").strip()
    if not challenge:
        raise ValueError("challenge is required")

    base = input_data.get("base", "main").strip()
    # Opt-in flag for slice 4. When False (default) behaviour is
    # byte-identical to slices 1–3.
    generate_code = bool(input_data.get("generate_code", False))
    # Slice 4b: if ``target_file`` is provided (and generate_code is on),
    # every contestant must emit a FILE block whose path equals that
    # value. Validated up front so a bad value aborts before any
    # branches are created.
    raw_target_file = input_data.get("target_file")
    target_file: Optional[str] = None
    if generate_code and raw_target_file is not None:
        tf_check = _validate_target_file(raw_target_file)
        if not tf_check["ok"]:
            return {
                "ok": False,
                "error": f"invalid target_file: {tf_check['error']}",
                "tournament_id": _generate_tournament_id(),
            }
        target_file = tf_check["normalized"]

    # Slice 5: validate validation_mode + validation_timeout_s up front.
    # Accepts missing/None as ``"none"`` (retrocompat default).
    vm_check = _validate_validation_mode(input_data.get("validation_mode"))
    if not vm_check["ok"]:
        return {
            "ok": False,
            "error": vm_check["error"],
            "tournament_id": _generate_tournament_id(),
        }
    validation_mode: str = vm_check["normalized"]

    # For pytest_target specifically, the defaults for python_compile
    # (20s) are too tight to even bootstrap pytest in the container.
    # If the caller did NOT pass an explicit value, apply the mode's
    # own default (45s); an explicit value still wins and is capped
    # by _VALIDATION_MAX_TIMEOUT_S.
    _timeout_input = input_data.get("validation_timeout_s")
    if _timeout_input is None and validation_mode == "pytest_target":
        _timeout_input = _PYTEST_TARGET_DEFAULT_TIMEOUT_S
    vt_check = _validate_validation_timeout(_timeout_input)
    if not vt_check["ok"]:
        return {
            "ok": False,
            "error": vt_check["error"],
            "tournament_id": _generate_tournament_id(),
        }
    validation_timeout_s: float = vt_check["normalized"]

    # Slice 6: opt-in re-judge pass after validation. When off
    # (default) behaviour is byte-identical to slices 1-5.
    rejudge_enabled = bool(input_data.get("rejudge", False))

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

    # Phase 2 slice 7b: prepare a single Docker sandbox context shared
    # by all contestants. On failure, the context carries ``ok=False``
    # with a human-readable error; each contestant's validation will
    # then surface that error via its own ``validation.error`` field
    # instead of aborting the tournament. Cleanup runs in the
    # ``finally`` block regardless.
    pytest_ctx: Optional[Dict[str, Any]] = None
    if validation_mode == "pytest_target":
        pytest_ctx = _prepare_pytest_target_context(
            repo_path=config.GITHUB_REPO_PATH,
            target_file=target_file,
            tournament_id=tournament_id,
        )
        if not pytest_ctx.get("ok"):
            logger.warning(
                "pytest_target context preparation failed: %s",
                pytest_ctx.get("error"),
            )

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

            # Phase 2 slice 4 (opt-in): ask the LLM for one sandboxed
            # file, validate + write + commit it on the contestant
            # branch. Failures are captured in `code_change` and do NOT
            # abort the tournament.
            code_change: Optional[Dict[str, Any]] = None
            if generate_code:
                code_change = _generate_and_commit_code_change(
                    tournament_id=tournament_id,
                    label=label,
                    idx=i + 1,
                    approach=approach,
                    challenge=challenge,
                    branch=branch,
                    judge_model=input_data.get("judge_model"),
                    temperature=float(input_data.get("temperature", 0.3)),
                    max_tokens=int(input_data.get("max_tokens", 2048)),
                    target_file=target_file,
                )

            # Phase 2 slice 5 (opt-in): validate the contestant's code
            # change. Never raises, never gates downstream steps —
            # observational only. Failing contestants are marked but
            # remain elegible for the winner selection already done by
            # the judge.
            validation = _run_contestant_validation(
                mode=validation_mode,
                code_change=code_change,
                target_file=target_file,
                timeout_s=validation_timeout_s,
                pytest_ctx=pytest_ctx,
            )

            contestants.append({
                "id": approach.get("id", i + 1),
                "approach": approach.get("approach_name", f"Approach {label.upper()}"),
                "branch": branch,
                "proposal_excerpt": (approach.get("proposal") or "")[:500],
                "artifact": artifact,
                "code_change": code_change,
                "validation": validation,
            })

        # ---- 4. Optional re-judge pass (Phase 2 slice 6) ----
        #
        # When ``rejudge=True``, run a second LLM pass that sees the
        # actual per-contestant evidence (code_change + validation)
        # produced by slices 4-5. The resulting verdict supersedes
        # the initial one for the cherry-pick decision; the initial
        # verdict is preserved as shadow info in the output. Never
        # raises — on LLM failure, we fall back to the initial
        # verdict so the flow always lands on a decision.
        rejudge_result: Dict[str, Any] = {
            "ran": False,
            "text": "",
            "winner_id": None,
            "escalate": False,
            "override_attempt": False,
            "duration_ms": 0,
            "model_used": None,
            "error": None,
        }
        effective_verdict = verdict
        if rejudge_enabled:
            rj_model = str(
                input_data.get("judge_model")
                or tournament.get("meta", {}).get("models_used", ["azure_foundry"])[0]
                or "azure_foundry"
            )
            rejudge_result = _run_rejudge(
                challenge=challenge,
                contestants=contestants,
                judge_model=rj_model,
                max_tokens=int(input_data.get("max_tokens", 2048)),
            )
            if rejudge_result.get("error") is None:
                effective_verdict = {
                    "text": rejudge_result["text"],
                    "winner_id": rejudge_result["winner_id"],
                    "escalate": rejudge_result["escalate"],
                }

        # ---- 5. Create final branch + cherry-pick the winner ----
        # (Phase 2 slice 2)
        #
        # Safe preconditions for cherry-pick:
        #   - effective verdict has a winner_id
        #   - effective verdict is not ESCALATE
        #   - the winning contestant has a successful commit from slice 1
        #   - the final branch was created cleanly
        #
        # Any missing precondition degrades to the Phase-1 behaviour
        # (final branch created from base with no commits), with an
        # explicit reason surfaced via `final_result.error`.
        final_branch = None
        final_result: Optional[Dict[str, Any]] = None
        if not effective_verdict.get("escalate") and effective_verdict.get("winner_id") is not None:
            winner_sha, winner_cid = _winner_commit_info(
                contestants=contestants,
                winner_id=effective_verdict.get("winner_id"),
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
        # Phase 2 slice 7b: always tear down the per-tournament sandbox
        # workspace, even on early exit. ``cleanup_workspace`` refuses
        # to touch anything without the ``umbral-sbx-`` prefix or
        # outside ``tempfile.gettempdir()``, so this is safe even if
        # ``pytest_ctx`` carries a surprising value. Never raises.
        if pytest_ctx and pytest_ctx.get("ws_path"):
            cu = cleanup_workspace(pytest_ctx["ws_path"])
            if not cu.get("ok"):
                logger.warning(
                    "sandbox workspace cleanup failed for %s: %s",
                    pytest_ctx.get("ws_path"), cu.get("error"),
                )
        _checkout_base(base)

    # Slice 6: if re-judge ran and produced a parseable verdict, the
    # top-level ``verdict`` reflects it and the initial one is preserved
    # as ``verdict_initial`` for traceability. If re-judge was off or
    # failed, ``verdict`` is the initial verdict and ``verdict_initial``
    # is ``None`` (keeps output shape predictable for consumers).
    verdict_out = {
        "text": effective_verdict.get("text", ""),
        "winner_id": effective_verdict.get("winner_id"),
        "escalate": effective_verdict.get("escalate", False),
    }
    verdict_initial_out: Optional[Dict[str, Any]] = None
    if rejudge_result.get("ran") and rejudge_result.get("error") is None:
        verdict_initial_out = {
            "text": verdict.get("text", ""),
            "winner_id": verdict.get("winner_id"),
            "escalate": verdict.get("escalate", False),
        }

    # Tournament-run already counts its own LLM calls. Add +1 for the
    # re-judge call so meta.total_llm_calls stays honest.
    rejudge_llm_calls = 1 if rejudge_result.get("ran") else 0

    return {
        "ok": True,
        "tournament_id": tournament_id,
        "challenge": challenge,
        "base": base,
        "contestants": contestants,
        "verdict": verdict_out,
        "verdict_initial": verdict_initial_out,
        "rejudge": rejudge_result,
        "final_branch": final_branch,
        "final_result": final_result,
        "branches_created": branches_created,
        "meta": {
            "total_llm_calls": tournament.get("meta", {}).get(
                "total_llm_calls", 0,
            ) + rejudge_llm_calls,
            "total_duration_ms": int((time.time() - t0) * 1000),
            "models_used": tournament.get("meta", {}).get("models_used", []),
            "generate_code": generate_code,
            "target_file": target_file,
            "validation_mode": validation_mode,
            "validation_timeout_s": validation_timeout_s,
            "rejudge": rejudge_enabled,
            "pytest_target": (
                {
                    "ok": bool(pytest_ctx.get("ok")),
                    "image_ref": pytest_ctx.get("image_ref"),
                    "resolved_target": pytest_ctx.get("resolved_target"),
                    "allowlist_size": pytest_ctx.get("allowlist_size", 0),
                    "workspace_prepared": pytest_ctx.get("ws_path") is not None,
                    "error": pytest_ctx.get("error"),
                }
                if pytest_ctx is not None
                else None
            ),
        },
    }
