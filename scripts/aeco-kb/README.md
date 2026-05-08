# `scripts/aeco-kb/`

Scripts data-plane para la KB **Conocimiento Técnico AECO** (épica O16.2).

Servicio target: `srch-umbral-kb-prod` (AI Search Basic, RG `rg-umbral-agents-prod`, region `eastus`).

## Scripts

| Script | Sub-task | Propósito |
|---|---|---|
| `create_initial_index.py` | 046 | Crea índice vacío `aeco-kb-es-vYYYYMMDD` + alias estable `aeco-kb-es-current`. Idempotente. |
| `pdf_parser.py` | 047 | Parsea 1 PDF de `crudos/aeco/raw/...` con DI prebuilt-layout + chunkea + escribe JSONL a `crudos/aeco/parsed/...`. Idempotente vía `parser_version`. |

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
