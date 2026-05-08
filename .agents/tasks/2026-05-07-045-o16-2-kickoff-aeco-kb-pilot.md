---
id: 2026-05-07-045
title: O16.2 kickoff — Piloto Área 2 Conocimiento Técnico AECO (AI Search KB + AgenteUB File Search)
status: open
priority: P1 (deadline duro Sponsorship 2026-06-30)
assigned_to: copilot-chat
created_at: 2026-05-07
created_by: copilot-chat (post-O16.1 closure 044)
parent: O16.2 (plan Q2 línea ~876)
relates_to: docs/architecture/17-areas-gerencias-agentes-subagentes-model.md, docs/audits/2026-05-07-o16-1-smoke-deploy.md, registry/agents-canonical.yaml §autonomous_agent_operations_areas
depends_on: O16.1 ✅ (infra Azure live: AI Search Basic eastus, Document Intelligence S0 eastus2, Container Apps Env eastus2, Storage, KV, UAMI con RBAC ya asignado)
blocks: O16.6 (Áreas 3+4 condicionales al éxito de O16.2)
---

# 045 — O16.2 kickoff: Piloto Área 2 Conocimiento Técnico AECO

## Contexto

O16.1 cerró con infra Azure provisionada en `rg-umbral-agents-prod` (commit `1044adc0`, audit `docs/audits/2026-05-07-o16-1-smoke-deploy.md`). UAMI ya tiene RBAC sobre AI Search (`Search Service Contributor` + `Search Index Data Contributor`) y Document Intelligence (`Cognitive Services User`). Container Apps Environment listo (scale-to-0 Consumption). Falta llenar la KB y conectarla al `AgenteUB` ya productivo en `umbralbim-resource` (Foundry, sub Sponsorship).

Este task **NO implementa todos los subagentes** — produce decisiones locked + decomposición en sub-tasks ejecutables. Implementación en PRs incrementales.

## Objetivo medible (criterio Friday retro 26-jun)

> **Bot Umbral en producción cita un párrafo de buildingSMART/IFC con su versión KB visible (`aeco-kb-es-vYYYYMMDD`) y URL fuente.**

Sin esto, O16.2 no está cerrado. Smoke = pregunta tipo "¿qué dice IFC 4.3 sobre IfcWall?" → respuesta del bot incluye cita + version tag KB.

## Decisiones a lockear en este task

### D1. Fuentes Q2 (legales + costo cero/bajo)

| # | Fuente | Tipo | Acceso | Decisión |
|---|---|---|---|---|
| 1 | **buildingSMART** (IFC schemas 4.x, BCF, IDS, MVD) | Open spec | HTTPS público + GitHub | ✅ INCLUIR — fuente principal Q2 |
| 2 | **Chile MINVU** (DDU, NCh aplicables) | Gov público | Web pública | ✅ INCLUIR (gap 1 confirmado 2026-05-06) |
| 3 | **AR IRAM** (normas BIM/construcción públicas) | Gov público | Web pública | ✅ INCLUIR (gap 1 confirmado) |
| 4 | **MX NMX** (NMX-R-* construcción) | Gov público | Web pública | ✅ INCLUIR (gap 1 confirmado) |
| 5 | **ISO 19650** (full text) | Paid spec | ISO Store | ❌ EXCLUIR Q2 — solo abstracts/intro públicos vía `docs/external-context/` (riesgo legal de scraping paid). Re-evaluar Q3 con licencia formal. |
| 6 | Otros (Chilean NCh, ICONTEC CO, NTE INEN EC, etc.) | Variable | Variable | ⏸ Diferido a O16.6 si O16.2 sale a tiempo |

**Default lockeado:** Q2 = buildingSMART + 3 fuentes LATAM gov. ISO body = solo metadata pública.

### D2. Foundry: reusar `umbralbim-resource`, NO crear nueva cuenta

El `AgenteUB` ya productivo (consumido por `umbral-bot-2` en producción) vive en `umbralbim-resource` (Foundry, eastus2 según `umbral-bot-2/.github/copilot-instructions.md`). **NO crear** Foundry account/project nuevo en `rg-umbral-agents-prod`. La integración será:

1. Crear connection desde el Foundry project del `AgenteUB` hacia `srch-umbral-kb-prod` (cross-RG, mismo tenant) usando UAMI o key-based auth.
2. Agregar el index `aeco-kb-es-current` (alias) como data source de la **File Search tool** del `AgenteUB`.

