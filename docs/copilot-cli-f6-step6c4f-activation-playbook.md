# F6 step 6C-4F — Manual activation playbook (DOCS ONLY, NOT EXECUTED)

> **STATUS: DOCUMENTED, NOT EXECUTED.** This playbook describes the
> exact sequence required to flip the Rick × GitHub Copilot CLI
> capability from its current "deployed but locked" state into a
> "real Copilot HTTPS execution" state. It is **NOT** an authorization
> to do so. Activation requires an explicit human decision per
> capability design F1 §3 and §9-D9.

---

## 1. Why this playbook exists

After F6 step 6C-4D, the capability is:

- **deployed live** — task `copilot_cli.run` is registered, the worker
  is running on `main` (currently `73ae88b`), and the token is loaded
  in the worker process env;
- **locked at multiple layers** — every real-execution path is gated
  off, and all the gates default to "off".

This document explains, in operational terms, what an authorised
operator would do — in what order, with what verification, and with
what rollback — to turn each gate. The point is **predictability**:
no surprise during activation, and a safe rollback at every step.

This is a runbook, not an approval. Approval is per-flag, per-phase,
and explicit. Each gate has its own decision (D9 in `docs/copilot-cli-capability-design.md`).

---

## 2. Current locked state

As of `main` HEAD `73ae88b` (PR #270 merged), the four execution gates are:

| Gate | Layer | File | Required value to enable | Current value |
|---|---|---|---|---|
| **G1 policy master switch** | repo config | `config/tool_policy.yaml :: copilot_cli.enabled` | `true` | `false` |
| **G2 execute toggle** | live envfile | `~/.config/openclaw/copilot-cli.env :: RICK_COPILOT_CLI_EXECUTE` | `true` | `false` |
| **G3 code constant** | repo source | `worker/tasks/copilot_cli.py :: _REAL_EXECUTION_IMPLEMENTED` | `True` | `False` |
| **G4 egress activation** | repo config | `config/tool_policy.yaml :: copilot_cli.egress.activated` | `true` | `false` |

A fifth env-layer gate (`RICK_COPILOT_CLI_ENABLED`) is already `true`
because step 6C-2 set it so the token would load into the worker process.
That gate by itself does NOT enable execution; it only enables
*consideration* of the task.

For **any real Copilot HTTPS call** to occur, **all four** of G1–G4
must be true *and* the live worktree must hold the code that
implements the real subprocess invocation, and the egress must have
been actually applied (nft rules + Docker network).

---

## 3. Pre-activation checklist (operator)

Before flipping anything, the operator must confirm:

- [ ] Live worker `/health` returns 200.
- [ ] `git -C /home/rick/umbral-agent-stack rev-parse HEAD` matches
      the latest `origin/main`.
- [ ] `~/.config/openclaw/copilot-cli-secrets.env` exists, mode `0600`,
      contains `COPILOT_GITHUB_TOKEN=github_pat_…` (fine-grained PAT v2
      with the `Copilot Requests` permission).
- [ ] `python scripts/verify_copilot_cli_env_contract.py --runtime
      ~/.config/openclaw/copilot-cli.env --secrets
      ~/.config/openclaw/copilot-cli-secrets.env --strict` exits 0.
- [ ] `python scripts/verify_copilot_egress_contract.py --strict`
      exits 0 (egress profile is internally consistent).
- [ ] CI on the activation branch is green.
- [ ] At least one human reviewer has approved the activation step
      *for this phase only* in writing (Linear issue or PR comment).

If any item fails, **STOP** and remediate before proceeding.

---

## 4. Activation order (canonical)

The order matters: it minimises the time during which the system is
"partially activated" with mismatched gates.

### Recommended canonical order

```
G3 (_REAL_EXECUTION_IMPLEMENTED) → in code, behind a PR + merge
G4 (copilot_cli.egress.activated)   → in repo config, same PR
G1 (copilot_cli.enabled)            → in repo config, same PR
G2 (RICK_COPILOT_CLI_EXECUTE)       → on live host, last and most reversible
```

Rationale:

* **G3 first** — flipping `_REAL_EXECUTION_IMPLEMENTED=True` is the only
  change that *requires real subprocess code to be merged*. It must
  happen via a code PR (the constant flips value at the same time as
  the implementation lands). Until that PR merges and the live worker
  pulls, even an accidental policy flip cannot run subprocess.

* **G4 next** — egress activation flips the network plane: the egress
  resolver writes nft rules and a Docker network. Must be in the same
  PR as G3, *and* must be verified by `verify_copilot_egress_contract`
  *and* exercised in dry-run on a staging worker before any flag flip.

* **G1 then** — flipping `copilot_cli.enabled` in `config/tool_policy.yaml`
  only changes whether the policy gate accepts the task. With G3 still
  False on a live worker that hasn't pulled, this is a no-op.

* **G2 last and on the live host only** — flipping
  `RICK_COPILOT_CLI_EXECUTE=true` in `~/.config/openclaw/copilot-cli.env`
  is the smallest, most reversible operation. It does not require a
  restart-with-pull; it only requires `systemctl --user restart
  umbral-worker.service` to pick up the new env. Inverse: flip back to
  `false`, restart. This is the **kill switch**.

### Why not "all at once"?

Because the failure mode of "all at once" is "everything is on, and
when something breaks we don't know which gate caused it". Per-gate
flip + per-gate verification means we can localise any failure.

---

## 5. Per-gate procedure

### Gate G3 — `_REAL_EXECUTION_IMPLEMENTED` (code constant)

#### Pre-requisites
- A separate PR exists that:
  1. implements the real subprocess invocation (Docker run with the
     egress network, the smoke wrapper, the seccomp profile, the
     read-only mount, the timeout enforcement);
  2. flips the constant to `True` in the same commit as the
     implementation;
  3. adds tests that prove subprocess is **not** invoked unless all
     of G1, G2, G3, G4 are simultaneously true.
- Reviewer approval recorded.
- CI green.

#### Procedure
```
# 1. Operator merges the implementation PR via GitHub UI.

# 2. On the live host:
cd /home/rick/umbral-agent-stack
git ls-remote origin refs/heads/main      # capture authoritative SHA
git fetch origin refs/heads/main:refs/remotes/origin/main
git status --short                        # editorial untracked OK
git pull --ff-only origin main
git rev-parse HEAD                        # must match the new main

# 3. Verify constant in the pulled code:
grep -E '^_REAL_EXECUTION_IMPLEMENTED' worker/tasks/copilot_cli.py
# Expected: _REAL_EXECUTION_IMPLEMENTED = True

# 4. Restart worker exactly once:
systemctl --user restart umbral-worker.service
sleep 2
systemctl --user show umbral-worker.service -p ActiveState -p MainPID

# 5. Probe — capability is NOT yet enabled at policy layer, so the
# response should still say "capability_disabled / policy_off":
TOKEN=$(tr '\0' '\n' < /proc/$(systemctl --user show umbral-worker.service -p MainPID --value)/environ | grep '^WORKER_TOKEN=' | cut -d= -f2-)
curl -s -X POST http://127.0.0.1:8088/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"task":"copilot_cli.run","input":{"mission":"research","prompt":"probe","repo_path":"/home/rick/umbral-agent-stack","dry_run":true,"max_wall_sec":60,"metadata":{}}}'
# Expected: result.error == "capability_disabled", reason == "policy_off"
```

#### Rollback for G3
```
# Revert the constant by reverting the merged PR or pulling a hotfix
# PR that flips _REAL_EXECUTION_IMPLEMENTED back to False.
# DO NOT manually edit the file in the live worktree —
# always go through PR + pull + restart.
git -C /home/rick/umbral-agent-stack pull --ff-only origin main
systemctl --user restart umbral-worker.service
```

### Gate G4 — `copilot_cli.egress.activated` (network plane)

#### Pre-requisites
- Resolver dry-run on the merged main produces a stable allow-list
  (`scripts/copilot_egress_resolver.py --dry-run` JSON deterministic).
- `infra/networking/copilot-egress.nft.example` reviewed by a network
  operator.
- Docker network `copilot-cli-egress` plan reviewed.
- The activation PR for G4 is merged (it flips
  `config/tool_policy.yaml :: copilot_cli.egress.activated: true`
  and the resolver wrapper begins applying the staged ruleset).

#### Procedure
```
# 1. After PR merge, pull on live host (G3 may already be active):
cd /home/rick/umbral-agent-stack
git pull --ff-only origin main

# 2. Apply the staged nft fragment (operator chooses scope; current
# staging is at ~/.config/openclaw/copilot-egress.nft, mode 0600,
# never auto-loaded):
sudo nft -c -f ~/.config/openclaw/copilot-egress.nft   # syntax check first
sudo nft       -f ~/.config/openclaw/copilot-egress.nft

# 3. Create the Docker network for egress isolation:
docker network create \
  --driver bridge \
  --subnet  10.42.0.0/30 \
  --gateway 10.42.0.1 \
  --opt 'com.docker.network.bridge.enable_icc=false' \
  copilot-cli-egress

# 4. Verify:
sudo nft list ruleset | grep -A20 'table inet copilot_cli'
docker network inspect copilot-cli-egress

# 5. Restart worker so it picks up the activation flag:
systemctl --user restart umbral-worker.service
```

#### Rollback for G4
```
# 1. Flip activated back to false via revert PR + pull.
# 2. Tear down the network plane:
sudo nft delete table inet copilot_cli
docker network rm copilot-cli-egress
# 3. Restart worker:
systemctl --user restart umbral-worker.service
```

### Gate G1 — `copilot_cli.enabled` (policy master switch)

#### Pre-requisites
- G3 and G4 activated and green for at least one human-confirmed
  observation period (operator's call; default 24 h).
- The G1 activation PR is merged. It flips the master switch to
  `true` and may include companion changes (per-mission rate limits,
  audit log retention).

#### Procedure
```
# 1. After PR merge:
cd /home/rick/umbral-agent-stack
git pull --ff-only origin main

# 2. Verify:
grep -E '^[[:space:]]*enabled:' config/tool_policy.yaml | head -3
# Expected: enabled: true under copilot_cli

# 3. Restart worker:
systemctl --user restart umbral-worker.service

# 4. Probe (G2 is still false, so we expect a different rejection):
curl -s -X POST http://127.0.0.1:8088/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"task":"copilot_cli.run","input":{"mission":"research","prompt":"probe","repo_path":"/home/rick/umbral-agent-stack","dry_run":true,"max_wall_sec":60,"metadata":{}}}'
# Expected: result.error == "execute_disabled" (or similar), reason
# referencing RICK_COPILOT_CLI_EXECUTE=false. would_run still false.
```

#### Rollback for G1
```
# Revert the master-switch PR + pull + restart.
# This restores the "deployed but locked" state.
git -C /home/rick/umbral-agent-stack pull --ff-only origin main
systemctl --user restart umbral-worker.service
```

### Gate G2 — `RICK_COPILOT_CLI_EXECUTE` (kill-switch)

#### Pre-requisites
- G1, G3, G4 all green and stable.
- Operator has a defined first task (mission, prompt, repo_path) to
  exercise the capability and confirm an end-to-end Copilot HTTPS
  call from a sandboxed Docker container.

#### Procedure
```
# 1. Edit ONE line in the live envfile:
sed -i.bak.6c4f -E \
  's/^RICK_COPILOT_CLI_EXECUTE=false$/RICK_COPILOT_CLI_EXECUTE=true/' \
  ~/.config/openclaw/copilot-cli.env

grep -E '^RICK_COPILOT_CLI_EXECUTE' ~/.config/openclaw/copilot-cli.env
# Expected: RICK_COPILOT_CLI_EXECUTE=true

# 2. Restart worker so it picks up the new env:
systemctl --user restart umbral-worker.service
sleep 2
systemctl --user show umbral-worker.service -p ActiveState -p MainPID

# 3. End-to-end probe with dry_run=false (or whatever the
# activation plan specifies):
curl -s -X POST http://127.0.0.1:8088/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '<canonical first-task payload>'
# Expected: result.ok == true, result.would_run == true, result
# contains audit_log path and Docker container ID.

# 4. Inspect audit log:
ls -t reports/copilot-cli/$(date +%Y-%m)/ | head -1
# Confirm: no token-shaped strings, decision recorded, exit code
# captured, wall time within max_wall_sec.
```

#### Rollback for G2 (kill-switch)
```
# This is the smallest, fastest rollback in the entire system.
sed -i.bak.kill -E \
  's/^RICK_COPILOT_CLI_EXECUTE=true$/RICK_COPILOT_CLI_EXECUTE=false/' \
  ~/.config/openclaw/copilot-cli.env
systemctl --user restart umbral-worker.service
# Capability is now back to "policy on, code on, egress on,
# execute off" — i.e., gated rejection at the execute layer.
```

---

## 6. Observability during activation

For each flip, capture and retain (do **not** commit; these contain
operational metadata):

* `systemctl --user show umbral-worker.service -p ActiveState -p
  MainPID -p ExecMainStartTimestamp` (before and after).
* `journalctl --user -u umbral-worker.service --since "5 min ago"`
  — copy stderr lines around the restart.
* `/health` HTTP response.
* Audit log entry for the post-flip probe (path returned by the
  worker; gitignored).

If the activation plan specifies metrics (latency, error rate),
record them per-flip.

---

## 7. Hard-stop conditions (abort and rollback)

Stop activation immediately and roll back the most-recently-flipped
gate if any of the following is observed:

* Worker `/health` returns non-200 after restart and does not recover
  within 30 s.
* Audit log records a token leak (any match for the redaction regex
  in raw form).
* Egress test traffic reaches an endpoint not on the allow-list (
  the resolver allow-list is the canonical reference).
* Docker container spawned by `copilot_cli.run` fails to start
  with a `seccomp` denial that was not observed in the F2.5 hardening
  smoke tests.
* PR diff between activation phase N and phase N+1 contains changes
  outside the explicitly listed gate file(s).

---

## 8. What this playbook does NOT do

- It does not flip any gate. Every command in §4 and §5 is
  description, not execution.
- It does not change the live worker state.
- It does not authorise activation. Authorisation is per-phase,
  per-flag, by an explicit human decision recorded in the
  capability design's §9 decision log.
- It does not unlock the seccomp profile, the read-only mount, the
  Docker network isolation, or any other F2/F2.5/F6 hardening.
- It does not cover Notion / publish / gate flows; those are
  separate scopes.

---

## 9. References

- `docs/copilot-cli-capability-design.md` — the master design log,
  including §9 decision history (D1–D27) and §11 phase status table.
- `docs/copilot-cli-f6-step6c4d-live-deploy-evidence.md` — the
  evidence of the deploy step that immediately precedes this
  playbook.
- `infra/networking/copilot-egress-resolver.md` — egress profile
  rationale.
- `scripts/verify_copilot_cli_env_contract.py` — envfile invariants.
- `scripts/verify_copilot_egress_contract.py` — egress invariants.
- `worker/tasks/copilot_cli.py` — handler with the `_REAL_EXECUTION_IMPLEMENTED`
  constant and gate logic.

---

## 10. State at time of writing

| Item | Value |
|---|---|
| `main` HEAD | `73ae88b` |
| Live worker HEAD | `73ae88b` |
| Live worker MainPID | `1124888` (since 6C-4D restart) |
| `/health` | 200 |
| `copilot_cli.enabled` | **false** |
| `_REAL_EXECUTION_IMPLEMENTED` | **False** |
| `copilot_cli.egress.activated` | **false** |
| `RICK_COPILOT_CLI_EXECUTE` | **false** |
| `RICK_COPILOT_CLI_ENABLED` | true (set in 6C-2 to load token) |
| Real Copilot HTTPS calls performed to date | **zero** |
