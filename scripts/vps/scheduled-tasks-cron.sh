#!/usr/bin/env bash
# Cron wrapper: check_and_enqueue del TaskScheduler.
# Ejecuta tareas programadas que ya cumplieron su plazo.
# Frecuencia recomendada: * * * * * (cada minuto).
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
cd "$REPO_DIR"

source .venv/bin/activate 2>/dev/null || true

exec python -c "
import os, redis
from dispatcher.scheduler import TaskScheduler
from dispatcher.queue import TaskQueue

url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
r = redis.Redis.from_url(url, decode_responses=True)
scheduler = TaskScheduler(r)
queue = TaskQueue(r)
scheduler.check_and_enqueue(queue)
"
