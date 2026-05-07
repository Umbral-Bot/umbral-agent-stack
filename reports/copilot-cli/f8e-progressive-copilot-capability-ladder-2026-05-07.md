# F8E — Progressive Copilot capability ladder

- Task: [.agents/tasks/f8e-progressive-copilot-capability-ladder-2026-05-07.md](../../.agents/tasks/f8e-progressive-copilot-capability-ladder-2026-05-07.md)
- Approval: `APPROVE_F8E_PROGRESSIVE_COPILOT_CAPABILITY_LADDER=YES`
- Date (UTC): 2026-05-07
- Branch: `rick/f8e-progressive-copilot-capability-ladder-2026-05-07`
- Verdict: **verde fuerte** (after token rotation retry — see History)

## Headline

After David rotated the worker `COPILOT_GITHUB_TOKEN` in
`~/.config/openclaw/copilot-cli-secrets.env` (length 93, fingerprint
`066741648703 → 39fa34a87824`, never printed), the entire F8E ladder was
re-executed from T1 under the same approval string.

T0 → T7 all GREEN, with one residual amarillo parcial in T3
(`opus_available=false`: the Copilot backend does not expose
`Claude Opus 4.7` for this token; default model works fine and was used
for T4–T7 per spec). Network drops `0/0` across every probe, no token
leak, rollback verified clean (`/health=200`, no `inet copilot_egress`
table, no `copilot-egress` docker network, tokens shredded).

The worker-mediated canonical `copilot_cli.run` path is **end-to-end
proven** for read-only research missions: gates L1–L5 reachable, audit
JSONL written, artifact manifest populated, `secret_scan: clean`,
hardened sandbox argv recorded.

## Test ladder result table

| Test | Status | Verdict | Notes |
|---|---|---|---|
| T0 sync + source gates | run | pass | `/health=200`, branch checked out, sandbox image rebuilt deterministically |
| T1 token entitlement | run | **green** | `F8E_T1_OK`, rc=0, `nft_drop_delta=0/0`, `container_ready_ms=347`, `copilot_exit_ms=11846` |
| T2 default-model minimal compute | run | **green** | rc=0, stdout `17`, drops=0/0, `copilot_exit_ms=9019`, `container_ready_ms=279` |
| T3 model override discovery (Opus 4.7) | run | **amarillo parcial** | `Error: Model "Claude Opus 4.7" from --model flag is not available.` → `opus_available=false`; default model used for T4+ |
| T4 canonical `copilot_cli.run` | run | **green** | decision=`completed`, `exit_code=0`, `duration_sec=13.275`, stdout contains `F8E_T4_CANONICAL_OK`, audit + manifest written |
| T5 repo comprehension | run | **green (5/5)** | 5 distinct responsibilities, file paths cited, identifies L1–L5, sandbox, audit, allowlist, egress |
| T6 risk review | run | **green (5/5)** | 5 distinct risks with severity + mitigation, code-grounded (DNS, wrapper gap, tool list, diff gate, write enforcement) |
| T7 patch proposal text-only | run | **green (5/5)** | All 5 required sections present (gates, sandbox, tests, rollback, acceptance); ≥3 file path citations |

## History — first run vs retry

