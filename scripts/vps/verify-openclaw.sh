#!/usr/bin/env bash
# ============================================================
# verify-openclaw.sh â€” VerificaciÃ³n rÃ¡pida de OpenClaw + worker
# ============================================================
set -euo pipefail

echo "=== VerificaciÃ³n del Umbral Agent Stack ==="
echo ""

# 1. OpenClaw service
echo "1. OpenClaw Service:"
if systemctl --user is-active openclaw > /dev/null 2>&1; then
    echo "   âœ… OpenClaw: RUNNING"
else
    echo "   âŒ OpenClaw: NOT RUNNING"
fi

# 2. OpenClaw status
echo ""
echo "2. OpenClaw Status:"
openclaw status --all 2>/dev/null || echo "   âš ï¸  No se pudo obtener status"

# 3. Tailscale
echo ""
echo "3. Tailscale:"
if tailscale status > /dev/null 2>&1; then
    echo "   âœ… Tailscale: CONNECTED"
    echo "   IP: $(tailscale ip -4)"
else
    echo "   âŒ Tailscale: NOT CONNECTED"
fi

# 4. Worker health
echo ""
echo "4. Worker Health:"
if [ -n "${WORKER_URL:-}" ]; then
    HEALTH=$(curl -sf "${WORKER_URL}/health" 2>/dev/null) && {
        echo "   âœ… Worker: OK â€” $HEALTH"
    } || {
        echo "   âŒ Worker: NOT REACHABLE at $WORKER_URL"
    }
else
    echo "   âš ï¸  WORKER_URL not set â€” skipping"
fi

echo ""
echo "=== VerificaciÃ³n completa ==="
