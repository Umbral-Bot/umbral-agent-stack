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

## Review-branch update: strict lookup implemented (not deployed)
This section supersedes the earlier matching/pagination and historical-test gaps.
- New query_database_with_coverage returns explicit complete/results/reason. Missing/inconsistent pagination, repeated cursors, malformed/duplicate page IDs, read failures and 1000-page bound return incomplete with no partial results.
- Existing query_database implementation and its callers remain unchanged; only raw ingestion uses the new API.
- Raw caller returns defer/raw_lookup_incomplete without writes or notifications on incomplete coverage.
- Multiple candidates at a matching tier return ambiguous rather than a ranked winner or absence; raw caller returns defer/raw_match_ambiguous. Distinct document IDs still do not match through title/date fallback.
- Historical reconciliation tests now expect preserved existing pages and explicit review.
- Offline checks: 20 historical methods pass with external imports stubbed; 7 preservation tests and 8 detection/caller tests pass. New tests wire exact strict-query and matching functions through the real handler with fake transport; no network/live data.
- Full pytest/import/config integration and all other consumers' test fixtures still require regression review. No claim of full suite green.
- A complete query is not a snapshot or a distributed creation lock: concurrent creates, changes after query and unmatched identity variants remain unresolved. No durable review queue or automatic correction implemented.

## Round-trip and conservative no-op review
Latest isolated regression: 22 historical methods (includes schema overrides and create/query/detect/no-op round-trip), 7 preservation tests and 11 detection/caller tests pass. External imports/transports remain substituted; no full pytest/config integration claim.
The historical mock now honors schema=None versus an explicit empty schema. Round-trip uses the actual write payload to construct the subsequent queried page, adding only server property-type annotations; identity and metrics are not independently fabricated. The second ingest identifies the same page and returns noop with zero writes.
A malformed neighboring row or insufficient schema can defer the whole scan BEFORE a valid existing page's no-op is evaluated. This is intentional fail-closed behavior: no-op is preserved only after complete trustworthy coverage and usable schema/identities. It may stop otherwise harmless ingests until data is reviewed. No automatic repair/delete, widening of permissions, or silent exception for legacy rows.

## Legacy fallback regression and full-suite route
23 historical methods now pass in the isolated harness. New legacy round-trip omits document ID and source URL, persists title + accented date + trace metrics, then detects exact_title_date/noop on repeat with task-writing and notification flags enabled: zero downstream task/comment calls.
Local full suite is NOT complete: this workspace has selected source files, no full checkout/test dependencies and no pytest installation. Official .github/workflows/test.yml runs pytest tests/ on Python 3.11/3.12, triggered only by push main or a PR targeting main. It has no deployment step or workflow_dispatch. Do not push main to trigger it; a reviewed PR is the appropriate route. No PR/CI dispatch was initiated by this change.

## Persistence/concurrency recommendation (proposal only)
Inspected existing infra:
- dispatcher/notion_poller.py uses Redis SET NX with expiry for processed comments. Useful claim pattern, but expiry alone cannot guard an uncertain Notion creation or durable human review.
- Editorial SQLite is explicitly scoped to sequential discovery stages; docs/editorial-pipeline/sqlite-policy.md and scripts/discovery/lib/sqlite_utils.py document commits/migrations and busy_timeout. Do not reuse its production DB/schema for Granola.
- OpsLogger and feeder per-run JSON remain evidence breadcrumbs, not acknowledged review storage.

Recommend one canonical ingestion writer with an explicitly approved durable registry location and owner. For a single host, an isolated SQLite registry using unique source keys and committed transactions is the smallest option; multiple hosts require a shared transactional authority, not per-host SQLite files. Do not claim the existing Redis deployment has proven persistence/backup guarantees without operator evidence.

Two separate records: (1) source reservation keyed by stable upstream document identity, (2) review item keyed by source identity + incoming content hash + reason. Store IDs/hashes/status/timestamps only, no transcript/title body. Legacy title/date is a matching aid, not a globally unique reservation key; ambiguous/no stable identity goes to review.
States: prepared -> attempting -> verified, or uncertain/review_required. Commit attempting before sending a creation; after a lost response, leave uncertain and reconcile read-only, never auto-expire into a second create. A unique registry row coordinates our writers but cannot stop unrelated Notion writers. Operator must define backup, restore, retention, ownership and outage behavior before integration.
Before activation, test two processes claiming the same identity, crash before/after request, successful Notion write plus lost response, registry unavailable/full disk, restart and restore. No store, migration, lease, notification or live writer was created here.
