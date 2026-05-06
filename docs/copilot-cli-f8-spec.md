# F8 — Copilot CLI single-agent productive mode spec

**Date:** 2026-05-05
**Owner:** David approval gate; Rick / Gerencia Desarrollo runtime owner
**Status:** Spec only. No runtime activation.
**Scope:** first productive single-agent `copilot_cli.run` mode, before any
multi-agent tournament.

---

## 1. Purpose

F8 turns `copilot_cli.run` from a rehearsed capability into a **single-agent
productive mode**: Rick may delegate one bounded, auditable, sandboxed task to
Copilot CLI and receive artifacts back.

F8 is not multi-agent batch mode. It is the last proving ground before F8.5 /
F11 tournament pilots.

F8 must prove:

1. A single `copilot_cli.run` can execute safely in the sandbox.
2. The run produces useful artifacts.
3. The run leaves complete traceability: `batch_id`, `agent_id`,
   `mission_run_id`, tokens, cost, exit code, duration, artifacts.
4. No external channel, Notion write, GitHub push, merge, publish, or persistent
   OpenClaw subagent is created.

---

## 2. Current state and blocker

Latest F7.5A evidence:

- Report: `reports/copilot-cli/f7-5a-code-gate-deploy-2026-05-05.md`
- Verdict: **verde**
- Meaning: the code-side gate L5 is open in live runtime, and the worker still
  blocks safely at L3 (`execute_flag_off_dry_run`).

This F8A PR implements the missing real subprocess/Docker execution path. It
does **not** open L3 or L4 in production.

Current gate posture after F7.5A:

| Layer | Gate | Current state | F8 implication |
|---|---|---:|---|
| L1 | `RICK_COPILOT_CLI_ENABLED` | `true` | already open |
| L2 | `copilot_cli.enabled` | `true` | already open |
| L3 | `RICK_COPILOT_CLI_EXECUTE` | `false` | must open only inside approved run window |
| L4 | `copilot_cli.egress.activated` + live nft/Docker egress | `false` / absent | must be provisioned before real run |
| L5 | `_REAL_EXECUTION_IMPLEMENTED` | `True` | code gate open; F8A adds the real execution path |

F8 cannot be marked closed until at least 3 productive single-agent runs are
green. F8A only makes the first controlled run technically possible.

---

## 3. Governance boundary

This spec follows `notion-governance@main` commit `1122e9b`,
`docs/architecture/15-rick-organizational-model.md`:

- §8.bis: `copilot_cli.run` is a runtime sandboxed capability, not an OpenClaw
  persistent subagent.
- Runs are ephemeral and identified by `batch_id`, `agent_id`,
  `mission_run_id`.
- The capability is owned by Gerencia Desarrollo and may be invoked by
  Investigación only under policy.
- Runs must not touch external channels §3.5.
- If a result should be published, Rick or Comunicación handles that later with
  the correct identity and explicit approval.
- §11 tournament mode is blocked until F7.5 + F8 are closed and an N=2 pilot is
  green.

F8 must therefore stay single-agent and artifact-only.

---

## 4. Non-goals

F8 does not allow:

- multi-agent batches;
- persistent OpenClaw subagents;
- writes to Notion, Slack, Telegram, LinkedIn, Gmail, or any channel §3.5;
- `git push`;
- `gh pr create`;
- merge;
- deploy;
- production writes;
- arbitrary shell;
- web-open browsing from sandbox;
- unbounded egress;
- concurrent runs.

---

## 5. F8 closure criteria

F8 is closed only when all criteria below are met.

### A. F7.5 prerequisite

- [ ] F7.5 verdict is **verde**.
- [ ] F7.5 report includes non-`n/a` values for:
  - `batch_id`
  - `agent_id`
  - `mission_run_id`
  - `tokens`
  - `cost_usd`
  - `exit_code`
  - `duration_sec`
  - `artifacts`
- [ ] F7.5 rollback evidence shows L3 returned to `false` after the one-shot
  run, unless David explicitly approved a longer bounded run window.

### B. Three productive single-agent runs

- [ ] 3 consecutive single-agent runs complete without manual intervention
  during the run.
- [ ] Each run uses exactly one `agent_id`.
- [ ] Each run has one `mission_run_id`.
- [ ] No run invokes tournament or multi-agent semantics.
- [ ] Each run produces at least one artifact.
- [ ] Each run is reviewed by Rick/Codex before being counted.

### C. Cost and duration limits

Default F8 budget until David changes it:

| Limit | Value |
|---|---:|
| max cost per run | USD 1.00 |
| max total cost for 3-run F8 closure | USD 3.00 |
| max wall time per run | 10 minutes |
| max files read per run | 80 |
| max artifacts per run | 10 |
| max output artifact size per run | 2 MB |

