#!/usr/bin/env bash
# Granola Gap Check — VPS cron wrapper
# Checks Notion raw DB for recent pages that lack traceability or content.
# Designed to run daily on VPS even without the VM cache file.
#
# Cron: 0 8 * * * bash ~/umbral-agent-stack/scripts/vps/granola-gap-check.sh >> /tmp/granola_gap_check.log 2>&1
#
# Exit codes:
#   0 = no issues
#   2 = recent gaps detected (requires review)
#   1 = script error
set -euo pipefail

REPO_DIR="$HOME/umbral-agent-stack"
ENV_FILE="$HOME/.config/openclaw/env"
LOG_DIR="/tmp"
JSON_OUTPUT="$LOG_DIR/granola_gap_check_latest.json"

cd "$REPO_DIR"
source .venv/bin/activate
source "$REPO_DIR/scripts/vps/load-openclaw-env.sh"
load_openclaw_env "$ENV_FILE"
export PYTHONPATH="$PWD"

echo "$(date '+%Y-%m-%d %H:%M:%S') Starting Granola gap check..."

# Run the Notion-only health check
python3 -c "
import json, os, sys
from datetime import datetime, timedelta, timezone
from worker import config, notion_client

db_id = config.NOTION_GRANOLA_DB_ID
if not db_id:
    print(json.dumps({'error': 'NOTION_GRANOLA_DB_ID not set'}))
    sys.exit(1)

raw = notion_client.read_database(db_id, max_items=200)
items = raw.get('items', [])
now = datetime.now(timezone.utc)
recent_cutoff = (now - timedelta(days=7)).isoformat()

issues = []
for item in items:
    page_id = item.get('page_id', '')
    title = item.get('title', '')
    props = item.get('properties', {})

    # Extract date
    date_str = ''
    for dname in ('Fecha', 'Date'):
        dp = props.get(dname)
        if isinstance(dp, dict) and dp.get('type') == 'date':
            date_str = ((dp.get('date') or {}).get('start') or '')
            break

    # Extract traceability
    traz = ''
    for tname in ('Trazabilidad', 'Traceability'):
        tp = props.get(tname)
        if isinstance(tp, dict) and tp.get('type') == 'rich_text':
            traz = ''.join(t.get('plain_text', '') for t in (tp.get('rich_text') or []))
            break

    # Extract estado
    estado = ''
    for sname in ('Estado', 'Status'):
        sp = props.get(sname)
        if isinstance(sp, dict):
            if sp.get('type') == 'select':
                estado = ((sp.get('select') or {}).get('name') or '')
            elif sp.get('type') == 'status':
                estado = ((sp.get('status') or {}).get('name') or '')
            break

    # Check for issues
    issue_reasons = []
    has_document_id = 'granola_document_id=' in traz

    if not traz.strip():
        issue_reasons.append('no_traceability')
    elif not has_document_id:
        issue_reasons.append('missing_granola_document_id')

    if estado and estado.lower() in ('', 'pendiente'):
        issue_reasons.append('still_pending')

    if issue_reasons and date_str >= recent_cutoff[:10]:
        issues.append({
            'page_id': page_id,
            'title': title,
            'date': date_str,
            'estado': estado,
            'has_traceability': bool(traz.strip()),
            'has_document_id': has_document_id,
            'reasons': issue_reasons,
        })

report = {
    'timestamp': now.isoformat(),
    'total_pages': len(items),
    'recent_issues': len(issues),
    'issues': issues,
}

print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(2 if issues else 0)
" > "$JSON_OUTPUT" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') WARNING: Recent gaps detected. See $JSON_OUTPUT"
elif [ $EXIT_CODE -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') OK: No recent gaps."
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: Gap check failed (exit=$EXIT_CODE). See $JSON_OUTPUT"
fi

exit $EXIT_CODE
