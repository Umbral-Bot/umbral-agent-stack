# ADR-017 — Áreas / Gerencias / Agentes / Subagentes (Autonomous Agent Operations on Azure)

- **Date:** 2026-05-06
- **Status:** Accepted (promoted from `notion-governance/docs/handoffs/2026-05-06-O16-autonomous-agent-operations-azure.md` Proposed)
- **Closes:** O16.0 (Plan Q2-2026 §O16, checkbox "Diseño organizacional")
- **Owner:** umbral-agent-stack (este repo) — único productor; `umbral-bot-2` y `notion-governance` son consumidores.
- **Source of truth (jerarquía + agent IDs):** [`notion-governance/registry/agents-canonical.yaml`](https://github.com/Umbral-Bot/notion-governance/blob/main/registry/agents-canonical.yaml) sección `autonomous_agent_operations_areas`.
- **Rationale completo (trade-offs, alternativas descartadas, gaps):** [handoff draft 2026-05-06](https://github.com/Umbral-Bot/notion-governance/blob/main/docs/handoffs/2026-05-06-O16-autonomous-agent-operations-azure.md).
- **Deadline duro O16.5:** 2026-06-30 (30 días antes de expiración Sponsorship 2026-07-30).

---

## 1. Decisión

Implementar autonomía operacional del stack mediante una capa multi-agente jerárquica **Áreas → Gerencias → Agentes → Subagentes** sobre primitivas nativas OpenClaw (`sessions_spawn` + `parallel-specialist-lanes`, ver ADR `tournament-on-openclaw-primitives.md`). El saldo Sponsorship Azure ($21,619 / 86 días desde 2026-05-06) financia la infraestructura. **Profundidad máxima 2 niveles de subagent.**

## 2. Localización

| Repo | Rol |
|---|---|
| `umbral-agent-stack` (este repo) | Hospeda agentes, infra Azure (Bicep en `infra/azure/`), runtime OpenClaw. **Único productor.** |
| `umbral-bot-2` | Consume outputs de Área 2 (AI Search index → File Search del `AgenteUB`) y Área 3 (modelo Foundry deployment swap). Provee lectura read-only de Supabase a Área 4. |
| `notion-governance` | Refleja jerarquía Áreas en `registry/agents-canonical.yaml` (governance contract). Hospeda handoff draft + skill `agents-canonical-registry`. |

## 3. Las 4 Áreas

| # | Área | Output principal | Aterriza en | Piloto |
|---|---|---|---|---|
| 1 | **Inteligencia Comercial** | Lead profiles + scoring + ruta recomendada (Autodidacta/Guiada/Premium) | Notion DB Leads + Cosmos DB NoSQL | O16.3 (S4-S5) |
| 2 | **Conocimiento Técnico AECO** ⭐ | AI Search index `aeco-kb-{lang}-vYYYYMMDD` (ISO 19650, buildingSMART, vendor docs, normativa LATAM) | Foundry File Search del `AgenteUB` (consumido por `umbral-bot-2` con cita de versión) | O16.2 (S3-S4) — **principal** |
| 3 | **Datos y Modelos** | Datasets curados versionados + 1 fine-tuning experimental Phi-4 + eval results | Foundry model registry + Storage Blob + Cosmos DB | O16.6 (S5-S6, condicional) |
| 4 | **Ops de Producto Bot AECO** | KB refresh agendado + telemetría agregada + eval continuo + partner ops (estructura) | Foundry deployment swap de `umbral-bot-2`; lee Supabase read-only | O16.6 (S5-S6, parcial) |

**Nombre Área 4 confirmado** `Ops de Producto Bot AECO` — enfatiza ops/operación. Construcción del bot vive en `umbral-bot-2`; esta Área lo OPERA desde el stack.

## 4. Inventario inicial

**4 Áreas + 11 Gerencias + ~16 agentes/subagentes** (lista canónica con roles + subagent links en `registry/agents-canonical.yaml` §`autonomous_agent_operations_areas`).

Resumen por Gerencia:

```
Área 1: Inteligencia Comercial
├── Gerencia Lead Intelligence: lead_profiler + linkedin_scraper + empresa_info + tech_stack_detector
└── Gerencia Lead Scoring: lead_scoring (gpt-5 razonamiento)

Área 2: Conocimiento Técnico AECO  ⭐
├── Gerencia Estándares Globales: iso_buildingsmart_crawler + vendor_docs_harvester
├── Gerencia Normativa LATAM: latam_regulation_crawler
└── Gerencia Pipeline KB: pdf_parser + version_detector + index_publisher

Área 3: Datos y Modelos  (subdir umbral-agent-stack/data-science/)
├── Gerencia Datasets: dataset_builder + dataset_curator + dataset_versioner
└── Gerencia Training/Eval: fine_tuning_operator + eval_harness + model_registry_publisher

Área 4: Ops de Producto Bot AECO
├── Gerencia KB Refresh Ops: kb_refresh_orchestrator
├── Gerencia Telemetría & Insights: conversation_analyst
├── Gerencia Eval Continuo: continuous_eval_runner
└── Gerencia Partner Ops: partner_discount_curator (estructura preparatoria, NO onboarding Q2)
```

## 5. Reglas duras (routing + governance)

| Tipo de dato / consumidor | Backend | Razón |
|---|---|---|
| Producción usuarios externos (chat, auth, payments, RLS) | **Supabase** | Funciona en `umbral-bot-2`, RLS configurado. |
| Operación interna multi-agente + datos generados por agentes | **Azure** (Cosmos DB NoSQL serverless preferido; Storage Blob crudos; AI Search KB; Foundry modelos) | Consume Sponsorship + leverage. Cosmos NoSQL: vector search nativo + schema flexible + pay-per-op. |
| Vista humana navegable | **Notion** | David es consumidor principal. |

**Forbidden** (registry §`routing_rule.forbidden`):
- VM persistentes Azure.
- Escritura directa a Supabase desde agentes del stack.
- Subagents profundidad > 2.
- Anthropic Claude vía AOAI Foundry asumiendo cobertura Sponsorship (es Marketplace, NO cubre).
- Firecracker microVM en VPS Hostinger actual (no expone `/dev/kvm`).
- Reviewer (eval) en mismo contexto que implementer (sesgo confirma errores).
- Subagents pasando mensajes encadenados sin escribir a FS compartido (telephone game).
- Confiar en system prompt para bloquear comandos destructivos (requiere classifier determinístico pre-tool-call).
- Crear agente nuevo sin RFC-lite previo (80% queries AECO se resuelven con generalista + KB correcto).
- ACA scale-to-zero en servicio interactivo `bim-rag` (cold start 15-37s; `min_replicas=1` obligatorio).

## 6. Decisiones confirmadas (gaps cerrados 2026-05-06)

1. **Sources Área 2 LATAM (gap 1):** ✅ confirmado — Chile MINVU + Argentina IRAM + México NMX (top 3 ~80% PIB AECO LATAM hispano). Brasil fase 2 (idioma + ABNT). Perú/Colombia entran por pull, no push. Registry: `decision_status: confirmed_2026_05_06_david`. Habilita codear `latam_regulation_crawler` en O16.2.

2. **Estrategia Área 3 fine-tuning (gap 2):** ✅ confirmado — Q2 = datasets curados + RAG-first; sólo 1 fine-tuning experimental Phi-4 (open weights, dataset pequeño) en O16.6 para validar pipeline. Productivo = Q3 si eval continuo (Área 4) muestra gap específico que RAG no cierra. Registry: `decision_status: confirmed_2026_05_06_david`.

3. **Naming Área 4 (gap 3):** ✅ confirmado — `Ops de Producto Bot AECO`.

## 7. Pre-requisitos antes de O16.1

- O5 ✅ Plan B Hostinger decidido (libera 100% Sponsorship).
- O3.0 ✅ registry baseline con `autonomous_agent_operations_areas` poblado.
- O14 ✅ OpenClaw 5.3 instalado (soporta `subagents` + `parallel-specialist-lanes`).
- O7 ✅ formato tournament estándar definido (`docs/79-tournament-protocol-openclaw-native.md`) — no bloqueo duro pero complementa.
- **Pendiente runtime change**: `agents.defaults.subagents.maxSpawnDepth` 1→2 (PR separado + sign-off David vía skill `openclaw-vps-operator`). Mismo flag que bloquea primer tournament real.

## 8. Próximos pasos (checklist O16 del plan)

- O16.1 — Infra base Azure (Bicep, S2-S3).
- O16.2 — Piloto Área 2 KB AECO (S3-S4) ⭐.
- O16.3 — Piloto Área 1 Lead Intelligence (S4-S5).
- O16.4 — Observabilidad multi-agente sobre Mission Control (S4-S5).
- O16.5 — Hardening costos + plan off-Sponsorship (S5-S6, **deadline 2026-06-30**).
- O16.6 — Áreas 3 + 4 mínimas (S5-S6, condicional).

## 9. Métricas de éxito Q2 (medibles Friday retro 2026-06-26)

- Área 2: KB AECO viva publicada al menos 1 vez, citable por el bot, con versión visible.
- Área 1: ≥10 leads procesados end-to-end con scoring + ruta recomendada en Notion.
- Saldo Sponsorship gastado ≥ 50% en operación (no en VMs zombi).
- 0 incidentes de burn descontrolado.

## 10. Referencias

- Handoff completo (rationale, alternativas, trade-offs): `notion-governance/docs/handoffs/2026-05-06-O16-autonomous-agent-operations-azure.md`.
- Registry source-of-truth: `notion-governance/registry/agents-canonical.yaml` §`autonomous_agent_operations_areas`.
- Plan Q2-2026 §O16: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`.
- ADR tournament primitives: [`docs/adr/tournament-on-openclaw-primitives.md`](../adr/tournament-on-openclaw-primitives.md).
- Tournament protocol v1: [`docs/79-tournament-protocol-openclaw-native.md`](../79-tournament-protocol-openclaw-native.md).
- Modelo organizacional Rick CEO: [`docs/architecture/15-rick-organizational-model.md`](15-rick-organizational-model.md) v1.1 (referencia profundidad max + delegación).
- O5 decisión Plan B Hostinger: `notion-governance/docs/handoffs/2026-05-06-O5-codegen-backend-decision-plan-B-hostinger.md`.
- O6 audit Sponsorship: `notion-governance/docs/audits/2026-05-03-cloud-runway-audit.md`.
- ROADMAP `umbral-bot-2` (KB como snapshot operativo, gap a cerrar): `umbral-bot-codex-clean/docs/ROADMAP.md`.
- Skill `agents-canonical-registry`: `notion-governance/.agents/skills/agents-canonical-registry/SKILL.md`.
- Research synthesis: `notion-governance/docs/handoffs/2026-05-06-O16-research-synthesis-from-perplexity.md`.
