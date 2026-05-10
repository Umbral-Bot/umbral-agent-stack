# Stage 2 — Source Verification & Dedup (Hilo 3 / wave1)

> **Status:** DRAFT — DO NOT MERGE (waiting for Hilo 4 + Hilo 6 to wire the contract). Author: Copilot-VPS.

## Purpose

Stage 2 is the **single gatekeeper** between raw discovery (S0–S1) and ranking
(S5). Before any signal is scored, we must answer three questions
deterministically:

1. **Is the source real?** (HTTP probe with retries.)
2. **What is its canonical URL?** (Resolve redirects + `<link rel="canonical">`.)
3. **Have we ever published its content before?** (Stable `content_hash`.)

The output is consumed by S5 (rank), S10 (publish), and any future
republication guard. S10 MUST call `is_duplicate(content_hash)` before
shipping a post and MUST call `register_published(content_hash, url, platform)`
after a successful publish.

## Inputs

`signals_raw` (owned by Hilo 2 — see `migrations/0001_referentes_signals.sql`):

| column | type | notes |
|---|---|---|
| `signal_id` | INTEGER PK AUTOINCREMENT | |
| `url` | TEXT | source URL captured at ingest |
| `title` | TEXT | best-effort at ingest |
| `excerpt` | TEXT | best-effort at ingest |
| `source_status` | TEXT | **Hilo 2 ingest status** — NOT the same enum as Stage 2 |
| `dedup_hash` | TEXT UNIQUE | Hilo 2 ingest-level dedup, not used by Stage 2 |

Stage 2 does **not** mutate `signals_raw`. It only reads.

## Outputs

`signals_verified` (owned by Stage 2 — see `migrations/0002_signals_verified_published_history.sql`):

| column | type | notes |
|---|---|---|
| `signal_id` | INTEGER PK | FK → `signals_raw.signal_id` |
| `canonical_url` | TEXT NOT NULL | redirect-resolved + `<link rel=canonical>` |
| `source_status` | TEXT NOT NULL | enum below |
| `content_hash` | TEXT NOT NULL | sha256 |
| `idempotency_key` | TEXT NOT NULL | sha256 |
| `paywall_detected` | INTEGER NOT NULL DEFAULT 0 | 0/1 |
| `verified_at` | TEXT NOT NULL | ISO-8601 UTC |
| `http_status` | INTEGER | nullable |
| `final_url` | TEXT | post-redirect |
| `error` | TEXT | empty when probe succeeded |

`published_history` (owned by `lib/dedup`):

| column | type |
|---|---|
| `content_hash` | TEXT PK |
| `published_url` | TEXT NOT NULL |
| `published_at` | TEXT NOT NULL |
| `platform` | TEXT NOT NULL |

## `source_status` enum

| value | condition |
|---|---|
| `ok` | final 2xx, host unchanged, no paywall heuristic hit |
| `redirect` | final 2xx but cross-host redirect |
| `404` | final response 404 |
| `410` | final response 410 |
| `paywall` | HTTP 402 OR paywall keyword OR `<500` visible chars |
| `timeout` | transport-level timeout after retries |
| `blocked` | other 4xx/5xx, malformed URL, or transport error other than timeout |

## HTTP policy

* HEAD first; fallback to GET on 405/403/501 or any HTTPError.
* Default timeout: **10s**.
* Retry budget: **2 retries** with backoffs `(1.0s, 3.0s)` → up to 3 attempts.
* `User-Agent`: `umbral-stage2-verify/1.0 (+https://umbral.bot)`.
* `follow_redirects=True`.

## Paywall heuristic

A response is paywall iff **any** of:

* `status_code == 402`
* body contains any of `DEFAULT_PAYWALL_KEYWORDS` (case-insensitive)
* visible-text length `< 500` chars (script/style stripped)

This is intentionally conservative — it flags, it does not blacklist. S5 may
deprioritize paywall sources but is free to keep them.

## Hash policy

```
content_hash    = sha256(canonical_url.strip() + "\n" +
                         normalize_text(title) + "\n" +
                         normalize_text(excerpt))
idempotency_key = sha256(canonical_url.strip() + "\n" + content_hash)
```

`normalize_text` = lowercase + strip + collapse whitespace. Two distinct URLs
sharing the exact title+excerpt collide on `content_hash` on purpose — that
is the duplicate signal we want.

## Public API for downstream stages

```python
from scripts.discovery.lib.dedup import (
    compute_content_hash,
    compute_idempotency_key,
    is_duplicate,
    register_published,
)
```

| caller | usage |
|---|---|
| S5 (rank) | read `signals_verified.source_status` — drop `404`, `410`, `blocked`; soft-deprio `paywall` |
| S10 (publish) | **before** publishing: `if is_duplicate(conn, content_hash): skip`. **after** publishing: `register_published(conn, content_hash, published_url, platform)` |

## CLI

```
python -m scripts.discovery.stage2_verify_sources \
    [--db PATH] [--batch N] [--dry-run] [--retry-failed] [--verbose]
```

Prints a JSON summary to stdout: `{processed, by_status, paywalls, dry_run}`.
With `--verbose`, one verdict JSON per line is emitted before the summary.

## Compatibility constraints

* `scripts/discovery/source_verifier.py` (legacy, consumed by
  `stage7_5_copy_writer.py`) MUST remain untouched. Stage 2 lives in a
  new module; legacy verifier keeps its own SQLite cache and contract.
  See `tests/discovery/test_source_verifier_compat.py`.

## Open coordination items

* **Hilo 2** — `signals_raw.dedup_hash` is ingest-level. Stage 2's
  `content_hash` operates on the canonical URL post-probe and is the one
  S10 must consult. If Hilo 2 ever wants to align them, agree on
  hash inputs first.
* **Hilo 4** — when adding a `idempotency_key` field to the
  📰 Publicaciones writer, source the value from
  `signals_verified.idempotency_key` rather than recomputing.
* **Hilo 6** — S10 is contractually required to call
  `is_duplicate(content_hash)` and `register_published(...)`.
