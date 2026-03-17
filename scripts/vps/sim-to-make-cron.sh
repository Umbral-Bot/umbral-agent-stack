#!/usr/bin/env bash
# SIM â†’ Make.com pipeline cron wrapper.
# Runs after each SIM report (9:00, 15:00, 21:00 UTC).
# Enqueues composite.research_report, polls result, sends to Make.com webhook.
set -euo pipefail

REPO_DIR="${HOME}/umbral-agent-stack"
VENV_DIR="${REPO_DIR}/.venv"
LOG_TAG="[sim-to-make]"

echo "${LOG_TAG} $(date -u '+%Y-%m-%d %H:%M:%S UTC') â€” Starting SIMâ†’Make pipeline"

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

# Run pipeline
cd "${REPO_DIR}"
python scripts/sim_to_make.py --timeout 180

EXIT_CODE=$?
echo "${LOG_TAG} $(date -u '+%Y-%m-%d %H:%M:%S UTC') â€” Done (exit ${EXIT_CODE})"
exit ${EXIT_CODE}
