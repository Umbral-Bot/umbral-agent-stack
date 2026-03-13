#!/usr/bin/env bash
# Cron wrapper: OODA weekly report.
# Genera reporte OODA con datos de Redis + Langfuse y lo guarda en /tmp.
# Frecuencia recomendada: 0 7 * * 1 (lunes 7:00 UTC).
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
cd "$REPO_DIR"

source .venv/bin/activate

# Load env vars from the live VPS env first, then fallback to repo-local .env.
if [ -f "${HOME}/.config/openclaw/env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${HOME}/.config/openclaw/env"
    set +a
elif [ -f "${REPO_DIR}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${REPO_DIR}/.env"
    set +a
fi

REPORT_FILE="/tmp/ooda_report_$(date +%Y%m%d).md"
REPORT_TITLE="OODA Weekly Report - $(date +%Y-%m-%d)"

python scripts/ooda_report.py --week-ago 0 --format markdown > "$REPORT_FILE"

echo "OODA report saved to $REPORT_FILE"

# Optionally post to Notion via Worker API
if [ -n "${WORKER_URL:-}" ] && [ -n "${WORKER_TOKEN:-}" ]; then
    REPORT_FILE="$REPORT_FILE" REPORT_TITLE="$REPORT_TITLE" python - <<'PY' 2>&1 \
        || { echo "[ERROR] $(date): OODA Notion post failed" >> /tmp/ooda_report.log; }
import os
from client.worker_client import WorkerClient

wc = WorkerClient(base_url=os.environ["WORKER_URL"], token=os.environ["WORKER_TOKEN"])

with open(os.environ["REPORT_FILE"], encoding="utf-8") as f:
    report = f.read()

try:
    created = wc.run(
        "notion.create_report_page",
        {
            "title": os.environ["REPORT_TITLE"],
            "content": report,
            "metadata": {
                "team": "improvement",
                "report_type": "ooda_weekly",
                "generated_by": "scripts/vps/ooda-report-cron.sh",
            },
        },
    )
    result = created.get("result", created)
    page_url = result.get("page_url") or result.get("url") or ""
    wc.run(
        "notion.add_comment",
        {
            "text": (
                f"OODA semanal generado: {page_url}"
                if page_url
                else "OODA semanal generado y guardado como reporte hijo."
            )
        },
    )
    print("OODA report posted to Notion report page")
except Exception as e:
    import sys, datetime
    msg = f"[ERROR] {datetime.datetime.utcnow().isoformat()}Z OODA Notion post failed: {e}\n"
    print(msg, end="", file=sys.stderr)
    with open("/tmp/ooda_report.log", "a") as _log:
        _log.write(msg)
PY
fi
