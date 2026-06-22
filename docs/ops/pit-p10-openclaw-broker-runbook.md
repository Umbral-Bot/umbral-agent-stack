# PIT P10 — OpenClaw broker-real torneo (runbook)

- **Date (UTC):** 2026-06-22
- **Surface split:** Copilot Windows (repo + PR) builds and validates the code
  path; `ssh umbral-vps` (host srv1431451, user `rick`) executes plan-only and —
  only inside a David-authorized window — the real spawn.
- **Status without GO:** `P10_OPENCLAW_BROKER_PLAN_OK` (plan-only) + this runbook
  + PR. Real spawn (Fase 8) stays **BLOCKED** until David provides the verbatim
  authorization + spawn phrases (§6).
- **Evidence root (Windows):** `C:\Users\david\.coord-ag-evidence\pit-p10-openclaw-broker-20260622\`

This runbook closes the gap left open by the P1–P9 handoff
(`docs/ops/pit-broker-real-pass-handoff-20260622.md` §4): broker-real was proven
via **direct worker POSTs** (`openclaw_total=0`). P10 orchestrates **ephemeral
OpenClaw agents** that each dispatch exactly one `copilot_cli.run`, so the token
ledger records `openclaw_total>0`.

---

## 1. P9 → P10 gap and the `openclaw_total` nuance

| | P9 (broker-real golden) | P10 (this) |
|---|---|---|
| Who fires `copilot_cli.run` | a shell loop POSTing the Worker directly | ephemeral OpenClaw agents `<pit_id>-lane-*` |
| OpenClaw agents spawned | none | one per lane (`main_standalone`) |
| Ledger `openclaw_total` | `0` (expected) | `> 0` (the agents' own reasoning tokens) |
| Worker contract | `copilot_cli.run`, 1 POST/lane, no retries | identical — unchanged |

**Nuance — what `openclaw_total` actually counts.** `pit_collect_tokens.py` sums
the token usage recorded in `~/.openclaw/agents/<pit_id>-lane-*/sessions.json`.
That is the **OpenClaw agent's own** token spend (its reasoning to construct and
fire the `worker-call`), **not** the `copilot_cli.run` execution cost (GitHub
Copilot CLI does not report tokens — see P9 handoff §4). Consequently:

- `openclaw_total>0` is achieved as soon as the ephemeral agents run and reason,
  **even if** the Worker returns `capability_disabled` (L3/G2 closed). The agent
  still spends tokens deciding to call the Worker and parsing the reply.
- Therefore **a green `openclaw_total>0` does NOT require opening L3/L4/nft.** The
  default-closed spawn (Fase 8 with only the spawn gate, gates closed) is enough
  to prove OpenClaw orchestration end-to-end. Opening L3/L4/nft only changes
  whether `copilot_cli.run` does *real* execution (egress), which is a separate,
  optional escalation reusing the P9 window machinery.
- Lane "broker completeness" (`BROKER_EXECUTED=true` + `BROKER_EXIT=0`) is a
  property of the **lane's announce**, independent of `openclaw_total`.

This split is why P10 can deliver a meaningful PASS (`openclaw_total>0`, OpenClaw
orchestration proven) under closed gates, and treat real egress execution as an
opt-in built on the already-audited P9 rollback-guaranteed window.

---

## 2. Artifacts (this package)

Isolated **v2 broker code path** — the v1 product runner is left 100% intact.

| Artifact | Purpose |
|---|---|
| `examples/pit/pit_spec.openclaw-broker-v1.yaml` | P10 spec (schema_version 2, broker) — 3 lanes, `openclaw_orchestration` block |
| `examples/pit/pit-openclaw-broker-v1.lanes.yaml` | lane enrichment (`lane_id` + `lane_focus`) |
| `openclaw/workspace-templates/pit-lane-agent/ROLE.template.broker.md` | per-lane ROLE template (broker contract, no WORKER_TOKEN leak) |
| `scripts/pit/pit_spec_validate.py` | `OpenClawOrchestration` model + `openclaw_orchestration` field on `PitSpecV2` |
| `scripts/pit/pit_broker_run.py` | **core P10 runner** — smoke + plan-only + real spawn; isolated from v1 |
| `scripts/pit/pit_tournament_run.py` | unchanged v1 flow + a top-of-`main` router that delegates broker specs to `pit_broker_run.main` |
| `scripts/pit/pit_broker_dry_run.sh` | local smoke wrapper (no OpenClaw, no Worker, no internet) |
| `scripts/pit/pit_openclaw_broker_run.sh` | VPS entrypoint (PATH `~/.npm-global/bin`; sources WORKER_URL/WORKER_TOKEN) |
| `scripts/pit/pit_broker_window.sh` | Fase 8 L3/L4/nft window manager, safe-by-default, auto-rollback trap |
| `tests/test_pit_openclaw_broker.py` | broker unit/integration tests (FakeOpenClaw harness) |
| `tests/test_pit_spec_validate.py` | extended with `openclaw_orchestration` cases |

### 2.1 Verdict markers (`pit_broker_run.py`)

| Marker | exit | Meaning |
|---|---|---|
| `PIT_DRY_RUN_PASS` / `PIT_DRY_RUN_FAIL` | 0 / 1 | `--smoke` outcome (feeds the run smoke gate) |
| `P10_OPENCLAW_BROKER_PLAN_OK` | 0 | plan-only: spec+lanes+roles+spawn-prompt rendered, **no spawn**, gates untouched |
| `P10_OPENCLAW_BROKER_RUN_PASS` | 0 | all lanes `broker_complete` after real spawn |
| `P10_OPENCLAW_BROKER_PARTIAL` | 1 | ≥2 lanes complete (not all) |
| `P10_OPENCLAW_BROKER_FAIL` | 1 | spawn failed or <2 lanes complete |
| `P10_OPENCLAW_BROKER_BLOCKED` | 2 | gate phrase / smoke / preflight failed |

A lane is `broker_complete` iff its workspace has `announce.md` **and**
`broker_result.json` **and** the announce carries `BROKER_EXECUTED=true` **and**
`BROKER_EXIT=0`.

### 2.2 Code-path isolation (v1 safety)

`pit_tournament_run.py:main` begins with a router: if the first positional arg is
a file that `is_broker_spec()` recognizes (schema_version 2 or a `broker_contract`
key), it calls `pit_broker_run.main(raw_args)` and returns. Otherwise v1's
argparse/preflight/flow runs unchanged. Verified both directions in
`tests/test_pit_openclaw_broker.py` and the existing v1 suite
(`tests/test_pit_tournament_run.py`).

---

## 3. Local validation (Fase 4 — Windows or any dev box)

```powershell
$env:PYTHONIOENCODING = "utf-8"; $env:WORKER_TOKEN = "test"
python scripts/pit/pit_spec_validate.py examples/pit/pit_spec.openclaw-broker-v1.yaml   # status: pass, exit 0
python scripts/pit/pit_broker_run.py examples/pit/pit_spec.openclaw-broker-v1.yaml `
  examples/pit/pit-openclaw-broker-v1.lanes.yaml --smoke                                # PIT_DRY_RUN_PASS, exit 0
python scripts/pit/pit_broker_run.py examples/pit/pit_spec.openclaw-broker-v1.yaml `
  examples/pit/pit-openclaw-broker-v1.lanes.yaml --plan-only                            # P10_OPENCLAW_BROKER_PLAN_OK, exit 0
