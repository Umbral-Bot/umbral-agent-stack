// infra/azure/cosmos.bicep
// Cosmos DB NoSQL serverless. Database: umbral-internal.
// Containers: agents-state, eval-results, lead-profiles.

@description('Azure region.')
param location string

@description('Environment tag (dev|prod).')
param env string

@description('Common tags.')
param tags object

var accountName = 'cosmos-umbral-o16-${env}-${uniqueString(resourceGroup().id)}'
var dbName = 'umbral-internal'

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' = {
  name: substring(accountName, 0, min(44, length(accountName)))
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      { name: 'EnableServerless' }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    disableLocalAuth: true // managed identity / RBAC only
    publicNetworkAccess: 'Enabled' // dev default; prod should use private endpoint
    minimalTlsVersion: 'Tls12'
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 1440
        backupRetentionIntervalInHours: 168
        backupStorageRedundancy: 'Local'
      }
    }
  }
}

resource db 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-12-01-preview' = {
  parent: cosmos
  name: dbName
  properties: {
    resource: {
      id: dbName
    }
  }
}

var containers = [
  {
    name: 'agents-state'
    pk: '/agentId'
  }
  {
    name: 'eval-results'
    pk: '/runId'
  }
  {
    name: 'lead-profiles'
    pk: '/leadId'
  }
]

resource cosmosContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = [for c in containers: {
  parent: db
  name: c.name
  properties: {
    resource: {
      id: c.name
      partitionKey: {
        paths: [ c.pk ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
      }
    }
  }
}]

output endpoint string = cosmos.properties.documentEndpoint
output accountId string = cosmos.id
output databaseName string = dbName
