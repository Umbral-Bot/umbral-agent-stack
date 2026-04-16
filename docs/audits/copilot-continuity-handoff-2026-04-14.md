# Copilot Continuity Handoff — 2026-04-14

## Purpose

This document captures the relevant technical context from the recent Granola, UX, diagnostics, reconciliation, and Rick/GitHub planning work so a new Copilot thread can continue from facts instead of re-discovering the same state.

Use this as a handoff baseline before starting any new analysis or implementation.

## Canonical Coordination Baseline

- Coordination repo path: `C:\GitHub\umbral-agent-stack-codex-coordinador`
- Canonical coordination branch: `main`
- Current canonical coordination commit: `d4d092e`
- Meaning of `d4d092e`: reconciliation commit that aligns `origin/main` with the functional code that was already running in the VPS runtime

Important:

- Do **not** use `C:\GitHub\umbral-agent-stack-codex` as the canonical source of truth for coordination.
- That older clone remains useful as a historical/feature workspace, but it is not the clean baseline.

## Runtime / Repo Alignment Status

This was a major blocker and is now considered functionally resolved.

### Verified state

- VPS deployed repo path: `/home/rick/umbral-agent-stack`
- VPS deployed branch: `main`
- Runtime worker and dispatcher were reported as running from that deployed repo
- `origin/main` was previously behind the deployed VPS repo by 25 functional commits
- A reconciliation branch was created, excluding restricted metadata paths:
  - `.claude/CLAUDE.md`
  - `.claude/settings.json`
  - `.agents/board.md`
- PR `#195` was opened and merged
- Post-merge verdict reported by Copilot:
  - functional code aligned between runtime and `origin/main`
  - only local-only metadata remained divergent

### Residual divergence accepted as local-only metadata

- `.claude/CLAUDE.md`
- `.claude/settings.json`
- `.agents/board.md`

These files were explicitly classified as tooling/governance metadata, not runtime-functional code.

## What Is Already in `main`

The current `main` already contains the major Granola/runtime work that was reconciled from the VPS:

- Granola raw transcript persistence verification
- Gap audit tooling and tests
- Granola VM/VPS ingestion tooling
- Sanitizer fix for content-heavy tasks
- Supporting runtime/task/test updates brought in by the reconciliation

Current `main` log around the top of the reconciled history:

- `d4d092e` reconciliation: align runtime with origin (25 commits)
- `e1aca46` fix(tests): align upsert_task test with V2 noise reduction
- `75a998d` fix(worker): per-task string limit in sanitizer for content-heavy tasks
- `b93b59e` fix(granola): deprecate standalone gap audit for content classification
- `59d7351` feat(granola): add gap audit scripts — Python for VM, shell for VPS
- `14e721b` fix(granola): resolve merge gaps from codex/granola-raw-intake-batch integration
- `c5f563d` merge(granola): integrate codex/granola-raw-intake-batch — raw integrity verification, gap audit, dedupe hardening

## What Was Diagnosed or Prepared but Is Not Canonical in `main`

These items were discussed and partially prepared in other threads/clones/VPS work, but should **not** be assumed to be merged into current `main` unless verified explicitly.

### UX-1 / UX-2a noise reduction and direct route work

There was a separate UX track covering:

- `S1`: `notify_enlace` default off
- `S3`: trace comments off by default
- `S5`: email draft no longer posted as Notion comment
- `UX-2a`: remove `allow_legacy_raw_to_canonical` gate, mark V1 handlers as deprecated

Copilot reported:

- draft PR `#193`
- later extended to include both UX-1 and UX-2a
- but **current canonical `main` still contains `allow_legacy_raw_to_canonical` logic**

That means:

- treat UX-1 / UX-2a as analyzed and potentially prepared elsewhere
- do **not** assume those changes are in `main`
- if future work depends on them, re-verify from current code first

### Non-canonical documents created in VPS analysis

Copilot reported creating these documents during analysis, but they are **not** present in current canonical `main` and should be treated as thread outputs, not repo baselines:

- `docs/audits/system-megadiagnostic-2026-04-14.md`
- `docs/audits/rick-copilot-baseline-2026-04-14.md`
- `docs/audits/repo-reconciliation-2026-04-14.md`

This handoff captures the most important conclusions from those analyses.

## Key Findings from the Megadiagnostic

Copilot reported the following top findings as the most important system-level conclusions:

