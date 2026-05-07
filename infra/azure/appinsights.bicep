// infra/azure/appinsights.bicep
// Workspace-based Application Insights + Log Analytics workspace.
// Sampling 25%, retention 30d.

@description('Azure region.')
param location string

@description('Environment tag (dev|prod).')
param env string

@description('Common tags.')
param tags object

var workspaceName = 'log-umbral-o16-${env}'
var appInsightsName = 'appi-umbral-o16-${env}'

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    SamplingPercentage: 25
    RetentionInDays: 30
    IngestionMode: 'LogAnalytics'
    DisableLocalAuth: true
  }
}

output logAnalyticsWorkspaceId string = workspace.id
output appInsightsId string = appInsights.id
output appInsightsConnectionString string = appInsights.properties.ConnectionString
