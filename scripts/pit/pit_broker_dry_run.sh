#!/usr/bin/env bash
# pit_broker_dry_run.sh — P10: smoke local del torneo OpenClaw broker (sin
# OpenClaw, sin Worker, sin internet). Simula los announces broker de cada
# lane sobre un pit-vault scratch y deja final-metrics.json con veredicto
# PIT_DRY_RUN_PASS | PIT_DRY_RUN_FAIL (exit 0 | 1) que alimenta el smoke gate
# del run real (pit_openclaw_broker_run.sh).
#
# Uso:
#   scripts/pit/pit_broker_dry_run.sh <spec.yaml> [lanes.yaml] [--evidence-dir DIR] [opciones]
#
#   <spec.yaml>   pit_spec v2 broker validado (ej.: examples/pit/pit_spec.openclaw-broker-v1.yaml)
#   [lanes.yaml]  lanes opcionales (lane_id + lane_focus) para enriquecer prompts
#
# Protocolo: docs/ops/pit-p10-openclaw-broker-runbook.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SPEC="${1:?usage: pit_broker_dry_run.sh <spec.yaml> [lanes.yaml] [options]}"
shift
LANES=""
if [ "${1:-}" ] && [ "${1#-}" = "${1}" ]; then
  LANES="$1"
  shift
fi

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

ARGS=("$REPO_ROOT/scripts/pit/pit_broker_run.py" "$SPEC")
if [ -n "$LANES" ]; then
  ARGS+=("$LANES")
fi
ARGS+=(--smoke "$@")

exec "$PYTHON_BIN" "${ARGS[@]}"