1. V1 `session_capitalizable` still exists in code/runtime paths while governance V2 treats it as retired.
2. `worker/tasks/granola.py` is oversized and mixes multiple responsibilities.
3. Architecture docs and current code/runtime diverge significantly.
4. `WORKER_TOKEN` handling is weak: any non-empty string, one shared admin token.
5. `dispatcher/smart_reply.py` is large and under-tested.
6. `_load_openclaw_env()` overwrites all env vars without a whitelist.
7. Alert cooldown is in-memory only.
8. systemd templates lack hardening.
9. `quota_policy.yaml` is parsed in multiple places with divergent fallbacks.
10. Dashboard/alerts leak internal telemetry to David-facing surfaces.

### Megadiagnostic summary conclusions

- Biggest bottleneck: unresolved V1/V2 ambiguity
- Biggest leverage: align docs with reality and split oversized modules

## Key Findings from the Rick + Copilot Baseline

Copilot reported the following baseline facts:

### Rick today

- Rick already has substantial operational capability
- Multiple agent identities exist
- Rick can operate through Telegram, Notion, Linear, and OpenClaw tooling
- Rick already has structured traceability patterns (OpsLogger, Notion/Linear stamps, source/source_kind)

### Main blocker before any serious GitHub/Copilot workflow

- `gh` CLI was installed but **not authenticated**
- GitHub API workflows were blocked:
  - no PR creation
  - no issue creation
  - no comment via `gh`

### Copilot state

- `gh copilot` CLI not installed at that moment
- `github-copilot-sdk` not installed in the VPS venv
- `copilot_agent/` code exists in repo
- no verified Copilot seat/license state at that time

### Baseline conclusion

Before “Rick + Copilot” as a full development backend, the more urgent MVP is:

- Rick + GitHub operational loop:
  - create branch
  - commit
  - push
  - open PR
  - return PR URL to Notion/Linear

## Granola Incident Context That Matters Going Forward

The recent Granola work produced several important conclusions that affect future architecture decisions:

1. `Asesoría discurso 10` **did** have real summary/transcript content in Granola private API.
2. Cache-only inspection was insufficient; private API hydration matters.
3. The previous system allowed silent truncation through the HTTP sanitizer.
4. A sanitizer fix for content-heavy tasks was later validated through normal HTTP path.
5. Functional runtime + repo are now aligned after reconciliation.

This matters because future automation or GitHub/Copilot orchestration should avoid assuming:

- cache-only data is sufficient
- runtime behavior equals old repo state
- comments/telemetry in Notion are safe UX defaults

## Current Recommended Next Front

The next front should **not** start with full “Rick + Copilot” implementation.

The recommended sequence is:

1. Reconciliation complete (done)
2. Use canonical clean `main` as the coordination baseline (done)
3. Open **Rick + GitHub MVP** first
4. Only after GitHub operational readiness is real, decide whether to add:
   - Copilot CLI
   - Copilot coding agent
   - hybrid model

## Recommended Next Front: Rick + GitHub MVP

### Objective

Before integrating Copilot as a coding backend, make the GitHub loop operational for Rick:

- branch
- commit
- push
- PR
- PR URL back to Notion / Linear

### Why this is next

- It is the tactical blocker revealed by the baseline
- It is lower risk than jumping straight to Copilot integration
- It gives a real substrate for later Copilot orchestration
- It avoids designing on top of missing GitHub auth and missing GitHub workflow primitives

## Explicit Non-Goals for the Next Front

Do **not** assume these are already approved for implementation:

- full Copilot CLI integration
- full GitHub Copilot coding agent integration
- automatic merge/deploy by Rick
- multi-session coding orchestration with Copilot as backend
- direct implementation of UX-1 / UX-2a unless revalidated from current `main`

## Constraints and Guardrails to Preserve

Any next-step design should preserve:

- explicit human approval before major execution
- separation of planning vs implementation vs QA vs merge/deploy
- strong traceability back to Notion and/or Linear
- no silent merge or deploy
- no assumption that local-only coordination metadata belongs in runtime reconciliation

## Source Hygiene

When continuing from this handoff:

- treat `C:\GitHub\umbral-agent-stack-codex-coordinador` on `main` as the coordination baseline
- verify current code before assuming older PR/thread proposals are merged
- distinguish carefully between:
  - what was reported in threads
  - what is in canonical `main`
  - what is local-only VPS metadata

## Suggested Continuation Prompt

Use this as the next prompt if you want to continue from this exact handoff:

> Revisa `docs/audits/copilot-continuity-handoff-2026-04-14.md` y continúa desde ese baseline. No reabras el incidente Granola ni la reconciliación. El siguiente frente es diseñar y aterrizar el MVP `Rick + GitHub` (no Copilot todavía): readiness real de `gh`, identidad GitHub de Rick, branch/commit/push/PR, y trazabilidad de vuelta a Notion/Linear. Antes de proponer implementación, confirma desde el código actual de `main` qué partes de UX-1/UX-2a están realmente presentes y cuáles no.
