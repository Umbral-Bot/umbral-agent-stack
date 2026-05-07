# F8A run-6 after Copilot token refresh — evidence report

- Date (UTC): 2026-05-07
- Task: `.agents/tasks/f8a-run6-after-token-refresh-2026-05-07.md`
- Approval: `APPROVE_F8A_RUN6_AFTER_TOKEN_REFRESH=YES`
- Branch: `rick/f8a-run6-after-token-refresh-2026-05-07`
- main HEAD at start: `ed4e5ca` (includes #316 fixes + #318 stop evidence)
- This report continues the prior "O0 stop" evidence from PR #318 because
  token rotation later succeeded and the canonical run was executed
  end-to-end.

## Verdict

**amarillo** — infra path executed end-to-end, scoped egress activated only inside the run window, exactly one `copilot_cli.run` issued, rollback clean. Copilot CLI itself exited `1` with zero bytes on both stdout and stderr (provider/network-side limitation, no Umbral runtime regression).

## O0 — token refresh verification

Worker restarted to load the refreshed token (rotated by Rick from a separate SSH session in `/home/rick/.config/openclaw/copilot-cli-secrets.env`).

```
OLD_PID=19264 NEW_PID=19491
worker_health=200
COPILOT_GITHUB_TOKEN=present_by_name
RICK_COPILOT_CLI_EXECUTE=false
GITHUB_USER_HTTP=200
TOKEN_STATUS=valid
```

Token never printed; `present_by_name` only.

## O1 — source + gated dry-run probe

Source contract (against `worker/tasks/copilot_cli.py` on `ed4e5ca`):

| line | contract |
| --- | --- |
| 54 | `_REAL_EXECUTION_IMPLEMENTED = True` |
| 163 | `_DEFAULT_DOCKER_NETWORK = "copilot-egress"` |
| 472 | `"-i"` |
| 478 | `"--tmpfs", "/home/runner/.copilot:size=32m,mode=1777",` |
| 513 | `"prompt=$(cat \"$prompt_file\")\n"` |
| 515 | `"--prompt \"$prompt\""` |

`python3 scripts/verify_copilot_egress_contract.py` → `OK`.

Dry-run probe (`brief_id=O1`, gates closed):

```
decision=execute_flag_off_dry_run
would_run=False
execute_enabled=False
real_execution_implemented=True
egress_activated=False
```

## O2 — resolver + docker network

```
copilot_v4_count=3
copilot_v6_count=0
```

IPs resolved (from `/tmp/f8a-run6-egress.json`): `4.228.31.149`, `4.228.31.153`, `140.82.114.22`.

Docker network created by this task (`network-created-by-task=true`):

```
name=copilot-egress bridge=br-copilot icc=false
```

## O3 — backup, scoped nft, L4 open, envfile, restart, RUN

Backup directory: `/home/rick/.copilot/backups/f8a-run6-20260507T005028Z` (mode 0600, includes `copilot-cli.env`, `tool_policy.yaml`, `nft-ruleset-before.nft`).

Scoped nft installed from `infra/networking/copilot-egress.nft.example` (`forward` chain only, no host-wide `output policy drop`). Sets populated with the resolver IPs.

L4 in working tree only (`config/tool_policy.yaml`):

```
egress:
  profile_name: copilot-egress
  activated: true
  ...
```

Envfile delta (`/home/rick/.config/openclaw/copilot-cli.env`):

```
RICK_COPILOT_CLI_EXECUTE=true
COPILOT_CLI_DIAGNOSTIC_MODE=true
COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:6940cf0f274d
COPILOT_CLI_DOCKER_NETWORK=copilot-egress
```

Worker process env after restart (PID=20309):

```
process RICK_COPILOT_CLI_ENABLED=true
process RICK_COPILOT_CLI_EXECUTE=true
process COPILOT_CLI_DIAGNOSTIC_MODE=true
process COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:6940cf0f274d
process COPILOT_CLI_DOCKER_NETWORK=copilot-egress
process COPILOT_GITHUB_TOKEN=present_by_name
worker_health=200
```

## The single `copilot_cli.run`

Exactly one run was issued. Window:

```
RUN_START=2026-05-07T00:51:30Z
RUN_END  =2026-05-07T00:52:15Z
```

Result fields:

| field | value |
| --- | --- |
| `mission_run_id` | `4c00f4de3f474abdbae75252725d58a8` |
| `decision` | `completed` |
| `phase` | `F8A.real_execution` |
| `executed` | `true` |
| `exit_code` | `1` |
| `duration_sec` | `44.428` |
| `egress_activated` | `true` |
| `batch_id` | `f8a-run6-after-token-refresh` |
| `agent_id` | `copilot-vps-single-006` |
| `audit_log` | `reports/copilot-cli/2026-05/4c00f4de3f474abdbae75252725d58a8.jsonl` |
| `artifact_dir` | `artifacts/copilot-cli/2026-05/f8a-run6-after-token-refresh/copilot-vps-single-006/4c00f4de3f474abdbae75252725d58a8/` |
| `manifest` | `…/4c00f4de3f474abdbae75252725d58a8/manifest.json` |

Stdout/stderr bytes (after secret scan): both `0` (sha256 = empty-string sha256 `e3b0c44298fc…b855`). No previews to render — both files empty on disk.

Tokens / cost: `source=not_reported_by_github_copilot_cli`, all values null.

## nft counters during the window

Before: `counter packets 0 bytes 0 drop`.
After:  `counter packets 36 bytes 2160 drop`.

Drop counter increment of 36 packets / 2160 bytes was observed on the scoped DROP rule. Combined with `exit_code=1` and zero bytes of stdout/stderr from Copilot CLI, the most likely cause is Copilot CLI attempting outbound endpoints not present in the resolver set (or required IPs that drifted from the small static list of 3) and being scoped-dropped. No host-wide egress was affected.

## Worker journal window

`journalctl --user -u umbral-worker.service` between RUN_START and RUN_END only shows the routine task dispatch lines for `copilot_cli.run` (task_id=`ac52c2b4-db0e-48ea-a71e-1dd84e4e76bc`, trace_id=`1fe5d2b9-4164-4fac-853b-0851137dce29`); no exceptions, no traceback. Other concurrent tasks (`notion.read_database`) were normal.

## Audit JSONL

Two entries in `reports/copilot-cli/2026-05/4c00f4de3f474abdbae75252725d58a8.jsonl`:

1. `decision=execute_started`, `egress_activated=true`, `docker_network=copilot-egress`, `phase=F8A`.
2. `decision=completed`, `exit_code=1`, `duration_sec=44.428`, `secret_scan.status=clean`.

## Secret scans

Patterns: `ghp_…`, `github_pat_…`, `gho_…`, `ghs_…`, `ghu_…`, `sk-…(20+)`, `xoxb-…`, `AKIA…`, `-----BEGIN … PRIVATE KEY-----`.

```
stdout.txt: clean
stderr.txt: clean
manifest.json: clean
4c00f4de…58a8.jsonl: clean
f8a-run6-response.json: clean
```

Token never appeared in any captured artifact, log, or this report.

## O5 — rollback (final state)

```
worker_health=200
RICK_COPILOT_CLI_EXECUTE=false
COPILOT_CLI_DIAGNOSTIC_MODE=(absent)
config/tool_policy.yaml: egress.activated=false
nft table inet copilot_egress: (absent)
docker network copilot-egress: (absent — removed because this task created it)
no host-wide `output policy drop` introduced
```

Backup directory retained at `/home/rick/.copilot/backups/f8a-run6-20260507T005028Z`.

## Diagnosis (no second run)

- Infra path: ✓ end-to-end. Worker built the correct argv (with `-i`, `--tmpfs /home/runner/.copilot`, `--network=copilot-egress`, prompt-quoting fix, `_REAL_EXECUTION_IMPLEMENTED=True`).
- Token: ✓ valid against `https://api.github.com/user` immediately before run; passed into container by name only.
- Container exit: `1` with zero output. Wrapper redirects copilot stdout/stderr to host files; emptiness suggests early failure inside the container (e.g., copilot startup auth, telemetry, or an outbound endpoint blocked by the scoped IP set — see drop counter delta).
- Per task rule: a second `copilot_cli.run` is not allowed. Further diagnosis requires either (a) widening the resolver / IP set to include all endpoints copilot pings at startup, or (b) running the wrapper interactively in a separate diagnostic session outside the canonical task.

## Invariants honored

- Exactly one `copilot_cli.run` issued (task_id `ac52c2b4-db0e-48ea-a71e-1dd84e4e76bc`).
- L3/L4 only opened after O0=valid; closed in rollback.
- `COPILOT_CLI_DIAGNOSTIC_MODE=true` while open; absent after rollback.
- `COPILOT_CLI_DOCKER_NETWORK=copilot-egress`.
- Scoped nft only (`table inet copilot_egress`, `chain forward`); no host-wide drop.
- Token never printed; only `present_by_name`.
- Rollback complete and verified.

## Appendix — prior O0 stop evidence retained

Before this successful O0 + real-run attempt, the same task was invoked twice
while the live token was still invalid. Those attempts are part of the same
F8A run-6 lifecycle and are retained here for traceability.

### O0 stop after history recovery

PR #316 restored the canonical task, scoped egress fixes, and writable
`/home/runner/.copilot` tmpfs to `main`. The first O0 attempt after that
recovery stopped correctly before opening L3/L4:

```text
COPILOT_GITHUB_TOKEN=present_by_name
GITHUB_USER_HTTP=401
TOKEN_STATUS=invalid
error_message=Bad credentials
```

Safety state for that stop:

```text
RICK_COPILOT_CLI_ENABLED=true
RICK_COPILOT_CLI_EXECUTE=false
COPILOT_CLI_DIAGNOSTIC_MODE absent
egress.activated=false
no nft table inet copilot_egress
no docker network copilot-egress
worker /health HTTP 200
```

### O0 re-attempt before token rotation

A second O0-only re-attempt also stopped correctly. Source checks were already
good on `main` (`d3e9a65`), including the writable Copilot home tmpfs and
`verify_copilot_egress_contract.py -> OK`, but the token had not been rotated:

```text
OLD_PID=14687 NEW_PID=16571
worker_health=200
COPILOT_GITHUB_TOKEN=present_by_name
RICK_COPILOT_CLI_ENABLED=true
RICK_COPILOT_CLI_EXECUTE=false
GITHUB_USER_HTTP=401
error_message=Bad credentials
TOKEN_STATUS=invalid_or_expired
```

Token-source forensics for that stop:

| Check | Result |
| --- | --- |
| EnvironmentFile for token | `/home/rick/.config/openclaw/copilot-cli-secrets.env` |
| Secrets file mtime | `2026-04-26 23:20:07 -04` |
| disk_token vs process_token | identical content; no refresh pending on disk |

No L3/L4, nft table, Docker network, or `copilot_cli.run` was used in either
O0 stop. The only real execution in this lifecycle is
`mission_run_id=4c00f4de3f474abdbae75252725d58a8`.
