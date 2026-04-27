# Copilot CLI — F6 Step 6C-4B Evidence: PR draft opened (operator action)

**Phase:** F6 step 6C-4B — operator opened the draft PR via the
GitHub web UI. Agent records the URL/number. **No merge. No deploy.
No worker restart. No flag flip. No `gh` API call.**

**Branch:** `rick/copilot-cli-capability-design`
**HEAD before this evidence:** `9884600`

---

## 1. PR coordinates (reported by operator)

| Field | Value |
|---|---|
| URL | https://github.com/Umbral-Bot/umbral-agent-stack/pull/269 |
| Number | **#269** |
| Title | `[Draft][F1-F6] Rick × Copilot CLI capability — gated, staged, no execution` |
| Base | `main` |
| Head | `rick/copilot-cli-capability-design` |
| Draft | yes |
| Opened by | operator (web UI) |
| `gh` used by agent | NO (`gh auth status` → not logged in; preserved by design) |
| Body source | `docs/pr-bodies/F6-rick-copilot-cli-capability.md` (committed in 6C-4A) |

The agent did NOT call the GitHub API for this PR; the URL/number
came from the operator and was not independently verified by the
agent.

## 2. State invariants — unchanged since F6 step 6C-2

```
$ git -C /home/rick/umbral-agent-stack-copilot-cli rev-parse HEAD
98846009f3df994919cabad31534d7fa7176d958

$ git -C /home/rick/umbral-agent-stack rev-parse HEAD
e6128bc5fc2fa848c6a1e8255ff597c22436d4e8

$ systemctl --user show umbral-worker.service -p MainPID --value
1114334

$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8088/health
HTTP 200
```

| Check | Value |
|---|---|
| Live worktree HEAD | `e6128bc` (unchanged) |
| Live worker MainPID | 1114334 (unchanged since F6 step 6C-2) |
| Live worker /health | 200 |
| `RICK_COPILOT_CLI_ENABLED` | true (since 6C-2; only flipped flag) |
| `RICK_COPILOT_CLI_EXECUTE` | false |
| `copilot_cli.enabled` | false |
| `_REAL_EXECUTION_IMPLEMENTED` | False |
| `copilot_cli.egress.activated` | false |
| nft applied | NO |
| Docker network | NO |
| Token printed | NO |
| Token committed | NO |
| Merge done | NO |
| Deploy done | NO |
| Notion / gates / publish touched | NO |

## 3. F6 step 6C-4C unblock conditions (review + merge)

PR #269 is now open as draft. To advance:

1. Reviewer (David) marks the PR ready for review when desired.
2. Reviewer walks the 8-item checklist embedded in the PR body
   (`docs/pr-bodies/F6-rick-copilot-cli-capability.md`):
   - `copilot_cli.enabled: false`
   - `_REAL_EXECUTION_IMPLEMENTED = False`
   - `copilot_cli.egress.activated: false`
   - both `RICK_COPILOT_CLI_*=false` defaults in `.env.example`
   - no token in diff (regex scan)
   - no edits to other agents' tasks
   - `worker/tool_policy.py` change preserves existing behaviour
   - CI green
3. Reviewer approves.
4. Reviewer merges with `--ff-only` (or "Create a merge commit",
   not squash; see F6 step 6C-3 §4.1 for the rationale).
5. Only AFTER merge does F6 step 6C-4D (live deploy via
   `git pull --ff-only` + 1 restart + probes 1–6) become eligible.

## 4. F6 step 6C-4C recommendation (human reviewer action)

> Reviewer: walk the 8-item checklist embedded in the PR #269 body
> against the diff. If satisfied, merge `--ff-only` to `main`. Do
> NOT flip any flag in this merge. Do NOT modify
> `_REAL_EXECUTION_IMPLEMENTED`. After merge, ping the agent so
> F6 step 6C-4D (operator-executed deploy) can proceed under
> explicit approval.
