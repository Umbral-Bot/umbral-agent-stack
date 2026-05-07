# F8D — Default-model Copilot CLI egress proof (no `--model`)

- Task: [.agents/tasks/f8d-default-model-egress-proof-2026-05-07.md](../../.agents/tasks/f8d-default-model-egress-proof-2026-05-07.md)
- Approval: `APPROVE_F8D_DEFAULT_MODEL_EGRESS_PROOF=YES`
- Date (UTC): 2026-05-07
- Branch: `rick/f8d-default-model-egress-proof-2026-05-07`
- Verdict: **amarillo**

## Headline

With PR #327 (`--include-github-meta`) and PR #328 merged on `main`, the
scoped egress allow-list now contains `140.82.112.0/20` and the Copilot
CLI request reaches the GitHub backend successfully (kernel accepts to
`140.82.112.22`, `nft_drop_delta = 0/0`). The default-model probe (no
`--model`) failed with an explicit, non-secret backend error:

```
Error: Authentication failed (Request ID: C654:A4EF6:39971B4:3F5E407:69FC0881)
```

The presence of a backend Request ID confirms the request was accepted
by the network and answered by Copilot's API. The failure mode is
**token entitlement** (worker token is a generic GitHub token without the
`Copilot Requests` scope), **not** egress and **not** model availability.

## 0. Source verification

| Item | Value |
|---|---|
| `git rev-parse HEAD` | `a0c6b6b` (was `origin/main` at task start) |
| Branch used | `rick/f8d-default-model-egress-proof-2026-05-07` |
| PR #327 merged | `c55676a79cce18114d8ef9fd4aad4c9a4c869800` @ 2026-05-07T03:08:35Z |
| PR #328 merged | `a0c6b6bcc6ecf5340acbaf56ec256f52168ceba1` @ 2026-05-07T03:31:44Z |
| Sandbox image | `umbral-sandbox-copilot-cli:6940cf0f274d` |

## 1. Token + CLI capability

```
WORKER_TOKEN=present_by_name
COPILOT_GITHUB_TOKEN=present_by_name
GITHUB_USER_HTTP=200
TOKEN_STATUS=valid (for api.github.com/user)
```

Token never echoed. Read directly from `/proc/$WORKER_PID/environ`,
exported only as `COPILOT_GITHUB_TOKEN` for the docker run, and shredded
post-run.

## 2. Resolver with GitHub Meta CIDRs

`python3 scripts/copilot_egress_resolver.py --include-github-meta --non-strict --format json`

```
copilot_v4_count = 37
copilot_v6_count = 2
has_140_82_112_0_20 = True
github_meta.included = True
github_meta.keys = api, web, copilot_api
```

`140.82.112.0/20` confirmed in `ip_sets.copilot_v4`. Verifier
(`python3 scripts/verify_copilot_egress_contract.py`) returned `OK`.

## 3. nft + docker network setup

- `docker network create --driver bridge --opt com.docker.network.bridge.name=br-copilot --subnet 10.88.42.0/24 copilot-egress`
  - `NET_CREATED_BY_TASK=1` (network did not pre-exist).
- `sudo nft -f infra/networking/copilot-egress.nft.example`
  - Table `inet copilot_egress` loaded.
- Sets populated from `/tmp/f8d-egress.json`: 37 v4 elements, 2 v6.
- Drop counter (`forward` chain handle 11) baseline: `0 packets / 0 bytes`.

## 4. Direct probe (no `--model`)

Single `docker run` with full hardening:

```
--read-only --memory=1g --cpus=1.0 --pids-limit=256
--cap-drop=ALL --security-opt no-new-privileges
--user 10001:10001 --ipc=none --network=copilot-egress
--tmpfs /tmp,/scratch,/home/runner/.cache,/home/runner/.copilot
-e COPILOT_GITHUB_TOKEN
```

CLI invocation (no `--model`):

```
copilot --no-color --no-auto-update --no-remote --no-ask-user \
  --disable-builtin-mcps \
  --secret-env-vars=COPILOT_GITHUB_TOKEN \
  --available-tools=view,grep,glob \
  --log-level=debug \
  --prompt "Return exactly: F8D_OK"
```

Result:

| Field | Value |
|---|---|
| `rc` | `1` |
| `stdout_bytes` | `0` |
| `stderr_bytes` | `598` |

stderr (full, no secrets):

