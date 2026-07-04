#!/usr/bin/env bash
# pit_lane_workspace_init.sh — PIT-DEV: workspace curado por lane.
#
# Prepara pit/<pit_id>/lanes/<lane_id>/workspace/ con snapshot read-only del
# repo (git archive del ref pinneado — NO worktree sobre main vivo) +
# CONTEXT_INDEX.md generado (mapa docs/worker/dispatcher/client/scripts,
# endpoints del Worker, tasks registradas, env vars lógicas — solo nombres).
#
# Uso:
#   scripts/pit/pit_lane_workspace_init.sh \
#     --pit-id <pit_id> --lane-id <lane_id> \
#     --repo <checkout> --ref <tag|commit> [--vault-path <vault>] [--force]
#
# Contrato: docs/ops/pit-dev-mode-vision-2026-07-03.md §4
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Elegir un python que realmente ejecute (en Windows/Git Bash el alias
# python3 de WindowsApps existe en PATH pero es un stub que no corre).
PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  for candidate in python3 python; do
    if "$candidate" -c 'import sys' >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: no usable python interpreter found (set PYTHON_BIN)" >&2
  exit 1
fi

export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

exec "$PYTHON_BIN" "$REPO_ROOT/scripts/pit/pit_lane_workspace_init.py" "$@"
