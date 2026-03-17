#!/usr/bin/env bash
# ============================================================
# install-tailscale.sh â€” Instala Tailscale en Ubuntu/Debian VPS
# ============================================================
set -euo pipefail

echo "=== Instalando Tailscale ==="

# Instalar
curl -fsSL https://tailscale.com/install.sh | sh

# Iniciar con SSH habilitado
echo ""
echo "=== Iniciando Tailscale ==="
sudo tailscale up --ssh

# Mostrar estado
echo ""
echo "=== Estado ==="
tailscale status

echo ""
echo "=== IP Tailscale ==="
tailscale ip -4

echo ""
echo "Tailscale instalado. Anotar la IP para configurar WORKER_URL."
