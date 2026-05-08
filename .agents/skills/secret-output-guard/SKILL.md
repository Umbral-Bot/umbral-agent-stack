---
name: secret-output-guard
description: Repo-level pointer to the cross-repo behavioural guardrail that prevents tokens, secrets, and API keys from leaking into agent outputs. Apply before commits, retros, mailbox messages, PR bodies, reports, or any visible output. Motivated by incident AF-1k.16i1c (gate-token leak, 2026-04-26).
---

# Skill: secret-output-guard (stub — pointer)

> **Canonical source:** this skill lives at the **user level**, not in the repo.
>
> - Copilot Chat / VS Code: `~/.copilot/skills/secret-output-guard/SKILL.md`
> - Codex CLI: `~/.codex/skills/secret-output-guard/SKILL.md`
> - Notion-governance mirror: [`notion-governance/.agents/skills/secret-output-guard/SKILL.md`](https://github.com/Umbral-Bot/notion-governance/blob/main/.agents/skills/secret-output-guard/SKILL.md)
>
> This file exists only so that the skill is discoverable by agents that scan repo-level skill mirrors (Copilot-VPS, Claude Code, Codex working inside this repo). **Do not edit this stub** — modify the canonical user-level source and the threads pick it up automatically.

## Why it is user-level (not repo-level)

It is a **cross-repo, cross-IDE behavioural guardrail**. The triggering incident (gate-token leak AF-1k.16i1c) happened in `umbral-bot-copilot`, not here. Tying the rule to a single repo would mean threads working in other repos would not load it.

## Apply before

- `git commit` of any file the agent generated (especially reports, retros, audit docs, mailbox messages).
- Posting a Friday retro (skill `q-friday-retro` quality gate invokes this).
- Writing a `.agents/mailbox/` message (mailbox README rule 5 invokes this).
- Generating a PR body, GitHub Issue body, Linear comment, or Notion update.
- Streaming any payload back to the user that includes raw stdout/stderr from worker tasks, CLI runs, or HTTP responses.

## Minimum checklist (full version in the canonical source)

1. Scan output for these patterns and redact before emitting:
   - `gh[oprsu]_[A-Za-z0-9]{36,}` (GitHub PATs)
   - `sk-[A-Za-z0-9]{20,}` and `sk-ant-[A-Za-z0-9-]+` (OpenAI / Anthropic)
   - `ghs_[A-Za-z0-9]{36,}` (gate tokens — root cause of AF-1k.16i1c)
   - `xoxb-`, `xoxp-`, `xoxa-` (Slack)
   - `eyJhbGciOi[A-Za-z0-9_=-]+\.` (JWTs — likely Supabase service-role / Auth)
   - `AKIA[0-9A-Z]{16}` (AWS access keys), `(?i)aws_secret_access_key\s*[:=]`
   - `(?i)(notion|mp_|mercadopago|azure|foundry|hostinger).{0,20}(token|key|secret)\s*[:=]\s*["']?[A-Za-z0-9_\-./]{20,}`
2. Replace any hit with `<REDACTED:<kind>>` and append `note: redacted N secret(s) per secret-output-guard`.
3. If the secret was about to be committed, refuse the commit, surface the path + line, and ask the user how to proceed (rotate vs ignore-list).
4. For Copilot-VPS specifically: never `cat ~/.config/openclaw/*.env` or `~/.config/umbral/*.env` into the chat transcript. Use `grep -c '^[A-Z_]*=' <file>` or hashed previews instead.

## Cross-references

- Tournament protocol: [`docs/79-tournament-protocol-openclaw-native.md`](../../docs/79-tournament-protocol-openclaw-native.md) §7 smoke test gate.
- Q2 plan: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` §6 (secrets risk in transcripts) + §8.3 (audit tooling).
- Mailbox protocol: [`.agents/PROTOCOL.md`](../../PROTOCOL.md).
