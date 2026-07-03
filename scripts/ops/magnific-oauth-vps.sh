#!/usr/bin/env bash
# Completa OAuth de Magnific MCP en la VPS (usuario rick).
# Desde Windows, en otra terminal, dejá el túnel abierto:
#   ssh -N -L 11390:127.0.0.1:11390 vps-umbral
#
# Luego en la VPS:
#   bash ~/umbral-agent-stack/scripts/ops/magnific-oauth-vps.sh
set -euo pipefail

export PATH="${HOME}/.npm-global/bin:/usr/bin:/bin:${PATH}"

PORT="${MAGNIFIC_MCP_OAUTH_PORT:-11390}"
REMOTE_URL="${MAGNIFIC_MCP_URL:-https://mcp.magnific.com}"

echo "==> Magnific MCP OAuth bootstrap"
echo "    Remote: ${REMOTE_URL}"
echo "    Callback port (VPS): ${PORT}"
echo ""
echo "En Windows (otra terminal), mantené el túnel:"
echo "  ssh -N -L ${PORT}:127.0.0.1:${PORT} vps-umbral"
echo ""
echo "Cuando el script imprima la URL de auth.magnific.com, abrila en tu browser."
echo "El redirect a http://localhost:${PORT}/oauth/callback debe volver por el túnel."
echo ""

# Limpia lock huérfano si quedó de un intento anterior
LOCK_DIR="${HOME}/.mcp-auth/mcp-remote-0.1.37"
if [[ -d "${LOCK_DIR}" ]]; then
  for f in "${LOCK_DIR}"/*_lock.json; do
    [[ -f "$f" ]] || continue
    echo "==> Lockfile existente: $f (se reutiliza o reemplaza al iniciar mcp-remote)"
  done
fi

echo "==> Iniciando mcp-remote (Ctrl+C tras 'Authentication successful' o token guardado)"
echo ""

# Sin timeout: espera hasta que David complete OAuth
exec npx -y mcp-remote "${REMOTE_URL}"
