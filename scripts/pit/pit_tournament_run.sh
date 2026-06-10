#!/usr/bin/env bash
# pit_tournament_run.sh — PIT-2b: spawn real de agentes efímeros OpenClaw.
#
# Corre el torneo PIT real post-smoke: gate literal David ("ok, arranca") +
# PIT_DRY_RUN_PASS obligatorios; spawn sessions_spawn × N desde main
# standalone (G-D1b); collect contra el pit-vault (pit.lane_announce,
# lane_complete obligatorio); kill + desregistro de efímeros al cierre.
#
# Uso:
#   scripts/pit/pit_tournament_run.sh <spec.yaml> <lanes.yaml> --gate "ok, arranca" [opciones]
#
#   <spec.yaml>    pit_spec v1 validado (ej.: examples/pit-salud-mental-pilot.yaml)
#   <lanes.yaml>   identidades de lanes derivadas por Rick (lane_id + lane_focus)
#   --plan-only    renderiza plan (roles + agents.yaml + prompt) sin spawn — para
#                  validación post-merge en VPS sin gastar budget
#
# Salida: ~/.coord-ag-evidence/pit-run/<pit_id>/run-metrics.json con veredicto
# PIT_RUN_PASS | PIT_RUN_PARTIAL | PIT_RUN_FAIL (exit 0|1|1);
# PIT_RUN_BLOCKED (exit 2) si gate/smoke/preflight/registro fallan pre-spawn.
# Protocolo: docs/ops/pit-2-runner-protocol.md §7
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SPEC="${1:?usage: pit_tournament_run.sh <spec.yaml> <lanes.yaml> --gate \"ok, arranca\" [options]}"
LANES="${2:?usage: pit_tournament_run.sh <spec.yaml> <lanes.yaml> --gate \"ok, arranca\" [options]}"
shift 2

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

exec "$PYTHON_BIN" "$REPO_ROOT/scripts/pit/pit_tournament_run.py" "$SPEC" "$LANES" "$@"
