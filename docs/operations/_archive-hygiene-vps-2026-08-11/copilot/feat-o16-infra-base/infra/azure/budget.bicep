// infra/azure/budget.bicep
// Action Group + monthly subscription budget (alerts at 80%/100%/120%).
// Deployed at resource group scope so that the action group has a valid host.
// The budget itself is created at subscription scope from main via this module's
// outputs (since Microsoft.Consumption/budgets is subscription-scoped).

@description('Environment tag.')
param env string

@description('Email recipient for budget alerts.')
param alertEmail string

@description('Common tags.')
param tags object

resource ag 'Microsoft.Insights/actionGroups@2024-10-01-preview' = {
  name: 'ag-umbral-o16-${env}'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'umbralO16'
    enabled: true
    emailReceivers: [
      {
        name: 'contacto'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

output actionGroupId string = ag.id
