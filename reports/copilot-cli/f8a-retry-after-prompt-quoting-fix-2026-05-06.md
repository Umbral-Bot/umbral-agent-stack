# F8A Retry After Prompt Quoting Fix — Interrupted Window Evidence

**Date:** 2026-05-06
**Verdict:** 🟡 amarillo
**Task spec:** `.agents/tasks/f8a-retry-after-prompt-quoting-fix-2026-05-06.md`
**Branch:** `rick/f8a-retry-after-prompt-quoting-fix-2026-05-06`
**Live HEAD at start:** `800a7af` (prompt quoting fix merged)
**mission_run_id (real run):** n/a — window interrupted before run executed
**Prior runs referenced:** `5d270087a2944283957bc3d21e4059e7` (diagnostic),
`863af7a4e81c452faec1c06f94cf2132` (stdin fix retry — exposed prompt quoting bug
and DNS issue)

## Summary

This retry was intended to validate the prompt-quoting fix
(`prompt=$(cat "$prompt_file")` + `--prompt "$prompt"` separation, merged via PR
prior to this session). Preflight (O1 + O2) passed, the run window was opened
(L3=true, L4=true, nft applied, worker restarted with diagnostic mode), but the
controlling bash session was killed before the `copilot_cli.run` curl was
issued. **No real Copilot execution occurred during the open window.**

The window did, however, surface a **critical architectural finding**: the
egress nft profile applies a host-wide `output` chain with `policy drop`, which
blocked every non-Copilot outbound TCP/443 connection on the worker host. During
the ≈ 8-minute window, 39 DNS-failure log entries and 13 worker `[ERROR]` events
were recorded — all from Notion tasks (`notion.read_database`,
`notion.poll_comments`) failing to reach `api.notion.com`.

Recovery executed cleanly: gates restored, nft table removed, worker restarted,
`/health` 200, no Copilot artifacts left behind.

## Preflight (O1 + O2) — Passed

### Source confirmation (HEAD `800a7af`)

| Check | Line | Result |
|---|---|---|
| `_REAL_EXECUTION_IMPLEMENTED = True` | `worker/tasks/copilot_cli.py:54` | ✅ |
| docker argv contains `"-i"` | `worker/tasks/copilot_cli.py:472` | ✅ |
| wrapper `prompt=$(cat "$prompt_file")` | `worker/tasks/copilot_cli.py:512` | ✅ |
| wrapper `--prompt "$prompt"` (variable form) | `worker/tasks/copilot_cli.py:513` | ✅ |
| Old `--prompt "$(cat \"$prompt_file\")"` pattern | absent | ✅ |
| `COPILOT_CLI_DIAGNOSTIC_MODE` env handling | `worker/tasks/copilot_cli.py:160` | ✅ |

### O1 — Gated probe (L3=false)

| Field | Value |
|---|---|
| `mission_run_id` | `6e3989dd6b4349458667fdc551f1f32d` |
| `decision` | `execute_flag_off_dry_run` |
| `dry_run` | `true` |
| `egress_activated` | `false` |
| `phase_blocks_real_execution` | `true` (expected for L3=false path) |
| `policy.real_execution_implemented` | `true` |
| `policy.execute_enabled` | `false` |
| audit log | `reports/copilot-cli/2026-05/6e3989dd6b4349458667fdc551f1f32d.jsonl` |

Probe ran at `2026-05-06T12:51:33Z`, **before** the window-open backup at
`12:52:30Z`. This is the only audit event from this session — no second event
was written.

### O2 — DNS resolver (`scripts/copilot_egress_resolver.py --non-strict --format json`)

VPS DNS resolved correctly this session (in contrast to the previous
`863af7a4` retry where it failed).

| set | count | sample |
|---|---:|---|
| `copilot_v4` | 6 | `140.82.112.21`, `140.82.112.22`, `140.82.114.21`, `140.82.114.22`, `4.228.31.149`, `4.228.31.153` |
| `copilot_v6` | 0 | — |

DNS hard-stop did **not** trigger; window proceeded to O3.

## Window Open / Interrupted (≈ 12:52:30Z → 13:00:00Z)

### Backup taken before opening
`/home/rick/.copilot/backups/f8a-prompt-quoting-20260506T125230Z/`

