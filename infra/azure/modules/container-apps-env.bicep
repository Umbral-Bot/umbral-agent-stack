// =============================================================================
// container-apps-env.bicep — Container Apps Environment (Consumption plan)
// =============================================================================
// Sub-task: 2026-05-07-040 (O16.1 cross-cutting infra)
// Status: REAL (direct ARM resource)
// =============================================================================
// Plan: Consumption (scale-to-0). Sin VNet integration en Q2.
// Workload profile: Consumption (default). Logs → Log Analytics workspace.
//
// Container Apps Jobs concretos (crawler, ingester, eval) NO se crean acá —
// los crea cada repo agente vía CI/CD apuntando a este environment.
// =============================================================================

@description('Container Apps Environment name.')
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Resource name of the Log Analytics workspace (same RG as this module).')
param logAnalyticsWorkspaceName string

@description('Enable zone redundancy. False for Sponsorship (single-region cost-effective).')
param zoneRedundant bool = false

// Reference workspace as existing — sharedKey resuelto sin cruzar boundary.
resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

// NOTA: Managed Environment NO soporta identity ni publicNetworkAccess a nivel
// de environment. La identity (UAMI) se asigna por Container App / Job al deploy
// (responsabilidad de cada repo agente). El environment solo provee el host.
resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
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
    zoneRedundant: zoneRedundant
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

output resourceId string = cae.id
output name string = cae.name
output defaultDomain string = cae.properties.defaultDomain
output staticIp string = cae.properties.staticIp
