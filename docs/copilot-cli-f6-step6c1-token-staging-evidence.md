# Copilot CLI — F6 Step 6C-1 Evidence: Token Staging (verification only)

**Phase:** F6 step 6C-1 — operator pasted the real fine-grained PAT v2
into the staged secrets envfile. Verification ONLY. **No worker
restart. No flag flip. No Copilot HTTPS. No egress activation.**

**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability remains DISABLED at four layers
(`RICK_COPILOT_CLI_ENABLED=false`, `RICK_COPILOT_CLI_EXECUTE=false`,
`copilot_cli.enabled=false`, `_REAL_EXECUTION_IMPLEMENTED=False`).
`copilot_cli.egress.activated=false`. Live `umbral-worker.service`
process `MainPID=675339` is **identical** to the value captured in
F6 step 6B — no restart since staging.

The token value is **never** printed in this document, in the
verifier output, in commits, or in command transcripts. Only
metadata (presence, length, prefix shape) is recorded.

---

## 1. Operator action (out-of-band)

The operator opened `~/.config/openclaw/copilot-cli-secrets.env` in
`$EDITOR`, added a single uncommented line of the form
`COPILOT_GITHUB_TOKEN=github_pat_…`, and saved. No shell history
echo. No copy-paste through chat. The agent never saw the value.

## 2. File metadata

```
$ stat -c '%U %G %a %n  size=%s' ~/.config/openclaw/copilot-cli-secrets.env
rick rick 600 /home/rick/.config/openclaw/copilot-cli-secrets.env  size=1129
```

Owner / group / mode unchanged from F6 step 6B (`rick:rick 0600`).
Size delta vs F6 step 6B is `1129 − 1075 = 54 bytes`, consistent
with one new line `COPILOT_GITHUB_TOKEN=…\n`.

## 3. Structural scan (token value NEVER printed)

```
COPILOT_GITHUB_TOKEN_present: yes
value_length_chars:           104
starts_with_github_pat_:      yes
starts_with_classic_ghp_:     no
GH_TOKEN_present:             no
GITHUB_TOKEN_present:         no
```

Classic-PAT pattern scan over the whole file (must be 0):
```
$ grep -cE '\bghp_[A-Za-z0-9]{20,}\b' ~/.config/openclaw/copilot-cli-secrets.env
0
```

The token has the fine-grained PAT v2 prefix `github_pat_` and length
in the expected range for v2 PATs. `GH_TOKEN` and `GITHUB_TOKEN` are
both absent from the secrets file (forbidden by F6 step 1 contract).

## 4. Verifier `--strict`

```
$ python scripts/verify_copilot_cli_env_contract.py \
    --runtime ~/.config/openclaw/copilot-cli.env \
    --secrets ~/.config/openclaw/copilot-cli-secrets.env \
    --strict
OK — no findings.
$ echo $?
0
```

The previous `WARN no_copilot_token` from F6 step 6B is **gone**.
There are zero errors and zero warnings.

## 5. Live worker process — token NOT loaded

```
$ systemctl --user show umbral-worker.service -p MainPID --value
675339

$ tr '\0' '\n' < /proc/675339/environ \
  | awk -F= '{print $1}' \
  | grep -E 'COPILOT|RICK_COPILOT|GH_TOKEN|GITHUB_TOKEN'
GITHUB_TOKEN
```

- `MainPID=675339` is identical to the value captured in F6 step 6B
  (and to the value captured immediately after `daemon-reload`). The
  service has **not been restarted** since the staging in step 6B.
- The live process environment contains `GITHUB_TOKEN` (variable
  name printed; value NOT printed) — but this comes from the
  **pre-existing** `EnvironmentFile=/home/rick/.config/openclaw/env`
  that the unit has loaded since long before this work. It is NOT
  from `copilot-cli-secrets.env`, which we just verified does not
  contain `GITHUB_TOKEN`.
- Crucially, `COPILOT_GITHUB_TOKEN` is **absent** from the live
  process. The token written in step 6C-1 is on disk only and has
  not been re-read by systemd into the worker, exactly as required.

## 6. Flags still false

```
$ grep -E '^(RICK_COPILOT_CLI_ENABLED|RICK_COPILOT_CLI_EXECUTE)=' \
       ~/.config/openclaw/copilot-cli.env
RICK_COPILOT_CLI_ENABLED=false
RICK_COPILOT_CLI_EXECUTE=false

$ grep -E '^(RICK_COPILOT_CLI_ENABLED|RICK_COPILOT_CLI_EXECUTE)=' .env.example
RICK_COPILOT_CLI_ENABLED=false
RICK_COPILOT_CLI_EXECUTE=false

$ grep -A2 '^copilot_cli:' config/tool_policy.yaml | head
copilot_cli:
  enabled: false                    # MASTER SWITCH — no tocar sin aprobación.
  default_max_wall_sec: 120
```