```
copilot-cli.env           (envfile snapshot — L3=false)
tool_policy.yaml          (policy snapshot — egress.activated=false)
nft-ruleset-before.nft    (full host nft ruleset snapshot)
nft-table-during.txt      (copilot_egress table after apply)
```

### Changes applied during window

- `sudo nft -f infra/networking/copilot-egress.nft.example` → **table created**
- `nft add element inet copilot_egress copilot_v4 { 6 IPs }` → **populated**
- `config/tool_policy.yaml`: `egress.activated: false → true` (working tree
  only, never committed)
- `/home/rick/.config/openclaw/copilot-cli.env`:
  - `RICK_COPILOT_CLI_EXECUTE=false → true`
  - added `COPILOT_CLI_DIAGNOSTIC_MODE=true`
  - added `COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:6940cf0f274d`
  - added `COPILOT_CLI_DOCKER_NETWORK=bridge`
- `systemctl --user restart umbral-worker.service` → restart succeeded
  (PID `980 → 16764`); `/health` returned 200

### Why no run executed

The bash session running the orchestrator script was killed (likely
copilot-cli session loss or VM disconnect) immediately after the worker
restart and **before the `curl POST /run` line**. No second audit event was
written. No artifact directory was created for this batch_id. The audit
folder still shows `6e3989dd…` (O1 probe) as the most recent event.

## Critical architectural finding — host-wide egress drop policy

The `infra/networking/copilot-egress.nft.example` table installs a
`hook output priority filter; policy drop;` chain that applies to **all
host outbound traffic**, not just the Docker container. During the ≈ 8-minute
window the rules were active, every connection from the worker process to
non-Copilot destinations was dropped:

```
journalctl --user -u umbral-worker --since '12:52' --until '13:00'
  Temporary failure in name resolution   : 39 occurrences
  [ERROR] entries                        : 13 occurrences
```

All 13 errors are from `notion.read_database` and `notion.poll_comments` losing
egress to `api.notion.com`.

**This is a real production risk.** Before any future F8A real-run window:
1. The egress profile should be scoped to the Copilot container’s netns or
   to a cgroup, not applied as a host-global filter; **or**
2. The allowlist must include every endpoint the worker process needs (Notion
   API, GitHub API for non-Copilot use, etc.); **or**
3. All other worker tasks (Notion poller, etc.) must be paused for the
   duration of the run window.

Option 1 is architecturally cleanest and matches the original intent (sandbox
the Copilot container, not the host).

## Rollback / recovery (executed in a separate session)

```text
RICK_COPILOT_CLI_ENABLED=true        ✅ unchanged (L1 stays open)
RICK_COPILOT_CLI_EXECUTE=false       ✅ restored from backup
COPILOT_CLI_DIAGNOSTIC_MODE          ✅ removed from envfile
egress.activated=false               ✅ restored in tool_policy.yaml
inet copilot_egress nft table        ✅ deleted
docker network copilot               ✅ never created
worker restart                       ✅ OLD_PID=980  → NEW_PID=6956
/health                              ✅ HTTP 200
process RICK_COPILOT_CLI_EXECUTE     ✅ false in /proc/$PID/environ
process COPILOT_GITHUB_TOKEN         ✅ present_by_name
```

## Secret scan

| Surface | Patterns checked | Result |
|---|---|---|
| audit `6e3989dd…jsonl` | `ghp_*`, `github_pat_*`, `ghs_*`, `sk-*` | ✅ clean |
| backup envfile snapshot | same | ✅ clean (token only present by reference, not in repo) |
| this report body | same | ✅ clean (`present_by_name` only) |

## Verdict — 🟡 amarillo

- Source fixes (prompt quoting, `-i`, diagnostic mode) confirmed in main.
- Preflight O1/O2 passed cleanly.
- Window opened safely, restart succeeded, no Copilot run occurred.
- Recovery completed; system is in the expected pre-window state.
- **Blocker for next retry**: host-wide egress drop policy must be redesigned
  before a real run is attempted, otherwise the Notion poller (and any other
  outbound worker traffic) will continue to fail during the window.

## Suggested next task

`f8a-redesign-egress-scope-2026-05-07.md` (or similar) covering:
- containerised egress (Docker network + per-container nft) instead of host
  hook;
- additive allowlist for Notion / GitHub Web while a Copilot run is active;
- pause-mode for Notion poller during run windows as a fallback.

Once that is in place, schedule another F8A first-real-run retry.
