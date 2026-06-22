#!/usr/bin/env bash
# pit_broker_window.sh — P10 Fase 8: gestión de la ventana de ejecución
# (L3 execute toggle + L4 egress nft/docker) para el torneo OpenClaw broker.
#
# Maneja SOLO las dos compuertas host-side reversibles:
#   L3 (G2) RICK_COPILOT_CLI_EXECUTE  -> ~/.config/openclaw/copilot-cli.env  (+ restart worker)
#   L4 (G4) egress nft table + docker network copilot-cli-egress
# G1 (copilot_cli.enabled) y G3 (_REAL_EXECUTION_IMPLEMENTED) son code/config
# vía PR+pull y NO se tocan acá: solo se verifican en `status`.
#
# SEGURIDAD POR DEFECTO:
#   - Sin --execute, todo comando es DRY (imprime el plan, no muta nada).
#   - `open` además exige --authorized (el operador afirma el GO explícito de
#     David: "autorizo P10 openclaw broker-real ... read-only probe").
#   - `open --execute` instala un trap (EXIT INT TERM HUP) que hace rollback
#     automático si el script termina sin un `commit` explícito (--keep-open).
#
# Uso:
#   scripts/pit/pit_broker_window.sh status
#   scripts/pit/pit_broker_window.sh open   [--execute --authorized] [--keep-open]
#   scripts/pit/pit_broker_window.sh close  [--execute]
#
# Protocolo: docs/ops/pit-p10-openclaw-broker-runbook.md  (Fase 8)
set -euo pipefail

ENV_FILE="${COPILOT_CLI_ENV:-$HOME/.config/openclaw/copilot-cli.env}"
NFT_TABLE="${COPILOT_NFT_TABLE:-inet copilot_egress}"
NFT_FILE="${COPILOT_NFT_FILE:-$HOME/.config/openclaw/copilot-egress.nft}"
DOCKER_NET="${COPILOT_DOCKER_NET:-copilot-cli-egress}"
WORKER_UNIT="${WORKER_UNIT:-umbral-worker.service}"
TOOL_POLICY="${TOOL_POLICY:-$HOME/umbral-agent-stack/config/tool_policy.yaml}"
COPILOT_CLI_PY="${COPILOT_CLI_PY:-$HOME/umbral-agent-stack/worker/tasks/copilot_cli.py}"

EXECUTE=0
AUTHORIZED=0
KEEP_OPEN=0
CMD="${1:-status}"
shift || true
for arg in "$@"; do
  case "$arg" in
    --execute) EXECUTE=1 ;;
    --authorized) AUTHORIZED=1 ;;
    --keep-open) KEEP_OPEN=1 ;;
    *) echo "WARN: arg desconocido: $arg" >&2 ;;
  esac
done

log() { echo "[broker-window] $*"; }
run() {
  # Ejecuta (o solo imprime) un comando segun --execute.
  if [ "$EXECUTE" -eq 1 ]; then
    log "EXEC: $*"
    "$@"
  else
    log "DRY : $*"
  fi
}

l3_value() {
  if [ -f "$ENV_FILE" ]; then
    grep -E '^RICK_COPILOT_CLI_EXECUTE=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true
  else
    echo "ENVFILE_ABSENT"
  fi
}
nft_present() { sudo nft list table $NFT_TABLE >/dev/null 2>&1 && echo present || echo ABSENT; }
docker_net_present() { docker network inspect "$DOCKER_NET" >/dev/null 2>&1 && echo present || echo ABSENT; }

