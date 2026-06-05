---
name: tournament-github-cli
description: >-
  GitHub CLI workflow for OpenClaw-native tournament lane agents only.
  Use when you are a tournament participant (subagent lane): create branch
  tournament/<id>/lane-<specialty>, commit explicit files, push, open PR
  with mandatory title prefix, verify PR, announce PR_URL to parent.
  Do NOT use for daily rick/ branches (github-ops) or ideational tournaments
  (skill tournament). Prefer umbral_tournament_* plugin tools when available;
  raw gh is fallback only.
metadata:
  openclaw:
    emoji: "🏎️"
    requires:
      env:
        - GITHUB_TOKEN
---

# Tournament GitHub CLI (lane participant)

You are a **lane** in an OpenClaw-native tournament (`docs/79`). Your job ends when the parent has a **verified PR URL**, not when code "looks done".

## Hard rules

1. **Branch only:** `tournament/<tournament_id>/lane-<specialty>` from updated `main`.
2. **Never** merge your own PR. **Never** push to `main`.
3. **Never** `git add -A` — stage an explicit file list only.
4. **PR title:** `[tournament:<tournament_id>:<specialty>] <issue_title>`
5. **Last line of announce to parent (literal):** `PR_URL=https://github.com/Umbral-Bot/umbral-agent-stack/pull/<n>`
6. **Do not** use `umbral_github_*` or `github.create_branch` with `rick/` prefix — wrong contract.

## Tool priority

| Step | Preferred (D3.6 plugin) | Fallback (coding shell) |
|------|-------------------------|-------------------------|
| Preflight | `umbral_tournament_preflight` | `gh auth status`; `git status`; `git fetch origin main` |
| Branch | `umbral_tournament_create_lane_branch` | `git checkout -b tournament/...` |
| Commit+push | `umbral_tournament_commit_and_push` | `git add <files>`; `git commit`; `git push -u origin HEAD` |
| Open PR | `umbral_tournament_open_pr` | `gh pr create --title "..." --body-file ...` |
| Verify | `umbral_tournament_verify_pr` | `gh pr view <url> --json url,headRefName,title,mergeable,statusCheckRollup` |

If plugin tools are missing, complete the fallback but report `TOOLING_DEGRADED` in announce.

## Procedure (ordered)

### 1. Confirm inputs from parent task

- `tournament_id`, `specialty`, `issue_url`, `issue_title`, `repo_path` (default `~/umbral-agent-stack`).

### 2. Preflight

```bash
cd <repo_path>
git fetch origin main
git checkout main
git pull --ff-only origin main
git status --porcelain   # must be empty
gh auth status
```

Abort with exact error if not clean or gh not authenticated.

### 3. Create and checkout lane branch

```bash
git checkout -b tournament/<tournament_id>/lane-<specialty>
```

### 4. Implement issue scope

- Touch only files required by the issue.
- Run tests the issue implies (e.g. `pytest` paths from task).

### 5. Commit and push (explicit files)

```bash
git add path/to/file1 path/to/file2
git commit -m "tournament(<specialty>): <short description>"
git push -u origin HEAD
```

### 6. Open PR

```bash
gh pr create \
  --repo Umbral-Bot/umbral-agent-stack \
  --base main \
  --head "tournament/<tournament_id>/lane-<specialty>" \
  --title "[tournament:<tournament_id>:<specialty>] <issue_title>" \
  --body-file /tmp/pr-body.md
```

PR body must include: issue link, specialty focus, test command run, checklist “I did not merge”.

### 7. Verify before announce

```bash
gh pr view <url> --json url,headRefName,title,mergeable,statusCheckRollup,additions,deletions
```

Confirm `headRefName` matches lane branch and title contains `[tournament:<tournament_id>:<specialty>]`.

### 8. Announce-back JSON + PR_URL line

```json
{
  "specialty": "<specialty>",
  "pr_url": "https://github.com/Umbral-Bot/umbral-agent-stack/pull/N",
  "head_ref": "tournament/<tournament_id>/lane-<specialty>",
  "diff_stats": "+X -Y",
  "checks_status": "pending|success|failure",
  "tooling": "plugin|shell_degraded"
}
```

Final line alone on last line:

```text
PR_URL=https://github.com/Umbral-Bot/umbral-agent-stack/pull/N
```

## Failure reporting

If blocked, announce: `LANE_BLOCKED: <reason>` (auth, dirty tree, push rejected, gh error). Do not claim success without `PR_URL`.

## References

- Roadmap plugin: `docs/ops/d36-tournament-github-cli-plugin-roadmap-2026-06-04.md`
- Protocol: `docs/79-tournament-protocol-openclaw-native.md` §3–§4
- Parent skill: `multi-agent-tournament-orchestrator`
