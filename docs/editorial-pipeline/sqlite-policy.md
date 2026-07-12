# SQLite Policy — Editorial Pipeline Wave 2

> **Status:** Active policy · updated 2026-06-01 for Wave 2 hardening
> **Scope:** SQLite usage across discovery stages S0/S1/S2.
> **Source files audited:** `scripts/discovery/stage0_load_referentes.py`,
> `scripts/discovery/stage1_discover_signals.py`,
> `scripts/discovery/stage2_verify_sources.py`,
> `scripts/discovery/lib/dedup.py`,
> `scripts/discovery/lib/sqlite_utils.py`,
> `scripts/discovery/migrations/0001_referentes_signals.sql`,
> `scripts/discovery/migrations/0002_signals_verified_published_history.sql`.

This document records the current SQLite policy after the Wave 2 hardening
changes. The main deltas vs. Wave 1.5 are: a shared connection setup with
`PRAGMA busy_timeout=5000`, and an ordered migration runner backed by
`schema_migrations`.

## 1. Database file

- Single SQLite file (path passed via `--sqlite` to S0/S1, `--db` to S2).
- Tables (after migrations 0001 + 0002): `schema_migrations`,
  `referentes_snapshot`, `signals_raw`, `signals_verified`, `published_history`.
- Migrations are pure DDL with `IF NOT EXISTS` everywhere — verified
  idempotent on the smoke run (re-applied 0001 and 0002 to a non-empty
  DB; both `exit_code = 0`).

### 1.1 Known disconnected `discovered_items` spine

The repository also contains an older pipeline that uses the same default
`state.sqlite` path but a separate schema:

- `stage2_ingest.py` creates and fills `discovered_items` directly from its
  own RSS/RSSHub fetch;
- `stage3_promote.py`, `stage4_push_notion.py`,
  `stage5_rank_candidates.py`, and `stage6_llm_combinator.py` consume that
  table;
- S1/S2 Wave 2 instead write `signals_raw` and `signals_verified`.

There is no static `INSERT ... SELECT`, adapter, or dispatcher/cron step that
promotes `signals_raw`/`signals_verified` into `discovered_items`. Sharing a
SQLite filename does not connect the schemas. The current
`discovery-publish-cron.sh` begins with a `discovered_items` backfill/Stage 4,
then invokes Stage 6; it does not run S0/S1/S2 or Stage 5, and leaves Stage 7
manual.

**b0004 verdict:** the spines remain disconnected. No minimal wiring is
applied here because the two Stage 2 implementations have different source
and schema contracts; choosing a conversion boundary requires an explicit
pipeline design decision rather than a mechanical patch.

## 2. PRAGMAs (observed live)

On a freshly-initialised DB after both migrations:

| PRAGMA | Value | Decision |
|---|---|---|
| `journal_mode` | `delete` (default) | **Kept as-is in Wave 2.** Current cron topology is still effectively single-writer. WAL was evaluated and intentionally deferred to avoid `*-wal` / `*-shm` operational sidecars without a demonstrated concurrency need. Revisit only if a true parallel writer lands. |
| `busy_timeout` | `5000` | **Wave 2 fix shipped.** Discovery-stage connections now apply `PRAGMA busy_timeout=5000` during connection setup via `scripts/discovery/lib/sqlite_utils.py`. Short lock contention should wait instead of failing immediately with `SQLITE_BUSY`. |
| `foreign_keys` | not asserted | `signals_verified.signal_id` references `signals_raw.signal_id` semantically but no FK constraint is declared in 0002 and `PRAGMA foreign_keys=ON` is not issued. Still a documented follow-up, not part of this hardening pass. |

## 3. Transaction model per stage

| Stage | File | Pattern observed |
|---|---|---|
| S0 | `stage0_load_referentes.py` | Uses shared `open_sqlite()` helper: connection setup applies `busy_timeout`, then migrations are checked/applied, then snapshot upserts commit per batch. |
| S1 | `stage1_discover_signals.py` | Uses shared `open_sqlite()` helper once per run. Per-canal commits remain unchanged, but the connection now inherits `busy_timeout` and the migration runner. |
| S2 | `stage2_verify_sources.py` | Uses shared connection configuration plus migration runner before fetching work. Verdict upserts still commit per row. |
| `lib.dedup` | `lib/dedup.py` | Helper functions commit on demand when called from S2/S10. No WAL or FK behavior change here. |

**Verdict:** every stage opens its own connection and commits at least at the
end of its work. No stage leaves an uncommitted transaction across process
exit. Crash recovery semantics: SQLite default rollback journal protects
against torn writes.

## 4. Concurrency between stages

The pipeline is **strictly sequential** today: cron runs `S0 → S1 → S2 → ...`
one after another. There is no scheduled overlap. This means:

- **What if S2 runs while S1 is committing?** The cron still serialises
  them, but if short overlap happens anyway the contending connection now
  waits up to 5 seconds before raising `SQLITE_BUSY`. This is a hardening
  improvement, not a license to introduce uncontrolled parallel writers.
- **What about a reader (e.g. dashboard) running while S2 writes?**
  SQLite default rollback-journal mode still blocks readers during the
  writer's commit window. With current small batches this remains
  acceptable. WAL would remove most read blocking; it is still deferred.

## 5. `published_at` / `iso_pub` ausente

Cross-reference: [`./hash-contract.md`](./hash-contract.md) §3.

- `signals_raw.published_at` is `TEXT NULL`. Rows with no upstream date are
  inserted with `published_at = NULL`.
- `dedup_hash` for those rows is `sha256(canonical_url + "\n")` — stable, so
  the `UNIQUE(dedup_hash)` constraint correctly dedups repeat discoveries
  of the same un-dated URL.
- **Gap:** there is no observability counter for `signals_raw WHERE
  published_at IS NULL`. Wave 2 dashboard ticket.

## 6. Migration governance

- Files live under `scripts/discovery/migrations/NNNN_<slug>.sql`.
- Discovery stages now use a thin embedded migration runner in
  `scripts/discovery/lib/sqlite_utils.py`.
- The runner creates and maintains `schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)`.
- Migrations are applied in filename order and recorded once. On legacy DBs
  that predate `schema_migrations`, 0001/0002 are re-run one time and then
  recorded; this is safe because both files remain idempotent via
  `IF NOT EXISTS` guards.
- New migrations therefore apply automatically on the next stage run,
  without requiring an operator to invoke raw `sqlite3 < file.sql`.

## 7. Remaining backlog (summary)

1. Decide WAL on/off when S10b (parallel publisher) or another real
   concurrent writer is designed.
2. Add observability counter for `signals_raw.published_at IS NULL`.
3. Add an explicit FK from `signals_verified.signal_id` to
   `signals_raw.signal_id` and turn on `PRAGMA foreign_keys=ON` per
   connection.

## 8. Verification snippets

The current policy is verified by focused tests covering:

```bash
python3 -m pytest tests/discovery/test_sqlite_hardening.py -q
```

Those tests assert:

- `PRAGMA busy_timeout=5000` is present on discovery connections.
- `schema_migrations` records 0001/0002 in order and remains idempotent.
- a short writer lock clears successfully instead of immediately failing.

Cross-reference: issue [#403](https://github.com/Umbral-Bot/umbral-agent-stack/issues/403).
