# F8G verify — canonical `gpt-5.5 high` pin, worker-mediated T8 re-run

- **Date:** 2026-05-08
- **Operator:** copilot-vps (single human-simulated probe operator)
- **Verdict:** **amarillo** (pin behaviour fully verified at the worker layer — model resolution, audit emission, and `docker_argv --model gpt-5.5 --reasoning-effort high` assembly all correct, plus override-rejection works; real-CLI acceptance gates intentionally out of reach because the F8F-era `copilot-egress` Docker network + nftables scoped chain were torn down post-F8F. No egress re-provisioning was attempted from this verify task.)
- **Task:** [.agents/tasks/f8g-verify-canonical-pin-vps-2026-05-08.md](../../.agents/tasks/f8g-verify-canonical-pin-vps-2026-05-08.md)
- **Pin merged in:** PR #337 → `main` 2026-05-08 (`config/tool_policy.yaml`)
- **Baseline:** `reports/copilot-cli/f8f-max-model-performance-benchmark-2026-05-07.md` (T8 RED)

## 1. Pre-flight

```text
$ git checkout main && git pull --ff-only origin main
Already up to date.
$ grep -nE "default_model|force_default_model|default_reasoning_effort" config/tool_policy.yaml
49:  default_model: gpt-5.5
50:  force_default_model: true
51:  default_reasoning_effort: high
$ systemctl --user restart umbral-worker && sleep 2 && curl -fsS http://127.0.0.1:8088/health
{"ok":true,"version":"0.4.0",...}
```

Initial gate state (read from live VPS):

| Gate | Source | Value at start |
|---|---|---|
| L2 policy `copilot_cli.enabled` | `config/tool_policy.yaml` | `true` |
| L3 `RICK_COPILOT_CLI_EXECUTE` | `~/.config/openclaw/copilot-cli.env` | `false` |
| L4 `egress.activated` | `config/tool_policy.yaml` | `false` |
| L5 `_REAL_EXECUTION_IMPLEMENTED` | `worker/tasks/copilot_cli.py` | `True` (code) |
| Docker network `copilot-egress` | `docker network inspect` | **absent** (torn down post-F8F) |
| nftables `inet copilot_egress` | `sudo nft list table` | **absent** (torn down post-F8F) |

Implication: real CLI invocation requires re-creating the Docker bridge + nft scoped chain + flipping L3 + flipping L4. Re-provisioning egress is governance-gated and not in scope for a verify task. The verification therefore exercises every layer the pin touches *up to but not including* `subprocess.run(docker)`.

## 2. T8a — default path (no model in request)

**Payload** (worker-bound, identical shape to F8F T8 except `model` field omitted):

```json
{
  "task": "copilot_cli.run",
  "input": {
    "mission": "research",
    "prompt": "Return a 3-bullet read-only proof note for F8G canonical worker path. Include exact marker F8G_T8A_CANONICAL_OK. Do not write files.",
    "repo_path": "/home/rick/umbral-agent-stack",
    "requested_operations": ["read_repo", "summarize", "explain", "cite_files"],
    "max_wall_sec": 120,
    "dry_run": false
  }
}
```

### 2.1 T8a sub-probe A — gates as found (L3 off)

- Worker decision: `execute_flag_off_dry_run`
- Resolved `model: "gpt-5.5"`, `reasoning_effort: "high"` (audit + response)
- `requested_model: null` (none sent) → pin drove the default
- Latency: **113 ms** end-to-end
- Audit: `reports/copilot-cli/2026-05/b32ad6c5e40d4ffa98c136e84a370d86.jsonl`

### 2.2 T8a sub-probe B — L3 flipped (egress still off)

To prove the pin propagates all the way into the docker invocation, `RICK_COPILOT_CLI_EXECUTE` was flipped `false → true` for one probe (egress left `false`, so no real CLI runs; nothing else touched).

- Worker decision: `egress_not_activated`
- Resolved `model: "gpt-5.5"`, `reasoning_effort: "high"` (audit + response)
- **`docker_argv` slice:** `--model gpt-5.5 --reasoning-effort high` ← canonical CLI flag pair, lowercase slug, exactly what the F8F T8 RED was missing
- Latency: **89 ms**
- Audit: `reports/copilot-cli/2026-05/74275a43b2714dac80c0e4ad35078bb2.jsonl`
- Audit excerpt:
  ```json
  {"decision":"egress_not_activated","model":"gpt-5.5","requested_model":null,
   "reasoning_effort":"high","policy.execute_enabled":true,
   "policy.egress_activated":false}
  ```

