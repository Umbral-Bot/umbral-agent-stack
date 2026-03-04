#!/usr/bin/env bash
# Cron wrapper for Notion Poller — polls Control Room comments and enqueues tasks.
# Install: crontab -e → * * * * * ~/umbral-agent-stack/scripts/vps/notion-poller-cron.sh >> /tmp/notion_poller.log 2>&1
# Or run: bash scripts/vps/install-notion-poller-cron.sh

set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate
set -a && source ~/.config/openclaw/env 2>/dev/null && set +a
export PYTHONPATH="$PWD"

python3 -m dispatcher.notion_poller --once
