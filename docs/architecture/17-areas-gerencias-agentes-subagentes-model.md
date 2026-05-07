# 17 — Áreas / Gerencias / Agentes / Subagentes (O16 model)

- **Date:** 2026-05-06
- **Status:** Planned (Q2-2026). No agent built yet.
- **Owner:** umbral-bim
- **Source:** Promoted from `notion-governance` handoff `docs/handoffs/2026-05-06-O16-autonomous-agent-operations-azure.md` and registry section `autonomous_agent_operations_areas:` in `notion-governance/registry/agents-canonical.yaml@1317d05`.
- **Governance contract:** The canonical machine-readable form lives at `notion-governance/registry/agents-canonical.yaml` (section `autonomous_agent_operations_areas:`). This document is the human-readable runtime architecture inside the repo that **operates** these agents (`umbral-agent-stack`).
- **Related:**
  - [ADR-009](../adr/ADR-009-mission-control-scope.md) (Mission Control scope)
  - [docs/runbooks/azure-off-sponsorship-2026-07-30.md](../runbooks/azure-off-sponsorship-2026-07-30.md) (cost lifecycle)
  - `infra/azure/` (Bicep scaffold for the supporting Azure surfaces)

---

## 1. Scope

The O16 model defines the organizational layer that runs **inside** `umbral-agent-stack` to operate autonomous agents on Azure (Sponsorship balance ~$21,619, expires 2026-07-30; deadline for hardening 2026-06-30).

Implementation rule: **`subagents` + `parallel-specialist-lanes` native OpenClaw**, max depth 2, consistent with the O7 reformulation 2026-05-05. No new orchestration primitive.

## 2. Routing rule (data plane)

| Data class | Lands in | Why |
|---|---|---|
| Production users | **Supabase** (read-only from this stack) | User-facing system of record (umbral-bot-2). Stack consumes, never mutates. |
| Internal agents | **Azure** — Cosmos DB NoSQL serverless preferred, Storage Blob for raw artifacts, AI Search for KB indexes, Foundry for models | Sponsorship balance covers it; serverless = autoscale to 0. |
| Human view | **Notion** | Where David already operates. Agents render summaries here, not raw state. |

**Forbidden** (governance-enforced via Bicep + PR review):

- Persistent VMs on Azure.
- Agents in this stack writing directly to Supabase.
- Subagents at depth > 2.

## 3. Áreas (4)

### Área 1 — Inteligencia Comercial

- **Output:** Lead profiles + scoring + ruta recomendada (Autodidacta / Guiada / Premium).
- **Lands in:** Notion DB Leads, Cosmos DB NoSQL (memoria interna).
- **Status:** `planned_q2_2026`
- **Pilot objective:** O16.3 (S4-S5).
- **Smoke metric:** 5 leads procesados < 30 min, scoring + ruta citables.

| Gerencia | Agent | Role |
|---|---|---|
| `lead_intelligence` | `lead_profiler` | Coordina enrichment de un lead nuevo; delega a subagents. |
| `lead_intelligence` | `linkedin_scraper` (subagent) | Extrae perfil público LinkedIn con rate-limit + ToS. |
| `lead_intelligence` | `empresa_info` (subagent) | Bing search + Document Intelligence sobre web corporativa. |
| `lead_intelligence` | `tech_stack_detector` (subagent) | Detecta stack BIM/CAD/AECO de la empresa (Wappalyzer-like + heurísticas). |
| `lead_scoring` | `lead_scoring` | Aplica modelo de scoring (gpt-5 razonamiento). Output: score 0-100 + ruta + justificación. |

### Área 2 — Conocimiento Técnico AECO

