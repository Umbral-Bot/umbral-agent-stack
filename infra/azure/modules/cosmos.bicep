// =============================================================================
// cosmos.bicep — Cosmos DB NoSQL (Serverless)
// =============================================================================
// Sub-task: 2026-05-07-041 (O16.1 data plane)
// Status: REAL (direct ARM resources)
// =============================================================================
// Serverless + Vector Search. DB 'umbral-ops' + 4 containers. SQL data-plane
// RBAC Built-in Data Contributor → UAMI.
// =============================================================================

@description('Cosmos DB account name.')
param name string

@description('Azure region.')
param location string

@description('Tags.')
param tags object = {}

@description('Principal ID for Cosmos DB Built-in Data Contributor.')
param principalIdDataContributor string

@description('Database name.')
param databaseName string = 'umbral-ops'

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-08-15' = {
  name: name
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
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    capabilities: [
      {
        name: 'EnableServerless'
      }
      {
        name: 'EnableNoSQLVectorSearch'
      }
    ]
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    enableAutomaticFailover: false
  }
}

resource db 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-08-15' = {
  parent: cosmos
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

var containerSpecs = [
  { name: 'agent-memory', pk: '/agentId' }
  { name: 'leads', pk: '/companyId' }
  { name: 'eval-results', pk: '/agentId' }
  { name: 'mailbox-messages', pk: '/threadId' }
]

resource containers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = [for c in containerSpecs: {
  parent: db
  name: c.name
  properties: {
    resource: {
      id: c.name
      partitionKey: {
        paths: [c.pk]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
      }
    }
  }
}]

// SQL data-plane RBAC (Cosmos uses its own role system, NOT Microsoft.Authorization)
// Built-in role 'Cosmos DB Built-in Data Contributor': 00000000-0000-0000-0000-000000000002
var cosmosDataContributorRoleId = '00000000-0000-0000-0000-000000000002'

resource cosmosDataContributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-08-15' = {
  parent: cosmos
  name: guid(cosmos.id, principalIdDataContributor, cosmosDataContributorRoleId)
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContributorRoleId}'
    principalId: principalIdDataContributor
    scope: cosmos.id
  }
}

output resourceId string = cosmos.id
output name string = cosmos.name
output endpoint string = cosmos.properties.documentEndpoint
output databaseName string = db.name
