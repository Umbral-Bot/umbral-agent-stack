#!/usr/bin/env bash
#
# Configura PATH para n8n (instalado en ~/.npm-global/bin) y opcionalmente
# servicio systemd user para que n8n quede en segundo plano y sobreviva reinicios.
#
# Ejecutar EN LA VPS como el usuario que instaló n8n (ej. rick):
#   cd ~/umbral-agent-stack && bash scripts/vps/n8n-path-and-service.sh
#
# Requisitos: n8n ya instalado (ej. npm install n8n -g con prefix ~/.npm-global).
set -e

NPM_GLOBAL_BIN="$HOME/.npm-global/bin"
PATH_LINE="export PATH=\"\$HOME/.npm-global/bin:\$PATH\""

# 1) Añadir PATH a .bashrc si no está
if [ -f "$HOME/.bashrc" ]; then
  if grep -q '.npm-global/bin' "$HOME/.bashrc" 2>/dev/null; then
    echo "[OK] PATH para n8n ya esta en .bashrc"
  else
    echo "" >> "$HOME/.bashrc"
    echo "# n8n (npm global)" >> "$HOME/.bashrc"
    echo "$PATH_LINE" >> "$HOME/.bashrc"
    echo "[OK] PATH anadido a .bashrc"
  fi
else
  echo "[INFO] No existe .bashrc; creando con PATH."
  echo "$PATH_LINE" > "$HOME/.bashrc"
fi

# Aplicar en esta sesión
export PATH="$HOME/.npm-global/bin:$PATH"

# 2) Comprobar que n8n existe
if ! command -v n8n >/dev/null 2>&1; then
  if [ -x "$NPM_GLOBAL_BIN/n8n" ]; then
    echo "[OK] n8n encontrado en $NPM_GLOBAL_BIN/n8n (usa 'n8n' en nuevas sesiones)"
  else
    echo "[ERROR] n8n no encontrado en $NPM_GLOBAL_BIN. Revisar instalacion."
    exit 1
  fi
else
  echo "[OK] n8n en PATH: $(command -v n8n)"
fi

# 3) Servicio systemd user (opcional): crear unit para n8n
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"
UNIT_FILE="$SYSTEMD_USER_DIR/n8n.service"

if [ ! -f "$UNIT_FILE" ]; then
  N8N_BIN="$HOME/.npm-global/bin/n8n"
  cat > "$UNIT_FILE" << UNIT
[Unit]
Description=n8n workflow automation
After=network.target

[Service]
Type=simple
ExecStart=$N8N_BIN start
Restart=on-failure
RestartSec=10
Environment=NODE_ENV=production

[Install]
WantedBy=default.target
UNIT
  echo "[OK] Creado $UNIT_FILE"
  echo "     Para activar: systemctl --user daemon-reload && systemctl --user enable n8n && systemctl --user start n8n"
  echo "     Ver estado:   systemctl --user status n8n"
else
  echo "[OK] Unit n8n.service ya existe"
fi

echo ""
echo "Siguiente: en esta sesion (o tras 'source ~/.bashrc') ejecuta 'n8n' para levantar la UI."
echo "O bien: systemctl --user start n8n (si activaste el servicio)."
