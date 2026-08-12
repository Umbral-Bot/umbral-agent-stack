// infra/azure/document-intelligence.bicep
// Azure AI Document Intelligence (Form Recognizer), kind=FormRecognizer, SKU S0.
// Used by pdf_parser subagent (Área 2 — Conocimiento Técnico AECO).

@description('Azure region.')
param location string

@description('Environment tag (dev|prod).')
param env string

@description('Common tags.')
param tags object

var docintName = 'docint-umbral-o16-${env}-${uniqueString(resourceGroup().id)}'

resource docint 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: substring(docintName, 0, min(64, length(docintName)))
  location: location
  tags: tags
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: substring(docintName, 0, min(64, length(docintName)))
    publicNetworkAccess: 'Enabled' // dev default; prod private endpoint
    disableLocalAuth: true
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

output endpoint string = docint.properties.endpoint
output docintId string = docint.id