If Copilot CLI does not expose exact token/cost metrics directly, F8 cannot close
until the report records a defensible source for them, for example a GitHub
usage export, billing view, or explicit `tokens_source` / `cost_source` field
accepted by David.

### D. Safety limits

- [ ] 0 secret patterns in reports/artifacts (`ghp_`, `github_pat_`, `ghs_`,
  `sk-`, `WORKER_TOKEN`, `COPILOT_GITHUB_TOKEN` values).
- [ ] 0 wrapper deny-list bypasses.
- [ ] 0 nft egress drops caused by unexpected Copilot traffic, or drops are
  explained and the run is marked yellow.
- [ ] 0 writes outside scratch/artifact paths.
- [ ] 0 GitHub push/PR/merge/deploy attempts.
- [ ] 0 Notion/channel writes.
- [ ] Worker remains healthy after each run.

### E. Governance limits

- [ ] Each run includes `runtime_refs` suitable for later linking to a Rick
  delegation trace.
- [ ] Runs are not registered in `openclaw.json`.
- [ ] Runs do not require `subagents.allowAgents`.
- [ ] Runs remain owned by Gerencia Desarrollo.
- [ ] Any research dependency is handled through structured material, not open
  web browsing from sandbox.

---

## 6. Initial safe brief catalog

Only these briefs are candidates for F8. Anything else requires a new review.

| ID | Brief | Mission | Allowed operations | Expected artifact | Risk |
|---|---|---|---|---|---|
| F8-B1 | "Read `worker/tasks/copilot_cli.py` and list the top 3 risks before enabling writes." | `research` | `read_repo` | risk report markdown | low |
| F8-B2 | "Explain why this captured pytest failure happened, using only the provided log artifact." | `test_explain` | `read_artifact` | explanation markdown | low |
| F8-B3 | "Compare `docs/copilot-cli-autonomy-vision-roadmap.md` and `docs/copilot-cli-capability-design.md`; list drift only." | `research` | `read_repo` | drift report markdown | low |
| F8-B4 | "Propose a test plan for `copilot_cli.run`; do not write code." | `plan_patch` | `read_repo` | test plan markdown | low |
| F8-B5 | "Summarize the egress readiness docs and list missing evidence for a green run." | `research` | `read_repo` | checklist markdown | low |
| F8-B6 | "Given a pasted CI log artifact, classify failure bucket and recommend next diagnostic command." | `test_explain` | `read_artifact` | diagnostic markdown | low |

Not allowed in F8:

- "fix this bug";
- "apply this patch";
- "open a PR";
- "publish this";
- "write to Notion";
- "run arbitrary tests";
- "browse the web";
- "use multiple agents";
- "compare N strategies".

Those belong to F9+ or F11.

---

## 7. Required observability hooks

Each run must produce a JSONL event stream and an artifact manifest.

### Required JSONL fields

```yaml
timestamp: "<iso8601>"
event: "copilot_cli.run.started|completed|blocked|failed"
batch_id: "<string>"
agent_id: "<string>"
mission_run_id: "<uuid>"
mission: "research|test_explain|plan_patch"
brief_id: "F8-B1"
prompt_sha256: "<hash, not raw prompt if sensitive>"
repo_path: "<allowlisted path>"
repo_head: "<git sha>"
sandbox_image: "umbral-sandbox-copilot-cli:<tag>"
container_id: "<docker id or n/a>"
requested_operations: ["read_repo"]
allowed_operations: ["read_repo"]
denied_operations: []
gate_snapshot:
  L1_env_enabled: true
  L2_policy_enabled: true
  L3_execute_enabled: true
  L4_egress_activated: true
  L5_real_execution_implemented: true
egress_snapshot:
  nft_table_present: true
  copilot_v4_count: 1
  copilot_v6_count: 0
  docker_network: "<name>"
duration_sec: 0
exit_code: 0
tokens:
  input: 0
  output: 0
  total: 0
  source: "<source>"
cost_usd:
  value: 0.0
  source: "<source>"
artifacts:
  - path: "artifacts/copilot-cli/<batch>/<agent>/<run>/report.md"
    sha256: "<hash>"
redaction:
  secret_scan: "clean"
  token_values_printed: false
policy_violation: false
```

### Required artifact manifest

```yaml
batch_id: "<string>"
agent_id: "<string>"
mission_run_id: "<uuid>"
brief_id: "F8-B1"
created_at: "<iso8601>"
artifacts:
  - path: "report.md"
    sha256: "<hash>"
    bytes: 1234
    type: "markdown"
review:
  reviewer: "rick|codex|david"
  verdict: "green|yellow|red"
  notes: ""
```

### Required log sources

Each run report must cite:

- Worker audit JSONL path.
- `journalctl --user -u umbral-worker.service` time window.
- Docker container inspect summary.
- nft table/set/counter snapshot before and after the run.
- Artifact manifest path.
- Secret scan result.

---

## 8. Gate opening plan for L3, L4, L5

