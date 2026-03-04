# AGENTS.md

## Coordinación inter-agentes

Este repositorio es trabajado por múltiples agentes AI de forma coordinada.
Antes de empezar cualquier trabajo, lee el protocolo y el board:

1. **Protocolo**: [`.agents/PROTOCOL.md`](.agents/PROTOCOL.md) — reglas de coordinación, formato de tareas, ciclo de vida.
2. **Board**: [`.agents/board.md`](.agents/board.md) — estado actual de tareas asignadas.
3. **Tareas**: [`.agents/tasks/`](.agents/tasks/) — archivos individuales por tarea.

> Si sos Antigravity o Codex, buscá tareas con `assigned_to` igual a tu nombre y seguí las instrucciones del protocolo.

---

## Cursor Cloud specific instructions

### Overview

Umbral Agent Stack is a Python-based multi-agent orchestration system with two core services:

- **Worker** (`worker/`): FastAPI HTTP service on port 8088 — receives and executes tasks. Auth via `WORKER_TOKEN` Bearer token.
- **Dispatcher** (`dispatcher/`): Control Plane service that polls a Redis task queue and routes tasks to the Worker or executes locally.
- **Client** (`client/`): Python SDK for calling the Worker API.

### Running tests

```bash
source .venv/bin/activate
WORKER_TOKEN=test python -m pytest tests/ -v
```

Tests use `fakeredis` (no real Redis needed). All 130+ tests should pass (1 may be skipped if `cryptography` is not installed).

### Starting services for development

1. **Redis** (required by Dispatcher):
   ```bash
   redis-server --daemonize yes
   ```

2. **Worker** (FastAPI):
   ```bash
   source .venv/bin/activate
   export WORKER_TOKEN="dev-test-token-12345"
   python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info
   ```

3. **Dispatcher** (requires Redis + Worker running):
   ```bash
   source .venv/bin/activate
   export WORKER_TOKEN="dev-test-token-12345"
   export WORKER_URL="http://localhost:8088"
   export REDIS_URL="redis://localhost:6379/0"
   python -m dispatcher.service
   ```

### Gotchas

- `python3.12-venv` must be installed via apt before creating the virtualenv (`sudo apt-get install -y python3.12-venv`).
- Redis must be installed via apt (`sudo apt-get install -y redis-server`) and started manually with `redis-server --daemonize yes` — systemd is not available in this environment.
- Notion tasks (`notion.*`) require `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`, and `NOTION_GRANOLA_DB_ID` env vars. Without them, only `ping` task works fully.
- The `.env` file is not auto-loaded by the app; environment variables must be exported in the shell or set inline.
