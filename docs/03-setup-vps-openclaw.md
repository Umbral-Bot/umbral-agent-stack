# 03 - Setup VPS + OpenClaw

## Pre-requisitos

- VPS con Ubuntu 24 LTS (Hostinger o similar)
- Acceso SSH configurado
- OpenClaw instalado

## Servicio systemd

### Verificar estado

```bash
systemctl --user status openclaw-gateway
```

### Ver puertos

```bash
ss -lntp | grep :18789
```

### Logs

```bash
journalctl --user -u openclaw-gateway -n 100 --no-pager
```

### Logs en vivo

```bash
journalctl --user -u openclaw-gateway -f
```

## Configuracion de variables de entorno

### Crear archivo env

```bash
mkdir -p ~/.config/openclaw
cat > ~/.config/openclaw/env << 'EOF'
# Worker HTTP (FastAPI en Windows via Tailscale)
WORKER_URL=http://CHANGE_ME_WINDOWS_TAILSCALE_IP:8088
WORKER_TOKEN=CHANGE_ME_WORKER_TOKEN

# Otros (agregar segun necesidad)
# OPENAI_API_KEY=CHANGE_ME_OPENAI_KEY
EOF

chmod 600 ~/.config/openclaw/env
```

### Unit systemd con EnvironmentFile

```ini
# ~/.config/systemd/user/openclaw-gateway.service
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/node %h/.npm-global/lib/node_modules/openclaw/dist/index.js gateway --port 18789
Restart=always
RestartSec=5
KillMode=process
Environment=HOME=%h
Environment=TMPDIR=/tmp
Environment=PATH=%h/.local/bin:%h/.npm-global/bin:/usr/local/bin:/usr/bin:/bin
Environment=OPENCLAW_GATEWAY_PORT=18789
Environment=OPENCLAW_SYSTEMD_UNIT=openclaw-gateway.service
Environment=OPENCLAW_SERVICE_MARKER=openclaw
Environment=OPENCLAW_SERVICE_KIND=gateway
EnvironmentFile=%h/.config/openclaw/env

[Install]
WantedBy=default.target
```

### Aplicar cambios

```bash
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway
systemctl --user enable openclaw-gateway
```

### Validar que las variables se cargaron

```bash
PID=$(systemctl --user show -p MainPID openclaw-gateway | cut -d= -f2)
cat /proc/$PID/environ | tr '\0' '\n' | grep WORKER
```

Debe mostrar algo como:

```text
WORKER_URL=http://...
WORKER_TOKEN=...
```

## Acceso a Control UI

### Importante: no exponer los puertos 18789/18791 a internet

La UI de OpenClaw contiene controles administrativos y no debe exponerse directamente.

### Opcion 1: SSH port forwarding

```bash
ssh -N -L 18789:127.0.0.1:18789 -L 18791:127.0.0.1:18791 rick@VPS_PUBLIC_IP
```

Luego abrir:

- `http://localhost:18789`
- `http://localhost:18791`

### Opcion 2: Tailscale

```bash
http://VPS_TAILSCALE_IP:18789
```

## Reinicio controlado

```bash
systemctl --user restart openclaw-gateway
```

## Verificacion completa

```bash
systemctl --user status openclaw-gateway
openclaw status --all
openclaw models status
openclaw status --all | grep -i telegram
```

## OpenClaw Node en la VM (PCRick)

El nodo OpenClaw en la VM conecta al gateway de la VPS via Tailscale, permitiendo a Rick controlar el navegador y otros recursos en PCRick.

### Token del gateway

1. En la VPS:

```bash
NEW_TOKEN=$(openssl rand -hex 32)
openclaw config set gateway.auth.token "$NEW_TOKEN"
systemctl --user restart openclaw-gateway
```

2. En la VM:

```powershell
$env:OPENCLAW_GATEWAY_TOKEN = "EL_TOKEN_GENERADO"
openclaw node run --host srv1431451.tail0b266a.ts.net --port 18789 --tls
```

### Arranque automatico

Para que el node arranque tras reiniciar la VM, usar el servicio NSSM segun [runbooks/runbook-vm-openclaw-node.md](../runbooks/runbook-vm-openclaw-node.md).

### Aprobar dispositivos pendientes

```bash
openclaw devices list
openclaw devices approve <requestId>
```

## Notion como tool

Rick recomienda configurar Notion como herramienta y no como skill. Ver `docs/rick-notion-tool-instead-of-skill.md`.
