#!/usr/bin/env bash
# ============================================================
# openclaw-systemd-setup.sh - Configura OpenClaw Gateway como
# servicio systemd de usuario en la VPS.
# ============================================================
set -euo pipefail

OPENCLAW_CONFIG_DIR="$HOME/.config/openclaw"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CANONICAL_UNIT="openclaw-gateway.service"
CANONICAL_UNIT_PATH="$SYSTEMD_USER_DIR/$CANONICAL_UNIT"
LEGACY_UNIT="openclaw.service"
LEGACY_UNIT_PATH="$SYSTEMD_USER_DIR/$LEGACY_UNIT"
LEGACY_DISABLED_PATH="$SYSTEMD_USER_DIR/$LEGACY_UNIT.legacy-disabled"

echo "=== Configurando OpenClaw Gateway como servicio systemd ==="

mkdir -p "$OPENCLAW_CONFIG_DIR"
mkdir -p "$SYSTEMD_USER_DIR"

if [ -f "$OPENCLAW_CONFIG_DIR/env" ]; then
    echo "WARN: $OPENCLAW_CONFIG_DIR/env ya existe. No se sobreescribe."
    echo "      Para regenerar, eliminar manualmente y volver a ejecutar."
else
    cp "$REPO_ROOT/openclaw/env.template" "$OPENCLAW_CONFIG_DIR/env"
    chmod 600 "$OPENCLAW_CONFIG_DIR/env"
    echo "Creado: $OPENCLAW_CONFIG_DIR/env (permisos: 600)"
    echo "IMPORTANTE: editar y reemplazar los valores CHANGE_ME_*"
fi

if [ -f "$CANONICAL_UNIT_PATH" ]; then
    echo "WARN: $CANONICAL_UNIT_PATH ya existe. No se sobreescribe."
else
    cp "$REPO_ROOT/openclaw/systemd/openclaw-gateway.service.template" "$CANONICAL_UNIT_PATH"
    echo "Creado: $CANONICAL_UNIT_PATH"
fi

if [ -f "$LEGACY_UNIT_PATH" ]; then
    echo "Legacy detectado: $LEGACY_UNIT_PATH"
    systemctl --user disable --now "$LEGACY_UNIT" || true
    if [ ! -f "$LEGACY_DISABLED_PATH" ]; then
        mv "$LEGACY_UNIT_PATH" "$LEGACY_DISABLED_PATH"
        echo "Legacy archivado en: $LEGACY_DISABLED_PATH"
    else
        echo "WARN: $LEGACY_DISABLED_PATH ya existe. Se deja el legacy sin mover."
    fi
fi

echo
echo "=== Habilitando linger ==="
loginctl enable-linger "$(whoami)"

echo
echo "=== Recargando systemd ==="
systemctl --user daemon-reload

echo
echo "=== Habilitando servicio canonico ==="
systemctl --user enable "$CANONICAL_UNIT"

echo
echo "=== Reiniciando servicio canonico ==="
systemctl --user restart "$CANONICAL_UNIT"

echo
echo "=== Estado ==="
systemctl --user status "$CANONICAL_UNIT" --no-pager

echo
echo "IMPORTANTE: editar $OPENCLAW_CONFIG_DIR/env con valores reales."
echo "Despues: systemctl --user restart $CANONICAL_UNIT"
