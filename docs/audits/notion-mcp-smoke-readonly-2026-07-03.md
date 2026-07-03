# Smoke read-only Notion MCP IDE — QW-2 · O1

- **Date:** 2026-07-03 · Task `2026-07-03-008` (Ola O1, gate G-NMCP-1).
- **Objetivo:** cerrar la Fase B BLOCKED-parcial del [audit #512](notion-mcp-opportunity-audit-2026-07-03.md): verificar identidad (`get-self`), workspace visible, transport, y un search/fetch acotado — todo read-only.
- **Veredicto:** `QW2_SMOKE_BLOCKED` — no ejecutable en esta sesión.

## Qué pasó

Las tools `notion-API-*` del host **fueron removidas de la sesión Copilot antes de esta ejecución** (tool-change notice 2026-07-03 10:13; mismo estado que impidió el smoke durante el audit #512). Precondición del megaprompt ("Notion MCP conectado en el host, tools visibles") **no se cumple** → 0 llamadas MCP ejecutadas, 0 writes, 0 lecturas.

## Evidencia disponible (del registro del host, sesión del audit)

- Catálogo: ~25 tools `notion-API-*` (wrapper OpenAPI estilo `@notionhq/notion-mcp-server`), incl. `post-search`, `retrieve-a-page`, `retrieve-a-database`, `query-data-source`, `retrieve/update-page-markdown`, `get-self`, `get-users`, `create-a-comment`.
- Las tools `*-page-markdown` + soporte `data-source` ⇒ server actualizado (API 2025-09+).
- `notion-create-attachment` NO presente ⇒ wrapper local, no el hosted `mcp.notion.com`.
- Transport y OAuth scope: **no verificables sin conexión** (el wrapper corre típicamente stdio local con un token de integration; a confirmar).

## Pasos para David (reconexión y re-run)

1. En el host (VS Code/Copilot): re-habilitar el server MCP de Notion (Settings → MCP / `mcp.json` del host) y verificar que las tools `notion-API-*` aparecen en el catálogo de la sesión.
2. Pedir a Copilot re-ejecutar este smoke (solo lecturas):
   - `notion-API-get-self` → anotar nombre de integration/bot y workspace.
   - `notion-API-post-search` con query acotada (`"Control Room"` o `"Dashboard Rick"`) → solo títulos/IDs.
   - `notion-API-retrieve-page-markdown` sobre la [página demo pública](https://nine-coreopsis-f5f.notion.site/What-is-MCP-3915436b72f581ee8971e4169e8bf1e0) (nota: al ser sitio público `notion.site`, si la tool exige page ID del workspace, usar una página interna no sensible, p. ej. la página `OpenClaw` runtime).
3. Actualizar este doc con: identidad, workspace visible, transport, conteo de resultados. **Sin dumps completos, sin PII, sin tokens.**

## Gate de scope (queda armado)

Si `get-self`/search revelan que la conexión ve **workspaces personales fuera de "Umbral BIM"** (riesgo audit 006 §6.7): documentar **RESTRICCIÓN obligatoria** (reducir el sharing de la integration o cambiar a integration dedicada) **antes de cualquier write MCP futuro**. Hasta ese momento, `ide_mcp_agent` permanece read-only (ver [notion-mcp-ide-surface.md](../ops/notion-mcp-ide-surface.md) §7).

## Impacto en O1

QW-2 BLOCKED **no bloquea** QW-1/QW-3/QW-4/Fase 5 (completadas en el PR de O1). ST-1 (HTML attachment) sigue DEFER — su precondición explícita es este smoke en verde.
