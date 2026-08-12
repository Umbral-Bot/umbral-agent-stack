// infra/azure/container-apps.bicep
// Container Apps Environment (consumption only) wired to Log Analytics + App Insights.
// Apps default to minReplicas=0 / maxReplicas=3 — autoscale to 0 (cost = 0 idle).
// No actual app definitions here (those land per-service via separate modules
// or the deploy pipeline). This module only stands up the environment.

@description('Azure region.')
param location string

@description('Environment tag (dev|prod).')
param env string

@description('Common tags.')
param tags object

@description('Log Analytics workspace resource ID (from appinsights module).')
param logAnalyticsWorkspaceId string

@description('Application Insights connection string (from appinsights module).')
@secure()
param appInsightsConnectionString string

var envName = 'cae-umbral-o16-${env}'

// Read the workspace customer ID + shared key from the resource ID.
resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: last(split(logAnalyticsWorkspaceId, '/'))
}

resource cae 'Microsoft.App/managedEnvironments@2024-10-02-preview' = {
  name: envName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
    daprAIConnectionString: appInsightsConnectionString
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}

output environmentId string = cae.id
output environmentName string = cae.name
output defaultDomain string = cae.properties.defaultDomain