cmd_status() {
  log "=== P10 broker window — STATUS (read-only) ==="
  log "L3 RICK_COPILOT_CLI_EXECUTE = $(l3_value)   ($ENV_FILE)"
  log "L4 nft table '$NFT_TABLE'   = $(nft_present)"
  log "L4 docker net '$DOCKER_NET' = $(docker_net_present)"
  if [ -f "$TOOL_POLICY" ]; then
    log "G1 copilot_cli.enabled      = $(grep -E '^[[:space:]]*enabled:' "$TOOL_POLICY" | head -1 | tr -d ' ')"
    log "G4 egress.activated         = $(grep -E '^[[:space:]]*activated:' "$TOOL_POLICY" | head -1 | tr -d ' ')"
  fi
  if [ -f "$COPILOT_CLI_PY" ]; then
    log "G3 _REAL_EXECUTION_IMPLEMENTED = $(grep -E '^_REAL_EXECUTION_IMPLEMENTED' "$COPILOT_CLI_PY" | head -1)"
  fi
  log "worker $WORKER_UNIT: $(systemctl --user is-active "$WORKER_UNIT" 2>/dev/null || echo unknown)"
}

_rollback() {
  local rc=$?
  if [ "$KEEP_OPEN" -eq 1 ]; then
    log "trap: --keep-open set, NO auto-rollback (ventana queda abierta a proposito)."
    return 0
  fi
  log "trap: rollback automatico de la ventana (rc=$rc) ..."
  EXECUTE=$EXECUTE cmd_close_inner || true
}

cmd_close_inner() {
  # Revertir L3 -> false + restart, y tear-down L4 (nft + docker net).
  if [ -f "$ENV_FILE" ]; then
    run sed -i.bak.window -E 's/^RICK_COPILOT_CLI_EXECUTE=true$/RICK_COPILOT_CLI_EXECUTE=false/' "$ENV_FILE"
    run systemctl --user restart "$WORKER_UNIT"
  fi
  run sudo nft delete table $NFT_TABLE
  run docker network rm "$DOCKER_NET"
}

cmd_open() {
  if [ "$AUTHORIZED" -ne 1 ]; then
    log "BLOCKED: 'open' requiere --authorized (afirmacion del GO explicito de David)."
    log "Sin autorizacion solo se permite 'status' o 'close'."
    exit 2
  fi
  if [ "$EXECUTE" -ne 1 ]; then
    log "DRY-RUN open: estos son los pasos que se ejecutarian con --execute:"
  else
    log "EXEC open: instalando trap de rollback (EXIT INT TERM HUP)."
    trap _rollback EXIT INT TERM HUP
  fi
  # L4 primero (red), L3 al final (kill-switch mas reversible).
  if [ -f "$NFT_FILE" ]; then
    run sudo nft -c -f "$NFT_FILE"
    run sudo nft -f "$NFT_FILE"
  else
    log "WARN: $NFT_FILE ausente — el operador debe generarlo via copilot_egress_resolver antes de abrir L4."
  fi
  run docker network create --driver bridge \
    --opt com.docker.network.bridge.enable_icc=false "$DOCKER_NET"
  if [ -f "$ENV_FILE" ]; then
    run sed -i.bak.window -E 's/^RICK_COPILOT_CLI_EXECUTE=false$/RICK_COPILOT_CLI_EXECUTE=true/' "$ENV_FILE"
    run systemctl --user restart "$WORKER_UNIT"
  else
    log "WARN: $ENV_FILE ausente — no se puede abrir L3."
  fi
  log "open completado. Estado:"
  cmd_status || true
  if [ "$EXECUTE" -eq 1 ] && [ "$KEEP_OPEN" -ne 1 ]; then
    log "NOTA: sin --keep-open, el trap cerrara la ventana al salir de este proceso."
    log "      Para una ventana persistente durante el torneo usa --keep-open y cierra"
    log "      manualmente con: pit_broker_window.sh close --execute"
  fi
}

cmd_close() {
  log "=== P10 broker window — CLOSE / rollback ==="
  cmd_close_inner
  log "close completado. Estado:"
  cmd_status || true
}

case "$CMD" in
  status) cmd_status ;;
  open)   cmd_open ;;
  close)  cmd_close ;;
  *) echo "usage: pit_broker_window.sh {status|open|close} [--execute --authorized --keep-open]" >&2; exit 1 ;;
esac