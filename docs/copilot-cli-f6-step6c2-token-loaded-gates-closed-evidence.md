# Copilot CLI — F6 Step 6C-2 Evidence: Token Loaded into Worker, Gates Stay Closed

**Phase:** F6 step 6C-2 — flip ONE flag (`RICK_COPILOT_CLI_ENABLED=true`),
restart `umbral-worker.service` once, prove the running process now
holds `COPILOT_GITHUB_TOKEN`, and prove that **no Copilot HTTPS
request can occur** because every other gate stays closed.

**Branch:** `rick/copilot-cli-capability-design`
**HEAD before this evidence:** `f245e26`

---

## 1. Surgical config change

Single line in `~/.config/openclaw/copilot-cli.env`:

```diff
-RICK_COPILOT_CLI_ENABLED=false
+RICK_COPILOT_CLI_ENABLED=true
 RICK_COPILOT_CLI_EXECUTE=false
```

```
$ stat -c '%U %G %a %n' ~/.config/openclaw/copilot-cli.env
rick rick 600 /home/rick/.config/openclaw/copilot-cli.env
```

Backup `~/.config/openclaw/copilot-cli.env.bak.6c2` retained for
rollback. No other file edited. No other variable changed.

## 2. Single restart

```
OLD_PID=675339
$ systemctl --user restart umbral-worker.service
NEW_PID=1114334
ActiveState=active
SubState=running
```

PID changed → restart confirmed (only one). Worker `/health` →
`HTTP 200`.

## 3. New process environment — names only, values never printed

```
$ tr '\0' '\n' < /proc/1114334/environ \
  | awk -F= '{print $1}' \
  | grep -E '^(COPILOT_GITHUB_TOKEN|RICK_COPILOT_CLI_ENABLED|RICK_COPILOT_CLI_EXECUTE|GITHUB_TOKEN)$' | sort -u
COPILOT_GITHUB_TOKEN
GITHUB_TOKEN
RICK_COPILOT_CLI_ENABLED
RICK_COPILOT_CLI_EXECUTE
```

`COPILOT_GITHUB_TOKEN` is now in the worker process env (loaded by
systemd via the user-scope drop-in's
`EnvironmentFile=-/home/rick/.config/openclaw/copilot-cli-secrets.env`).
The token value is never printed.

The values for `RICK_COPILOT_CLI_*` come from the runtime envfile,
which we control directly:

```
$ grep -E '^(RICK_COPILOT_CLI_ENABLED|RICK_COPILOT_CLI_EXECUTE)=' \
       ~/.config/openclaw/copilot-cli.env
RICK_COPILOT_CLI_ENABLED=true
RICK_COPILOT_CLI_EXECUTE=false
```

## 4. Repo-side gates — still closed

```
$ grep -A2 '^copilot_cli:' config/tool_policy.yaml | head
copilot_cli:
  enabled: false                    # MASTER SWITCH — no tocar sin aprobación.
  default_max_wall_sec: 120

$ grep '^_REAL_EXECUTION_IMPLEMENTED' worker/tasks/copilot_cli.py
_REAL_EXECUTION_IMPLEMENTED = False

$ grep 'activated' config/tool_policy.yaml | head
    activated: false
```

So three of the four flags remain `false` / `False`:

| Gate | Value |
|---|---|
| `RICK_COPILOT_CLI_ENABLED` (env, layer 1) | **true** ← only this flipped |
| `copilot_cli.enabled` (policy, layer 2) | false |
| `RICK_COPILOT_CLI_EXECUTE` (env, layer 3a) | false |
| `_REAL_EXECUTION_IMPLEMENTED` (code, layer 3b) | False |
| `copilot_cli.egress.activated` (policy, network) | false |

## 5. Probe 1 — live worker rejects the task entirely

The live `umbral-worker.service` runs from `/home/rick/umbral-agent-stack/`
on branch `main` at HEAD `e6128bc` — it does not even contain the
`copilot_cli.run` handler. This is an **additional safety layer**
not assumed by the design but observed empirically.

```
$ curl -s -X POST http://127.0.0.1:8088/run \
    -H "Authorization: Bearer $WORKER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"task":"copilot_cli.run","input":{"mission":"research","prompt":"hello","requested_operations":["read_repo"]}}'
{"detail":"Unknown task: copilot_cli.run. Available: ['ping', ...]"}
```

So even if a caller had the worker token AND knew the task name AND
`RICK_COPILOT_CLI_ENABLED=true` is now in the worker's env, the live
worker would reject at the route layer. There is no execution path
through the live worker.

## 6. Probe 2 — handler-level rejection in F6 branch code

To exercise the actual gate logic (which would run if the F6 branch
were the deployed worker), we invoke the handler directly from the
F6 worktree, simulating the worker's env (`RICK_COPILOT_CLI_ENABLED=true`,
`RICK_COPILOT_CLI_EXECUTE=false`):

```
$ RICK_COPILOT_CLI_ENABLED=true RICK_COPILOT_CLI_EXECUTE=false \
  python -c "from worker.tasks.copilot_cli import handle_copilot_cli_run; \
             import json; print(json.dumps(handle_copilot_cli_run({ \
               'mission':'research','prompt':'hello', \
               'requested_operations':['read_repo']}), indent=2))"
{
  "ok": false,
  "error": "capability_disabled",
  "capability": "copilot_cli",
  "reason": "policy_off",
  "would_run": false,
  "audit_log": ".../reports/copilot-cli/2026-04/e63f1….jsonl",
  "mission_run_id": "e63f112cfc5841a49cb94c798ada2b93",
  "policy": { "env_enabled": true, "policy_enabled": false }
}
```

