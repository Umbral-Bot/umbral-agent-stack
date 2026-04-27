# Copilot CLI — F6 Step 6C-3 Evidence: Live Worker Deployment Plan (no execution)

**Phase:** F6 step 6C-3 — produce a verifiable plan to land the F6
branch into `/home/rick/umbral-agent-stack/` so `copilot_cli.run` is
registered on the running worker. **No deploy executed. No worker
restart. No flag flip. No PR opened.**

**Branch:** `rick/copilot-cli-capability-design`
**HEAD before this evidence:** `04150f2`

---

## 1. Why this step exists

F6 step 6C-2 left the system in a useful but partial state:

- The live `umbral-worker.service` process holds
  `COPILOT_GITHUB_TOKEN` and `RICK_COPILOT_CLI_ENABLED=true`.
- BUT the live worker loads code from `/home/rick/umbral-agent-stack/`
  on `main` HEAD `e6128bc`, where `worker/tasks/copilot_cli.py`
  doesn't exist. So `POST /run {"task":"copilot_cli.run", …}`
  returns `{"detail":"Unknown task: copilot_cli.run …"}`.

This is the strongest possible "off" state for the route layer: the
handler is literally absent. F6 step 6C-3 documents how to bring the
handler into the live tree without enabling execution.

## 2. Live worktree state (read-only, captured for this evidence)

```
$ git -C /home/rick/umbral-agent-stack branch --show-current
main

$ git -C /home/rick/umbral-agent-stack rev-parse HEAD
e6128bc5fc2fa848c6a1e8255ff597c22436d4e8

$ git -C /home/rick/umbral-agent-stack status --short
?? docs/ops/cand-003-ve-publication-options-run.md

$ git -C /home/rick/umbral-agent-stack log --oneline -5
e6128bc (HEAD -> main, origin/main, origin/HEAD) docs: add linkedin writing rules source
0850694 docs: define editorial agent flow implementation prompt
890b5e8 docs: add CAND-003 V6.1 candidate and QA
204282b docs: harden communication director skill loading
1e8083c docs: document communication director skill materialization
```

Live worker process (from F6 step 6C-2):
- `MainPID=1114334` running `uvicorn worker.app:app` from
  `/home/rick/umbral-agent-stack/.venv/`.
- `/health` → `HTTP 200`.
- `POST /run {"task":"copilot_cli.run", …}` → `Unknown task`.

The single untracked file `docs/ops/cand-003-ve-publication-options-run.md`
is editorial work owned by another thread (CAND-003). It does NOT
overlap with anything in this branch. The deploy plan must NOT
discard it. `git pull --ff-only` is safe with untracked files
present (Git only blocks pulls that would overwrite tracked
modifications, not untracked files in unrelated paths).

## 3. Feature branch state

```
$ git -C /home/rick/umbral-agent-stack-copilot-cli rev-parse HEAD
04150f2681776d74616cba6e5964541a2122536b

$ git -C /home/rick/umbral-agent-stack-copilot-cli merge-base HEAD origin/main
e6128bc5fc2fa848c6a1e8255ff597c22436d4e8

$ git -C /home/rick/umbral-agent-stack-copilot-cli merge-tree e6128bc HEAD origin/main
(empty)
```

**Strict fast-forward.** `origin/main` HEAD equals the merge-base,
so the F6 branch is purely ahead of `main` — `git merge` would be a
fast-forward, and `git pull --ff-only` after merge will succeed
deterministically. Zero conflict markers from `git merge-tree`.

### 3.1 Diff summary vs `origin/main`

```
43 files changed, 8521 insertions(+)
```

| Category | Files modified (M) | Files added (A) |
|---|---|---|
| Top-level config | `.env.example`, `.gitignore` | — |
| Policy | `config/tool_policy.yaml` | — |
| Worker code | `worker/tasks/__init__.py`, `worker/tool_policy.py` | `worker/tasks/copilot_cli.py` |
| Worker sandbox | — | `worker/sandbox/Dockerfile.copilot-cli`, 5 helper scripts |
| Infra | — | `infra/env/copilot-cli{,-secrets}.env.example`, `infra/networking/copilot-egress.{nft.example,resolver.md}`, `infra/systemd/umbral-worker-copilot-cli.conf.example` |
| Scripts | — | `scripts/{verify_copilot_cli_env_contract.py, verify_copilot_egress_contract.py, copilot_egress_resolver.py, plan_copilot_cli_live_staging.py}` |
| Tests | — | `tests/test_{copilot_cli, rick_tech_agent, verify_copilot_cli_env_contract, verify_copilot_egress_contract, copilot_egress_resolver, plan_copilot_cli_live_staging}.py` |
| Agent overrides | — | `openclaw/workspace-agent-overrides/rick-tech/{ROLE.md, HEARTBEAT.md}` |
| Docs | — | 13 `docs/copilot-cli-*.md` files |

