# F7 Rehearsal 1 — Policy Gate Only: Live Deploy Evidence

**Date:** 2026-05-05
**Operator:** David (human) + Rick AI (automated evidence)
**Branch merged:** `rick/copilot-cli-f7-policy-gate-rehearsal` → PR #274
**Evidence branch:** `rick/copilot-cli-f7-policy-gate-rehearsal-evidence`

---

## 1. Objective (Rehearsal 1)

Open **only** L2 policy gate (`config/tool_policy.yaml :: copilot_cli.enabled: false → true`) to verify
that the capability transitions from `policy_off` to the next expected rejection: `execute_flag_off_dry_run`.

No real Copilot execution. No subprocess. No egress. No flag flips beyond L2.

---

## 2. Pre-Deploy State

| Item | Value |
|---|---|
| Live HEAD (before pull) | `45ff7e1` |
| MainPID (before restart) | `1124888` |
| `/health` | 200 |
| `copilot_cli.enabled` (live yaml, before) | `false` |
| `RICK_COPILOT_CLI_ENABLED` (envfile) | `true` |
| `RICK_COPILOT_CLI_EXECUTE` (envfile) | `false` |
| `_REAL_EXECUTION_IMPLEMENTED` (code) | `False` |
| `egress.activated` (yaml) | `false` |
| Expected probe result (before) | `capability_disabled / policy_off` |

---

## 3. Deploy Steps Executed

### Step 1 — Pull

```
git pull --ff-only origin main
# Updating 45ff7e1..6ce6cae
# config/tool_policy.yaml | 2 +-
# tests/test_copilot_cli.py | 74 ++++++++++++++-
# docs/copilot-cli-f7-policy-gate-rehearsal.md | 175 +++
# + 2 other docs/tasks files
```

New live HEAD: **`6ce6cae`** (merge commit of PR #274)

### Step 2 — Restart

```
OLD_PID=1124888
systemctl --user restart umbral-worker.service
sleep 3
NEW_PID=1403101
ActiveState=active  SubState=running
```

### Step 3 — /health

```
HTTP 200
```

---

## 4. Probe Results — Post Deploy

**Command:**
```bash
curl -s -X POST http://127.0.0.1:8088/run \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task":"copilot_cli.run","input":{"mission":"research","prompt":"F7 rehearsal 1 probe","requested_operations":["read_repo"],"repo_path":"/home/rick/umbral-agent-stack"}}'
```

**Response (trimmed):**
```json
{
  "ok": true,
  "task": "copilot_cli.run",
  "result": {
    "ok": true,
    "would_run": false,
    "phase": "F6.step1",
    "phase_blocks_real_execution": true,
    "decision": "execute_flag_off_dry_run",
    "policy": {
      "env_enabled": true,
      "policy_enabled": true,
      "execute_enabled": false,
      "real_execution_implemented": false,
      "phase_blocks_real_execution": true
    },
    "mission": "research",
    "mission_run_id": "766f5ef9c22e47bf829490db49ce6791",
    "audit_log": "reports/copilot-cli/2026-05/766f5ef9c22e47bf829490db49ce6791.jsonl",
    "egress_activated": false
  }
}
```

### Signal Transition ✅

| Before deploy | After deploy |
|---|---|
| `capability_disabled` / `policy_off` | `ok:true` / `execute_flag_off_dry_run` |

**L2 policy gate passed** → blocked at **L3 execute flag** as expected.
Execution is **impossible** because:
- L3: `execute_enabled=false` (`RICK_COPILOT_CLI_EXECUTE=false`)
- L5: `real_execution_implemented=false` (`_REAL_EXECUTION_IMPLEMENTED=False`)
- `egress_activated=false`

---

## 5. Gate Verification

```yaml
# config/tool_policy.yaml (live, post-pull)
copilot_cli:
  enabled: true        # L2 — OPEN (rehearsal 1 change)
  egress:
    activated: false   # L4 — still CLOSED
```

```python
# worker/tasks/copilot_cli.py line 55
_REAL_EXECUTION_IMPLEMENTED = False  # L5 — still CLOSED
```

```ini
# /home/rick/.config/openclaw/copilot-cli.env
RICK_COPILOT_CLI_ENABLED=true   # L1 — open (pre-existing)
RICK_COPILOT_CLI_EXECUTE=false  # L3 — CLOSED
```

---

## 6. Side-Effect Verification

| Check | Result |
|---|---|
| nft copilot rules | none |
| Docker network copilot | none |
| audit log gitignored | YES (`reports/copilot-cli/` in .gitignore) |
| audit log token scan (ghp_, github_pat_, ghs_, sk-) | CLEAN |
| audit log content | `decision: execute_flag_off_dry_run`, `docker_argv_redacted` (no real run) |
| Copilot HTTPS requests | none (subprocess never launched) |
| Notion writes | none |
| Gates publish | none |
| Token printed to logs | NO |

---

## 7. Post-Deploy State

| Item | Value |
|---|---|
| Live HEAD | `6ce6cae` |
| MainPID | `1403101` (changed once) |
| `/health` | 200 |
| `copilot_cli.enabled` (live) | `true` ← F7 change |
| `RICK_COPILOT_CLI_ENABLED` | `true` |
| `RICK_COPILOT_CLI_EXECUTE` | `false` ← unchanged |
| `_REAL_EXECUTION_IMPLEMENTED` | `False` ← unchanged |
| `egress.activated` | `false` ← unchanged |
| Probe signal | `execute_flag_off_dry_run` ← ✅ expected |

---

## 8. Rollback Plan

If needed:
```bash
# Edit config/tool_policy.yaml: copilot_cli.enabled: false
git commit -m "revert(copilot-cli): F7 rollback — close policy gate"
git push ...
# Pull in live worktree + restart worker
```
Capability returns to `policy_off`. No data loss. No egress to undo.

---

## 9. Next Phase

**Rehearsal 2 (not yet approved):** Open L3 execute flag (`RICK_COPILOT_CLI_EXECUTE=true`)
to test that the blocking transitions to `real_execution_not_implemented` (L5 code constant).
Still no real Copilot subprocess.

**No action without David's explicit approval.**
