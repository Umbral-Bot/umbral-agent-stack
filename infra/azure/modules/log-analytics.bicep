// =============================================================================
// log-analytics.bicep — Log Analytics Workspace + Application Insights
// =============================================================================
// Sub-task: 2026-05-07-040 (O16.1 cross-cutting infra)
// Status: REAL (direct ARM resources)
// =============================================================================
// Crea:
//   - Log Analytics Workspace (PerGB2018, 30d retention)
//   - Application Insights (workspace-based, kind=web)
//   - RBAC: Monitoring Metrics Publisher → UAMI sobre el AppInsights component
//
// Notas:
//   - workspace-based AppInsights (classic deprecado).
//   - retentionInDays=30 default (Q2 cost-effective).
//   - publicNetworkAccess: Enabled (Q3 evaluar Private Link).
//   - connection string se almacenará en Key Vault como secret en task 041
//     (NO outputear directo desde main.bicep raíz).
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

@description('Daily ingestion cap in GB. -1 = no cap.')
param dailyQuotaGb int = -1

@description('Principal ID of the UAMI granted Monitoring Metrics Publisher.')
param uamiPrincipalId string

// -----------------------------------------------------------------------------
// Log Analytics Workspace
// -----------------------------------------------------------------------------

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionDays
    workspaceCapping: {
      dailyQuotaGb: dailyQuotaGb
    }
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// -----------------------------------------------------------------------------
// Application Insights (workspace-based)
// -----------------------------------------------------------------------------

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    DisableLocalAuth: false
  }
}

// -----------------------------------------------------------------------------
// RBAC: Monitoring Metrics Publisher → UAMI sobre AppInsights
// Built-in role ID: 3913510d-42f4-4e42-8a64-420c390055eb
// -----------------------------------------------------------------------------

var monitoringMetricsPublisherRoleId = '3913510d-42f4-4e42-8a64-420c390055eb'

resource appInsightsMetricsPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: appInsights
  name: guid(appInsights.id, uamiPrincipalId, monitoringMetricsPublisherRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringMetricsPublisherRoleId)
    principalId: uamiPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// -----------------------------------------------------------------------------
// Outputs
// -----------------------------------------------------------------------------

output workspaceId string = workspace.id
output workspaceName string = workspace.name
output workspaceCustomerId string = workspace.properties.customerId

output appInsightsId string = appInsights.id
output appInsightsName string = appInsights.name

@description('App Insights connection string. Pasar a Key Vault (task 041) — NO loguear.')
@secure()
output appInsightsConnectionString string = appInsights.properties.ConnectionString