`_REAL_EXECUTION_IMPLEMENTED=False` in `worker/tasks/copilot_cli.py`
(unchanged since F6 step 1).

## 7. Live host — nothing else changed

```
$ nft list ruleset | grep -i copilot
(empty)

$ docker network ls | grep copilot
(empty)

$ systemctl --user show umbral-worker.service \
    -p ActiveState -p SubState -p MainPID
ActiveState=active
SubState=running
MainPID=675339
```

No nft rule loaded. No `copilot-egress` Docker network. Worker still
healthy, same PID, same DropInPaths.

## 8. Repo state — no token committed

The token lives ONLY in `~/.config/openclaw/copilot-cli-secrets.env`
on the live host. It is NOT in any repo file, NOT in any commit, NOT
in any shell history snippet quoted in this document.

```
$ git diff --check
(clean)

$ git status --short
 M docs/copilot-cli-capability-design.md
?? docs/copilot-cli-f6-step6c1-token-staging-evidence.md
```

Secret scan over staged + tracked files:
```
$ git diff | grep -iE 'ghp_[A-Za-z0-9]{20}|github_pat_[A-Za-z0-9]{30}|ghs_[A-Za-z0-9]{20}'
(empty)
```

## 9. Summary table

| Check | Result |
|---|---|
| Token real staged on host | yes |
| Token value printed by agent | **no** |
| Token committed to repo | **no** |
| Verifier `--strict` exit | 0 |
| `WARN no_copilot_token` | **gone** |
| Worker restarted | **no** (MainPID 675339 unchanged) |
| Worker process contains `COPILOT_GITHUB_TOKEN` | **no** |
| Worker process contains `GITHUB_TOKEN` | yes (pre-existing, from `~/.config/openclaw/env`, not from this work) |
| `RICK_COPILOT_CLI_ENABLED` | false |
| `RICK_COPILOT_CLI_EXECUTE` | false |
| `copilot_cli.enabled` | false |
| `_REAL_EXECUTION_IMPLEMENTED` | False |
| `copilot_cli.egress.activated` | false |
| nft applied | no |
| Docker network created | no |
| Copilot real executed | **no** |
| Notion / gates / publish touched | no |

## 10. What F6 step 6C-1 explicitly does NOT do

- ✗ NO `systemctl --user restart umbral-worker.service`
- ✗ NO flag flip (`RICK_COPILOT_CLI_ENABLED` stays `false`)
- ✗ NO `_REAL_EXECUTION_IMPLEMENTED` flip
- ✗ NO Copilot HTTPS request
- ✗ NO `nft -f`
- ✗ NO Docker network creation
- ✗ NO token printed / logged / committed
- ✗ NO Notion / gate / publish surface touched
- ✗ NO PR open / merge / comment

## 11. F6 step 6C-2 unblock conditions

To advance to F6 step 6C-2 (intentional flag flip + restart), ALL of
the following must hold:

1. This document reviewed and approved by David.
2. Operator commits to executing only:
   - flip `RICK_COPILOT_CLI_ENABLED=true` in
     `~/.config/openclaw/copilot-cli.env` (single line, surgical
     edit)
   - then `systemctl --user restart umbral-worker.service`
3. Operator does NOT flip `RICK_COPILOT_CLI_EXECUTE`.
4. Operator does NOT flip `copilot_cli.enabled`.
5. Operator does NOT flip `_REAL_EXECUTION_IMPLEMENTED` in code.
6. Egress remains inactive.
7. After restart:
   - `systemctl --user show umbral-worker.service -p MainPID`
     → new PID expected.
   - `tr '\0' '\n' < /proc/<new_pid>/environ | awk -F= '{print $1}' |
      grep -E 'COPILOT_GITHUB_TOKEN|RICK_COPILOT_CLI_ENABLED'`
     → both names expected (values NOT printed).
   - Worker `/health` still 200.
   - Submitting a `copilot_cli` task to the worker MUST be rejected
     by the layer-3 gate (`_REAL_EXECUTION_IMPLEMENTED=False` →
     `phase_blocks_real_execution`), proving real execution is still
     blocked at the implementation layer even with two of the four
     flags now true.

## 12. F6 step 6C-2 recommendation (DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 6C-2: operator flips ONLY
> `RICK_COPILOT_CLI_ENABLED=true` in
> `~/.config/openclaw/copilot-cli.env` and runs
> `systemctl --user restart umbral-worker.service` once. Agent then
> proves (a) the new MainPID has loaded `COPILOT_GITHUB_TOKEN` and
> `RICK_COPILOT_CLI_ENABLED=true` (names only, values NOT printed),
> (b) the layer-3 gate `phase_blocks_real_execution` still rejects
> any `copilot_cli` task because `_REAL_EXECUTION_IMPLEMENTED=False`
> and `RICK_COPILOT_CLI_EXECUTE=false`. NO Copilot HTTPS request.
> No egress. No Notion / no gates / no publish.
