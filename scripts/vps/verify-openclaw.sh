#!/usr/bin/env bash
# ============================================================
# verify-openclaw.sh — Verificación rápida de OpenClaw + worker
# ============================================================
set -euo pipefail

echo "=== Verificación del Umbral Agent Stack ==="
echo ""

# 1. OpenClaw service
echo "1. OpenClaw Service:"
if systemctl --user is-active openclaw > /dev/null 2>&1; then
    echo "   ✅ OpenClaw: RUNNING"
else
    echo "   ❌ OpenClaw: NOT RUNNING"
fi

# 2. OpenClaw status
echo ""
echo "2. OpenClaw Status:"
openclaw status --all 2>/dev/null || echo "   ⚠️  No se pudo obtener status"

# 3. Tailscale
echo ""
echo "3. Tailscale:"
if tailscale status > /dev/null 2>&1; then
    echo "   ✅ Tailscale: CONNECTED"
    echo "   IP: $(tailscale ip -4)"
else
    echo "   ❌ Tailscale: NOT CONNECTED"
fi

# 4. Worker health
echo ""
echo "4. Worker Health:"
if [ -n "${WORKER_URL:-}" ]; then
    HEALTH=$(curl -sf "${WORKER_URL}/health" 2>/dev/null) && {
        echo "   ✅ Worker: OK — $HEALTH"
    } || {
        echo "   ❌ Worker: NOT REACHABLE at $WORKER_URL"
    }
else
    echo "   ⚠️  WORKER_URL not set — skipping"
fi

echo ""
echo "=== Verificación completa ==="
