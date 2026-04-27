# Copilot CLI — F6 Step 6C-4A Evidence: PR materials prepared (PR open pending operator)

**Phase:** F6 step 6C-4A — prepare and stage everything needed to
open the draft PR for the F6 capability. **No PR opened by the
agent. No merge. No deploy. No worker restart. No flag flip.**

**Branch:** `rick/copilot-cli-capability-design`
**HEAD before this evidence:** `8c6a071`

---

## 1. Why the PR is not opened by the agent

`gh` is not authenticated on the VPS, by design (avoids storing a
GitHub PAT in shell history / `~/.config/gh/`). PR creation
therefore requires the operator to use the GitHub web UI from a
trusted machine.

```
$ gh auth status
You are not logged into any GitHub hosts. To log in, run: gh auth login
```

Opening the PR is a one-click operator action. This step makes that
action mechanical: the body is pre-written and committed alongside
the code so the operator only has to paste it.

## 2. What is staged in this commit

- `docs/pr-bodies/F6-rick-copilot-cli-capability.md` — the
  copy/paste PR body, including phase summary, diff scope, reviewer
  checklist, "what this PR does NOT do", post-merge plan, rollback,
  and a documentation index.
- This evidence doc.
- Design-doc D24 + §11 update marking 6C-4A done.

## 3. Operator action (one-shot, web UI)

1. Open compare URL:
   https://github.com/Umbral-Bot/umbral-agent-stack/compare/main...rick/copilot-cli-capability-design?expand=1
2. Title:
   `[Draft][F1-F6] Rick × Copilot CLI capability — gated, staged, no execution`
3. Body: copy from
   `docs/pr-bodies/F6-rick-copilot-cli-capability.md` (this branch,
   or the same file once `main` has it).
4. **Mark as Draft.**
5. "Create draft pull request".
6. Append the PR URL + number to this doc and commit a one-line
   addendum (next step, 6C-4B).

## 4. Pre-flight verification (captured)

```
$ git -C /home/rick/umbral-agent-stack-copilot-cli rev-parse HEAD
8c6a071715b8139f1a3a46fb79dc2a9676c47b01

$ git -C /home/rick/umbral-agent-stack-copilot-cli ls-remote origin \
    rick/copilot-cli-capability-design
8c6a071715b8139f1a3a46fb79dc2a9676c47b01  refs/heads/rick/copilot-cli-capability-design

$ git -C /home/rick/umbral-agent-stack-copilot-cli merge-base HEAD origin/main
e6128bc5fc2fa848c6a1e8255ff597c22436d4e8
$ git -C /home/rick/umbral-agent-stack-copilot-cli rev-parse origin/main
e6128bc5fc2fa848c6a1e8255ff597c22436d4e8
```

Branch is on origin at the expected SHA. Merge-base equals
`origin/main` HEAD → strict fast-forward, no conflicts (already
proven in F6 step 6C-3 §3 via `git merge-tree`).

## 5. State invariants — unchanged

| Check | Value |
|---|---|
| Live worktree HEAD | `e6128bc` (unchanged) |
| Live worker `MainPID` | 1114334 (unchanged since F6 step 6C-2) |
| `RICK_COPILOT_CLI_ENABLED` | true (unchanged since 6C-2) |
| `RICK_COPILOT_CLI_EXECUTE` | false |
| `copilot_cli.enabled` | false |
| `_REAL_EXECUTION_IMPLEMENTED` | False |
| `copilot_cli.egress.activated` | false |
| nft applied | NO |
| Docker network | NO |
| Token printed | NO |
| Token committed | NO (secret scan on diff for this commit: clean) |
| PR opened by agent | **NO** (operator action, web UI) |
| Merge done | NO |
| Deploy done | NO |
| Notion / gates / publish touched | NO |

## 6. F6 step 6C-4B unblock conditions

The next step is purely operator + reviewer:

1. Operator opens the draft PR per §3.
2. Operator pastes the URL/number back to the agent.
3. Agent appends a one-line addendum to this evidence doc capturing
   the URL and immediately stops.
4. Human reviewer (David) reviews the diff against the checklist in
   the PR body.
5. Reviewer approves.
6. Reviewer merges with `--ff-only` (or "Create a merge commit",
   not squash, to preserve per-step history).
7. Only AFTER merge does F6 step 6C-4C (deploy) become eligible.

## 7. F6 step 6C-4B recommendation (operator action only)

> Operator: open the draft PR via the URL in §3. Reply to the agent
> with the PR number/URL only. Do NOT mark the PR ready for review
> until §6 steps 4–5 are done. Do NOT merge until the reviewer
> checklist in the PR body is satisfied. Agent will then commit a
> one-line addendum and stop.
