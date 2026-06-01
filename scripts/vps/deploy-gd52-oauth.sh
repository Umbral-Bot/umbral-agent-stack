#!/usr/bin/env bash
# G-D5.2 — deploy order: repo from main, then patch secrets env (not in git).
set -euo pipefail

REPO="${HOME}/umbral-agent-stack"
PATCH_FILE="${1:-/tmp/rick-oauth.pending}"

cd "$REPO"
git fetch origin
if ! git diff --quiet -- worker/tasks/gmail.py worker/tasks/google_calendar.py 2>/dev/null; then
  echo "Resetting local drift on worker Google task modules before pull..."
  git checkout -- worker/tasks/gmail.py worker/tasks/google_calendar.py
fi
git pull --ff-only origin main
git log -1 --oneline

if [[ -f "$PATCH_FILE" ]]; then
  bash "$REPO/scripts/vps/patch-rick-oauth-env.sh" "$PATCH_FILE"
else
  echo "WARN: $PATCH_FILE missing — skipping env patch (assumes env already SET)"
fi

systemctl --user restart umbral-worker
sleep 2
systemctl --user is-active umbral-worker
bash "$REPO/scripts/vps/smoke-gd52-oauth.sh"