| Run | Commit | T1 result | Outcome |
|---|---|---|---|
| First (PR #331) | `20e11ff` | rc=1 `Authentication failed (Request ID …)` | STOP amarillo at T1; T2–T7 skipped |
| Retry (this revision) | this commit | rc=0 `F8E_T1_OK` | T1–T7 executed; verde fuerte |

Token rotation evidence (no value disclosed):

```
F8E_T1_TOKEN_INSTALLED=YES
COPILOT_GITHUB_TOKEN=present_by_name
COPILOT_GITHUB_TOKEN_LENGTH=93
TOK_FP_F8E_FIRST=066741648703
TOK_FP_F8E_RETRY=39fa34a87824
GITHUB_USER_HTTP=200
HEALTH=200
```

## 0. Source verification (T0 — re-run lite)

| Item | Value |
|---|---|
| Branch | `rick/f8e-progressive-copilot-capability-ladder-2026-05-07` |
| Worker `/health` | 200 |
| Sandbox image (deterministic tag) | `umbral-sandbox-copilot-cli:6940cf0f274d` (also tagged `:latest` for worker default) |
| Image rebuilt in retry | yes (`bash worker/sandbox/refresh-copilot-cli.sh`) — image was missing locally |

## 1. T1 — Default-model minimal probe (direct sandbox)

```json
{
  "label": "T1",
  "model": "default",
  "rc": 0,
  "stdout_bytes": 202,
  "stderr_bytes": 116,
  "container_ready_ms": 347,
  "copilot_exit_ms": 11846,
  "nft_drop_delta": {"packets": 0, "bytes": 0},
  "token_leak": false
}
```

stdout contains `F8E_T1_OK`. CLI footer: `Requests 1 Premium (7s)`,
`Tokens ↑ 4.4k • ↓ 11`. No drops.

## 2. T2 — Default-model minimal compute (direct sandbox)

Prompt: `Compute 12+5 and return only the result.`

```json
{
  "label": "T2",
  "model": "default",
  "rc": 0,
  "stdout": "17",
  "container_ready_ms": 279,
  "copilot_exit_ms": 9019,
  "nft_drop_delta": {"packets": 0, "bytes": 0}
}
```

## 3. T3 — Model override discovery (Opus 4.7, direct sandbox)

```
Error: Model "Claude Opus 4.7" from --model flag is not available.
```

`rc=1`, drops `0/0`, no leak. Per spec: register `opus_available=false`
and continue T4+ without `--model`.

## 4. T4 — Canonical `copilot_cli.run` (worker-mediated)

Gates opened in this window only:

- L4 (`tool_policy.copilot_cli.egress.activated: false → true`) — `config/tool_policy.yaml` line 222.
- L3 (`RICK_COPILOT_CLI_EXECUTE: false → true`) — `~/.config/openclaw/copilot-cli.env` (envfile already loaded by existing drop-in `copilot-cli.conf`).
- Diagnostic + docker network env via temporary drop-in `~/.config/systemd/user/umbral-worker.service.d/f8e-t4-enable.conf` (mode 0600, removed in rollback).
- Worker restarted; `/health=200`; token still present, `TOK_FP=39fa34a87824` unchanged.

Image alias: `docker tag umbral-sandbox-copilot-cli:6940cf0f274d
umbral-sandbox-copilot-cli:latest` so the worker's default tag resolves
locally.

Payload (verbatim):

```json
{
  "task": "copilot_cli.run",
  "input": {
    "mission": "research",
    "requested_operations": ["read_repo"],
    "repo_path": "/home/rick/umbral-agent-stack",
    "dry_run": false,
    "prompt": "Return exactly: F8E_T4_CANONICAL_OK. Do not write files."
  }
}
```

Worker response (relevant fields):

```
HTTP=200
decision=completed
phase=F8A.real_execution
executed=True
exit_code=0
duration_sec=13.275
egress_activated=True
mission_run_id=60d28545714a426f9d9aff69fac43d39
audit_log=reports/copilot-cli/2026-05/60d28545714a426f9d9aff69fac43d39.jsonl
artifact_manifest=artifacts/copilot-cli/2026-05/single/copilot-cli/60d28545714a426f9d9aff69fac43d39/manifest.json
artifacts.stdout.bytes=210
artifacts.stderr.bytes=79
secret_scan.status=clean
nft_drop_delta=0/0
```

Artifact stdout includes the marker `F8E_T4_CANONICAL_OK`. Docker argv
(redacted, captured by audit) confirms hardened invocation:
`--read-only --cap-drop=ALL --security-opt no-new-privileges --user
10001:10001 --ipc=none --network=copilot-egress
--mount type=bind,source=/home/rick/umbral-agent-stack,target=/work,readonly
--env COPILOT_GITHUB_TOKEN`, plus tmpfs for `/tmp`, `/scratch`,
`/home/runner/.cache`, `/home/runner/.copilot`, and Copilot CLI flags
`--no-color --no-auto-update --no-remote --no-ask-user
--disable-builtin-mcps --secret-env-vars=COPILOT_GITHUB_TOKEN
--available-tools=view,grep,glob --log-level=debug`.

## 5. T5 — Repo comprehension (worker-mediated, score 5/5)

Prompt: `Read the repo at /work and return a 5-bullet map of the
responsibilities of worker/tasks/copilot_cli.py. Cite at least 3 file
paths. Do not write files.`

Result: `decision=completed`, `exit_code=0`, `duration_sec=29.919`,
drops `0/0`. Output covers all checklist items:

1. Multi-layer execution gating (L1–L5), cites lines 8–14, 342–347.
2. Schema & policy validation, cites `worker/tool_policy.py` and
   `_GLOBAL_HARD_DENY_OPERATIONS`.
3. Sandboxed Docker execution, cites lines 462–570 (read-only,
   `--cap-drop=ALL`, scoped egress).
4. Repo path allowlisting (`_REPO_ROOT`, optional
   `COPILOT_CLI_ALLOWED_REPO_ROOTS`), cites lines 60–153.
5. Append-only audit logging & artifact writing, cites lines 155–333,
   redaction via `_SENSITIVE_PATTERNS`.

Score: **5/5**.

## 6. T6 — Risk review (worker-mediated, score 5/5)

Prompt asked for top-5 remaining risks before write-limited missions
with severity + one-sentence mitigation. Result: `exit_code=0`,
`duration_sec=83.75`, drops `0/0`. Risks identified (severity in
parentheses):

1. **HIGH** — No write enforcement at container level despite policy
   declaring `max_files_touched > 0` for some missions. Mitigation:
   per-mission writable overlay (tmpfs + explicit copy-out) gated by a
   path/file-count enforcer.
2. **HIGH** — Unrestricted DNS in `copilot-egress.nft.example`
   (`udp/tcp dport 53` accepted with no destination IP filter).
   Mitigation: pin to host resolver IP(s) or route via a logging
   resolver checking against `allowed_endpoints`.
3. **HIGH** — Copilot's internal agentic tool calls bypass the
   substring matcher in `copilot-cli-wrapper`. Mitigation: seccomp /
   `--security-opt` to block `execve` of `git`, `gh`, `sh` at kernel
   level for defense-in-depth.
4. **MED** — `--available-tools` is hardcoded per execution mode, not
   per mission. Mitigation: thread `allowed_operations` from policy
   through to a per-mission tool list at `_build_docker_argv` time.
5. **MED** — No structured diff capture or human-approval checkpoint
   between sandbox stdout and artifact persistence. Mitigation: add a
   diff-capture stage as first-class artifact + keep
   `requires_human_materialization: true` until an approval workflow
   exists.

Score: **5/5**.

## 7. T7 — Patch proposal text-only (worker-mediated, score 5/5)

Prompt requested a text-only implementation plan for write-limited
patch proposals with explicit sections (gates, sandbox/FS, tests,
rollback, acceptance) and ≥3 file citations. Result: `exit_code=0`,
`duration_sec=105.934`, drops `0/0`, `stdout_bytes=12968`.

All 5 required sections present. File paths cited include
`worker/tasks/copilot_cli.py`, `config/tool_policy.yaml`,
`worker/tool_policy.py`, `worker/sandbox/workspace.py`,
`tests/test_copilot_cli.py`, `tests/test_sandbox_workspace.py`,
`copilot_agent/agent.py`, `copilot_agent/__main__.py`. No file edits;
no full code patch emitted.

Score: **5/5**.

## 8. Score system (final)

| Score | Value | Rationale |
|---|---|---|
| `network_score` | **1.0** | All probes (T1, T2, T3, T4, T5, T6, T7) `nft_drop_delta=0/0` |
| `auth_score` | **1.0** | T1 backend auth succeeded after rotation |
| `canonical_score` | **1.0** | T4 worker-mediated `copilot_cli.run` `decision=completed exit_code=0`; secret_scan clean; audit + manifest written |
| `quality_score` | **1.0** | (T5 + T6 + T7) / 15 = 15/15 |
| `safety_score` | **1.0** | No leaks, no writes, host policy unchanged, rollback verified clean |
| `model_power_score` | **0.5** | Default model fully proven; Opus 4.7 not exposed by Copilot for this token (`opus_available=false`) |

Verdict mapping: T1–T4 GREEN + `network_score=1` + `safety_score=1` +
`canonical_score=1` + (T5,T6,T7) ≥ 4/5 each → **verde fuerte**.

## 9. Rollback proof

```
~/.config/openclaw/copilot-cli.env restored from /tmp/.f8e-cliEnv.bak
RICK_COPILOT_CLI_EXECUTE=false                    (verified in /proc/$WPID/environ)
COPILOT_CLI_DIAGNOSTIC_MODE                       absent (drop-in removed)
config/tool_policy.yaml :: egress.activated=false (verified)
~/.config/systemd/user/umbral-worker.service.d/f8e-t4-enable.conf  removed
systemctl --user daemon-reload && restart umbral-worker.service     ok
curl http://127.0.0.1:8088/health                                   HEALTH=200
sudo nft delete table inet copilot_egress                           ok
sudo nft list tables | grep -c copilot_egress                       0
docker network rm copilot-egress                                    ok
docker network ls | grep -c copilot-egress                          0
shred -u /tmp/.f8e-tok /tmp/.f8e-wtok                                ok
```

Pre-existing host firewall `policy drop` chains were not modified. The
sandbox image and the `:latest` tag added by this task remain locally
available; they are not a security exposure (no privileged exec, no
network without explicit run flags).

## 10. Recommendations

1. **Provision Copilot Opus access for the worker token** if Opus 4.7
   is desired in production routing — current token only exposes
   default and other Claude/GPT models. Until then, leave model
   selection to the default in mission configs.
2. **Promote T4 path under a controlled rollout**: keep L3/L4 gates
   closed by default; require an explicit `APPROVE_*` per session
   before flipping `egress.activated` and `RICK_COPILOT_CLI_EXECUTE`.
3. **Address the T6 HIGH risks before any write-limited mission is
   enabled**: container DNS pinning, kernel-level `execve` block of
   `git`/`gh`/`sh`, and a write enforcement layer with diff capture.
4. **Tag policy at the worker layer**: have the worker prefer the
   pinned `umbral-sandbox-copilot-cli:6940cf0f274d` tag (env
   `COPILOT_CLI_SANDBOX_IMAGE`) instead of relying on `:latest`, so the
   `docker tag :latest` workaround used in this retry can be removed.

## 11. Artifacts

- T4 audit log: `reports/copilot-cli/2026-05/60d28545714a426f9d9aff69fac43d39.jsonl`
- T4 artifacts: `artifacts/copilot-cli/2026-05/single/copilot-cli/60d28545714a426f9d9aff69fac43d39/`
- T5/T6/T7 audit logs: `reports/copilot-cli/2026-05/*.jsonl` (mission_run_ids logged in audit)
- Probe helper (direct sandbox T1/T2/T3): `/tmp/f8e-probe.sh` (ephemeral, not committed)

cc @codex
