# Runbook: Worker en la VPS (usar mientras sin VM)

Para operar Rick con el Worker en la VPS en lugar de la VM. Ver [docs/20-vm-to-vps-worker-migration.md](../docs/20-vm-to-vps-worker-migration.md).

## 1. Dependencias

En la VPS (repo en `~/umbral-agent-stack`):

```bash
cd ~/umbral-agent-stack
pip3 install -r worker/requirements.txt
```

## 2. Variables de entorno

El Worker necesita al menos `WORKER_TOKEN`. Para tareas Notion también: `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`, `NOTION_GRANOLA_DB_ID`.

Si ya tenés `~/.config/openclaw/env` con `WORKER_TOKEN` (y opcionalmente Notion), el mismo archivo sirve para el Worker. Si no:

```bash
# Añadir a ~/.config/openclaw/env (o crear)
WORKER_TOKEN=el_mismo_que_usa_el_dispatcher
# Opcional para Notion:
# NOTION_API_KEY=...
# NOTION_CONTROL_ROOM_PAGE_ID=...
# NOTION_GRANOLA_DB_ID=...
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

## 4. Apuntar el Dispatcher al Worker en la VPS

En `~/.config/openclaw/env` (o donde definas las variables del Dispatcher):

```bash
WORKER_URL=http://127.0.0.1:8088
WORKER_TOKEN=el_mismo_valor_que_el_worker
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

## 6. Volver a usar la VM

Poner en env `WORKER_URL=http://IP_TAILSCALE_VM:8088` (ej. `http://100.109.16.40:8088`), reiniciar Dispatcher. Opcional: parar el Worker en la VPS con `systemctl --user stop openclaw-worker-vps`.
