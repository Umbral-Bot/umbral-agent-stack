# Copilot CLI — F6 Step 1 Evidence: Token Plumbing Contract + Execute Flag

**Phase:** F6 step 1 of N — declarative contract for token plumbing and a
new operator-controlled execute flag. **No real activation. No token
provisioned. No subprocess invocation.**
**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability remains **DISABLED** at three independent layers
plus a hard safety constant.

---

## 1. What F6 step 1 actually does

- Adds `RICK_COPILOT_CLI_EXECUTE=false` to `.env.example` as a separate
  flag from `RICK_COPILOT_CLI_ENABLED`.
- Documents the production EnvironmentFile layout for systemd:
  `/etc/umbral/copilot-cli.env` (non-secret runtime flags) and
  `/etc/umbral/copilot-cli-secrets.env` (`COPILOT_GITHUB_TOKEN`).
- Wires the handler `worker/tasks/copilot_cli.py` to read the new flag and
  surface it in the response/audit.
- Adds a hard safety constant `_REAL_EXECUTION_IMPLEMENTED = False` that
  short-circuits the real-execution path even if all three operator
  flags flip to true. The constant is the F6 step N graduation lever.
- Adds 8 new tests (total 63 passing).

It does **not** enable the capability, **not** provision any token,
**not** call subprocess, **not** activate egress, **not** restart any
service, **not** modify `~/.openclaw/`.

## 2. Triple-flag + safety constant model

For real Copilot CLI execution, **all four** must be true:

| # | Layer | Variable | Default | Owner | Where |
|---|---|---|---|---|---|
| 1 | env (operator) | `RICK_COPILOT_CLI_ENABLED` | `false` | systemd EnvironmentFile / `.env` | `/etc/umbral/copilot-cli.env` |
| 2 | policy (config) | `copilot_cli.enabled` | `false` | repo | `config/tool_policy.yaml` |
| 3 | execute (operator) | `RICK_COPILOT_CLI_EXECUTE` | `false` | systemd EnvironmentFile / `.env` | `/etc/umbral/copilot-cli.env` |
| 4 | safety (code) | `_REAL_EXECUTION_IMPLEMENTED` | `False` | repo | `worker/tasks/copilot_cli.py` |

Layer 4 is intentionally **not operator-controllable**. Only a reviewed
commit graduating F6 to step N can flip it. This means:
- Even if an attacker leaks all three operator flags, no real subprocess
  runs.
- Even if the operator misconfigures, no real subprocess runs.
- Only when (1)+(2)+(3)+(4) are true does the docker invocation become
  reachable — and even then, the wrapper deny-list applies.

## 3. EnvironmentFile layout (production target — F6 step 2/3 will create these)

> **F6 step 1 does NOT create these files.** This section is the contract
> David / `rick-ops` will follow when provisioning. F6 step 1 only adds
> `RICK_COPILOT_CLI_EXECUTE=false` to `.env.example` for local dev.

### `/etc/umbral/copilot-cli.env`

```
# Owner: rick   Mode: 0600
# Non-secret runtime flags. Loaded by systemd dropin for umbral-worker.
RICK_COPILOT_CLI_ENABLED=false
RICK_COPILOT_CLI_EXECUTE=false
COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:6940cf0f274d
```

### `/etc/umbral/copilot-cli-secrets.env`

```
# Owner: rick   Mode: 0600
# SECRET — NEVER commit, NEVER echo to logs, NEVER pass to other services.
# Loaded by systemd dropin for umbral-worker as a separate EnvironmentFile
# so that rotation only touches this one file.
COPILOT_GITHUB_TOKEN=github_pat_<fine-grained PAT v2 con permiso "Copilot Requests">
```

Both files:
- Owner `rick:rick`, mode `0600`. Verify with `stat -c '%U %G %a' <path>`.
- Live OUTSIDE the repo, never under `/home/rick/umbral-agent-stack*`.
- Loaded via two separate `EnvironmentFile=` lines in
  `/etc/systemd/system/umbral-worker.service.d/copilot-cli.conf` (F6 step
  2 will write the dropin; step 1 only documents it).

### Systemd dropin (F6 step 2 — declarative target, NOT created in step 1)

```ini
# /etc/systemd/system/umbral-worker.service.d/copilot-cli.conf
[Service]
EnvironmentFile=/etc/umbral/copilot-cli.env
EnvironmentFile=/etc/umbral/copilot-cli-secrets.env
```

### Rotation procedure (when F6 step N enables real execution)

1. Mint a new fine-grained PAT v2 with the `Copilot Requests` permission
   on the user account. Set expiration ≤90 days.
2. Replace the value in `/etc/umbral/copilot-cli-secrets.env` (mode 0600).
3. `systemctl daemon-reload && systemctl restart umbral-worker`.
4. Verify with `journalctl -u umbral-worker -n 5` that the worker started
   without complaining about token absence (no token value is logged).
5. Revoke the old PAT in GitHub settings.

## 4. Why these tokens — and why NOT the others

