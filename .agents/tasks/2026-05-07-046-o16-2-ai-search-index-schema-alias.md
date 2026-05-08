---
id: 2026-05-07-046
title: O16.2 sub-task 046 — AI Search index schema + alias atomic
status: open
priority: P1 (deadline duro Sponsorship 2026-06-30)
assigned_to: copilot-chat
created_at: 2026-05-07
created_by: copilot-chat (descomposición desde 045)
parent: 2026-05-07-045 (O16.2 kickoff)
relates_to: infra/azure/modules/ai-search.bicep, scripts/aeco-kb/, docs/runbooks/aeco-kb-refresh.md (futuro)
depends_on: 045 (decisiones D1-D6 lockeadas), O16.1 ✅ (srch-umbral-kb-prod live + UAMI con Search Service Contributor + Search Index Data Contributor)
blocks: 047 (pdf-parser necesita el índice creado para test escritura), 048 (crawler ídem), 049 (alias swap requiere alias existente), 051 (Foundry File Search apunta al alias)
---

# 046 — AI Search index schema + alias atomic

## Objetivo

Crear el **índice vacío inicial** `aeco-kb-es-v20260507` con el schema completo lockeado en 045 §D3, más el **alias estable** `aeco-kb-es-current` apuntando a él. Sin contenido todavía. Esto desbloquea 047/048 (escritura de docs) y 051 (Foundry File Search wiring contra el alias).

## Por qué Python (no Bicep)

Microsoft.Search/searchServices es ARM (control plane), pero **indexes y aliases son data plane** — no exponen tipos `Microsoft.Search/searchServices/indexes` ni `/aliases` en ARM. Solo se crean vía REST (`/indexes?api-version=…`) o SDK (`SearchIndexClient`). Por eso este task entrega un **script Python idempotente** y no un módulo Bicep.

Bicep ya cubrió el servicio (`modules/ai-search.bicep` en O16.1).

## Schema lockeado (045 §D3)

| Campo | Tipo | Atributos | Notas |
|---|---|---|---|
| `id` | String | key=true, retrievable | UUID o `{parent_doc_id}_{chunk_id}` |
| `content` | String | searchable, retrievable, analyzer=`es.microsoft` | Texto del chunk |
| `content_vector` | Collection(Single) | searchable, retrievable, dimensions=1536, vectorSearchProfile=`hnsw-cosine` | text-embedding-3-small |
| `source_url` | String | retrievable, filterable | URL canónica del doc original |
| `source_type` | String | filterable, facetable, retrievable | `buildingsmart` \| `minvu` \| `iram` \| `nmx` |
| `jurisdiction` | String | filterable, facetable, retrievable | `intl` \| `cl` \| `ar` \| `mx` |
| `doc_type` | String | filterable, facetable, retrievable | `spec` \| `regulation` \| `guide` |
| `version` | String | filterable, retrievable | Versión del documento fuente (ej. `IFC4.3.2.0`) |
| `lang` | String | filterable, retrievable | `es` Q2 (D6) |
| `valid_from` | DateTimeOffset | filterable, sortable, retrievable | Fecha publicación doc |
| `valid_to` | DateTimeOffset | filterable, sortable, retrievable | Null si vigente |
| `chunk_id` | Int32 | filterable, sortable, retrievable | Posición del chunk |
| `parent_doc_id` | String | filterable, retrievable | Identificador del doc padre |
| `kb_version` | String | retrievable | `vYYYYMMDD` del índice — el bot lo cita |

**Vector profile**: `hnsw-cosine` (algorithm=HNSW default params m=4, efConstruction=400, efSearch=500; metric=cosine).

**Semantic configuration**: `default-semantic-cfg` con `prioritizedContentFields=[content]`, `prioritizedKeywordsFields=[source_type, jurisdiction, doc_type]`. Title field = none (los docs no tienen título de chunk; podríamos usar `parent_doc_id`).

**CORS**: ninguno (el bot consume vía Foundry File Search, no directo).

## Alias

- Nombre: `aeco-kb-es-current`
- Apunta inicialmente a `aeco-kb-es-v20260507`
- Swap futuro (sub-task 049) = `SearchIndexClient.create_or_update_alias(SearchAlias(name='aeco-kb-es-current', indexes=['aeco-kb-es-v<nueva>']))` — operación atómica server-side.

## Entregables

1. `scripts/aeco-kb/__init__.py` (vacío)
2. `scripts/aeco-kb/create_initial_index.py` — script idempotente:
   - Lee `AZURE_SEARCH_ENDPOINT` o construye desde `AZURE_SEARCH_SERVICE_NAME` (default `srch-umbral-kb-prod`).
   - Auth = `DefaultAzureCredential` (local: `az login`; runtime: UAMI ya con `Search Service Contributor`).
   - Define schema completo con `azure.search.documents.indexes.models`.
   - `create_or_update_index(index)` → idempotente. Si ya existe con mismo schema, no-op.
   - `create_or_update_alias(alias)` → idempotente.
   - Print final: índice + alias creados, link al portal Azure.
   - `--dry-run` flag que solo imprime el JSON del schema.
   - `--index-version v20260507` parametrizable (default = hoy).
3. `scripts/aeco-kb/README.md` — cómo correrlo (env vars, az login, validación post-deploy con `az search index show` y `az search alias show`).

## Validación post-deploy (DoD)

```bash
# Desde Azure CLI con permisos sobre srch-umbral-kb-prod
az search index show --service-name srch-umbral-kb-prod --resource-group rg-umbral-agents-prod --index-name aeco-kb-es-v20260507 --query "{name:name, fields:length(fields), vector:vectorSearch.profiles[0].name, semantic:semantic.configurations[0].name}"

# Esperado:
# {
#   "name": "aeco-kb-es-v20260507",
#   "fields": 14,
#   "vector": "hnsw-cosine",
#   "semantic": "default-semantic-cfg"
# }

az search alias show --service-name srch-umbral-kb-prod --resource-group rg-umbral-agents-prod --alias-name aeco-kb-es-current --query "{name:name, indexes:indexes}"

# Esperado:
# {
#   "name": "aeco-kb-es-current",
#   "indexes": ["aeco-kb-es-v20260507"]
# }
```

Audit-log + run capturado en `docs/audits/2026-05-07-o16-2-046-index-deploy.md` (post-ejecución).

## Decisiones diferidas (no bloquean 046)

- **Foundry connection cross-RG (D2)**: se valida en 051. 046 solo crea el index/alias; el wiring viene después.
- **Idempotencia con schema migration**: si en el futuro cambiamos el schema (ej. agregar campo `embedding_model`), `create_or_update_index` falla con `IndexUpdateNotAllowed` — la estrategia es crear nueva versión `aeco-kb-es-v<nueva>` + alias swap (049). Esto está OK porque alinea con la política de versionado lockeada.
- **Embedding model**: 1536 dims = text-embedding-3-small, lockeado por 045 (D5 cost). Si Q3 movemos a `-large` (3072 dims), nueva versión de índice + alias swap.

## Próximo

→ **047**: `pdf-parser` Container Apps Job (DI prebuilt-layout, blob-triggered desde `kb-aeco-crudos`).

## Notas runtime

- Script corre desde **local** (con `az login` del autorizado) o desde **Container Apps Job** (con UAMI). 046 no requiere el job todavía — basta con `python scripts/aeco-kb/create_initial_index.py` desde Windows con `az login` activo.
- No requiere VPS deploy (no hay servicio runtime que reiniciar).
- No requiere secret rotation.
- Idempotente: re-correr no rompe el alias ni el índice (siempre que schema no haya cambiado).
