# SQLite Policy — Editorial Pipeline Wave 1.5

> **Status:** Draft (do-not-merge) · branch `wave1.5-integration` · 2026-05-08
> **Scope:** documentation-only audit of the SQLite store used by S0/S1/S2.
> **Source files audited:** `scripts/discovery/stage0_load_referentes.py`,
> `scripts/discovery/stage1_discover_signals.py`,
> `scripts/discovery/stage2_verify_sources.py`,
> `scripts/discovery/lib/dedup.py`,
> `scripts/discovery/migrations/0001_referentes_signals.sql`,
> `scripts/discovery/migrations/0002_signals_verified_published_history.sql`.

This document records the **observed** state of SQLite usage across the
discovery stages. **No code changes are introduced in Wave 1.5.** Gaps are
noted for Wave 2 grooming.

## 1. Database file

- Single SQLite file (path passed via `--sqlite` to S0/S1, `--db` to S2).
- Tables (after migrations 0001 + 0002): `referentes_snapshot`, `signals_raw`,
  `signals_verified`, `published_history`.
- Migrations are pure DDL with `IF NOT EXISTS` everywhere — verified
  idempotent on the smoke run (re-applied 0001 and 0002 to a non-empty
  DB; both `exit_code = 0`).

## 2. PRAGMAs (observed live)

On a freshly-initialised DB after both migrations:

| PRAGMA | Value | Decision |
|---|---|---|
| `journal_mode` | `delete` (default) | **Keep `delete` for Wave 1.5.** Single-writer cron model — no concurrent writers. WAL adds operational complexity (`*-wal`, `*-shm` sidecars) without a proven need. **Wave 2 must revisit if a parallel publisher (S10b) lands.** |
| `busy_timeout` | `0` | **Gap.** No busy timeout is configured. Acceptable while there is exactly one writer process at a time, but if S2 ever runs concurrently with S1 the second writer fails immediately on `SQLITE_BUSY`. **Wave 2 candidate fix:** call `PRAGMA busy_timeout=5000` on connect in every stage. |
| `foreign_keys` | not asserted | `signals_verified.signal_id` references `signals_raw.signal_id` semantically but no FK constraint is declared in 0002 and `PRAGMA foreign_keys=ON` is not issued. Stage 1.5 leaves this as documented gap. |

## 3. Transaction model per stage

| Stage | File | Pattern observed |
|---|---|---|
| S0 | `stage0_load_referentes.py` | `sqlite3.connect()` → DDL writes → `conn.commit()` per batch (`L59`, `L128`). Single transaction per snapshot. |
| S1 | `stage1_discover_signals.py` | `sqlite3.connect()` once per run (`L577`). Inside each canal handler, a `conn.commit()` is issued after the per-canal batch (`L425`, `L439`, `L457`, `L477`, `L498`). Final `conn.commit()` at end of run (`L539`). Acceptable: each canal is its own atomic unit; partial-failure leaves earlier canals durably written. |
| S2 | `stage2_verify_sources.py` | `sqlite3.connect()` once per run (`L521`). Two commits: `L148` (history schema bootstrap), `L470` (after the entire batch is verified). Acceptable for batch sizes ≤ a few hundred. |
| `lib.dedup` | `lib/dedup.py` | Helper functions commit on demand (`L94`, `L141`) when called from S2/S10. |

**Verdict:** every stage opens its own connection and commits at least at the
end of its work. No stage leaves an uncommitted transaction across process
exit. Crash recovery semantics: SQLite default rollback journal protects
against torn writes.

## 4. Concurrency between stages

The pipeline is **strictly sequential** today: cron runs `S0 → S1 → S2 → ...`
one after another. There is no scheduled overlap. This means:

- **What if S2 runs while S1 is committing?** Today: cannot happen (cron
  serialises them). If it did happen, with `busy_timeout=0`, the
  second writer would hit `SQLITE_BUSY` immediately and crash. The
  store would remain consistent (each stage's writes are atomic) but
  the slower stage would fail loudly. **Acceptable risk for Wave 1.**
- **What about a reader (e.g. dashboard) running while S2 writes?**
  SQLite default rollback-journal mode blocks readers during the writer's
  commit window. With small batches (~30 rows) this is sub-second.
  **Acceptable.** WAL would remove the block; deferred to Wave 2.

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
- They are applied by raw `sqlite3 < file.sql`, not by an embedded
  migration runner. **This is intentional for Wave 1** (smaller surface,
  trivial to audit). Wave 2 should introduce a thin runner that records
  applied migrations in a `schema_migrations` table.
- All 0001 + 0002 statements are guarded with `CREATE TABLE IF NOT EXISTS`
  / `CREATE INDEX IF NOT EXISTS`. **Verified idempotent on smoke
  run** (Phase 5).

## 7. Wave 2 backlog (summary)

1. Add `PRAGMA busy_timeout=5000` on every `sqlite3.connect()` in
   `stage0/stage1/stage2`.
2. Decide WAL on/off when S10b (parallel publisher) is designed.
3. Add `schema_migrations` table + a runner that records applied versions.
4. Add observability counter for `signals_raw.published_at IS NULL`.
5. Add an explicit FK from `signals_verified.signal_id` to
   `signals_raw.signal_id` and turn on `PRAGMA foreign_keys=ON` per
   connection.

## 8. Verification snippets

The following commands, run on the smoke DB at end of Phase 5, produced
the values above:

```bash
sqlite3 "$SQLITE" "PRAGMA journal_mode;"   # delete
sqlite3 "$SQLITE" "PRAGMA busy_timeout;"   # 0
sqlite3 "$SQLITE" ".tables"                # published_history referentes_snapshot signals_raw signals_verified
```

Cross-reference: [`reports/2026-05-08-wave1_5-smoke.md`](../../reports/2026-05-08-wave1_5-smoke.md).
