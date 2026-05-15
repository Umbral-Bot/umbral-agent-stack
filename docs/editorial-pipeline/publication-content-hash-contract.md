# Publication content hash contract

**Issue**: #402
**Wave**: 2.A
**Status**: draft (do-not-merge bundle with #405 / #404-lite)
**Depends on**: #405 (`PublishFlags`, `publish_guard.runtime_block`).
**Consumed by**: #404-lite (`publish_log.jsonl` must persist this hash) and any
future real publisher.

## Purpose

Close the gap declared in `docs/editorial-pipeline/hash-contract.md §1bis`:

> **Wave 2 ticket (obligatorio antes de cualquier publicación real):**
> definir, computar y persistir `publication_content_hash` en
> `published_history` separado de `content_hash`.

`publication_content_hash` is the deterministic identity of the **copy
approved for a specific channel**, separate from the `source_content_hash`
(= `content_hash`) that identifies the source signal. Two channels publishing
the same signal MUST produce two distinct `publication_content_hash` values
because the copy itself differs. Same channel + identical copy MUST produce
the same hash so retries are idempotent.

## Why a second hash

* `content_hash` = identity of the source/signal (canonical_url + source title +
  source excerpt). Wave 1.5 used it as a provisional dedup proxy at
  `register_published` — that protects "have we ever published anything from
  this source?" but NOT "have we ever published this particular copy on this
  channel?".
* Once #406 source-use policy enables multi-channel adaptation (LinkedIn body
  vs blog draft from the same source), `content_hash` collides across
  channels. `publication_content_hash` does not.
* Once #405 stop button blocks at the runtime-flag layer, the next
  protection layer is the publication-copy idempotency: if David edits the
  approved copy, the hash flips and the system treats it as a new
  publication candidate (fresh approval needed).

## Inputs and normalization

`compute_publication_content_hash(channel, body_text, title="", source_content_hash="")`:

```text
payload = "\n".join([
    channel.strip().lower(),
    normalize_publication_text(title),
    normalize_publication_text(body_text),
    source_content_hash.strip(),
])
publication_content_hash = sha256(payload).hexdigest()
```

`normalize_publication_text(s)`:

* Returns `""` for `None` or non-string falsy input.
* Coerces non-string to `str`.
* Replaces CRLF / CR with LF.
* Strips trailing horizontal whitespace per line.
* Collapses runs of horizontal whitespace inside a line to a single space.
* Collapses runs of 3+ blank lines to exactly 2 (paragraph break).
* Strips leading/trailing blank lines.
* **Preserves case** — publication copy treats casing as semantic
  ("BIM" vs "bim" matter on a public post).

This is intentionally NOT the same normalization as
`lib.dedup.normalize_text` (which lowercases). Keeping a dedicated
normalizer for publication copy avoids a one-size-fits-all rule that loses
information needed for publication-grade idempotency.

`channel` is normalized as `strip().lower()` to match the existing
`gates._VALID_CHANNELS = {blog, linkedin, x, newsletter}` set.

`source_content_hash` is included so two unrelated signals that happen to
produce identical copy still hash distinctly. It defaults to `""` so the
function remains pure and callable from a test that only cares about
copy-level identity.

## Stability rules

* Deterministic across processes and Python versions (sha256 of a UTF-8
  byte string).
* Independent of wall clock.
* Independent of `published_at`.
* Flips iff at least one of `{channel, normalized title, normalized body,
  source_content_hash}` changes.
* Whitespace-only edits to the body do NOT flip the hash (per
  normalization above).
* Case edits to the body DO flip the hash.

## Persistence

`published_history` schema gains an additive column:

```sql
ALTER TABLE published_history
    ADD COLUMN publication_content_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_published_history_pub_hash
    ON published_history(publication_content_hash);
```

`ensure_published_history_schema` performs this migration idempotently using
`PRAGMA table_info(published_history)` to detect a missing column, so
existing `published_history.db` files on the VPS are upgraded in place
without manual intervention.