Reason advances from `env_flag_off` (when env flag is false) to
`policy_off` (when env true but `copilot_cli.enabled=false`). That's
the expected gate-2 rejection.

## 7. Audit log — token NOT recorded

```
$ grep -cE 'github_pat_[A-Za-z0-9_]{30,}|ghp_[A-Za-z0-9_]{20,}|ghs_[A-Za-z0-9_]{20,}' \
       reports/copilot-cli/2026-04/e63f1…jsonl
0
```

Audit record (token-shaped patterns redacted defensively, though
none exist):

```json
{
  "decision": "capability_disabled_policy",
  "dry_run": true,
  "mission": "research",
  "phase": "F3",
  "policy": {
    "egress_activated": false,
    "env_enabled": true,
    "execute_enabled": false,
    "missions_count": 4,
    "phase_blocks_real_execution": true,
    "policy_enabled": false,
    "real_execution_implemented": false
  },
  "prompt_summary": "hello",
  "task": "copilot_cli.run",
  "ts": "2026-04-27T03:29:55+00:00"
}
```

`reports/copilot-cli/` is gitignored (since F4) — audit logs never
reach the repo:

```
$ git check-ignore reports/copilot-cli/2026-04/e63f1….jsonl
reports/copilot-cli/2026-04/e63f1….jsonl
```

## 8. No side effects on the live host

```
$ nft list ruleset | grep -i copilot
(empty)
$ docker network ls | grep copilot
(empty)
$ systemctl --user show umbral-worker.service -p DropInPaths
DropInPaths=/home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf
```

No `nft -f`, no Docker network, no `/etc` write, no system-scope
systemd, no `gh` request, no Copilot HTTPS, no Notion write, no PR
open / merge / comment.

## 9. Summary table

| Check | Result |
|---|---|
| Token loaded into worker process | **yes** (via systemd EnvironmentFile after restart) |
| Token printed by agent | **no** |
| Token committed | **no** |
| Worker restarted | **yes** (1×) |
| OLD_PID / NEW_PID | 675339 → 1114334 |
| `RICK_COPILOT_CLI_ENABLED` | **true** (only flag flipped) |
| `RICK_COPILOT_CLI_EXECUTE` | false |
| `copilot_cli.enabled` | false |
| `_REAL_EXECUTION_IMPLEMENTED` | False |
| `copilot_cli.egress.activated` | false |
| Live worker registers `copilot_cli.run` route | **no** (live worker is on `main`, not F6) |
| Probe 1 result (live HTTP) | rejected: `Unknown task: copilot_cli.run` |
| Probe 2 result (handler in F6 worktree, env=true) | rejected: `capability_disabled / policy_off` |
| Audit log contains token | **no** (zero matches) |
| nft applied | no |
| Docker network created | no |
| Copilot HTTPS request | **no** |
| Notion / gates / publish touched | no |

## 10. What F6 step 6C-2 explicitly does NOT do

- ✗ NO `RICK_COPILOT_CLI_EXECUTE` flip (still false)
- ✗ NO `copilot_cli.enabled` flip (still false)
- ✗ NO `_REAL_EXECUTION_IMPLEMENTED` flip (still False)
- ✗ NO Copilot HTTPS request
- ✗ NO `nft -f`
- ✗ NO Docker network creation
- ✗ NO `/etc` write
- ✗ NO Notion / gates / publish surface touched
- ✗ NO PR open / merge / comment / merge

## 11. Rollback

If any anomaly is observed, rollback is one command:

```sh
cp ~/.config/openclaw/copilot-cli.env.bak.6c2 \
   ~/.config/openclaw/copilot-cli.env
systemctl --user restart umbral-worker.service
```

This restores `RICK_COPILOT_CLI_ENABLED=false` in the worker process
(token remains staged on disk; the worker simply ignores it at the
gate-1 check).

## 12. F6 step 6C-3 unblock conditions

To advance to step 6C-3 (deploy the F6 branch worker so
`copilot_cli.run` is actually registered on the live route), ALL of
the following must hold:

1. This document reviewed and approved by David.
2. F6 branch (`rick/copilot-cli-capability-design`) merged or
   selectively deployed to the worker's working tree
   (`/home/rick/umbral-agent-stack/`). Deployment plan needs its own
   step before any code is moved.
3. Egress remains inactive (`copilot_cli.egress.activated=false`).
4. `_REAL_EXECUTION_IMPLEMENTED=False` remains in code.
5. `copilot_cli.enabled=false` remains in policy.
6. After deploy + restart, the live HTTP probe must return the
   handler-level `capability_disabled / policy_off` (not
   `Unknown task`), proving the route is now mounted but the gate
   still rejects.

## 13. F6 step 6C-3 recommendation (DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 6C-3: deployment plan to land the F6 branch's
> `copilot_cli.run` handler into the live worker tree (so the route
> exists on the running worker), still with policy + execute gates
> false. Live HTTP probe should then return `capability_disabled /
> policy_off`, never `Unknown task`. NO Copilot HTTPS. NO
> `_REAL_EXECUTION_IMPLEMENTED` flip. NO egress activation. NO
> Notion / gates / publish.

**Note:** Step 6C-3 is *deployment*, which is a separate problem
from *execution*. The execution-level flag flip (`copilot_cli.enabled`
→ true) is yet another step beyond 6C-3.
