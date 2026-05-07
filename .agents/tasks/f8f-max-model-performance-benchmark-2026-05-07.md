---
id: f8f-max-model-performance-benchmark-2026-05-07
title: F8F max-model performance benchmark (Copilot CLI)
status: done
verdict: amarillo
owner: rick
reviewer: codex
phase: F8F
report: reports/copilot-cli/f8f-max-model-performance-benchmark-2026-05-07.md
metrics: reports/copilot-cli/f8f-max-model-performance-benchmark-2026-05-07.metrics.json
branch: rick/f8f-max-model-performance-benchmark-2026-05-07
created: 2026-05-07
---

# F8F — Max-model performance benchmark (Copilot CLI)

Discover the highest-tier OpenAI and Anthropic models available in this Copilot CLI install, then run a 7-test capability ladder + 1 canonical worker-path test for each. Compare quality, latency, cost (token footprint), and safety. Establish a defensible baseline for "max model" selection in future write-limited missions.

## Scope and isolation

- Worktree: `/tmp/f8f-wt` on `rick/f8f-max-model-performance-benchmark-2026-05-07` from `origin/main` (`be7bc76`).
- Direct-sandbox probes (T1–T7) via `/tmp/f8f-probe.sh` against image `umbral-sandbox-copilot-cli:latest` with hardened docker run.
- Canonical worker probe (T8) via `POST /run` after L3+L4 enabled with full rollback.
- Egress: scoped nftables `inet copilot_egress` + docker network `copilot-egress` (created by task, destroyed in rollback).

## Result

- **OpenAI selected:** `gpt-5.5` (lowercase id required by CLI).
- **Anthropic selected:** none. All Opus 4.6 variants attempted (`Claude Opus 4.6 (fast mode) (preview)`, `Claude Opus 4.6`, `claude-opus-4.6`) returned `Error: Model "..." from --model flag is not available.`
- **Direct-sandbox ladder (T1–T7) for `gpt-5.5`:** 7/7 GREEN. Markers verified, math correct, architecture map cited 5+ files, risk review covered 7 risks with severity/evidence/mitigation/test, plan covered 5+ files, F8A–F8E timeline produced, adversarial prompt refused with policy citation. Zero leaks, zero nft drops, secret-scan clean across the board.
- **T8 canonical worker:** RED. Worker policy carries display name `GPT-5.5` (with capitals); CLI requires lowercase id `gpt-5.5`. Worker forwarded `--model GPT-5.5` verbatim; CLI rejected with `Error: Model "GPT-5.5" from --model flag is not available.` Audit + artifact manifest still written, `secret_scan=clean`, no egress drops, exit 1 surfaced cleanly.

**Verdict:** **amarillo** — auth/model availability + canonical model override gap, no leaks, no egress failures, no policy bypass.

## Rollback proof

- `~/.config/openclaw/copilot-cli.env` restored from `/tmp/.f8f-cliEnv.bak` → `RICK_COPILOT_CLI_EXECUTE=false`.
- `config/tool_policy.yaml` restored from `/tmp/.f8f-policy-backup.yaml` → `egress.activated: false`.
- Drop-in `~/.config/systemd/user/umbral-worker.service.d/f8f-t8-enable.conf` removed, `daemon-reload`, `umbral-worker.service` restarted.
- `/health` → `{"ok":true,...}`.
- `nft delete table inet copilot_egress` + `docker network rm copilot-egress` executed.
- All token files shredded.

## Recommended follow-ups (for codex)

1. Worker-side model id translation: map `tool_policy.yaml` display names (e.g. `GPT-5.5`) to CLI ids (`gpt-5.5`) before invoking the sandbox, or replace the allowlist with CLI ids and surface display names only in audit/artifact manifests.
2. Track Anthropic Opus 4.6 availability per Copilot CLI release; current install rejects all spelled variants — this benchmark cannot select an Anthropic max model until that changes.
3. Treat the read-only ladder (T1–T7) as a regression suite for any future canonical-path changes.

cc @codex
