# 03 — Setup VPS + OpenClaw

## Pre-requisitos

- VPS con Ubuntu 24 LTS (Hostinger o similar)
- SSH acceso configurado
- OpenClaw instalado

## Servicio systemd

### Verificar estado

```bash
systemctl --user status openclaw
```

### Ver puertos

```bash
ss -lntp | grep :18789
```

### Logs

```bash
journalctl --user -u openclaw -n 100 --no-pager
```

### Logs en vivo (follow)

```bash
journalctl --user -u openclaw -f
```

## Configuración de Variables de Entorno

### Crear archivo env

```bash
mkdir -p ~/.config/openclaw
cat > ~/.config/openclaw/env << 'EOF'
# Worker HTTP (FastAPI en Windows vía Tailscale)
WORKER_URL=http://CHANGE_ME_WINDOWS_TAILSCALE_IP:8088
WORKER_TOKEN=CHANGE_ME_WORKER_TOKEN

# Otros (agregar según necesidad)
# OPENAI_API_KEY=CHANGE_ME_OPENAI_KEY
EOF

# Proteger el archivo
chmod 600 ~/.config/openclaw/env
```

### Systemd Unit con EnvironmentFile

```ini
# ~/.config/systemd/user/openclaw.service
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=%h/.config/openclaw/env
ExecStart=/usr/local/bin/openclaw serve
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

### Aplicar cambios

```bash
systemctl --user daemon-reload
systemctl --user restart openclaw
systemctl --user enable openclaw
```

### Validar que las variables se cargaron

```bash
# Obtener PID
PID=$(systemctl --user show -p MainPID openclaw | cut -d= -f2)

# Verificar variables
cat /proc/$PID/environ | tr '\0' '\n' | grep WORKER
```

Debe mostrar:
```
WORKER_URL=http://...
WORKER_TOKEN=...
```

## Acceso a Control UI

### ⚠️ IMPORTANTE: No exponer los puertos 18789/18791 a internet

La UI de OpenClaw contiene controles administrativos y NUNCA debe ser expuesta directamente.

### Opción 1: SSH Port-Forwarding (recomendado)

```bash
ssh -N -L 18789:127.0.0.1:18789 -L 18791:127.0.0.1:18791 rick@VPS_PUBLIC_IP
```

Después, abrir en el navegador local:
- **Control UI**: `http://localhost:18789`
- **API**: `http://localhost:18791`

> **Nota**: `localhost` y `127.0.0.1` funcionan igual porque el túnel SSH re-mapea el puerto del VPS al loopback local de tu PC. OpenClaw escucha en `127.0.0.1` en el VPS, así que la conexión SSH accede directamente.

### Opción 2: Tailscale (alternativa)

Si Tailscale está configurado y confías en la red mesh:

```bash
# Desde PC con Tailscale, acceder directamente
http://VPS_TAILSCALE_IP:18789
```

> Esto es seguro porque Tailscale es una red privada, pero se prefiere SSH tunnel para mayor control y auditabilidad.

## Reinicio controlado

```bash
systemctl --user restart openclaw
```

## Verificación completa

```bash
# Estado del servicio
systemctl --user status openclaw

# Estado de OpenClaw
openclaw status --all

# Estado de modelos
openclaw models status

# Verificar Telegram
openclaw status --all | grep -i telegram
```
