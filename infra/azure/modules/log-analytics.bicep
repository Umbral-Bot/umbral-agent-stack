// =============================================================================
// log-analytics.bicep — Log Analytics Workspace + App Insights
// =============================================================================
// Sub-task: 2026-05-07-040 (O16.1 cross-cutting infra)
// AVM refs:
//   - br/public:avm/res/operational-insights/workspace:0.7.0
//   - br/public:avm/res/insights/component:0.4.0
// Status: PLACEHOLDER — impl en 040
// =============================================================================
// Params esperados:
//   - workspaceName (string): 'log-umbral-agents-${env}'
//   - appInsightsName (string): 'appi-umbral-agents-${env}'
//   - location (string)
//   - tags (object)
//   - retentionDays (int): 30
//
// Outputs esperados:
//   - workspaceId (string)
//   - workspaceCustomerId (string)
//   - appInsightsId (string)
//   - appInsightsConnectionString (string)  ← @secure
//   - appInsightsInstrumentationKey (string)  ← @secure
// =============================================================================

@description('Log Analytics workspace name.')
param workspaceName string

@description('Application Insights component name.')
param appInsightsName string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Log retention in days.')
@minValue(30)
@maxValue(730)
param retentionDays int = 30

// TODO 040 — replace with AVM references for both LAW + AppInsights
// + RBAC: Monitoring Metrics Publisher para uami principalId

// Outputs (placeholder — se reemplazan al impl)
output workspaceId string = ''
output workspaceCustomerId string = ''
output appInsightsId string = ''
@secure()
output appInsightsConnectionString string = ''
