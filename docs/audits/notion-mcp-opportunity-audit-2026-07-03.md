# Auditoría Notion MCP oficial vs stack UAS — oportunidades

- **Date:** 2026-07-03 · **Task:** `2026-07-02-005` · **Modo:** diagnóstico READ-ONLY (0 writes Notion, 0 cambios VPS/runtime).
- **Surface:** Copilot Windows, repo `umbral-agent-stack` @ `main` post-#511, cross-read `C:\GitHub\notion-governance`.
- **Megaprompt:** [`docs/ops/MEGAPROMPT-notion-mcp-opportunity-audit-2026-07-02.md`](../ops/MEGAPROMPT-notion-mcp-opportunity-audit-2026-07-02.md).
- **Baseline previo:** [audit 006 (2026-05-05)](../../.agents/tasks/2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md) — *"Rick VPS NO tiene MCP Notion; todo es REST vía Worker"* — **sigue vigente** según evidencia en repo.
- **Veredicto:** `NOTION_MCP_AUDIT_READY` (Fase B live = BLOCKED parcial, ver §3).

---

## 1. Resumen ejecutivo

1. **En runtime (VPS) no hay MCP Notion y eso hoy es correcto**: Worker REST (`worker/notion_client.py` 1.766 loc + `worker/tasks/notion.py` 1.359 loc, 15 handlers) da schema tipado, idempotencia por hash, retries, gates HITL y audit `ops_log.jsonl` — nada de eso lo aporta el MCP oficial genérico.
2. **La oportunidad real está en la superficie dev (Windows/IDE), no en producción**: los agentes IDE ya tienen Notion MCP conectado a nivel host (evidencia §3), pero ese acceso no está documentado, no está registrado como actor en `notion-governance`, y convive con ~40 scripts REST one-off que duplican lecturas.
3. **Duplicación detectada:** en Windows conviven 3 vías a Notion (MCP host, scripts REST con `NOTION_API_KEY`, y el `mcp_server/` interno que espeja los 73 worker tasks). En VPS hay 1 sola vía (worker REST) — bien.
4. **Capability nueva sin equivalente interno:** `notion-create-attachment` (HTML interactivo embebible) del MCP hosted — candidata a piloto en docs internos/runbooks, nunca directo a editorial.
5. **Recomendación:** ejecutar **O1** (dev workflow, 4 quick wins) tras gate G-NMCP-1; O2 (Rick runtime híbrido) solo como evaluación con ADR; O3 (editorial) hoy **no** — los gates `aprobado_contenido`/`autorizar_publicacion` y el contrato de schema pesan más que las tools MCP.

---

## 2. Fase A — Inventario baseline (evidencia en repo)

| Superficie | Mecanismo hoy | Auth | Read/Write | Archivos clave |
|------------|---------------|------|------------|----------------|
| **Worker Rick (VPS)** | REST `api.notion.com/v1/*` | `NOTION_API_KEY` (bot "Rick", workspace Umbral BIM) + `NOTION_SUPERVISOR_API_KEY` (bot "Supervisor") + 13× `NOTION_*_DB_ID/PAGE_ID` | R+W (15 handlers: upsert_task/project/deliverable/bridge_item, write_transcript, enrich_bitacora, read_page/database, search, comments…) | `worker/notion_client.py`, `worker/tasks/notion.py`, `worker/notion_markdown.py` |
| **Notion Poller (VPS)** | REST polling (comments + `/v1/users/me` cacheado) | `NOTION_API_KEY` | R (comments) → dispara respuestas vía Worker | `dispatcher/notion_poller.py`, `dispatcher/extractors/notion_comment_paginator.py` |
| **Editorial pipeline** | REST helpers per-domain (decisión explícita de NO unificar cliente) | `NOTION_API_KEY` | `notion_read.py` = R-only (Referentes, `query_data_source`); `notion_publicaciones.py` = parser puro sin HTTP; writers S4/S7/S9/S10 gated | `scripts/discovery/lib/notion_read.py` (182 loc), `notion_publicaciones.py` (295 loc), stages 2/4/7/7.5/8/9/9c/X, [`notion-helpers-policy.md`](../editorial-pipeline/notion-helpers-policy.md) |
| **Scripts one-off** | REST directo | `NOTION_API_KEY` (`.env` local) | Mixto (mayoría lectura/diagnóstico) | ~40 scripts: `audit_notion_publicaciones.py`, `check_notion_comments_raw.py`, `get_db_parent.py`, `granola_*`, `dashboard_*`, `notion_curate_ops_vps.py`… |
| **MCP server interno (`mcp_server/`)** | **MCP stdio/SSE → proxy al Worker HTTP** (expone los 73 task handlers como tools, `notion.*`→`notion_*`) | `WORKER_TOKEN` (no toca token Notion directamente) | Espeja R+W del worker | `mcp_server/server.py`, `tool_registry.py`, `tests/test_mcp_server.py`, dep `mcp[cli]>=1.0.0` en `pyproject.toml` |
| **Rick VPS OpenClaw** | **NO MCP** (`openclaw mcp list` vacío — audit 006). Subagents declaran `notion.*` en TOOLS.md = worker tasks vía dispatcher | heredado del Worker | R+W indirecto | `openclaw/workspace-agent-overrides/*/TOOLS.md`, skill `notion-project-registry`, AGENTS.md regla 23 (`notion.upsert_project` primero) |
| **IDE agents (Copilot/Cursor Windows)** | **Notion MCP conectado a nivel host** (ver §3) | OAuth/integration del host (integration `1f8d872b-…` per audit 006, distinta del bot Rick) | R+W potencial — **no gobernado en repo** | Config del host (fuera del repo); sin doc en UAS |
| **n8n (VPS)** | Node Notion previsto por criterio; credenciales en almacén propio n8n | Credential store n8n | Según flujo (ninguno Notion committeado en repo) | `docs/37-n8n-vps-automation.md` |

