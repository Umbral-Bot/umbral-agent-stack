# Stage 2 — Source Verification Smoke Run

**Date:** 2026-05-08
**Branch:** `copilot/feat-s2-source-verification`
**Module:** `scripts.discovery.stage2_verify_sources`
**Mode:** real HTTP probe (HEAD + GET fallback), `follow_redirects=True`, timeout 8s, retries `(1.0s, 3.0s)`.

## Why this run

The smoke run exercises every status in the Stage 2 enum end-to-end against
real network targets so we can confirm the classifier matches the spec
before any downstream stage (S5, S10) wires the contract.

## Signals probed

| id | URL |
|---|---|
| g1 | `https://www.storytellingwithdata.com/blog/swdchallenge-human-ai` |
| g2 | `https://github.com/python/cpython` |
| g3 | `https://arxiv.org/abs/2401.12345` |
| r1 | `https://buildingsmart.org` |
| f1 | `https://github.com/this-org-does-not-exist-zzz/repo-zzz` |
| f2 | `https://www.storytellingwithdata.com/blog/this-post-does-not-exist-2026` |
| p1 | `https://httpbin.org/status/402` |
| p2 | `https://httpbin.org/status/410` |
| t1 | `https://10.255.255.1/never` (RFC 5737-style unreachable) |
| b1 | `not-a-url` (malformed) |
| b2 | `https://httpbin.org/status/503` |
| b3 | `https://example.invalid/x` (invalid TLD) |

## Verdicts

| id | status | http | paywall | canonical | error |
|---|---|---|---|---|---|
| g1 | ok | 200 | 0 | `https://www.storytellingwithdata.com/blog/swdchallenge-human-ai` | — |
| g2 | ok | 200 | 0 | `https://github.com/python/cpython` | — |
| g3 | ok | 200 | 0 | `https://arxiv.org/abs/2401.12345` | — |
| r1 | redirect | 200 | 0 | `https://www.buildingsmart.org/` | — |
| f1 | 404 | 404 | 0 | `https://github.com/this-org-does-not-exist-zzz/repo-zzz` | — |
| f2 | 404 | 404 | 0 | `https://www.storytellingwithdata.com/blog/this-post-does-not-exist-2026` | — |
| p1 | paywall | 402 | 1 | `https://httpbin.org/status/402` | — |
| p2 | 410 | 410 | 0 | `https://httpbin.org/status/410` | — |
| t1 | timeout | None | 0 | `https://10.255.255.1/never` | `timeout:ConnectTimeout` |
| b1 | blocked | None | 0 | `not-a-url` | `malformed_url` |
| b2 | blocked | 503 | 0 | `https://httpbin.org/status/503` | — |
| b3 | blocked | None | 0 | `https://example.invalid/x` | `transport:ConnectError:[Errno -2] Name or service not known` |

## Summary

```json
{"ok": 3, "redirect": 1, "404": 2, "410": 1, "paywall": 1, "timeout": 1, "blocked": 3}
```

Spec acceptance criteria — **met**:

* ≥ 10 real signals: ✅ (12).
* ≥ 1 of each: `ok` ✅, `redirect` ✅, `404` ✅, `paywall` ✅.
* Bonus coverage: `410` ✅, `timeout` ✅, `blocked` ✅, malformed URL ✅, DNS failure ✅.
* Retry budget honored on `t1` (timeout after `(1.0s, 3.0s)` backoff).
* Canonical URL resolution after redirect verified on `r1`
  (`buildingsmart.org` → `www.buildingsmart.org`).
* All `content_hash` / `idempotency_key` values were 64-char sha256 hex
  digests (verified during persistence — `signals_verified` row present
  for every signal).
