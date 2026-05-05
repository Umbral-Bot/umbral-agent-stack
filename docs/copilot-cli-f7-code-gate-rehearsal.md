# F7 Rehearsal 5A — Code Gate Open, Env Execute Gate Still Closed

**Date:** 2026-05-05
**Branch:** `rick/copilot-cli-f7-code-gate-rehearsal`
**Base HEAD:** `6282da6`

---

## Purpose

Open the last code-side constant (`_REAL_EXECUTION_IMPLEMENTED = True`) after
completing all four hardware/network rehearsals (4A sandbox image, 4B egress
parse-check, 4C nft live apply + rollback). This is a **code-only PR** — no
live flag flip, no nft apply, no Docker network, no Copilot execution.

After this PR merges and deploys, the live system should still respond:

```
decision: execute_flag_off_dry_run
would_run: false
execute_enabled: false
real_execution_implemented: true
```

L3 (`RICK_COPILOT_CLI_EXECUTE=false`) wins over L5 because the gate check
order is:

```python
if not execute_enabled:               # L3 checked FIRST → blocks
    decision = "execute_flag_off_dry_run"
elif not _REAL_EXECUTION_IMPLEMENTED: # L5 checked SECOND — now True, never reached
    decision = "real_execution_not_implemented"
else:
    decision = "would_run_dry_run" if dry_run else "would_run_blocked_phase_f3"
```

---

## What Changed

| File | Change |
|---|---|
| `worker/tasks/copilot_cli.py` | `_REAL_EXECUTION_IMPLEMENTED = False → True` |
| `tests/test_copilot_cli.py` | Update 4 assertions; add `test_f7_5a_*` tests |

### Code change (single line)

```python
# Before (F6/F7.1–4C)
_REAL_EXECUTION_IMPLEMENTED = False

# After (F7 rehearsal 5A)
_REAL_EXECUTION_IMPLEMENTED = True
```

### Test updates

| Test name | Change |
|---|---|
| `test_f6_real_execution_implemented_constant_is_false` | Renamed to `…_is_true`, assertion flipped |
| `test_f4_master_switch_still_off` | L5 assertion updated to `is True`; L3/L4 assertions unchanged |
| `test_f7_rehearsal_real_execution_constant_still_false` | Renamed to `…_now_true`, assertion flipped |
| `test_f6_execute_flag_on_still_blocked_by_real_execution_constant` | Updated: with L5=True + L3=True, decision is `would_run_dry_run` (subprocess mocked) |
| `test_f7_5a_code_gate_open_but_execute_env_gate_blocks` | **NEW**: L5=True, L3=False → `execute_flag_off_dry_run` (subprocess explosion guard active) |

---

## Expected Post-Deploy Signal

Deploy to live worker, then probe with task `copilot_cli.run` and
`RICK_COPILOT_CLI_EXECUTE=false`. Expected response:

```json
{
  "ok": true,
  "would_run": false,
  "decision": "execute_flag_off_dry_run",
  "policy": {
    "execute_enabled": false,
    "real_execution_implemented": true,
    "phase_blocks_real_execution": true
  }
}
```

Previously `decision` was also `execute_flag_off_dry_run` (L3 blocked),
and `real_execution_implemented` was `false`. After 5A, the only visible
difference is `real_execution_implemented: true`.

---

## Rollback

If this PR causes any issues, revert the constant:

```python
_REAL_EXECUTION_IMPLEMENTED = False
```

And restore the previous test assertions. This reverts to F7.4C state
(`execute_flag_off_dry_run` with L5=False).

---

## Next Rehearsal: 5B — Full Execution One-Shot

**5B requires ALL of the following before being attempted:**

1. David explicit approval for L3 flip (`RICK_COPILOT_CLI_EXECUTE=true`).
2. Resolver run to populate `copilot_v4`/`copilot_v6` nft sets with real IPs.
3. Live `nft -f` apply of `copilot_egress` table (from 4C procedure).
4. Docker network `copilot_egress` create.
5. One-shot probe with dry_run=false.
6. Immediate rollback: nft delete, Docker network rm, L3 re-close.
7. Evidence docs committed.

**5B is NOT started in this PR. This PR STOPS at L5=True + L3=False.**

---

## Gate Stack After 5A Deploy

| Layer | Gate | State |
|---|---|---|
| L1 | `RICK_COPILOT_CLI_ENABLED` | `true` (envfile) |
| L2 | `copilot_cli.enabled` in yaml | `true` |
| L3 | `RICK_COPILOT_CLI_EXECUTE` | **`false`** (envfile — CLOSED) |
| L4 | `copilot_cli.egress.activated` | `false` (yaml — CLOSED) |
| L5 | `_REAL_EXECUTION_IMPLEMENTED` | **`True`** ← opened by this PR |
