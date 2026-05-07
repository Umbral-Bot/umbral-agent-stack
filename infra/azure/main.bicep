// infra/azure/main.bicep
// O16 base infrastructure for Umbral autonomous agent operations.
//
// Scope: subscription. Creates one resource group per env and deploys all
// supporting Azure services for the O16 model documented in
// docs/architecture/17-areas-gerencias-agentes-subagentes-model.md
//
// HARD RULES (governance):
//   - Cero VMs persistentes.
//   - Autoscale a 0 donde el servicio lo permita.
//   - Managed identity para todo acceso entre servicios (no connection strings).
//   - Budget alert con hard cap por servicio.
//   - Tags obligatorios: env, owner, plan-ref, created-by.
//
// AVM coverage: this scaffold uses native resources for clarity. In production
// each `module` line below should be replaced by the equivalent
// `br/public:avm/res/<svc>/<type>` reference once AVM coverage is verified for
// every property we need. AVM gaps observed:
//   - Document Intelligence (Cognitive Services kind=FormRecognizer): AVM
//     covers via `avm/res/cognitive-services/account` but not all kinds in stable.
//   - Service Bus queue lifecycle / dead-letter detail tuning sometimes lags
//     stable AVM; verify before promoting.

targetScope = 'subscription'

@description('Azure region for all resources.')
param location string = 'eastus'

@description('Environment tag. Drives sizing.')
@allowed([
  'dev'
  'prod'
])
param env string = 'dev'

@description('Hard monthly USD cap for the budget alert. Triggers at 80%, 100%, 120%.')
param budgetCapUSD int = 200

@description('Email for budget + critical alerts.')
param alertEmail string = 'contacto@umbralbim.cl'

@description('Resource group name. Default: rg-umbral-o16-<env>.')
param resourceGroupName string = 'rg-umbral-o16-${env}'

var commonTags = {
  env: env
  owner: 'umbral-bim'
  'plan-ref': 'O16'
  'created-by': 'copilot-vps'
}

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: commonTags
}

module logws 'appinsights.bicep' = {
  name: 'appinsights'
  scope: rg
  params: {
    location: location
    env: env
    tags: commonTags
  }
}

module kv 'keyvault.bicep' = {
  name: 'keyvault'
  scope: rg
  params: {
    location: location
    env: env
    tags: commonTags
  }
}

module storage 'storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    location: location
    env: env
    tags: commonTags
  }
}

module cosmos 'cosmos.bicep' = {
  name: 'cosmos'
  scope: rg
  params: {
    location: location
    env: env
    tags: commonTags
  }
}

module search 'ai-search.bicep' = {
  name: 'ai-search'
  scope: rg
  params: {
    location: location
    env: env
    tags: commonTags
  }
}

module docint 'document-intelligence.bicep' = {
  name: 'document-intelligence'
  scope: rg
  params: {
    location: location
    env: env
    tags: commonTags
  }
}

module sb 'service-bus.bicep' = {
  name: 'service-bus'
  scope: rg
  params: {
    location: location
    env: env
    tags: commonTags
  }
}

module aca 'container-apps.bicep' = {
  name: 'container-apps'
  scope: rg
  params: {
    location: location
    env: env
    tags: commonTags
    logAnalyticsWorkspaceId: logws.outputs.logAnalyticsWorkspaceId
    appInsightsConnectionString: logws.outputs.appInsightsConnectionString
  }
}

// Action group lives inside the RG (its scope must match a deployable scope).
module budgetMod 'budget.bicep' = {
  name: 'budget-actiongroup'
  scope: rg
  params: {
    env: env
    alertEmail: alertEmail
    tags: commonTags
  }
}

// Budget itself is subscription-scoped (this file's targetScope).
resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: 'budget-umbral-o16-${env}'
  properties: {
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: '2026-05-01'
    }
    amount: budgetCapUSD
    category: 'Cost'
    notifications: {
      actual80: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: [ alertEmail ]
        contactGroups: [ budgetMod.outputs.actionGroupId ]
      }
      actual100: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: [ alertEmail ]
        contactGroups: [ budgetMod.outputs.actionGroupId ]
      }
      forecast120: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 120
        thresholdType: 'Forecasted'
        contactEmails: [ alertEmail ]
        contactGroups: [ budgetMod.outputs.actionGroupId ]
      }
    }
  }
}

output resourceGroupId string = rg.id
output keyVaultUri string = kv.outputs.keyVaultUri
output cosmosEndpoint string = cosmos.outputs.endpoint
output searchEndpoint string = search.outputs.endpoint
output storageAccountName string = storage.outputs.accountName
output serviceBusNamespace string = sb.outputs.namespaceName
output containerAppsEnvironmentId string = aca.outputs.environmentId