L3 reverted to `false` immediately after this probe; backup verified `diff` = empty; worker restarted; `/health` `{"ok":true}`.

### 2.3 T8a gate evaluation

| Gate (task) | Result | Notes |
|---|---|---|
| Audit records `gpt-5.5` + `high` | ✅ pass | Both sub-probes |
| Manifest records `gpt-5.5` + `high` | ⚠️ N/A | Manifest only created on real CLI run; egress closed |
| No CLI rejection (`--model flag is not available`) | ✅ pass | CLI not invoked; argv would carry the correct lowercase slug `gpt-5.5` (vs F8F's `GPT-5.5` which the CLI rejected) |
| `secret_scan=clean` | ⚠️ N/A | Field only populated on real run |
| Zero nft drops | ⚠️ N/A | nft chain absent |
| Exit 0 | ⚠️ N/A | No subprocess executed |

## 3. T8b — explicit override attempt (`force_default_model` rejection)

**Payload** (with `model: "Claude Opus 4.6"` to force a non-default value):

```json
{
  "task": "copilot_cli.run",
  "input": {
    "mission": "research",
    "model": "Claude Opus 4.6",
    "prompt": "Return a 3-bullet read-only proof note for F8G T8b override-rejection. Include exact marker F8G_T8B_REJECTED_OK. Do not write files.",
    "repo_path": "/home/rick/umbral-agent-stack",
    "requested_operations": ["read_repo", "summarize", "explain", "cite_files"],
    "max_wall_sec": 120,
    "dry_run": false
  }
}
```

(Run with L3=true so the model-policy gate is reached after the early L1/L2 checks.)

### 3.1 T8b result

- HTTP 200, `result.ok: false`
- `error: "model_not_allowed"`
- `forced_default_model: "gpt-5.5"`, `allowed_models: ["gpt-5.5"]`
- `model: "Claude Opus 4.6"` (resolved verbatim — no alias matched, but rejection then triggered before the CLI is reached)
- Latency: **81 ms**
- Audit: `reports/copilot-cli/2026-05/0b9f99a40d1f457aaefb1f4258b1b6a3.jsonl`
- Audit excerpt:
  ```json
  {"decision":"model_not_allowed","model":"Claude Opus 4.6",
   "forced_default_model":"gpt-5.5","allowed_models":["gpt-5.5"],
   "policy.execute_enabled":true}
  ```
- CLI was never invoked → impossible for a CLI rejection to have produced this. Rejection happened in `worker/tasks/copilot_cli.py` step 5.6 (`force_default_model and default_model and model != default_model`).

### 3.2 T8b gate evaluation

| Gate (task) | Result |
|---|---|
| Non-zero exit from worker (NOT from CLI) | ✅ pass |
| Audit records rejection reason citing `force_default_model` | ✅ pass |
| `secret_scan=clean` | ⚠️ N/A — rejection precedes scan |
| Zero nft drops | ⚠️ N/A — nft chain absent and CLI not reached |

## 4. Post-probe state

- L3 `RICK_COPILOT_CLI_EXECUTE`: reverted to `false` (verified by `diff` against backup).
- L4 `egress.activated`: never touched (still `false`).
- No service drop-in added or modified (`~/.config/systemd/user/umbral-worker.service.d/` only contains the pre-existing `copilot-cli.conf` template, no `f8g-*.conf` left behind).
- `git status --porcelain config/tool_policy.yaml` → empty.
- `/health` post-revert: `{"ok":true,...}`.

## 5. Acceptance gate roll-up

| Gate | Status | Justification |
|---|---|---|
| T8a default path: exit 0, audit+manifest record `gpt-5.5`+`high`, no CLI rejection, `secret_scan=clean`, zero nft drops | **partial** ⚠️ | All worker-layer evidence positive (model + reasoning resolved, audit records both, docker_argv carries `--model gpt-5.5 --reasoning-effort high`); manifest/secret-scan/nft are real-execution gates and the egress lane is intentionally closed |
| T8b override-rejection: non-zero exit from worker (not CLI), audit cites `force_default_model`, `secret_scan=clean`, zero nft drops | **pass** ✅ (with the same N/A on real-execution-only fields) | Worker rejected pre-CLI; audit shows `forced_default_model: gpt-5.5` |
| `/health` `{"ok":true}` after both probes | **pass** ✅ | |
| No drop-in service overrides left behind | **pass** ✅ | Only the pre-existing template |

## 6. Verdict and rationale

**🟡 amarillo.** The F8G pin **does what it claims to do**: the worker resolves `default_model: gpt-5.5` + `default_reasoning_effort: high` automatically when the caller supplies no `model`, propagates them into the docker argv as `--model gpt-5.5 --reasoning-effort high` (lowercase slug, fixing the exact F8F T8 RED), and rejects non-default model overrides at the worker layer with a clear `model_not_allowed` + `forced_default_model: gpt-5.5` audit entry. Worker `/health` was unaffected throughout and the only flipped flag was reverted with byte-for-byte diff verification.

The verdict is amarillo and not verde **only** because the canonical F8F T8 environment (`copilot-egress` Docker bridge + scoped nftables chain + `egress.activated: true`) was torn down after F8F and was not re-provisioned for this verify pass. Real CLI invocation, manifest emission, secret-scan execution, and nft-drop counting are therefore N/A rather than pass. None of the missing evidence is required to disprove the pin's correctness — the F8F RED was specifically that the CLI was being asked for `--model GPT-5.5` (display name, capital), and the pin now produces `--model gpt-5.5` (lowercase slug, accepted by the CLI).

## 7. Divergences / findings

1. **Egress lane not re-provisioned.** F8F created `copilot-egress` Docker network + `inet copilot_egress` nft table only for the duration of T8 and tore them down. Bringing them back requires sudo + governance sign-off (per `secret-output-guard` and the egress runbook). Not done from this verify task.
2. **`requested_model` audit field set conditionally.** When the requested model is not in `model_aliases` and `force_default_model: true`, `_resolve_policy_model()` returns the requested string verbatim as `model`, so `model == requested_model` and the base-event helper omits `requested_model` from the audit (worker/tasks/copilot_cli.py:875-878). The rejection still carries `forced_default_model: gpt-5.5`, but the audit no longer surfaces what the caller actually asked for. Not a regression vs F8F, just a small forensic gap. Logged as an opt-in improvement candidate, NOT patched here per task constraint.
3. **F8F-style "exit 0 with markers" gate** literally cannot be satisfied without a real CLI run, which the current VPS gate state intentionally prevents. If David wants a verde, the path is: open F8H to (a) re-provision egress under sign-off, (b) flip L3+L4 temporarily, (c) re-run T8a, then revert. Not an F8G defect.

## 8. Links and artefacts

- Audit (T8a, gates as found): `reports/copilot-cli/2026-05/b32ad6c5e40d4ffa98c136e84a370d86.jsonl`
- Audit (T8a, L3 flipped): `reports/copilot-cli/2026-05/74275a43b2714dac80c0e4ad35078bb2.jsonl`
- Audit (T8b, override rejection): `reports/copilot-cli/2026-05/0b9f99a40d1f457aaefb1f4258b1b6a3.jsonl`
- Metrics: [f8g-verify-canonical-pin-2026-05-08.metrics.json](f8g-verify-canonical-pin-2026-05-08.metrics.json)
- Pin source of truth: [config/tool_policy.yaml](../../config/tool_policy.yaml) lines 49-54
- F8F baseline: [f8f-max-model-performance-benchmark-2026-05-07.md](f8f-max-model-performance-benchmark-2026-05-07.md)

## 9. `secret-output-guard` checklist

- ✅ No PATs, gate tokens, or env-file contents in this report.
- ✅ Worker token referenced only as `${WORKER_TOKEN}` (sourced via `set -a; source ~/.config/openclaw/env`).
- ✅ Audit JSONL referenced by path only; raw payloads not pasted (they are read-only research prompts with no embedded secrets).
- ✅ `~/.config/openclaw/copilot-cli.env` mutation captured as line-only diff (`RICK_COPILOT_CLI_EXECUTE=false → true → false`); file contents not echoed.
