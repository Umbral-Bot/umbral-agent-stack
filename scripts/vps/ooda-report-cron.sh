#!/usr/bin/env bash
# Cron wrapper: OODA weekly report.
# Genera reporte OODA con datos de Redis + Langfuse y lo guarda en /tmp.
# Frecuencia recomendada: 0 7 * * 1 (lunes 7:00 UTC).
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
cd "$REPO_DIR"

source .venv/bin/activate 2>/dev/null || true

REPORT_FILE="/tmp/ooda_report_$(date +%Y%m%d).md"

python scripts/ooda_report.py --week-ago 0 --format markdown > "$REPORT_FILE"

echo "OODA report saved to $REPORT_FILE"

# Optionally post to Notion via Worker API
if [ -n "${WORKER_URL:-}" ] && [ -n "${WORKER_TOKEN:-}" ]; then
    python -c "
from client.worker_client import WorkerClient
wc = WorkerClient(base_url='${WORKER_URL}', token='${WORKER_TOKEN}')
with open('${REPORT_FILE}') as f:
    report = f.read()
try:
    wc.run('notion.upsert_task', {
        'task_id': 'ooda-weekly-$(date +%Y%m%d)',
        'status': 'done',
        'team': 'system',
        'task': 'system.ooda_report',
        'result_summary': report[:2000],
    })
    print('OODA report posted to Notion')
except Exception as e:
    print(f'Notion post skipped: {e}')
" 2>&1 || true
fi
