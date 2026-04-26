# Copilot CLI — F3 Task Evidence

**Phase:** F3 — `copilot_cli.run` task skeleton (registered, gated, audited).
**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability **DISABLED** (env + policy + missions: {} all enforce off-by-default).

---

## 1. What F3 actually does

F3 lands the *runtime surface* for the Copilot CLI capability without giving
it any real execution power. The task `copilot_cli.run` is now part of
`worker.tasks.TASK_HANDLERS`, validates input strictly, runs the full
guardrail stack, writes an append-only JSONL audit log, and **returns the
exact docker argv that F6+ would execute** — but never invokes
`subprocess`, never opens a network socket, never touches Copilot CLI.

Triple gate (any False = blocked):

1. **L1 env flag** — `RICK_COPILOT_CLI_ENABLED == "true"` (default false in `.env.example`).
2. **L2 policy flag** — `config/tool_policy.yaml :: copilot_cli.enabled == true` (default false).
3. **L4 mission allowlist** — `mission ∈ copilot_cli.missions` (currently `{}` ⇒ rejects everything).

Plus a deny-list scan over `prompt` and `repo_path` against the 53
`banned_subcommands` (same patterns as the in-container wrapper). The deny
scan runs **before** the capability gate so probes still get a clean
audit trail.

---

## 2. Files added / modified (F3 only)

```
worker/tasks/copilot_cli.py         (new, ~330 lines)
worker/tasks/__init__.py            (+2 lines: import + TASK_HANDLERS entry)
worker/tool_policy.py               (+5 helpers: is_copilot_cli_*, missions, banned, limits, egress)
tests/test_copilot_cli.py           (new, 17 tests)
docs/copilot-cli-f3-task-evidence.md  (this file)
docs/copilot-cli-capability-design.md (F3 status + task contract section)
```

No change to `.env.example`, `config/tool_policy.yaml`, sandbox image,
runner scripts, systemd units, OpenClaw config, or any active mission.
The capability remains disabled.

---

## 3. Schema (input contract)

```jsonc
{
  "mission": "research",            // ^[a-z][a-z0-9_-]{0,63}$, must be in missions allowlist
  "prompt":  "free text, ≤16000",   // scanned for banned_subcommands
  "repo_path": "/work",             // scanned for banned_subcommands
  "dry_run": true,                  // F3 ignores the value — never executes either way
  "max_wall_sec": 60,               // 5..600
  "metadata": { "requested_by": "rick-tech" }
}
```

Unknown top-level keys are rejected (`error: invalid_input`) to prevent
silent attribute-stuffing.

## 4. Output contracts

| Branch | `error` | `would_run` | Notes |
|---|---|---|---|
| Env flag off | `capability_disabled` (`reason: env_flag_off`) | false | default state |
| Policy flag off | `capability_disabled` (`reason: policy_off`) | false | env on, YAML off |
| Mission not in allowlist | `mission_not_allowed` | false | currently always (missions: {}) |
| Banned substring in prompt/repo_path | `banned_subcommand` | false | with `matched`, `field` |
| Invalid input | `invalid_input` | false | `error_message` field |
| All gates pass | `ok: true`, `phase: F3`, `phase_blocks_real_execution: true` | **false** | docker argv returned (redacted), still not executed |

Every branch writes one JSONL event to:
```
reports/copilot-cli/<YYYY-MM>/<mission_run_id>.jsonl
```
…or, in tests, the path pointed to by `COPILOT_CLI_AUDIT_DIR`.

## 5. Audit log event shape

```jsonc
{
  "ts": "2026-04-26T16:30:00+00:00",
  "mission_run_id": "<hex32>",
  "phase": "F3",
  "task": "copilot_cli.run",
  "policy": {
    "env_enabled": false,
    "policy_enabled": false,
    "egress_activated": false,
    "missions_count": 0
  },
  "mission": "research",
  "repo_path": "/work",
  "dry_run": true,
  "max_wall_sec": 60,
  "prompt_summary": "[≤200 chars, redacted]",
  "metadata_keys": ["requested_by"],
  "decision": "capability_disabled_env"  // or banned_subcommand / mission_not_allowed / would_run_dry_run / …
}
```

