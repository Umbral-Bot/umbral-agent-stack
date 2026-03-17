#!/usr/bin/env bash
# Curacion diaria de Notion operativo.
# Mantiene limpias Tareas y Bandeja Puente sin tocar proyectos/entregables canÃ³nicos.

set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate 2>/dev/null || true

if [ -f ~/.config/openclaw/env ]; then
  set -a
  source ~/.config/openclaw/env
  set +a
fi

export PYTHONPATH=.

python3 scripts/notion_curate_ops_vps.py
