# O16.1 Smoke Deploy — Audit Report

**Date**: 2026-05-07
**Sub-task**: 044 (smoke deploy real)
**Subscription**: `f14f61f0-e692-4fbb-900d-73e55a632374` ("Azure subscription 1", `dm@umbralbim.cl`)
**Region**: `eastus2` (excepto AI Search → `eastus` por capacidad)
**Resource Group**: `rg-umbral-agents-prod`
**Deploy name (final OK)**: `umbral-agents-smoke-20260507-232057` (3rd attempt)
**Result**: ✅ Succeeded

---

## Recursos creados

| Tipo | Nombre | Región | Notas |
|---|---|---|---|
| `Microsoft.ManagedIdentity/userAssignedIdentities` | `uami-umbral-agents-prod` | eastus2 | UAMI única para todos los servicios |
| `Microsoft.OperationalInsights/workspaces` | `log-umbral-agents-prod` | eastus2 | LAW PerGB2018 30d retention |
| `Microsoft.Insights/components` | `appi-umbral-agents-prod` | eastus2 | AppInsights workspace-based |
| `Microsoft.App/managedEnvironments` | `cae-umbral-agents-prod` | eastus2 | Container Apps Env Consumption profile |
| `Microsoft.Storage/storageAccounts` | `stumbralagentsprod` | eastus2 | LRS Hot, 3 containers: `crudos`, `datasets-curados`, `eval-results` |
| `Microsoft.DocumentDB/databaseAccounts` | `cosmos-umbral-agents-prod` | eastus2 | Serverless + EnableNoSQLVectorSearch, DB `umbral-ops` con 4 containers (`agent-memory`, `leads`, `eval-results`, `mailbox-messages`) |
| `Microsoft.KeyVault/vaults` | `kv-umbral-agents-prod` | eastus2 | RBAC mode, soft-delete 90d, secret `appinsights-connection-string` ✓ |
| `Microsoft.ServiceBus/namespaces` | `sb-umbral-mailbox-prod` | eastus2 | Standard, topics `mailbox` (subs: `codex`, `claude`, `copilot-vps`, `copilot-chat`) + `eval-events` |
| `Microsoft.Search/searchServices` | `srch-umbral-kb-prod` | **eastus** | Basic SKU 1×1, semantic free, `aadOrApiKey` |
| `Microsoft.CognitiveServices/accounts` | `di-umbral-prod` | eastus2 | FormRecognizer S0, AAD-only |

**Budgets** (subscription scope, 10 total):

| Nombre | Cap USD/mes | Filtro tipo |
|---|---:|---|
| `umbral-foundry` | 3,500 | `Microsoft.CognitiveServices/accounts` |
| `umbral-container-apps` | 700 | `Microsoft.App/*` |
| `umbral-document-intelligence` | 400 | `Microsoft.CognitiveServices/accounts` (overlap con foundry) |
| `umbral-ai-search` | 300 | `Microsoft.Search/searchServices` |
| `umbral-storage` | 300 | `Microsoft.Storage/storageAccounts` |
| `umbral-app-insights` | 300 | `Microsoft.Insights/components` + `Microsoft.OperationalInsights/workspaces` |
| `umbral-service-bus` | 200 | `Microsoft.ServiceBus/namespaces` |
| `umbral-cosmos` | 200 | `Microsoft.DocumentDB/databaseAccounts` |
| `umbral-key-vault` | 50 | `Microsoft.KeyVault/vaults` |
| `umbral-total-monthly` | **7,206** | RG completo (Opción B Sponsorship) |

Thresholds: 50% / 80% / 100% Actual + 100% Forecasted → `alertas@umbralbim.cl`.

---

## Issues encontrados durante deploy + fixes aplicados

### 1. KV `RoleDefinitionDoesNotExist` (1er intento)

**Síntoma**: `The specified role definition with ID '4633458b17de457cb1cd3cf7ff1ed1e9' does not exist.`

**Root cause**: El built-in `Key Vault Secrets User` en esta subscription tiene ID **distinto al documentado oficialmente**.

| Source | Role ID |
|---|---|
| Documentación pública | `4633458b-17de-457c-b1cd-3cf7ff1ed1e9` |
| Esta subscription (`f14f61f0`) | `4633458b-17de-408a-b874-0445c86b69e6` |

Verificado: `az role definition list --name "Key Vault Secrets User" --query "[].name" -o tsv`.

**Fix**: `modules/key-vault.bicep` actualizado con el ID válido en esta sub. Comentario inline registra la discrepancia y método de verificación.

**Lección**: ⚠️ Antes de hardcodear IDs de built-in roles, verificar con `az role definition list --name "<role>"` en la subscription target. Algunos built-ins tienen GUIDs distintos en distintas suscripciones (presumiblemente por motivos históricos / migraciones internas de Azure).

### 2. AI Search `InsufficientResourcesAvailable` en eastus2 (intentos 1 y 2)

**Síntoma**: `The region 'eastus2' is currently out of the resources required to provision new services.`

**Root cause**: Capacidad agotada para SKU Basic en eastus2 al momento del smoke.

