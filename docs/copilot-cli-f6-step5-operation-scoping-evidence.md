# Copilot CLI — F6 Step 5 Evidence: Operation Scoping Enforcement

**Phase:** F6 step 5 — convert per-mission `allowed_operations` /
`forbidden_operations` from documentation into runtime enforcement.
**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability remains **DISABLED** at four layers.
`copilot_cli.egress.activated` remains **`false`**. No `nft` /
`iptables` / Docker network / `systemctl` / Copilot HTTPS call.

---

## 1. What F6 step 5 actually does

- Adds the optional input field `requested_operations: list[str]` to
  `copilot_cli.run`.
- Adds an in-handler enforcement step (5.5) that rejects payloads
  whose requested operations are unknown, forbidden by the mission,
  or globally hard-denied.
- Adds a global hard-deny set of operations
  (`apply_patch`, `git_push`, `gh_pr_create`, `gh_pr_merge`,
  `gh_pr_comment`, `gh_release_create`, `notion_write`,
  `notion_update`, `notion_delete`, `publish`, `deploy`,
  `secret_read`, `secret_write`, `shell_exec`, `run_subprocess`,
  `network_egress`, `write_files`, `write_to_docs_dir`,
  `write_to_runbooks_dir`, `run_tests_directly`) — defence-in-depth so
  a future operator who accidentally allows one of these in policy
  still sees it refused.
- Persists `requested_operations`, `allowed_operations`,
  `forbidden_operations`, `operation_decision`,
  `operation_violation` in the JSONL audit log.
- Backward-compatible: payloads without `requested_operations` fall
  back to a conservative inferred default per mission (`read_repo`
  for all four shipped missions).

It does **not** flip flags, **not** call Copilot, **not** apply nft,
**not** spawn subprocesses, **not** touch `~/.openclaw`, **not** open
network sockets.

## 2. Files changed

```
worker/tasks/copilot_cli.py                  (operation scoping enforcement)
tests/test_copilot_cli.py                    (+12 F6 step 5 tests; 4 stubs updated)
docs/copilot-cli-f6-step5-operation-scoping-evidence.md (new)
docs/copilot-cli-capability-design.md        (D18 + §11 phase status)
```

Files NOT touched:
- `config/tool_policy.yaml` — the four shipped missions already
  declared `allowed_operations` / `forbidden_operations` in F4. F6
  step 5 only consumes them.
- `worker/tool_policy.py` — no new accessor needed; the mission spec
  is read directly from `get_copilot_cli_missions()`.
- `infra/`, `scripts/`, `~/.openclaw/`, `/etc/`.

## 3. Per-mission operation matrix (consumed from `tool_policy.yaml`)

| Mission | Allowed (subset) | Forbidden (subset) | Default inferred |
|---|---|---|---|
| `research` | `read_repo`, `summarize`, `explain`, `cite_files` | `write_files`, `run_subprocess`, `network_egress`, `shell_exec` | `[read_repo]` |
| `lint-suggest` | `read_repo`, `read_lint_output`, `propose_patch_text` | `apply_patch`, `write_files`, `run_subprocess`, `network_egress` | `[read_repo]` |
| `test-explain` | `read_repo`, `read_test_output`, `explain_failure` | `run_subprocess`, `run_tests_directly`, `write_files`, `network_egress` | `[read_repo]` |
| `runbook-draft` | `read_repo`, `generate_markdown_artifact` | `write_to_docs_dir`, `write_to_runbooks_dir`, `run_subprocess`, `network_egress` | `[read_repo]` |

All four still have `max_files_touched: 0`, `network: none`,
`execution_mode: dry_run_artifact_only`,
`requires_human_materialization: true`. F6 step 5 does NOT loosen any
of these limits.

## 4. Decision precedence (first match wins)

1. `requested_operations == []` → `operation_not_allowed` /
   `operation_violation: no_operation_requested`.
2. Operation is in the global hard-deny set →
   `operation_forbidden` / `operation_violation: global_hard_deny`.
3. Operation is in the mission's `forbidden_operations` →
   `operation_forbidden` / `operation_violation: mission_forbidden`.
4. Operation is not declared anywhere (allowed ∪ forbidden ∪ global
   hard-deny) → `unknown_operation` /
   `operation_violation: not_declared_in_policy`.
5. Operation is not in the mission's `allowed_operations` →
   `operation_not_allowed` /
   `operation_violation: not_in_mission_allowlist`.

Failure is **closed by default**: if every check returns "no opinion",
the operation is rejected, never accepted.

## 5. Backward compatibility

A pre F6 step 5 payload omits `requested_operations`. The handler
infers a conservative default per mission:

```python
_DEFAULT_INFERRED_OPERATIONS = {
    "research":      ["read_repo"],
    "lint-suggest":  ["read_repo"],
    "test-explain":  ["read_repo"],
    "runbook-draft": ["read_repo"],
}
```

The default is filtered against the mission's `allowed_operations` so
it can never bypass the policy. If a future mission omits
`read_repo` from its allow-list and the caller sends no
`requested_operations`, the gate returns
`operation_not_allowed` / `no_operation_requested` — failing closed.

`test_f6step5_backward_compat_no_requested_operations` pins this
behaviour.

## 6. Audit log additions

