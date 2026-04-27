# PR draft body — copy/paste into GitHub UI

**Title:**
`[Draft][F1-F6] Rick × Copilot CLI capability — gated, staged, no execution`

**Base:** `main`
**Compare:** `rick/copilot-cli-capability-design`
**Mark as Draft:** ✅ yes

**Compare URL:**
https://github.com/Umbral-Bot/umbral-agent-stack/compare/main...rick/copilot-cli-capability-design?expand=1

---

## What this PR does

Lands the off-by-default "Rick × GitHub Copilot CLI" capability,
phases F1 → F6 step 6C-3. The capability is **disabled at four
layers** by design and ships with no execution path:

1. `RICK_COPILOT_CLI_ENABLED` (env, layer 1) — defaults to `false`
   in `.env.example`.
2. `copilot_cli.enabled` (policy, layer 2) — `false` in
   `config/tool_policy.yaml`.
3. `RICK_COPILOT_CLI_EXECUTE` (env, layer 3a) — defaults to `false`.
4. `_REAL_EXECUTION_IMPLEMENTED` (code, layer 3b) — hard-coded
   `False` in `worker/tasks/copilot_cli.py`.

Plus `copilot_cli.egress.activated: false` for the network layer.

The handler is registered, schema-validated, policy-gated, and
audit-logged, but every path through it returns
`capability_disabled` until all four flags are intentionally flipped
in a future PR. No Copilot HTTPS request is possible from this
codebase as-is.

## Diff scope

43 files changed, 8521 insertions, 0 deletions. **Strict
fast-forward** of `main` (zero merge conflicts per `git merge-tree`).

| Category | M | A |
|---|---|---|
| Top-level config | `.env.example`, `.gitignore` | — |
| Policy | `config/tool_policy.yaml` | — |
| Worker code | `worker/tasks/__init__.py`, `worker/tool_policy.py` | `worker/tasks/copilot_cli.py` |
| Worker sandbox | — | `worker/sandbox/Dockerfile.copilot-cli` + 5 helper scripts |
| Infra (examples) | — | `infra/env/copilot-cli{,-secrets}.env.example`, `infra/networking/copilot-egress.{nft.example,resolver.md}`, `infra/systemd/umbral-worker-copilot-cli.conf.example` |
| Scripts (read-only) | — | `scripts/{verify_copilot_cli_env_contract,verify_copilot_egress_contract,copilot_egress_resolver,plan_copilot_cli_live_staging}.py` |
| Tests | — | 6 test modules, +132 tests |
| Agent overrides | — | `openclaw/workspace-agent-overrides/rick-tech/{ROLE,HEARTBEAT}.md` |
| Docs | — | 14 `docs/copilot-cli-*.md` files |

## Phases delivered

- **F1** — guardrails design (4 capability flags, 5 enforcement
  layers, audit log contract).
- **F2** — Docker sandbox image (`worker/sandbox/Dockerfile.copilot-cli`
  + smoke/wrapper helpers; never built or run by this PR).
- **F3** — handler skeleton in `worker/tasks/copilot_cli.py` with
  triple-gate (env / policy / execute+impl).
- **F4** — 4 mission contracts (`research`, `lint-suggest`,
  `test-explain`, `runbook-draft`) with strict allow/forbid op
  lists.
- **F5** — `rick-tech` agent role + heartbeat under
  `openclaw/workspace-agent-overrides/`.
- **F6 step 1** — `RICK_COPILOT_CLI_EXECUTE` flag +
  `_REAL_EXECUTION_IMPLEMENTED=False` constant.
- **F6 step 2** — `infra/systemd/`, `infra/env/` example artifacts +
  `verify_copilot_cli_env_contract.py`.
- **F6 step 3** — `infra/networking/copilot-egress.nft.example`,
  resolver design doc, `verify_copilot_egress_contract.py`.
- **F6 step 4** — `scripts/copilot_egress_resolver.py` dry-run
  resolver (refuses to invoke `nft`/`iptables`/`ufw`).
- **F6 step 5** — operation scoping enforcement in handler
  (`requested_operations` + global hard-deny set + audit enrichment).
- **F6 step 6A** — `scripts/plan_copilot_cli_live_staging.py`
  read-only planner (refuses any mutating systemctl verb).
- **F6 step 6B** — operator-only user-scope staging (envfiles +
  drop-in installed under `~/.config/openclaw/` and
  `~/.config/systemd/user/umbral-worker.service.d/`; daemon-reload
  only, no restart).
- **F6 step 6C-1** — operator pasted fine-grained PAT v2 into the
  staged secrets envfile (token never seen by agent, never committed).