**Fix**: Param nuevo `searchLocation` en `main.bicep` (default `'eastus'`). El service de Search se despliega en region distinta al resto. Aceptable: cross-region latency desde container apps a search es <50ms intra US East coast.

**Trade-off documentado**: Egress costs entre eastus2 ↔ eastus son negligibles para tráfico de búsqueda esperado (<10 GB/mes).

### 3. DI `NetworkAclsBypassNotSupported` (1er intento)

**Síntoma**: `The Kind 'FormRecognizer' does not support Trusted Services.`

**Root cause**: `kind=FormRecognizer` no soporta `networkAcls.bypass='AzureServices'` (sí lo soportan otros kinds de Cognitive Services como OpenAI o TextAnalytics).

**Fix**: Removido `bypass: 'AzureServices'` de `modules/document-intelligence.bicep`. Reemplazado por `ipRules: []` + `virtualNetworkRules: []` explícitos con `defaultAction: 'Allow'`.

**Lección**: Cada `kind` de Cognitive Services tiene matriz distinta de propiedades soportadas. Verificar contra la doc específica del kind antes de copiar template de otro.

### 4. KV data-plane access para David (post-deploy manual)

**Síntoma**: David (`dm@umbralbim.cl`) no podía listar secrets vía `az keyvault secret list` (Forbidden).

**Root cause**: El param `kvAdminObjectId` quedó vacío en el primer deploy → no se creó la role assignment `Key Vault Administrator` para David.

**Fix manual**: Asignación creada vía `az role assignment create --role "Key Vault Administrator" --assignee-object-id daf2e5a6-25df-433b-bc05-32a7478ecd95 --scope <vault-id>`.

**Fix permanente**: `main.bicepparam` ahora incluye `param kvAdminObjectId = 'daf2e5a6-25df-433b-bc05-32a7478ecd95'` con comentario inline. Próximo `az deployment sub create` re-aplicará la asignación idempotentemente.

---

## Verificación final post-fixes

```text
✓ 10 recursos en rg-umbral-agents-prod
✓ 10 budgets en subscription scope
✓ KV secret 'appinsights-connection-string' creado y legible (post role grant)
✓ Storage 3 containers
✓ Cosmos DB 'umbral-ops' + 4 containers
✓ SB 2 topics + 4 subscriptions en mailbox
✓ Search Basic 1×1 succeeded en eastus
✓ DI FormRecognizer S0 endpoint https://di-umbral-prod.cognitiveservices.azure.com/
```

## Costo proyectado primer mes

| Servicio | Componente fijo | Estimación uso esperado |
|---|---:|---:|
| AI Search Basic | $75 prorrateado | $75 (capacity-based, no usage cost) |
| Service Bus Standard | $10 prorrateado | $10-20 |
| Document Intelligence S0 | $0 base | <$50 (per-page billing, smoke no consume) |
| Cosmos serverless | $0 base | <$5 (per RU, smoke no escribe) |
| Storage LRS | $0 base | <$1 (~0 GB) |
| Container Apps | $0 base | $0 (no apps deployadas aún) |
| Foundry | $0 base | $0 (no agents deployados) |
| Key Vault Standard | $0 base | <$1 (10k operations free tier) |
| AppInsights workspace | $0 base | <$5 (low ingestion) |
| LAW | $0 base | <$5 |
| **Total estimado mes 1 (smoke)** | **$85** | **~$100-150** |

Margen vs budget total ($7,206): **>97% disponible** para Foundry agents + Container Apps cuando se deployen en sub-tasks futuros.

---

## Acciones futuras sugeridas

1. **Q3 2026**: Evaluar tag `service=foundry|document-intelligence` en cada `Microsoft.CognitiveServices/accounts` para que los budgets `umbral-foundry` y `umbral-document-intelligence` se diferencien por tag en vez de overlap por tipo.
2. **Cuando se deploye Container App**: Validar que UAMI realmente puede leer secret de KV + escribir a Storage + Cosmos + SB + Search vía `DefaultAzureCredential`.
3. **Cuando AI Search vuelva a tener capacidad en eastus2**: Re-evaluar mover Search de eastus → eastus2 para colocar todo en una región (cambiar `searchLocation` default a `'eastus2'` y re-deploy).
4. **Foundry account / project**: Aún NO deployados. Pertenecen a sub-task O16.2+.

---

## Comandos de teardown (si hace falta limpiar)

```powershell
# Borrar todos los recursos del RG (preserva budgets)
az group delete --name rg-umbral-agents-prod --yes --no-wait

# Borrar budgets uno por uno (no hay batch)
$budgets = @('umbral-foundry','umbral-container-apps','umbral-document-intelligence','umbral-ai-search','umbral-storage','umbral-app-insights','umbral-service-bus','umbral-cosmos','umbral-key-vault','umbral-total-monthly')
foreach ($b in $budgets) { az consumption budget delete --budget-name $b }
```

## Closeout O16.1

Sub-tasks 039 (scaffold) → 040 (cross-cutting) → 041 (data plane) → 042 (agent services) → 043 (budgets) → 044 (smoke deploy) ejecutados en orden. **O16.1 cerrado**. Próxima épica O16.2: Foundry account + project + first agent deploy.
