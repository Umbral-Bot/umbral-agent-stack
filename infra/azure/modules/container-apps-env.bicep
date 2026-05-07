// =============================================================================
// container-apps-env.bicep — Container Apps Environment (Consumption plan)
// =============================================================================
// Sub-task: 2026-05-07-040 (O16.1 cross-cutting infra)
// AVM ref: br/public:avm/res/app/managed-environment:0.8.0
// Status: PLACEHOLDER — impl en 040
// =============================================================================
// Params esperados:
//   - name (string): 'cae-umbral-agents-${env}'
//   - location (string)
//   - tags (object)
//   - logAnalyticsWorkspaceId (string)
//   - logAnalyticsCustomerId (string)
//
// Outputs esperados:
//   - resourceId (string)
//   - defaultDomain (string)
//   - staticIp (string)
//
// Notas:
//   - Plan = consumption (scale-to-0)
//   - zoneRedundant = false (Sponsorship single-region)
//   - Workload profile: 'Consumption' (no dedicated)
//   - Container Apps Jobs específicas (crawler, ingester, eval) se crean en
//     repos de cada agente vía CI/CD, NO acá.
// =============================================================================

@description('Container Apps Environment name.')
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Log Analytics workspace resource ID.')
param logAnalyticsWorkspaceId string

@description('Log Analytics workspace customer (workspace) ID.')
param logAnalyticsCustomerId string

// TODO 040 — replace with AVM reference

// Outputs (placeholder)
output resourceId string = ''
output defaultDomain string = ''
output staticIp string = ''
