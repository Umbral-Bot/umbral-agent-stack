#!/usr/bin/env bash
# pit_openclaw_broker_run.sh — P10: entrypoint del torneo OpenClaw broker-real.
#
# Orquesta agentes efímeros OpenClaw `<pit_id>-lane-*` que despachan UNA tarea
# `copilot_cli.run` cada uno contra el Worker, produciendo openclaw_total>0 en
# el ledger. Envuelve scripts/pit/pit_broker_run.py asegurando el entorno VPS:
#   - PATH con ~/.npm-global/bin (binario openclaw no está en PATH no-interactivo)
#   - WORKER_URL / WORKER_TOKEN sourced del EnvironmentFile del worker si no están
#     ya en el entorno (NUNCA se imprime el token; el spec lo deniega en el prompt).
#
# Uso:
#   # plan-only (Fase 5, sin spawn, gates cerrados — no requiere gate David):
#   scripts/pit/pit_openclaw_broker_run.sh <spec.yaml> <lanes.yaml> --plan-only
#
#   # spawn real (Fase 8, requiere ventana L3/L4/nft abierta + gate David):
#   scripts/pit/pit_openclaw_broker_run.sh <spec.yaml> <lanes.yaml> --gate "ok, arranca"
#
# Salida: <evidence>/run-metrics.json con veredicto
#   P10_OPENCLAW_BROKER_RUN_PASS | _PARTIAL | _FAIL (exit 0|1|1)
#   P10_OPENCLAW_BROKER_PLAN_OK (exit 0, plan-only)
#   P10_OPENCLAW_BROKER_RUN_BLOCKED (exit 2) si gate/smoke/preflight fallan.
# Protocolo: docs/ops/pit-p10-openclaw-broker-runbook.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SPEC="${1:?usage: pit_openclaw_broker_run.sh <spec.yaml> <lanes.yaml> [options]}"
LANES="${2:?usage: pit_openclaw_broker_run.sh <spec.yaml> <lanes.yaml> [options]}"
shift 2

# --- PATH: el binario openclaw vive en ~/.npm-global/bin (npm global) y no
# está en el PATH no-interactivo de sesiones ssh batch. ---
NPM_GLOBAL_BIN="${NPM_GLOBAL_BIN:-$HOME/.npm-global/bin}"
if [ -d "$NPM_GLOBAL_BIN" ]; then
  case ":$PATH:" in
    *":$NPM_GLOBAL_BIN:"*) : ;;
    *) PATH="$NPM_GLOBAL_BIN:$PATH" ;;
  esac
  export PATH
fi

# --- WORKER_URL / WORKER_TOKEN: si no están en el entorno, intentar leerlos del
# EnvironmentFile del worker. Solo se EXPORTAN; nunca se imprimen. ---
WORKER_ENV_FILE="${WORKER_ENV_FILE:-$HOME/.config/umbral/worker.env}"
if [ -z "${WORKER_URL:-}" ] || [ -z "${WORKER_TOKEN:-}" ]; then
  if [ -f "$WORKER_ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -a
    . "$WORKER_ENV_FILE"
    set +a
  fi
fi
export WORKER_URL="${WORKER_URL:-http://127.0.0.1:8088}"
if [ -z "${WORKER_TOKEN:-}" ]; then
  echo "WARN: WORKER_TOKEN no presente en entorno ni en $WORKER_ENV_FILE." >&2
  echo "      Las lanes no podrán autenticarse contra el Worker en spawn real." >&2
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  for candidate in "$REPO_ROOT/.venv/bin/python" python3 python; do
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

exec "$PYTHON_BIN" "$REPO_ROOT/scripts/pit/pit_broker_run.py" "$SPEC" "$LANES" "$@"