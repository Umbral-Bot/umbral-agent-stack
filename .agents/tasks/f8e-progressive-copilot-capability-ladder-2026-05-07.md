---
id: f8e-progressive-copilot-capability-ladder-2026-05-07
title: "F8E progressive Copilot capability ladder (T0–T7)"
assigned_to: copilot-vps
status: done
priority: high
reviewer: codex
created_at: 2026-05-07
completed_at: 2026-05-07
verdict: verde-fuerte
report: reports/copilot-cli/f8e-progressive-copilot-capability-ladder-2026-05-07.md
---

# F8E progressive Copilot capability ladder

## Objective

Run a progressive ladder of Copilot CLI tests (T0–T7) — increasing
complexity from token validation through canonical `copilot_cli.run` and
read-only repo comprehension — to certify which capability tier is
actually unlocked after PRs #327, #328 and #330.

## Approval

`APPROVE_F8E_PROGRESSIVE_COPILOT_CAPABILITY_LADDER=YES`

## Hard rules

- No tokens printed; only `COPILOT_GITHUB_TOKEN=present_by_name`.
- No `--allow-all`, `--allow-all-tools`, `--yolo`.
- No write tools enabled.
- No file edits from inside the sandbox.
- Scoped nft + `copilot-egress` only during probe windows.
- Resolver: `python3 scripts/copilot_egress_resolver.py --include-github-meta --non-strict --format json`.
- Mandatory rollback of nft table + docker network at the end.
- STOP rojo on leak / rollback fail / host-wide drop / token printed / unmappable drops.
- STOP amarillo on explicit non-secret error in T1 ("Authentication failed" / "Copilot Requests").

## Result

**verdict: verde-fuerte** — see report.

First run (commit `20e11ff`) STOP amarillo at T1 — token lacked
`Copilot Requests` permission. After David rotated the worker token
(`COPILOT_GITHUB_TOKEN`, fingerprint changed `066741648703 →
39fa34a87824`, length 93, never printed), F8E was re-executed from T1
under the same approval string.

- **T0 (re-run lite)** — `/health=200`, sandbox image rebuilt
  deterministically (`umbral-sandbox-copilot-cli:6940cf0f274d`).
- **T1 token entitlement** — GREEN. `F8E_T1_OK`, rc=0,
  `nft_drop_delta=0/0`, `container_ready_ms=347`, `copilot_exit_ms=11846`.
- **T2 minimal compute** — GREEN. rc=0, stdout `17`, drops=0/0.
- **T3 Opus 4.7 model override** — amarillo parcial:
  `opus_available=false`. Per spec, continued T4+ with default model.
- **T4 canonical `copilot_cli.run`** — GREEN. `decision=completed`,
  `exit_code=0`, `duration=13.275s`, `F8E_T4_CANONICAL_OK` in artifact
  stdout, drops=0/0, audit + manifest written, `secret_scan: clean`.
- **T5 repo comprehension** — GREEN, score 5/5.
- **T6 risk review** — GREEN, score 5/5.
- **T7 patch proposal text-only** — GREEN, score 5/5.

Rollback verified clean: `RICK_COPILOT_CLI_EXECUTE=false`,
`egress.activated=false`, drop-in removed, `/health=200`, no `inet
copilot_egress` table, no `copilot-egress` docker network, tokens
shredded.

Net effect: PR #331 upgraded from amarillo to verde fuerte. Single
residual amarillo note: Opus 4.7 not exposed by the Copilot backend
for this token (default model works fine).
