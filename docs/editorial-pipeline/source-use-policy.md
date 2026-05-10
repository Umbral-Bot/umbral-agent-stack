# Source Use Policy — RRSS Editorial Pipeline

> **Scope:** Wave 2.A doc-only. Defines policies for how external sources are
> ingested, attributed, and audited inside the RRSS editorial pipeline.
> Runtime enforcement lands in Wave 2.B.

## Purpose

Establish a single, reviewable contract for **what counts as an acceptable
external source** for the editorial pipeline (Stages 1 → 11), how each source
must be filtered, attributed, hashed, and logged, and who approves new
sources before they are wired into ingest.

This document is normative for any code path that calls out to the public
web on behalf of the pipeline. It is **not** a substitute for legal review
when ingesting copyrighted material at scale.

---

## 1. Source types

The pipeline accepts three classes of source. Anything outside this list
requires explicit human approval (see §6).

| Class            | Examples                                | Notes                                  |
|------------------|-----------------------------------------|----------------------------------------|
| RSS / Atom feeds | Vendor blogs, gov bulletins, journals   | Preferred. Stable, declared by source. |
| Web scraping     | HTML pages reachable via HTTPS          | Allowed only when no feed is offered.  |
| Authorized APIs  | Vendor APIs with token + ToS coverage   | Token must live in env, never repo.    |

### Out of scope (Wave 2.A)

- Social network scraping (Twitter/X, Instagram, Facebook, TikTok, LinkedIn
  feeds) — handled separately and requires platform ToS review.
- Paywalled / login-gated content — never bypassed.
- User-private channels (DMs, private Slack/Discord, private Notion).

---

## 2. Permissions and attribution

For every accepted source the pipeline records:

- `source_url` — canonical URL after redirect resolution.
- `source_domain` — eTLD+1 used by quota / dedup.
- `source_license` — one of: `public-domain`, `cc-by`, `cc-by-sa`,
  `permissive-tos`, `restricted`, `unknown`. `unknown` and `restricted`
  do **not** auto-publish; they go to human review.
- `source_attribution` — display string used downstream (publication body,
  citations, captions).
- `fetched_at` — UTC ISO-8601.

Attribution rules:

- Always attribute the original publisher, not the aggregator.
- Never strip author bylines if present in the source.
- For derivative pieces, link back to the canonical URL.

---

## 3. Filters before ingest

Every candidate must pass these filters before Stage 1 stores it. Failures
are logged to the ops log and dropped.

1. **Language allow-list** — default `["es", "en"]`. Configurable per source.
2. **Domain allow-list / deny-list** — explicit lists per pipeline run.
3. **`robots.txt` compliance** — fetch path must be allowed for our user
   agent; the user agent must identify the project and contact email.
4. **Content-type** — only `text/html`, `application/xhtml+xml`,
   `application/rss+xml`, `application/atom+xml`, `application/json` (for
   APIs). Binary downloads require explicit handling.
5. **Size cap** — discard responses above the configured byte cap.
6. **Charset** — require declared charset; treat undeclared as UTF-8 and
   flag for human review if that fails.

Sources that intermittently fail filters are degraded, not silently retried
forever. Repeated failures escalate to human review.

---

## 4. Relationship with hashes

The pipeline uses two distinct content hashes; they are governed by
[hash-contract.md](./hash-contract.md). This policy only summarizes the
relationship.

- **`source_content_hash`** (Stages 1–2): SHA-256 over the **normalized
  source body** at fetch time. Used for dedup against prior fetches and
  to detect upstream changes between runs.
- **`publication_content_hash`** (#410, Stage 10): SHA-256 over the
  **rendered publication payload** about to be sent to a channel. Used by
  the publish kill-switch and `publish_log` to enforce idempotency.

Invariant: `source_content_hash` is computed **before** any rewrite,
translation, or rendering. `publication_content_hash` is computed **after**
all transforms, immediately before send.

A change in `source_content_hash` does not automatically trigger
republication; that requires re-running the editorial path and producing a
new `publication_content_hash`.

---

## 5. Sources that require human review (never auto-ingest)

The pipeline must refuse, and route to human review, any source matching:

- Domains on the deny-list (set in `config/`, Wave 2.B).
- Content classified as: medical advice, legal advice, financial advice
  presented as recommendation, political campaign material, or material
  about identifiable private individuals.
- Content whose license string resolves to `restricted` or `unknown`.
- Content gated by login, paywall, captcha, or DRM.
- Content whose `robots.txt` disallows our user agent for the requested
  path.
- Mirrors / scrapers of paywalled originals.

Refusal is a non-error: the candidate is logged with reason and dropped.

---

## 6. Approval workflow for new sources

New sources are not added by the pipeline at runtime. The flow is:

1. Proposal opened (issue or task page) with: domain, source type,
   license claim, sample URL, expected volume, language(s).
2. **David approves** the source explicitly. No source is added without
   his sign-off.
3. Source is added to the configured allow-list (Wave 2.B introduces the
   config file path).
4. First production run is observed for at least one full cycle before
   the source is treated as stable.

Removing a source is reversible and does not require approval — anyone
on call may remove a misbehaving source and open a follow-up.

---

## 7. Audit: how each fetch is logged

Every outbound fetch on behalf of the pipeline writes one structured
record to `OPS_LOG_PATH` (see
[secrets-and-tokens.md](../runbooks/secrets-and-tokens.md) for the
variable). Minimum fields:

- `event` — e.g. `source.fetch`, `source.skip`, `source.refused`.
- `source_url`, `source_domain`.
- `http_status`, `bytes`, `duration_ms`.
- `source_content_hash` (when body was kept).
- `filter_failed` (when applicable): which filter rejected it.
- `user_agent`, `requested_at`, `fetched_at`.
- `run_id` — correlates with the editorial run.

No request bodies and no response bodies are logged. The hash is the
canonical evidence of "what we fetched."

---

## 8. What is deferred to Wave 2.B

The following are intentionally **out of scope** for this doc-only PR and
will land with runtime in Wave 2.B:

- Concrete allow-list / deny-list config files and loader.
- User-agent string and contact endpoint.
- `robots.txt` cache and TTL policy.
- Concrete byte / time caps.
- License-classifier implementation.
- Wiring of `source.fetch` events into the ops log writer.
- Tests covering each filter from §3 and each refusal reason from §5.

Until Wave 2.B is merged, any pipeline path that fetches external content
must run with `DRY_RUN=true` (see secrets/tokens runbook).
