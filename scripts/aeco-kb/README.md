# `scripts/aeco-kb/`

Scripts data-plane para la KB **Conocimiento Técnico AECO** (épica O16.2).

Servicio target: `srch-umbral-kb-prod` (AI Search Basic, RG `rg-umbral-agents-prod`, region `eastus`).

## Scripts

| Script | Sub-task | Propósito |
|---|---|---|
| `create_initial_index.py` | 046 | Crea índice vacío `aeco-kb-es-vYYYYMMDD` + alias estable `aeco-kb-es-current`. Idempotente. |
| `pdf_parser.py` | 047 | Parsea 1 PDF de `crudos/aeco/raw/...` con DI prebuilt-layout + chunkea + escribe JSONL a `crudos/aeco/parsed/...`. Idempotente vía `parser_version`. |
| `source_crawler.py` | 048 | Descarga PDFs desde `seeds/{source_type}.yaml` con rate-limit 1 req/s + dedupe SHA-256, manifest JSONL append-only en `crudos/aeco/raw/_manifest/{source}.jsonl`. |
| `version_detector.py` | 049 | Lee `aeco/parsed/{source}/*.chunks.jsonl` + manifest del index activo, emite diff JSON `{added, changed, removed, unchanged}`. |
| `index_publisher.py` | 049 | Clona schema del index activo → `aeco-kb-es-vYYYYMMDD` → embebe (Foundry text-embedding-3-small) → upload → valida (count + sample query) → alias swap atómico. |
| `run_pipeline.sh` | 050 | Bash orquestador secuencial Q2: arranca crawler → parser → publisher por cada source vía `az containerapp job start` y espera con polling. |
| `verify_kb.py` | 050 | Gate post-pipeline: doc_count >= min, cobertura >=1 chunk por jurisdicción, sample queries devuelven hits. |
| `foundry_connection.py` | 051 | Crea/actualiza connection `aeco-kb-search` en Foundry project `umbralbim` (cross-RG, AAD auth). Idempotente. |
| `smoke_agenteub_kb.py` | 051 | Smoke automatizado: invoca AgenteUB Responses API, valida `aeco-kb-es-vYYYYMMDD` + URL fuente en respuesta. |

## Auth

`DefaultAzureCredential`:

- **Local**: `az login` (usuario con role `Search Service Contributor` sobre `srch-umbral-kb-prod`).
- **Container Apps Job (futuro)**: UAMI `uami-umbral-agents-prod` ya tiene los roles asignados en O16.1.

## Variables de entorno

| Variable | Default | Notas |
|---|---|---|
| `AZURE_SEARCH_ENDPOINT` | _(auto desde service name)_ | Ej. `https://srch-umbral-kb-prod.search.windows.net`. |
| `AZURE_SEARCH_SERVICE_NAME` | `srch-umbral-kb-prod` | Solo se usa si no hay `AZURE_SEARCH_ENDPOINT`. |

## Uso típico (sub-task 046)

```powershell
# Desde Windows local con az login activo
az login --tenant f67a8c0b-ec74-47cd-836c-355c5a6162d4
az account set --subscription f14f61f0-e692-4fbb-900d-73e55a632374

# Dry-run (no toca Azure)
python scripts/aeco-kb/create_initial_index.py --dry-run

# Deploy real
python scripts/aeco-kb/create_initial_index.py

# Validar
az search index show `
    --service-name srch-umbral-kb-prod `
    --resource-group rg-umbral-agents-prod `
    --index-name aeco-kb-es-v20260507

az search alias show `
    --service-name srch-umbral-kb-prod `
    --resource-group rg-umbral-agents-prod `
    --alias-name aeco-kb-es-current
```

## Idempotencia y migración de schema

`create_or_update_index` es idempotente para cambios compatibles (agregar campo nuevo no-key, agregar synonym map, etc.). Para cambios incompatibles (cambiar tipo, eliminar campo, cambiar dimensiones del vector):

