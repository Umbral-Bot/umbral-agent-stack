# F8A Diagnose Silent Exit — 2026-05-06

**Verdict:** 🟡 amarillo (gates + sandbox + rollback worked; root cause located).

## Context

Prior runs of `copilot_cli.run` exited `exit_code=1` with empty stdout/stderr:

| mission_run_id | symptom |
|---|---|
| `49a1496515c84826b215ae9d8ec400e9` | exit 1, stderr 105B (`--no-banner` flag error — fixed in PR #298) |
| `ee5aa7b921d44fdcb435d1c0803656d2` | exit 1, **0B stdout, 0B stderr**, 2.399s |

PR #300 (merged to main `0a5aa82`) added `COPILOT_CLI_DIAGNOSTIC_MODE=true`, which removes
`--output-format=json --stream=off` and adds `--log-level=debug` so verbose Copilot output
should reach the terminal.

## What this run did

- Sync to main `0a5aa82`, restart worker (PID 4633→5330).
- O1 verification with L3 closed: `decision=execute_flag_off_dry_run` ✅.
- Backed up envfile + `tool_policy.yaml` + nft ruleset to `/home/rick/.copilot/backups/f8a-diagnose-…`.
- Applied `infra/networking/copilot-egress.nft.example` and populated v4/v6 sets via
  `scripts/copilot_egress_resolver.py --non-strict`.
- Flipped L4 in working tree (`activated: true`), set `RICK_COPILOT_CLI_EXECUTE=true`,
  `COPILOT_CLI_DIAGNOSTIC_MODE=true`, sandbox image `umbral-sandbox-copilot-cli:6940cf0f274d`,
  network `bridge`. Restarted worker → PID 5433.
- One `copilot_cli.run` (mission `research`, prompt: list 3 top-level files).
- Explicit rollback (envfile restored from backup → diagnostic line gone, L3=false; YAML
  restored → L4=false; nft table deleted; worker restarted; `/health` 200).

## Result

| field | value |
|---|---|
| `mission_run_id` | `5d270087a2944283957bc3d21e4059e7` |
| `batch_id` | `f8a-diagnose-silent-exit` |
| `agent_id` | `copilot-vps-diagnostic-001` |
| `decision` | `completed` |
| `phase` | `F8A.real_execution` |
| `exit_code` | **1** |
| `duration_sec` | **2.386** |
| `egress_activated` | true |
| `stdout.bytes` | **0** |
| `stderr.bytes` | **0** |
| `audit_log` | `reports/copilot-cli/2026-05/5d270087a2944283957bc3d21e4059e7.jsonl` |
| `manifest` | `artifacts/copilot-cli/.../5d270087.../manifest.json` |
| `secret_scan` | clean |

### Diagnostic flags ARE active in the docker_argv (verified)

```
exec copilot --no-color --no-auto-update --no-remote --no-ask-user
     --disable-builtin-mcps --secret-env-vars=COPILOT_GITHUB_TOKEN
     --available-tools=view,grep,glob --log-dir=/scratch/copilot-logs
     --log-level=debug --prompt "$(cat "$prompt_file")"
```

- `--output-format=json` → **absent** ✅
- `--stream=off` → **absent** ✅
- `--log-level=debug` → **present** ✅

Yet stdout AND stderr are still 0 bytes. Diagnostic mode worked at the source level but
did not change the symptom.

## Root cause located — structural, not auth

Direct probes inside the same sandbox image (no network, replicating the wrapper script
exactly) reproduced the empty-prompt path:

```sh
docker run --rm --network=none umbral-sandbox-copilot-cli:6940cf0f274d /bin/sh -lc '
  set -eu
  prompt_file=/tmp/copilot-prompt.txt
  cat > "$prompt_file"            # ← reads stdin into file
  echo "PROMPT_FILE_BYTES=$(wc -c < $prompt_file)"
  exec copilot ... --log-level=debug --prompt "$(cat "$prompt_file")"
' < /dev/null
```

Output:
```
PROMPT_FILE_BYTES=0
No prompt provided. Run in an interactive terminal or provide a prompt with -p or via standard in.
```

### Cause chain

1. `worker/tasks/copilot_cli.py:524` calls `subprocess.run(argv, input=prompt, …)`. Python
   pipes `prompt` to the docker child's stdin.
2. **The constructed `docker run` argv has no `-i` flag.** Without `-i`, docker does NOT
   forward stdin from the python parent into the container.
3. Inside the container, `cat > "$prompt_file"` reads from a closed stdin → file ends up
   **0 bytes**.
4. `--prompt "$(cat "$prompt_file")"` → `--prompt ""`.
5. With auth present and empty prompt, Copilot's non-interactive guard is ambiguous: it
   exits `1` after ~2s. In our run the visible message ("No prompt provided…") never
   surfaced, almost certainly because `--log-dir=/scratch/copilot-logs` redirects the
   message into a tmpfs path that is destroyed when the container exits (no bind mount
   captures `/scratch/copilot-logs/*`). Probes without `--log-dir` show the message on
   stderr.

This explains all three symptoms simultaneously:
- silent stdout/stderr,
- exit 1,
- ~2.4 s duration (no real Copilot work, just startup + UI guard).

The previous "auth / endpoint / `--log-dir` write" hypotheses from the F8A retry report
are subsumed by this single defect: **the prompt never reaches Copilot.**

## Fix proposed for next iteration (NOT applied here)

In `worker/tasks/copilot_cli.py`, add `-i` to `docker_argv` so the python pipe is
forwarded into the container:

```python
docker_argv = [
    "docker", "run", "--rm",
    "-i",                    # ← add this; wrapper's `cat >` needs it
    f"--network={network}",
    ...
]
```

Optional follow-ups (not required for the silent-exit fix):
- Bind-mount the artifact dir over `/scratch/copilot-logs` so `--log-dir` output survives
  container exit. Then diagnostic mode actually gives us logs.
- Drop `--log-dir` entirely in diagnostic mode so debug output goes to stderr.
- Pass `--allow-all-tools` (per `copilot --help`: "required for non-interactive mode").

## Rollback evidence (post-run)

```
RICK_COPILOT_CLI_ENABLED=true
RICK_COPILOT_CLI_EXECUTE=false
  egress:
    profile_name: copilot-egress
    activated: false
no copilot nft table
HTTP 200
diagnostic mode removed: clean
```

`grep -q '^COPILOT_CLI_DIAGNOSTIC_MODE=' /home/rick/.config/openclaw/copilot-cli.env`
returned non-zero → **DIAGNOSTIC_MODE_STILL_SET_BAD** check passed (line removed).

## Limits respected

- One `copilot_cli.run` only (`5d270087…`).
- L3/L4/diagnostic-mode opened only inside the run window; backup restored at exit.
- nft table created only inside the window; deleted at rollback.
- No publish, no Notion, no gates, no merge.
- Token never printed (`present_by_name` only).
- Secret scan on artifacts: clean.