- **Output:** AI Search index `aeco-kb-{lang}-vYYYYMMDD`.
- **Lands in:** Foundry File Search del AgenteUB (consumido por `umbral-bot-2` con cita de versión).
- **Status:** `planned_q2_2026`
- **Pilot objective:** O16.2 (S3-S4) — alto leverage comercial, **piloto principal**.
- **Smoke metric:** Bot cita versión KB en respuesta + version-detector valida pre-publish.
- **Leverage rationale:** Cierra gap explícito ROADMAP `umbral-bot-2` línea 72 (KB hoy = snapshot operativo manual).

**Sources priority Q2 (gap-1 — TENTATIVE, pending David confirm):**

- Tier-1 global: ISO 19650, buildingSMART (IFC, BCF), Autodesk docs, Bentley docs, Trimble docs, Graphisoft docs, Speckle docs.
- Tier-1 LATAM hispano: Chile MINVU, Argentina IRAM, Mexico NMX.
- Tier-2 Q3 or pull: Brasil ABNT (idioma portugués — fase 2), Perú, Colombia.
- **Rationale:** Top 3 LATAM hispano = ~80% PIB AECO de la región. Brasil pesa pero requiere lengua aparte. Perú/Colombia entran cuando lead específico lo justifique (criterio pull).

| Gerencia | Agent | Role |
|---|---|---|
| `estandares_globales` | `iso_buildingsmart_crawler` | Crawler ISO 19650 + buildingSMART. Versiona + diff. |
| `estandares_globales` | `vendor_docs_harvester` | Harvester docs Autodesk/Bentley/Trimble/Graphisoft/Speckle. Respeta robots.txt. |
| `normativa_latam` | `latam_regulation_crawler` | Crawler normativa LATAM hispano (Chile MINVU + AR IRAM + MX NMX en Q2). |
| `pipeline_kb` | `pdf_parser` (subagent) | Parseo PDFs vía Azure Document Intelligence. |
| `pipeline_kb` | `version_detector` (subagent) | Detecta cambios entre versiones; bumpea `aeco-kb-{lang}-vYYYYMMDD`. |
| `pipeline_kb` | `index_publisher` (subagent) | Publish atómico a AI Search index nuevo + rollback al previo si smoke falla. |

### Área 3 — Datos y Modelos

- **Output:** Datasets curados versionados + modelos fine-tuned + eval results.
- **Lands in:** Foundry model registry, Storage Blob (datasets), Cosmos DB (eval results).
- **Status:** `planned_q2_2026`
- **Pilot objective:** O16.6 (S5-S6, condicional).
- **Location in repo:** `umbral-agent-stack/data-science/` (subdir, NO repo nuevo). Notebooks Jupytext (texto plano versionable).

**Fine-tuning strategy (gap-2 — TENTATIVE, pending David confirm):**

- Q2 default: Datasets curados + RAG fuerte primero. 1 fine-tuning experimental Phi-4 (open weights, dataset pequeño) solo para validar pipeline.
- Q3 gate: Fine-tuning productivo solo si eval continuo (Área 4) muestra gap específico que RAG no cierra.
- **Rationale:** Fine-tuning consume mucho saldo + curva de eval. RAG con AI Search bien indexado suele ganar costo/beneficio.

| Gerencia | Agent | Role |
|---|---|---|
| `datasets` | `dataset_builder` | Construye datasets desde Granola transcripts + conversaciones bot + KB AECO. |
| `datasets` | `dataset_curator` | Filtra ruido, balancea clases, etiqueta calidad. |
| `datasets` | `dataset_versioner` | Versiona datasets en Storage Blob con metadata reproducible. |
| `training_eval` | `fine_tuning_operator` | Lanza jobs Foundry fine-tuning (Phi-4 exploratorio Q2; gpt-4o-mini si Q3 lo justifica). |
| `training_eval` | `eval_harness` | Continuous eval contra dataset hold-out + golden questions AECO. |
| `training_eval` | `model_registry_publisher` | Promueve modelo a Foundry registry si eval > threshold. |

### Área 4 — Ops de Producto Bot AECO

