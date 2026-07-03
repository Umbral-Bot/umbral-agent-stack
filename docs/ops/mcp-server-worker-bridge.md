# `mcp_server/` — bridge Worker→MCP (documentado, dormido hasta O2)

- **Status:** v1 — 2026-07-03 · Ola O1 (Fase 5). **No desplegar en VPS/OpenClaw en O1.**
- **Código:** [`mcp_server/`](../../mcp_server/) (`server.py`, `tool_registry.py`) · tests: [`tests/test_mcp_server.py`](../../tests/test_mcp_server.py) · dep `mcp[cli]>=1.0.0,<2.0.0` en `pyproject.toml`.

## Qué hace

Expone los **73 task handlers del Worker** como tools MCP (nombres `notion.upsert_task` → `notion_upsert_task`; descripciones auto-generadas del docstring del handler) y **proxya cada tool call al Worker HTTP** (`POST /run`).

- Transports: `stdio` (default, para VS Code/Claude Desktop/agents locales) y `sse` (HTTP remoto, `--port 8090`).
- Auth: `WORKER_URL` + `WORKER_TOKEN`. **No maneja `NOTION_API_KEY` directamente** — la identidad Notion sigue siendo la del Worker (bots Rick/Supervisor), con su audit y validaciones.
- Valor diferencial vs MCP Notion genérico: los tools espejo **conservan** schema tipado, idempotencia, gates y `ops_log.jsonl` del worker.

## Smoke local (solo lectura de código / tests)

```bash
# En el clon (Windows o VPS dev), con [test] instalado:
WORKER_TOKEN=test python -m pytest tests/test_mcp_server.py -v
# Arranque manual stdio (NO en producción):
WORKER_URL=http://localhost:8088 WORKER_TOKEN=<dev> python -m mcp_server.server
```

## Estado y roadmap

| Fase | Estado |
|---|---|
| O1 (hoy) | **Documentado, dormido.** No registrar en `openclaw.json`, no correr como servicio en VPS. |
| O2 (ST-3, gate G-NMCP-2) | Evaluación como bridge gobernado worker→IDE/agents, **después** de la allowlist per-agent del worker (audit 006 §6.7.1) y del spec de audit unificado (ST-4). |

Contexto de decisión: [audit #512 §5 ST-3](../audits/notion-mcp-opportunity-audit-2026-07-03.md) · superficie IDE: [`notion-mcp-ide-surface.md`](notion-mcp-ide-surface.md).
