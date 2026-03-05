# Runbook: Worker en la VPS (VPS autosuficiente + VM opcional)

El Dispatcher usa **siempre** un Worker local en la VPS (`WORKER_URL=http://127.0.0.1:8088`). Opcionalmente, si definís `WORKER_URL_VM`, las tareas que requieren VM (improvement, lab) van a la VM cuando está online. Ver [docs/21-vps-autosufficient-dual-worker.md](../docs/21-vps-autosufficient-dual-worker.md).

## 1. Dependencias

En la VPS (repo en `~/umbral-agent-stack`):

```bash
cd ~/umbral-agent-stack
pip3 install -r worker/requirements.txt
```

## 2. Variables de entorno

El Worker necesita al menos `WORKER_TOKEN`. Para tareas Notion: `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`; para pipeline Granola (transcripciones) también `NOTION_GRANOLA_DB_ID` (usa la misma `NOTION_API_KEY` Rick).

Si ya tenés `~/.config/openclaw/env` con `WORKER_TOKEN` (y opcionalmente Notion), el mismo archivo sirve para el Worker. Si no:

```bash
# Añadir a ~/.config/openclaw/env (o crear)
WORKER_TOKEN=el_mismo_que_usa_el_dispatcher
# Opcional para Notion:
# NOTION_API_KEY=...
# NOTION_CONTROL_ROOM_PAGE_ID=...
# NOTION_GRANOLA_DB_ID=...   # solo pipeline Granola; usa NOTION_API_KEY (Rick)
```

## 3. Arrancar el Worker

### Opción A — Manual (una terminal)

```bash
cd ~/umbral-agent-stack
export $(grep -v '^#' ~/.config/openclaw/env | xargs)
export PYTHONPATH=$HOME/umbral-agent-stack
python3 -m uvicorn worker.app:app --host 127.0.0.1 --port 8088 --log-level info
```

### Opción B — Servicio systemd (usuario)

```bash
# Copiar template y ajustar WorkingDirectory si hace falta
mkdir -p ~/.config/systemd/user
sed "s|%h|$HOME|g" ~/umbral-agent-stack/openclaw/systemd/openclaw-worker-vps.service.template \
  | sed "s|%h|$HOME|g" > ~/.config/systemd/user/openclaw-worker-vps.service

# Si el repo no está en ~/umbral-agent-stack, editar WorkingDirectory y PYTHONPATH en el .service

systemctl --user daemon-reload
systemctl --user enable --now openclaw-worker-vps
systemctl --user status openclaw-worker-vps
```

## 4. Variables del Dispatcher (doble Worker)

En `~/.config/openclaw/env` (o donde definas las variables del Dispatcher):

```bash
# Worker local (VPS) — siempre
WORKER_URL=http://127.0.0.1:8088
WORKER_TOKEN=el_mismo_valor_que_el_worker
REDIS_URL=redis://localhost:6379/0

# VM opcional: si la definís, improvement/lab van a la VM cuando esté online
WORKER_URL_VM=http://IP_TAILSCALE_VM:8088
```

Reiniciar Dispatcher y, si usás el Notion poller, reiniciarlo también.

## 5. Comprobar

```bash
curl -s http://127.0.0.1:8088/health
curl -s -X POST http://127.0.0.1:8088/run \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -d '{"task":"ping","input":{"msg":"from vps"}}'
```

## 6. Uso con VM

Con el esquema dual no hace falta “volver” a la VM: si definiste `WORKER_URL_VM`, el Dispatcher envía improvement/lab a la VM cuando está online. El Worker en la VPS sigue atendiendo el resto. Si querés dejar de usar la VM, quitá o comentá `WORKER_URL_VM` y reiniciá el Dispatcher.