- **Output:** KB refresh agendado + telemetría agregada + eval continuo + partner ops (estructura).
- **Lands in:** Foundry deployment de `umbral-bot-2` (escritura swap), Supabase `chat_messages` (read-only).
- **Status:** `planned_q2_2026`
- **Naming decision (gap-3 — CONFIRMED 2026-05-06):** "Ops de Producto Bot AECO" (vs "Plataforma del Producto"). Enfatiza **OPS** vs construcción. Construcción del bot es responsabilidad del repo `umbral-bot-2`; esta Área lo OPERA desde el stack.
- **Pilot objective:** O16.6 (S5-S6, parcial: KB refresh + telemetry insights básico).

| Gerencia | Agent | Role |
|---|---|---|
| `kb_refresh_ops` | `kb_refresh_orchestrator` | Cron-driven: consume outputs Área 2 + publica nuevo index a Foundry File Search del AgenteUB. |
| `telemetria_insights` | `conversation_analyst` | Lee Supabase `chat_messages` read-only. Top temas / gaps de KB / ruta clicked / churn signals. |
| `eval_continuo` | `continuous_eval_runner` | Eval semanal del AgenteUB sobre golden questions + alertas si degrada. |
| `partner_ops` | `partner_discount_curator` | Estructura preparatoria Q2 (NO onboarding comercial Q2). Cura ofertas de partners para Ruta Guiada. |

## 4. Tentative resolutions requiring David's explicit OK

| # | Item | Default applied | Confirmation status |
|---|---|---|---|
| 1 | LATAM tier-1 Q2 sources | Chile MINVU + AR IRAM + MX NMX (Brasil/Perú/Colombia → tier-2 Q3 or pull) | TENTATIVE |
| 2 | Área 3 fine-tuning Q2 | RAG primero + 1 experimento Phi-4 exploratorio. Productivo gateado a Q3 si eval continuo muestra gap | TENTATIVE |
| 3 | Área 4 nombre | "Ops de Producto Bot AECO" | **CONFIRMED 2026-05-06** |

Items 1 and 2 must be confirmed before the first real `az deployment` of supporting infra (because they shape AI Search index structure, Storage Blob containers for datasets, and Foundry deployment surface).

## 5. Governance notes

- This document is the human-readable runtime architecture inside `umbral-agent-stack`. The machine-readable governance contract is the registry section in `notion-governance`. Both must stay in sync.
- Migrate individual entries to a proper `agents:` section in the canonical registry as they are built and pass smoke.
- **Quality gate (extends O15):** Any new agent outside this list requires: caso de uso citable + dueño + métrica de uso real en 14 días.
- **Burn risk controls** (O16.5 hardening — deadline 2026-06-30):
  - Budget alerts hard cap por servicio (Bicep, see `infra/azure/main.bicep`).
  - Autoscale a 0 donde el servicio lo permita.
  - Kill switch documentado en runbook off-Sponsorship.
  - Revisión Friday retro.

## 6. Implementation surfaces (mapping to infra/azure/)

| Surface | Bicep module | Used by |
|---|---|---|
| Container Apps (consumption only, autoscale to 0) | `container-apps.bicep` | Long-running workers, schedulers. Preferred runtime. |
| Cosmos DB NoSQL serverless | `cosmos.bicep` | Internal agent state, lead profiles, eval results. |
| AI Search basic | `ai-search.bicep` | KB indexes (`aeco-kb-{lang}-vYYYYMMDD`). |
| Storage Account | `storage.bicep` | Datasets, KB raw + processed. Lifecycle Cool 30d / Archive 90d. |
| Key Vault | `keyvault.bicep` | Managed identity-based secrets only. |
| Application Insights | `appinsights.bicep` | Workspace-based, sampling 25%, retention 30d. |
| Document Intelligence S0 | `document-intelligence.bicep` | `pdf_parser` subagent (Área 2). |
| Service Bus Standard | `service-bus.bicep` | Inter-agent queues (`lead-enrichment`, `kb-refresh`). |