**¿Dónde hay duplicación REST + MCP?**

- **Windows/IDE:** SÍ, triple vía — (a) Notion MCP del host, (b) scripts REST del repo si el operador tiene `NOTION_API_KEY` en `.env`, (c) `mcp_server/` interno espejando worker tasks. Sin regla escrita de cuál usar para qué.
- **VPS:** NO — una sola vía (Worker REST). El poller y los agents convergen en el mismo cliente.
- **Editorial:** NO dentro del pipeline (helpers per-domain deliberados), pero los scripts one-off de diagnóstico duplican lecturas que el MCP del IDE ya cubre interactivamente.

---

## 3. Fase B — Notion MCP actual (live) — BLOCKED parcial

**Evidencia de conexión host:** al inicio de esta sesión el host Windows tenía registradas ~25 tools MCP Notion (catálogo estilo `@notionhq/notion-mcp-server`, wrapper OpenAPI): `notion-API-post-search`, `notion-API-retrieve-a-page`, `notion-API-retrieve-a-database`, `notion-API-query-data-source`, `notion-API-retrieve-a-data-source`, `notion-API-create-a-data-source`, `notion-API-update-a-data-source`, `notion-API-post-page`, `notion-API-patch-page`, `notion-API-move-page`, `notion-API-patch-block-children`, `notion-API-retrieve-a-block`, `notion-API-update-a-block`, `notion-API-delete-a-block`, `notion-API-create-a-comment`, `notion-API-retrieve-a-comment`, `notion-API-get-users`, `notion-API-get-self`, **`notion-API-retrieve-page-markdown`**, **`notion-API-update-page-markdown`**, `notion-API-list-data-source-templates`…

- Las dos tools `*-page-markdown` y el soporte `data-source` confirman un server actualizado (API 2025-09+, data sources multi-source).
- **Las tools fueron removidas de esta sesión antes de poder ejecutar el smoke read-only** → Fase B live queda **BLOCKED parcial**: catálogo documentado desde el registro del host; 0 llamadas ejecutadas; sin verificación de OAuth scope ni workspace visible.
- Contraste con el **hosted oficial `mcp.notion.com`** (Streamable HTTP + OAuth, página demo "What is MCP?"): tools de más alto nivel (`notion-create-pages`, `notion-update-page`, `notion-create-comment`, **`notion-create-attachment`** para HTML interactivo). El host local NO expone `create-attachment` → la capability HTML embebible requiere el hosted.
- **Pendiente (QW-2):** smoke `search`/`fetch` read-only sobre la página demo + Control Room cuando las tools estén re-disponibles, con evidencia en `docs/audits/`.

---

## 4. Fase C — Gap matrix (REST vs MCP) por flujo

