#!/usr/bin/env bash
# Daily Digest cron wrapper â€” runs at 22:00 UTC via install-cron.sh.
# Scans Redis for last 24h tasks, generates LLM summary, posts to Notion.
set -euo pipefail

REPO_DIR="${HOME}/umbral-agent-stack"
VENV_DIR="${REPO_DIR}/.venv"
LOG_TAG="[daily-digest]"

echo "${LOG_TAG} $(date -u '+%Y-%m-%d %H:%M:%S UTC') â€” Starting daily digest"

# Activate virtualenv
if [ -f "${VENV_DIR}/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
fi

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

# Run digest with Notion posting
cd "${REPO_DIR}"
python scripts/daily_digest.py --notion --hours 24

EXIT_CODE=$?
echo "${LOG_TAG} $(date -u '+%Y-%m-%d %H:%M:%S UTC') â€” Done (exit ${EXIT_CODE})"
exit ${EXIT_CODE}
