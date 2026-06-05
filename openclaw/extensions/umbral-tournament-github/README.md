# umbral-tournament-github (scaffold)

OpenClaw plugin for **tournament lane** GitHub operations. Implements roadmap **D3.6**.

## Status

| Component | State |
|-----------|--------|
| `openclaw.plugin.json` | ✅ Manifest |
| `index.ts` | ⏳ Pending — mirror `umbral-worker` after Worker tasks exist |
| Worker `tournament_lane.*` | ⏳ Pending — see `docs/ops/d36-tournament-github-cli-plugin-roadmap-2026-06-04.md` |
| VPS `plugins.load.paths` | ⏳ Do not enable until `index.ts` ships |

## Planned tools

- `umbral_tournament_preflight`
- `umbral_tournament_create_lane_branch`
- `umbral_tournament_commit_and_push`
- `umbral_tournament_open_pr`
- `umbral_tournament_verify_pr`

## Enable (post-implementation)

1. Merge Worker + plugin PR.
2. Add to `~/.openclaw/openclaw.json`:

```json5
"plugins": {
  "load": { "paths": ["~/umbral-agent-stack/openclaw/extensions/umbral-tournament-github"] },
  "entries": {
    "umbral-tournament-github": {
      "enabled": true,
      "config": {
        "baseUrl": "http://127.0.0.1:8088",
        "tokenFile": "/home/rick/.config/openclaw/worker-token",
        "defaultRepoPath": "/home/rick/umbral-agent-stack"
      }
    }
  }
}
```

3. Allowlist `umbral_tournament_*` on lane agents (`rick-delivery`, `rick-ops`, …).
4. `rsync` skill `tournament-github-cli` to VPS workspace skills.
5. Restart gateway; run tournament preflight dry-run.

## Skill for agents

Use repo template: `openclaw/workspace-templates/skills/tournament-github-cli/SKILL.md`
