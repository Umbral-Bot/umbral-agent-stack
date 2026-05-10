# Wave 2.A — #404-lite publish_log.jsonl report

**Issue**: #404-lite
**PR**: #411 (DRAFT — DO NOT MERGE)
**Branch**: `rrss-wave2a/404-lite-publish-log`
**Base**: `main` (intentionally NOT stacked on #407 / #410)
**Status**: shipped to draft, awaiting review.
**Date**: 2026-05-10

## What was delivered

### Contract

`docs/editorial-pipeline/publish-log-contract.md` (~250 lines).

Defines the schema for `publish_log.jsonl` — a single append-only
observability log that captures every publish-path event with the
publication-grade fields that `ops_log.jsonl` does not carry (channel,
publication_content_hash, would_publish, gate_outcomes).

Sections: Purpose · Scope · Path · Event schema (16 fields) · Event
ordering invariants · Writer API · Integration with #405 / #402 (post-
merge) · What this contract does NOT solve · References.

### Implementation

* New module `scripts/discovery/lib/publish_log.py` (~95 lines):
  * `write_event(event, path=None) -> Path` — permissive append-only
    writer. Resolution order: arg → `PUBLISH_LOG_PATH` env var →
    `~/.config/umbral/publish_log.jsonl`. Auto-injects `timestamp_utc`
    (ISO-8601 UTC) when missing. mkdir -p parent. Never mutates caller
    dict. Raises `TypeError` only on non-dict input.
  * `read_events(path=None) -> list[dict]` — test/inspection helper.
    Empty when missing. Skips blank lines. Raises `JSONDecodeError` on
    corruption.

Permissive-by-design: a writer that rejects malformed events leaves no
trace of the event, which is the wrong default for an audit log. Schema
enforcement lives in callers (publish_guard, future #402 publisher,
future #404 dashboard).

### Tests (18 new)

`tests/lib/test_publish_log.py`:

* Path resolution: arg wins over env, env wins over default, default
  shape.
* Mkdir: nested parent directories created.
* First-write creates file; existing content not truncated.
* Each line is valid JSON; appends one line per call.
* Timestamp: auto-injected with ISO-8601 UTC pattern; preserved when
  caller-supplied; caller dict not mutated.
* Permissive schema: arbitrary keys, unicode, only non-dict raises.
* `read_events`: empty when file missing, skips blank lines, raises on
  corruption.
* Contract round-trip: full 16-field event survives write+read verbatim.

## Test evidence

```text
$env:PYTHONPATH="."
python -m pytest tests/lib/ tests/discovery/ -q
... 242 passed, 1 failed in 6.86s
```

Same pre-existing unrelated failure as #410 / #407. Verified branch-
innocent.

## Why NOT stacked on #407 / #410

Stacking would have forced this PR's review to wait for both #407 and
#410. Splitting keeps the contract + writer reviewable independently. A
follow-up PR (post-#407 + #410 merge) wires
`publish_log.write_event` into the three guard outcomes
(`runtime_block`, `gate_block`, `gate_pass`) per the contract's
"Integration with #405 / #402" section.

## Restrictions respected

* No integration with `publish_guard.assert_can_publish` (intentional —
  waits for #407 + #410).
* No dashboard / reader / aggregation.
* No log rotation; file is monotonically growing append-only.
* No daily cap enforcement.
* No cron / scheduled job.
* No real publisher wiring.
* No Stage 7.5 / variants.py / O16.2 / Azure / aeco-kb changes.

## What this does NOT solve

* No reader or query layer.
* No log rotation policy (file grows monotonically; manual archival
  acceptable for the foreseeable future).
* No alerting on `would_publish=true && publish_enabled=true && dry_run=false`
  (Wave 2.B / monitoring concern; possibly via n8n use case #1 in the
  applicability scan).

## Decisions required from David

* Confirm `~/.config/umbral/publish_log.jsonl` as canonical path.
* Confirm 16-field closed schema + open `extra` dict.
* Confirm permissive-writer policy (schema enforcement in callers, not
  writer).
