#!/usr/bin/env bash
# Scheduled Tasks cron wrapper — checks Redis for due tasks and enqueues them.
# Frequency: * * * * * (every minute).
set -euo pipefail

REPO_DIR="${HOME}/umbral-agent-stack"
VENV_DIR="${REPO_DIR}/.venv"
LOG_TAG="[scheduled-tasks]"

# Activate virtualenv
if [ -f "${VENV_DIR}/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
fi

cd "${REPO_DIR}"

python -c "
import os, redis
from dispatcher.scheduler import TaskScheduler
from dispatcher.queue import TaskQueue

url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
r = redis.Redis.from_url(url, decode_responses=True)
queue = TaskQueue(r)
scheduler = TaskScheduler(r)
scheduler.check_and_enqueue(queue)
" 2>&1

echo "${LOG_TAG} $(date -u '+%Y-%m-%d %H:%M:%S UTC') — check_and_enqueue done"
