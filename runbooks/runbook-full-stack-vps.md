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

**Opción A — systemd:**
```bash
mkdir -p ~/.config/systemd/user
sed "s|%h|$HOME|g" ~/umbral-agent-stack/openclaw/systemd/openclaw-dispatcher.service.template > ~/.config/systemd/user/openclaw-dispatcher.service
systemctl --user daemon-reload
systemctl --user enable --now openclaw-dispatcher
systemctl --user status openclaw-dispatcher
```

**Opción B — manual (background):**
```bash
cd ~/umbral-agent-stack
source .venv/bin/activate && set -a && source ~/.config/openclaw/env && set +a
export PYTHONPATH=$HOME/umbral-agent-stack
nohup python3 -m dispatcher.service >> /tmp/dispatcher.log 2>&1 &
```

### 4. Notion poller (opcional)

En sesión separada o como servicio:
```bash
cd ~/umbral-agent-stack && source .venv/bin/activate && set -a && source ~/.config/openclaw/env && set +a
export PYTHONPATH=$HOME/umbral-agent-stack
python3 -m dispatcher.notion_poller
```

### 5. Test E2E

```bash
cd ~/umbral-agent-stack
export $(grep -v '^#' ~/.config/openclaw/env | xargs)
export PYTHONPATH=$HOME/umbral-agent-stack
python3 scripts/test_s2_dispatcher.py
```
