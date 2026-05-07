---
id: f8d-default-model-egress-proof-2026-05-07
title: "F8D default-model Copilot CLI egress proof (no --model)"
assigned_to: copilot-vps
status: done
priority: high
reviewer: codex
created_at: 2026-05-07
completed_at: 2026-05-07
verdict: amarillo
report: reports/copilot-cli/f8d-default-model-egress-proof-2026-05-07.md
---

# F8D default-model Copilot CLI egress proof

## Objective

Prove that, with PR #327 (resolver `--include-github-meta`) and PR #328
(F8C evidence) merged on `main`, the egress + token + Copilot CLI path is
healthy when **no** `--model` flag is passed (Copilot backend chooses its
own default model).

This isolates the egress / GitHub Meta CIDR fix from any model-availability
concern that surfaced in F8C (`Error: Model "Claude Opus 4.7" from --model
flag is not available.`).

## Approval

`APPROVE_F8D_DEFAULT_MODEL_EGRESS_PROOF=YES`

## Hard rules

- NO `copilot_cli.run` task.
- Exactly one direct sandbox probe.
- NO `--model` flag.
- NO write tools.
- NO `--allow-all`, `--allow-all-tools`, `--yolo`.
- Token never printed; only `COPILOT_GITHUB_TOKEN=present_by_name`.
- Resolver MUST use `--include-github-meta`.
- Mandatory rollback of nft + docker network.

## Verdict criteria

- verde: `rc=0`, stdout contains `F8D_OK`, `nft_drop_delta=0`.
- amarillo: `rc!=0` with explicit non-secret error.
- rojo: leak, rollback fail, token fail, missing CIDR, drops not mappable.

## Result

**verdict: amarillo** — see report.

Egress fix proven (`nft_drop_delta=0/0`, kernel logs show accepts to
`140.82.112.22` via `140.82.112.0/20`). Probe failed with explicit
non-secret backend error: `Authentication failed (Request ID: ...)` —
the worker token is valid for `api.github.com/user` (HTTP 200) but lacks
the `Copilot Requests` scope required by Copilot CLI.
