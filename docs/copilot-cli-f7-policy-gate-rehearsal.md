# F7 rehearsal 1 — policy gate only (`copilot_cli.enabled=true`)

> Status: **PR open, awaiting review/merge/deploy.**
> Scope: docs + minimal config flip + tests. **No runtime activation in this PR.**
> No Copilot HTTPS, no nft, no Docker network, no Notion/gates/publish.

## 1. Objective

Verify in production that flipping **only** the L2 policy gate
(`config/tool_policy.yaml :: copilot_cli.enabled`) transitions the
`copilot_cli.run` rejection from `policy_off` to the next gate in the
stack (`execute_flag_off_dry_run`), proving that the deeper gates
(L3 `RICK_COPILOT_CLI_EXECUTE`, L4 `copilot_cli.egress.activated`,
L5 `_REAL_EXECUTION_IMPLEMENTED`) hold the line independently.

This is a **rehearsal**, not an activation. No Copilot subprocess will
run. No HTTPS will leave the worker. No mutating operation is performed.

## 2. Canonical activation order vs this rehearsal

The canonical activation order documented in
[`docs/copilot-cli-f6-step6c4f-activation-playbook.md`](./copilot-cli-f6-step6c4f-activation-playbook.md)
is **G3 → G4 → G1 → G2** (egress preflight → image preflight → policy
gate → execute flag).

This rehearsal **intentionally diverges** from that order: it opens
**only G1** (policy gate) without preceding G3/G4 work. That is safe
because:

- G2 (`RICK_COPILOT_CLI_EXECUTE`) stays `false` ⇒ handler returns
  `decision="execute_flag_off_dry_run"` before constructing argv.
- L5 (`_REAL_EXECUTION_IMPLEMENTED`) stays `False` ⇒ even with G2 on,
  `phase_blocks_real_execution=true` and no subprocess is invoked.
- L4 (`copilot_cli.egress.activated`) stays `false` ⇒ no nft/Docker
  egress is opened.
- The handler does not invoke any I/O beyond writing the audit JSONL.

The point of the rehearsal is to **observe the gate transition signal
in live**, not to begin activation.

## 3. Scope of this PR

Single behavioural change:

```yaml
# config/tool_policy.yaml
copilot_cli:
  enabled: true                     # MASTER SWITCH — F7 rehearsal 1
```

Plus:

- This document.
- D29 entry + §11 row in `docs/copilot-cli-capability-design.md`.
- Test updates in `tests/test_copilot_cli.py`:
  - `test_capability_disabled_when_policy_off` now monkeypatches the
    policy gate to False so the assertion still holds independent of
    the yaml default.
  - `test_f4_master_switch_still_off` repurposed to assert that L2 is
    open (rehearsal contract) **and** L4/L5 remain closed.
  - 4 new `test_f7_rehearsal_*` tests pin the rehearsal contract.

## 4. Gates state matrix (post-merge, pre-rehearsal-deploy)

| Gate | Layer | Source | Required value | After this PR |
|------|-------|--------|----------------|---------------|
| G0 capability env | L1 | `RICK_COPILOT_CLI_ENABLED` | `true` | `true` (unchanged, set since F6.6C-4D) |
| G1 policy enabled | L2 | `config/tool_policy.yaml :: copilot_cli.enabled` | `true` (rehearsal) | **`true`** (this PR) |
| G2 execute flag | L3 | `RICK_COPILOT_CLI_EXECUTE` | `false` | `false` (unchanged) |
| G3 egress activated | L4 | `config/tool_policy.yaml :: copilot_cli.egress.activated` | `false` | `false` (unchanged) |
| G4 real execution constant | L5 | `worker/tasks/copilot_cli.py :: _REAL_EXECUTION_IMPLEMENTED` | `False` | `False` (unchanged) |

All execution paths are still blocked. The only observable change after
deploy is the **decision string** returned by `copilot_cli.run`.

## 5. Expected probe behaviour after deploy

Before deploy (current live, `73ae88b`):

```json
{
  "ok": false,
  "error": "capability_disabled",
  "reason": "policy_off",
  "would_run": false,
  "policy": { "env_enabled": true, "policy_enabled": false }
}
```

After deploy (live pulls this PR + restart):

```json
{
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
  }
}
```

If the response after deploy does NOT match the second shape exactly,
treat as anomaly and execute rollback (§7) immediately.

## 6. Deploy procedure (post-merge — separate operator step)

1. In `/home/rick/umbral-agent-stack`:

   ```bash
   git ls-remote origin refs/heads/main
   git fetch origin refs/heads/main:refs/remotes/origin/main
   git status --short
   git pull --ff-only origin main
   ```

2. **One** restart of the worker service:

   ```bash
   systemctl --user restart umbral-worker.service
   ```

3. Probe:

   ```bash
   curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8088/health
   curl -s -X POST http://127.0.0.1:8088/run \
     -H "Authorization: Bearer $WORKER_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"task":"copilot_cli.run","input":{"mission":"research","prompt":"rehearsal probe"}}' \
     | jq .
   ```

4. Verify `decision == "execute_flag_off_dry_run"`. Capture
   evidence as `docs/copilot-cli-f7-rehearsal-1-deploy-evidence.md`
   in a follow-up PR (post-merge evidence pattern, same as 6C-4E).

## 7. Rollback

If the deployed behaviour is anomalous (anything other than the
expected shape in §5), revert immediately:

- Open emergency PR setting `copilot_cli.enabled: false` in
  `config/tool_policy.yaml`, OR
- On the live worktree, pin the file locally and restart only after
  cherry-picking the revert. Do **not** touch any other gate.

There is no irreversible state to undo: no token has been used, no
subprocess invoked, no remote call made. Rollback is a single yaml
flip plus one worker restart.

## 8. Invariants this rehearsal must preserve

- `RICK_COPILOT_CLI_EXECUTE=false`
- `_REAL_EXECUTION_IMPLEMENTED=False`
- `copilot_cli.egress.activated=false`
- No Copilot HTTPS, no nft rules, no Docker network change.
- No Notion writes, no gates flips, no publish.
- No token printed in logs (audit log redacts `_redact()`).
- Live `umbral-worker.service` PID changes only at the deploy step
  restart; `/health` returns 200 throughout.

## 9. References

- [`docs/copilot-cli-capability-design.md`](./copilot-cli-capability-design.md) — master design (D29 added).
- [`docs/copilot-cli-f6-step6c4f-activation-playbook.md`](./copilot-cli-f6-step6c4f-activation-playbook.md) — canonical activation playbook.
- [`docs/copilot-cli-f6-step6c4d-live-deploy-evidence.md`](./copilot-cli-f6-step6c4d-live-deploy-evidence.md) — last live deploy evidence (worker now serves the handler).
- `worker/tasks/copilot_cli.py` — gate stack implementation.
- `tests/test_copilot_cli.py` — `test_f7_rehearsal_*` contract.
