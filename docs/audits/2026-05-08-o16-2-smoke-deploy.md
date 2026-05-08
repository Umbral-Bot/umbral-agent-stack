# O16.2 — Smoke Deploy Audit (2026-05-08)

**Owner:** Copilot Chat (autonomous mandate, dm@umbralbim.cl session)
**Tracking task:** `2026-05-08-051-o16-2-agenteub-filesearch-wiring.md`
**Status:** ⚠️ PARCIAL — RBAC + Foundry connection LIVE OK; build-images / pipeline-run / agent-smoke pendientes (requieren Docker + portal File Search wiring).

## Contexto

Cierre repo de O16.2 quedó en commit `0659b06b` (umbral-agent-stack/main).
Esta sesión ejecuta los pasos live deterministas que `az` CLI permite sin Docker
ni acceso al portal Foundry para File Search.

## Subscription / Tenant

- Sub: `f14f61f0-e692-4fbb-900d-73e55a632374` (Azure subscription 1)
- Tenant: `f67a8c0b-ec74-47cd-836c-355c5a6162d4`
- User: `dm@umbralbim.cl`

## Acciones ejecutadas

### 1. UAMI cross-RG roles ✅

UAMI: `uami-umbral-agents-prod` (rg-umbral-agents-prod)
principalId: `ebe48a91-588c-4331-b3ee-0d58906e48cd`

| Role | Scope | Resultado |
|---|---|---|
| Search Index Data Reader | `srch-umbral-kb-prod` (mismo RG, redundante con Contributor pero explícito) | ✅ Created |
| Cognitive Services OpenAI User | `umbralbim-resource` (rg-dm-8454) | ✅ Created |

### 2. Foundry connection `aeco-kb-search` ✅

Hallazgo: el Foundry productivo NO usa el patrón legacy
`Microsoft.MachineLearningServices/workspaces`, usa el patrón nuevo
`Microsoft.CognitiveServices/accounts/{account}/projects/{project}`.

- Account: `umbralbim-resource` (rg-dm-8454)
- Project: `umbralbim`
- Connection name: `aeco-kb-search`
- Target: `https://srch-umbral-kb-prod.search.windows.net`
- AuthType: `AAD` (usa system-MI del project)
- API: `2025-04-01-preview`

PUT realizado vía `az rest`. Respuesta 200 con `isDefault: true`.

### 3. Foundry project system-MI roles ✅

Project system-MI principalId: `3c449e41-294d-4429-80f6-ec32305a77ba`

| Role | Scope | Resultado |
|---|---|---|
| Search Index Data Reader | `srch-umbral-kb-prod` | ✅ Created |
| Search Service Contributor | `srch-umbral-kb-prod` | ✅ Created |

Esto habilita al `AgenteUB` (cuando File Search se cablee) a leer del index
`aeco-kb-es-current` con AAD.

### 4. Patch repo `foundry_connection.py` ✅

Script original asumía API legacy (MLS workspaces). Actualizado a:
- API version `2025-04-01-preview`
- Path `Microsoft.CognitiveServices/accounts/{account}/projects/{project}/connections`
- Defaults pre-poblados (foundry-sub, foundry-rg, foundry-account, foundry-project)
- F-INC-002 Python AST OK.

## Pendiente para cierre formal de O16.2

| Paso | Bloqueante | Owner |
|---|---|---|
| Build + push 3 imágenes ACA Jobs a GHCR (`aeco-source-crawler`, `aeco-pdf-parser`, `aeco-index-publisher`) | Docker local + GHCR PAT | David / CI |
| `az deployment group create` del Bicep umbrella `aeco-kb-pipeline.bicep` | Imágenes en GHCR | Auto post-build |
| `bash scripts/aeco-kb/run_pipeline.sh buildingsmart minvu iram nmx` | Jobs deployados | Auto |
| `python scripts/aeco-kb/verify_kb.py --min-chunks 500` | Pipeline corrió | Auto |
| Portal Foundry: configurar File Search del `AgenteUB` con index `aeco-kb-es-current` (mapping per `runbooks/o16-2-agenteub-filesearch-wiring.md`) | Manual portal | David |
| `python scripts/aeco-kb/smoke_agenteub_kb.py` (asserts `aeco-kb-es-vYYYYMMDD` + URL en respuesta) | File Search wired | Auto |
| Update este audit con resultados smoke | smoke OK | Copilot Chat |

## Acceptance criterion (Friday retro 2026-06-26)

> Bot Umbral en producción cita un párrafo buildingSMART/IFC con `aeco-kb-es-vYYYYMMDD` y URL fuente visible.

Status hoy: **infraestructura RBAC + connection LIVE listas**, falta pipeline run + portal wiring.

## Hashes / commits referencia

- Repo cerrado: `0659b06b` (umbral-agent-stack/main, 2026-05-08)
- Plan Q2 actualizado: notion-governance/main `79e2532` (2026-05-08)
- Patch script Foundry connection: pendiente commit en este audit run.