Sensitive patterns redacted via regex:
`ghp_*`, `ghs_*`, `ghu_*`, `gho_*`, `github_pat_*`, `sk-*`, `AKIA…`,
`Bearer …`, `x-api-key: …` → `[REDACTED]`.

The full prompt is **never** stored — only `prompt_summary` (≤200 chars,
redacted, truncation marker).

## 6. Test results

```
$ WORKER_TOKEN=test python -m pytest tests/test_copilot_cli.py -q
.................                                                        [100%]
17 passed in 0.85s
```

Coverage:
- (1) capability_disabled by env default
- (2) capability_disabled by policy default
- (3) mission_not_allowed when allowlist empty
- (4) banned `git push --force` in prompt
- (5) banned `gh pr create` in prompt
- (6) clean prompt → still capability_disabled (no false-positive banned)
- (7) audit log redacts `ghp_*` and `Bearer …`
- (8) docker argv built in dry-run **with subprocess.run/Popen monkeypatched to raise** → no execution
- (9) `COPILOT_GITHUB_TOKEN` in env never appears in returned argv or audit
- (10–11) schema rejects unknown keys and bad mission names
- (12) sensitive-pattern regex sanity (parametrized)
- (13) `copilot_cli.run` registered in `TASK_HANDLERS`

Worker import / inventory smoke also green:

```
$ python -c "from worker.app import app"
Registered tasks: [..., 'copilot_cli.run']
$ python -m pytest tests/test_worker_inventory_smoke.py -q
....                                                                     [100%]
```

## 7. What F3 explicitly does NOT do

- ✗ Does not flip `RICK_COPILOT_CLI_ENABLED` to true.
- ✗ Does not flip `copilot_cli.enabled` to true.
- ✗ Does not add any active mission.
- ✗ Does not call `subprocess.*` (test 8 proves this with monkeypatch sentinels).
- ✗ Does not import `docker`, no `socket`, no `requests` — pure stdlib.
- ✗ Does not require, read, or persist any token.
- ✗ Does not use `gh auth`, `gh` CLI, or any Copilot CLI binary on host.
- ✗ Does not activate egress.
- ✗ Does not restart any systemd unit.
- ✗ Does not touch Notion, gates, or publication.
- ✗ Does not open or merge any PR.

## 8. Risks / open items for F4

- **Active missions:** F4 must populate `copilot_cli.missions` with the 4
  approved missions (`research`, `lint-suggest`, `test-explain`,
  `runbook-draft`) and per-mission limits. Until then, even with both
  flags on, the task returns `mission_not_allowed`.
- **Token plumbing:** F3 reads no token. F4/F6 will need to inject
  `COPILOT_GITHUB_TOKEN` into the docker container via `--env-file`
  pointing at `/etc/umbral/copilot-cli-secrets.env` (mode 0600, root:rick).
- **Dry-run is permanent in F3:** even when all gates pass, the response
  carries `phase_blocks_real_execution: true`. F6 will switch this off
  behind a separate `RICK_COPILOT_CLI_EXECUTE` flag.
- **Audit log retention:** `reports/copilot-cli/` will grow append-only.
  Existing `scripts/ops_log_rotate.py` covers `ops_log.jsonl` only — need
  a parallel rotation policy before F6.
- **Egress profile:** designed in §10 of the design doc, still
  `activated: false`. F6 prerequisite.

## 9. Next prompt recommendation (F4 — DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F4: populate `copilot_cli.missions` with the 4 approved
> missions in `tool_policy.yaml`, add per-mission limits, but keep
> `copilot_cli.enabled: false` and `RICK_COPILOT_CLI_ENABLED=false`.
> Add mission-template tests (still no real execution). Document the
> mission contract in design doc §6.

PR remains **draft**, no merge.