| Variable | Used? | Why |
|---|---|---|
| `COPILOT_GITHUB_TOKEN` | **YES (preferred)** | Officially documented for Copilot CLI non-interactive auth. Highest precedence. |
| Fine-grained PAT v2 with `Copilot Requests` | **YES (token type)** | Officially confirmed in F2.5 against `copilot login --help` and docs.github.com. |
| OAuth Copilot CLI app token | YES (alt) | Acceptable; rotation handled by `copilot login` interactively — not used in non-interactive runtime. |
| GitHub App user-to-server (`ghu_`) | Aspirational | Cleaner audit; pending confirmation that Copilot CLI accepts it for non-interactive runs. |
| `GH_TOKEN` | **NO** | Would also enable the host `gh` CLI surface inside the container; we want only Copilot. Test `test_f6_gh_token_and_github_token_not_in_argv` enforces it never reaches the argv. |
| `GITHUB_TOKEN` | **NO** | Same reason as `GH_TOKEN`. |
| `gh auth login` interactive cache | **NO** | Persists credentials in `~/.config/gh/`; we need ephemeral, env-injected tokens. |
| `~/.copilot/config.json` | **NO** | Persistent on-disk credential store; against our "no secrets at rest" policy. |
| Classic PAT (`ghp_*`) | **NO** | Officially **not supported** by Copilot CLI for non-interactive auth (confirmed in F2.5). |

## 5. Handler changes (F6 step 1)

`worker/tasks/copilot_cli.py`:

```python
_ENV_FLAG = "RICK_COPILOT_CLI_ENABLED"
_EXEC_FLAG = "RICK_COPILOT_CLI_EXECUTE"

# Hard safety constant — only flipped by reviewed commit at F6 step N.
_REAL_EXECUTION_IMPLEMENTED = False
```

Response now includes:

```jsonc
{
  "ok": true,                       // gates passed (env + policy + mission)
  "would_run": false,               // F6 step 1: NEVER executes
  "phase": "F6.step1",
  "phase_blocks_real_execution": true,
  "decision": "execute_flag_off_dry_run"   // or "real_execution_not_implemented"
                                            //  / "would_run_dry_run"
                                            //  / "would_run_blocked_phase_f3"
                                            // depending on which guard fired
  "policy": {
    "env_enabled": true,
    "policy_enabled": true,
    "execute_enabled": false,           // ← new in F6 step 1
    "real_execution_implemented": false, // ← new in F6 step 1, hard constant
    "phase_blocks_real_execution": true
  },
  ...
}
```

Audit event records the same expanded `policy` block.

## 6. Tests

```
$ WORKER_TOKEN=test python -m pytest tests/test_copilot_cli.py tests/test_rick_tech_agent.py -q
...............................................................          [100%]
63 passed in ...
```

Coverage delta vs F5 (+8 tests):

- `test_f6_execute_flag_default_false`
- `test_f6_real_execution_implemented_constant_is_false` (hard guard)
- `test_f6_execute_flag_off_keeps_phase_blocked` (env+policy+mission true,
  execute false → `phase_blocks_real_execution: true`,
  `decision: execute_flag_off_dry_run`)
- `test_f6_execute_flag_on_still_blocked_by_real_execution_constant`
  (all three operator flags true; `_REAL_EXECUTION_IMPLEMENTED=False`
  short-circuits; subprocess monkeypatched to raise; result
  `decision: real_execution_not_implemented`)
- `test_f6_audit_records_all_three_flags`
- `test_f6_gh_token_and_github_token_not_in_argv`
- `test_f6_env_example_declares_execute_flag`
- `test_f6_design_doc_documents_envfile_layout` (asserts mode 0600,
  layout, "no classic PAT")

## 7. What F6 step 1 explicitly does NOT do

- ✗ Does NOT flip `RICK_COPILOT_CLI_ENABLED`.
- ✗ Does NOT flip `RICK_COPILOT_CLI_EXECUTE`.
- ✗ Does NOT flip `copilot_cli.enabled`.
- ✗ Does NOT flip `_REAL_EXECUTION_IMPLEMENTED`.
- ✗ Does NOT create `/etc/umbral/copilot-cli.env`.
- ✗ Does NOT create `/etc/umbral/copilot-cli-secrets.env`.
- ✗ Does NOT write the systemd dropin.
- ✗ Does NOT mint, store, log, or transmit any token.
- ✗ Does NOT activate egress.
- ✗ Does NOT call subprocess (test enforces with monkeypatch).
- ✗ Does NOT touch `~/.openclaw/` or any live runtime.
- ✗ Does NOT restart any systemd unit.
- ✗ Does NOT modify Notion / gates / publication.
- ✗ Does NOT open / merge / comment any PR.

## 8. Risks / open items

- **F6 step 2 = secrets file provisioning.** David / `rick-ops` create
  the two `/etc/umbral/copilot-cli*.env` files with mode 0600 and the
  systemd dropin. Verification script: `stat -c '%U %G %a'`.
- **F6 step 3 = egress activation.** Flip
  `copilot_cli.egress.activated: true` plus iptables/nftables rules per
  design §10.2.
- **F6 step 4 = operation scoping enforcement.** Wire
  `allowed_operations`/`forbidden_operations` from the mission contract
  into the wrapper / handler so anything outside is refused (today only
  the 53-pattern deny-list is enforced).
- **F6 step N = real execution.** Replace `_REAL_EXECUTION_IMPLEMENTED`
  with `True` in a single, reviewed commit. Add the `subprocess.run`
  call gated by the same flag. Verify token presence at handler entry,
  reject early with `error: token_missing` if absent.
- **Smoke test for token absence.** Once step N lands, add a test that
  with all flags true but `COPILOT_GITHUB_TOKEN` absent, the handler
  rejects with `token_missing` *before* spawning docker.
- **Token rotation observability.** Need a check (cron or healthcheck)
  that warns ≥7 days before PAT expiration.

## 9. Next prompt recommendation (F6 step 2 — DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 2: write the systemd dropin **as a repo artifact
> under `infra/systemd/`** (not yet installed live). Add a one-shot
> verification script that checks file ownership/mode against the
> contract. Capability remains DISABLED. No token provisioned. No live
> systemd touched. PR remains draft.
