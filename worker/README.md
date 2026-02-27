# Umbral Worker (FastAPI)

Worker HTTP que recibe tareas desde el VPS (OpenClaw) vía Tailscale.

## Quickstart

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar token

```powershell
# PowerShell
$env:WORKER_TOKEN="CHANGE_ME_WORKER_TOKEN"
```

```bash
# Bash
export WORKER_TOKEN="CHANGE_ME_WORKER_TOKEN"
```

### 3. Iniciar (modo dev)

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8088 --log-level info
```

### 4. Probar

```bash
# Health (sin auth)
curl http://localhost:8088/health

# Run (con auth)
curl -X POST http://localhost:8088/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer CHANGE_ME_WORKER_TOKEN' \
  -d '{"task":"ping","input":{"msg":"hello"}}'
```

## API

| Endpoint | Method | Auth | Descripción |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/run` | POST | Bearer | Ejecutar tarea |

## Extensión

Para agregar nuevas tareas, editar `app.py`:

```python
def _handle_my_task(input_data: dict) -> dict:
    # Tu lógica aquí
    return {"result": "done"}

TASK_HANDLERS["my_task"] = _handle_my_task
```

## Servicio Windows (NSSM)

Ver `scripts/setup-openclaw-service.ps1` y [docs/06-setup-worker-windows.md](../docs/06-setup-worker-windows.md).