Cross-RG entre Foundry (`rg-umbralbim-foundry` u otro) y AI Search (`rg-umbral-agents-prod`) es soportado vía connection string + RBAC en el AI Search service (asignar `Search Index Data Reader` al system-assigned MI del Foundry project, además del UAMI ya asignado para writes).

**Validación pre-implementación 046:** verificar con `az account show` + `az resource list -g <RG-foundry>` el resource group exacto donde vive `umbralbim-resource` y cuál es el system-assigned principalId del Foundry project.

### D3. Índice AI Search: schema + versionado

**Naming**: `aeco-kb-{lang}-vYYYYMMDD` (plan Q2). Lang = `es` para Q2 (LATAM-first). Posible `en` Q3 para buildingSMART original.

**Alias estable**: `aeco-kb-{lang}-current` apunta atómicamente al último index validado. Foundry File Search se configura contra el alias (no contra el versioned index directo). Swap = `az search alias create-or-update` en script `index-publisher`.

**Schema mínimo (vector + semantic):**
- `id` (key, string)
- `content` (Edm.String, searchable, retrievable)
- `content_vector` (Collection(Edm.Single), 1536 dims — text-embedding-3-small via Foundry; alineado a lo que el `AgenteUB` ya use)
- `source_url` (Edm.String, retrievable, filterable)
- `source_type` (Edm.String, filterable: `buildingsmart` | `minvu` | `iram` | `nmx`)
- `jurisdiction` (Edm.String, filterable: `intl` | `cl` | `ar` | `mx`)
- `doc_type` (Edm.String, filterable: `spec` | `regulation` | `guide`)
- `version` (Edm.String, filterable: ej `IFC-4.3.2.0`, `MINVU-DDU-450-2024`)
- `lang` (Edm.String, filterable)
- `valid_from` / `valid_to` (Edm.DateTimeOffset, nullable)
- `chunk_id` (Edm.Int32) + `parent_doc_id` (Edm.String, filterable, retrievable)
- `kb_version` (Edm.String, retrievable — `vYYYYMMDD` del index para que el bot pueda citarla)

**Semantic config**: `default-semantic-cfg` con `content` como contenido prioritario, `version`+`source_url` como metadata destacada.

**Vector profile**: `hnsw-cosine` (Basic SKU lo soporta).

### D4. Subagentes (4 mínimos del plan + 1 opcional)

Implementados como **OpenClaw subagents** (regla §3.2 modelo organizacional canónico — profundidad max 2 niveles). Runtime = **Container Apps Jobs efímeros** (cron + manual trigger), scale-to-0, leen creds desde KV vía UAMI.

| Subagent | Input | Output | Runtime |
|---|---|---|---|
| `aeco-source-crawler` | Lista de seeds + rate-limit config | Crudos en Storage `crudos/` (PDF/HTML/JSON, dedupe por hash) | Container App Job, cron diario 03:00 UTC |
| `pdf-parser` | Blob URL en `crudos/` | JSON estructurado (sections, tables) en `datasets-curados/` | Container App Job, event-triggered (Service Bus topic `eval-events` o blob trigger) |
| `version-detector` | Dataset crudo + previous index manifest | Diff manifest (added/changed/removed docs) | Container App Job, post `pdf-parser` |
| `index-publisher` | Datasets curados + diff manifest | Nuevo index `aeco-kb-es-vYYYYMMDD` populated + alias swap atómico | Container App Job, gated por health check |
| (opcional) `chunk-quality-eval` | Chunks pre-publish | Pass/fail + sample queries | Container App Job, NO bloqueante en Q2 (manual review) |

**NO usar** `latam-regulation-crawler` como subagent separado — colapsar a `aeco-source-crawler` parametrizado por `source_type` (más simple, mismo runtime).

### D5. Costo + guardrails