python -m pytest tests/test_pit_openclaw_broker.py tests/test_pit_spec_validate.py -q   # green
```

> On Windows the `tests/mission_control/test_pit_preview.py` symlink-escape tests
> error with `WinError 1314` (admin-only `os.symlink`); that is environmental and
> unrelated to P10 — those pass on Linux/VPS.

---

## 4. VPS deploy protocol (NEVER `pull` onto a dirty main)

The running services consume code from `~/umbral-agent-stack`. Deploy the PR
branch with `checkout -B` against the remote ref — never merge into or pull onto
local `main` (P9 audit found main carries a harmless untracked file).

```bash
cd ~/umbral-agent-stack
git fetch origin <pr-branch>
git checkout -B <pr-branch> origin/<pr-branch>
git rev-parse --short HEAD
# bash syntax-check the shipped scripts (deferred from Windows, no bash there):
bash -n scripts/pit/pit_broker_dry_run.sh
bash -n scripts/pit/pit_openclaw_broker_run.sh
bash -n scripts/pit/pit_broker_window.sh
```

No service restart is required for plan-only: the broker scripts are invoked on
demand and do not change `worker/`, `dispatcher/`, or `identity/`. (If a future
change touches those, follow the standard restart + health-check protocol.)

---

## 5. Fase 5 — plan-only on the VPS (gates stay CLOSED)

Goal: prove the spec validates, the smoke gate is green, and the runner renders
the full spawn plan **without spawning anything**, while confirming all gates are
closed. Produces `P10_OPENCLAW_BROKER_PLAN_OK`.

```bash
cd ~/umbral-agent-stack
PY=.venv/bin/python
EVID=~/.coord-ag-evidence/pit-p10-openclaw-broker-20260622
mkdir -p "$EVID"

