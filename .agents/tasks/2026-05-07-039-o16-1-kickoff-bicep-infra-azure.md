---
id: 2026-05-07-039
title: O16.1 kickoff — scaffold Bicep infra base Azure (AVM modules + RBAC + budgets)
status: open
priority: P1 (deadline duro Sponsorship 2026-06-30)
assigned_to: codex
created_at: 2026-05-07
created_by: claude (post-O15.1b closure, siguiente sequential del plan Q2)
parent: O16.1 (plan Q2 línea ~895)
relates_to: docs/architecture/17-areas-gerencias-agentes-subagentes-model.md, docs/adr/05-vps-vs-azure-decision.md (Plan B Hostinger)
blocks: O16.2, O16.3, O16.4, O16.5, O16.6
---

# 039 — O16.1 kickoff: scaffold Bicep infra base Azure

## Contexto

Plan Q2 O16 cerró diseño organizacional (O16.0 ✅) con ADR 17 (`17-areas-gerencias-agentes-subagentes-model.md`) — 4 Áreas + 11 Gerencias + ~16 agentes. El saldo Sponsorship $21,619 expira **2026-07-30** (deadline budget) y O16.5 marca **2026-06-30** como deadline para hardening costos. Quedan **54 días** desde 2026-05-07 hasta el deadline duro.

Este task **NO implementa todo el Bicep** — produce el scaffold + decomposición en sub-tasks ejecutables independientemente. La implementación full se reparte en PRs incrementales (1 servicio por PR, idealmente).

## Scope (entregables concretos)

### 1. Estructura del directorio `infra/azure/`

Crear scaffold (vacío de lógica, con README + `main.bicep` orquestador stub):

```
infra/azure/
├── README.md                      # decisiones, naming, RBAC matrix, deploy howto
├── main.bicep                     # orquestador subscription-scope (targetScope='subscription')
├── main.bicepparam                # params para 1 environment (dev/prod toggle)
├── modules/
│   ├── container-apps-env.bicep   # AVM: avm/res/app/managed-environment
│   ├── service-bus.bicep          # AVM: avm/res/service-bus/namespace
│   ├── storage.bicep              # AVM: avm/res/storage/storage-account
│   ├── cosmos.bicep               # AVM: avm/res/document-db/database-account (NoSQL serverless)
│   ├── ai-search.bicep            # AVM: avm/res/search/search-service
│   ├── key-vault.bicep            # AVM: avm/res/key-vault/vault
│   ├── app-insights.bicep         # AVM: avm/res/insights/component + log-analytics workspace
│   ├── document-intelligence.bicep # AVM: avm/res/cognitive-services/account (kind=FormRecognizer)
│   └── budget-alerts.bicep        # AVM: avm/res/consumption/budget
└── scripts/
    ├── validate.ps1               # az deployment sub validate
    ├── what-if.ps1                # az deployment sub what-if
    └── deploy.ps1                 # az deployment sub create (con confirmación)
```

### 2. Decisiones a documentar en `infra/azure/README.md`

- **Subscription target**: 1 sola sub Sponsorship; resource group único `rg-umbral-agents-{env}` o múltiples por área. **Recomendación inicial**: 1 RG `rg-umbral-agents` (simple) + tags por Área (`area=1|2|3|4`). Justificar.
- **Naming convention**: `{tipo}-umbral-{servicio}-{env}` (ej `cae-umbral-agents-prod`, `cosmos-umbral-ops-prod`, `kv-umbral-prod-001`). Adherirse a CAF (Cloud Adoption Framework) abreviaciones.
- **Region**: `eastus2` (default Sponsorship + mayor disponibilidad de Foundry/AI Search). Confirmar en script `validate.ps1`.
- **Identidad**: 1 User-Assigned Managed Identity (`uami-umbral-agents`) compartida por Container Apps Jobs. RBAC asignado a esa MI sobre cada servicio (least-privilege).
- **Secrets**: Key Vault como único store. Container Apps Jobs leen vía `secretRef` con MI. `NOTION_API_KEY`, `OPENAI_*`, etc., ahí.
- **No VMs persistentes**. Container Apps Jobs efímeros + Functions + autoscale-to-0 (consumption plan).
- **Budgets**: 1 budget por servicio con threshold 50% / 80% / 100% → alert email a David. Hard cap via budget action (si Azure lo soporta; si no, monitor + manual stop).

### 3. Matriz RBAC mínima (User-Assigned MI `uami-umbral-agents`)

