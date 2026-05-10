# Publish emergency stop runbook

**Issue**: #405
**Wave**: 2.A
**Severity**: P0 (use when publication may be happening unexpectedly)

## When to use

Activate this runbook the moment ANY of the following occurs:

- A publish event appears in `~/.config/umbral/ops_log.jsonl` that was
  not authorized by David.
- A real LinkedIn / blog / X post is observed without an approved
  Notion source page.
- `publish_guard.pass` events appear with `publish_enabled=true` and
  `dry_run=false` outside an explicit operator window.
- Any publisher in the stack starts emitting outbound HTTP traffic to a
  publish target endpoint.

## Step 1 — Hard kill via env

```bash
ssh rick@<vps>
# Edit the env file that loads the publish-path flags.
sed -i 's/^PUBLISH_ENABLED=.*/PUBLISH_ENABLED=false/' ~/.config/openclaw/env
# If the line is missing, append it:
grep -q '^PUBLISH_ENABLED=' ~/.config/openclaw/env || \
  echo 'PUBLISH_ENABLED=false' >> ~/.config/openclaw/env
# Verify
grep PUBLISH_ENABLED ~/.config/openclaw/env
# Same for DRY_RUN as belt-and-suspenders.
sed -i 's/^DRY_RUN=.*/DRY_RUN=true/' ~/.config/openclaw/env
grep -q '^DRY_RUN=' ~/.config/openclaw/env || echo 'DRY_RUN=true' >> ~/.config/openclaw/env
grep DRY_RUN ~/.config/openclaw/env
```

The defaults in `scripts/discovery/lib/publish_flags.py` are already
fail-closed (`PUBLISH_ENABLED=false`, `DRY_RUN=true`), so simply removing
overrides also stops new publishes. Any new process started after this
edit reads the new env.

## Step 2 — Disable cron

```bash
crontab -l > /tmp/crontab-backup-$(date +%s).txt
crontab -e   # comment out any line invoking the publish path or stage9c
crontab -l   # verify the publish-related lines are commented
# If timers are used instead:
systemctl --user list-timers --all | grep -iE 'publish|stage9|linkedin'
# Stop and disable any matching timer:
# systemctl --user stop  <name>.timer && systemctl --user disable <name>.timer
```

## Step 3 — Revoke external token (if behavior is suspicious)

- LinkedIn: revoke at <https://www.linkedin.com/developers/apps>.
- Notion: rotate integration secret in Notion admin (only if Notion is the
  publication channel; in Wave 2.A this is the editorial channel, not a
  publish target).
- Blog (`umbralbim.cl` once wired): rotate API key per
  `docs/runbooks/secrets-tokens.md` (see #406).

## Step 4 — Inspect last 24h

```bash
# Once #404-lite is merged the publish log lives here:
tail -200 ~/.config/umbral/publish_log.jsonl 2>/dev/null | \
  jq 'select(.timestamp_utc > (now - 86400 | strftime("%Y-%m-%dT%H:%M:%SZ")))'

# Until #404-lite lands, the canonical signal is publish_guard events:
tail -500 ~/.config/umbral/ops_log.jsonl | \
  jq 'select(.event | startswith("publish_guard"))'
```

Look for any `publish_guard.pass` line where downstream behaviour suggests
a real network write happened.

## Step 5 — Register incident

Create `docs/audits/incidents/<UTC-date>-publish-incident.md` with at
least:

- Timeline (UTC).
- Root cause hypothesis.
- Items published (URL, content_hash, page_id).
- Items prevented by Step 1 / Step 2.
- Tokens rotated.
- Follow-up tasks (link to Linear / GitHub issues opened).

## Step 6 — Re-enable only after root cause closed

Keep `PUBLISH_ENABLED=false` and `DRY_RUN=true` in the env file until:

1. The incident document above has a written closure with sign-off from
   David.
2. The `publish_flags` defaults still hold (`from_env({}).allows_real_publish() is False`).
3. A full pytest run on `main` is green.

Only then flip flags ON during a single operator window, with manual
observation of `ops_log.jsonl` in `tail -F` mode.

## Verification commands (paste-and-run)

```bash
# 1. Confirm env is fail-closed:
PYTHONPATH=~/umbral-agent-stack ~/umbral-agent-stack/.venv/bin/python -c "
from scripts.discovery.lib.publish_flags import PublishFlags
import os
flags = PublishFlags.from_env(os.environ)
print('publish_enabled=', flags.publish_enabled)
print('dry_run=',         flags.dry_run)
print('max_posts=',       flags.max_posts)
print('max_posts_per_day=', flags.max_posts_per_day)
print('allows_real_publish=', flags.allows_real_publish())
assert flags.allows_real_publish() is False, 'KILL SWITCH NOT EFFECTIVE'
print('OK kill switch effective')
"

# 2. Confirm no cron entry will run a publisher:
crontab -l | grep -iE 'publish|stage9|linkedin' || echo 'OK no publish cron'
```

## What this runbook does NOT solve

- It does not delete already-published content from the external target;
  that is a manual step on each platform.
- It does not roll back Notion-side state (use the editorial UI for that).
- It does not alert David automatically; the operator running this
  runbook is responsible for paging David before / immediately after
  Step 1.
