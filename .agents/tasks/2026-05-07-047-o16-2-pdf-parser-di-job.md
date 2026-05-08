---
id: 2026-05-07-047
title: O16.2 sub-task 047 — pdf-parser (Document Intelligence prebuilt-layout) + Container Apps Job
status: open
priority: P1 (deadline duro Sponsorship 2026-06-30)
assigned_to: copilot-chat
created_at: 2026-05-07
created_by: copilot-chat (descomposición desde 045)
parent: 2026-05-07-045 (O16.2 kickoff)
relates_to: scripts/aeco-kb/, infra/docker/aeco-pdf-parser/, infra/azure/modules/aeco-pdf-parser-job.bicep
depends_on: 046 (índice + alias deben existir para que el ingester downstream tenga target), O16.1 ✅ (DI `di-umbral-prod` eastus2 + Storage `stumbralagentsprod` + UAMI `uami-umbral-agents-prod` con `Cognitive Services User` y `Storage Blob Data Contributor` y `Key Vault Secrets User`)
blocks: 048 (crawler escribe PDFs en `crudos/aeco/raw/` → parser los procesa), 049 (publisher consume chunks parseados), 050 (e2e), 051 (smoke)
---

# 047 — pdf-parser (DI prebuilt-layout) + Container Apps Job

## Objetivo

Función reutilizable + ejecutable containerizado que toma un PDF en blob storage, lo manda a **Document Intelligence prebuilt-layout** (`di-umbral-prod` en eastus2), parsea la respuesta a chunks normalizados (texto + metadata canónica del schema 046) y los persiste como JSON en blob storage para consumo del `index-publisher` (049).

**No incluye**: trigger automático Event Grid → Service Bus → KEDA. Eso se cablea en **050 (e2e)**. Q2 valida el parser via invocación manual del Job (`az containerapp job start`).

## Criterio de éxito (DoD)

```bash
# Subir PDF de prueba a crudos/aeco/raw/
az storage blob upload --account-name stumbralagentsprod --container-name crudos \
    --name aeco/raw/buildingsmart/IFC4.3.2.0-sample.pdf --file ./samples/IFC4.3.2.0-sample.pdf --auth-mode login

# Ejecutar Job pasando el blob path como override env
az containerapp job start --name aeco-pdf-parser --resource-group rg-umbral-agents-prod \
    --env-vars "INPUT_BLOB_PATH=aeco/raw/buildingsmart/IFC4.3.2.0-sample.pdf" \
               "SOURCE_TYPE=buildingsmart" "JURISDICTION=intl" "DOC_TYPE=spec" "VERSION=IFC4.3.2.0"

# Verificar output:
az storage blob list --account-name stumbralagentsprod --container-name crudos \
    --prefix aeco/parsed/buildingsmart/ --auth-mode login --query "[].name" -o tsv
# Esperado: aeco/parsed/buildingsmart/IFC4.3.2.0-sample.chunks.jsonl con N chunks ≥1

# Inspect 1 chunk:
az storage blob download ... --query content -o tsv | head -1 | jq .
# Esperado: {"id":"...","content":"...","source_type":"buildingsmart","jurisdiction":"intl",
#            "doc_type":"spec","version":"IFC4.3.2.0","lang":"es",
#            "chunk_id":0,"parent_doc_id":"...","source_url":null,
#            "valid_from":null,"valid_to":null,
#            "kb_version":null}  // kb_version se setea en 049 al publicar
```

`content_vector` **no se rellena acá** — lo hace 049 (`index-publisher`) al embebearlo. 047 deja el campo ausente.

## Decisiones lockeadas en 047

### D7. Modelo DI: `prebuilt-layout` (NO `prebuilt-document` ni `prebuilt-read`)

- `prebuilt-read`: solo OCR plano. Pierde estructura de tablas/secciones.
- `prebuilt-document`: extrae key-value pairs (formularios). Overkill para spec/regulación.
- ✅ `prebuilt-layout`: paragraphs + tables + sections + reading order. Ideal para specs IFC, normas MINVU/IRAM/NMX. Soporta PDFs escaneados (built-in OCR) y PDFs nativos.

Costo S0: $1.50/1k pages (`prebuilt-layout`). Cap operativo lockeado en 045 §D5: 200k pages ≈ $300.

### D8. Chunking: párrafo-aware con cap de tokens

Estrategia conservadora Q2:
- Unidad base = párrafo (`paragraph` element del DI response).
- Si párrafo tiene >800 tokens (rough estimate `len(text.split()) * 1.3`), split por sentencia (regex `[.!?]\s+`).
- Si párrafo tiene <50 tokens, mergear con siguiente hasta llegar a 200-500 tokens.
- Tablas: serializar a markdown (1 chunk por tabla).
- Headings: prepend al chunk siguiente como contexto (formato `## {heading}\n\n{paragraph}`).

