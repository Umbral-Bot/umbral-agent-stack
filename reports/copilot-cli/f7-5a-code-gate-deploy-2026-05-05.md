# F7.5A Code Gate Deploy — VPS evidence

**Date:** 2026-05-05T22:47:46Z
**Executed by:** copilot-vps
**Repo HEAD (main):** `4b4b70af63835586434419e054af12a89c520fbc`
**PR merged:** #291 (`[F7.5A] Copilot CLI — open code gate only`)
**Commit (5A change):** `0d6ad83`

---

## Verdict

🟢 **VERDE**

L5 (`_REAL_EXECUTION_IMPLEMENTED`) successfully flipped to `True` after
deploy. Worker restarted once. Probe confirms `execute_flag_off_dry_run` with
`real_execution_implemented=true` and `execute_enabled=false`. No nft table,
no Docker network, no token leak, no subprocess invocation.

---

## Executive summary

- `git pull --ff-only origin main` brought HEAD to `4b4b70a` (includes PR #291).
- `worker/tasks/copilot_cli.py` line 52: `_REAL_EXECUTION_IMPLEMENTED = True` confirmed.
- Worker restarted once: PID `1418206 → 1438752`. Health HTTP 200 after restart.
- Post-restart process env confirms L3 still `RICK_COPILOT_CLI_EXECUTE=false`.
- Task probe (`copilot_cli.run`, `dry_run=true`) returned:
  - `decision: execute_flag_off_dry_run` ✅
  - `real_execution_implemented: true` ✅
  - `execute_enabled: false` ✅
  - `would_run: false` ✅
  - `egress_activated: false` ✅
- No nft `copilot_egress` table live. No Docker copilot network.
- Audit JSONL `d2563823682948448bb3fc395061b3dd.jsonl` — token scan clean.
- Journal shows `copilot_cli.run` task executed at `18:47:46`, returned 200 OK.
- No subprocess, no Copilot HTTPS, no token printed.

---

## Gate matrix

| Layer | Repo/envfile dice | VPS muestra | Match | Evidence |
|---|---|---|---|---|
| **L1** `RICK_COPILOT_CLI_ENABLED` | `true` (envfile) | `true` (process `/proc/1438752/environ`) | ✅ OPEN | `awk` filter on process env |
| **L2** `copilot_cli.enabled` | `true` (config/tool_policy.yaml) | `true` (HEAD `4b4b70a`) | ✅ OPEN | `grep -A12 '^copilot_cli:'` |
| **L3** `RICK_COPILOT_CLI_EXECUTE` | `false` (envfile) | `false` (process `/proc/1438752/environ`) | ✅ **CLOSED** | process env post-restart — **blocks execution** |
| **L4** `egress.activated` | `false` (config/tool_policy.yaml) | no nft table; no Docker copilot network | ✅ **CLOSED** | `sudo nft list table inet copilot_egress` → not found |
| **L5** `_REAL_EXECUTION_IMPLEMENTED` | `True` (worker/tasks/copilot_cli.py line 52) | `True` (live code after restart, probe confirms `real_execution_implemented: true`) | ✅ **OPEN** | grep line 52 + probe response field |

---

## Restart evidence

| Field | Value |
|---|---|
| OLD_PID | `1418206` |
| NEW_PID | `1438752` |
| restart count | exactly 1 |
| ActiveState after restart | `active` |
| SubState after restart | `running` |
| /health after restart | HTTP 200 |

---

## Probe evidence

**Request:** `POST /run` with `task=copilot_cli.run`, `mission=research`, `dry_run=true`, `requested_operations=["read_repo"]`

**Response summary (no secrets):**

```json
{
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
      "real_execution_implemented": true,
      "phase_blocks_real_execution": true
    },
    "mission": "research",
    "mission_run_id": "d2563823682948448bb3fc395061b3dd",
    "egress_activated": false,
    "operations": {
      "requested": ["read_repo"],
      "decision": "allowed"
    }
  }
}
```

---

## Run fields

| Field | Value |
|---|---|
| batch_id | n/a — no real run |
| agent_id | n/a — no real run |
| mission_run_id | `d2563823682948448bb3fc395061b3dd` (probe audit entry) |
| tokens | 0 (no Copilot HTTPS, no subprocess) |
| cost_usd | $0.00 |
| exit_code | n/a (no subprocess invoked) |
| duration_sec | n/a (no real run) |
| artifacts | n/a |

---

## Logs

### Worker journal (around copilot_cli.run)

```
May 05 18:47:46 srv1431451 python[1438752]: Executing task: copilot_cli.run
  (task_id=62448599-9bd4-43c7-a30c-f9c80b745fde, trace=c610707e-7f65-4ba3-bc36-0aa73ec1d835)
May 05 18:47:46 srv1431451 python[1438752]: INFO: 127.0.0.1:33524 - "POST /run HTTP/1.1" 200 OK
```

No subprocess invocation. No Docker. No network calls to GitHub/Copilot.

### Audit JSONL

- **Path:** `reports/copilot-cli/2026-05/d2563823682948448bb3fc395061b3dd.jsonl`
- **Token scan:** clean (no `ghp_*`, `github_pat_*`, `ghs_*`, `sk-*` patterns)

### Side-effect checks

```
sudo nft list table inet copilot_egress → no copilot nft table ✅
docker network ls | grep copilot        → no copilot docker network ✅
audit token scan                        → clean ✅
process RICK_COPILOT_CLI_EXECUTE=false  → confirmed in /proc/1438752/environ ✅
```

---

## Decision tree confirmation

With L5=True and L3=False, the handler followed:

```python
if not execute_enabled:  # L3=False → True, this branch taken
    decision = "execute_flag_off_dry_run"
# L5 branch (elif not _REAL_EXECUTION_IMPLEMENTED) never reached
```

This confirms the gate precedence design: L3 blocks independently of L5 state.
The 5A rehearsal hypothesis is validated in production.

---

## Lessons learned

1. **L5 flip confirmed safe.** Opening `_REAL_EXECUTION_IMPLEMENTED=True` in
   code does NOT change the runtime decision when L3=False. The `execute_flag_off_dry_run`
   path is taken before L5 is checked.

2. **Single restart sufficient.** `systemctl --user restart umbral-worker.service`
   picked up the new code from disk in one shot, PID changed cleanly.

3. **Token plumbing confirmed.** `COPILOT_GITHUB_TOKEN=present_by_name` in process
   env persisted through restart — EnvironmentFile drop-in loaded correctly.

4. **Zero Copilot HTTPS calls.** Journal confirms no outbound requests to
   `api.githubcopilot.com` or `api.github.com` during the probe.

---

## Next steps for F8

To proceed to F8 (first real run):

1. **David explicit L3 flip:** `RICK_COPILOT_CLI_EXECUTE=false → true` in
   `/home/rick/.config/openclaw/copilot-cli.env` + worker restart.
2. **Egress provisioning before L3 flip:**
   - Run `scripts/copilot_egress_resolver.py` to populate IP sets.
   - `sudo nft -f` to apply `copilot_egress` table.
   - Confirm `copilot_v4`/`copilot_v6` sets populated with real IPs.
   - Optionally: `docker network create copilot_egress` if sandbox requires it.
3. **One-shot scratch run** with exactly one trivial prompt.
4. **Immediate rollback:** L3 → false, nft delete table, restart worker.
5. **Commit evidence** with all 8 traceable fields.

The 5-gate infrastructure is now at final pre-execution state:
- L1 ✅ OPEN · L2 ✅ OPEN · L3 ❌ CLOSED · L4 ❌ CLOSED · L5 ✅ OPEN
- Only L3 and L4 stand between current state and first real Copilot run.

---

## Second-run addendum (2026-05-05T22:48:49Z)

A second verification pass was performed in this same session after the report
above was committed:

- **Restart:** OLD_PID `1438752` → NEW_PID `1438899` (worker active/running, HTTP 200)
- **Probe** `mission_run_id: 52865bcdc228426a84bfc55f158e10f6` — same results:
  `decision=execute_flag_off_dry_run`, `real_execution_implemented=true`,
  `execute_enabled=false`, `would_run=false`, `egress_activated=false`
- **Side-effects:** no nft table, no Docker network, audit token scan clean
- **Process env (PID 1438899):** `RICK_COPILOT_CLI_EXECUTE=false` confirmed

Verdict unchanged: 🟢 **VERDE**