1. Crear nueva versión: `--index-version v<nueva>`.
2. Backfill de contenido en la nueva versión (vía sub-tasks 047/048/050).
3. Alias swap atómico (sub-task 049 — `index-publisher`).

El alias garantiza zero-downtime: el `AgenteUB` File Search siempre apunta a `aeco-kb-es-current`.

## Sub-task 047 — `pdf_parser.py`

Parser DI prebuilt-layout. Lee 1 PDF, chunkea párrafo-aware (target 50-800 tokens estimados), serializa tablas a markdown, escribe JSONL a `crudos/aeco/parsed/{source_type}/{doc_id}.chunks.jsonl`.

### Smoke local

```powershell
pip install -e .[aeco-kb]
az login --tenant f67a8c0b-ec74-47cd-836c-355c5a6162d4

# Local: invocar por path (la carpeta tiene guión, no es módulo Python)
python scripts/aeco-kb/pdf_parser.py `
    --blob-path aeco/raw/buildingsmart/sample.pdf `
    --source-type buildingsmart --jurisdiction intl `
    --doc-type spec --version IFC4.3.2.0 --lang es --dry-run
```

> En el container, el Dockerfile renombra la carpeta a `scripts/aeco_kb/` (underscore) para permitir `python -m scripts.aeco_kb.pdf_parser` como entrypoint.

### Container Apps Job (manual trigger)

Definido en `infra/azure/modules/aeco-pdf-parser-job.bicep`. Image: `ghcr.io/umbral-bot/aeco-pdf-parser:latest`. Build vía Dockerfile en `infra/docker/aeco-pdf-parser/Dockerfile`.

```bash
az containerapp job start --name aeco-pdf-parser --resource-group rg-umbral-agents-prod \
    --env-vars "INPUT_BLOB_PATH=aeco/raw/buildingsmart/IFC4.3.2.0.pdf" \
               "SOURCE_TYPE=buildingsmart" "JURISDICTION=intl" \
               "DOC_TYPE=spec" "VERSION=IFC4.3.2.0" "LANG=es"
```

Trigger automático Event Grid → SB → KEDA: cableado en sub-task 050. Q2 invoca manualmente.

### Idempotencia

`PARSER_VERSION = "v1.0.0"` constante en el script. Si el output existe con el mismo version, skip. Bump manual cuando cambie chunking o se actualice DI model.

## Schema (lockeado en task 045 §D3 + 046)

14 campos. Vector profile `hnsw-cosine` (HNSW + cosine, 1536 dims). Semantic config `default-semantic-cfg`.

Ver detalle en [`.agents/tasks/2026-05-07-046-o16-2-ai-search-index-schema-alias.md`](../../.agents/tasks/2026-05-07-046-o16-2-ai-search-index-schema-alias.md).

## Sub-task 048 — `source_crawler.py`

Crawler parametrizado por `--source-type`. Lee seeds estáticos en `scripts/aeco-kb/seeds/{source_type}.yaml`, aplica rate-limit 1 req/s + User-Agent identificable, respeta `robots.txt` best-effort, dedupe SHA-256 contra metadata del blob existente, escribe a `crudos/aeco/raw/{source_type}/{doc_id}.pdf` y appendea manifest JSONL en `crudos/aeco/raw/_manifest/{source_type}.jsonl`.

### Smoke local

```powershell
pip install -e .[aeco-kb]
az login --tenant f67a8c0b-ec74-47cd-836c-355c5a6162d4

# Dry-run (sin tocar Azure)
python scripts/aeco-kb/source_crawler.py --source-type buildingsmart --max-docs 3 --dry-run

# Real
python scripts/aeco-kb/source_crawler.py --source-type buildingsmart --max-docs 3
```

### Container Apps Job (manual trigger)

Definido en `infra/azure/modules/aeco-source-crawler-job.bicep`. Image: `ghcr.io/umbral-bot/aeco-source-crawler:latest`.

```bash
az containerapp job start --name aeco-source-crawler --resource-group rg-umbral-agents-prod \
    --env-vars "SOURCE_TYPE=buildingsmart" "MAX_DOCS=30"
