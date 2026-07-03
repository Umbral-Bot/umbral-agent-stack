# Notion MCP — superficie IDE (dev) · O1

- **Status:** v1 — 2026-07-03 · Ola O1 (gate **G-NMCP-1** firmado por David).
- **Scope:** el MCP Notion **del host IDE** (Copilot/Cursor en Windows) como superficie de **desarrollo y diagnóstico** de UAS. **NO es el path de producción Rick/VPS** — producción sigue siendo Worker REST + Poller.
- **Origen:** [audit #512](../audits/notion-mcp-opportunity-audit-2026-07-03.md) · task `2026-07-03-008`.

---

## 1. Qué es (y qué no es)

El host IDE (VS Code/Copilot/Cursor) puede tener conectado un server MCP de Notion (estilo `@notionhq/notion-mcp-server`, wrapper OpenAPI de la API pública, o el hosted `mcp.notion.com`). Cuando está conectado, el agente del IDE ve tools `notion-API-*` y puede leer/escribir Notion **con la identidad de esa conexión**, sin pasar por el Worker.

- **Es**: herramienta de lecturas ad-hoc, diagnóstico de datos Notion, y (futuro, gated) writes dev gobernados.
- **No es**: sustituto del Worker REST para writes de producción, gates HITL, idempotencia por hash, ni audit `ops_log.jsonl`.

## 2. Dónde se configura

En el host IDE (config MCP de VS Code / Copilot / Cursor), **fuera de este repo**. No se commitea config ni credencial alguna aquí. La identidad usada (OAuth de David vs integration dedicada) se verifica en el smoke QW-2 ([evidencia](../audits/notion-mcp-smoke-readonly-2026-07-03.md)) — mientras no esté verificada, asumir scope amplio y tratar TODO como read-only.

## 3. Tabla de decisión de superficies (canónica O1)

| Superficie | Mecanismo | Cuándo usar |
|-------------------------|-----------------------------------|--------------------------------------|
| IDE (Cursor/Copilot) | Notion MCP del host (OAuth/tools) | Lecturas ad-hoc, diagnóstico, dev |
| Worker VPS | REST `api.notion.com` | Writes producción, gates, idempotencia |
| Scripts one-off repo | REST + `NOTION_API_KEY` local | **LEGACY** — no crear nuevos de lectura |
| `mcp_server/` (repo) | Proxy MCP → Worker HTTP | Bridge documentado; [dormido hasta O2](mcp-server-worker-bridge.md) |
| Rick OpenClaw VPS | `notion.*` worker tasks | Runtime agents; sin MCP Notion nuevo |

**Regla QW-3:** lecturas ad-hoc → MCP IDE. Writes producción → Worker REST únicamente.

## 4. Tools relevantes observadas

**Config actual del host (confirmada 2026-07-03, O1-close):** hosted **`https://mcp.notion.com/mcp`** — tools de alto nivel `notion-search`, `notion-fetch`, `notion-create-pages`, `notion-create-attachment`, etc. Catálogo histórico de la sesión del audit #512 (~25 tools `notion-API-*`, wrapper OpenAPI: `post-search`, `retrieve/update-page-markdown`, `query-data-source`, `get-self`…) correspondía a otra configuración.

> Verificación live (identidad, workspace visible) pendiente del smoke QW-2 — 3 intentos BLOCKED por re-inyección de sesión ([estado](../audits/notion-mcp-smoke-readonly-2026-07-03.md)).

## 5. Hosted `mcp.notion.com` — implicancias

El hosted (Streamable HTTP + OAuth) es la config vigente del host y expone **`notion-create-attachment`** (HTML interactivo embebible) → la capability ST-1 está técnicamente disponible cuando el smoke pase, pero **sigue DEFER por decisión David** (ver §8). El scope OAuth (qué workspaces ve) es exactamente lo que el smoke QW-2 debe verificar antes de cualquier write.

## 6. Diferencia vs Worker REST y vs `mcp_server/` interno

| | MCP IDE | Worker REST (VPS) | `mcp_server/` interno |
|---|---|---|---|
| Identidad | OAuth/integration del host | Bots `Rick` + `Supervisor` (`ntn_`) | `WORKER_TOKEN` (no toca token Notion) |
| Schema tipado Publicaciones/Tasks | ❌ genérico | ✅ 15 handlers | ✅ (espeja worker) |
| Gates HITL / idempotencia hash | ❌ | ✅ | ✅ (vía worker) |
| Audit trail | el del host (opaco) | `ops_log.jsonl` | `ops_log.jsonl` (vía worker) |
| Estado O1 | read-only dev | producción | documentado, dormido |

## 7. NO-TOUCH surfaces (ADR-007) — MCP IDE = read-only en O1

Prohibido escribir vía MCP IDE en: **`Bandeja de revisión - Rick`**, **`Control Room`**, **`Sistema Maestro Apoyo Editorial`**, **`Asesorías & Proyectos`**, y los campos gated de **`Publicaciones`** (`aprobado_contenido`, `autorizar_publicacion` — solo David, jamás vía MCP). En O1 el actor `ide_mcp_agent` (registrado en `notion-governance`) opera **read-only sobre superficies protegidas/editoriales**; cualquier write futuro requiere el modo declarado en `registry/runtime-bridge-contract.yaml` + gate.

## 8. Deferred ST-1 — piloto HTML attachment

**NO ejecutar en O1** (decisión David: defer hasta post-QW-2 smoke verde).

- Requiere hosted MCP `mcp.notion.com` + tool `notion-create-attachment`.
- Sandbox propuesto: página efímera interna (preferencia David, post-QW-2).
- Nunca tocar props/gates de `Publicaciones` en el piloto.

## 9. Referencias

- Audit O0: [`docs/audits/notion-mcp-opportunity-audit-2026-07-03.md`](../audits/notion-mcp-opportunity-audit-2026-07-03.md)
- Smoke QW-2: [`docs/audits/notion-mcp-smoke-readonly-2026-07-03.md`](../audits/notion-mcp-smoke-readonly-2026-07-03.md)
- Bridge interno: [`docs/ops/mcp-server-worker-bridge.md`](mcp-server-worker-bridge.md)
- Governance: `notion-governance/registry/runtime-bridge-contract.yaml` (actor `ide_mcp_agent`) + `docs/policies/02-permissions-by-surface.md`
- Baseline runtime: task `2026-05-05-006` (VPS = REST puro)
