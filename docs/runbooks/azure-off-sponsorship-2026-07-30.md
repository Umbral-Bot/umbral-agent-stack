# Runbook — Azure off-Sponsorship transition (deadline 2026-07-30)

- **Status:** Active.
- **Owner:** umbral-bim (David).
- **Hard deadline:** **2026-07-30** — Azure Sponsorship balance ($21,619 at 2026-05-06) expires. Pay-as-you-go billing starts the next day at full retail prices.
- **O16.5 hardening soft deadline:** **2026-06-30** — by this date all O16 surfaces in `infra/azure/` must be either (a) stopped, (b) migrated to a billable subscription with explicit budget approval, or (c) torn down with data exported.
- **Related:**
  - [docs/architecture/17-areas-gerencias-agentes-subagentes-model.md](../architecture/17-areas-gerencias-agentes-subagentes-model.md)
  - [infra/azure/README.md](../../infra/azure/README.md)
  - [docs/adr/ADR-009-mission-control-scope.md](../adr/ADR-009-mission-control-scope.md)

---

## 1. Activation triggers

Activate this runbook when **any** of the following is true:

1. **Calendar:** today is on or after `2026-06-30` (28 days before Sponsorship expiry).
2. **Burn alert:** budget alert fires `Forecasted >120%` for two consecutive months.
3. **Balance:** Sponsorship remaining balance < $2,000 USD.
4. **Decision:** David explicitly says "off-Sponsorship".

If only trigger #2 fires, prefer scoping down (right-size, scale to 0, remove premium SKUs) before tearing down.

## 2. Kill-switch order

Order is by **(cost descending, criticality ascending)**: highest-cost / least-critical first, lowest-cost / most-critical last.

| Order | Component | Bicep module | Why this order | Kill command (RG: `rg-umbral-o16-<env>`) |
|---|---|---|---|---|
| 1 | **AI Search basic** | `ai-search.bicep` | ~$75/mo idle regardless of use; rebuildable from raw KB blobs in Storage. | `az search service delete -g rg-umbral-o16-<env> -n <name>` |
| 2 | **Document Intelligence S0** | `document-intelligence.bicep` | Per-page billing; eliminate after KB raw → processed batch is done. | `az cognitiveservices account delete -g rg-umbral-o16-<env> -n <name>` |
| 3 | **Container Apps Environment** | `container-apps.bicep` | Per-vCPU-second when active; scaling to 0 already minimizes but env itself bills small fixed. | `az containerapp env delete -g rg-umbral-o16-<env> -n cae-umbral-o16-<env>` |
| 4 | **Service Bus Standard** | `service-bus.bicep` | ~$10/mo namespace fee + ops; harmless if no agents are running. | `az servicebus namespace delete -g rg-umbral-o16-<env> -n <name>` |
| 5 | **Cosmos DB serverless** | `cosmos.bicep` | Pay-per-RU + storage. **Export first** (see §3). | `az cosmosdb delete -g rg-umbral-o16-<env> -n <name> --yes` |
| 6 | **Storage Account** | `storage.bicep` | Cheapest at rest (Cool/Archive after lifecycle). **Export first** (see §3). | `az storage account delete -g rg-umbral-o16-<env> -n <name> --yes` |
| 7 | **App Insights + Log Analytics** | `appinsights.bicep` | Tiny cost; keep last for forensic diff if cost spike investigation needed. | (deletes with RG below) |
| 8 | **Key Vault** | `keyvault.bicep` | **Soft-delete + purge protection** is on. After RG delete, vault stays in soft-delete 7 days. Run `az keyvault purge` only if you are sure no rollback is needed. | `az keyvault delete -g rg-umbral-o16-<env> -n <name>` then `az keyvault purge -n <name>` |
| 9 | **Resource Group** | (all of `main.bicep`) | Single command deletes everything left. | `az group delete --name rg-umbral-o16-<env> --yes --no-wait` |
| 10 | **Budget alert + Action Group** | `budget.bicep`, top of `main.bicep` | Subscription-scoped, NOT removed by RG delete. | `az consumption budget delete --budget-name budget-umbral-o16-<env>`<br>`az monitor action-group delete -g rg-umbral-o16-<env> -n ag-umbral-o16-<env>` |

> **Quick-kill (skip per-service order, accept full data loss):** `az group delete --name rg-umbral-o16-<env> --yes --no-wait` + step 10. Use only when balance is already drained and there is nothing worth exporting.

## 3. Data export (do BEFORE steps 5 and 6)

