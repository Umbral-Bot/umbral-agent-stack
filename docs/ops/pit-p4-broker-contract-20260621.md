# PIT P4 — `copilot_cli.run` broker contract

**Date:** 2026-06-21
**Surface:** Copilot Windows (worker code) · no VPS writes
**Scope:** lane-correlation metadata, audit correlation, `reasoning_effort` input contract.

This contract lets a PIT tournament dispatch many `copilot_cli.run` lanes and
join every audit event and worker response back to its `batch_id` / `lane_id` /
`pit_id` / `iteration`. It builds on the P3 model-slug audit
([`evidence-imports/pit-p3-vps-copilot-slugs-audit-20260621/REPORT.md`](evidence-imports/pit-p3-vps-copilot-slugs-audit-20260621/REPORT.md)).

## Canonical lane payload

```json
{
  "mission": "research",
  "model": "Claude Opus 4.7",
  "prompt": "Summarize the failing tests in this repo.",
  "repo_path": "/work",
  "dry_run": true,
  "max_wall_sec": 60,
  "reasoning_effort": "xhigh",
  "metadata": {
    "batch_id": "pit-batch-01",
    "agent_id": "copilot-a",
    "lane_id": "lane-friccion",
    "pit_id": "pit-salud-mental",
    "iteration": 3,
    "requested_by": "rick-tech"
  }
}
```

- `model` accepts a display name (`Claude Opus 4.7`) and resolves to the
  lowercase-hyphenated slug (`claude-opus-4.7`) via the post-P3 policy aliases.
  `force_default_model` is `false`, so per-lane overrides are honored.
- `reasoning_effort` is a **top-level** key (not inside `metadata`). When
  omitted, the policy default (`high`) applies.

## PIT metadata validation

| Field | Rule | Error on violation |
|---|---|---|
| `batch_id`, `agent_id`, `lane_id`, `pit_id` | `^[A-Za-z0-9._-]{1,64}$` | `invalid_metadata:<field>` |
| `iteration` | integer in `[0, 999]` (no `bool`) | `invalid_metadata:iteration` |

`batch_id` defaults to `single` and `agent_id` to `copilot-cli` when absent;
`lane_id` / `pit_id` / `iteration` are optional and only echoed when present.
Validation errors surface the specific code in the response `error` field — never
an opaque `invalid_input`.

## `reasoning_effort` allowed values

GitHub Copilot CLI `1.0.36` exposes `low | medium | high | xhigh` (per P3
evidence). The broker also accepts the display alias `max`, normalized to
`xhigh`. Any other value is rejected with `invalid_reasoning_effort` (the
offending value is echoed back, redacted). On a real run the value is passed to
the container as `--reasoning-effort <value>`.

## Audit + response correlation

Every audit JSONL event (`F8A` phase) and the worker response carry, when
present:

- `batch_id`, `agent_id` (always; defaulted as above)
- `pit_id`, `lane_id`, `iteration` (only when supplied + valid)
- `model` (resolved slug), `requested_model` (when an alias was used),
  `reasoning_effort`
- token/cost block via the artifact manifest: when the CLI does not report
  usage, `tokens.source = "not_reported_by_github_copilot_cli"` (same pattern
  as P2 run3).

Secrets are redacted; tokens are never written to the audit trail.

## Test coverage

`tests/test_copilot_cli.py` (mocked subprocess, no Docker / no network):

- PIT metadata appears in audit JSONL and in the dry-run response.
- `reasoning_effort=xhigh` accepted and passed to argv; `max` → `xhigh`.
- `reasoning_effort=bogus` → `invalid_reasoning_effort` (not `invalid_input`).
- Malformed `lane_id` → `invalid_metadata:lane_id`; `iteration=1000` →
  `invalid_metadata:iteration`.
- Display model `Claude Opus 4.7` resolves to `claude-opus-4.7`.

**Verdict:** `P4_WORKER_CONTRACT_OK`