`register_published(db, content_hash, published_url, platform,
publication_content_hash=None)` accepts the new value as an OPTIONAL
parameter to preserve back-compat with legacy callers (Wave 1.5 stage10c).
When supplied, it is persisted; when omitted, the row stores `NULL` and
`is_duplicate_publication` simply will not match it.

`is_duplicate_publication(db, publication_content_hash)` returns `True` iff a
row exists where `publication_content_hash = ?`. Tolerates a missing column
or missing table by returning `False` (consistent with `is_duplicate`).

## Idempotency for real publishers

Once a real publisher exists (post Wave 2.A), the call sequence becomes:

1. Build the approved copy from the Notion page (channel-specific).
2. Compute `publication_content_hash`.
3. Call `publish_guard.assert_can_publish(notion_page, content_hash, db,
   flags=flags)` — `PublishFlags` first, then editorial gates, then
   `is_duplicate(content_hash)`.
4. Call `is_duplicate_publication(db, publication_content_hash)`. If True,
   abort with `publication_already_emitted` outcome (no second POST).
5. POST to the channel.
6. On success, `register_published(db, content_hash, published_url,
   platform, publication_content_hash=publication_content_hash)`.

Step 4 is the new, copy-grade idempotency. Step 3 is unchanged from #405.

## Integration with #405 stop button

`publish_guard.assert_can_publish(..., flags=flags)` already raises
`PublishBlockedError(flags.block_reasons())` BEFORE evaluating editorial
gates or touching the DB whenever `flags` is explicit and
`flags.allows_real_publish() is False`. #402 does NOT modify that order.
The publication-hash check sits AFTER the runtime flag check and AFTER the
existing 6 gates, in the publisher itself, NOT in `publish_guard`. The
guard is intentionally signal-grade; the publisher is publication-grade.

The integration test
`tests/discovery/test_publish_guard_publication_hash_integration.py`
verifies all four orderings:

1. `flags` blocking + duplicate publication → raises `PublishBlockedError`
   (flag check fires first, never reaches dedup).
2. `flags` allowing + duplicate publication → guard passes, publisher then
   blocks via `is_duplicate_publication`.
3. `flags` allowing + fresh copy → guard passes, publisher would proceed.
4. `flags=None` (legacy) + fresh copy → byte-identical to pre-#402.

## Carry-overs

* **#404-lite** must persist `publication_content_hash` AND
  `source_content_hash` on every `publish_log.jsonl` event, plus the
  `block_reasons` and `cross_validation` from `PublishFlags`. Field name
  `publication_content_hash` is canonical; `source_content_hash` mirrors
  the existing `content_hash` semantically.
* **#406** source-use policy must require `publication_content_hash` to be
  present on every `published_history` row before any LinkedIn / blog
  publish window opens. Until then, NULL is tolerated as a back-compat
  signal that the row was registered by a Wave 1.5 publisher.
* **Stage 7.5** is NOT modified. The publication hash is computed
  downstream of S7.5; S7.5 only produces the approved copy fields.

## What this contract does NOT solve

* No real publisher wiring (blog `umbralbim.cl`, LinkedIn).
* No daily-cap enforcement (waits for #404-lite).
* No automatic re-approval flow when copy edits flip the hash. The
  expectation is the editorial UI / Notion gates (`aprobado_contenido` +
  `autorizar_publicacion`) get reset by a Stage 9 invalidator hook in a
  later wave.
* No Notion writeback of `publication_content_hash`. It lives in SQLite
  for now; surfacing it on the Notion page is a Wave 2.B concern.
* No retroactive backfill of pre-#402 `published_history` rows.

## References

* `docs/editorial-pipeline/hash-contract.md` (signal hash family).
* `docs/editorial-pipeline/runtime-flags-contract.md` (runtime flags + stop
  button).
* `docs/audits/2026-05-10-wave2a-plan.md` (wave bundle and order).
* `scripts/discovery/lib/dedup.py` (signal hash impl + `published_history`
  helpers).
* `scripts/discovery/lib/publish_guard.py` (S10 6-gate guard).
