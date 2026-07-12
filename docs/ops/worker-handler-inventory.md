# Worker handler inventory — static-orphan set b0004

Date: 2026-07-12
Baseline: `umbral-agent-stack@29897de3` (`117` keys in `TASK_HANDLERS`)

This page consumes the b0003 finding (`117 registered / 108 statically
referenced / 9 registered-only`) and closes the omitted name. It is not a new
full Worker audit.

## Method and scope

A **static invoker** is executable repository code or an OpenClaw tool bridge
that dispatches the task. The registry entry, handler implementation, tests,
runbooks, and authorization-only lists such as `config/client_tiers.yaml` do
not count as invokers. They are still retained below as evidence that a
contract exists.

The b0003 deposit named eight members (`web.*` and `client.*`) but did not list
the ninth. Applying the same bounded criterion reconstructs the ninth as
`google_drive.upload_presentation`: its only occurrences outside the registry
are its implementation, focused tests, and documentation. The current PIT
flow instead calls `document.create_presentation` and
`google_drive.upload_file` separately.

## Complete registered-only set

| Handler | Registered | Static invoker outside registry/tests/docs/policy | Contract evidence | Verdict |
|---|---:|---:|---|---|
| `web.publish_editorial_post` | yes | no | Handler tests; Azure editorial ADR/runbook; manual Worker call is the production entry point. | **KEEP** — externally/manual-invoked by design. |
| `web.unpublish_editorial_post` | yes | no | Handler tests; Azure rollback runbook; CAND-001 closeout records real use. | **KEEP** — rollback surface with operational evidence. |
| `client.register` | yes | no | Direct handler and security tests; blocked for non-admin tiers in `client_tiers.yaml`. | **DOCUMENT** — internal admin API; no in-repo admin CLI. |
| `client.revoke` | yes | no | Direct handler and security tests; admin-only tier policy. | **DOCUMENT**. |
| `client.rotate_key` | yes | no | Direct handler and security tests; admin-only tier policy. | **DOCUMENT**. |
| `client.list` | yes | no | Direct handler and security tests; admin-only tier policy. | **DOCUMENT**. |
| `client.usage` | yes | no | Direct handler and security tests; admin-only tier policy. | **DOCUMENT**. |
| `client.get` | yes | no | Direct handler and security tests; admin-only tier policy. | **DOCUMENT**. |
| `google_drive.upload_presentation` | yes | no | `tests/test_google_drive_upload.py`; convenience wrapper builds and uploads in one call. PIT currently uses the two underlying handlers separately. | **DOCUMENT** — retain until external-use evidence is available. |

No handler receives **DEPRECATE** in this pass. Static silence alone does not
prove zero external use for a Worker task API, so no deprecation comment or
registry removal is justified. A future deprecation requires runtime/task-log
evidence and a migration window.

## D-13 collateral: document handlers (read-only)

| Handler | Implementation exists | Focused test | Static reference | Result |
|---|---:|---|---|---|
| `document.create_word` | yes — `worker/tasks/document_generator.py` | yes — `tests/test_document_generator.py` | yes — executable bridge `openclaw/extensions/umbral-worker/index.ts` plus the `document-generation` skill | **KEEP** |
| `document.create_pdf` | yes — `worker/tasks/document_generator.py` | yes — `tests/test_document_generator.py` | yes — executable bridge `openclaw/extensions/umbral-worker/index.ts` plus the `document-generation` skill | **KEEP** |
| `document.create_presentation` | yes — `worker/tasks/document_generator.py` | yes — `tests/test_document_generator.py` | yes — executable bridge; direct imports from `worker/tasks/google_drive.py` and `scripts/pit/pit_build_outcome_deck.py` | **KEEP** |

All three are registered and tested. D-13 therefore has no missing Worker
handler; any capitalisation gap is upstream/downstream orchestration, not
absence of document generation code.
