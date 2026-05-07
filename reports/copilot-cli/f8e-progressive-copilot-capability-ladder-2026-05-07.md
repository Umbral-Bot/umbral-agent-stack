# F8E — Progressive Copilot capability ladder

- Task: [.agents/tasks/f8e-progressive-copilot-capability-ladder-2026-05-07.md](../../.agents/tasks/f8e-progressive-copilot-capability-ladder-2026-05-07.md)
- Approval: `APPROVE_F8E_PROGRESSIVE_COPILOT_CAPABILITY_LADDER=YES`
- Date (UTC): 2026-05-07
- Branch: `rick/f8e-progressive-copilot-capability-ladder-2026-05-07`
- Verdict: **amarillo**

## Headline

T0 (source gates) and infra setup PASS. **T1 fails with the same
explicit `Authentication failed` error observed in F8D**: the worker's
`COPILOT_GITHUB_TOKEN` authenticates against `api.github.com/user`
(HTTP 200) but Copilot's backend rejects it for missing the
`Copilot Requests` permission. The post-rotation token did not change
this outcome — Copilot still does not honour it.

Per task rule (`Si T1 falla con "Authentication failed" o "Copilot
Requests": STOP amarillo`), T2–T7 were **not executed**. Egress remains
proven (`nft_drop_delta = 0/0`), no leaks, rollback complete.

## Test ladder result table

| Test | Status | Verdict | Notes |
|---|---|---|---|
| T0 sync + source gates | run | pass | PRs #327/#328/#330 merged on `main`; resolver `--include-github-meta` present; `140.82.112.0/20` in v4; contract verifier OK |
| T1 token entitlement | run | **fail (amarillo)** | `rc=1`, `Authentication failed (Request ID: DEE2:E621D:...)`; `nft_drop_delta=0/0`; no leak |
| T2 default model no tools | **skipped** | — | Gated by T1 |
| T3 model override discovery | **skipped** | — | Gated by T1 |
| T4 canonical `copilot_cli.run` | **skipped** | — | Gated by T1 |
| T5 repo comprehension | **skipped** | — | Gated by T4 |
| T6 risk review | **skipped** | — | Gated by T5 |
| T7 patch proposal text-only | **skipped** | — | Gated by T6 |

## 0. Source verification (T0)

| Item | Value |
|---|---|
| `git rev-parse origin/main` | `28a54e0` |
| PR #327 merged | `c55676a` @ 2026-05-07T03:08:35Z |
| PR #328 merged | `a0c6b6b` @ 2026-05-07T03:31:44Z |
| PR #330 merged | `28a54e0` @ 2026-05-07T03:53:53Z |
| Resolver flag `--include-github-meta` | present (1 occurrence in `scripts/copilot_egress_resolver.py`) |
| Resolver `copilot_v4_count` | 37 |
| Resolver `copilot_v6_count` | 2 |
| `140.82.112.0/20` in `copilot_v4` | True |
| `github_meta.included` | True |
| `github_meta.keys` | `api`, `web`, `copilot_api` |
| `verify_copilot_egress_contract.py` | OK |
| Sandbox image | `umbral-sandbox-copilot-cli:6940cf0f274d` |

## 1. Worker + token state (T1 prep)

```
HEALTH=200
WORKER_TOKEN=present_by_name
COPILOT_GITHUB_TOKEN=present_by_name
GITHUB_USER_HTTP=200          # token IS valid for GitHub REST
TOK_FP=066741648703           # SHA256[0:12] of token (NOT the token)
```

The token was read from `/proc/$WORKER_PID/environ`, exported only as
`COPILOT_GITHUB_TOKEN` for the docker run, and shredded after rollback.
A short SHA256 fingerprint (`TOK_FP`) is recorded so future runs can
confirm whether the token actually rotated, **without ever revealing
its value**.

## 2. nft + docker network setup

- `docker network create copilot-egress` (created by this task; `NET_CREATED_BY_TASK=1`).
- `sudo nft -f infra/networking/copilot-egress.nft.example` → `inet copilot_egress` loaded.
- Sets populated from `/tmp/f8e-egress.json`: 37 v4, 2 v6.
- Drop counter baseline: `0 packets / 0 bytes`.

## 3. T1 — Default-model minimal probe

Single direct sandbox probe, **no `--model`**, prompt: `Return exactly: F8E_T1_OK`.

Hardening identical to F8C/F8D:
`--read-only --memory=1g --cpus=1.0 --pids-limit=256 --cap-drop=ALL
--security-opt no-new-privileges --user 10001:10001 --ipc=none
--network=copilot-egress` + tmpfs for `/tmp`, `/scratch`,
`/home/runner/.cache`, `/home/runner/.copilot`.