Every event written by `copilot_cli.run` after F6 step 5 includes:

- `requested_operations`: list of operations the caller requested
  (after defaulting).
- `allowed_operations`: mission's allow-list at decision time.
- `forbidden_operations`: mission's deny-list at decision time.
- `operation_decision`: `allowed` | `operation_not_allowed` |
  `operation_forbidden` | `unknown_operation`.
- `operation_violation`: present only on rejection. One of
  `no_operation_requested`, `global_hard_deny`, `mission_forbidden`,
  `not_declared_in_policy`, `not_in_mission_allowlist`.

Tokens, prompts, env vars are NOT added. Existing redaction via
`_SENSITIVE_PATTERNS` is unchanged.

## 7. Tests

```
$ WORKER_TOKEN=test python -m pytest \
    tests/test_copilot_cli.py \
    tests/test_rick_tech_agent.py \
    tests/test_verify_copilot_egress_contract.py \
    tests/test_copilot_egress_resolver.py \
    tests/test_verify_copilot_cli_env_contract.py -q
........................................................................   [ 63%]
..........................................                                  [100%]
114 passed in 1.52s
```

Coverage delta vs F6 step 4 (+12 tests):

- `test_f6step5_allowed_operation_passes_to_dry_run`
- `test_f6step5_forbidden_operation_rejects_before_docker_argv`
- `test_f6step5_unknown_operation_rejects`
- `test_f6step5_operation_not_in_allowed_list_rejects`
- `test_f6step5_apply_patch_rejected_for_all_four_missions`
- `test_f6step5_global_hard_deny_blocks_git_push_open_pr_notion_write`
- `test_f6step5_audit_records_operation_lists`
- `test_f6step5_no_subprocess_called_during_operation_enforcement`
- `test_f6step5_backward_compat_no_requested_operations`
- `test_f6step5_empty_requested_operations_rejected`
- `test_f6step5_invalid_operation_name_rejects_at_schema`
- `test_f6step5_shipped_policy_missions_still_have_all_required_keys`

The four pre-existing tests that stubbed `get_copilot_cli_missions`
with empty mission specs (`{}` / `{"description": "test"}`) were
updated to declare `allowed_operations: ["read_repo"]` so the
operation gate has something to validate against. No production
behaviour changed; only the test stubs caught up with the new
contract.

## 8. What F6 step 5 explicitly does NOT do

- ✗ Does NOT flip `RICK_COPILOT_CLI_ENABLED`.
- ✗ Does NOT flip `RICK_COPILOT_CLI_EXECUTE`.
- ✗ Does NOT flip `copilot_cli.enabled`.
- ✗ Does NOT flip `copilot_cli.egress.activated`.
- ✗ Does NOT flip `_REAL_EXECUTION_IMPLEMENTED`.
- ✗ Does NOT call any Copilot HTTPS endpoint.
- ✗ Does NOT spawn any subprocess (asserted by
  `test_f6step5_no_subprocess_called_during_operation_enforcement`).
- ✗ Does NOT touch `nftables`, `iptables`, `ufw`, Docker networks,
  `systemctl`, `/etc/`.
- ✗ Does NOT touch Notion / gates / publication.
- ✗ Does NOT modify `rick-delivery` agent.
- ✗ Does NOT change `copilot_cli.missions` shape — only consumes it.

## 9. F6 step 6 unblock conditions

To advance to F6 step 6 (operator-only live install: `nft -c -f` of
the dropin under `/etc/nftables.d/`, install of
`/etc/umbral/copilot-cli{,-secrets}.env` with real fine-grained PAT,
systemd dropin, **still** without flipping
`copilot_cli.egress.activated` or `RICK_COPILOT_CLI_EXECUTE`), the
following must hold:

1. This document reviewed and approved by David.
2. Operator has the fine-grained PAT v2 with `Copilot Requests`
   minted, recorded in a secrets manager, and ready to paste into the
   secrets envfile **without echoing it to a shell history**.
3. Operator has confirmed the rollback drill from F6 step 3 §6
   (`sudo nft delete table inet copilot_egress` clears all rules
   atomically).
4. F6 step 6 plan must keep
   `copilot_cli.egress.activated = false`,
   `RICK_COPILOT_CLI_ENABLED = false`,
   `RICK_COPILOT_CLI_EXECUTE = false`,
   `_REAL_EXECUTION_IMPLEMENTED = False`. Step 6 is a *staging* step,
   not an activation step.
5. Verifiers (`verify_copilot_cli_env_contract.py` with `--strict` and
   permission checks; `verify_copilot_egress_contract.py`) all exit 0
   on the live host post-install.

## 10. Next prompt recommendation (F6 step 6 — DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 6: operator-only live staging. Install
> `/etc/umbral/copilot-cli{,-secrets}.env` (mode 0600, owner rick),
> install `/etc/nftables.d/copilot-egress.nft` (parse-checked with
> `nft -c -f`, NOT applied), install systemd dropin under
> `/etc/systemd/system/umbral-worker.service.d/copilot-cli.conf`,
> `systemctl daemon-reload` only. ALL flags stay false. The agent
> drives **only** the verifier runs and the evidence doc; the
> operator runs every `sudo install` / `sudo systemctl` command from
> their own shell. PR remains draft.
