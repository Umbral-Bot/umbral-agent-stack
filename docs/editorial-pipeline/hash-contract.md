# Hash Contract — Editorial Pipeline Wave 1.5

> **Status:** Draft (do-not-merge) · branch `wave1.5-integration` · 2026-05-08
> **Owner:** integration team (Wave 1.5)
> **Reconciles:** H2 (`signal_hash`/`dedup_hash`) ↔ H3 (`content_hash`/`idempotency_key`)

This document is the single source of truth for every **hash field** the
discovery pipeline computes and persists across stages S1, S2 and S10.
It exists to prevent the cross-stage drift identified in the Wave 1.5
external review (conflict #6: "two hash layers without contract").

## 1. Matrix

| Hash | Where it is computed | Inputs | Stage owner | Purpose | Stability |
|---|---|---|---|---|---|
| `dedup_hash` (a.k.a. `signal_hash`) | S1 — [`scripts/discovery/stage1_discover_signals.py`](../../scripts/discovery/stage1_discover_signals.py) `dedup_hash(canonical_url, published_at)` | `sha256(canonical_url + "\n" + (published_at or ""))` | H2 | Discovery dedup — keep one row per `(URL, pub_date)` in `signals_raw.dedup_hash UNIQUE`. Prevents re-processing the same item across cron runs. | Deterministic by construction. **Independent of wall clock** (`None`/`""` is hashed as empty string, not as `now()`). |
| `content_hash` | S2 — [`scripts/discovery/lib/dedup.py`](../../scripts/discovery/lib/dedup.py) `compute_content_hash(canonical_url, title, excerpt)` | `sha256(canonical_url + "\n" + normalize(title) + "\n" + normalize(excerpt))` | H3 | Pre-publish content dedup — detect URL-distinct mirrors of the same content. Stored on `signals_verified.content_hash`. | Deterministic. Date-independent. Sensitive to title/excerpt edits. |
| `idempotency_key` | S2 — [`scripts/discovery/lib/dedup.py`](../../scripts/discovery/lib/dedup.py) `compute_idempotency_key(canonical_url, content_hash)` | `sha256(canonical_url + "\n" + content_hash)` | H3 | Idempotency for downstream POSTs (LinkedIn / blog / newsletter). Stored on `signals_verified.idempotency_key`. Re-used by S10 (Hilo 6) and reconciled with the existing `📰 Publicaciones.idempotency_key` Notion property. | Deterministic. Changes iff `content_hash` changes. |

## 2. Naming alias

The task brief uses `signal_hash`. The implementation in S1 uses
`dedup_hash`. They are the same thing. Going forward, prefer
`dedup_hash` (matches the column name in `signals_raw`).

## 3. Edge case — `published_at` ausente / vacío / `None`

**Observed behaviour (verified on `wave1.5-integration` smoke run, 2026-05-08):**

- Input `published_at = None` → hashed as empty string. Result: `sha256("<canonical_url>\n")`. Deterministic.
- Input `published_at = ""` → identical to `None` (empty string).
- Input `published_at = "2026-05-08T12:00:00Z"` → distinct from the empty case for the same URL.

**Implication for cron idempotency:** when the upstream feed never publishes a
date for an item, every cron run computes the same `dedup_hash`. The
`UNIQUE(dedup_hash)` constraint then prevents a second insert. The cron is
idempotent in that case.

**Implication for content updates:** if upstream later starts emitting a
`published_at` for the *same* URL, the new `dedup_hash` will differ from the
prior hash, and a second `signals_raw` row will be inserted for the same
URL. This is **expected and tolerated in Wave 1**: S2 will still dedup
downstream via `content_hash`, and S10 will dedup via `idempotency_key`.

**Gap (postponed Wave 2):** there is no observability counter for this case
(rows with `published_at IS NULL`) in `signals_raw`. Wave 2 should add a
metric `signals_raw.no_pub_date_total` to the dashboard. **No code change in
Wave 1.5** — this is documentation-only per task brief antipattern #8.

## 4. Wave 2 candidate fix (NOT IMPLEMENTED in 1.5)

Two stable strategies are on the table for Wave 2; neither ships in 1.5:

1. **Use `discovered_at` as fallback** — would change `dedup_hash` semantics
   from "URL identity" to "URL+seen-at identity"; rejected as more brittle
   than current behaviour.
2. **Emit a separate `signal_first_seen_hash`** — `sha256(canonical_url)` only,
   stored alongside `dedup_hash`, used by S2 for the "is this URL new ever?"
   query. Lower risk; keeps the existing UNIQUE constraint intact.

David should pick one in Wave 2 grooming. Wave 1.5 keeps the current S1
behaviour.

## 5. Verification — tests

Tests live in [`tests/discovery/test_hash_contract.py`](../../tests/discovery/test_hash_contract.py)
and assert:

- `dedup_hash` is deterministic for the same `(url, iso_pub)` pair.
- `dedup_hash` for `published_at=None`, `""`, missing key are all equal.
- `dedup_hash` for `published_at="2026-05-08T..."` differs from the empty case.
- `content_hash` ignores `published_at` entirely (date-independent) but flips
  when `title` or `excerpt` change.
- `idempotency_key` flips iff `content_hash` flips, for the same canonical URL.

## 6. Cross-references

- Smoke run that produced the live counts: [`reports/2026-05-08-wave1_5-smoke.md`](../../reports/2026-05-08-wave1_5-smoke.md) (Phase 5).
- Notion `idempotency_key` property audit: [`docs/audits/2026-05-08-notion-publicaciones-schema-audit.md`](../audits/2026-05-08-notion-publicaciones-schema-audit.md).
- SQLite policy for the storage side: [`./sqlite-policy.md`](./sqlite-policy.md).
- Notion helpers policy (read vs write split): [`./notion-helpers-policy.md`](./notion-helpers-policy.md).
