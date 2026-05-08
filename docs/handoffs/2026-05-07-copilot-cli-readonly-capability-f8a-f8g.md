# Copilot CLI read-only capability — handoff F8A → F8G

**Date**: 2026-05-07
**Status**: capability **stable** for read-only research; write-limited missions **gated until hardening lands**.
**Owners**: Codex/Cursor/Copilot-VPS coordination layer. Copilot Chat treats this as analysis/reasoning gear, not autonomous deploy/write agent.

## TL;DR

GitHub Copilot CLI is now a **proven READ-ONLY capability** through `copilot_cli.run`. The end-to-end path (token → scoped Docker bridge → nft-pinned egress → sandboxed container → audit JSONL → secret-scan → rollback) is operational and exercised under approval `APPROVE_F8E_PROGRESSIVE_COPILOT_CAPABILITY_LADDER=YES`. Use it for repo comprehension, risk review, implementation plans, and cited architecture analysis. Do **not** use it as an autonomous deploy/write agent.

## Reports anchoring this handoff

All under `reports/copilot-cli/`:

- `f8a-first-real-run-2026-05-05.md`
- `f8a-retry-after-no-banner-fix-2026-05-06.md`
- `f8a-retry-after-docker-stdin-fix-2026-05-06.md`
- `f8a-retry-after-prompt-quoting-fix-2026-05-06.md`
- `f8a-egress-scope-staging-2026-05-07.md`
- `f8a-run6-after-token-refresh-2026-05-07.md`
- `f8b-diagnose-egress-and-model-power-2026-05-07.md`
- `f8c-retry-after-github-meta-egress-fix-2026-05-07.md`
- `f8d-default-model-egress-proof-2026-05-07.md`
- `f8e-progressive-copilot-capability-ladder-2026-05-07.md` ← **canonical capability proof**

## The 7 rules (always apply)

1. **GitHub Copilot CLI is a READ-ONLY capability** through `copilot_cli.run`, not a general write agent.
2. **Safe path**:
   - `mission=research`
   - `requested_operations=["read_repo","summarize","explain","cite_files"]`
   - `repo_path=/home/rick/umbral-agent-stack` (or other read-only target)
   - no file writes, no shell exec, no git/gh mutations, no Notion writes
3. **Egress only safe** through scoped `copilot-egress` Docker bridge and nft table populated by:
   `scripts/copilot_egress_resolver.py --include-github-meta`
4. **Token handling strict**: never print or request the token value. Only use `COPILOT_GITHUB_TOKEN=present_by_name`, length, and short fingerprint if rotation evidence is needed.
5. **Canonical model policy**: `gpt-5.5` with `--reasoning-effort high` once PR #337 merges. `GPT-5.5` is the human display alias; CLI slug is `gpt-5.5`.
6. **Opus 4.6/4.7 unavailable** for the current token/account in F8E (`opus_available=false`). Do not route production work to Opus unless a fresh availability probe proves otherwise.
7. **Write-limited missions intentionally blocked** until hardening lands: DNS pinning, kernel-level exec restrictions, write overlay/diff capture, human approval materialization.

## Operating envelope

### What the capability is for

- Repo comprehension at speed (citations included).
- Risk reviews of proposed changes.
- Implementation plans grounded in existing code.
- Architecture analysis with file:line evidence.
- Audits over installed third-party trees (e.g. OpenClaw runtime npm package) when local debugging requires source-level evidence — read-only, scoped path.

### What it is NOT for

- Materializing file edits → assign to Codex/Cursor/another code agent outside `copilot_cli.run`. Copilot CLI may produce text-only plans or diffs but must not write.
- Shell exec, git/gh mutations, Notion writes — blocked by current sandbox; remain blocked.
- Running OpenClaw agents or restarting services.
- Anything that needs L3/L4 gates. Those stay closed by default. Open only inside an approved run window, then rollback immediately.

## Dispatch checklist for any new probe

1. Approval string scoped to the mission (`APPROVE_<MISSION>=YES`).
2. Branch named `rick/<mission-slug>-<YYYY-MM-DD>`.
3. Worker `/health=200` precondition.
4. Sandbox image rebuilt deterministically if missing (`bash worker/sandbox/refresh-copilot-cli.sh`).
5. Token sanity: `COPILOT_GITHUB_TOKEN=present_by_name`, length, short fingerprint logged.
6. Egress via `copilot-egress` bridge, nft populated by `scripts/copilot_egress_resolver.py --include-github-meta`.
7. Run report under `reports/copilot-cli/<id>-<slug>-<date>.md` including:
   - rc, duration, stdout_bytes/stderr_bytes
   - `nft_drop_delta` (packets, bytes)
   - `secret_scan: clean`
   - audit path
   - artifact manifest
   - rollback proof (`/health=200`, no `inet copilot_egress`, no `copilot-egress` docker network, tokens shredded)
8. L3/L4 gates closed at end. Verify rollback before closing PR.

## Known caveats (as of F8E)

- **First-run T1 auth failure** without token rotation. If a session shows `Authentication failed (Request ID …)`, rotate `COPILOT_GITHUB_TOKEN` in `~/.config/openclaw/copilot-cli-secrets.env` and retry. Log fingerprint pre/post (never the value).
- **Opus models gated** at backend: `Error: Model "Claude Opus 4.7" from --model flag is not available.` → fall back to default model and document.
- **Sandbox image may be missing** locally on fresh hosts → rebuild deterministically, do not pull arbitrary tag.

## How this connects to the live work

- Used for `f9-openclaw-subagent-prompt-injection-audit` (task 018, 2026-05-07) to localize the OpenClaw runtime bug behind F-NEW (subagent canned refusal under `**Your Role**` empty section). Read-only audit over the installed npm package, with file:line citations, as input to decide between options (a) bug upstream / (b) config workaround / (c) update OpenClaw 2026.5.6.
- Will be the default lens for any future "what does this code do / why does it fail / what's the smallest safe fix" question over a repo we don't want to perturb.

## Out of scope here

- Any path that needs write/exec inside the sandbox. That requires the hardening track (DNS pin, exec restrictions, write overlay/diff capture, human approval materialization). Until then, keep it text-only.