```

### Seeds

Q2 carga `buildingsmart` (3 PDFs IFC) + `minvu` (placeholders, validar URLs antes del primer run). `iram` y `nmx` quedan vacíos; se pueblan en sub-task 050.

### Cron

Q2: invocación manual. Cron diario 03:00 UTC se cablea en **050** (cambio `triggerType: 'Schedule'` + `scheduleTriggerConfig`).

## Sub-task 049 — version-detector + index-publisher

### version_detector.py

Lee parsed chunks bajo `crudos/aeco/parsed/{source}/` y los compara con el manifest del index activo (alias target) en `crudos/aeco/index/{index}/manifest.jsonl`. Emite diff JSON.

```powershell
az login --tenant f67a8c0b-ec74-47cd-836c-355c5a6162d4
python scripts/aeco-kb/version_detector.py --source-type buildingsmart
```

### index_publisher.py

Pipeline completo: clona schema, embebe, sube docs, valida (gate), swap atómico del alias. Escribe nuevo manifest del index publicado.

```powershell
python scripts/aeco-kb/index_publisher.py --source-types buildingsmart minvu --dry-run
python scripts/aeco-kb/index_publisher.py --source-types buildingsmart minvu
```

Gate de validación pre-swap:

- `documentCount >= expected * 0.95`.
- Sample query `IFC OR norma OR construcción` devuelve >= 3 results.
- Failure rate uploads <= 5%.

### Container Apps Job (manual trigger)

Definido en `infra/azure/modules/aeco-index-pipeline-job.bicep`. Image: `ghcr.io/umbral-bot/aeco-index-pipeline:latest`. Subcomandos vía args:

```bash
az containerapp job start --name aeco-index-pipeline --resource-group rg-umbral-agents-prod --args 'detect --source-type buildingsmart'
az containerapp job start --name aeco-index-pipeline --resource-group rg-umbral-agents-prod --args 'publish --source-types buildingsmart minvu'
```

### Rollback

Manual repointing del alias al index previo:

```bash
az search alias create-or-update --service-name srch-umbral-kb-prod --resource-group rg-umbral-agents-prod --name aeco-kb-es-current --indexes aeco-kb-es-v20260501
```


## Sub-task 050 — pipeline e2e + IRAM/NMX seeds

Orquestación Q2 secuencial vía bash. Q3 upgrade -> Service Bus chained.

```bash
# Trigger pipeline e2e (require az login + UAMI roles + imágenes built/pushed)
bash scripts/aeco-kb/run_pipeline.sh buildingsmart minvu iram nmx

# Validar gate >=500 chunks + cobertura por jurisdicción
python scripts/aeco-kb/verify_kb.py --min-chunks 500 --jurisdictions ar,cl,mx,intl
```

### Bicep umbrella

Despliega los 3 jobs en una sola operación (referencia los módulos existentes):

```bash
az deployment group create -g rg-umbral-agents-prod \`n  -f infra/azure/aeco-kb-pipeline.bicep \`n  -p location=eastus2 \`n  -p environmentId=$CAE_ID \`n  -p userAssignedIdentityId=$UAMI_ID \`n  -p userAssignedIdentityClientId=$UAMI_CLIENT_ID \`n  -p storageAccountName=stumbralagentsprod \`n  -p searchServiceName=srch-umbral-kb-prod \`n  -p diEndpoint=https://di-umbral-prod.cognitiveservices.azure.com/
```

### Seeds populated

- `seeds/buildingsmart.yaml` (3 PDFs IFC 4.3.x — international).
- `seeds/minvu.yaml` (2 placeholders DDU — validar HEAD).
- `seeds/iram.yaml` (2 PDFs SISCO + IRAM ISO 19650-1).
- `seeds/nmx.yaml` (2 PDFs SHCP Estrategia BIM + NMX-R-098).

