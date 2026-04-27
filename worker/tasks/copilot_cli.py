"""Task: copilot_cli.run — Rick × GitHub Copilot CLI capability (F3 skeleton).

This task is the runtime surface for the Copilot CLI capability designed in
``docs/copilot-cli-capability-design.md``. **It does NOT execute Copilot in
F3.** It is registered, schema-validated, policy-gated, audit-logged and
returns the docker argv it WOULD have run, but the actual ``docker run`` is
intentionally not invoked.

Triple-gate (any False = capability blocked):
  1. L1 env flag    ``RICK_COPILOT_CLI_ENABLED == "true"``
  2. L2 policy flag ``config/tool_policy.yaml :: copilot_cli.enabled == true``
  3. L4 mission     ``mission`` must exist in ``copilot_cli.missions`` allowlist

Plus L2 deny-list: substring match against ``copilot_cli.banned_subcommands``
applied to (prompt + repo_path + any other free-form input field). Any match
short-circuits with ``error: banned_subcommand`` BEFORE the gate check, so
an attacker probing the surface still gets the same audit trail.

Audit log:
  ``reports/copilot-cli/<YYYY-MM>/<mission_run_id>.jsonl`` (append-only,
  one event per call). Tokens are redacted via ``_SENSITIVE_PATTERNS``.
  No prompt is stored in full — only a redacted summary truncated to
  ``_PROMPT_SUMMARY_MAX`` chars.

The task NEVER calls ``subprocess`` and NEVER opens a network socket in F3.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .. import tool_policy

logger = logging.getLogger("worker.tasks.copilot_cli")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENV_FLAG = "RICK_COPILOT_CLI_ENABLED"
_EXEC_FLAG = "RICK_COPILOT_CLI_EXECUTE"

# Hard safety constant: even if the operator sets every flag to true, F6
# step 1 has not implemented the real execution path. This stays False
# until F6 step N (token plumbing + egress + operation scoping
# enforcement + real subprocess invocation) is reviewed and approved.
# Tests assert this constant is False.
_REAL_EXECUTION_IMPLEMENTED = False

_REPO_ROOT: Path = Path(__file__).resolve().parents[2]

# F6 step 6C-4B-fixup: allowlist of canonical repo roots that the
# ``copilot_cli.run`` task is permitted to operate on. ``repo_path``
# must canonicalize (via ``Path.resolve``) to one of these roots OR a
# descendant of one. The check rejects ``/``, ``/home/rick``,
# nonexistent paths, regular files, and any symlink that escapes
# upward via resolution.
#
# The list is intentionally short:
#   * the worker's own checkout (``_REPO_ROOT``);
#   * the live VPS worktree at ``/home/rick/umbral-agent-stack`` (when
#     this code actually runs from a feature worktree).
#
# Operators / tests can extend it via the ``COPILOT_CLI_ALLOWED_REPO_ROOTS``
# env var (colon-separated absolute paths). Tests also use
# ``set_allowed_repo_roots_for_test`` to make this deterministic.
_HARDCODED_ALLOWED_REPO_ROOTS: Tuple[Path, ...] = (
    _REPO_ROOT,
    Path("/home/rick/umbral-agent-stack"),
    Path("/home/rick/umbral-agent-stack-copilot-cli"),
)

_REPO_ROOTS_ENV = "COPILOT_CLI_ALLOWED_REPO_ROOTS"

_ALLOWED_REPO_ROOTS_OVERRIDE: Optional[Tuple[Path, ...]] = None


def set_allowed_repo_roots_for_test(roots: Optional[Tuple[Path, ...]]) -> None:
    """Test helper: override the allowlist. Pass ``None`` to clear."""
    global _ALLOWED_REPO_ROOTS_OVERRIDE
    if roots is None:
        _ALLOWED_REPO_ROOTS_OVERRIDE = None
    else:
        _ALLOWED_REPO_ROOTS_OVERRIDE = tuple(Path(r).resolve(strict=False) for r in roots)


def _allowed_repo_roots() -> List[Path]:
    if _ALLOWED_REPO_ROOTS_OVERRIDE is not None:
        return list(_ALLOWED_REPO_ROOTS_OVERRIDE)
    roots: List[Path] = []
    seen: set = set()
    for r in _HARDCODED_ALLOWED_REPO_ROOTS:
        try:
            resolved = r.resolve(strict=False)
        except (OSError, RuntimeError):
            continue
        if resolved.exists() and resolved.is_dir() and str(resolved) not in seen:
            roots.append(resolved)
            seen.add(str(resolved))
    extra = os.environ.get(_REPO_ROOTS_ENV, "").strip()
    if extra:
        for raw in extra.split(":"):
            raw = raw.strip()
            if not raw:
                continue
            try:
                resolved = Path(raw).resolve(strict=False)
            except (OSError, RuntimeError):
                continue
            if resolved.exists() and resolved.is_dir() and str(resolved) not in seen:
                roots.append(resolved)
                seen.add(str(resolved))
    return roots


def _validate_repo_path(raw: str) -> Path:
    """Canonicalize ``raw`` and assert it is inside the allowlist.

    Raises ``_ValidationError`` with a stable error code on rejection.
    Never executes anything; pure path validation.
    """
    try:
        candidate = Path(raw).resolve(strict=False)
    except (OSError, RuntimeError):
        raise _ValidationError("repo_path_not_resolved", "'repo_path' could not be canonicalized")
    if not candidate.exists():
        raise _ValidationError("repo_path_not_found", "'repo_path' does not exist")
    if not candidate.is_dir():
        raise _ValidationError("repo_path_not_directory", "'repo_path' is not a directory")
    roots = _allowed_repo_roots()
    if not roots:
        # Defensive: if no root resolves on this host, refuse.
        raise _ValidationError(
            "repo_path_not_allowed",
            "'repo_path' rejected: no allowlisted repo root exists on this host",
        )
    for root in roots:
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        return candidate
    raise _ValidationError(
        "repo_path_not_allowed",
        "'repo_path' is not inside any allow-listed repo root",
    )

_DEFAULT_AUDIT_BASE: Path = _REPO_ROOT / "reports" / "copilot-cli"

_AUDIT_BASE_ENV = "COPILOT_CLI_AUDIT_DIR"

_SANDBOX_IMAGE_DEFAULT = "umbral-sandbox-copilot-cli"

_PROMPT_SUMMARY_MAX = 200

# Redact tokens, ssh keys, x-api-key style headers, generic Bearer leaks.
_SENSITIVE_PATTERNS = re.compile(
    r"("
    r"ghp_[A-Za-z0-9]{20,}"
    r"|ghs_[A-Za-z0-9]{20,}"
    r"|ghu_[A-Za-z0-9]{20,}"
    r"|gho_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{30,}"
    r"|sk-[A-Za-z0-9]{20,}"
    r"|AKIA[A-Z0-9]{10,}"
    r"|Bearer\s+[A-Za-z0-9._\-]{20,}"
    r"|x-api-key:\s*\S+"
    r")",
    re.IGNORECASE,
)

# Hard caps. Per-mission overrides will land in F4 via missions[name].
_MAX_WALL_SEC_CAP = 600
_MIN_WALL_SEC = 5

# Allowed top-level keys in the input envelope. Anything else is rejected.
_ALLOWED_INPUT_KEYS = frozenset({
    "mission",
    "prompt",
    "repo_path",
    "dry_run",
    "max_wall_sec",
    "metadata",
    "requested_operations",
})

# Free-form fields that must be scanned against banned_subcommands.
_BANNED_SCAN_FIELDS = ("prompt", "repo_path")

# F6 step 5: operation scoping. If the caller does not supply
# ``requested_operations`` we fall back to a conservative inferred
# set per mission. The values here MUST be a strict subset of every
# mission's ``allowed_operations`` from ``config/tool_policy.yaml`` so
# that the default never bypasses the policy.
_DEFAULT_INFERRED_OPERATIONS: Dict[str, List[str]] = {
    "research": ["read_repo"],
    "lint-suggest": ["read_repo"],
    "test-explain": ["read_repo"],
    "runbook-draft": ["read_repo"],
}

# Operations that are HARD-DENIED across every mission, regardless of
# what the policy file says — defence-in-depth. If a future operator
# accidentally adds one of these to ``allowed_operations`` for a
# mission, the handler still refuses. Mirrors the no-publish /
# no-merge / no-Notion / no-secret-mutation contract from `rick-tech`.
_GLOBAL_HARD_DENY_OPERATIONS = frozenset({
    "apply_patch",
    "git_commit",
    "git_push",
    "gh_pr_create",
    "gh_pr_merge",
    "gh_pr_comment",
    "gh_release_create",
    "notion_write",
    "notion_update",
    "notion_delete",
    "publish",
    "deploy",
    "secret_read",
    "secret_write",
    "shell_exec",
    "run_subprocess",
    "network_egress",
    "write_files",
    "write_to_docs_dir",
    "write_to_runbooks_dir",
    "run_tests_directly",
})

_OPERATION_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _redact(text: str) -> str:
    if not text:
        return ""
    return _SENSITIVE_PATTERNS.sub("[REDACTED]", text)


def _summarize(text: str, limit: int = _PROMPT_SUMMARY_MAX) -> str:
    redacted = _redact(text or "")
    if len(redacted) <= limit:
        return redacted
    return redacted[:limit] + "…(truncated)"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _audit_base_dir() -> Path:
    """Resolve audit directory. Tests override via env var."""
    override = os.environ.get(_AUDIT_BASE_ENV, "").strip()
    if override:
        return Path(override)
    return _DEFAULT_AUDIT_BASE


def _audit_log_path(mission_run_id: str) -> Path:
    base = _audit_base_dir()
    yyyy_mm = datetime.now(timezone.utc).strftime("%Y-%m")
    target = base / yyyy_mm
    target.mkdir(parents=True, exist_ok=True)
    return target / f"{mission_run_id}.jsonl"


def _write_audit_event(path: Path, event: Dict[str, Any]) -> None:
    """Append a single JSON event. Caller has already redacted sensitive data."""
    line = json.dumps(event, ensure_ascii=False, sort_keys=True, default=str)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _env_enabled() -> bool:
    return os.environ.get(_ENV_FLAG, "").strip().lower() == "true"


def _execute_enabled() -> bool:
    return os.environ.get(_EXEC_FLAG, "").strip().lower() == "true"


def _scan_for_banned(text: str, banned: List[str]) -> Optional[str]:
    """Return the first banned pattern that occurs as substring in ``text``.

    Mirrors the substring semantics of ``worker/sandbox/copilot-cli-wrapper``
    so the in-process gate matches the in-container gate exactly.
    """
    if not text or not banned:
        return None
    for pat in banned:
        if not pat:
            continue
        if pat in text:
            return pat
    return None


def _coerce_op_list(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _mission_operations(
    missions: Dict[str, Any], mission: str,
) -> tuple[List[str], List[str]]:
    """Return ``(allowed_operations, forbidden_operations)`` for ``mission``."""
    spec = missions.get(mission) or {}
    if not isinstance(spec, dict):
        return [], []
    allowed = _coerce_op_list(spec.get("allowed_operations"))
    forbidden = _coerce_op_list(spec.get("forbidden_operations"))
    return allowed, forbidden


def _resolve_requested_operations(
    requested: Optional[List[str]],
    mission: str,
    allowed: List[str],
) -> List[str]:
    """Pick the conservative default if the caller didn't ask for anything.

    The default MUST be a subset of ``allowed`` for the mission, otherwise
    we return an empty list and let the gate reject with
    ``operation_not_allowed`` (failing closed).
    """
    if requested is not None:
        return requested
    inferred = _DEFAULT_INFERRED_OPERATIONS.get(mission, [])
    return [op for op in inferred if op in allowed]


class _OperationDecision:
    __slots__ = ("error", "violation", "operation")

    def __init__(self, error: Optional[str], violation: Optional[str],
                 operation: Optional[str]):
        self.error = error
        self.violation = violation
        self.operation = operation

    @property
    def ok(self) -> bool:
        return self.error is None


def _enforce_operations(
    requested: List[str],
    allowed: List[str],
    forbidden: List[str],
) -> _OperationDecision:
    """Reject ``requested`` against the per-mission policy + global hard deny.

    Order of precedence (first match wins):
      1. Empty requested set → ``operation_not_allowed``.
      2. Operation in global hard-deny set → ``operation_forbidden``.
      3. Operation in mission's ``forbidden_operations`` → ``operation_forbidden``.
      4. Operation NOT in mission's ``allowed_operations`` → ``operation_not_allowed``.
      5. (Reserved) Unknown operation never declared anywhere → ``unknown_operation``.

    "Unknown" is reported when the operation name is not in any of the
    three sets (allowed ∪ forbidden ∪ global hard-deny). This prevents
    typos from silently masquerading as legitimate calls.
    """
    if not requested:
        return _OperationDecision("operation_not_allowed",
                                  "no_operation_requested", None)

    allowed_set = set(allowed)
    forbidden_set = set(forbidden)
    known_universe = allowed_set | forbidden_set | _GLOBAL_HARD_DENY_OPERATIONS

    for op in requested:
        if op in _GLOBAL_HARD_DENY_OPERATIONS:
            return _OperationDecision("operation_forbidden",
                                      "global_hard_deny", op)
        if op in forbidden_set:
            return _OperationDecision("operation_forbidden",
                                      "mission_forbidden", op)
        if op not in known_universe:
            return _OperationDecision("unknown_operation",
                                      "not_declared_in_policy", op)
        if op not in allowed_set:
            return _OperationDecision("operation_not_allowed",
                                      "not_in_mission_allowlist", op)

    return _OperationDecision(None, None, None)


def _build_docker_argv(
    *,
    mission_run_id: str,
    repo_path: str,
    image: str,
    max_wall_sec: int,
) -> List[str]:
    """Construct the docker argv that WOULD be executed in F6+.

    F3 returns this list as part of the dry-run result. **This function
    does not call subprocess.** The caller never executes the argv.
    """
    return [
        "docker", "run", "--rm",
        "--network=none",
        "--read-only",
        "--tmpfs", "/tmp:size=64m,mode=1777,exec,nosuid,nodev",
        "--tmpfs", "/scratch:size=64m,mode=1777,nosuid,nodev",
        "--tmpfs", "/home/runner/.cache:size=32m,mode=1777",
        "--memory=1g", "--memory-swap=1g", "--cpus=1.0",
        "--pids-limit=256",
        "--cap-drop=ALL",
        "--security-opt", "no-new-privileges",
        "--user", "10001:10001",
        "--ipc=none",
        "--mount", f"type=bind,source={repo_path},target=/work,readonly",
        "--workdir", "/work",
        "--name", f"copilot-cli-{mission_run_id}",
        "--stop-timeout", str(min(max_wall_sec, _MAX_WALL_SEC_CAP)),
        image,
        "/usr/local/bin/copilot-cli-smoke",
    ]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class _ValidationError(Exception):
    def __init__(self, code: str, message: str, **extra: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


def _validate_input(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise _ValidationError("invalid_input", "input must be a JSON object")

    extra = set(data.keys()) - _ALLOWED_INPUT_KEYS
    if extra:
        raise _ValidationError(
            "invalid_input",
            f"unknown input keys: {sorted(extra)}",
            unknown_keys=sorted(extra),
        )

    mission = data.get("mission")
    if not isinstance(mission, str) or not mission.strip():
        raise _ValidationError("invalid_input", "'mission' is required (non-empty string)")
    if len(mission) > 64 or not re.match(r"^[a-z][a-z0-9_-]{0,63}$", mission):
        raise _ValidationError(
            "invalid_input",
            "'mission' must match ^[a-z][a-z0-9_-]{0,63}$",
        )

    prompt = data.get("prompt", "")
    if not isinstance(prompt, str):
        raise _ValidationError("invalid_input", "'prompt' must be string")
    if len(prompt) > 16_000:
        raise _ValidationError("invalid_input", "'prompt' too long (>16000 chars)")

    repo_path = data.get("repo_path", str(_REPO_ROOT))
    if not isinstance(repo_path, str) or not repo_path.strip():
        raise _ValidationError("invalid_input", "'repo_path' must be non-empty string")
    # F6 step 6C-4B-fixup: canonicalize + allowlist enforcement.
    canonical_repo_path = _validate_repo_path(repo_path.strip())

    dry_run = data.get("dry_run", True)
    if not isinstance(dry_run, bool):
        raise _ValidationError("invalid_input", "'dry_run' must be boolean")

    max_wall_sec_raw = data.get("max_wall_sec", 120)
    try:
        max_wall_sec = int(max_wall_sec_raw)
    except (TypeError, ValueError):
        raise _ValidationError("invalid_input", "'max_wall_sec' must be integer")
    if not (_MIN_WALL_SEC <= max_wall_sec <= _MAX_WALL_SEC_CAP):
        raise _ValidationError(
            "invalid_input",
            f"'max_wall_sec' out of range [{_MIN_WALL_SEC}, {_MAX_WALL_SEC_CAP}]",
        )

    metadata = data.get("metadata", {}) or {}
    if not isinstance(metadata, dict):
        raise _ValidationError("invalid_input", "'metadata' must be object")

    requested_operations_raw = data.get("requested_operations", None)
    requested_operations: Optional[List[str]]
    if requested_operations_raw is None:
        requested_operations = None
    elif isinstance(requested_operations_raw, list):
        if len(requested_operations_raw) > 16:
            raise _ValidationError(
                "invalid_input",
                "'requested_operations' too long (>16 entries)",
            )
        cleaned: List[str] = []
        for item in requested_operations_raw:
            if not isinstance(item, str) or not item.strip():
                raise _ValidationError(
                    "invalid_input",
                    "'requested_operations' entries must be non-empty strings",
                )
            name = item.strip()
            if not _OPERATION_NAME_RE.match(name):
                raise _ValidationError(
                    "invalid_input",
                    f"'requested_operations' entry not well-formed: {name!r}",
                )
            cleaned.append(name)
        # Preserve order, drop duplicates.
        seen: set = set()
        deduped: List[str] = []
        for n in cleaned:
            if n not in seen:
                seen.add(n)
                deduped.append(n)
        requested_operations = deduped
    else:
        raise _ValidationError(
            "invalid_input",
            "'requested_operations' must be a list of strings",
        )

    return {
        "mission": mission.strip(),
        "prompt": prompt,
        "repo_path": str(canonical_repo_path),
        "dry_run": dry_run,
        "max_wall_sec": max_wall_sec,
        "metadata": metadata,
        "requested_operations": requested_operations,
    }


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------


def handle_copilot_cli_run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """F3 skeleton: validate → policy-gate → audit → return dry-run argv.

    NEVER executes Copilot CLI in F3. NEVER calls subprocess. NEVER opens a
    network socket. The capability remains DISABLED by default at multiple
    layers; even with all flags flipped, F3 only returns the argv that
    F6+ would execute.
    """
    mission_run_id = uuid.uuid4().hex
    audit_path = _audit_log_path(mission_run_id)
    audit_path_str = str(audit_path)

    env_enabled = _env_enabled()
    execute_enabled = _execute_enabled()
    policy_enabled = tool_policy.is_copilot_cli_policy_enabled()
    egress_activated = tool_policy.is_copilot_cli_egress_activated()
    banned = tool_policy.get_copilot_cli_banned_subcommands()
    missions = tool_policy.get_copilot_cli_missions()

    # F6 step 1 hard guard: even when all three flags are true, the real
    # execution path has not been implemented. This guarantees no
    # subprocess call can leak through misconfiguration.
    real_execution_blocked = not _REAL_EXECUTION_IMPLEMENTED or not execute_enabled

    base_event: Dict[str, Any] = {
        "ts": _now_iso(),
        "mission_run_id": mission_run_id,
        "phase": "F3",
        "task": "copilot_cli.run",
        "policy": {
            "env_enabled": env_enabled,
            "policy_enabled": policy_enabled,
            "execute_enabled": execute_enabled,
            "real_execution_implemented": _REAL_EXECUTION_IMPLEMENTED,
            "phase_blocks_real_execution": real_execution_blocked,
            "egress_activated": egress_activated,
            "missions_count": len(missions),
        },
    }

    # 1) Schema validation.
    try:
        validated = _validate_input(input_data)
    except _ValidationError as e:
        event = {
            **base_event,
            "decision": "invalid_input",
            "error": e.code,
            "error_message": _redact(e.message),
            **{k: _redact(str(v)) for k, v in e.extra.items()},
        }
        _write_audit_event(audit_path, event)
        return {
            "ok": False,
            "error": e.code,
            "error_message": e.message,
            "would_run": False,
            "audit_log": audit_path_str,
            "mission_run_id": mission_run_id,
        }

    mission = validated["mission"]
    prompt = validated["prompt"]
    repo_path = validated["repo_path"]
    dry_run = validated["dry_run"]
    max_wall_sec = validated["max_wall_sec"]

    # Always populate the redacted summary on subsequent events.
    base_event["mission"] = mission
    base_event["repo_path"] = repo_path
    base_event["dry_run"] = dry_run
    base_event["max_wall_sec"] = max_wall_sec
    base_event["prompt_summary"] = _summarize(prompt)
    base_event["metadata_keys"] = sorted((validated.get("metadata") or {}).keys())

    # 2) Banned subcommand scan — BEFORE the capability gate so even
    # disabled-state probes get the same audit trail.
    for field in _BANNED_SCAN_FIELDS:
        value = validated.get(field, "")
        matched = _scan_for_banned(value or "", banned)
        if matched:
            event = {
                **base_event,
                "decision": "banned_subcommand",
                "matched_pattern": matched,
                "matched_in_field": field,
            }
            _write_audit_event(audit_path, event)
            return {
                "ok": False,
                "error": "banned_subcommand",
                "matched": matched,
                "field": field,
                "would_run": False,
                "audit_log": audit_path_str,
                "mission_run_id": mission_run_id,
            }

    # 3) Capability gate — env flag.
    if not env_enabled:
        event = {**base_event, "decision": "capability_disabled_env"}
        _write_audit_event(audit_path, event)
        return {
            "ok": False,
            "error": "capability_disabled",
            "capability": "copilot_cli",
            "reason": "env_flag_off",
            "would_run": False,
            "audit_log": audit_path_str,
            "mission_run_id": mission_run_id,
            "policy": {"env_enabled": False, "policy_enabled": policy_enabled},
        }

    # 4) Capability gate — policy flag.
    if not policy_enabled:
        event = {**base_event, "decision": "capability_disabled_policy"}
        _write_audit_event(audit_path, event)
        return {
            "ok": False,
            "error": "capability_disabled",
            "capability": "copilot_cli",
            "reason": "policy_off",
            "would_run": False,
            "audit_log": audit_path_str,
            "mission_run_id": mission_run_id,
            "policy": {"env_enabled": True, "policy_enabled": False},
        }

    # 5) Mission allowlist.
    if not tool_policy.is_copilot_cli_mission_allowed(mission):
        event = {
            **base_event,
            "decision": "mission_not_allowed",
            "missions_allowed": sorted(missions.keys()),
        }
        _write_audit_event(audit_path, event)
        return {
            "ok": False,
            "error": "mission_not_allowed",
            "mission": mission,
            "missions_allowed": sorted(missions.keys()),
            "would_run": False,
            "audit_log": audit_path_str,
            "mission_run_id": mission_run_id,
        }

    # 5.5) Operation scoping enforcement (F6 step 5).
    mission_allowed_ops, mission_forbidden_ops = _mission_operations(
        missions, mission,
    )
    requested_ops = _resolve_requested_operations(
        validated.get("requested_operations"), mission, mission_allowed_ops,
    )
    op_decision = _enforce_operations(
        requested_ops, mission_allowed_ops, mission_forbidden_ops,
    )
    base_event["requested_operations"] = requested_ops
    base_event["allowed_operations"] = mission_allowed_ops
    base_event["forbidden_operations"] = mission_forbidden_ops
    if not op_decision.ok:
        event = {
            **base_event,
            "decision": op_decision.error,
            "operation_decision": op_decision.error,
            "operation_violation": op_decision.violation,
            "operation": op_decision.operation,
        }
        _write_audit_event(audit_path, event)
        return {
            "ok": False,
            "error": op_decision.error,
            "operation": op_decision.operation,
            "operation_violation": op_decision.violation,
            "mission": mission,
            "requested_operations": requested_ops,
            "allowed_operations": mission_allowed_ops,
            "forbidden_operations": mission_forbidden_ops,
            "would_run": False,
            "audit_log": audit_path_str,
            "mission_run_id": mission_run_id,
        }
    base_event["operation_decision"] = "allowed"

    # 6) All gates passed (env + policy + mission). F6 step 1 still does
    # NOT execute Copilot for two independent reasons:
    #   a) RICK_COPILOT_CLI_EXECUTE flag — operator-controlled.
    #   b) _REAL_EXECUTION_IMPLEMENTED constant — hard guard, only flipped
    #      when F6 step N (subprocess wiring + token plumbing + egress)
    #      ships under explicit review.
    # Build the docker argv that F6 step N would run, audit it, return.
    image = os.environ.get("COPILOT_CLI_SANDBOX_IMAGE", _SANDBOX_IMAGE_DEFAULT)
    docker_argv = _build_docker_argv(
        mission_run_id=mission_run_id,
        repo_path=repo_path,
        image=image,
        max_wall_sec=max_wall_sec,
    )
    redacted_argv = [_redact(a) for a in docker_argv]

    if not execute_enabled:
        decision = "execute_flag_off_dry_run"
    elif not _REAL_EXECUTION_IMPLEMENTED:
        decision = "real_execution_not_implemented"
    else:
        decision = "would_run_dry_run" if dry_run else "would_run_blocked_phase_f3"

    event = {
        **base_event,
        "decision": decision,
        "image": image,
        "docker_argv_redacted": redacted_argv,
        "egress_activated": egress_activated,
        "phase_blocks_real_execution": real_execution_blocked,
    }
    _write_audit_event(audit_path, event)

    return {
        "ok": True,
        "would_run": False,  # F6 step 1: never executes
        "phase": "F6.step1",
        "phase_blocks_real_execution": real_execution_blocked,
        "decision": decision,
        "policy": {
            "env_enabled": env_enabled,
            "policy_enabled": policy_enabled,
            "execute_enabled": execute_enabled,
            "real_execution_implemented": _REAL_EXECUTION_IMPLEMENTED,
            "phase_blocks_real_execution": real_execution_blocked,
        },
        "mission": mission,
        "mission_run_id": mission_run_id,
        "audit_log": audit_path_str,
        "docker_argv": redacted_argv,
        "operations": {
            "requested": requested_ops,
            "allowed": mission_allowed_ops,
            "forbidden": mission_forbidden_ops,
            "decision": "allowed",
        },
        "limits": {
            "max_wall_sec": max_wall_sec,
            **{k: v for k, v in tool_policy.get_copilot_cli_default_limits().items()
               if k != "max_wall_sec"},
        },
        "egress_activated": egress_activated,
    }
