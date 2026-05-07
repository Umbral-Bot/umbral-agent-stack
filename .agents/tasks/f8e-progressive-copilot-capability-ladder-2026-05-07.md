---
id: f8e-progressive-copilot-capability-ladder-2026-05-07
title: "F8E progressive Copilot capability ladder (T0–T7)"
assigned_to: copilot-vps
status: done
priority: high
reviewer: codex
created_at: 2026-05-07
completed_at: 2026-05-07
verdict: amarillo
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

**verdict: amarillo** — see report.

T0 (sync + source gates) and infra setup PASS. T1 (token entitlement)
FAIL with explicit non-secret error: `Authentication failed (Request
ID: ...)` / hint about `Copilot Requests` permission. Per task rules,
T2–T7 SKIPPED. Rollback clean (`/health=200`, no nft, no docker network,
no `br-copilot`, tokens shredded).
