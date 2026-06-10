#!/usr/bin/env bash
# pit_tournament_dry_run.sh — PIT-2: smoke local de torneo PIT sin OpenClaw.
#
# Simula las N lanes del spec en secuencia (init → 1 iteración fake →
# fulfillment → announce) sobre un pit-vault scratch. NO internet, NO
# Magnific, NO sessions_spawn — el spawn real de agentes efímeros es PIT-2b.
#
# Uso:
#   scripts/pit/pit_tournament_dry_run.sh <spec.yaml> [EVIDENCE_DIR]
#
#   <spec.yaml>    pit_spec v1 (ej.: examples/pit-salud-mental-pilot.yaml)
#   EVIDENCE_DIR   default: ~/.coord-ag-evidence/pit-dry-run/<pit_id>
#
# Salida: <EVIDENCE_DIR>/final-metrics.json con veredicto
# PIT_DRY_RUN_PASS | PIT_DRY_RUN_FAIL (exit code 0 | 1).
# Protocolo: docs/ops/pit-2-runner-protocol.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SPEC="${1:?usage: pit_tournament_dry_run.sh <spec.yaml> [evidence_dir]}"
EVIDENCE_DIR="${2:-}"

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

# Salida JSON/markdown con acentos: no depender del code page de la consola.
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

ARGS=("$REPO_ROOT/scripts/pit/pit_dry_run.py" "$SPEC")
if [ -n "$EVIDENCE_DIR" ]; then
  ARGS+=(--evidence-dir "$EVIDENCE_DIR")
fi

exec "$PYTHON_BIN" "${ARGS[@]}"