```
F8D_CONTAINER_READY_MS=1778124925722958964
Error: Authentication failed (Request ID: C654:A4EF6:39971B4:3F5E407:69FC0881)

Your GitHub token may be invalid, expired, or lacking the required permissions.

To resolve this, try the following:
  • Start 'copilot' and run the '/login' command to re-authenticate
  • If using a Fine-Grained PAT, ensure it has the 'Copilot Requests' permission enabled
  • If using COPILOT_GITHUB_TOKEN, GH_TOKEN or GITHUB_TOKEN environment variable, verify the token is valid and not expired
  • Run 'gh auth status' to check your current authentication status
```

The Request ID proves the request reached GitHub's Copilot API.

## 5. nft accept / drop summary

- Drop rule (handle 11) post-probe: `0 packets / 0 bytes` → `nft_drop_delta = 0/0`.
- Kernel accept logs (excerpt, `sudo journalctl -k`):

```
copilot-egress accept v4: ... DST=4.228.31.149   DPT=443 SYN
copilot-egress accept v4: ... DST=140.82.112.22  DPT=443 SYN
copilot-egress accept v4: ... DST=140.82.112.22  DPT=443 SYN
```

`140.82.112.22` is exactly inside the `140.82.112.0/20` Meta CIDR
that PR #327 added — confirming the F8B regression is fixed and that
the backend was reachable end-to-end.

## 6. Metrics JSON

```json
{
  "container_ready_ms": 308,
  "copilot_exit_ms": 4488,
  "docker_start_ms": 0,
  "first_stdout_byte_ms": null,
  "nft_drop_delta": {"bytes": 0, "packets": 0},
  "stderr_bytes": 598,
  "stdout_bytes": 0,
  "rc": 1
}
```

## 7. Secret scan

`grep -F "$COPILOT_GITHUB_TOKEN" /tmp/f8d/stdout /tmp/f8d/stderr` →
no match → `secret_scan=clean`. Token never appears in any captured
artifact, log, or this report.

## 8. Rollback

- `sudo nft delete table inet copilot_egress` → `no copilot tables`.
- `docker network rm copilot-egress` (created by this task) → success;
  `docker network ls | grep copilot-egress` → empty.
- `ip -br link show br-copilot` → `Device "br-copilot" does not exist.`
- `curl /health` → `HEALTH_HTTP=200`.
- Pre-existing host `policy drop` chains were not modified by this task
  (same baseline observed in F8B and F8C).

## 9. Root-cause separation

| Layer | F8B | F8C | F8D |
|---|---|---|---|
| Egress (nft drops) | 36 packets dropped (`140.82.113.21` not in set) | 0/0 | **0/0** |
| Backend reachability | n/a (blocked) | n/a (blocked at model gate) | **OK (Request ID returned)** |
| Model gate | n/a | `Model "Claude Opus 4.7" ... not available` | **bypassed (no `--model`)** |
| Token entitlement | not exercised | not exercised | **fails: missing `Copilot Requests`** |

F8D isolates the remaining blocker as **token entitlement on the worker's
GitHub token**. The token authenticates fine for the GitHub REST API but
the Copilot backend rejects it because it lacks the `Copilot Requests`
permission. This is independent of egress and independent of `--model`.

## 10. Verdict — amarillo

- `rc=1` with an **explicit, non-secret error** (`Authentication failed`)
  and a public GitHub Request ID.
- No leaks, no host-wide drop, rollback complete, `/health=200`.
- Egress fix from PR #327 conclusively validated by a non-`--model` probe.

## 11. Recommendations

1. Provision a Copilot-entitled token for the worker (Fine-Grained PAT
   with `Copilot Requests` enabled, or a Copilot OAuth token from
   `gh auth login --scopes copilot`). Store as `COPILOT_GITHUB_TOKEN` in
   the worker unit `Environment=` / drop-in.
2. Re-run F8D after token swap to capture the `verde` baseline (`rc=0`,
   stdout containing `F8D_OK`).
3. Only after `verde` is reached, schedule the canonical `copilot_cli.run`
   retry — with `--include-github-meta` retained in the runtime nft path.
4. No Plan B trigger.

## 12. Artifacts

- Resolver JSON: `/tmp/f8d-egress.json` (ephemeral, not committed).
- Probe stderr/stdout/metrics: `/tmp/f8d/{stdout,stderr,metrics.json}` (ephemeral).
- Kernel accept log lines: `sudo journalctl -k --since "2 minutes ago" | grep copilot-egress`.

cc @codex