- **Document Intelligence**: budget $400/mes ($1.50 / 1k pages prebuilt-layout). Cap operativo: ≤200k pages/mes (~$300, margen 25%). Crawler debe contar páginas y cortar antes.
- **AI Search Basic**: $75 base ya pagado por estar provisioned. Indexar dentro del Basic limit (15M docs / 2GB). Para Q2 (~10-50k docs estimados), holgado.
- **Embeddings**: text-embedding-3-small = $0.02 / 1M tokens. Para 50k chunks × 800 tokens = 40M tokens = $0.80. Negligible.
- **Container Apps Jobs**: pay-per-use, scale-to-0. Estimado <$50/mes con cron diario + jobs cortos.
- **Total O16.2 mensual estimado**: ~$400-500. Dentro de budgets foundry+search+DI ($4,200 combinados).
- **Kill switch**: cron del crawler verifica `az consumption budget show` antes de correr; si DI budget >85% used, skip.

### D6. Idiomas

- **Q2**: `es` only (LATAM-first + bot ya responde en español).
- **Q3 (post-O16.2)**: agregar `en` para buildingSMART original (índices duplicados — buscar via filter `lang in ('es','en')`).

## Plan de sub-tasks (decomposición)

| # | Title | Output |
|---|---|---|
| **046** | AI Search index schema + alias strategy | Bicep/Python module que crea `aeco-kb-es-v<initial>` empty + alias `aeco-kb-es-current`. Validate via `az search index show`. |
| **047** | `pdf-parser` subagent (DI prebuilt-layout) | Container App Job + Python code: input blob URL → output JSON estructurado. Test contra 1 PDF buildingSMART real. |
| **048** | `aeco-source-crawler` (buildingSMART + 1 LATAM source) | Container App Job + crawler con rate-limit (1 req/s) + dedupe hash. Smoke: 50 docs en `crudos/`. |
| **049** | `version-detector` + `index-publisher` (alias swap atómico) | Pipeline post-parser que diff-ea, embebe, indexa a `vYYYYMMDD`, valida, swap alias. |
| **050** | Pipeline e2e + 3 LATAM sources restantes | Cron orquestador (Container App Job o Service Bus chained) + MINVU/IRAM/NMX seeds. ≥500 chunks indexados. |
| **051** | AgenteUB File Search wiring (Foundry connection) + smoke "bot cita KB version" | Foundry portal/API config + manual test query → bot responde citando version + URL. **Cierra O16.2.** |

Cada sub-task = 1 PR independiente, F-INC-002 estricto, deploy real sólo en 049/050/051.

## Acceptance (este task 045)

- [x] Decisiones D1-D6 lockeadas en este markdown.
- [x] Plan de sub-tasks 046-051 definido con outputs concretos.
- [ ] Plan Q2 actualizado: O16.2 marcada "kickoff abierto 2026-05-07 (task 045)" + decisiones D1-D6 referenciadas.
- [ ] Commit + push umbral-agent-stack/main + notion-governance/main.

NO implementación en este task. NO deploy. NO touch Foundry todavía.

## Salvavidas

- **NO crear** Foundry account nuevo. Reusar `umbralbim-resource`.
- **NO scrapear** ISO body (paid). Solo metadata pública.
- **NO indexar** sin rate-limit en crawler (riesgo ban + burn DI budget).
- **NO swap alias** sin validation (chunks > N + sample query OK).
- **F-INC-002** estricto antes de cada push.
- **secret-output-guard #8**: connection strings de Foundry → AI Search van por KV, NO commit.
- Container Apps Jobs **scale-to-0** verificado en cada deploy.

## Capitalización (C4)

- Skill `aeco-kb-crawler` (reusable para futuras KB Áreas 1/3/4).
- Schema AI Search documentado en `infra/azure/README.md` § "AI Search index conventions".
- Runbook `docs/runbooks/aeco-kb-refresh.md` (cómo correr el cron manual + rollback alias).
- ADR `docs/adr/18-aeco-kb-versioning-and-alias-strategy.md` (decisiones D3+D4 formalizadas si surgen objeciones).

## Decisiones diferidas a David (no bloquean apertura del kickoff)

1. ¿Aceptar D1 (excluir ISO 19650 body de scraping)? → si dice no, abrir gap antes de 049.
2. ¿Aceptar D2 (reusar `umbralbim-resource` para Foundry)? → si quiere Foundry separado, replanificar 051.
3. ¿Acepta lang=es Q2 only? → si quiere bilingüe Q2, ampliar 050 con index `en`.

Bajo mandato autónomo: defaults D1+D2+D6 son los más conservadores en costo + riesgo legal + scope. Procedo con ellos hasta que David los revise.
