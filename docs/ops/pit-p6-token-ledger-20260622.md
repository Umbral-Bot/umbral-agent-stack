# PIT-P6 — Token ledger collector (read-only)

**Status:** `P6_TOKEN_LEDGER_OK`
**Date:** 2026-06-22
**Surface:** Copilot Windows (repo + PR). Read-only VPS smoke optional.
**Script:** `scripts/pit/pit_collect_tokens.py`
**Tests:** `tests/test_pit_collect_tokens.py` (+ fixtures `tests/fixtures/pit-token-ledger/`)

## Purpose

Aggregate, per tournament and per lane, the token usage that two independent
subsystems already write to disk, and emit a single
`metrics/token_ledger.yaml`. The collector is **strictly read-only**: it never
mutates runtime state, never opens gates, never restarts the worker, and never
prints secrets/PAT material (only numeric usage, model names and PIT
correlation ids are read).

It closes the P-series loop: P4 stamped `pit_id` / `lane_id` / `iteration` into
the broker audit (see `pit-p4-broker-contract-20260621.md`); P5 enforced
broker-only lanes (see `pit-p5-broker-enforce-20260622.md`); P6 now reads those
correlation fields back out to build a cost/usage ledger.

## Sources

| Source | Location | Shape |
| --- | --- | --- |
| OpenClaw lane sessions | `<openclaw_root>/agents/<pit_id>-lane-*/sessions/sessions.json` | JSON dict, camelCase `inputTokens` / `outputTokens` / `totalTokens` / `cacheRead` (same reader as `scripts/openclaw_runtime_snapshot.py`). Any `sessions/*.jsonl` transcripts are also scanned as a fallback. |
| Copilot CLI broker audit | `<audit_root>/<YYYY-MM>/<mission_run_id>.jsonl` | P4 audit events, filtered by `metadata.pit_id`, bucketed by `lane_id`. |

Lane id is derived from the agent directory name. The canonical on-disk form is
`<pit_id>-lane-<slug>` where `pit_id` already carries its `pit-` prefix (e.g.
`pit-umbral-bim2-sharepoint-acc-lane-foundry-tools` → `lane-foundry-tools`). An
agent named exactly `<pit_id>` maps to the synthetic lane `_pit_root`. The
documented `pit-<pit_id>` form is also tolerated when the id does not already
start with `pit-`.

## Token reporting limitation

GitHub Copilot CLI does **not** surface token counts. The broker therefore
records `tokens: { source: "not_reported_by_github_copilot_cli" }` in its
`manifest.json` / response, and never writes a populated token block to the
audit JSONL. As a result the per-lane `copilot_cli.tokens` block in the ledger
stays `not_reported_by_github_copilot_cli` unless a future audit event carries
a numeric tokens object. OpenClaw sessions **do** report tokens, so the
`openclaw` block is the authoritative usage signal today.

## Commands

Local (Windows, from repo root):

```powershell
python scripts/pit/pit_collect_tokens.py `
  --pit-id pit-umbral-bim2-sharepoint-acc `
  --vault-root "$env:USERPROFILE\umbral-pit-vault" `
  --openclaw-root "$env:USERPROFILE\.openclaw" `
  --audit-root reports/copilot-cli `
  --stdout
```

VPS (read-only; use the repo venv because system `python3` lacks PyYAML/pydantic):

```bash
cd ~/umbral-agent-stack
PY=./.venv/bin/python; test -x "$PY" || PY=python3
$PY scripts/pit/pit_collect_tokens.py \
  --pit-id pit-umbral-bim2-sharepoint-acc \
  --vault-root ~/umbral-pit-vault \
  --openclaw-root ~/.openclaw \
  --audit-root reports/copilot-cli \
  --output /tmp/token_ledger_smoke.yaml
head -60 /tmp/token_ledger_smoke.yaml
```

Default output (no `--output`): `<vault_root>/pit/<pit_id>/metrics/token_ledger.yaml`.

## Output schema

```yaml
pit_id: pit-umbral-bim2-sharepoint-acc
generated_at_utc: 2026-06-22T07:44:58Z
schema_version: 1
lanes:
  lane-foundry-tools:
    openclaw:
      input: 0
      output: 0
      cache_read: 0
      total: 0
      model: null
      sessions: 0
      events: 0
    copilot_cli:
      calls: 0
      dry_run: 0
      real: 0
      exit_codes: {}
      duration_sec: { sum: 0.0, avg: null }
      tokens:
        source: not_reported_by_github_copilot_cli
    budget_usd_allocated: null
    budget_usd_estimated: null
tournament_total:
  openclaw_total: 0
  copilot_cli_calls: 0
  lanes: 1
  notes: []
sources:
  openclaw_root: ...
  openclaw_found: true
  audit_root: ...
  audit_found: true
  vault_root: ...
  vault_found: true
```

Field notes:

- `copilot_cli.real` vs `dry_run` — a `mission_run_id` is classified **real**
  when any of its audit events carries an `exit_code` or a decision in
  `{execute_started, completed, secret_pattern_redacted}`; otherwise it is a
  dry-run/gated call.
- `copilot_cli.exit_codes` — histogram keyed by stringified exit code.
- `copilot_cli.duration_sec` — sum and average across the lane's calls (only
  the real-execution final events carry `duration_sec`).
- `budget_usd_allocated` — best-effort, from `<vault>/pit/<pit_id>/spec/pit_spec.yaml`
  (`budget_usd_total` split evenly across lanes, or a per-lane `budget_usd`
  override). `null` when no spec/budget is present. `budget_usd_estimated`
  is reserved (always `null` in P6).
- `tournament_total.notes` — non-fatal warnings (missing roots, unreadable
  files). The collector still exits 0 and writes the YAML.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Collector ran and wrote the YAML (warnings allowed). |
| `2` | Invalid `pit_id` (must match `^[A-Za-z0-9._-]{1,64}$`) or output not writable. |

Missing OpenClaw/audit/vault roots are **not** fatal — they produce warnings in
`tournament_total.notes` and a zeroed ledger, so historical or partially
populated tournaments still yield a usable file.

## Relation to P4 audit fields

The collector reads exactly the correlation fields P4 added to the broker
audit: `pit_id` (filter), `lane_id` (bucket), plus `mission_run_id`,
`decision`, `exit_code` and `duration_sec`. No new audit fields are required;
P6 is purely a consumer.

## Tests

```powershell
python -m pytest tests/test_pit_collect_tokens.py -q
```

Covers: OpenClaw per-lane aggregation, foreign-agent isolation, copilot_cli
per-`pit_id`/`lane_id` aggregation + filtering, `not_reported` token fallback,
invalid `pit_id` → exit 2, default + explicit YAML output keys, and
best-effort budget split.

## Hard rules honored

- No new tournament, no L3/L4/nft gate changes, no worker restart.
- No secrets printed; only numeric usage, model names and correlation ids read.
- Scope limited to P6 (one new script + tests + fixtures + this doc).