### 3.2 Risk surface — the only modifications

The five `M` (modified) files are the only places where the deploy
overwrites existing code:

- `.env.example` — adds two lines (`RICK_COPILOT_CLI_ENABLED=false`,
  `RICK_COPILOT_CLI_EXECUTE=false`). Documentation-only.
- `.gitignore` — adds `reports/copilot-cli/` and a few sandbox
  cache patterns. Documentation/hygiene only.
- `config/tool_policy.yaml` — adds the entire `copilot_cli:` block.
  Master switch lands as `enabled: false`. **No existing key
  changed.**
- `worker/tasks/__init__.py` — two-line addition (`from
  .copilot_cli import handle_copilot_cli_run` and the
  `"copilot_cli.run": handle_copilot_cli_run` entry in the
  registry). No existing entry modified.
- `worker/tool_policy.py` — adds `copilot_cli` policy loader;
  preserves all existing behaviour for other tools.

All other 38 files are pure additions. Probability of regressing
existing tasks is minimal.

## 4. Recommended deploy strategy

The repo policy is human-reviewed PR → `main` → `git pull` on the
live worktree. We follow that policy.

```
[ feature branch ]                  [ main ]                    [ live worktree ]
rick/copilot-cli-capability-design  origin/main                 /home/rick/umbral-agent-stack
HEAD 04150f2                        HEAD e6128bc                HEAD e6128bc
        │                                  │                            │
        │  (1) operator opens PR draft     │                            │
        ├─────────────────────────────────►│                            │
        │  (2) reviewer approves           │                            │
        │  (3) operator merges --ff-only   │                            │
        │                                  │                            │
        │                                  │  (4) operator git pull --ff-only
        │                                  ├───────────────────────────►│
        │                                  │  (5) operator restarts (1×)│
        │                                  │                            │
        │                                  │  (6) post-deploy probes    │
```

Order matters: PR review → merge → pull → restart → probe. **No flag
flip in this step. No `_REAL_EXECUTION_IMPLEMENTED` flip.**

### 4.1 Why fast-forward, not squash

The branch contains 18 commits, every one of which is structured as
"feat" + "docs" pairs with explicit phase tags (F2 → F6 step 6C-2).
This commit history is the audit trail. Squashing to a single commit
would lose the per-step delivery contract. **Recommended: `git merge
--ff-only`** so the linear feature history lands intact on `main`.

## 5. Manual command pack for F6 step 6C-3 → 6C-4 transition (NOT executed)

All `# manual_only`. Operator runs from rick's shell.

### 5.1 Pre-flight (live, read-only)

```sh
# manual_only — confirm state matches this evidence doc before proceeding
git -C /home/rick/umbral-agent-stack rev-parse HEAD          # expect e6128bc
git -C /home/rick/umbral-agent-stack-copilot-cli rev-parse HEAD  # expect 04150f2
systemctl --user show umbral-worker.service -p MainPID --value   # capture OLD_PID
curl -sf http://127.0.0.1:8088/health > /dev/null && echo OK
```

### 5.2 Open PR draft

`gh` is NOT authenticated on the VPS, so PR creation is fully
manual via the web UI:

```
# manual_only — open in browser, NOT via gh
https://github.com/Umbral-Bot/umbral-agent-stack/compare/main...rick/copilot-cli-capability-design?expand=1
```

PR title: `feat(copilot-cli): F6 — Rick × GitHub Copilot CLI capability (off-by-default)`

PR body must include:
- Phases delivered F2 → F6 step 6C-2.
- Reviewer checklist:
  - [ ] `copilot_cli.enabled: false` in `config/tool_policy.yaml`
  - [ ] `_REAL_EXECUTION_IMPLEMENTED = False` in
        `worker/tasks/copilot_cli.py`
  - [ ] `copilot_cli.egress.activated: false`
  - [ ] No token in diff (`git diff origin/main...HEAD | grep -E
        'github_pat_|ghp_'` returns empty)
  - [ ] CI green
  - [ ] No edits to existing notion / linear / worker tasks
- Mark **Draft** until reviewer approval.