CLI flags:
`--no-color --no-auto-update --no-remote --no-ask-user
--disable-builtin-mcps --secret-env-vars=COPILOT_GITHUB_TOKEN
--available-tools=view,grep,glob --log-level=debug
--prompt "Return exactly: F8E_T1_OK"`.

### Result

```json
{
  "label": "T1",
  "model": "default",
  "rc": 1,
  "stdout_bytes": 0,
  "stderr_bytes": 584,
  "container_ready_ms": 324,
  "copilot_exit_ms": 5085,
  "nft_drop_delta": {"packets": 0, "bytes": 0},
  "token_leak": false
}
```

stderr (full, no secrets):

```
READY_NS=1778126235151342709
Error: Authentication failed (Request ID: DEE2:E621D:3AE4A6E:40D5A9E:69FC0D9F)

Your GitHub token may be invalid, expired, or lacking the required permissions.

To resolve this, try the following:
  • Start 'copilot' and run the '/login' command to re-authenticate
  • If using a Fine-Grained PAT, ensure it has the 'Copilot Requests' permission enabled
  • If using COPILOT_GITHUB_TOKEN, GH_TOKEN or GITHUB_TOKEN environment variable, verify the token is valid and not expired
  • Run 'gh auth status' to check your current authentication status
```

The Request ID confirms the request **reached** Copilot's API (egress
fix from PR #327 still proven). The failure is at the entitlement layer.

## 4. Score system

| Score | Value | Rationale |
|---|---|---|
| `network_score` | **1** | T1 `nft_drop_delta=0/0`; no other probes ran |
| `auth_score` | **0** | T1 backend auth failed |
| `canonical_score` | **0** | T4 not executed (gated) |
| `quality_score` | **n/a** | T5/T6/T7 not executed |
| `safety_score` | **1** | No leaks, no writes, rollback clean, no host-wide drop added by task |
| `model_power_score` | **0** | No Copilot model proved working with current token |

## 5. Rollback proof

```
sudo nft delete table inet copilot_egress   → ok
sudo nft list tables | grep copilot         → no copilot tables
NET_CREATED_BY_TASK=1
docker network rm copilot-egress            → ok
docker network ls | grep ^copilot-egress$   → empty
ip -br link show br-copilot                 → Device "br-copilot" does not exist.
RICK_COPILOT_CLI_EXECUTE                    → unset_or_no_access (L3/L4 never opened)
curl /health                                → HEALTH=200
tokens                                      → shredded
```

Pre-existing host firewall `policy drop` chains (input/forward) were not
modified by this task — same baseline observed in F8B/F8C/F8D.

## 6. Verdict — amarillo

- T1 `rc=1` with **explicit, non-secret** GitHub-issued error including
  a public Request ID.
- Egress proven again: `nft_drop_delta=0/0` and the request reached the
  backend.
- No leaks. Rollback complete. `/health=200`.
- T2–T7 correctly **skipped** because the rule requires STOP at T1 when
  the failure mode is "Authentication failed" / "Copilot Requests" —
  none of T2–T7 isolates that error; they all assume Copilot auth works.

## 7. Recommendation (NOT executed)

The token rotation announced by David did not unblock Copilot CLI. The
new token still lacks the `Copilot Requests` permission required by
the Copilot backend (it is, however, valid for `api.github.com/user`).

Action items, all out of scope for this task:

1. Issue a Copilot-entitled token. Two viable shapes:
   - Fine-Grained PAT for the worker's account with `Copilot Requests`
     enabled, OR
   - OAuth token from `gh auth login --scopes copilot` (interactive
     `gh auth refresh -h github.com -s copilot` works on a console with
     browser).
2. Confirm the account itself has Copilot enabled (Individual / Business
   / Enterprise — `gh api /copilot_internal/user` or
   `gh api /user/copilot_billing`).
3. Place the new token only in the worker's systemd-user `Environment=`
   (or drop-in) — never echo it; preserve the `TOK_FP` discipline so
   we can detect future rotations without leaking values.
4. Re-run F8E from T1; once T1 is green, T2–T7 can proceed
   automatically without further user approval beyond the original
   `APPROVE_F8E_*` string.
5. No Plan B trigger; no canonical `copilot_cli.run` until T1 is green.

## 8. Artifacts

- Resolver JSON: `/tmp/f8e-egress.json` (ephemeral).
- T1 stdout/stderr/metrics: `/tmp/f8e/T1/{stdout,stderr,metrics.json}` (ephemeral).
- Probe helper: `/tmp/f8e-probe.sh` (ephemeral; not committed).

cc @codex
