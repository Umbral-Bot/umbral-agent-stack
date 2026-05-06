# F8A Retry After Docker `-i` Stdin Fix — 2026-05-06

**Verdict:** 🟡 amarillo (PR #302 docker `-i` fix CONFIRMED at argv level and prompt
reaches the container, but a second wrapper-quoting defect was exposed; copilot still
invoked with empty prompt and exits 1).

## References

- Diagnostic run that found the original cause: `5d270087a2944283957bc3d21e4059e7`
  (report `reports/copilot-cli/f8a-diagnose-silent-exit-2026-05-06.md`).
- PR #302 (merged): `fix(copilot-cli): keep docker stdin open for prompt`.
- HEAD on main during this run: `7b3b97f`.

## Run

| field | value |
|---|---|
| `mission_run_id` | `863af7a4e81c452faec1c06f94cf2132` |
| `batch_id` | `f8a-retry-stdin-fix` |
| `agent_id` | `copilot-vps-single-003` |
| `decision` | `completed` |
| `phase` | `F8A.real_execution` |
| `exit_code` | **1** |
| `duration_sec` | **3.873** (+1.5 s vs `5d270087…` 2.386 s) |
| `egress_activated` | true |
| `stdout.bytes` | **0** |
| `stderr.bytes` | **0** |
| `audit_log` | `reports/copilot-cli/2026-05/863af7a4e81c452faec1c06f94cf2132.jsonl` |
| `manifest` | `artifacts/copilot-cli/2026-05/f8a-retry-stdin-fix/copilot-vps-single-003/863af7a4e81c452faec1c06f94cf2132/manifest.json` |
| `secret_scan` | clean (`patterns_redacted: false`) |
| `cost_usd.source` | `not_reported_by_github_copilot_cli` |

## What this run confirmed about PR #302

`docker_argv_redacted` from the audit log:

```
docker run --rm -i --network=bridge --read-only ...
```

- `"-i"` is present at index 4 ✅ (the L5+L4+L3 open path now uses it).
- `COPILOT_CLI_DIAGNOSTIC_MODE=true` was loaded by the worker (verified in `/proc/$PID/environ`).
- The wrapper `prompt_file` was successfully populated by `cat > "$prompt_file"`. An
  out-of-band probe replicating the same docker invocation with `-i` and a 33-byte
  prompt on stdin showed `PROMPT_BYTES=33` inside the container, proving stdin is
  forwarded.

So PR #302 closed the original empty-stdin defect.

## New defect exposed (NOT fixed in this PR)

Even with the prompt file populated, copilot is invoked with **`--prompt ""`** and exits
silently. The reason is in `worker/tasks/copilot_cli.py:513`:

```python
"--prompt \"$(cat \"$prompt_file\")\""
```

Once joined into the wrapper script string and run via `sh -lc "<long script>"`, the
nested-quote sequence `\"$(cat \"$prompt_file\")\"` does not expand to the file
contents in this shell context. An out-of-band probe in the same sandbox image shows the
exact failure:

```
$ sh -c "echo \"PROMPT=[\$(cat \\\"/tmp/copilot-prompt.txt\\\")]\""
cat: '"/tmp/copilot-prompt.txt"': No such file or directory
PROMPT=[]
```

The literal `\"` is preserved through the outer `sh -c` parse and `cat` receives
`"/tmp/copilot-prompt.txt"` (with quotes) as the filename. Same prompt file, simpler
syntax (`PROMPT=[$(cat "$prompt_file")]`), works fine — so the defect is the over-escaped
quoting in the worker-built script.

That collapses the actual copilot invocation back to `copilot ... --prompt ""`, which
matches the previous silent-exit symptom. The reason the visible "No prompt provided"
message still does not surface as stderr in the artifact is the same as last run:
`--log-dir=/scratch/copilot-logs` is a tmpfs that is destroyed when the container exits.

The +1.5 s duration vs the previous run is consistent with the prompt actually being
piped through (docker `-i` plumbing adds latency) before the wrapper quoting fails.

## Proposed fix (NOT applied here)

In `worker/tasks/copilot_cli.py` at line 513, swap to a heredoc-free form that does not
rely on nested `\"...\"` inside `$(...)`. Either:

```python
# Option A — read file into a variable first:
"prompt=$(cat /tmp/copilot-prompt.txt)\n"
"exec copilot ... --prompt \"$prompt\""
```

or

```python
# Option B — use stdin to copilot directly:
"exec copilot ... < /tmp/copilot-prompt.txt"
```

Optional follow-ups (subsumed by previous report and still relevant):
- Drop `--log-dir=/scratch/copilot-logs` in diagnostic mode (or bind-mount the log dir)
  so debug stderr survives container exit.
- Pass `--allow-all-tools` (per `copilot --help`: "required for non-interactive mode").
- Investigate VPS DNS — `scripts/copilot_egress_resolver.py --non-strict` returned **0**
  v4 and 0 v6 entries because every Copilot endpoint failed with
  `gaierror: [Errno -3] Temporary failure in name resolution`. This means even after the
  prompt bug is fixed, network egress to `api.githubcopilot.com` would still be blocked
  by the empty `copilot_v4` set in the nft table.

## Gates / state during the window

```
process RICK_COPILOT_CLI_EXECUTE=true
process COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:6940cf0f274d
process COPILOT_CLI_DOCKER_NETWORK=bridge
process COPILOT_CLI_DIAGNOSTIC_MODE=true
process COPILOT_GITHUB_TOKEN=present_by_name
worker /health: 200, PID 14960
```

## nft state

| moment | table `inet copilot_egress` |
|---|---|
| before | absent |
| during | present, `copilot_v4` and `copilot_v6` flushed (resolver returned empty sets — DNS broken on VPS) |
| after rollback | absent (`sudo nft list table inet copilot_egress` → "no copilot nft table") |

Backup of pre-window nft ruleset: `/home/rick/.copilot/backups/f8a-stdin-fix-20260506T121720Z/nft-ruleset-before.nft`.

## Rollback evidence (post-run)

```
RICK_COPILOT_CLI_ENABLED=true
RICK_COPILOT_CLI_EXECUTE=false
  egress:
    profile_name: copilot-egress
    activated: false
no copilot nft table
diagnostic mode removed clean
HTTP 200
```

`grep -q '^COPILOT_CLI_DIAGNOSTIC_MODE=' /home/rick/.config/openclaw/copilot-cli.env`
returned non-zero → diagnostic mode line removed cleanly.

## Limits respected

- Exactly one `copilot_cli.run` (`863af7a4…`).
- O1 dry-run probe with L3 closed PASSED before opening anything.
- L3, L4, diagnostic mode flipped only inside the run window; backup restored at exit.
- nft table created only inside the window; deleted at rollback.
- No publish, no Notion, no gates, no merge.
- Token never printed (`present_by_name` only).
- Secret scan on artifacts: clean.

## Token / cost

Source: `not_reported_by_github_copilot_cli` (Copilot CLI does not expose token usage or
cost on stdout in this configuration).

## Out-of-band evidence captured

- `journal-window.txt`: 0 lines matched copilot/docker/exit/error pattern (no
  worker-side errors logged for this run).
- `nft-table-during.txt`: snapshot of nft table state during the window (sets empty due
  to DNS).
- `nft-ruleset-before.nft`: pre-window ruleset for restoration verification.
