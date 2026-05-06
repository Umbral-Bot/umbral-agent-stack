# F8A — Real Execution Path Behind L1-L5

**Date:** 2026-05-05
**Status:** PR-only implementation. No runtime activation by Codex.
**Owner:** Codex implements; Copilot-VPS verifies runtime after merge.

---

## Objective

F8A changes `copilot_cli.run` from "it can only say what it would run" to "it
can run the sandboxed Docker command when every gate is open".

This is not full F8 productive mode yet. It is the missing runtime plumbing
needed before the first controlled scratch run.

---

## Gate Contract

Real subprocess execution is reachable only when all conditions are true:

| Layer | Requirement |
|---|---|
| L1 | `RICK_COPILOT_CLI_ENABLED=true` |
| L2 | `config/tool_policy.yaml :: copilot_cli.enabled=true` |
| L3 | `RICK_COPILOT_CLI_EXECUTE=true` |
| L4 | `config/tool_policy.yaml :: copilot_cli.egress.activated=true` |
| L5 | `_REAL_EXECUTION_IMPLEMENTED=True` |
| Request | `dry_run=false` |

If L3 is false, the handler keeps returning `execute_flag_off_dry_run`.
If L4 is false and `dry_run=false`, the handler returns
`egress_not_activated` and does not call subprocess.
If `dry_run=true`, no subprocess is called even with L3/L5 open.

---

## Runtime Behavior

When every gate is open, the handler:

1. Builds a hardened `docker run` argv.
2. Passes `COPILOT_GITHUB_TOKEN` by environment variable name only, never by
   value in argv or logs.
3. Sends the prompt through subprocess stdin, not argv.
4. Captures stdout/stderr.
5. Writes redacted artifacts under `artifacts/copilot-cli/`.
6. Writes `manifest.json` with `batch_id`, `agent_id`, `mission_run_id`,
   exit code, duration, hashes, token/cost source fields, and secret-scan
   status.
7. Appends audit JSONL events for `execute_started` and final decision.

The handler does not infer billing. Current token/cost fields are explicit:
`not_reported_by_github_copilot_cli`. F8 cannot close until David accepts a
defensible token/cost source.

---

## Artifact Layout

Default root:

```text
artifacts/copilot-cli/<YYYY-MM>/<batch_id>/<agent_id>/<mission_run_id>/
  stdout.txt
  stderr.txt
  manifest.json
```

Override:

```bash
COPILOT_CLI_ARTIFACT_DIR=/path/to/artifacts
```

Docker image/network overrides:

```bash
COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:<tag>
COPILOT_CLI_DOCKER_NETWORK=copilot-egress
```

---

## Tests Added

`tests/test_copilot_cli.py` now covers:

- L3 closed still blocks with no subprocess.
- L3/L5 open + `dry_run=true` still calls no subprocess.
- L3/L5 open + L4 closed + `dry_run=false` returns `egress_not_activated`.
- All gates open + `dry_run=false` calls mocked `subprocess.run` once.
- Prompt is passed via stdin, not argv.
- Token value is not present in argv.
- stdout/stderr artifacts and `manifest.json` are written.
- Token-shaped output is redacted before artifact write and marks the run
  non-green.

Local result:

```text
76 passed, 1 skipped
```

---

## Runtime Verification After Merge

Copilot-VPS must deploy this PR with L3 still false first. Expected result:

```json
{
  "decision": "execute_flag_off_dry_run",
  "policy": {
    "execute_enabled": false,
    "real_execution_implemented": true
  },
  "would_run": false
}
```

Only after that can David approve a bounded L4+L3 run window.

---

## Stop Conditions

Stop and rollback if any of these happen:

- token value appears in report, artifact, audit log, or PR;
- worker `/health` fails after deploy;
- L3 opens without a named run window;
- L4 egress is broad, unpopulated, or not verifiable;
- subprocess launches while `dry_run=true`;
- subprocess launches with L3 false or L4 false;
- artifacts are missing manifest, hashes, or secret-scan status.

