// =============================================================================
// main.bicep — Umbral Agents Azure infra (subscription-scope orchestrator)
// =============================================================================
// Tasks:
//   - 2026-05-07-039 (scaffold)
//   - 2026-05-07-040 (cross-cutting infra: UAMI + LAW + AppInsights + CAE)
// targetScope: subscription (necesita crear el RG)
// =============================================================================

targetScope = 'subscription'

// -----------------------------------------------------------------------------
// Parámetros
// -----------------------------------------------------------------------------

@description('Environment name (prod / dev). Affects naming.')
@allowed(['prod', 'dev'])
param environment string = 'prod'

@description('Azure region for all resources.')
param location string = 'eastus2'

@description('Email recipient for budget + monitor alerts.')
param alertEmail string = 'alertas@umbralbim.cl'

@description('Total monthly budget cap in USD for the whole RG.')
@minValue(100)
@maxValue(15000)
param totalMonthlyBudgetUsd int = 7206

@description('Log Analytics retention in days.')
@minValue(30)
@maxValue(730)
param logRetentionDays int = 30

@description('Tags applied to the resource group + all resources.')
param tags object = {
  owner: 'david-moreira'
  project: 'umbral-agents'
  costCenter: 'sponsorship-2026'
  environment: environment
  managedBy: 'bicep'
}

// -----------------------------------------------------------------------------
// Variables (naming — CAF-aligned)
// -----------------------------------------------------------------------------

var rgName = 'rg-umbral-agents-${environment}'
var uamiName = 'uami-umbral-agents-${environment}'
var workspaceName = 'log-umbral-agents-${environment}'
var appInsightsName = 'appi-umbral-agents-${environment}'
var caeName = 'cae-umbral-agents-${environment}'

// -----------------------------------------------------------------------------
// Resource Group
// -----------------------------------------------------------------------------

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: tags
}

// -----------------------------------------------------------------------------
// Sub-task 040 — cross-cutting infra
// -----------------------------------------------------------------------------

module mod_uami 'modules/managed-identity.bicep' = {
  name: 'deploy-uami'
  scope: rg
  params: {
    name: uamiName
    location: location
    tags: tags
  }
}

module mod_logs 'modules/log-analytics.bicep' = {
  name: 'deploy-logs'
  scope: rg
  params: {
    workspaceName: workspaceName
    appInsightsName: appInsightsName
    location: location
    tags: tags
    retentionDays: logRetentionDays
    uamiPrincipalId: mod_uami.outputs.principalId
  }
}

module mod_cae 'modules/container-apps-env.bicep' = {
  name: 'deploy-cae'
  scope: rg
  params: {
    name: caeName
    location: location
    tags: tags
    logAnalyticsWorkspaceName: mod_logs.outputs.workspaceName
  }
}

// -----------------------------------------------------------------------------
// Sub-task 041 — data plane (PENDIENTE)
// -----------------------------------------------------------------------------
// module mod_storage 'modules/storage.bicep' = { ... }
// module mod_cosmos  'modules/cosmos.bicep' = { ... }
// module mod_kv      'modules/key-vault.bicep' = { ... }

// -----------------------------------------------------------------------------
// Sub-task 042 — agent-specific services (PENDIENTE)
// -----------------------------------------------------------------------------
// module mod_sb     'modules/service-bus.bicep' = { ... }
// module mod_search 'modules/ai-search.bicep' = { ... }
// module mod_di     'modules/document-intelligence.bicep' = { ... }

// -----------------------------------------------------------------------------
// Sub-task 043 — budget alerts (PENDIENTE)
// -----------------------------------------------------------------------------
// module mod_budgets 'modules/budget-alerts.bicep' = { ... }

// -----------------------------------------------------------------------------
// Outputs
// -----------------------------------------------------------------------------

output resourceGroupName string = rg.name
output resourceGroupId string = rg.id
output environment string = environment
output location string = location

// 040 cross-cutting
output uamiResourceId string = mod_uami.outputs.resourceId
output uamiPrincipalId string = mod_uami.outputs.principalId
output uamiClientId string = mod_uami.outputs.clientId

output logAnalyticsWorkspaceId string = mod_logs.outputs.workspaceId
output logAnalyticsCustomerId string = mod_logs.outputs.workspaceCustomerId
output appInsightsId string = mod_logs.outputs.appInsightsId

output containerAppsEnvId string = mod_cae.outputs.resourceId
output containerAppsEnvDefaultDomain string = mod_cae.outputs.defaultDomain
