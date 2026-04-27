# Copilot CLI — F4 Mission Contracts Evidence

**Phase:** F4 — define the 4 approved missions as policy contracts. **No execution. No flags flipped.**
**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability remains **DISABLED** (`copilot_cli.enabled: false`, `RICK_COPILOT_CLI_ENABLED=false`).

---

## 1. What F4 actually does

F4 lands the **mission contracts** that bound what Rick / Copilot CLI can be
asked to do once F6 flips real execution. Each mission is a structured
record under `config/tool_policy.yaml :: copilot_cli.missions` declaring
operations, limits, network policy and human-materialization requirement.
**No mission is executable** until both the env flag and the policy flag
are flipped — and even then, F3's `phase_blocks_real_execution: true`
still short-circuits the docker invocation.

## 2. Files changed

```
config/tool_policy.yaml             (+95 lines: 4 mission contracts under copilot_cli.missions)
.gitignore                          (+5 lines: reports/copilot-cli/ + artifacts/copilot-cli/)
tests/test_copilot_cli.py           (+10 new tests; total 39 passing)
docs/copilot-cli-f4-mission-contracts-evidence.md   (this file)
docs/copilot-cli-capability-design.md  (F4 status entry)
```

Untouched: `.env.example`, `worker/tasks/copilot_cli.py`, `worker/tool_policy.py`,
sandbox image, runner scripts, systemd, OpenClaw config.

## 3. The four missions (all read-only, artifact-only, network=none)

| Mission | Purpose | wall_sec | prompt | output | files_read |
|---|---|---|---|---|---|
| `research` | Read & explain repo, map modules, answer code questions | 300 | 8 000 | 32 000 | 200 |
| `lint-suggest` | Explain lint/test errors, propose patch text — does NOT apply | 300 | 12 000 | 32 000 | 100 |
| `test-explain` | Explain tests + failures from output captured by human | 240 | 12 000 | 24 000 | 100 |
| `runbook-draft` | Generate runbook/doc markdown as artifact under `reports/copilot-cli/` | 300 | 12 000 | 40 000 | 80 |

Common to all four:
- `max_files_touched: 0` — read-only.
- `network: none` — no egress, F3 sandbox unchanged.
- `execution_mode: dry_run_artifact_only` — output is an artifact, never a side effect.
- `requires_human_materialization: true` — David / Rick reviews, then materializes (commit, file move, PR draft) outside the task.
- Each declares `allowed_operations` and `forbidden_operations` (e.g. `apply_patch`, `run_subprocess`, `network_egress`, `write_to_docs_dir`).

## 4. Why these 4 are safe to "burn credits" on

- All are **input-only consumers** of the repo. They produce text artifacts.
- The deny-list (53 substring patterns from F2.5) still applies — `git push`, `gh pr create`, `rm -rf`, `sudo`, etc. blocked at task entry.
- Even if a Copilot response includes a destructive command, it lands in a markdown artifact, not in a shell pipe.
- `requires_human_materialization: true` makes the human the only path to disk/remote mutation. There is no F4 code path that writes outside `reports/copilot-cli/` or `artifacts/copilot-cli/` (both gitignored).
- `network: none` keeps the sandbox offline — Copilot CLI itself cannot run yet (needs egress), but the mission *contract* is what F6 will execute against.

## 5. Audit hygiene

- `.gitignore` now includes `reports/copilot-cli/` and `artifacts/copilot-cli/`. Production audit logs are NOT tracked.
- F3 evidence already committed under `docs/copilot-cli-f*-*.md` stays tracked (those are docs, not runtime audit).
- New test `test_f4_reports_copilot_cli_is_gitignored` enforces this.
- New test `test_f4_audit_dir_default_is_under_reports_copilot_cli` pins the production path.

## 6. Test results

```
$ WORKER_TOKEN=test python -m pytest tests/test_copilot_cli.py -q
.......................................                                  [100%]
39 passed in 1.06s
```

Coverage delta vs F3 (+10 tests):
- 4 × `test_f4_mission_exists[<name>]`
- 4 × `test_f4_mission_has_required_keys[<name>]`
- 4 × `test_f4_mission_is_read_only[<name>]` (asserts `max_files_touched==0`, `network=='none'`, `execution_mode`, `requires_human_materialization`)
- 4 × `test_f4_mission_limits_within_caps[<name>]`
- `test_f4_master_switch_still_off` (defensive: contracts must NOT flip the master switch)
- `test_f4_valid_mission_still_blocked_when_capability_disabled`
- `test_f4_unknown_mission_rejected_when_gates_pass`
- `test_f4_banned_subcommand_still_blocks_with_real_mission` (deny-list precedes capability gate)
- `test_f4_audit_dir_default_is_under_reports_copilot_cli`
- `test_f4_reports_copilot_cli_is_gitignored`

## 7. What F4 explicitly does NOT do

- ✗ Does not flip `copilot_cli.enabled` or `RICK_COPILOT_CLI_ENABLED`.
- ✗ Does not enable any mission for real execution (F3 still returns `phase_blocks_real_execution: true`).
- ✗ Does not provision token, secrets file, or systemd EnvironmentFile.
- ✗ Does not activate egress.
- ✗ Does not create the `rick-tech` agent (that is F5).
- ✗ Does not call subprocess. Tests still monkeypatch subprocess to raise.
- ✗ Does not touch Notion / gates / publication / PR / merge.

## 8. Risks / open items for F5 / F6

- **F5: `rick-tech` agent.** Need to scaffold the new agent surface (ROLE.md, mailbox, audit conventions) before F6 productive activation. Until then no agent has Copilot CLI as a tool in its policy.
- **F6: token plumbing.** `/etc/umbral/copilot-cli.env` + `/etc/umbral/copilot-cli-secrets.env` (mode 0600, owner `rick`). Token: `COPILOT_GITHUB_TOKEN` (fine-grained PAT v2 with `Copilot Requests`).
- **F6: `RICK_COPILOT_CLI_EXECUTE` flag.** Separate from `RICK_COPILOT_CLI_ENABLED`; flipping it removes `phase_blocks_real_execution`.
- **F6: egress activation.** `copilot_cli.egress.activated: true` + iptables/nftables rules per design §10.2.
- **F6: artifact rotation.** `reports/copilot-cli/` will grow; need rotation script analogous to `scripts/ops_log_rotate.py`.
- **Mission scoping enforcement:** F4 declares `allowed_operations`/`forbidden_operations` as policy text only. F6 must wire the wrapper to actually refuse any command outside `allowed_operations` (currently only deny-list is enforced).

## 9. Next prompt recommendation (F5 — DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F5: scaffold the `rick-tech` agent (separate from `rick-delivery`).
> Add agent ROLE.md, declare `copilot_cli.run` as the only mutating tool in
> its policy, wire mailbox conventions, add tests. Capability remains
> DISABLED. No token, no execution, no egress. PR remains draft.
