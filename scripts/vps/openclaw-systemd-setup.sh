#!/usr/bin/env bash
# ============================================================
# openclaw-systemd-setup.sh — Configura OpenClaw como servicio systemd
# ============================================================
# Crea el archivo env desde template y configura el unit systemd.
# IMPORTANTE: Editar los valores CHANGE_ME_* después de ejecutar.
# ============================================================
set -euo pipefail

OPENCLAW_CONFIG_DIR="$HOME/.config/openclaw"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Configurando OpenClaw como servicio systemd ==="

# --- Crear directorio de config ---
mkdir -p "$OPENCLAW_CONFIG_DIR"
mkdir -p "$SYSTEMD_USER_DIR"

# --- Copiar env template ---
if [ -f "$OPENCLAW_CONFIG_DIR/env" ]; then
    echo "WARN: $OPENCLAW_CONFIG_DIR/env ya existe. No se sobreescribe."
    echo "      Para regenerar, eliminar manualmente y volver a ejecutar."
else
    cp "$REPO_ROOT/openclaw/env.template" "$OPENCLAW_CONFIG_DIR/env"
    chmod 600 "$OPENCLAW_CONFIG_DIR/env"
    echo "Creado: $OPENCLAW_CONFIG_DIR/env (permisos: 600)"
    echo "IMPORTANTE: Editar y reemplazar los valores CHANGE_ME_*"
fi

# --- Copiar unit systemd ---
if [ -f "$SYSTEMD_USER_DIR/openclaw.service" ]; then
    echo "WARN: $SYSTEMD_USER_DIR/openclaw.service ya existe. No se sobreescribe."
else
    cp "$REPO_ROOT/openclaw/systemd/openclaw.service.template" "$SYSTEMD_USER_DIR/openclaw.service"
    echo "Creado: $SYSTEMD_USER_DIR/openclaw.service"
fi

# --- Enable linger so user services survive headless reboots ---
echo ""
echo "=== Habilitando loginctl linger (necesario para reboot sin sesión interactiva) ==="
loginctl enable-linger "$(whoami)"

# --- Reload y restart ---
echo ""
echo "=== Recargando systemd ==="
systemctl --user daemon-reload

echo ""
echo "=== Habilitando servicio ==="
systemctl --user enable openclaw

echo ""
echo "=== Reiniciando servicio ==="
systemctl --user restart openclaw

echo ""
echo "=== Estado ==="
systemctl --user status openclaw --no-pager

echo ""
echo "IMPORTANTE: Editar $OPENCLAW_CONFIG_DIR/env con valores reales."
echo "Después: systemctl --user restart openclaw"
