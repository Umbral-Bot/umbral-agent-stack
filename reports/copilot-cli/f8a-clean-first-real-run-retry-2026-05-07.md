# F8A Clean First Real Run Retry — Evidence Report

**Date:** 2026-05-07  
**Verdict:** amarillo — infra clean, two root causes identified, action needed

## Summary

This is the fifth F8A run attempt (mission_run_id=`8dad30fe39f94c3781ee481d4d7d4349`). The sandbox infrastructure is now fully working (scoped nft egress, bridge network, stdin fixed, prompt quoting fixed). However, copilot exits with `exit_code=1` and 0 bytes output due to **two compounding bugs** discovered in post-run investigation:

1. **Missing `--tmpfs /home/runner/.copilot`** — the container filesystem is `--read-only`, and copilot tries to initialize its home directory at `$HOME/.copilot`. Without a writable tmpfs there, copilot fails silently before printing anything. Fix: add `--tmpfs /home/runner/.copilot:size=32m,mode=1777` to docker argv.

2. **`COPILOT_GITHUB_TOKEN` is expired/invalid** — the `github_pat_` token in the worker env returns **HTTP 401** from `api.github.com`. This is the auth root cause. Fix: regenerate the token (human action required).

## Run Fields

| Field | Value |
|---|---|
| mission_run_id | `8dad30fe39f94c3781ee481d4d7d4349` |
| batch_id | `f8a-clean-real-run` |
| agent_id | `copilot-vps-single-005` |
| decision | `completed` |
| phase | `F8A` |
| exit_code | `1` |
| duration_sec | `4.024` |
| egress_activated | `true` |
| audit_log | `reports/copilot-cli/2026-05/8dad30fe39f94c3781ee481d4d7d4349.jsonl` |
| artifact_dir | `artifacts/copilot-cli/2026-05/f8a-clean-real-run/copilot-vps-single-005/8dad30fe39f94c3781ee481d4d7d4349/` |

## Artifact Summary

| Stream | Bytes | Notes |
|---|---:|---|
| stdout | 0 | silent exit — copilot home not writable |
| stderr | 0 | silent exit — copilot home not writable |

## Infrastructure Status (This Run)

- ✅ Scoped nft table `inet copilot_egress` applied (no host-wide drop)
- ✅ Docker bridge network `copilot-egress` with `br-copilot`, ICC disabled
- ✅ `-i` flag in docker run (stdin reaches container)
- ✅ `prompt=$(cat "$prompt_file")` quoting correct
- ✅ `--network=copilot-egress` in docker argv
- ✅ `COPILOT_GITHUB_TOKEN` passed via `--env COPILOT_GITHUB_TOKEN` (confirmed in container)
- ✅ nft drop counter = 0 (no traffic blocked during run)
- ✅ Diagnostic mode enabled during run
- ❌ `--tmpfs /home/runner/.copilot` missing → silent exit before auth
- ❌ `COPILOT_GITHUB_TOKEN` is expired → 401 from GitHub API

## Root Cause Analysis

### Bug 1: Missing writable `~/.copilot`

The copilot CLI initializes its home directory (`$HOME/.copilot` = `/home/runner/.copilot`) on startup. The container is launched with `--read-only`, and only `/tmp`, `/scratch`, and `/home/runner/.cache` have `--tmpfs` mounts. `/home/runner/.copilot` is not writable.

**Evidence:**
```
# Without --tmpfs /home/runner/.copilot:
returncode=1, stdout=0b, stderr=0b  ← SILENT

# With --tmpfs /home/runner/.copilot:
returncode=1, stdout=404b
Error: No authentication information found.
```

When the copilot home can't be initialized, copilot exits silently with code 1 and zero bytes output. This was the cause of the "silent exit" pattern seen in runs 2, 3, 4, and 5.

**Fix (code):** Add to docker argv in `worker/tasks/copilot_cli.py`:
```python
"--tmpfs", "/home/runner/.copilot:size=32m,mode=1777",
```

### Bug 2: `COPILOT_GITHUB_TOKEN` expired

After fixing Bug 1, copilot becomes verbose and reports "No authentication information found." Direct GitHub API test with the current token returns HTTP 401:

```
GitHub API /user: HTTP 401 (Unauthorized)
Copilot API token endpoint: HTTP 401
```

The token format is `github_pat_` (fine-grained PAT, length 104). It was either revoked, expired, or never had the required Copilot scopes.

**Fix (human action required):** Generate a new fine-grained PAT with:
- Account: the GitHub account with active Copilot subscription
- Scope: read access to repository (or `copilot` scope if available)
- Update `/home/rick/.config/openclaw/env` → `COPILOT_GITHUB_TOKEN=<new_token>`
- Restart worker: `systemctl --user restart umbral-worker.service`

## Security Analysis

| Check | Result |
|---|---|
| Audit token scan | ✅ clean — no raw tokens in JSONL |
| Artifact token scan | ✅ clean — no raw tokens in artifact dir |
| nft drop counter | ✅ 0 packets (no traffic during run) |
| Container writable paths | ✅ only /tmp, /scratch, /home/runner/.cache |
| rollback complete | ✅ EXECUTE=false, egress.activated=false, diagnostic absent, nft removed, docker net removed |
| worker /health | ✅ HTTP 200 |

## Recovery State (Post-Rollback)

```text
RICK_COPILOT_CLI_ENABLED=true
RICK_COPILOT_CLI_EXECUTE=false
egress.activated=false
COPILOT_CLI_DIAGNOSTIC_MODE absent
no copilot nft table
no copilot docker network
/health HTTP 200
worker PID: 14687
```

## Next Steps

### Immediate (required before F8A-run-6):

1. **Token refresh (human):** Generate new `COPILOT_GITHUB_TOKEN` with valid Copilot access, update `/home/rick/.config/openclaw/env`
2. **Code fix (PR):** Add `--tmpfs /home/runner/.copilot:size=32m,mode=1777` to `worker/tasks/copilot_cli.py` docker argv

### Code diff needed:

```python
# In worker/tasks/copilot_cli.py, in the docker run args list, after:
"--tmpfs", "/home/runner/.cache:size=32m,mode=1777",
# Add:
"--tmpfs", "/home/runner/.copilot:size=32m,mode=1777",
```

### After both fixes:

Run F8A-run-6 with same task template. Expected result: copilot authenticates, attempts to call GitHub Copilot API, produces output.

## F8A Run History

| Run | mission_run_id | exit_code | root_cause | fixed_in |
|---|---|---|---|---|
| 1 | 49a14965 | 1 | `--no-banner` invalid flag | PR #299 |
| 2 | ee5aa7b9 | 1 | docker missing `-i` (prompt not piped) | PR #302 |
| 3 (diagnostic) | 5d270087 | 1 | confirmed stdin fix; found prompt quoting issue | PR #304 |
| 4 (quoting) | 6e3989dd | interrupted | window interrupted; quoting fixed | PR #305 |
| 5 (this) | 8dad30fe | 1 | missing `--tmpfs ~/.copilot` + expired token | this PR |

