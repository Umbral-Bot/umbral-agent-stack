#!/usr/bin/env bash
# =================================================================
# Umbral E2E Validation â€” Cron wrapper
# Runs the full E2E validation suite and posts results to Notion.
# On failure, posts an alert to Notion Control Room.
#
# Schedule: daily at 06:00 UTC
#   0 6 * * * bash ~/umbral-agent-stack/scripts/vps/e2e-validation-cron.sh >> /tmp/e2e_validation.log 2>&1
# =================================================================
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
LOG_FILE="/tmp/e2e_validation.log"

# shellcheck source=/dev/null
source "$REPO_DIR/scripts/vps/lib/umbral_alerting.sh"
umbral_load_env || true

if ! REPO="$REPO_DIR" bash "$REPO_DIR/scripts/vps/ensure-main-for-run.sh"; then
    echo "[ensure-main-for-run] blocked; skipping this run" >&2
    exit 0
fi
cd "$REPO_DIR"

# Activate virtualenv if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo ""
echo "=== E2E Validation â€” $(date -u +"%Y-%m-%d %H:%M UTC") ==="

# Run E2E validation suite with Notion posting.
#
# `set -euo pipefail` (arriba) abortaba el script en cuanto e2e_validation.py
# terminaba con sys.exit(1), de modo que TODO lo que sigue —la captura del codigo,
# el [FAIL] y la alerta— era codigo inalcanzable. Medido: 29 «passed», 0 fallos
# registrados, y dos corridas reales cerradas en 11/17. Incidente Linear UMB-276.
# Por eso el codigo de salida se captura con set +e explicito.
set +e
PYTHONPATH="$REPO_DIR" python3 scripts/e2e_validation.py --notion 2>&1
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 0 ]; then
    echo "[OK] E2E validation passed"
    umbral_heartbeat_write e2e-validation
    if umbral_alert_active e2e-validation; then
        RC_INFO=0
        # Se nombra el incidente que cierra —no la fecha, que cambia siempre y
        # haria que dos recuperaciones seguidas nunca se deduplicaran.
        umbral_alert e2e-validation "la suite E2E vuelve a pasar" "Cierra el incidente $(umbral_alert_fingerprint e2e-validation | cut -c1-12)." info || RC_INFO=$?
        # El incidente no se cierra hasta que el aviso de recuperacion sale de
        # verdad: rc=2 es "no se pudo entregar", y entonces se conserva el
        # estado para reintentarlo en el proximo ciclo. rc=1 es "callado por
        # duplicado", que significa que ya se conto.
        if [ "$RC_INFO" -ne 2 ]; then umbral_clear_alert e2e-validation >/dev/null || true; fi
    fi
else
    echo "[FAIL] E2E validation had failures (exit code $EXIT_CODE)"

    # Aviso por la libreria compartida: carga el env (antes WORKER_TOKEN llegaba
    # vacio bajo cron), trocea por debajo del maximo de Notion y deduplica.
    umbral_alert e2e-validation \
        "la suite E2E tiene fallos (exit $EXIT_CODE)" \
        "Corrida del $(date -u +'%Y-%m-%d %H:%M UTC'). Detalle en /tmp/e2e_validation.log." \
        error || true
fi

exit $EXIT_CODE
