#!/usr/bin/env bash
# Configura Magnific MCP en OpenClaw VPS (Rick).
# Ejecutar en la VPS como usuario rick:
#   bash ~/umbral-agent-stack/scripts/ops/setup-magnific-mcp-vps.sh
set -euo pipefail

export PATH="${HOME}/.npm-global/bin:/usr/bin:/bin:${PATH}"

JSON='{"command":"npx","args":["-y","mcp-remote","https://mcp.magnific.com"]}'

echo "==> Registrando MCP magnific en openclaw.json"
openclaw mcp set magnific "$JSON"

echo "==> MCP servers configurados:"
openclaw mcp list

echo "==> Reiniciando openclaw-gateway"
systemctl --user restart openclaw-gateway
sleep 2
systemctl --user is-active openclaw-gateway

echo ""
echo "OK. Próximo paso OBLIGATORIO: completar OAuth antes de usar Rick."
echo "  1) En Windows: ssh -N -L 11390:127.0.0.1:11390 vps-umbral"
echo "  2) En VPS: bash ~/umbral-agent-stack/scripts/ops/magnific-oauth-vps.sh"
echo "  3) Abrir URL auth.magnific.com que imprima el script (no URLs viejas)"
echo "  4) Verificar: ls ~/.mcp-auth/mcp-remote-0.1.37/*_tokens.json"
echo "Smoke: Rick o openclaw agent → tool account_balance (Magnific)"
