// =============================================================================
// budget-alerts.bicep — Consumption Budgets (per-service + total)
// =============================================================================
// Sub-task: 2026-05-07-043 (O16.1 cost hardening)
// Scope: subscription
// Status: REAL (direct ARM resources)
// =============================================================================
// Opción B conservadora ($7,206/mes total). Per-service dimension=ResourceGroupName
// + ResourceType (donde aplica). Thresholds 50/80/100 (Actual) + 100 (Forecasted)
// → email a alertEmail. Hard stop NO automático (runbook manual).
// =============================================================================

targetScope = 'subscription'

@description('Email recipient for all budget alerts.')
param alertEmail string

@description('Total monthly budget in USD (Opción B = 7206).')
param totalMonthlyBudgetUsd int

@description('Resource group name to scope per-service and total budgets.')
param resourceGroupName string

@description('Budget start date (must be first of a month, yyyy-MM-dd).')
param billingStartDate string = utcNow('yyyy-MM-01')

@description('Budget end date (far future).')
param billingEndDate string = '2030-12-31'

var contactEmails = [
  alertEmail
]

// Per-service budgets. resourceTypes filtered via dimension Where clause.
// Total budget uses only ResourceGroupName.
var perServiceBudgets = [
  {
    name: 'umbral-foundry'
    amount: 3500
    resourceTypes: [
      'microsoft.cognitiveservices/accounts'
    ]
  }
  {
    name: 'umbral-ai-search'
    amount: 300
    resourceTypes: [
      'microsoft.search/searchservices'
    ]
  }
  {
    name: 'umbral-cosmos'
    amount: 200
    resourceTypes: [
      'microsoft.documentdb/databaseaccounts'
    ]
  }
  {
    name: 'umbral-container-apps'
    amount: 700
    resourceTypes: [
      'microsoft.app/managedenvironments'
      'microsoft.app/containerapps'
      'microsoft.app/jobs'
    ]
  }
  {
    name: 'umbral-storage'
    amount: 300
    resourceTypes: [
      'microsoft.storage/storageaccounts'
    ]
  }
  {
    name: 'umbral-document-intelligence'
    amount: 400
    resourceTypes: [
      'microsoft.cognitiveservices/accounts'
    ]
  }
  {
    name: 'umbral-service-bus'
    amount: 200
    resourceTypes: [
      'microsoft.servicebus/namespaces'
    ]
  }
  {
    name: 'umbral-app-insights'
    amount: 300
    resourceTypes: [
      'microsoft.insights/components'
      'microsoft.operationalinsights/workspaces'
    ]
  }
  {
    name: 'umbral-key-vault'
    amount: 50
    resourceTypes: [
      'microsoft.keyvault/vaults'
    ]
  }
]

resource perServiceBudget 'Microsoft.Consumption/budgets@2023-05-01' = [for b in perServiceBudgets: {
  name: b.name
  properties: {
    category: 'Cost'
    amount: b.amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: billingStartDate
      endDate: billingEndDate
    }
    filter: {
      and: [
        {
          dimensions: {
            name: 'ResourceGroupName'
            operator: 'In'
            values: [
              resourceGroupName
            ]
          }
        }
        {
          dimensions: {
            name: 'ResourceType'
            operator: 'In'
            values: b.resourceTypes
          }
        }
      ]
    }
    notifications: {
      Actual_GreaterThan_50_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 50
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }
      Actual_GreaterThan_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }
      Actual_GreaterThan_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }
      Forecasted_GreaterThan_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: contactEmails
      }
    }
  }
}]

resource totalBudget 'Microsoft.Consumption/budgets@2023-05-01' = {
  name: 'umbral-total-monthly'
  properties: {
    category: 'Cost'
    amount: totalMonthlyBudgetUsd
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: billingStartDate
      endDate: billingEndDate
    }
    filter: {
      dimensions: {
        name: 'ResourceGroupName'
        operator: 'In'
        values: [
          resourceGroupName
        ]
      }
    }
    notifications: {
      Actual_GreaterThan_50_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 50
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }
      Actual_GreaterThan_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }
      Actual_GreaterThan_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }
      Forecasted_GreaterThan_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: contactEmails
      }
    }
  }
}

output budgetIds array = [for (b, i) in perServiceBudgets: perServiceBudget[i].id]
output totalBudgetId string = totalBudget.id
