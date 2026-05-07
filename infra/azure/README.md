# Umbral Agents — Azure Infrastructure (Bicep + AVM)

> **Status**: scaffold — task `2026-05-07-039` (O16.1 kickoff)
> **Owner**: David Moreira / Umbral BIM
> **Last update**: 2026-05-07

## Propósito

Infraestructura base Azure para soportar el modelo organizacional de 4 Áreas / 11 Gerencias / ~16 agentes definido en `docs/architecture/17-areas-gerencias-agentes-subagentes-model.md`.

**Alcance**: Container Apps Jobs efímeros + Cosmos DB + AI Search + Storage + Key Vault + Service Bus + App Insights + Document Intelligence. **Sin VMs persistentes**.

**Deadline duro**: Sponsorship $21,619 expira **2026-07-30**. Hardening costos hito **2026-06-30** (O16.5).

---

## Decisiones rectoras

| # | Decisión | Valor | Justificación |
|---|---|---|---|
| 1 | IaC tool | **Bicep + AVM** | Azure-only stack; sin state file (ARM es state); AVM oficial MS; 1 comando deploy |
| 2 | Resource Groups | **1 RG (`rg-umbral-agents`) + tags** | 1 owner; Cost Management filtra por tag `area=1\|2\|3\|4`; nuke de un golpe al expirar Sponsorship |
| 3 | Region | **`eastus2`** | Default Sponsorship + cobertura completa Foundry / AI Search / Cosmos vector |
| 4 | Subscription | 1 Sponsorship sub | Sin separación dev/prod (Q2 es proof-of-concept; Q3 evaluar) |
| 5 | Identidad | 1 User-Assigned MI `uami-umbral-agents` | Compartida por Container Apps Jobs; RBAC least-privilege |
| 6 | Secrets store | **Key Vault** único | Container Apps leen vía `secretRef` con MI |
| 7 | Email alerts | **`alertas@umbralbim.cl`** | Param `alertEmail`; budgets + monitor alerts |
| 8 | Budget approach | Per-service + total monthly | Threshold 50% / 80% / 100% → email |

---

## Naming convention

CAF (Cloud Adoption Framework) abreviaciones + sufijo `-{env}`:

| Servicio | Patrón | Ejemplo |
|---|---|---|
| Resource Group | `rg-umbral-agents-{env}` | `rg-umbral-agents-prod` |
| Container Apps Env | `cae-umbral-agents-{env}` | `cae-umbral-agents-prod` |
| Storage Account | `stumbralagents{env}` | `stumbralagentsprod` (≤24 chars, lowercase) |
| Cosmos DB | `cosmos-umbral-ops-{env}` | `cosmos-umbral-ops-prod` |
| AI Search | `srch-umbral-kb-{env}` | `srch-umbral-kb-prod` |
| Key Vault | `kv-umbral-{env}-001` | `kv-umbral-prod-001` (≤24 chars, único global) |
| Service Bus | `sb-umbral-mailbox-{env}` | `sb-umbral-mailbox-prod` |
| App Insights | `appi-umbral-agents-{env}` | `appi-umbral-agents-prod` |
| Log Analytics | `log-umbral-agents-{env}` | `log-umbral-agents-prod` |
| Document Intelligence | `di-umbral-{env}` | `di-umbral-prod` |
| Managed Identity | `uami-umbral-agents-{env}` | `uami-umbral-agents-prod` |

---

## RBAC matrix (User-Assigned MI `uami-umbral-agents`)

Codificado vía `roleAssignments` param de cada AVM module (NO `Microsoft.Authorization/roleAssignments` manual).