- **F6 step 6C-2** — flipped `RICK_COPILOT_CLI_ENABLED=true` and
  performed one worker restart; `COPILOT_GITHUB_TOKEN` now in process
  env, but route still `Unknown task` because handler isn't deployed
  to the live tree yet.
- **F6 step 6C-3** — this deployment plan (the doc this PR carries
  in `docs/copilot-cli-f6-step6c3-live-worker-deployment-plan.md`).

## Reviewer checklist (must hold for merge)

Before approving this PR, confirm by inspecting the diff:

- [ ] `config/tool_policy.yaml` → `copilot_cli.enabled: false`
- [ ] `worker/tasks/copilot_cli.py` → `_REAL_EXECUTION_IMPLEMENTED = False`
- [ ] `config/tool_policy.yaml` → `copilot_cli.egress.activated: false`
- [ ] `.env.example` → both `RICK_COPILOT_CLI_ENABLED=false` and
      `RICK_COPILOT_CLI_EXECUTE=false`
- [ ] No token in diff:
      `git diff origin/main...HEAD | grep -E 'github_pat_|ghp_|ghs_'`
      returns empty
- [ ] No edits to `notion/`, `dispatcher/`, `client/`, or any
      existing task handler beyond two-line registry insertion in
      `worker/tasks/__init__.py`
- [ ] `worker/tool_policy.py` change preserves all existing tool
      behaviour (only adds `copilot_cli` loader)
- [ ] `.gitignore` change limited to `reports/copilot-cli/` and
      sandbox cache patterns
- [ ] CI green (132 new tests in 6 test modules; pre-existing tests
      unaffected)

## What this PR does NOT do

- ✗ Does NOT enable the capability (every flag stays `false`/`False`).
- ✗ Does NOT call Copilot HTTPS.
- ✗ Does NOT build the Docker sandbox image.
- ✗ Does NOT install anything under `/etc/`.
- ✗ Does NOT modify `/etc/nftables.conf` or apply `nft -f`.
- ✗ Does NOT create any Docker network.
- ✗ Does NOT install systemd drop-ins (those are operator-only on
  the host; this PR ships them as `infra/systemd/*.example`).
- ✗ Does NOT touch any Notion / gates / publication surface.
- ✗ Does NOT modify any other agent's tasks.

## Post-merge plan (separate PR / step, not this one)

After merge to `main`:

1. Operator runs `git pull --ff-only` in
   `/home/rick/umbral-agent-stack/`.
2. Operator runs **one** `systemctl --user restart umbral-worker.service`.
3. Operator runs probes 1–6 from
   `docs/copilot-cli-f6-step6c3-live-worker-deployment-plan.md` §5.6.
4. Success criterion: `POST /run {"task":"copilot_cli.run", …}`
   changes from `"Unknown task: copilot_cli.run"` to
   `{"error":"capability_disabled","reason":"policy_off", …}`.

Flipping `copilot_cli.enabled`, `RICK_COPILOT_CLI_EXECUTE`,
`_REAL_EXECUTION_IMPLEMENTED`, and `copilot_cli.egress.activated`
to `true` requires multiple additional explicit PRs and reviews —
see `docs/copilot-cli-capability-design.md` §11.

## Rollback (post-merge)

If any post-deploy probe fails:

```sh
git -C /home/rick/umbral-agent-stack reset --hard <pre-merge-main-sha>
systemctl --user restart umbral-worker.service
```

Or, more conservatively, open a revert PR on the merge commit.

## Documentation index

- `docs/copilot-cli-capability-design.md` — master design doc
  (decisions D1 → D23, phase status §11)
- `docs/copilot-cli-f2-sandbox-evidence.md`
- `docs/copilot-cli-f3-task-evidence.md`
- `docs/copilot-cli-f4-mission-contracts-evidence.md`
- `docs/copilot-cli-f5-rick-tech-agent-evidence.md`
- `docs/copilot-cli-f6-step1-token-plumbing-evidence.md`
- `docs/copilot-cli-f6-step2-envfile-artifacts-evidence.md`
- `docs/copilot-cli-f6-step3-egress-design-evidence.md`
- `docs/copilot-cli-f6-step4-egress-resolver-dry-run-evidence.md`
- `docs/copilot-cli-f6-step5-operation-scoping-evidence.md`
- `docs/copilot-cli-f6-step6a-live-staging-readiness.md`
- `docs/copilot-cli-f6-step6b-user-staging-evidence.md`
- `docs/copilot-cli-f6-step6c1-token-staging-evidence.md`
- `docs/copilot-cli-f6-step6c2-token-loaded-gates-closed-evidence.md`
- `docs/copilot-cli-f6-step6c3-live-worker-deployment-plan.md`
