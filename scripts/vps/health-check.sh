#!/usr/bin/env bash
# =================================================================
# Umbral VPS Health Check
# Verifies core services are running and logs are being written.
# Exit 0 = all OK, Exit 1 = something failed.
#
# Install as cron:
#   */30 * * * * bash ~/umbral-agent-stack/scripts/vps/health-check.sh >> /tmp/health_check.log 2>&1
# =================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/lib/umbral_alerting.sh"
# Carga ~/.config/openclaw/env. Antes no se hacia, asi que bajo cron WORKER_TOKEN
# llegaba vacio y el aviso se saltaba en silencio (incidente Linear UMB-276).
umbral_load_env || echo "[WARN] no se pudo leer el archivo de entorno"

WORKER_URL="${WORKER_URL:-http://127.0.0.1:8088}"
GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:18789}"
OPS_LOG="${UMBRAL_OPS_LOG_DIR:-$HOME/.config/umbral}/ops_log.jsonl"
REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
DISPATCHER_CTL="${DISPATCHER_CTL:-$REPO_DIR/scripts/vps/dispatcher-service.sh}"
FAILURES=()
NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

echo "=== Health Check - $NOW ==="

# ---------------------------------------------------------------
# 1. Redis
# ---------------------------------------------------------------
if redis-cli ping 2>/dev/null | grep -qi "PONG"; then
    echo "[OK]  Redis is running"
else
    echo "[FAIL] Redis is NOT responding"
    FAILURES+=("Redis not responding")
fi

# ---------------------------------------------------------------
# 2. Worker (FastAPI on port 8088)
# ---------------------------------------------------------------
WORKER_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "${WORKER_URL}/health" 2>/dev/null || echo "000")
if [ "$WORKER_STATUS" = "200" ]; then
    echo "[OK]  Worker responding (HTTP 200)"
else
    echo "[FAIL] Worker not responding (HTTP $WORKER_STATUS)"
    FAILURES+=("Worker HTTP $WORKER_STATUS at ${WORKER_URL}/health")
fi

# ---------------------------------------------------------------
# 3. Dispatcher status (systemd + real process count)
# ---------------------------------------------------------------
if DISPATCHER_STATUS="$(bash "$DISPATCHER_CTL" status 2>&1)"; then
    echo "[OK]  Dispatcher canonical"
    while IFS= read -r line; do
        [ -n "$line" ] && echo "      $line"
    done <<< "$DISPATCHER_STATUS"
else
    echo "[FAIL] Dispatcher drift detected"
    while IFS= read -r line; do
        [ -n "$line" ] && echo "      $line"
    done <<< "$DISPATCHER_STATUS"
    FAILURES+=("Dispatcher drift: $(echo "$DISPATCHER_STATUS" | tr '\n' ' ' | sed 's/  */ /g')")
fi

# ---------------------------------------------------------------
# 4. Ops log has recent events
# ---------------------------------------------------------------
if [ -f "$OPS_LOG" ]; then
    LINE_COUNT=$(wc -l < "$OPS_LOG" | tr -d ' ')
    echo "[OK]  ops_log.jsonl exists ($LINE_COUNT lines)"
    LAST_LINE=$(tail -1 "$OPS_LOG" 2>/dev/null || true)
    if [ -n "$LAST_LINE" ]; then
        LAST_TS=$(echo "$LAST_LINE" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('ts',''))" 2>/dev/null || true)
        if [ -n "$LAST_TS" ]; then
            echo "       Last event: $LAST_TS"
        fi
    fi
else
    echo "[WARN] ops_log.jsonl not found at $OPS_LOG"
    FAILURES+=("ops_log.jsonl not found")
fi

# ---------------------------------------------------------------
# 5. Gateway de OpenClaw
#
# Ningun monitor lo vigilaba: supervisor.sh no contiene la palabra "gateway".
# ---------------------------------------------------------------
GW_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "${GATEWAY_URL}/health" 2>/dev/null || echo "000")
if [ "$GW_STATUS" = "200" ]; then
    echo "[OK]  Gateway responding (HTTP 200)"
else
    echo "[FAIL] Gateway not responding (HTTP $GW_STATUS)"
    FAILURES+=("Gateway HTTP $GW_STATUS at ${GATEWAY_URL}/health")