### 3.1 Cosmos DB → JSON in `umbral-agent-stack/.cache/exports/`

For each container in DB `umbral-internal` (`agents-state`, `eval-results`, `lead-profiles`):

```bash
az cosmosdb sql container show \
  -g rg-umbral-o16-<env> -a <cosmos-account> -d umbral-internal -n <container> \
  > /tmp/${container}-meta.json

# Use Cosmos DB Data Migration Tool or SDK script. Example with Azure SDK:
python3 scripts/azure/export_cosmos.py \
  --endpoint https://<cosmos-account>.documents.azure.com:443/ \
  --db umbral-internal \
  --container <container> \
  --out .cache/exports/cosmos-<container>-$(date +%Y%m%d).jsonl
```

(`scripts/azure/export_cosmos.py` is **not yet implemented** — create when this runbook is first activated. Use `azure-cosmos` Python SDK with managed identity.)

Verify: `wc -l .cache/exports/cosmos-*.jsonl` matches container counts within ±0.1%.

### 3.2 Storage Blob → archive bundle

```bash
mkdir -p .cache/exports/storage
az storage blob download-batch \
  --auth-mode login \
  --account-name <storage-account> \
  --source datasets \
  --destination .cache/exports/storage/datasets/

az storage blob download-batch \
  --auth-mode login \
  --account-name <storage-account> \
  --source kb-processed \
  --destination .cache/exports/storage/kb-processed/

# kb-raw is regenerable from upstream sources; export only if not.
```

Bundle and move off-VPS:

```bash
tar -czf umbral-azure-export-$(date +%Y%m%d).tar.gz .cache/exports/
sha256sum umbral-azure-export-*.tar.gz | tee .cache/exports/SHA256SUMS
# Move to David's external storage (NOT to umbral-agent-stack git history).
```

### 3.3 AI Search index definitions (schema only — data regenerable)

```bash
for IDX in $(az search index list -g rg-umbral-o16-<env> --service-name <search-name> --query '[].name' -o tsv); do
  az search index show -g rg-umbral-o16-<env> --service-name <search-name> --name "$IDX" \
    > .cache/exports/search-${IDX}-schema.json
done
```

### 3.4 Key Vault → secret list (NOT values)

Soft-delete (purge protection enabled) keeps secrets recoverable for 7 days after vault delete. Just record what existed:

```bash
az keyvault secret list --vault-name <kv-name> --query '[].name' -o tsv \
  > .cache/exports/keyvault-secret-names.txt
```

**Do not export secret values to the repo or to local files.** If migration to another vault is needed, do it MI-to-MI vault-to-vault, not through file intermediates.

## 4. Rollback (within 7 days)

If you delete the RG and decide to restore:

- **Cosmos:** restore from periodic backup (168h retention configured in `cosmos.bicep`). Open a support ticket. ETA ~hours.
- **Storage:** soft-delete 7d on blobs + 7d on containers (configured in `storage.bicep`). Use `az storage blob undelete`.
- **Key Vault:** `az keyvault recover -n <kv-name>` within 7 days.
- **Bicep redeploy:** `az deployment sub create --location eastus --template-file infra/azure/main.bicep --parameters env=<env> budgetCapUSD=<cap>` recreates everything else.

After 7 days, recovery is impossible without exports from §3.

## 5. Post-kill verification

Run within 24 h of completing the kill order:

```bash
# 1. RG gone
az group exists --name rg-umbral-o16-<env>          # => false

# 2. No subscription budget left
az consumption budget list --query '[].name' -o tsv | grep umbral-o16   # => empty

# 3. No Action Group orphaned
az monitor action-group list --query '[].name' -o tsv | grep umbral-o16 # => empty

# 4. Cost should drop to 0 within 48h. Verify in Cost Management:
#    Azure Portal → Cost Management → Cost analysis → filter tag:plan-ref=O16
```

If anything remains and you are sure all data is exported, force-delete and document in a SEV-1 retro under `docs/ops/`.

## 6. After-action

1. Move `.cache/exports/*.tar.gz` to David's offline backup. Do NOT commit.
2. Open ADR documenting the off-Sponsorship decision and what was kept / what was archived.
3. Update [docs/architecture/17-areas-gerencias-agentes-subagentes-model.md](../architecture/17-areas-gerencias-agentes-subagentes-model.md) status block from `planned_q2_2026` → `archived_2026_<MM>` for affected areas.
4. Add this runbook activation to the next Friday retro.
