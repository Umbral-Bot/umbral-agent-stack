---
name: umbral-tournament-github
description: >-
  OpenClaw plugin bridge for tournament lane GitHub tools (Worker
  tournament_lane.*). Use only inside tournament lanes; pair with skill
  tournament-github-cli. Not enabled until D3.6 Phase 3 deploy.
metadata:
  openclaw:
    requires:
      env:
        - GITHUB_TOKEN
---

# Umbral Tournament GitHub (plugin skill)

When this plugin is **enabled** on the gateway, prefer these tools over raw shell `gh`:

| Tool | Worker task |
|------|-------------|
| `umbral_tournament_preflight` | `tournament_lane.preflight` |
| `umbral_tournament_create_lane_branch` | `tournament_lane.create_branch` |
| `umbral_tournament_commit_and_push` | `tournament_lane.commit_and_push` |
| `umbral_tournament_open_pr` | `tournament_lane.open_pr` |
| `umbral_tournament_verify_pr` | `tournament_lane.verify_pr` |

If this plugin is not enabled in the active gateway profile yet, follow
**`tournament-github-cli`** shell fallback and report `TOOLING_DEGRADED`.

See: `docs/ops/d36-tournament-github-cli-plugin-roadmap-2026-06-04.md`
