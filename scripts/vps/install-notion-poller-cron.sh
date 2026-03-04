#!/usr/bin/env bash
# Install Notion Poller cron job (run once on VPS).
# Preserves existing crontab entries — only adds poller line if not present.
set -euo pipefail

CRON_LINE="* * * * * $HOME/umbral-agent-stack/scripts/vps/notion-poller-cron.sh >> /tmp/notion_poller.log 2>&1"

if crontab -l 2>/dev/null | grep -qF "notion-poller-cron.sh"; then
    echo "Notion Poller cron already installed."
else
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "Notion Poller cron added (every minute)."
fi

echo ""
echo "Current crontab:"
crontab -l