# 1. spec validates
$PY scripts/pit/pit_spec_validate.py examples/pit/pit_spec.openclaw-broker-v1.yaml | tee "$EVID/01-spec-validate.txt"

# 2. smoke gate (no OpenClaw/Worker/internet) — writes final-metrics.json
PYTHON_BIN=$PY bash scripts/pit/pit_broker_dry_run.sh \
  examples/pit/pit_spec.openclaw-broker-v1.yaml \
  examples/pit/pit-openclaw-broker-v1.lanes.yaml \
  --evidence-dir "$EVID/smoke" | tee "$EVID/02-smoke.txt"        # PIT_DRY_RUN_PASS

# 3. plan-only (renders roles + spawn-prompt, no spawn). The smoke gate runs
#    before the plan-only branch, so point it at the metrics written in step 2.
PYTHON_BIN=$PY bash scripts/pit/pit_openclaw_broker_run.sh \
  examples/pit/pit_spec.openclaw-broker-v1.yaml \
  examples/pit/pit-openclaw-broker-v1.lanes.yaml \
  --plan-only --smoke-metrics "$EVID/smoke/final-metrics.json" \
  --evidence-dir "$EVID/plan" | tee "$EVID/03-plan.txt"          # P10_OPENCLAW_BROKER_PLAN_OK