L5 is already open after F7.5A. For actual runtime safety, L3 remains the last
gate opened because it is the fastest kill-switch. The activation order for one
run is now: **deploy F8A with L3 false -> provision L4 egress -> open L3
temporary window -> run once -> rollback L3**.

| Gate | Evidence needed before opening | How to open | Rollback | Owner |
|---|---|---|---|---|
| L3 `RICK_COPILOT_CLI_EXECUTE` | F7.5A deployed; L4 egress ready; one approved brief; budget set; worker healthy; token present by name only | edit envfile `false -> true`, restart worker | restore backup envfile, restart worker | David/operator |
| L4 `egress.activated` + live nft/Docker | resolver dry-run clean; IP sets populated; `sudo nft -c` clean; apply/rollback tested; no stale table | apply nft table with populated sets, create required Docker network, set policy `activated=true` by PR if handler requires it | delete nft table, remove Docker network, revert policy | Copilot-VPS under David approval |
| L5 `_REAL_EXECUTION_IMPLEMENTED` | F7.5A evidence green; F8A code path tested with mocked subprocess; L3 remains false | already open in live; F8A deploy should still block at L3 until David opens it | revert PR or deploy rollback commit | Codex/David approval |

### Minimum evidence to keep L3 open during a run

L3 can stay `true` only inside a named run window:

```yaml
run_window_id: "f8-run-001"
starts_at: "<iso8601>"
expires_at: "<iso8601, <= 30 minutes>"
approved_by: "David"
brief_id: "F8-B1"
max_cost_usd: 1.00
rollback_command: "cp copilot-cli.env.bak.<id> copilot-cli.env && systemctl --user restart umbral-worker.service"
```

If the window expires, Copilot-VPS must rollback L3 before doing anything else.

---

## 9. F8 run protocol

### Phase 0 — Readiness

- Pull `main`.
- Verify Worker health.
- Verify L1/L2 open.
- Verify L3 false before planned window.
- Verify L4 egress table/network ready if required.
- Verify L5 true after deploy.
- Verify no stale run window.

### Phase 1 — Approve run

David approves:

- `brief_id`;
- cost cap;
- time cap;
- whether L3 opens for one run only;
- rollback instruction.

### Phase 2 — Open execution window

Copilot-VPS:

- backs up envfile;
- opens L3;
- restarts worker;
- verifies process env shows L3 true;
- records `run_window_id`.

### Phase 3 — Execute one run

Worker receives one `copilot_cli.run`.

The request must include:

```yaml
batch_id: "f8-single-agent-001"
agent_id: "rick-tech-f8-single-001"
mission_run_id: "<uuid>"
brief_id: "F8-B1"
mission: "research"
requested_operations:
  - "read_repo"
limits:
  max_wall_sec: 600
  max_cost_usd: 1.00
```

### Phase 4 — Rollback

Immediately after the run:

- restore L3 false;
- restart worker;
- verify L3 false in process env;
- remove nft/Docker network only if this was a temporary F8 rehearsal setup;
- verify worker health.

### Phase 5 — Review

Codex/Rick reviews:

- report completeness;
- cost/tokens;
- artifacts;
- policy violations;
- secrets scan;
- governance boundaries.

Only reviewed runs can count toward F8 closure.

---

## 10. F8 verdict scale

| Verdict | Meaning |
|---|---|
| green | run completed, artifact useful, all metrics complete, no violations, rollback verified |
| yellow | run blocked or completed with non-dangerous gap (missing metric source, artifact weak, egress warning) |
| red | token exposure, unexpected write, channel touch, unbounded egress, worker unhealthy, rollback failed, or policy bypass |

F8 closure requires 3 consecutive green runs.

---

## 11. Relationship to F8.5 and F11 tournament

F8.5 is the first N=2 pilot:

- still read-only;
- no PR creation;
- no writes;
- two ephemeral `agent_id`s;
- same brief, different strategies;
- tournament trace schema from `notion-governance` §11.4.

F11 only starts after:

1. F7.5 green.
2. F8 closed.
3. F8.5 N=2 green.
4. Investigation/research dependency has a structured path or an accepted manual
   stub.

Until then, "Modo Torneo" remains design-only.

---

## 12. Immediate next actions

Given F7.5A is green and F8A implements the real execution path, the next
actions are:

1. Review/merge the F8A real-execution-path PR.
2. Ask Copilot-VPS to deploy F8A with L3 still false and verify the probe still
   blocks at `execute_flag_off_dry_run`.
3. Provision L4 egress with populated IP sets and verify no broad egress.
4. Open L3 for one approved scratch run window only.
5. Execute one F8A/F7.5 scratch run with `dry_run=false`.
6. Roll back L3 immediately and review artifacts, token scan, exit code,
   duration, and cost/tokens source.

No F8 productive run should be counted until the one-shot F8A scratch run is
green and reviewed.