### 5.3 Merge (after human approval)

```sh
# manual_only — performed by reviewer in the GitHub UI, "Rebase and merge"
# disabled; "Squash" disabled; choose "Create a merge commit" OR
# locally:
git -C /home/rick/umbral-agent-stack-copilot-cli push origin rick/copilot-cli-capability-design
# Then on the reviewer machine (NOT here):
git checkout main
git merge --ff-only origin/rick/copilot-cli-capability-design
git push origin main
```

### 5.4 Pull on live worktree

```sh
# manual_only — runs on the VPS in rick's shell, no sudo
git -C /home/rick/umbral-agent-stack fetch origin main
git -C /home/rick/umbral-agent-stack pull --ff-only origin main
git -C /home/rick/umbral-agent-stack rev-parse HEAD   # should now be 04150f2 (or newer)
git -C /home/rick/umbral-agent-stack status --short   # should still list only
                                                      # docs/ops/cand-003-ve-publication-options-run.md
```

The untracked CAND-003 file remains untouched: `git pull --ff-only`
will only refuse if there are *modifications to tracked files* that
would be overwritten. Untracked files in unrelated paths are
preserved.

### 5.5 Restart worker (single restart)

```sh
# manual_only
OLD_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
systemctl --user restart umbral-worker.service
sleep 3
NEW_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
test "$OLD_PID" != "$NEW_PID" && echo "restart OK ($OLD_PID -> $NEW_PID)"
curl -sf http://127.0.0.1:8088/health
```

### 5.6 Post-deploy probes (must all pass)

```sh
# manual_only — probe 1: live HTTP /run with copilot_cli.run
TOKEN=$(grep '^WORKER_TOKEN=' ~/.config/openclaw/env | head -1 | cut -d= -f2-)
curl -s -X POST http://127.0.0.1:8088/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task":"copilot_cli.run",
       "input":{"mission":"research","prompt":"hello",
                "requested_operations":["read_repo"]}}'
# EXPECTED change: NO LONGER "Unknown task: copilot_cli.run".
# EXPECTED NEW shape (from worker/tasks/copilot_cli.py handler):
#   {"ok": false, "error": "capability_disabled",
#    "reason": "policy_off",
#    "policy": {"env_enabled": true, "policy_enabled": false}, ...}

# manual_only — probe 2: confirm policy still off in deployed tree
grep -A2 '^copilot_cli:' /home/rick/umbral-agent-stack/config/tool_policy.yaml
# expect:  enabled: false

# manual_only — probe 3: confirm code constant still False
grep '^_REAL_EXECUTION_IMPLEMENTED' /home/rick/umbral-agent-stack/worker/tasks/copilot_cli.py
# expect: _REAL_EXECUTION_IMPLEMENTED = False

# manual_only — probe 4: confirm egress still off
grep -A4 'copilot_cli:' /home/rick/umbral-agent-stack/config/tool_policy.yaml | grep activated
# expect: activated: false

# manual_only — probe 5: confirm no nft / Docker side effects
nft list ruleset 2>/dev/null | grep -i copilot || echo "nft: clean"
docker network ls | grep copilot || echo "docker: clean"

# manual_only — probe 6: tests on the deployed tree
cd /home/rick/umbral-agent-stack
WORKER_TOKEN=test .venv/bin/python -m pytest \
  tests/test_copilot_cli.py tests/test_rick_tech_agent.py \
  tests/test_verify_copilot_egress_contract.py \
  tests/test_copilot_egress_resolver.py \
  tests/test_verify_copilot_cli_env_contract.py \
  tests/test_plan_copilot_cli_live_staging.py -q
# expect: 132 passed
```

The transition success criterion is **probe 1 changing from
`Unknown task` to `capability_disabled / policy_off`**. That is the
single observable signal that 6C-3 → 6C-4 advanced cleanly.

## 6. Manual rollback pack (NOT executed)

If any post-deploy probe fails, rollback is one git operation:

```sh
# manual_only
PRE_DEPLOY_SHA=e6128bc5fc2fa848c6a1e8255ff597c22436d4e8
git -C /home/rick/umbral-agent-stack reset --hard "$PRE_DEPLOY_SHA"
systemctl --user restart umbral-worker.service
curl -sf http://127.0.0.1:8088/health && \
  echo "live worker restored to pre-deploy state"
```

Token + envfiles staged in `~/.config/openclaw/` are unaffected by
the rollback. To also revert F6 step 6C-2 (the env flag flip), see
that step's `§11 Rollback` section.