Tokens estimados via heuristic (no requiere `tiktoken`). Q3 evaluar `tiktoken` si calidad de retrieval es baja.

### D9. Storage layout

```
stumbralagentsprod/crudos/
├── aeco/
│   ├── raw/
│   │   ├── buildingsmart/{doc_id}.pdf       ← input crawler (048)
│   │   ├── minvu/{doc_id}.pdf
│   │   ├── iram/{doc_id}.pdf
│   │   └── nmx/{doc_id}.pdf
│   └── parsed/
│       ├── buildingsmart/{doc_id}.chunks.jsonl   ← output parser (047)
│       ├── minvu/{doc_id}.chunks.jsonl
│       ├── iram/{doc_id}.chunks.jsonl
│       └── nmx/{doc_id}.chunks.jsonl
```

JSONL = 1 chunk por línea. `parent_doc_id` = filename sin extensión.

### D10. Container image: build local + push a ACR (futuro) o GHCR

Q2 simple: build vía GitHub Actions → push a **GHCR** (`ghcr.io/umbral-bot/aeco-pdf-parser:latest`). Container Apps Job lee imagen pública desde GHCR (no requiere ACR + auth en Q2).

Q3 si hay sensibilidad de IP: migrar a ACR privado en `rg-umbral-agents-prod` con UAMI auth.

### D11. Idempotencia del parser

- Si `aeco/parsed/{source_type}/{parent_doc_id}.chunks.jsonl` ya existe **y** contiene metadata `parser_version` igual al actual: skip (no re-parse).
- Si difiere o flag `--force` está set: re-parse + sobrescribir.
- `parser_version` = constante `PARSER_VERSION = "v1.0.0"` en `pdf_parser.py` (bump manual cuando cambie chunking o DI model).

## Entregables

1. `scripts/aeco-kb/pdf_parser.py` — módulo + CLI.
2. `infra/docker/aeco-pdf-parser/Dockerfile` — Python 3.12-slim + deps mínimas.
3. `infra/docker/aeco-pdf-parser/entrypoint.sh` — invoca `python -m scripts.aeco_kb.pdf_parser`.
4. `infra/azure/modules/aeco-pdf-parser-job.bicep` — Container Apps Job ARM (manualTrigger profile, UAMI, env vars secretRef desde KV si aplica).
5. `pyproject.toml` — agregar opt-dep `aeco-kb` con `azure-ai-documentintelligence` + `azure-storage-blob`.
6. `scripts/aeco-kb/README.md` — actualizar con sección "pdf-parser".

## Smoke local (sin Container Apps Job)

```powershell
pip install -e .[aeco-kb]
az login --tenant f67a8c0b-ec74-47cd-836c-355c5a6162d4
$env:DI_ENDPOINT="https://di-umbral-prod.cognitiveservices.azure.com/"
$env:STORAGE_ACCOUNT="stumbralagentsprod"

python -m scripts.aeco_kb.pdf_parser --blob-path aeco/raw/buildingsmart/sample.pdf `
    --source-type buildingsmart --jurisdiction intl --doc-type spec --version IFC4.3.2.0 --lang es
```

> Nota: localmente la carpeta es `scripts/aeco-kb/` (con guión) — invocar con path: `python scripts/aeco-kb/pdf_parser.py ...`. El Dockerfile la renombra a `scripts/aeco_kb/` (underscore) para soportar `python -m`.

## Decisiones diferidas (no bloquean 047)

- **Trigger Event Grid → SB → KEDA**: cableado en 050. 047 deja el Job creado con `triggerType=Manual`.
- **Embeddings**: en 049. 047 emite chunks **sin** `content_vector`.
- **Idempotencia con DI versionado**: si MS upgrades `prebuilt-layout` GA a una versión que cambia output schema, bump `PARSER_VERSION` y full re-parse de la KB (manejado en 049 via alias swap).

## Notas runtime

- No requiere VPS deploy (Container Apps Job es Azure-native).
- Requiere image pull desde GHCR (público inicialmente; si volvemos a privado, GHA secret para login).
- Sponsorship cost impact: build+push GHA → 0 (free tier). Job ejecución → DI call (paid) + 1 vCPU × 0.5 GiB × N seg × Consumption rate. Smoke 1 PDF (~5 pages) = <$0.05.

## Próximo

→ **048**: `aeco-source-crawler` Container Apps Job (parametrizado por `source_type`, cron diario 03:00 UTC, smoke 50 docs en `aeco/raw/`).
