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

## Step 0 — Page David BEFORE touching anything

Before executing Step 1, send a one-line message to David through the
fastest available channel (Notion comment in `Control Room`,
WhatsApp, SMS):

> `[publish-incident][PXX:00 UTC] starting publish-emergency-stop runbook on <vps>. Reason: <one-line>. Will report back inside 15 min.`

Do NOT wait for an answer; proceed with Step 1 immediately. The
notification is for traceability, not authorization — the runbook is
pre-authorized for any P0 publish situation.

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

## Step 1.5 — Kill in-flight publisher processes and stop systemd units

Step 1 only affects processes started AFTER the env edit. Anything already
running keeps the in-memory flags from when it was launched. Force the
running processes down NOW:

```bash
# Identify any publish-path process. Patterns cover Stage 9c (publisher),
# Stage 9b (LinkedIn OAuth refresh) and any module name containing
# "publisher" or "publish_".
pgrep -af 'stage9c|stage_9c|publisher\.py|scripts\.discovery.*publish' || \
  echo 'OK no publisher process running'

# Kill them (SIGTERM first, then SIGKILL after 5s if still alive).
pkill -TERM -f 'stage9c|stage_9c|publisher\.py|scripts\.discovery.*publish' || true
sleep 5
pkill -KILL -f 'stage9c|stage_9c|publisher\.py|scripts\.discovery.*publish' || true

# Stop user systemd units that wrap the publish path (no `sudo`; services
# run as user units under ~/.config/systemd/user/).
systemctl --user list-units --type=service --all | \
  grep -iE 'publish|stage9|linkedin' || echo 'OK no matching unit'
# For each match found above:
#   systemctl --user stop  <unit>
#   systemctl --user disable <unit>   # also stops at boot

# OBJECTIVE STOP VERIFICATION (must echo OK both lines):
pgrep -af 'stage9c|stage_9c|publisher\.py|scripts\.discovery.*publish' && \
  echo 'FAIL still running' || echo 'OK no publish process'
systemctl --user is-active --quiet 'umbral-publish*' && \
  echo 'FAIL unit active' || echo 'OK no active publish unit'
```

If either FAIL line appears, escalate immediately and re-run with
elevated patterns; do NOT continue to Step 2 until both verifications
echo `OK`.

## Step 1.6 — Revert deployment if a recent commit triggered the incident

If the incident correlates with a recent merge, revert the deployment to
the previous known-good commit BEFORE re-enabling anything. Use a clean
revert commit, never `git reset --hard` on `main`:

```bash
cd ~/umbral-agent-stack
git fetch --all --prune
git log --oneline -10 main          # identify the offending commit <SHA>
git checkout main
git pull --ff-only origin main

# Create a revert on a temporary branch, push, open PR (do NOT push
# straight to main from the VPS).
git checkout -b incident/revert-<SHA>
git revert --no-edit <SHA>
git push origin incident/revert-<SHA>
# Open PR via gh from your workstation:
#   gh pr create --base main --head incident/revert-<SHA> \
#     --title "incident: revert <SHA> (publish emergency)" \
#     --body  "See docs/audits/incidents/<UTC-date>-publish-incident.md"

# After the PR is merged from a workstation, redeploy on the VPS:
git checkout main && git pull --ff-only origin main
# Re-run the per-service restart from the VPS-deploy-after-edit skill
# for whichever service consumed the offending file. Do NOT skip the
# associated health check.
```

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

# 3. Confirm no publisher process is running (objective stop verification):
pgrep -af 'stage9c|stage_9c|publisher\.py|scripts\.discovery.*publish' && \
  echo 'FAIL still running' || echo 'OK no publish process'

# 4. Confirm no active systemd publish unit:
systemctl --user list-units --state=active --type=service --no-legend | \
  grep -iE 'publish|stage9|linkedin' && \
  echo 'FAIL active publish unit' || echo 'OK no active publish unit'

# 5. Confirm publish_guard now raises on any explicit flags call:
PYTHONPATH=~/umbral-agent-stack ~/umbral-agent-stack/.venv/bin/python -c "
import sqlite3, tempfile, os
from scripts.discovery.lib.publish_flags import PublishFlags
from scripts.discovery.lib.publish_guard import (
    PublishBlockedError, assert_can_publish,
)
flags = PublishFlags.from_env(os.environ)
db = sqlite3.connect(':memory:')
try:
    assert_can_publish({'id': 'verify'}, 'h'*64, db, flags=flags)
    print('FAIL: guard did not raise')
except PublishBlockedError as exc:
    print('OK: guard raised with reasons=', exc.reasons)
"
```

## What this runbook does NOT solve

- It does not delete already-published content from the external target;
  that is a manual step on each platform.
- It does not roll back Notion-side state (use the editorial UI for that).
- It does not alert David automatically; the operator running this
  runbook is responsible for paging David before / immediately after
  Step 1.