| Flujo | REST hoy | MCP podría | Gap | ¿Migrar? |
|-------|----------|------------|-----|----------|
| Editorial S0–S10 (Publicaciones) | Helpers tipados + writers gated + `content_hash` idempotente | `post-page`/`patch-page`/`update-page-markdown` genéricos | MCP no valida el schema de 25 props, no conoce gates HITL ni idempotencia | **NO** (core). Re-evaluar solo brief visual (ST-1) |
| Poller comments → Rick | Polling REST 60 min + paginator | `retrieve-a-comment`/`create-a-comment` | MCP tampoco da push/webhooks; cero ventaja sobre poller probado | **NO** |
| Granola pipeline (transcripts → bitácora) | `notion.write_transcript`, `enrich_bitacora_page` (bloques tipados) | `update-page-markdown` (markdown-first simplificaría bloques) | Pérdida de control property-level y del audit trail worker | **NO ahora** — re-evaluar en O2 |
| Supervisor alerts | Handler propio con `NOTION_SUPERVISOR_API_KEY` (bot separado) | — | Separación de bots ya resuelta mejor que OAuth único | **NO** |
| Dev governance / diagnóstico (IDE) | ~40 scripts one-off REST + `.env` local | `post-search`, `query-data-source`, `retrieve-page-markdown` interactivos | Duplicación real; scripts exigen token en filesystem Windows | **SÍ — O1** |
| OpenClaw agents (VPS) | Worker tasks `notion.*` vía dispatcher | Registrar MCP server en `openclaw.json` (hoy 0 configurados) | Duplicaría el path worker; perdería audit + futura allowlist per-agent (hardening 006) | **PARCIAL — evaluar O2** (solo lecturas ad-hoc) |
| Docs/runbooks internos | No existe HTML interactivo en Notion | **`notion-create-attachment`** (hosted): HTML embebible | Capability nueva sin equivalente REST propio | **SÍ — piloto O1/O2** en docs internos |
| n8n | Node Notion nativo con credenciales propias | MCP client node (n8n ≥1.88) | Sin caso de uso que el node no cubra | **NO** |

**HTML/attachments — impacto:** Stage 7 visual editorial podría recibir briefs interactivos (comparativas, carruseles preview) como attachment en la página de la Publicación **sin tocar propiedades ni gates** — es un add-on de revisión para David, no un writer de pipeline. Runbooks/demos internos son el sandbox natural de menor riesgo.

---

## 5. Fase D — Oportunidades priorizadas (top 10)

| # | Oportunidad | Clase | Esfuerzo | Detalle |
|---|-------------|-------|----------|---------|
| QW-1 | **Documentar el MCP Notion del host Windows en el repo** (qué server, qué integration, qué workspace ve) — cierra open question #3 del audit 006 | Quick win | ~2 h | Nuevo doc corto en `docs/` + referencia en AGENT_INSTRUCTIONS |
| QW-2 | **Smoke read-only MCP** (search/fetch página demo + Control Room) con evidencia en `docs/audits/` | Quick win | ~1 h | Desbloquea la Fase B pendiente; 0 writes |
| QW-3 | **Regla "lecturas ad-hoc → MCP del IDE, no scripts nuevos"**: congelar creación de scripts one-off de lectura Notion; los existentes quedan legacy-ok | Quick win | ~2 h | Reduce superficie de token en Windows; doc + nota en scripts/README |
| QW-4 | **Registrar actor `ide_mcp_agent` en `notion-governance`** (`02-permissions-by-surface.md` + `runtime-bridge-contract.yaml`): hoy solo `cursor_live_implementer` existe como `mcp_client` y Copilot IDE opera sin figura propia | Quick win | ~3 h (PR en repo governance) | Policy gap real; write scope explícito antes de cualquier write MCP |
| ST-1 | **Piloto HTML attachments** (hosted MCP) en runbook/doc interno; si convence, extender a briefs visuales editoriales como attachment-only | Strategic | 2–4 d + ADR | Nunca toca props ni gates; requiere OAuth hosted |
| ST-2 | **Evaluación Rick VPS híbrido**: mantener Worker REST para TODO write; evaluar MCP read-only (search/fetch) para el orchestrator | Strategic | 1–2 sem + ADR | Gate G-NMCP-2; el audit 006 §6.7 (allowlist per-agent) va PRIMERO |
| ST-3 | **Capitalizar `mcp_server/` interno**: documentarlo + smoke como bridge worker→IDE (ya existe y está testeado; infra-utilizado) | Strategic | 2–3 d | Alternativa "MCP con gobernanza propia": tools espejo del worker CON audit |
| ST-4 | **Spec de evento común de auditoría** Notion (REST worker `ops_log.jsonl` + tool-calls MCP) para observabilidad unificada si O2 avanza | Strategic | 3–5 d | Prerrequisito de cualquier write MCP no-IDE |
| DF-1 | Migrar writers editoriales (S4/S7/S9/S10) a MCP | Defer | — | Gates HITL + hash + schema tipado > tools genéricas; sin ganancia de rate limit |
| DF-2 | Migrar Poller a MCP / MCP para n8n | Defer | — | Sin push nativo en ambos casos; el node n8n ya cubre |

**Conteo: 4 quick wins · 4 strategic · 2 defer.**

---

## 6. Fase E — Riesgos y gates