| Servicio | Rol | Built-in role ID | Justificación |
|---|---|---|---|
| Storage account | **Storage Blob Data Contributor** | `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | Crudos + datasets read/write |
| Cosmos DB (data plane) | **Cosmos DB Built-in Data Contributor** | `00000000-0000-0000-0000-000000000002` | Memoria agentes, leads, eval results |
| AI Search (data) | **Search Index Data Contributor** | `8ebe5a00-799e-43f5-93ac-243d3dce84a7` | Read/write index `aeco-kb-{lang}-vYYYYMMDD` |
| AI Search (mgmt) | **Search Service Contributor** | `7ca78c08-252a-4471-8644-bb5ff32d4ba0` | Crear/eliminar indexes |
| Key Vault | **Key Vault Secrets User** | `4633458b-17de-4321-b1ad-d9bb4dd5ad8a` | Solo lectura secretos |
| Service Bus | **Azure Service Bus Data Sender** | `69a216fc-b8fb-44d8-bc22-1f3c2cd27a39` | Send mailbox |
| Service Bus | **Azure Service Bus Data Receiver** | `4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0` | Receive mailbox |
| Document Intelligence | **Cognitive Services User** | `a97b65f3-24c7-4388-baec-2e87135dc908` | OCR/parsing PDFs |
| App Insights | **Monitoring Metrics Publisher** | `3913510d-42f4-4e42-8a64-420c390055eb` | Telemetría custom |

---

## Budget plan (Sponsorship $21,619 / ≈3 meses → $7,206/mes)

**Estrategia: Opción B conservadora** — AI Search Basic + Cosmos serverless puro + buffer reasignable a Foundry.

| Servicio | $/mes | Tier inicial | Notas |
|---|---|---|---|
| Foundry (modelos + File Search) | **$3,500** | gpt-4o-mini default + Phi-4 experimental | Mayor volatilidad — el buffer migra acá |
| AI Search | **$300** | Basic ($75 base) + queries | Promover a Standard solo si KB >5GB |
| Cosmos DB serverless | **$200** | Serverless puro | RU/s pay-per-op + vector |
| Container Apps Jobs | **$700** | Consumption plan | Scale-to-0; spikes por crawler |
| Storage Blob | **$300** | Hot tier | Crudos PDFs + datasets |
| Document Intelligence | **$400** | Pay-per-page S0 | OCR LATAM |
| Service Bus | **$200** | Standard | Mailbox cross-agente |
| App Insights + Log Analytics | **$300** | 30d retention | Telemetría |
| Key Vault | **$50** | Standard | Operaciones secretos |
| **Buffer / imprevistos** | **$1,256** | — | 17% — reasignable |
| **TOTAL** | **$7,206/mes** | | |

**Budget alerts (codificados en `modules/budget-alerts.bicep`)**:

- Per-service: 1 budget por línea con thresholds 50% / 80% / 100% → email `alertas@umbralbim.cl`.
- `total-monthly`: $7,206 con thresholds 50% / 80% / 100%.
- **Hard stop**: NO automático (requiere Action Group + Logic App custom). Manual review en runbook `docs/runbooks/azure-budget-exceeded.md` (a crear en task 043).

---

## Estructura del directorio

```
infra/azure/
├── README.md                       # este archivo
├── main.bicep                      # orquestador subscription-scope
├── main.bicepparam                 # params dev/prod toggle
├── modules/
│   ├── resource-group.bicep        # RG + tags por Área
│   ├── managed-identity.bicep      # UAMI compartida
│   ├── log-analytics.bicep         # workspace + App Insights
│   ├── container-apps-env.bicep    # CAE consumption
│   ├── storage.bicep               # Storage account + RBAC
│   ├── cosmos.bicep                # Cosmos NoSQL serverless + RBAC
│   ├── ai-search.bicep             # AI Search Basic + RBAC
│   ├── key-vault.bicep             # KV + RBAC + secret seed
│   ├── service-bus.bicep           # SB Standard + queues + RBAC
│   ├── document-intelligence.bicep # DI account + RBAC
│   └── budget-alerts.bicep         # budgets per-service + total
└── scripts/
    ├── validate.ps1                # az deployment sub validate
    ├── what-if.ps1                 # az deployment sub what-if
    └── deploy.ps1                  # az deployment sub create (con prompt)
```

---

## Plan de deploy incremental

| Sub-task | Scope | Outcome |
|---|---|---|
| **039 (este)** | Scaffold + decisiones + RBAC matrix + budget plan + AVM placeholders | PR open con scaffold; `validate` pasa contra stub |
| **040** | Implementar `main.bicep` real + Container Apps Env + Log Analytics + App Insights | Cross-cutting infra desplegable |
| **041** | Storage + Cosmos + Key Vault + RBAC | Data plane completo |
| **042** | Service Bus + AI Search + Document Intelligence | Servicios específicos a agentes |
| **043** | Budget alerts + monitoring dashboards + runbook `azure-budget-exceeded.md` | Hardening costos |
| **044** | Smoke deploy real Sponsorship: `validate` → `what-if` → `create` → `az resource list` | Infra base productiva |

---

## Cómo deployar (cuando 040-044 estén listos)

```powershell
# 1. Login a la sub Sponsorship
az login
az account set --subscription "<SPONSORSHIP_SUB_ID>"

# 2. Validar (no consume créditos)
./scripts/validate.ps1

# 3. What-if (preview de cambios; no consume créditos)
./scripts/what-if.ps1

# 4. Deploy real (con prompt de confirmación)
./scripts/deploy.ps1
```

Subscription ID NO se commitea — se pasa via env var `AZURE_SUBSCRIPTION_ID` o se prompta en `deploy.ps1`.

---

## TODO confirmar (decisiones pendientes / a calibrar)

- [ ] Subscription ID Sponsorship — leer de `az account show` al primer deploy.
- [ ] AAD tenant ID para Key Vault `tenantId` — auto-resuelto en runtime.
- [ ] Object ID de David para RBAC `Key Vault Administrator` — leer al deploy via `az ad signed-in-user show`.
- [ ] Calibrar budget split mes 1 con datos reales (revisar 2026-06-07 en Friday retro).
- [ ] Decidir si environment es `prod` único o agregar `dev` separado en Q3.

---

## Salvavidas operativos

- **NO deploy real** se hace desde 039. Solo `validate`.
- **NO commit** de subscription IDs, tenant IDs, secrets, object IDs.
- **NO touch** runtime VPS desde este directorio (Hostinger es independiente).
- **F-INC-002** estricto antes de push.
- **secret-output-guard #8**: secrets via `@secure()` params + Key Vault. NO en logs.
- AVM modules vía `br/public:avm/res/...` con versión pinneada (no `latest`).

---

## Referencias

- ADR canónico: [`docs/architecture/17-areas-gerencias-agentes-subagentes-model.md`](../../docs/architecture/17-areas-gerencias-agentes-subagentes-model.md)
- ADR Plan B Hostinger (libera Sponsorship): [`docs/adr/05-vps-vs-azure-decision.md`](../../docs/adr/05-vps-vs-azure-decision.md)
- Plan Q2 O16: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`
- Spec kickoff: [`.agents/tasks/2026-05-07-039-o16-1-kickoff-bicep-infra-azure.md`](../../.agents/tasks/2026-05-07-039-o16-1-kickoff-bicep-infra-azure.md)
- Azure Verified Modules (Bicep): https://aka.ms/avm/bicep
