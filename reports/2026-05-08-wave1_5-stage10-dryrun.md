# Wave 1.5 — Stage 10 Dry-Run (3 synthetic scenarios)

> **Branch:** `wave1.5-integration` · **Date:** 2026-05-08 · **Operator:** Copilot-VPS
> **Source of truth:** [tests/discovery/test_stage9c_dry_run.py](../tests/discovery/test_stage9c_dry_run.py)
> **Cross-reference (H6 audit):** [reports/2026-05-08-stage10-dry-run-audit.md](2026-05-08-stage10-dry-run-audit.md)

The 3 dry-run scenarios required by the Wave 1.5 task brief are encoded as
the first 3 tests in `test_stage9c_dry_run.py`. They run on the integrated
branch with `gates`, `dedup` and `publish_guard` all real (no lazy
fallback — see report §10), and assert that no `httpx.Client` is
instantiated during the dry run.

| # | Scenario | Test | Expected | Actual |
|---|---|---|---|---|
| 1 | SYN-pass — all 6 gates green | `test_dry_run_all_gates_ok_would_publish_true` | `would_publish=true`, no POST | **PASSED** |
| 2 | SYN-blocked-gate — `aprobado_contenido=False` | `test_dry_run_gate_failing_would_publish_false` | `would_publish=false`, `reasons=[aprobado_contenido_missing]`, no POST | **PASSED** |
| 3 | SYN-blocked-dup — `content_hash` already in `published_history` | `test_dry_run_duplicate_content_hash_blocks` | `would_publish=false`, `reasons=[contenido_duplicado]`, no POST | **PASSED** |

Companion safety test:

| # | Scenario | Test | Result |
|---|---|---|---|
| 4 | No literal POST URL hardcoded outside dry-run guard | `test_no_hardcoded_linkedin_post_urls` | **PASSED** |

## Run output

```
$ PYTHONPATH=. python -m pytest tests/discovery/test_stage9c_dry_run.py -v
tests/discovery/test_stage9c_dry_run.py::test_dry_run_all_gates_ok_would_publish_true PASSED
tests/discovery/test_stage9c_dry_run.py::test_dry_run_gate_failing_would_publish_false PASSED
tests/discovery/test_stage9c_dry_run.py::test_dry_run_duplicate_content_hash_blocks PASSED
tests/discovery/test_stage9c_dry_run.py::test_no_hardcoded_linkedin_post_urls PASSED
4 passed in 0.50s
```

## Why we did not invoke the CLI directly with `--proposal-id`

The task brief sketched commands like
`python -m scripts.discovery.stage9c_linkedin_publish --dry-run --proposal-id <SYN-pass>`,
but the actual CLI surface in H6 does not accept `--proposal-id`. The
real CLI flags are `--state-db`, `--max-posts`, `--dry-run`,
`--author-urn`, `--tokens-path`. Synthetic proposal scenarios are
exercised through the test harness (which seeds the SQLite state DB and
the Notion-page fixtures directly), not through CLI flags. The harness
gives us what the brief asked for: pass / blocked-by-gate /
blocked-by-dup verification with **0 real HTTP** and **0 LinkedIn POST**.

## What is *not* covered by this dry-run

- No live LinkedIn token refresh (`--tokens-path` is not set).
- No live Notion fetch of a real proposal page (`notion_fetcher` is mocked
  with `lambda pid: {"id": pid}` in the harness).
- No publish to `published_history` with a real content hash from a real
  proposal — synthetic hashes only.

These are intentional scope cuts: Wave 1.5 is integration verification,
not a Stage 10 deployment rehearsal. Stage 10 deployment rehearsal is a
separate Wave-2 task.
