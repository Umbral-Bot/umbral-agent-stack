---
id: 2026-05-08-O7a-pat-issues-write-scope
title: O7a — extend Copilot-VPS PAT with issues:write for tournament wrapper
status: open
verdict: pending
owner: david
reviewer: copilot-chat
phase: O7-followup
depends_on:
  - o7-smoke-tournament-as-rick-2026-05-08 (PR #378, merged)
created: 2026-05-08
priority: medium
---

# O7a — PAT scope upgrade: issues:write

## Why

During the O7 smoke (PR #378), Copilot-VPS could not post the tournament
contract JSON as a comment on Mission Control issue #375 because its PAT
lacks `issues:write`. The contract was inlined into the report as
workaround.

For the **real** tournament wrapper (`multi-agent-tournament-orchestrator`)
to post the contract on Mission Control per protocol §6, the PAT must be
extended.

## Action (David)

1. GitHub → Settings → Developer settings → Personal access tokens (or
   fine-grained tokens) → locate the Copilot-VPS PAT.
2. Add scope `issues:write` (classic) **or** under the fine-grained token
   add repository permission "Issues" → Read and write.
3. Limit to the repos the wrapper actually needs: `Umbral-Bot/umbral-agent-stack`,
   `Umbral-Bot/notion-governance` if applicable.
4. Update the secret on the VPS:
   ```bash
   ssh rick@<vps>
   # Locate where the PAT is stored (likely ~/.config/openclaw/env or similar)
   grep -lE "GITHUB_TOKEN|GH_TOKEN" ~/.config/openclaw/ 2>/dev/null
   # Update the value (DO NOT echo the token)
   ```
5. Smoke-verify after rotation:
   ```bash
   ssh rick@<vps> "GH_TOKEN=<new> gh api repos/Umbral-Bot/umbral-agent-stack/issues/375/comments --method POST -f body='O7a smoke: PAT scope verification. Safe to delete.' -q '.id'"
   # Then delete the smoke comment by id
   ```

## Acceptance

- [ ] PAT scope updated.
- [ ] VPS secret rotated (no token in this task or any output).
- [ ] Smoke comment posted + deleted on issue #375.
- [ ] Update this task: `status: done`, `verdict: verde`.

## Hard constraints

- `secret-output-guard`: never echo the PAT, do not paste it into PRs,
  reports, or this task file.
- Old PAT must be revoked or have its `issues:write` scope removed if a
  new token is minted (avoid two live tokens).

## Notes

This unblocks the wrapper task (real `multi-agent-tournament-orchestrator`
build). Without this, the wrapper would have to inline the contract into
the report just like the smoke did.