| Riesgo | Severidad | Mitigación / gate |
|--------|-----------|-------------------|
| Write MCP accidental en NO-TOUCH (ADR-007: `Bandeja de revisión - Rick`, `Control Room`, `Sistema Maestro`, `Asesorías & Proyectos`) | **Alta** | O0/O1 = read-only estricto; actor governance (QW-4) antes de cualquier write; gates `aprobado_contenido`/`autorizar_publicacion` JAMÁS via MCP |
| OAuth de David (hosted MCP) ve **más** que el bot Rick — workspaces personales incluidos; invierte el hardening pedido en 006 §6.7 | **Alta** | Smoke QW-2 debe listar el workspace visible; si excede Umbral BIM → restringir conexión antes de O1 |
| Tokens históricos en session JSONL de OpenClaw (006 §6.8.4: patrones `ntn_` en `~/.openclaw/agents/*/sessions/`) — **sigue abierto** | **Alta** (preexistente) | Rotar `NOTION_API_KEY` + `NOTION_SUPERVISOR_API_KEY` y limpiar JSONL (task VPS separada; fuera de scope acá) |
| Drift de schema: tools MCP genéricas no validan las 25 props de `Publicaciones` ni los mapeos hardcodeados de `worker/notion_client.py` | Media | Fuente de verdad sigue en repo; MCP solo lecturas/attachments hasta ST-4 |
| Rate limits: MCP usa la misma API (~3 rps sustained, ADR-007); hosted añade su propia capa de throttling | Media | No prometer throughput; batch/backoff del worker sigue siendo el camino de escritura masiva |
| Duplicación de paths → confusión de agentes ("¿worker task o MCP tool?") | Media | Regla QW-3 + tabla de decisión en doc QW-1 |
| Gobernanza: writes MCP sin declarar en `runtime-bridge-contract.yaml` violan policy 02 (§"permissions must be declared, not inferred") | Media | QW-4 obligatorio antes de G-NMCP-2 |

---

## 7. Fase F — Roadmap recomendado O0–O3

| Ola | Alcance | Estado | Gate David |
|-----|---------|--------|------------|
| **O0** | Esta auditoría + smoke read-only MCP (QW-2 pendiente por tools removidas) | ✅ doc listo / smoke pendiente | — |
| **O1** | Dev workflow Windows: QW-1 doc host MCP · QW-3 regla lecturas · QW-4 actor governance · piloto attachment HTML en doc interno (ST-1 fase 1) | **Recomendada** | **G-NMCP-1** |
| **O2** | Rick runtime eval (VPS): ADR MCP-vs-REST híbrido · allowlist per-agent del worker (006 §6.7.1) primero · ST-3/ST-4 | Solo evaluación, no implementación | G-NMCP-2 |
| **O3** | Editorial producción (attachments en Publicaciones; writers NUNCA) | No proponer hasta O1+O2 verdes | G-NMCP-3 |

**Recomendación: arrancar O1.** Bajo riesgo, cierra deuda de gobernanza real (actor MCP sin registrar), y no toca VPS ni editorial.

---

## 8. Preguntas abiertas para David

1. El MCP del IDE, ¿está conectado con **tu** OAuth personal o con una integration dedicada? (determina el scope real; QW-2 lo verifica).
2. ¿Autorizás **G-NMCP-1** (O1: docs + regla lecturas + actor governance + piloto attachment en doc interno)?
3. La rotación de tokens Notion recomendada en audit 006 §6.8.4 sigue pendiente — ¿la priorizamos como task VPS antes de O2?
4. Para el piloto HTML: ¿preferís sandbox en página OpenClaw (runtime surface, `edit_full` para Rick) o una página nueva efímera?
5. ¿Querés que `mcp_server/` interno (worker-as-MCP) entre en el roadmap O1 como bridge documentado, o lo dejamos dormido hasta O2?

---

## 9. Referencias

- Task 006 baseline: `.agents/tasks/2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md`
- ADR-007 Notion hub editorial + NO-TOUCH: `docs/adr/ADR-007-notion-como-hub-editorial.md`
- Helpers policy editorial: `docs/editorial-pipeline/notion-helpers-policy.md` · Schema: `docs/editorial-pipeline/notion-schema.md`
- LinkedIn pipeline (bloqueos audit MCP resueltos por 006): `docs/plans/linkedin-publication-pipeline.md`
- Governance cross-repo: `notion-governance/docs/policies/02-permissions-by-surface.md` + `registry/runtime-bridge-contract.yaml`
- MCP interno: `mcp_server/` + `tests/test_mcp_server.py`
- Página demo externa: [What is MCP? (Notion)](https://nine-coreopsis-f5f.notion.site/What-is-MCP-3915436b72f581ee8971e4169e8bf1e0)
- n8n criterio: `docs/37-n8n-vps-automation.md`
