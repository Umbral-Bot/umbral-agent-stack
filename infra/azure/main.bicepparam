using 'main.bicep'

// =============================================================================
// main.bicepparam — params para deploy (1 environment por archivo si necesitás)
// =============================================================================
// Subscription ID NO se commitea — se setea al deploy via:
//   az deployment sub create --location eastus2 \
//     --template-file main.bicep \
//     --parameters main.bicepparam
// =============================================================================

param environment = 'prod'
param location = 'eastus2'
param alertEmail = 'alertas@umbralbim.cl'
param totalMonthlyBudgetUsd = 7206
// David Moreira (dm@umbralbim.cl) — KV Admin para leer secretos en data-plane.
// Obtenido vía `az ad signed-in-user show --query id -o tsv` en smoke 044.
param kvAdminObjectId = 'daf2e5a6-25df-433b-bc05-32a7478ecd95'
param tags = {
  owner: 'david-moreira'
  project: 'umbral-agents'
  costCenter: 'sponsorship-2026'
  environment: 'prod'
  managedBy: 'bicep'
}
