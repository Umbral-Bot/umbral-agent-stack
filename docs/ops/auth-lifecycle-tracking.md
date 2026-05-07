# Auth Lifecycle Tracking

Track the expiry and operational status of external credentials used by
the editorial system (LinkedIn, Ghost, n8n, Freepik, Vertex AI, Make)
without storing or exposing secret values.

## What this does

- Classifies each credential into one of five statuses: `ok`, `warning`,
  `critical`, `expired`, `unknown`.
- Emits `auth_lifecycle_check` events to OpsLogger (`ops_log.jsonl`).
- Provides a CLI script for dry-run evaluation or log-writing mode.
- **Does not store secrets**. Only metadata (provider, credential label,
  expiry date, thresholds, playbook references).

## Status taxonomy

| Status | Meaning |
|--------|---------|
| `ok` | Credential has >warning_days until expiry |
| `warning` | Expires within warning_days |
| `critical` | Expires within critical_days |
| `expired` | Already expired |
| `unknown` | No expiry information available (e.g. API keys with no known TTL) |

## Files

| File | Purpose |
|------|---------|
| `infra/auth_lifecycle.py` | Core module: parse, classify, build records |
| `infra/ops_logger.py` | Extended with `auth_lifecycle_check()` method |
| `config/auth_lifecycle.example.yaml` | Example config with all tracked credentials |
| `scripts/auth_lifecycle_check.py` | CLI: evaluate config, dry-run or write to log |
| `tests/test_auth_lifecycle.py` | Unit tests for classification logic |
| `tests/test_auth_lifecycle_check.py` | Tests for OpsLogger integration and CLI |

## Usage

### Dry-run (default, no log writes)

```bash
python scripts/auth_lifecycle_check.py --config config/auth_lifecycle.example.yaml
```

Output:
```
  [?] linkedin/linkedin_personal_access_token: unknown (n/a)
  [?] ghost/ghost_admin_api_key: unknown (n/a)
  ...
7 credentials evaluated (dry-run, no log written).
```

### JSON output

```bash
python scripts/auth_lifecycle_check.py --config config/auth_lifecycle.example.yaml --json
```

### Write to OpsLogger

```bash
python scripts/auth_lifecycle_check.py --config config/auth_lifecycle.yaml --write-ops-log
```

This writes one `auth_lifecycle_check` event per credential to
`~/.config/umbral/ops_log.jsonl`.

## Configuration

Copy the example and fill in expiry dates as credentials are provisioned:

```bash
cp config/auth_lifecycle.example.yaml config/auth_lifecycle.yaml
```

Each entry has:
- `provider` — service name (linkedin, ghost, n8n, etc.)
- `credential_ref` — safe label, never the actual secret
- `expires_at` — ISO 8601 datetime (optional; omit for keys with no known expiry)
- `warning_days` / `critical_days` — alert thresholds
- `notes` — human-readable context
- `owner` — who can re-auth (david, rick)
- `reauth_playbook` / `recovery_playbook` — steps to fix

## Integration roadmap

This module is a foundation. Future integrations (not in this PR):

1. **Cron job**: run `auth_lifecycle_check.py --write-ops-log` daily via
   the VPS health check or a dedicated cron.
2. **Alerting**: read `auth_lifecycle_check` events from OpsLogger and
   surface `warning`/`critical`/`expired` to Notion or Telegram.
3. **LinkedIn token**: after OAuth flow, update `expires_at` in config
   and run the check to verify tracking.
4. **Ghost**: after Custom Integration setup, register the key in config.

## Security

- No secret values are stored in config, logs, or test fixtures.
- The `auth_lifecycle_check` OpsLogger method strips sensitive field names
  (`secret`, `token`, `api_key`, `password`, etc.) even if passed accidentally.
- The `credential_ref` field is always a label, never a value.
