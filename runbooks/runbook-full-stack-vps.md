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

### 3. Dispatcher y Notion poller (si los usás)

En la VPS, en sesiones separadas o como servicios:

```bash
cd ~/umbral-agent-stack
export $(grep -v '^#' ~/.config/openclaw/env | xargs)
export PYTHONPATH=$HOME/umbral-agent-stack
python3 -m dispatcher.service     # Cola → Worker
python3 -m dispatcher.notion_poller   # Notion → Cola
```

### 4. Test E2E

```bash
cd ~/umbral-agent-stack
export $(grep -v '^#' ~/.config/openclaw/env | xargs)
export PYTHONPATH=$HOME/umbral-agent-stack
python3 scripts/test_s2_dispatcher.py
```
