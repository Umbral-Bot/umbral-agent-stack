# Runbook: Levantar todo el sistema en la VPS

## Pre-requisitos

- SSH a VPS configurado (`vps-umbral` o `rick@srv...`)
- `~/.config/openclaw/env` con `WORKER_URL`, `WORKER_TOKEN`, `REDIS_URL` (y opcional `WORKER_URL_VM`, `NOTION_*`)

## Pasos

### 1. Sincronizar repo y levantar todo

```bash
ssh vps-umbral 'cd ~/umbral-agent-stack && git pull origin main && bash scripts/vps/full-stack-up.sh'
```

### 2. Verificar identidad Rick en OpenClaw

Los archivos `IDENTITY.md` y `SOUL.md` se copian de `openclaw/workspace-templates/` a `~/.openclaw/workspace/` si no existen. OpenClaw los lee al iniciar.

```bash
ssh vps-umbral 'ls -la ~/.openclaw/workspace/'
```

Debe existir `IDENTITY.md` y `SOUL.md`.

### 3. Dispatcher (obligatorio para E2E)

Metodo canonico:

```bash
cd ~/umbral-agent-stack
bash scripts/vps/dispatcher-service.sh start
bash scripts/vps/dispatcher-service.sh status
```

Si detectas drift entre `systemctl` y procesos reales:

```bash
cd ~/umbral-agent-stack
bash scripts/vps/dispatcher-service.sh reconcile
```

La operacion canonica del dispatcher en VPS queda solo por `systemd`. No usar `nohup python3 -m dispatcher.service` como camino normal.

### 4. Notion poller (opcional)

En sesion separada o como servicio:

```bash
cd ~/umbral-agent-stack && source .venv/bin/activate && set -a && source ~/.config/openclaw/env && set +a
export PYTHONPATH=$HOME/umbral-agent-stack
python3 -m dispatcher.notion_poller
```

### 5. Test E2E

```bash
cd ~/umbral-agent-stack
bash scripts/vps/dispatcher-service.sh smoke
```
