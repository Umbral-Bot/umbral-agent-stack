# infra/azure/ — O16 base infrastructure (Bicep)

> **Status:** scaffold only. Validated via `bicep build`. **No `az deployment` has run.** First real deploy waits for explicit OK from David and confirmation of the 3 tentative resolutions in [docs/architecture/17-areas-gerencias-agentes-subagentes-model.md](../../docs/architecture/17-areas-gerencias-agentes-subagentes-model.md).

## What this stack creates

Subscription-scope deployment (`main.bicep`) that provisions one resource group `rg-umbral-o16-<env>` plus:

| Module | Resource | Purpose |
|---|---|---|
| `appinsights.bicep` | Log Analytics workspace + App Insights (workspace-based, sampling 25%, 30d retention) | Telemetry. |
| `keyvault.bicep` | Key Vault (RBAC mode, purge protection on) | Secrets, MI-only access. |
| `storage.bicep` | StorageV2 + 3 containers (`datasets`, `kb-raw`, `kb-processed`) + lifecycle (Cool 30d / Archive 90d) | Datasets + KB raw/processed. |
| `cosmos.bicep` | Cosmos DB NoSQL serverless + DB `umbral-internal` + 3 containers (`agents-state`, `eval-results`, `lead-profiles`) | Internal agent state. |
| `ai-search.bicep` | AI Search basic SKU (managed identity) | KB indexes `aeco-kb-{lang}-vYYYYMMDD`. |
| `document-intelligence.bicep` | Cognitive Services FormRecognizer S0 | PDF parsing for Área 2. |
| `service-bus.bicep` | Service Bus Standard + 2 queues (`lead-enrichment`, `kb-refresh`) | Inter-agent messaging. |
| `container-apps.bicep` | Container Apps Environment (Consumption profile) | Worker runtime, autoscale to 0. |
| `main.bicep` (top) | Action Group + monthly Budget alert (80% / 100% / 120%) | Cost guard. |

Mandatory tags applied to every resource: `env`, `owner=umbral-bim`, `plan-ref=O16`, `created-by=copilot-vps`.

## Hard governance rules baked in

- **Cero VMs persistentes.** No `Microsoft.Compute/virtualMachines` anywhere.
- **Autoscale a 0** where the service supports it (Container Apps min replicas 0; Cosmos serverless = pay per RU; Storage = pay per GB).
- **Managed identity only**: `disableLocalAuth: true` set on Cosmos, Service Bus, Document Intelligence, App Insights. Storage has `allowSharedKeyAccess: false`. Key Vault is RBAC-mode.
- **Budget hard cap** alerts at 80% actual / 100% actual / 120% forecast → email `contacto@umbralbim.cl`.
- **Public network access** is `Enabled` in this scaffold for dev convenience; **flip to private endpoints before prod first deploy**.

## AVM coverage notes

This scaffold uses native `Microsoft.<provider>/<type>` resources rather than `br/public:avm/res/...` modules. AVM is recommended for production but was deliberately not used here because:

1. **Faster review surface.** A reviewer can read each property directly without hopping into AVM module source.
2. **Pinning risk.** AVM stable versions sometimes lag the API version we want (e.g. Cosmos `2024-12-01-preview`, Service Bus DLQ tuning).
3. **Mixed kinds.** Document Intelligence (Cognitive Services kind=FormRecognizer) is on the boundary of AVM stable coverage; mixing AVM + native invites style drift.

Promotion plan: replace each module's body with the equivalent `br/public:avm/res/<svc>/<type>` reference once the AVM module exposes every property used here. Track per-module in the PR that does the AVM migration; not in this scaffold PR.

## Validate

Bicep CLI standalone (no `az` login required):

```bash
# Install (one-time)
mkdir -p ~/.local/bin
curl -sLo ~/.local/bin/bicep https://github.com/Azure/bicep/releases/latest/download/bicep-linux-x64
chmod +x ~/.local/bin/bicep
export PATH="$HOME/.local/bin:$PATH"

# Build (compiles to ARM JSON, surfaces all syntax/type errors)
bicep build infra/azure/main.bicep

# Lint
bicep lint infra/azure/main.bicep
```

Full `az deployment sub validate` and `az deployment sub what-if` require Azure login and were **NOT** executed during this scaffold's PR (REPO ONLY rule). After David confirms the 3 tentative resolutions:

```bash
# Login (interactive, on a workstation — NOT on the VPS)
az login --tenant <umbral-tenant>
az account set --subscription <sponsorship-sub>

# What-if (dry run, no changes)
az deployment sub what-if \
  --location eastus \
  --template-file infra/azure/main.bicep \
  --parameters env=dev budgetCapUSD=200

# Real deploy (after what-if reviewed)
az deployment sub create \
  --location eastus \
  --template-file infra/azure/main.bicep \
  --parameters env=dev budgetCapUSD=200
```

## Destroy (kill switch)

See [../../docs/runbooks/azure-off-sponsorship-2026-07-30.md](../../docs/runbooks/azure-off-sponsorship-2026-07-30.md) for the full kill-switch order and data export procedure (deadline 2026-06-30).

Quick kill: delete the resource group.

```bash
az group delete --name rg-umbral-o16-dev --yes --no-wait
```

This deletes every resource in the scaffold but does **not** delete the budget alert / action group (subscription-scoped). Remove those separately:

```bash
az consumption budget delete --budget-name budget-umbral-o16-dev
az monitor action-group delete --resource-group rg-umbral-o16-dev --name ag-umbral-o16-dev
```

## Cost monitoring

- Daily: budget alert fires automatically at thresholds.
- Weekly retro: open Cost Management → Cost analysis → filter `tag:plan-ref=O16` → trend by service.
- Track AI Search separately — basic SKU has a fixed ~$75/mo idle cost regardless of use.
