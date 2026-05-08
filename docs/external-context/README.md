# external-context

External knowledge bases and reference snapshots used by agents working on this repo.

These files are NOT runtime config and NOT live source of truth. They are point-in-time mirrors of upstream documentation, kept in-tree so any agent (Cursor, Codex, Claude, Antigravity, Copilot Chat) can grep them without network access.

## Inventory

| File | Source | Purpose | Refresh policy |
|---|---|---|---|
| `n8n-llms-full.txt` | `https://docs.n8n.io/llms-full.txt` | Full n8n docs single-file dump (~4.5 MB) for the `n8n-expert` agent skill | Manual — re-download when n8n features used here change |
| `openclaw-llms.txt` | `https://myclaw.ai/llms.txt` | OpenClaw / MyClaw public docs index (~3 KB). No `-full` variant published | Manual — re-download on rebrand or major feature change |
| `openclaw-known-issues.md` | internal | Issues observed in our VPS OpenClaw deployment | Update when a new issue is observed and stabilized |
| `adr-16-multichannel-rick-channels.md` | internal | ADR-16 reference | n/a |

## Refresh commands (PowerShell)

```powershell
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest 'https://docs.n8n.io/llms-full.txt' -OutFile 'docs/external-context/n8n-llms-full.txt' -UseBasicParsing
Invoke-WebRequest 'https://myclaw.ai/llms.txt'        -OutFile 'docs/external-context/openclaw-llms.txt'  -UseBasicParsing
```

## Wired skills (user-level)

The `n8n-expert` and `openclaw-expert` skills under `~/.cursor/skills/`, `~/.codex/skills/`, and `~/.claude/skills/` reference these files as their canonical knowledge source.
