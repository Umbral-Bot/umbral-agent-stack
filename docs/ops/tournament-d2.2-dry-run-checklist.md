# Tournament D2.2 — dry-run checklist (Mega 1)

- **Status:** Active
- **Date:** 2026-06-01
- **Closes:** spine D2.2 — pre-flight without real `sessions_spawn`
- **Related:** `docs/79-tournament-protocol-openclaw-native.md` §7, skill `multi-agent-tournament-orchestrator`

---

## Purpose

Validate tournament readiness on VPS **before** the first smoke with real lane spawns. No PRs, no merge, no `sessions_spawn` in the automated script path.

---

## Prerequisites

- G-D1a + G-D1a-RESTART done (`maxSpawnDepth=2` effective).
- G-D1b decided: launch from `main` standalone.
- Repo synced: `git pull --ff-only origin main` on VPS.
- Skill synced to OpenClaw workspace (handoff after Cursor push).

---

## Step 1 — Script dry-run (VPS)

```bash
cd ~/umbral-agent-stack
git pull --ff-only origin main
# Usar bash (no chmod) para evitar dirty worktree si core.filemode=true
bash scripts/openclaw/tournament-preflight-dry-run.sh \
  openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/smoke-tournament-spec.yaml
```

**Pass:** exit 0, no `FAIL` lines. **G-D1b** remains manual (WARN expected).

---

## Step 2 — Manual G-D1b probe (`main` session)

In OpenClaw Control UI (or CLI new session), agent **`main`**:

1. Confirm tool list includes `sessions_spawn`.
2. Confirm session is **not** nested under `rick-orchestrator`.
3. Optional: `agents_list` / `subagents` visible (standalone signature per ISSUE-001).

**Fail:** if only nested path available → do not proceed to smoke.

---

## Step 3 — Skill visibility

```bash
# After workspace sync — exact command depends on OpenClaw version
openclaw skills list 2>/dev/null | grep -i multi-agent-tournament || true
```

Skill `multi-agent-tournament-orchestrator` must appear for `main`.

---

## Step 4 — Spec review (no spawn)

1. Open `examples/smoke-tournament-spec.yaml`.
2. Replace `issue_url` / `issue_id` with David-approved trivial typo issue.
3. Verify 2 lanes, distinct specialties, branch naming convention.

---

## Step 5 — Gate before smoke (D3.0)

| Gate | Required |
|---|---|
| D2.2 dry-run script pass | Yes |
| G-D1b manual pass | Yes |
| G-D1c Azure stable | Recommended (see Mega 2 cross-ref) |
| David approves smoke issue | Yes |
| David present for merge step | Yes |

---

## Step 6 — Smoke (separate task — not D2.2)

When all above pass, run full tournament per `docs/79` §7 using the smoke spec. That is **D3.0 / first smoke**, not this dry-run.

---

## Evidence

Store under `~/.coord-ag-evidence/D2.2/` on VPS:

- `dry-run.log` (script output)
- `gd1b-tool-list.txt` (screenshot or paste of main session tools)
- commit SHA of `umbral-agent-stack` used

---

## References

- `.agents/tasks/2026-06-01-003-d2.1-multi-agent-tournament-orchestrator-skill.md`
- `docs/architecture/tournament-protocol.md`
