---
id: 2026-05-08-O7c-gh-auth-status-leak-pattern
title: O7c — document gh auth status PAT-prefix leak pattern in secret-output-guard
status: open
verdict: pending
owner: copilot-chat
reviewer: david
phase: O7-followup
depends_on:
  - o7-smoke-tournament-as-rick-2026-05-08 (PR #378, merged)
created: 2026-05-08
priority: low
---

# O7c — `gh auth status` partial token leak

## Why

During O7 smoke, `gh auth status` emitted a partially-masked PAT prefix
(e.g. `Token: gho_abcd******`) into the terminal. Even partial leakage:

- ends up in agent logs and conversation transcripts,
- can be enough to cross-reference a token in audit log breaches,
- violates the spirit of `secret-output-guard` even if `gh` is technically
  upstream behavior.

The recommended mitigation is a one-liner pipe:

```bash
gh auth status 2>&1 | grep -v "^  - Token:"
```

This needs to be a documented pattern, not tribal knowledge.

## Action

Update `secret-output-guard` skill (canonical: user-level
`~/.copilot/skills/secret-output-guard/SKILL.md` and
`~/.codex/skills/secret-output-guard/SKILL.md`; mirrors:
`notion-governance/.agents/skills/secret-output-guard/SKILL.md` and
`umbral-agent-stack/.agents/skills/secret-output-guard/SKILL.md`):

1. Add a new section **"Tool-emitted partial leaks"** with at minimum:
   - `gh auth status` → pipe through `grep -v "^  - Token:"`.
   - `git config --list` (when GitHub creds are baked into URLs) → use
     `git config --list | grep -v "url\.\|extraheader"`.
   - Any future entries observed.
2. Reference this task as the originating incident.
3. Add a one-line note in the AF-1k.16i1c incident memory pointing here.

## Acceptance

- [ ] Skill updated in canonical location (user-level).
- [ ] Mirrors synced in both repos.
- [ ] Memory note added.
- [ ] Update this task: `status: done`, `verdict: verde`.

## Hard constraints

- `secret-output-guard` itself: do NOT include any real token (even masked)
  as an example. Use placeholders like `gho_<REDACTED>`.

## Notes

Low priority but high signal-to-effort ratio. Single-PR change to the
canonical skill.
