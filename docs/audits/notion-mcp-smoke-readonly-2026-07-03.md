# Smoke read-only Notion MCP IDE — QW-2 · O1

- **Date:** 2026-07-03 · Task `2026-07-03-008` (Ola O1, gate G-NMCP-1). **Re-run:** 2026-07-03 13:05 (megaprompt `NOTION-MCP-QW2-RERUN-v1`).
- **Objetivo:** cerrar la Fase B BLOCKED-parcial del [audit #512](notion-mcp-opportunity-audit-2026-07-03.md): verificar identidad (`get-self`), workspace visible, transport, y un search/fetch acotado — todo read-only.
- **Veredicto:** `QW2_SMOKE_BLOCKED` (host) — 2 intentos, tools no visibles en la sesión.

## Intentos

| # | Fecha/hora (-04:00) | Resultado | Detalle |
|---|---|---|---|
| 1 | 2026-07-03 ~12:50 (ejecución O1) | BLOCKED | Tools `notion-API-*` removidas de la sesión (tool-change notice 10:13) |
| 2 | 2026-07-03 13:05 (re-run QW-2) | **BLOCKED** | Paso A negativo: el último tool-change notice de la sesión (12:47) lista las ~25 tools `notion-API-*` como *no longer available* y **no llegó notificación de re-alta**. 0 llamadas ejecutadas; sin resultados inventados. |

## Qué pasó

La precondición del megaprompt ("Notion MCP conectado en el host, tools visibles") **no se cumple en la sesión del agente**: aunque el server esté configurado en el host, las tools no fueron re-inyectadas a esta conversación. 0 llamadas MCP ejecutadas, 0 writes, 0 lecturas.

## Evidencia disponible (del registro del host, sesión del audit)

- Catálogo: ~25 tools `notion-API-*` (wrapper OpenAPI estilo `@notionhq/notion-mcp-server`), incl. `post-search`, `retrieve-a-page`, `retrieve-a-database`, `query-data-source`, `retrieve/update-page-markdown`, `get-self`, `get-users`, `create-a-comment`.
- Las tools `*-page-markdown` + soporte `data-source` ⇒ server actualizado (API 2025-09+).
- `notion-create-attachment` NO presente ⇒ wrapper local, no el hosted `mcp.notion.com`.
- Transport y OAuth scope: **no verificables sin conexión** (el wrapper corre típicamente stdio local con un token de integration; a confirmar).

## Pasos para David (reconexión y re-run) — precisados tras intento 2

1. **VS Code / Copilot:** abrir el panel de MCP (Command Palette → `MCP: List Servers`, o Settings → Extensions → Copilot → MCP) y verificar el estado del server Notion: debe figurar **Running/Started**, no `Stopped`/`Error`. Si usa `mcp.json` del host (user-level `%APPDATA%\Code\User\mcp.json` o workspace `.vscode/mcp.json`), confirmar la entrada del server Notion y arrancarlo (`Start Server`).
2. **Clave del bloqueo actual:** las tools deben quedar disponibles **dentro de la sesión del agente** (aparecen en el catálogo de tools al inicio o vía tool-change notice). Si el server está Running pero el agente no las ve → reiniciar la sesión de chat/agente después de arrancar el server, o toggle off/on del server.
3. Pedir a Copilot re-ejecutar este smoke (solo lecturas):
   - `notion-API-get-self` → anotar nombre de integration/bot y workspace. Sin token ni email.
   - `notion-API-post-search` con query acotada (`"Control Room"` o `"Dashboard Rick"`) → solo N resultados + títulos/IDs.
   - `notion-API-retrieve-page-markdown` sobre página interna NO sensible (preferida: página `OpenClaw` runtime; la [demo pública](https://nine-coreopsis-f5f.notion.site/What-is-MCP-3915436b72f581ee8971e4169e8bf1e0) es `notion.site` y puede no resolver por page ID).
   - Anotar transport (stdio vs HTTP) si es deducible del server config.
4. Actualizar la sección "Resultado live" de este doc. **Sin dumps completos, sin PII, sin tokens.**

## Resultado live

| Tool | OK/FAIL | Notas |
|---|---|---|
| `notion-API-get-self` | — | No ejecutado (tools no visibles en sesión — 2 intentos) |
| `notion-API-post-search` | — | No ejecutado |
| `notion-API-retrieve-page-markdown` | — | No ejecutado |

*(Completar en el próximo re-run con tools live.)*

## Gate de scope (queda armado)

Si `get-self`/search revelan que la conexión ve **workspaces personales fuera de "Umbral BIM"** (riesgo audit 006 §6.7): veredicto `QW2_SCOPE_RESTRICT` → documentar **RESTRICCIÓN obligatoria** (reducir el sharing de la integration o cambiar a integration dedicada) **antes de cualquier write MCP futuro**. Si el scope es solo Umbral BIM: `QW2_SCOPE_OK`. Hasta el smoke verde, `ide_mcp_agent` permanece read-only (ver [notion-mcp-ide-surface.md](../ops/notion-mcp-ide-surface.md) §7).

## Impacto en O1

QW-2 BLOCKED **no bloquea** QW-1/QW-3/QW-4/Fase 5 (completadas en el PR de O1). ST-1 (HTML attachment) sigue DEFER — su precondición explícita es este smoke en verde.