fi

# ---------------------------------------------------------------
# 6. Canario: ¿puede el agente GENERAR TEXTO ahora mismo?
#
# Liveness no es capacidad. Esta es la comprobacion que faltaba y por cuya
# ausencia el stack estuvo 3,7 dias caido con todos los indicadores en verde.
# ---------------------------------------------------------------
CANARY_OUT=""
if [ "${UMBRAL_SKIP_CANARY:-0}" = "1" ]; then
    echo "[SKIP] canario desactivado por UMBRAL_SKIP_CANARY=1"
else
    set +e
    CANARY_OUT=$(bash "$SCRIPT_DIR/canary-inference.sh" --agent "${UMBRAL_CANARY_AGENT:-main}" 2>&1)
    CANARY_RC=$?
    set -e
    echo "$CANARY_OUT"
    if [ $CANARY_RC -ne 0 ]; then
        FAILURES+=("Canario: el agente no pudo generar texto")
    elif printf '%s' "$CANARY_OUT" | grep -q 'POR FALLBACK'; then
        # No es fallo: es degradacion. El servicio responde, pero por el camino
        # de reserva, y eso hay que saberlo antes de que se agote tambien.
        echo "[WARN] el canario respondio por fallback: el proveedor primario no sirve"
        umbral_alert health-check-degradado \
            "el agente responde solo por fallback" \
            "El proveedor primario no atiende; la capacidad depende del camino de reserva. $(printf '%s' "$CANARY_OUT" | tail -1)" \
            warn || true
    fi
fi

# ---------------------------------------------------------------
# 7. ¿Murio algun otro monitor? Se detecta por AUSENCIA de marca fresca,
#    no por presencia de logs: el silencio de un cron es ambiguo.
# ---------------------------------------------------------------
for entry in "e2e-validation:172800"; do
    mon="${entry%%:*}"; maxage="${entry##*:}"
    if umbral_heartbeat_stale "$mon" "$maxage"; then
        age=$(umbral_heartbeat_age "$mon")
        if [ "$age" -lt 0 ]; then
            echo "[WARN] monitor '$mon' sin ninguna marca de ejecucion correcta todavia"
        else
            echo "[FAIL] monitor '$mon' lleva ${age}s sin ejecucion correcta (maximo ${maxage}s)"
            FAILURES+=("Monitor '$mon' rancio: ${age}s sin ejecucion correcta")
        fi
    fi
done

# ---------------------------------------------------------------
# 8. Report result
# ---------------------------------------------------------------
echo ""
if [ ${#FAILURES[@]} -eq 0 ]; then
    echo "All checks passed"
    umbral_heartbeat_write health-check
    # Aviso de recuperacion, una sola vez, como TRANSICION y no como muestreo.
    if umbral_alert_active health-check; then
        RC_INFO=0
        umbral_alert health-check "el VPS vuelve a estar sano" "Todos los chequeos pasan, incluido el canario de generacion." info || RC_INFO=$?
    # El incidente no se cierra hasta que el aviso de recuperacion sale de
    # verdad: rc=2 es "no se pudo entregar", y entonces se conserva el estado
    # para reintentarlo en el proximo ciclo. rc=1 es "callado por duplicado",
    # que significa que ya se conto.
        if [ "$RC_INFO" -ne 2 ]; then umbral_clear_alert health-check >/dev/null || true; fi
    fi
    umbral_ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"health_check\",\"release\":\"$(umbral_release_sha)\",\"status\":\"ok\",\"failures\":0}"
    exit 0
fi

echo "${#FAILURES[@]} check(s) failed:"
for f in "${FAILURES[@]}"; do
    echo "  - $f"
done

umbral_heartbeat_write health-check
DETALLE=$(printf '%s; ' "${FAILURES[@]}")
umbral_ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"health_check\",\"release\":\"$(umbral_release_sha)\",\"status\":\"fail\",\"failures\":${#FAILURES[@]},\"detail\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$DETALLE")}"

# Un unico camino de aviso, deduplicado, con enfriamiento y troceado por debajo
# del maximo de Notion. Antes habia dos ramas y ninguna funcionaba bajo cron.
umbral_alert health-check "hay chequeos fallando en el VPS" "${#FAILURES[@]} fallo(s): $DETALLE" error || true

exit 1
