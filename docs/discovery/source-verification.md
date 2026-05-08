# Stage 7.5 — Pre-LLM Source Verification Gate

> Status: **active** (introduced 2026-05-08, branch `rick/stage7_5-source-verify`).
> Owner: `Copilot-VPS`.
> Scope: blocks copy generation against suspect or unreachable sources **before**
> the OpenClaw call so we never spend tokens or write Notion content on top of
> a dead/sandbox/blocklisted URL.

## 1. Threat model

Stage 7.5 turns a discovered article into a LinkedIn-ready copy that gets
written to the Notion database **Publicaciones**. Each post carries a
`Fuente: <URL>` line that David's audience may click. Failure modes we want to
avoid:

| Risk                              | Manifestation                                                  | Why we block                                                                 |
|-----------------------------------|----------------------------------------------------------------|------------------------------------------------------------------------------|
| Sandbox / placeholder URLs        | `example.com`, `*.test`, `*.invalid`                          | Brand risk + dead links surfaced to David's network.                         |
| Dead links                        | HTTP 4xx / 5xx / DNS failure                                   | Reader experience; Stage 7.5 should fail closed instead of publishing junk.  |
| Redirect spam / domain swap       | Origin host A → final host B                                   | Hijacked URLs and link laundering.                                           |
| Wrong content type                | `application/octet-stream`, `image/*`                          | Not a real article; LLM cannot summarise it.                                 |
| Malformed arXiv URLs              | `/abs/foo` or future-dated identifiers                         | Common scraper artefact; cheaper to reject early.                            |
| Fresh / unknown domain            | First time we see this host                                    | Soft signal — only warns when combined with a thin body.                     |

The gate runs **before** prompt construction and the OpenClaw call. It is a
separate process from the editorial evaluator (`eval_stage7_5_copy.py`), but
the same verdict is also enforced as **R17** at evaluation time so a bad
source cannot slip through if the gate is bypassed.

## 2. Rules

Hard rules (any one fails → process blocked, status `failed_source_unverified`):

| Reason                       | Trigger                                                         |
|------------------------------|-----------------------------------------------------------------|
| `empty_url`                  | URL missing or whitespace-only.                                 |
| `malformed_url`              | URL parse failure or non-`http(s)` scheme.                      |
| `blocklist_tld`              | Host TLD ∈ `{.test, .invalid, .local, .example}`.               |
| `blocklist_domain`           | Registrable suffix ∈ blocklist (`example.com`, `localhost`, …). |
| `arxiv_malformed`            | arXiv host but path ≠ `^/abs/\d{4}\.\d{4,5}(v\d+)?/?$`.         |
| `arxiv_year_out_of_range`    | arXiv year < `arxiv_min_year` or > current year + offset.       |
| `http_unreachable`           | Network/transport error, DNS failure, timeout.                  |
| `http_<status>`              | HEAD/GET returned 4xx or 5xx.                                   |
| `redirect_domain_change`     | Final URL host ≠ origin host (registrable suffix compared).     |
| `redirect_to_<reason>`       | Redirect lands on another blocklisted/malformed target.         |
| `content_type_rejected`      | Response `Content-Type` ∉ allowed set.                          |

Soft warnings (do **not** block):

| Warning           | Trigger                                                          |
|-------------------|------------------------------------------------------------------|
| `new_domain`      | Domain unseen for `warning_new_domain_days`, body is short, host not in allowlist. |
| `missing_title`   | HTML response without parseable `<title>`.                       |
| `short_body`      | Body content shorter than `short_body_min_chars`.                |

## 3. Configuration

`config/source_verifier.yaml` (loaded via `load_config(path)` — falls back to
defaults if file is missing):

```yaml
blocklist_domains: [example.com, example.org, example.net, localhost, placeholder.test]
blocklist_tlds:    [.test, .invalid, .local, .example]
allowlist_high_trust:  # 15 entries — arxiv.org, autodesk.com, ieee.org, …
warning_new_domain_days: 180
arxiv_min_year: 2020
arxiv_max_year_offset: 1
short_body_min_chars: 400
allowed_content_types: [text/html, application/xhtml+xml, application/pdf]
http_timeout_s: 10.0
http_retries: 1
```

