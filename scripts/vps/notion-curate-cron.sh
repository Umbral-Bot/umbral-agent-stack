#!/usr/bin/env bash
# Curacion diaria de Notion operativo.
# Mantiene limpias Tareas y Bandeja Puente sin tocar proyectos/entregables canÃ³nicos.

set -euo pipefail

cd ~/umbral-agent-stack
source .venv/bin/activate 2>/dev/null || true

if [ -f ~/.config/openclaw/env ]; then
  # shellcheck disable=SC1091
  source "$HOME/umbral-agent-stack/scripts/vps/load-openclaw-env.sh"
  load_openclaw_env "$HOME/.config/openclaw/env"
fi

export PYTHONPATH=.

python3 scripts/notion_curate_ops_vps.py
