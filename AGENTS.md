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
pip install -e ".[test]"            # installs test + document-generation deps
WORKER_TOKEN=test python -m pytest tests/ -v
```

Tests use `fakeredis` (no real Redis needed). All 130+ tests should pass (1 skipped: encrypt/decrypt requires `cryptography` package).

Document-generation tests (`tests/test_document_generator.py`) require `docxtpl`, `fpdf2`, `python-docx`, and `python-pptx`. These are declared in `[project.optional-dependencies] test` inside `pyproject.toml`. If the packages are missing, the tests are skipped automatically via `pytest.importorskip`.

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
- Notion tasks (`notion.*`) require `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`; Granola pipeline also uses `NOTION_API_KEY` (Rick) and optionally `NOTION_GRANOLA_DB_ID`. Without core Notion vars, only `ping` task works fully.
- The `.env` file is not auto-loaded by the app; environment variables must be exported in the shell or set inline.
- The Dispatcher's health monitor will log `Health check failed: Connection refused` and eventually `VM declared OFFLINE` when running locally without a remote VM — this is expected and the Dispatcher still works in "partial" mode for local tasks.