# 4. gates CLOSED (read-only assertions)
grep '^RICK_COPILOT_CLI_EXECUTE=' ~/.config/openclaw/copilot-cli.env | tee "$EVID/04-gates.txt"   # =false
sed -n '240p' config/tool_policy.yaml | tee -a "$EVID/04-gates.txt"                                 # activated: false
sudo -n nft list table inet copilot_egress 2>&1 | tee -a "$EVID/04-gates.txt"                       # ABSENT
```

Plan-only also runs the **vault preflight** (read-only) against the default real
vault `~/umbral-pit-vault` — present on the VPS from P9. If your vault lives
elsewhere, pass `--vault-path <path>` (or set `$PIT_VAULT_PATH`).

Copy evidence back to Windows:

```powershell
scp -r umbral-vps:~/.coord-ag-evidence/pit-p10-openclaw-broker-20260622/* `
  "$env:USERPROFILE\.coord-ag-evidence\pit-p10-openclaw-broker-20260622\"
```

---

## 6. Fase 8 — real spawn (BLOCKED until David authorizes)

> Do **not** proceed without both verbatim phrases below. Real spawn registers
> ephemeral agents and restarts the OpenClaw gateway; opening L3/L4/nft is an
> additional, separately-authorized escalation.

### 6.1 GO phrases (verbatim)

- **Window authorization (only if opening L3/L4/nft for real egress):**
  `autorizo P10 openclaw broker-real torneo 3 lanes copilot_cli read-only probe`
- **Spawn gate (always required for any real spawn):** `ok, arranca`

Per the P9 doctrine, every run needs a fresh, explicit, bounded phrase — there is
no standing authorization.

### 6.2 Spawn with gates CLOSED (recommended first real run)

This proves OpenClaw orchestration and yields `openclaw_total>0` without touching
L3/L4/nft. `copilot_cli.run` returns `capability_disabled` (expected); lanes still
announce and the agents still spend tokens.

```bash
cd ~/umbral-agent-stack
PY=.venv/bin/python
EVID=~/.coord-ag-evidence/pit-p10-openclaw-broker-20260622
# Reuses the fresh smoke metrics from Fase 5 step 2 (re-run it if stale):
PYTHON_BIN=$PY bash scripts/pit/pit_openclaw_broker_run.sh \
  examples/pit/pit_spec.openclaw-broker-v1.yaml \
  examples/pit/pit-openclaw-broker-v1.lanes.yaml \
  --gate "ok, arranca" --smoke-metrics "$EVID/smoke/final-metrics.json" \
  --evidence-dir "$EVID/spawn-closed" | tee "$EVID/08-spawn-closed.txt"
```

### 6.3 Optional escalation — real egress execution (reuses P9 window)

Only if David also gives the §6.1 window phrase. `pit_broker_window.sh` manages
the host-side L3 (G2) toggle and L4 (nft + docker) with an auto-rollback trap.

```bash
# inspect current gate state (always dry/read-only)
bash scripts/pit/pit_broker_window.sh status

# open (requires the operator to assert David's GO):
bash scripts/pit/pit_broker_window.sh open --execute --authorized --keep-open

#   ... run §6.2 spawn while the window is open ...

# close (restore byte-identical, nft ABSENT, worker health 200):
bash scripts/pit/pit_broker_window.sh close --execute
```

`open --execute` without `--keep-open` installs `trap rollback EXIT INT TERM HUP`,
so an abnormal exit auto-closes the window. G1 (`copilot_cli.enabled`) and G3
(`_REAL_EXECUTION_IMPLEMENTED`) are code/config gates changed only via PR+pull and
are never mutated by the window script — only verified in `status`.

---

## 7. Ledger collection (post-run, read-only)

```bash
.venv/bin/python scripts/pit/pit_collect_tokens.py \
  --pit-id pit-openclaw-broker-v1 --vault-root ~/umbral-pit-vault \
  --openclaw-root ~/.openclaw --audit-root reports/copilot-cli \
  --output ~/umbral-pit-vault/pit/pit-openclaw-broker-v1/metrics/token_ledger.yaml
```

P10 success criterion: `lanes=3`, **`openclaw_total>0`**, per-lane present, and
the broker verdict `P10_OPENCLAW_BROKER_RUN_PASS` (or `_PARTIAL` ≥2 lanes).

### 7.1 Refire results — 2026-06-22 §6.2 read-only probe (gates CLOSED)

First real spawn executed under §6.2 (gates never opened). Authorization phrase:
`ok, arranca` ("copilot_cli read-only probe"). Evidence dir
`~/.coord-ag-evidence/pit-p10-openclaw-broker-fase8-refire-20260622`.

**Outcome — orchestration + dispatch proven end-to-end:**

- `PIT_SPAWN_FIRED 3` in the gateway journal → 3 ephemeral lanes spawned via
  `sessions_spawn` under the standalone `main` agent (G-D1b).
- All 3 lanes POSTed `copilot_cli.run` to the Worker and received **HTTP 200**
  (`"ok":true`, real `task_id`/`trace_id`) — lane→Worker auth works (the
  `WORKER_TOKEN` reaches lanes via the gateway `EnvironmentFile`, not the
  orchestrator env). This closes the auth gap that blocked the prior attempt.
- The Worker gated execution at the **egress layer** for every lane:
  `error:"egress_not_activated"`, `would_run:false`, `egress_activated:false` →
  `BROKER_EXECUTED=false`, `BROKER_EXIT=1`, with a real `BROKER_AUDIT_ID` +
  audit log per lane. This is the intended read-only probe — the broker reached
  the final gate and correctly refused real execution because egress is off.

| lane | model | session | input | output | audit_id (8) |
|---|---|---|---|---|---|
| lane-foundry-tools | gpt-5.5/high | df06db1a | 52,494 | 1,861 | 5550e52f |
| lane-codex-depth | claude-opus-4.7/xhigh | 8544144a | 27,581 | 1,729 | 87cc44ec |
| lane-cost-mini | gpt-5.4-mini/medium | 840bcfa1 | 48,068 | 1,645 | fba4c7f6 |

**`openclaw_total` = 133,378 tokens** (input 128,143 + output 5,235) vs **P9 = 0**.
The P10 headline (real OpenClaw agents spend tokens, not direct POSTs) is met.

**⚠ Collector path-convention gap (follow-up, not a run failure):**
`pit_collect_tokens.py` globs `agents/<pit_id>-lane-*/sessions/sessions.json`, but
this runner spawns lanes as `sessions_spawn` **sub-sessions of `main`**, so their
token records live in `~/.openclaw/agents/main/sessions/sessions.json` (1:1 to each
lane via trajectory `lane_id` match). The official collector therefore reports
`openclaw_total=0` with the note *"no openclaw lane agents matched …"* while
correctly capturing `copilot_cli_calls=3`. The authoritative spend is the direct
read above (`31-ledger-direct.txt`). **Fix forward:** teach the collector to also
attribute `agents/main/sessions/` entries by `lane_id`, or have the runner spawn
into dedicated `<pit_id>-lane-*` agent dirs. Token records persist after cleanup
(the `finally` kills live sub-sessions + deregisters agents; it does not delete the
`main` session store).

**Broker verdict caveat:** `broker_complete` requires `BROKER_EXECUTED=true`, so
with egress gated the strict verdict is FAIL/PARTIAL **by design** — that label
reflects the intentional gating, not a defect. The collection loop also blocks
until `lane_timeout` (1800 s) because no lane reaches `broker_complete`; the probe
was ended early with `SIGINT` once all lanes had written terminal results.

**Gates after run:** nft `copilot_egress` ABSENT (closed), worker health 200, no
orphan lane processes, VPS returned to `main`. Secret scan over evidence: CLEAN.

**§6.3 (real egress execution, `BROKER_EXECUTED=true`) was NOT run** — it requires
David's explicit §6.1 window phrase, which was not given. Recommended as the
optional next escalation.

---

## 8. Default gate state (must hold outside an authorized window)

| Gate | Default | Verify |
|---|---|---|
| L3 execute | `RICK_COPILOT_CLI_EXECUTE=false` | `grep '^RICK_COPILOT_CLI_EXECUTE=' ~/.config/openclaw/copilot-cli.env` |
| L4 egress | `activated: false` (L240) | `sed -n '240p' config/tool_policy.yaml` |
| nft egress | ABSENT | `sudo -n nft list table inet copilot_egress` |

After any Fase 8 work, return the VPS to `main` with gates closed:

```bash
cd ~/umbral-agent-stack
git checkout main && git pull --ff-only origin main 2>/dev/null || git fetch origin main
# confirm L3=false, L4=activated:false, nft ABSENT, no <pit_id>-lane-* agents registered
```

---

## 9. Known limitations

- **`copilot_cli` token cost is `not_reported`** — GitHub Copilot CLI does not emit
  token/cost; `openclaw_total` measures the OpenClaw agents' reasoning only (§1).
- **Spec lane_ids vs operational lane_ids** — the spec uses
  `lane-foundry-tools / lane-codex-depth / lane-cost-mini` for ledger continuity
  with the P9 golden lanes (same models).
- **No retries on real broker POSTs** — each lane fires exactly one
  `copilot_cli.run`; a failed POST yields an incomplete lane, never a retry.
- **Ephemerals are always deregistered** — `run_broker_tournament` kills and
  deregisters `<pit_id>-lane-*` in a `finally` block even when spawn fails.
