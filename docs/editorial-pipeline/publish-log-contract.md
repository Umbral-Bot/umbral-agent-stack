# publish_log.jsonl observability contract

**Issue**: #404-lite
**Wave**: 2.A
**Status**: draft (do-not-merge bundle with #405 / #402)
**Depends on**: #405 (PR #407, `PublishFlags`), #402 (PR #410,
`publication_content_hash`).
**Consumed by**: future dashboard (NOT in scope for this issue), Friday
retro evidence, post-mortem of any false-positive publish.

## Purpose

Provide a single append-only observability log of every publish-path
event (gate pass, gate block, runtime block, dry-run rehearsal, real
publish attempt) so that:

* David can answer "what did the system try to publish in the last 24h?"
  from a single file, without scraping 6 different log destinations.
* Stop-button activations leave an audit trail that survives process
  restarts (`ops_log.jsonl` already does this for `publish_guard.*`, but
  `publish_log.jsonl` carries the publication-grade fields too — channel,
  publication_content_hash, would_publish — that `ops_log` does not).
* Future continuous-eval / monitoring jobs can ingest a stable schema
  instead of parsing free-form ops_log entries.

## Scope

This issue ships:

1. The schema (this document).
2. A pure writer module `scripts/discovery/lib/publish_log.py`.
3. Unit tests.

This issue does NOT ship:

* Integration into `publish_guard.assert_can_publish` (waits for #402
  merge).
* Any reader / dashboard / aggregation code.
* Rotation policy (file is single-shot append for now; rotation deferred).
* Cron / scheduled job wiring.

## Path

Default: `~/.config/umbral/publish_log.jsonl`.
Override (tests + VPS): env var `PUBLISH_LOG_PATH`, mirroring the
`OPS_LOG_PATH` pattern already used by `publish_guard`.

If the parent directory does not exist, the writer creates it
(`mkdir -p` semantics). If the file does not exist, the first write
creates it. No truncation, ever — this file is append-only.

## Event schema (one line per JSON object)

Fields in canonical order. All fields are MANDATORY unless marked
optional. Unknown / missing values are persisted as `null`, NOT omitted,
so consumers can rely on key presence.

| Field                          | Type     | Source                                                         |
|---|---|---|
| `timestamp_utc`                | string   | ISO-8601 UTC with seconds precision; auto-injected if missing  |
| `event`                        | string   | one of `publish_log.runtime_block`, `publish_log.gate_block`, `publish_log.gate_pass`, `publish_log.dry_run`, `publish_log.publication_blocked`, `publish_log.publish_attempt`, `publish_log.publish_success`, `publish_log.publish_failure` |
| `page_id`                      | string   | Notion page id (or `null` for system events)                   |
| `source_content_hash`          | string   | sha256 from `lib.dedup.compute_source_content_hash` (= `content_hash`) |
| `publication_content_hash`     | string\|null | sha256 from `lib.publication_hash` (#402); `null` until copy approved |
| `channel`                      | string\|null | `linkedin`, `blog`, `x`, `newsletter`, or `null`            |
| `target`                       | string\|null | resolved publish URL when known (else `null`)               |
| `publish_enabled`              | bool     | `PublishFlags.publish_enabled`                                 |
| `dry_run`                      | bool     | `PublishFlags.dry_run`                                         |
| `max_posts`                    | int      | `PublishFlags.max_posts`                                       |
| `max_posts_per_day`            | int      | `PublishFlags.max_posts_per_day`                               |
| `block_reasons`                | string[] | `PublishFlags.block_reasons()` (empty list if not blocking)    |
| `cross_validation`             | string[] | `PublishFlags.cross_validation_warnings()`                     |
| `gate_outcomes`                | object\|null | flat dict of the 6 editorial gates; `null` when not evaluated (runtime_block path) |
| `would_publish`                | bool     | True iff every guard layer would have allowed a real POST     |
| `published_url`                | string\|null | populated only on `publish_log.publish_success`             |
| `extra`                        | object   | optional caller-supplied dict, persisted verbatim              |

`extra` is the only "open" field; everything else is closed-schema. This
keeps the file machine-parseable while leaving an escape hatch for
callers (e.g. attaching a dispatcher attempt id, a Notion comment id,
etc.) without a schema migration.

### Event ordering invariants

* `publish_log.runtime_block` is mutually exclusive with
  `publish_log.gate_block` / `publish_log.gate_pass`. Runtime block wins
  and emits exactly one line.
* `publish_log.gate_pass` may be followed by either
  `publish_log.publication_blocked` (publication-hash dedup hit, #402),
  `publish_log.dry_run` (PublishFlags allows real publish but the call
  site is a dry-run rehearsal), or `publish_log.publish_attempt` →
  `publish_log.publish_success` / `publish_log.publish_failure`.
* `would_publish` is a derived field that consumers can use to filter
  "what would have happened in a real publish?" without re-implementing
  the layered guard logic.

## Writer API

`scripts/discovery/lib/publish_log.py`:

```python
def write_event(
    event: dict,
    path: str | os.PathLike | None = None,
) -> None:
    """Append one JSON line to publish_log.jsonl.

    * Resolves path from arg, then PUBLISH_LOG_PATH env var, then default.
    * Auto-injects timestamp_utc if missing.
    * Does NOT validate event keys against the schema (schema enforcement
      lives in the future integration code; this writer is intentionally
      permissive so it is safe to call from emergency scripts).
    * Atomic per-line append: opens with mode 'a', writes a single
      json.dumps(...) + '\\n', closes. No buffering across calls.
    """
```

Permissive on purpose: a writer that rejects malformed events leaves no
trace of the event and that is the wrong default for an audit log. The
contract enforcement is the responsibility of the caller (publish_guard,
#402 publisher, future #404 dashboard).

## Integration with #405 / #402 (post-merge)

When this PR's writer is wired into `publish_guard.assert_can_publish`
(post-merge of all three Wave 2.A PRs), the call sites are:

1. **runtime_block path** (flags fail-closed): writer emits
   `publish_log.runtime_block` with `gate_outcomes=null`,
   `would_publish=false`, `block_reasons=flags.block_reasons()`.
2. **gate_block path** (flags pass, editorial gate fails):
   `publish_log.gate_block` with `gate_outcomes={...}`,
   `would_publish=false`.
3. **gate_pass path**: `publish_log.gate_pass` with `would_publish=true`
   when flags allow real publish AND no publication_content_hash dedup
   hit; `would_publish=false` when flags allow but the publisher would
   then dry-run / abort on publication-hash.

Until that wiring lands, this PR ships only the schema + writer. It does
NOT modify `publish_guard.py` or any other Wave 1.5 / 2.A runtime path.

## What this contract does NOT solve

* No daily cap enforcement (deferred — `MAX_POSTS_PER_DAY` is logged but
  not consulted to block).
* No log rotation. The file grows monotonically. A 1-line-per-publish
  rate is bounded enough for several years before manual archival is
  needed.
* No reader, query, or aggregation layer.
* No alerting on `would_publish=true` while
  `publish_enabled=true && dry_run=false` (Wave 2.B / monitoring concern).

## References

* `docs/editorial-pipeline/runtime-flags-contract.md`
* `docs/editorial-pipeline/publication-content-hash-contract.md`
* `docs/audits/2026-05-10-wave2a-plan.md`
* `scripts/discovery/lib/publish_flags.py`
* `scripts/discovery/lib/publish_guard.py`
