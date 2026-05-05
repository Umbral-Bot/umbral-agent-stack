# Copilot CLI — F6 step 6C-4F Evidence: PR draft opened (operator action)

**Phase:** F6 step 6C-4F — operator opened the draft PR via the
GitHub web UI (Windows browser). Agent records the URL/number.
**No merge. No deploy. No worker restart. No flag flip. No `gh` API
call. DOCS-ONLY.**

**Branch:** `rick/copilot-cli-f6-step6c4f-activation-playbook`
**HEAD at time of evidence:** `4c5f148`

---

## 1. PR coordinates (reported by operator)

| Field | Value |
|---|---|
| URL | https://github.com/Umbral-Bot/umbral-agent-stack/pull/271 |
| Number | **#271** |
| Title | `[Draft][F6 step 6C-4F] Rick × Copilot CLI — manual activation playbook (DOCS ONLY)` |
| Base | `main` (`73ae88b`) |
| Head | `rick/copilot-cli-f6-step6c4f-activation-playbook` (`4c5f148`) |
| Draft | yes |
| Opened by | operator (web UI, Windows browser) |
| `gh` used by agent | NO (`gh auth status` → not logged in; preserved by design) |
| Body source | `~/.copilot/session-state/c309f537-b132-4112-815b-2f6a4c92a474/files/PR_BODY_F6_step6c4f.md` |

The agent did NOT call the GitHub API for this PR; the URL/number
came from the operator and was not independently verified by the agent.

## 2. State invariants — verified live at time of evidence commit

```
$ git -C /home/rick/umbral-agent-stack-activation-playbook branch --show-current
rick/copilot-cli-f6-step6c4f-activation-playbook

$ git -C /home/rick/umbral-agent-stack-activation-playbook rev-parse HEAD
4c5f148091945b12d4fd2b0a3441401a5e7370c5

$ git -C /home/rick/umbral-agent-stack rev-parse HEAD
73ae88ba5cff55ff7c8f401fcaeb5841d784a038

$ git -C /home/rick/umbral-agent-stack branch --show-current
main

$ systemctl --user show umbral-worker.service -p MainPID -p ActiveState -p SubState
MainPID=1124888
ActiveState=active
SubState=running

$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8088/health
HTTP 200
```

| Check | Value |
|---|---|
| Feature branch HEAD | `4c5f148` (unchanged since push) |
| Live worktree HEAD | `73ae88b` (main, PR #270 merge) |
| Live worker MainPID | `1124888` (unchanged since F6 step 6C-4D restart) |
| Live worker ActiveState | active |
| Live worker /health | 200 |
| `RICK_COPILOT_CLI_ENABLED` | true (since 6C-2; env-layer gate only) |
| `RICK_COPILOT_CLI_EXECUTE` | **false** |
| `copilot_cli.enabled` | **false** |
| `_REAL_EXECUTION_IMPLEMENTED` | **False** |
| `copilot_cli.egress.activated` | **false** |
| nft rules applied | NO |
| Docker network created | NO |
| Token printed | NO |
| Token committed | NO |
| Merge done | NO |
| Deploy done | NO |
| Worker restarted | NO |
| Flags changed | NO |
| Notion / gates / publish touched | NO |
| Real Copilot HTTPS calls to date | **zero** |

## 3. PR contents (docs-only)

PR #271 contains exactly:
- `docs/copilot-cli-f6-step6c4f-activation-playbook.md` (new, 405 lines)
- `docs/copilot-cli-capability-design.md` (+D28 + §11 rows for F6.step6C-4E
  and F6.step6C-4F)

No code changes. No config changes. No flag flips. No test changes.
No edits outside `docs/`.

Diff validation at commit time:
- `git diff --check` — clean
- secret scan (regex for `ghp_`, `ghs_`, `github_pat_`, `sk-`) — 0 hits

## 4. Next step: human review → merge

PR #271 is a docs-only draft. To advance:

1. Reviewer marks the PR **Ready for review** when desired.
2. Reviewer confirms:
   - No code or config changed.
   - No flag flipped in `config/tool_policy.yaml` or envfiles.
   - `_REAL_EXECUTION_IMPLEMENTED` still `False` on `main` post-merge.
   - 0 token-shaped literals in diff.
   - §11 row says "doc-only" for F6.step6C-4F.
3. Reviewer merges to `main`.
4. After merge: live worktree pull is optional (docs-only, no restart
   required). If pulled: `git pull --ff-only origin main` only;
   do NOT restart `umbral-worker.service`.

**Activation is NOT authorised by merging this PR.** Merging only
syncs the runbook doc to `main`. Activation requires separate,
explicit, per-flag human decisions per `docs/copilot-cli-capability-design.md`
§9 / D9.