The high-trust allowlist suppresses the `new_domain` warning. It is
intentionally narrow — adding a host requires a written justification in the
PR description.

## 4. Cache

- Backend: SQLite at `~/.cache/rick-discovery/source_verification.sqlite`.
- Key: full URL (post-trim, pre-redirect).
- TTL: 7 days. Expired rows are ignored on read; the next call re-probes and
  overwrites.
- Schema is **self-healing**: if the table exists with an older column set,
  `_ensure_cache` drops and recreates it (cache is non-authoritative).
- Both `cache_get` and `cache_put` swallow `sqlite3.Error` — verification
  must succeed even if the cache is unwriteable.

ops_log emits `stage7_5.source.cache_hit` whenever a cached verdict is
returned.

## 5. Hook into `stage7_5_copy_writer.py`

`process_proposal` runs the gate immediately after the
`skipped_existing_copy` short-circuit and **before** prompt assembly:

1. Resolve URL from page properties (`Fuente primaria`, then
   `Fuente referente`, then proposal `fuentes_urls[0]`).
2. Call `source_verifier.verify_source(url)`.
3. If `verdict["ok"] is False` → mark proposal `failed_source_unverified`,
   log `stage7_5.source_blocked`, return without calling the LLM.
4. If the verifier module fails to import → log
   `stage7_5.source_verifier_unavailable` and proceed (fail-open only on
   missing module — every other failure is fail-closed).
5. If `verify_source` itself raises → mark proposal
   `failed_source_unverified` with reason `source_verifier_crash`.

### Dev override

`--skip-source-verify` (CLI flag on `stage7_5_copy_writer.py`) bypasses the
gate entirely. **Use only for local debugging.** It does not bypass R17 in
the evaluator unless the fixture also sets `fixture_skip_source_verify=true`.

## 6. R17 in the evaluator

Hard rule **R17 — `Source URL verified`** in `eval_stage7_5_copy.py`:

- Extracts the first URL via `URL_RE` from the rendered copy (or
  `fixture["source_url"]` fallback).
- Calls `verify_source` and hard-fails the rule if `ok=False`.
- Fixture flag `fixture_skip_source_verify=true` short-circuits with PASS.
  Required for canned fixtures that intentionally use sandbox URLs.

## 7. ops_log events

| Event                                  | When                                                                |
|----------------------------------------|---------------------------------------------------------------------|
| `stage7_5.source.cache_hit`            | Verdict returned from cache.                                        |
| `stage7_5.source.verified`             | Fresh probe succeeded (ok=True, no warnings).                       |
| `stage7_5.source_warnings`             | ok=True with one or more soft warnings.                             |
| `stage7_5.source_blocked`              | Hard-block emitted (gate or verifier crash).                        |
| `stage7_5.source_verifier_unavailable` | Module import failed; pipeline fell open.                           |

## 8. Manual smoke

```bash
source .venv/bin/activate
python scripts/discovery/source_verifier.py "https://arxiv.org/abs/2024.12345"
python scripts/discovery/source_verifier.py "https://example.com" || true
python scripts/discovery/source_verifier.py "https://this-domain-does-not-exist-zzz.test" || true
# Re-run arxiv to demonstrate cache hit:
python scripts/discovery/source_verifier.py "https://arxiv.org/abs/2024.12345"
tail ~/.config/umbral/ops_log.jsonl | jq 'select(.event | startswith("stage7_5.source"))'
```

## 9. Rollback

The gate is purely additive:

1. Pass `--skip-source-verify` on the Stage 7.5 CLI for an emergency unblock.
2. Or revert this PR — `process_proposal` reverts to its pre-gate path, R17
   disappears from `HARD_RULES`, and existing fixtures keep passing because
   `fixture_skip_source_verify` is silently ignored on older eval code.