For an even more conservative rollback (revert on `main` rather
than reset live), the reviewer can open a revert PR on the merge
commit. That's the preferred path if the merge has already been
pulled by other consumers.

## 7. Risks (declared, mitigations baked into the plan)

| Risk | Mitigation |
|---|---|
| PR is large (43 files, 8.5k LOC additions) | Almost all additions are isolated under `worker/sandbox/`, `worker/tasks/copilot_cli.py`, `infra/`, `scripts/`, `tests/`, `docs/`, `openclaw/workspace-agent-overrides/rick-tech/`. The 5 modified files have surgical diffs. Reviewer can split review by directory. |
| Token already loaded in the live worker (post-6C-2) | After deploy, the route exists, but `policy_enabled=false` rejects every request. Token is never sent over HTTPS until step 6C-4 flips `copilot_cli.enabled`. |
| `RICK_COPILOT_CLI_ENABLED=true` is active | Same as above; gate-2 still rejects. |
| `gh` not authenticated → can't open PR via CLI | PR opens manually via web UI; this is acceptable VPS hygiene (no PAT needed in shell history). |
| Restart of `umbral-worker.service` interrupts in-flight requests | Worker is stateless for the relevant routes; clients retry. The restart window is < 5 s in practice. Schedule the restart during a quiet period. |
| `git pull --ff-only` could fail if `main` has diverged by deploy time | The plan re-runs `git fetch` + `merge-base` + `merge-tree` checks immediately before pull. If `main` has diverged, abort and re-plan; do NOT attempt rebase or merge in the live worktree. |
| Untracked CAND-003 doc in live worktree | `git pull --ff-only` preserves untracked files in unrelated paths. No mitigation needed. |
| Docker sandbox image not present on host yet | F6 step 6C-4 (or later) is responsible for `docker build`-ing `umbral-sandbox-copilot-cli:<sha>`. The handler with `_REAL_EXECUTION_IMPLEMENTED=False` never tries to run a container, so deploying without the image is safe. |
| Reviewer accidentally edits `_REAL_EXECUTION_IMPLEMENTED=True` during merge | PR description includes that line in the reviewer checklist. CI does not currently fail on it; future step 6C-4 should add a CI check. |

## 8. What F6 step 6C-3 explicitly does NOT do

- ✗ NO merge to `main`
- ✗ NO `git pull` in `/home/rick/umbral-agent-stack/`
- ✗ NO modification of `/home/rick/umbral-agent-stack/`
- ✗ NO worker restart
- ✗ NO flag flip
- ✗ NO `copilot_cli.enabled` flip
- ✗ NO `_REAL_EXECUTION_IMPLEMENTED` flip
- ✗ NO egress activation
- ✗ NO `nft -f`
- ✗ NO Docker network creation
- ✗ NO Copilot HTTPS request
- ✗ NO PR opened via `gh` (not authenticated)
- ✗ NO PR comment / merge / approve
- ✗ NO Notion / gates / publish surface touched
- ✗ NO token printed

## 9. F6 step 6C-4 unblock conditions

To advance to step 6C-4 (operator-executed deploy), ALL of the
following must hold:

1. This document reviewed and approved by David.
2. Manual PR opened (web UI), reviewer-approved, and merged
   `--ff-only` to `main`.
3. Live worktree HEAD advances to the new `main` SHA via
   `git pull --ff-only`.
4. Single restart of `umbral-worker.service`.
5. Probe 1 returns `capability_disabled / policy_off` (NOT
   `Unknown task`).
6. Probes 2–5 confirm `copilot_cli.enabled=false`,
   `_REAL_EXECUTION_IMPLEMENTED=False`, `egress.activated=false`,
   no nft, no Docker network.
7. Test suite passes on the deployed tree (132/132).
8. Token remains untouched on disk and in process; no token in
   audit log.
9. CAND-003 untracked doc still present and unmodified.

## 10. F6 step 6C-4 recommendation (DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 6C-4: operator opens the PR (web UI),
> reviewer-merges to `main`, runs `git pull --ff-only` in
> `/home/rick/umbral-agent-stack/`, performs one
> `systemctl --user restart umbral-worker.service`, and runs
> probes 1–6 from §5.6. Agent only observes outputs and updates
> evidence docs. NO `copilot_cli.enabled` flip. NO
> `_REAL_EXECUTION_IMPLEMENTED` flip. NO Copilot HTTPS request.
> NO egress activation. NO Notion / gates / publish.
