# F8A Run-6 After Token Refresh — O0 Stop Evidence

**Date:** 2026-05-07  
**Verdict:** amarillo — stopped at O0; token still invalid  
**mission_run_id:** none; no `copilot_cli.run` executed

## Summary

Copilot-VPS attempted the O0 precheck for
`.agents/tasks/f8a-run6-after-token-refresh-2026-05-07.md`.
The task correctly stopped before opening L3/L4 because the
`COPILOT_GITHUB_TOKEN` loaded in the worker process still returned HTTP
401 from GitHub API `/user`.

No runtime gate was opened, no nft table was applied, no Docker network was
created, and no Copilot CLI run was issued.

## O0 Evidence

| Field | Value |
|---|---|
| worker PID | `14687` |
| `COPILOT_GITHUB_TOKEN` | `present_by_name` |
| token family | fine-grained PAT (`github_pat_`) |
| `GITHUB_USER_HTTP` | `401` |
| `TOKEN_STATUS` | `invalid` |
| error message | `Bad credentials` |

The raw token value was not printed.

## Safety State

Verified after the failed O0 precheck:

```text
RICK_COPILOT_CLI_ENABLED=true
RICK_COPILOT_CLI_EXECUTE=false
COPILOT_CLI_DIAGNOSTIC_MODE absent
egress.activated=false
no nft table inet copilot_egress
no docker network copilot-egress
worker /health HTTP 200
```

## Main History Drift

During the VPS attempt, `origin/main` did not contain the previously merged
F8A PRs #311, #312, and #314. GitHub still reported those PRs as merged, but
`origin/main` had been updated to a history that omitted them. That is why the
VPS observed:

- `.agents/tasks/f8a-run6-after-token-refresh-2026-05-07.md` missing.
- `worker/tasks/copilot_cli.py` missing the writable
  `/home/runner/.copilot` tmpfs fix.

This recovery PR re-lands the missing F8A changes on top of the current
`origin/main`.

## Required Before Next O0 Attempt

1. David must generate a new `COPILOT_GITHUB_TOKEN` with active Copilot access.
2. Update the live VPS secret source consumed by `umbral-worker.service`.
3. Restart the worker so the refreshed token is in `/proc/$PID/environ`.
4. Re-run the existing task
   `.agents/tasks/f8a-run6-after-token-refresh-2026-05-07.md`.

The task remains pending because no real run was executed. A valid O0 signal is:

```text
COPILOT_GITHUB_TOKEN=present_by_name
GITHUB_USER_HTTP=200
TOKEN_STATUS=valid
```

Only after that may Copilot-VPS open L3/L4 and execute exactly one
`copilot_cli.run`.

## Security

| Check | Result |
|---|---|
| Raw token printed | No |
| L3 opened | No |
| L4 opened | No |
| nft applied | No |
| Docker network created | No |
| `copilot_cli.run` executed | No |
| Worker health | HTTP 200 |
