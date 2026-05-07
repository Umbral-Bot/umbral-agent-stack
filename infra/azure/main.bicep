// =============================================================================
// main.bicep — Umbral Agents Azure infra (subscription-scope orchestrator)
// =============================================================================
// Task: 2026-05-07-039 (O16.1 kickoff scaffold)
// Status: SCAFFOLD — modules referenciados como placeholders; impl en 040-044
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

@description('Tags applied to the resource group + all resources.')
param tags object = {
  owner: 'david-moreira'
  project: 'umbral-agents'
  costCenter: 'sponsorship-2026'
  environment: environment
  managedBy: 'bicep'
}

// -----------------------------------------------------------------------------
// Variables (naming)
// -----------------------------------------------------------------------------

var rgName = 'rg-umbral-agents-${environment}'

// -----------------------------------------------------------------------------
// Resource Group
// -----------------------------------------------------------------------------

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: tags
}

// -----------------------------------------------------------------------------
// Modules — PLACEHOLDERS (impl en sub-tasks 040-044)
// -----------------------------------------------------------------------------
// Cada module está documentado como header en modules/*.bicep con:
//   - AVM ref que usará
//   - params esperados
//   - outputs esperados
//   - sub-task de implementación
//
// Activación incremental:
//   040 → managed-identity, log-analytics, container-apps-env
//   041 → storage, cosmos, key-vault
//   042 → service-bus, ai-search, document-intelligence
//   043 → budget-alerts
// -----------------------------------------------------------------------------

// Sub-task 040 — cross-cutting
// module mi 'modules/managed-identity.bicep' = { ... }
// module logs 'modules/log-analytics.bicep' = { ... }
// module cae 'modules/container-apps-env.bicep' = { ... }

// Sub-task 041 — data plane
// module storage 'modules/storage.bicep' = { ... }
// module cosmos 'modules/cosmos.bicep' = { ... }
// module kv 'modules/key-vault.bicep' = { ... }

// Sub-task 042 — agent-specific services
// module sb 'modules/service-bus.bicep' = { ... }
// module search 'modules/ai-search.bicep' = { ... }
// module di 'modules/document-intelligence.bicep' = { ... }

// Sub-task 043 — budget alerts
// module budgets 'modules/budget-alerts.bicep' = { ... }

// -----------------------------------------------------------------------------
// Outputs
// -----------------------------------------------------------------------------

output resourceGroupName string = rg.name
output resourceGroupId string = rg.id
output environment string = environment
output location string = location
