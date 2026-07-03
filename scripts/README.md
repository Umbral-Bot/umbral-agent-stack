# scripts/ — reglas de uso

## Regla Notion (QW-3 · Ola O1, 2026-07-03)

**Lecturas ad-hoc de Notion → usar el MCP del IDE. NO crear scripts nuevos que solo lean Notion.**

- Writes de producción → **Worker REST únicamente** (`worker/tasks/notion.py`), nunca scripts sueltos ni MCP.
- Tabla de decisión completa de superficies: [`docs/ops/notion-mcp-ide-surface.md`](../docs/ops/notion-mcp-ide-surface.md).
- Los ~40 scripts existentes que tocan Notion (`audit_notion_publicaciones.py`, `check_notion_comments_raw.py`, `get_db_parent.py`, `granola_*`, `dashboard_*`, `notion_curate_ops_vps.py`, `scripts/discovery/*`, etc.) quedan **legacy-ok**: se mantienen, no se borran en O1, pero no son el patrón a replicar para lecturas nuevas.
- Excepción válida para script nuevo: forma parte de un pipeline productivo (cron/stage) con tests — no una lectura exploratoria.

## Convenciones generales

- PowerShell → tareas Windows/VM; Bash → operaciones VPS; Python → todo lo demás (PEP 8, type hints).
- Credenciales SIEMPRE por variables de entorno (VPS: `~/.config/openclaw/env`); nada hardcodeado ni commiteado.
- Scripts se invocan on-demand: no requieren deploy/restart de servicios al cambiar (ver tabla en `.github/copilot-instructions.md`).
