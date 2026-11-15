# ADR11 follow-up: durable review and existing-page detection

Status: proposal / not deployed. 2026-11-15. Branch: codex/adr11-raw-reconcile-review-20261115.

## Evidence inspected
- worker/tasks/granola.py: matching ladder and raw upsert guard.
- worker/notion_client.py query_database: cursor pagination, exceptions propagate. Does not validate has_more/next_cursor consistency or cursor repetition.
- scripts/vm/granola_drive_feeder.py run_item: performs dry-run, verifies identity agreement, then optionally calls worker again. Only noop short-circuits; defer can produce a redundant execute request (worker still blocks writes).
- Feeder main writes per-run run-<timestamp>.json after each item with write_text. This is a run report, not an atomic deduplicated durable review queue. Review reason/flag is not copied into the row.
- infra/ops_logger.py OpsLogger._write: append-only JSONL, catches and logs persistence exceptions. Not an acknowledged durable review store.

## Offline evidence
Current branch preservation suite: 7 tests / 13 scenarios pass using exact production function AST with external dependencies mocked.
Additional exact production matching helpers tested locally with synthetic data: exact document ID, distinct document IDs with identical title/date, unique legacy title/date, two ambiguous legacy matches, duplicate exact IDs. Five characterization assertions pass.
Ambiguous legacy matches currently return no match, which can lead to creation. Duplicate exact IDs select a ranked page rather than surfacing ambiguity. Existing guard preserves any matched page but does not solve these cases or concurrent create races.

## Minimum staged proposal
1. Extend feeder report row with explicit review_required and stable reason from worker; short-circuit defer before second call. This makes reports truthful but MUST NOT claim durable queue delivery.
2. Before allowing creation, require complete read coverage and explicit no-match; ambiguous candidates or inconsistent pagination must defer. Keep distinct stable document IDs distinct. Do not globally change shared query helper without regression coverage.
3. For durable review, agree owner and existing state location first. Use a unique review key (source identity + incoming content hash + reason), page IDs and status only; no transcript or title copies. Acknowledge persisted only after an atomic committed write. Do not turn failures into success. No automatic notification or approval-to-write behavior.
4. Cross-process creation requires uniqueness/reservation in an agreed durable backend, not an in-process lock or an extra query. Define crash/retry recovery and uncertain-create reconciliation before enabling.

## Integration gaps before merge
The historical tests/test_granola_transcript_reconciliation.py contains expectations of in-place replacement in test_partial_then_full_reconciles_same_page and test_legacy_page_without_document_id_can_still_match_by_title_date. Adapt these assertions to defer while preserving identity, then run full existing reconciliation and feeder suites with all transports mocked.
No full repository test suite was run here; AST tests do not prove imports/config/deployment integration.
Need tests for incomplete pagination, repeated cursor, duplicate IDs, ambiguous fallback, concurrent creates, store failures and process restart. Do not silently convert ambiguous absence into new-page creation.

## Boundary
No new durable store, runtime writer, notification, permission change, merge or deployment implemented. review_required remains returned metadata, not a persisted review request. Main and live Notion untouched.
