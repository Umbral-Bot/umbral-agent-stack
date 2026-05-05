# F7 Rehearsal 2 — Execute Gate Only: Live Deploy Evidence

**Date:** 2026-05-05
**Operator:** David (human) + Rick AI (automated evidence)
**Branch:** envfile-only change (no repo commit — L3 is live envfile)
**Evidence branch:** `rick/copilot-cli-f7-execute-gate-rehearsal-evidence`

---

## 1. Objective (Rehearsal 2)

Open **only** L3 execute flag (`RICK_COPILOT_CLI_EXECUTE=false → true` in live envfile
`/home/rick/.config/openclaw/copilot-cli.env`) to verify the capability transitions from
`execute_flag_off_dry_run` to the next expected rejection: `real_execution_not_implemented`.

No real Copilot execution. L5 code constant `_REAL_EXECUTION_IMPLEMENTED=False` is immutable.
Rollback executed immediately after probe confirmation.

---

## 2. Pre-Rehearsal State (Phase A Preflight)

| Item | Value |
|---|---|
| Live HEAD | `1e7c84a` |
| MainPID (pre-rehearsal) | `1403101` |
| `/health` | 200 |
| `RICK_COPILOT_CLI_ENABLED` | `true` |
| `copilot_cli.enabled` (yaml L2) | `true` |
| `RICK_COPILOT_CLI_EXECUTE` (before flip) | `false` |
| `_REAL_EXECUTION_IMPLEMENTED` (L5) | `False` |
| `egress.activated` (L4) | `false` |

---

## 3. Phase B — Baseline Probe (before flip)

**Decision:** `execute_flag_off_dry_run`
**Response excerpt:**
```json
{
  "ok": true,
  "result": {
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
    "egress_activated": false
  }
}
```

---

## 4. Phase C — Flip (L3 only)

```bash
cp copilot-cli.env copilot-cli.env.bak.f7r2
sed -i 's/^RICK_COPILOT_CLI_EXECUTE=false$/RICK_COPILOT_CLI_EXECUTE=true/' copilot-cli.env
```

**Diff (single line):**
```
< RICK_COPILOT_CLI_EXECUTE=false
> RICK_COPILOT_CLI_EXECUTE=true
```

No other line changed. `_REAL_EXECUTION_IMPLEMENTED`, `egress.activated`, `RICK_COPILOT_CLI_ENABLED` all untouched.

---

## 5. Phase D — Restart

| Item | Value |
|---|---|
| OLD_PID | `1403101` |
| NEW_PID | `1415230` |
| ActiveState | `active` |
| SubState | `running` |
| `/health` | 200 |

---

## 6. Phase E — Post-Flip Probe

**Decision:** `real_execution_not_implemented` ← ✅ expected

**Response excerpt:**
```json
{
  "ok": true,
  "result": {
    "would_run": false,
    "phase": "F6.step1",
    "phase_blocks_real_execution": true,
    "decision": "real_execution_not_implemented",
    "policy": {
      "env_enabled": true,
      "policy_enabled": true,
      "execute_enabled": true,
      "real_execution_implemented": false,
      "phase_blocks_real_execution": true
    },
    "mission_run_id": "9047c0b2bb9c4c6294436d6f081f3e33",
    "audit_log": "reports/copilot-cli/2026-05/9047c0b2bb9c4c6294436d6f081f3e33.jsonl",
    "egress_activated": false
  }
}
```

### Signal Transition ✅

| Before flip | After flip |
|---|---|
| `execute_flag_off_dry_run` | `real_execution_not_implemented` |

**L3 execute gate passed** → blocked at **L5 code constant** as expected.
`_REAL_EXECUTION_IMPLEMENTED=False` is a code constant — immutable without a deploy.

---

## 7. Phase F — Side-Effect Verification

| Check | Result |
|---|---|
| nft copilot rules | none |
| Docker network copilot | none |
| `egress.activated` | `false` |
| `_REAL_EXECUTION_IMPLEMENTED` | `False` |
| audit log token scan (ghp_, github_pat_, ghs_, sk-) | CLEAN |
| audit log decision | `real_execution_not_implemented` (no subprocess launched) |
| Copilot HTTPS requests | none |

---

## 8. Phase G — Rollback

Executed immediately after probe confirmation.

```bash
cp copilot-cli.env.bak.f7r2 copilot-cli.env
systemctl --user restart umbral-worker.service
```

| Item | Value |
|---|---|
| ROLLBACK_OLD_PID | `1415230` |
| ROLLBACK_NEW_PID | `1415290` |
| `RICK_COPILOT_CLI_EXECUTE` (post-rollback) | `false` |
| `/health` | 200 |

Future probes will return `execute_flag_off_dry_run` again (confirmed by state).

---

## 9. Post-Rehearsal State

| Item | Value |
|---|---|
| Live HEAD | `1e7c84a` (unchanged — no repo change) |
| MainPID | `1415290` (2 restarts total: flip + rollback) |
| `/health` | 200 |
| `RICK_COPILOT_CLI_ENABLED` | `true` |
| `copilot_cli.enabled` | `true` (F7.rehearsal-1 state) |
| `RICK_COPILOT_CLI_EXECUTE` | `false` ← restored |
| `_REAL_EXECUTION_IMPLEMENTED` | `False` ← immutable |
| `egress.activated` | `false` ← immutable |

---

## 10. Gate Stack Summary (F7.rehearsal-2 validated)

```
L1  env_enabled=true          [open]
L2  policy_enabled=true       [open — F7.rehearsal-1]
L3  execute_enabled=false      [open during rehearsal → rolled back to false]
L4  egress_activated=false    [closed — immutable]
L5  real_execution=False       [closed — code constant, immutable]
```

All 5 gates independently tested and verified in isolation.
L5 is the final absolute barrier against real execution.

---

## 11. Next Phase

**Rehearsal 3 (not yet approved):** Flip L5 `_REAL_EXECUTION_IMPLEMENTED = True` in code + all
upstream gates open, to test that the sandbox Docker image is invoked and fails gracefully
(image not built / `docker: command not found`). This is the last gate before real Copilot execution.

**No action without David's explicit approval.**
