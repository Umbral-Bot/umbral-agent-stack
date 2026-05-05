# F7 Rehearsal 5A — Code Gate Open, Env Execute Gate Still Closed

**Date:** 2026-05-05
**Branch:** `codex/f7-5a-code-gate-2026-05-05`
**Base:** current `origin/main` after F7.5 yellow evidence and F8 spec

---

## Purpose

Open the final code-side gate:

```python
_REAL_EXECUTION_IMPLEMENTED = True
```

This is not a real execution step. L3 remains the operator kill-switch:

```ini
RICK_COPILOT_CLI_EXECUTE=false
```

After this PR is deployed to the live worker, the expected signal is:

```json
{
  "decision": "execute_flag_off_dry_run",
  "would_run": false,
  "policy": {
    "execute_enabled": false,
    "real_execution_implemented": true
  }
}
```

That signal proves the deployed code can pass L5, while L3 still blocks any
subprocess or Copilot CLI invocation.

---

## What changed

| File | Change |
|---|---|
| `worker/tasks/copilot_cli.py` | `_REAL_EXECUTION_IMPLEMENTED = False -> True` |
| `tests/test_copilot_cli.py` | Update gate expectations and add L5-open/L3-closed guard test |
| `docs/copilot-cli-capability-design.md` | Add D36 and phase-row entry |

---

## Gate order after 5A

The handler still evaluates L3 before L5:

```python
if not execute_enabled:
    decision = "execute_flag_off_dry_run"
elif not _REAL_EXECUTION_IMPLEMENTED:
    decision = "real_execution_not_implemented"
else:
    decision = "would_run_dry_run" if dry_run else "would_run_blocked_phase_f3"
```

Therefore, with L3 false:

- Docker subprocess is not invoked.
- Copilot HTTPS is not attempted.
- nft/Docker egress is not needed for the probe.
- The expected post-deploy probe remains `execute_flag_off_dry_run`.

---

## Validation contract

Local tests must prove:

- L5 is now `True`.
- L4 egress remains `false`.
- L3 default remains `false`.
- L5 true + L3 false returns `execute_flag_off_dry_run`.
- L5 true + L3 true + `dry_run=True` returns `would_run_dry_run` without
  launching subprocess.

Post-deploy VPS validation is delegated to Copilot-VPS in a separate task.

---

## Explicit non-goals

This PR does not:

- flip `RICK_COPILOT_CLI_EXECUTE`;
- activate `copilot_cli.egress.activated`;
- apply nft;
- create Docker network;
- run Copilot;
- consume Copilot tokens;
- write artifacts through Copilot CLI;
- touch Notion, publish, GitHub PRs, or external channels.

---

## Rollback

Rollback is one code revert:

```python
_REAL_EXECUTION_IMPLEMENTED = False
```

Then deploy and restart the worker. Expected signal returns to:

```json
{
  "decision": "execute_flag_off_dry_run",
  "policy": {
    "execute_enabled": false,
    "real_execution_implemented": false
  }
}
```

---

## Next step after merge

Copilot-VPS must:

1. Pull `main`.
2. Restart `umbral-worker.service` once.
3. Verify L3 remains false in process env.
4. Verify L5 is true in checked-out code.
5. Probe `copilot_cli.run`.
6. Confirm decision remains `execute_flag_off_dry_run`.
7. Commit evidence in a new PR.

No F7.5 green run is attempted in this step.
