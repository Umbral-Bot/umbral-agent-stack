#!/usr/bin/env bash
# Check Notion Poller health — cron status, log tail, Redis state.
set -euo pipefail

echo "=== Notion Poller Health Check ==="
echo ""

# 1. Cron installed?
echo "1. Cron Job:"
if crontab -l 2>/dev/null | grep -qF "notion-poller-cron.sh"; then
    echo "   ✅ Cron installed"
    crontab -l 2>/dev/null | grep "notion-poller-cron.sh" | sed 's/^/   /'
else
    echo "   ❌ Cron NOT installed"
    echo "   → Run: bash ~/umbral-agent-stack/scripts/vps/install-notion-poller-cron.sh"
fi

# 2. Process running?
echo ""
echo "2. Process:"
if pgrep -f "dispatcher.notion_poller" > /dev/null 2>&1; then
    echo "   ✅ Poller process running (PID: $(pgrep -f 'dispatcher.notion_poller' | head -1))"
else
    echo "   ℹ️  No poller process (normal if using --once cron mode)"
fi

# 3. Redis last timestamp
echo ""
echo "3. Redis (last poll timestamp):"
LAST_TS=$(redis-cli GET "umbral:notion_poller:last_ts" 2>/dev/null || echo "")
if [ -n "$LAST_TS" ]; then
    echo "   ✅ Last poll: $LAST_TS"
else
    echo "   ⚠️  No timestamp found (poller has not run yet?)"
fi

# 4. Log tail
echo ""
echo "4. Recent Log (last 15 lines):"
if [ -f /tmp/notion_poller.log ]; then
    tail -15 /tmp/notion_poller.log | sed 's/^/   /'
else
    echo "   ⚠️  Log file not found at /tmp/notion_poller.log"
fi

echo ""
echo "=== Check complete ==="
