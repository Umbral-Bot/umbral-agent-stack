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

## Hardening minimo recomendado

Para no dejar el gateway en el contexto implicito `full`, la config de OpenClaw en la VPS debe fijar un perfil base de tools y el plugin `umbral-worker` debe apuntar a un `baseUrl` explicito en `plugins.entries`.

Ejemplo de fragmento recomendado en `~/.openclaw/openclaw.json`:

```json
{
  "tools": {
    "profile": "coding"
  },
  "plugins": {
    "entries": {
      "umbral-worker": {
        "config": {
          "baseUrl": "http://127.0.0.1:8088",
          "interactiveBaseUrl": "http://100.109.16.40:8089",
          "tokenFile": "~/.config/openclaw/worker-token",
          "defaultTeam": "system",
          "defaultTaskType": "general",
          "timeoutMs": 120000
        }
      }
    }
  }
}
```

Notas:

- El plugin `umbral-worker` ya no debe depender de `WORKER_URL` como fallback generico dentro del gateway; el destino canonico se fija en `plugins.entries.umbral-worker.config.baseUrl`.
- Si necesitas browser/gui contra la VM, define `interactiveBaseUrl` en `plugins.entries.umbral-worker.config` en vez de depender de `WORKER_URL_VM_INTERACTIVE` dentro del plugin.
- El bearer token del plugin debe ir en `tokenFile` con permisos `600`; el plugin no debe leer `WORKER_TOKEN` directamente desde `process.env`.
- `gateway.trustedProxies` solo debe configurarse si realmente expones la Control UI detras de un reverse proxy. Si accedes por loopback, Tailscale directo o tunel SSH, mantenerlo vacio es aceptable.

Ejemplo para materializar `tokenFile` desde la env existente:

```bash
grep '^WORKER_TOKEN=' ~/.config/openclaw/env | cut -d= -f2- > ~/.config/openclaw/worker-token
chmod 600 ~/.config/openclaw/worker-token
```

## Gobernanza del workspace

OpenClaw distingue dos archivos distintos en el workspace:

- `BOOTSTRAP.md`: asset de primer arranque / reconstruccion del workspace. Conviene versionarlo en el repo, pero no mantenerlo persistente en workspaces maduros.
- `HEARTBEAT.md`: checklist persistente y breve que si conviene mantener por rol.

Convencion canonica para este repo:

- `BOOTSTRAP.md` vive versionado en `openclaw/workspace-templates/BOOTSTRAP.md` como ritual one-shot para onboarding o rebuild del workspace.
- `HEARTBEAT.md` vive versionado en `openclaw/workspace-templates/HEARTBEAT.md` y puede tener overrides por agente en `openclaw/workspace-agent-overrides/<agentId>/HEARTBEAT.md`.
- En workspaces maduros, `BOOTSTRAP.md` no debe persistirse. La configuracion recomendada es `agents.defaults.skipBootstrap: true` en `~/.openclaw/openclaw.json`.
- El archivo persistente de gobernanza por agente es `HEARTBEAT.md`; no reemplaza a `AGENTS.md`, sino que lo complementa.

Ejemplo minimo en `~/.openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "skipBootstrap": true
    }
  }
}
```

Para sincronizar estos archivos en la VPS despues de `git pull`:

```bash
cd ~/umbral-agent-stack
python3 scripts/sync_openclaw_workspace_governance.py --dry-run
python3 scripts/sync_openclaw_workspace_governance.py --execute
systemctl --user restart openclaw-gateway
```

Verificacion minima:

```bash
/home/rick/.npm-global/bin/openclaw status --all
```

Es aceptable que los agentes activos sigan apareciendo con `Bootstrap file ABSENT` si el workspace ya esta maduro y `skipBootstrap=true` quedo fijado.

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
