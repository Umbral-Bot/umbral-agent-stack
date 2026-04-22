# Publish Tracking

Structured telemetry for publication attempts across Ghost, LinkedIn, X,
and manual channels.  **This layer does not publish anything.** It only
records attempt / success / failed events so future adapters have a
ready-made audit trail and idempotency surface.

## What this does

- Classifies publication events into three states: `publish_attempt`,
  `publish_success`, `publish_failed`.
- Normalizes channel names to a stable taxonomy: `ghost`, `linkedin`,
  `x`, `manual`, `unknown`.
- Computes a deterministic `content_hash` (SHA-256, 16 hex chars) so
  the same content always produces the same hash.
- Derives an `idempotency_key` from `channel + content_hash +
  notion_page_id` — usable for dedup in future publish adapters.
- Strips sensitive fields (`token`, `secret`, `api_key`, `password`,
  etc.) from metadata and extra kwargs.
- Truncates long fields to prevent log bloat.
- **Never stores full post content.**

## Files

| File | Purpose |
|------|---------|
| `infra/publish_tracking.py` | Core module: normalize, hash, build records, sanitize |
| `infra/ops_logger.py` | Extended with `publish_attempt()`, `publish_success()`, `publish_failed()` |
| `scripts/publish_tracking_demo.py` | CLI: generate demo events (dry-run or write to log) |
| `tests/test_publish_tracking.py` | Unit + integration tests |

## Usage

### Dry-run (default, no log writes)

```bash
python scripts/publish_tracking_demo.py
```

Output:
```
  [->] ghost: publish_attempt (hash=e4c9b27a)
  [OK] ghost: publish_success (hash=e4c9b27a)
  [->] linkedin: publish_attempt (hash=3f7c12d8)
  [XX] linkedin: publish_failed (hash=3f7c12d8) error=auth_expired
  [OK] manual: publish_success (hash=9a1b5e2f)
  [->] unknown: publish_attempt (hash=f0d3c8e1)

6 demo events generated (dry-run, no log written).
```

### JSON output

```bash
python scripts/publish_tracking_demo.py --json
```

### Write to OpsLogger

```bash
python scripts/publish_tracking_demo.py --write-ops-log
```

## How future adapters will use this

When a real Ghost/LinkedIn/X adapter is implemented, the flow is:

1. **Before calling the platform API:**
   ```python
   ops_log.publish_attempt(
       channel="ghost",
       content_hash=compute_content_hash(post_body),
       notion_page_id=page_id,
       publication_id=pub_id,
   )
   ```

2. **On platform confirmation:**
   ```python
   ops_log.publish_success(
       channel="ghost",
       content_hash=content_hash,
       platform_post_id=ghost_post_id,
       publication_url=post_url,
   )
   ```

3. **On failure:**
   ```python
   ops_log.publish_failed(
       channel="ghost",
       content_hash=content_hash,
       error_kind="api_error",
       error_code="422",
       retryable=True,
   )
   ```

## Relation to Notion `content_hash`

The `content_hash` field here uses the same algorithm as the proposed
`content_hash` property in the Publicaciones DB.  When a Notion page is
updated, the adapter computes `content_hash` from the page content and
passes it to `publish_attempt`.  On `publish_success`, the same hash is
recorded — enabling idempotency: if the hash hasn't changed since the
last `publish_success`, the adapter can skip re-publishing.

## Relation to human gates

Two gates in the editorial spec govern when publishing can occur:

- **`aprobado_contenido`** — content review passed (required before any
  `publish_attempt`).
- **`autorizar_publicacion`** — explicit human authorization to publish
  (required for LinkedIn and X in initial phases).

The publish tracking layer does not enforce these gates — it only records
events.  Gate enforcement is the responsibility of the publish adapter
or the Dispatcher.

## Rules

- Never log full post content in events.
- Never log secrets, tokens, API keys, or passwords.
- Never record `publish_success` without actual platform confirmation.
- LinkedIn and X require HITL (human-in-the-loop) authorization in
  initial phases.
- Ghost may eventually support automated publishing after
  `aprobado_contenido` gate passes.

## Security

- No secret values are stored in events, metadata, or test fixtures.
- The `sanitize_publish_metadata()` function strips sensitive field
  names (`secret`, `token`, `api_key`, `password`, `access_token`,
  `refresh_token`, `private_key`, `encryption_key`, `key_value`,
  `bearer`, `authorization`) even if passed accidentally.
- The `content_hash` is a one-way hash — the original content cannot be
  recovered from it.