| Servicio | Rol | Justificación |
|---|---|---|
| Storage account | Storage Blob Data Contributor | Crudos + datasets read/write |
| Cosmos DB | Cosmos DB Built-in Data Contributor | Memoria agentes, leads, eval results |
| AI Search | Search Index Data Contributor + Search Service Contributor | Crear/actualizar indexes `aeco-kb-{lang}-vYYYYMMDD` |
| Key Vault | Key Vault Secrets User | Solo lectura secretos (no admin) |
| Service Bus | Azure Service Bus Data Sender + Receiver | Mailbox cross-agente |
| Document Intelligence | Cognitive Services User | OCR/parsing PDFs |
| App Insights | Monitoring Metrics Publisher | Telemetría |

Documentar en README; codificar via `roleAssignments` param de los AVM modules (no manual `Microsoft.Authorization/roleAssignments`).

### 4. Budget alerts

- **Per-service budgets**: Cosmos $X, AI Search $Y, Storage $Z, Container Apps $W, Foundry $V. Sumar ≤ $21,619 / 3 (margen para 3 meses operación).
- **Alert thresholds**: 50% (warning), 80% (alert), 100% (action — qué acción exacta? definir).
- **Email recipients**: David's email (env var, no hardcoded).

### 5. Plan de deploy incremental (sub-tasks futuros)

Después de 039 (scaffold), abrir tasks separados:

- `040` — Implementar `main.bicep` + Container Apps Environment + Log Analytics + App Insights (servicios cross-cutting).
- `041` — Storage + Cosmos DB + Key Vault + RBAC (data plane).
- `042` — Service Bus + AI Search + Document Intelligence (servicios específicos a agentes).
- `043` — Budget alerts + monitoring dashboards.
- `044` — Smoke deploy a Sponsorship con `az deployment sub validate` + `what-if` + create real → smoke `az resource list -g rg-umbral-agents`.

Este task 039 produce solo el **scaffold + decisiones**, no PRs de implementación.

## Acceptance

- [ ] `infra/azure/` creado con estructura listada en §1.
- [ ] `README.md` con decisiones §2 + matriz RBAC §3 + budget plan §4 + plan incremental §5.
- [ ] `main.bicep` stub válido (`targetScope='subscription'`, `var location = 'eastus2'`, sin recursos aún o con 1 dummy resource group si necesita pasar `validate`).
- [ ] `main.bicepparam` con params placeholder.
- [ ] Cada `modules/*.bicep` con header comment + import del AVM module correcto + lista de params esperados (sin lógica todavía).
- [ ] Scripts `validate.ps1`/`what-if.ps1`/`deploy.ps1` funcionales contra el stub (validate debería pasar aunque no haya recursos).
- [ ] PR opens en `umbral-agent-stack/main` con esos archivos. NO requiere deploy real a Azure todavía.
- [ ] Plan Q2 actualizado (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`) — O16.1 marcada "scaffold ✅, sub-tasks 040-044 abiertas".

## Salvavidas

- **NO deploy real a Azure** en este task. Solo `validate` (no consume créditos).
- **NO touch** runtime VPS (gateway/worker/dispatcher). Este task es 100% repo-only.
- **NO hardcodear** subscription IDs, tenant IDs, emails. Usar `bicepparam` o env vars.
- **F-INC-002** estricto antes de push.
- **secret-output-guard** #8: NO commitear secrets. AVM modules generan password/keys via `@secure()` params + Key Vault.
- Preferir **AVM (Azure Verified Modules)** del registro `br/public:avm/res/...` en lugar de modules custom. Reduce mantenimiento.

## Capitalización

- Skill `azure-bicep-avm-scaffold` (reusable para futuros stacks Azure de Umbral).
- README.md de `infra/azure/` queda como source-of-truth para deploys futuros.
- Plan de sub-tasks 040-044 da visibilidad de cuántas semanas faltan a O16.1 100%.

## Decisiones a confirmar con David antes de PR

- [ ] **Bicep vs Terraform**: plan Q2 dice Bicep. ¿Confirmar? (Bicep recomendado: native Azure, mejor integración Sponsorship, AVM más maduro para Azure puro).
- [ ] **1 RG vs múltiples**: recomendación 1 RG con tags. ¿Aceptar?
- [ ] **Region**: `eastus2`. ¿OK?
- [ ] **Email para alerts**: ¿`david@umbralbim.cl`? (env var)
- [ ] **Budget split**: $21,619 / 3 meses ≈ $7,206/mes. ¿Aceptar el split por servicio propuesto o pide otro?

Si David no responde estos 5 antes de empezar, asumir defaults documentados y dejar marcado `## TODO confirmar` en README.
