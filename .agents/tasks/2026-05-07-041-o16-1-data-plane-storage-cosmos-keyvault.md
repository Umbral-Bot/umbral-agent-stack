---
id: 2026-05-07-041
title: O16.1 sub-task 041 — data plane (Storage + Cosmos + Key Vault + RBAC)
status: in-progress
created: 2026-05-07
assigned_to: copilot-chat
parent: 2026-05-07-039
depends_on: 2026-05-07-040  # commit 674202fc (UAMI + LAW + AppInsights + CAE)
blocks: [2026-05-07-042, 2026-05-07-043, 2026-05-07-044]
---

# 041 — Data plane (Storage + Cosmos + Key Vault + RBAC)

## Objetivo

Promover a REAL los módulos de la capa de datos:

- **storage.bicep** → Storage Account `Standard_LRS` Hot tier + 3 containers (`crudos`, `datasets-curados`, `eval-results`) + RBAC `Storage Blob Data Contributor` → UAMI.
- **cosmos.bicep** → Cosmos DB NoSQL **Serverless** + DB `umbral-ops` + 4 containers (`agent-memory`, `leads`, `eval-results`, `mailbox-messages`) + SQL data-plane RBAC `Cosmos DB Built-in Data Contributor` → UAMI.
- **key-vault.bicep** → KV `standard` RBAC mode, soft-delete 90d, purge protection on, public access enabled (Q3 Private Endpoint). RBAC `Key Vault Secrets User` → UAMI; `Key Vault Administrator` opcional → David (parametrizado, vacío = no se asigna). **Secret `appinsights-connection-string` cargado desde output de task 040** (cierra el loop secret-output-guard #8).
- **main.bicep** → wire 3 módulos, params nuevos, outputs (storageId, cosmosId, kvId, kvUri).

## Decisiones

- **Direct ARM** (no AVM registry pulls — consistente con 040). Schemas estables.
- **Cosmos vector search**: capability `EnableNVectorIndex` ⚠️ no estándar; uso `EnableServerless` + `EnableNoSQLVectorSearch`. Si la API rechaza, fallback a sólo `EnableServerless` (vector search se habilita por container con `vectorEmbeddingPolicy`).
- **Storage account name**: `stumbralagents${env}` ≤24 lowercase sin guiones.
- **Cosmos containers**: partition key explícita por dominio (`/agentId`, `/companyId`, `/threadId`).
- **KV name**: `kv-umbral-agents-${env}` ≤24, asumimos único en tenant.
- **purgeProtection: true** + soft-delete 90d.
- **NO secrets sembrados en bicep** — solo el AppInsights connection string (output de 040 que ya está en plano del despliegue, no es leak adicional).

## RBAC matrix (esta task)

| Resource | Role | Built-in ID | Principal |
|---|---|---|---|
| Storage Account | Storage Blob Data Contributor | `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | UAMI |
| Cosmos DB account | Cosmos DB Built-in Data Contributor (data plane) | `00000000-0000-0000-0000-000000000002` | UAMI |
| Key Vault | Key Vault Secrets User | `4633458b-17de-457c-b1cd-3cf7ff1ed1e9` | UAMI |
| Key Vault | Key Vault Administrator | `00482a5a-887f-4fb3-b363-3b7fe8e74483` | David (opcional) |

## Acceptance

- `az bicep build main.bicep` clean (warnings 043 esperadas).
- `az deployment sub validate` Succeeded (si hay sesión AZ; opcional offline).
- AppInsights connection string aterriza en KV secret `appinsights-connection-string` (output cerrado, no se outputea desde main.bicep raíz).
- NO deploy real.

## Guardrails

- F-INC-002 estricto pre-push.
- secret-output-guard #8: connection strings nunca outputean en root; van a KV.
- NO touch openclaw / VPS / runtime.
- Direct ARM = mismo patrón que 040.

## Next

- 042 — Service Bus + AI Search Basic + Document Intelligence (RBAC data plane).
- 043 — Budget alerts (consume `alertEmail` + `totalMonthlyBudgetUsd` reservados desde 039).
- 044 — Smoke deploy real (`az deployment sub create`).
