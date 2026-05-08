---
id: 2026-05-08-049
title: O16.2 sub-task 049 — version-detector + index-publisher (alias swap atómico)
status: open
priority: P1 (deadline duro Sponsorship 2026-06-30)
assigned_to: copilot-chat
created_at: 2026-05-08
created_by: copilot-chat (descomposición desde 045)
parent: 2026-05-07-045 (O16.2 kickoff)
relates_to: scripts/aeco-kb/, infra/docker/aeco-index-pipeline/, infra/azure/modules/aeco-index-pipeline-job.bicep
depends_on: O16.1 ✅, 046 ✅ (alias `aeco-kb-es-current`), 047 ✅ (parsed JSONL en `aeco/parsed/`)
blocks: 050 (e2e), 051 (smoke final)
---

# 049 — version-detector + index-publisher

## Objetivo

Pipeline post-parser que:
1. **version-detector**: lee `crudos/aeco/parsed/{source}/*.chunks.jsonl`, calcula diff vs manifest del index activo (alias target), emite `{added, changed, removed}` doc-ids.
2. **index-publisher**: clona schema del index activo a uno nuevo `aeco-kb-es-vYYYYMMDD[-HHMM]`, embebe chunks con `text-embedding-3-small` del Foundry productivo `umbralbim-resource`, sube docs, valida health (count + sample query), hace alias swap atómico.

Resultado: alias `aeco-kb-es-current` apunta al nuevo index validado; índice anterior queda intacto (rollback manual disponible).

## Criterio de éxito (DoD)

```bash
# Pre-req: 048 corrió y hay parsed/ en storage
az storage blob list --account-name stumbralagentsprod --container-name crudos \
    --prefix aeco/parsed/buildingsmart/ --auth-mode login --query "length(@)" -o tsv
# >= 3

# Smoke local
az login --tenant f67a8c0b-ec74-47cd-836c-355c5a6162d4
python scripts/aeco-kb/version_detector.py --source-type buildingsmart --output -
# Esperado: JSON con added=[3 doc_ids], changed=[], removed=[]

python scripts/aeco-kb/index_publisher.py --source-types buildingsmart minvu --dry-run
# Imprime plan: nuevo index name, count chunks, no toca Azure

python scripts/aeco-kb/index_publisher.py --source-types buildingsmart minvu
# Crea aeco-kb-es-v20260508, indexa, valida, swap alias
```

Verificación post-run:

```bash
az search alias show --service-name srch-umbral-kb-prod --name aeco-kb-es-current \
    --resource-group rg-umbral-agents-prod --query "indexes[0]" -o tsv
# Esperado: aeco-kb-es-v20260508 (o -HHMM si segundo run del día)

az search index show --service-name srch-umbral-kb-prod --name aeco-kb-es-v20260508 \
    --resource-group rg-umbral-agents-prod --query "statistics.documentCount"
# Esperado: >= 50
```

Sample query (REST):
```bash
curl -X POST "https://srch-umbral-kb-prod.search.windows.net/indexes/aeco-kb-es-current/docs/search?api-version=2024-07-01" \
    -H "Authorization: Bearer $(az account get-access-token --resource https://search.azure.com --query accessToken -o tsv)" \
    -H "Content-Type: application/json" \
    -d '{"search":"IFC","top":3}'
# Esperado: value[].length >= 3
```

## Decisiones lockeadas en 049

### D19. Estrategia de diff (version-detector)

Input:
- `crudos/aeco/parsed/{source}/{doc_id}.chunks.jsonl` (output 047, primera línea es `_meta`).
- Manifest del index activo en `crudos/aeco/index/{index_name}/manifest.jsonl` (escrito por publisher en run anterior). Si no existe (primer run) → todo es `added`.

Diff por **parent_doc_id + chunks_sha256** (sha256 sobre concatenación ordenada de chunk text). Output:

```json
{
  "source_type": "buildingsmart",
  "computed_at": "2026-05-08T03:00:00Z",
  "previous_index": "aeco-kb-es-v20260501",
  "added": ["IFC-4.3.2.0"],
  "changed": [{"doc_id": "IFC-4.3.1.0", "old_sha": "...", "new_sha": "..."}],
  "removed": ["IFC-4.2.0.0"],
  "unchanged": ["IFC-4.3.0.0"]
}
```

Strategy: `removed` es soft-delete (publisher omite esos docs del nuevo index). Rollback = repoint alias.

### D20. Embeddings: Foundry productivo cross-RG

- Endpoint: `https://umbralbim-resource.openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2024-10-21` (verificar deployment exacto en portal antes de live; si nombre difiere, override por env `EMBEDDING_DEPLOYMENT`).
- Auth: UAMI con role `Cognitive Services OpenAI User` en `umbralbim-resource`. Si no asignado todavía → tarea para 050 deploy real (publisher detecta 401 y exit con mensaje claro).
- Batch size: 16 chunks por request (límite seguro Azure OpenAI). Rate limit cliente: max 60 req/min.
- Retry: 3x exp backoff [2s, 8s, 32s] en 429+5xx.
- Costo estimado smoke 50 docs × ~50 chunks × 800 tokens = 2M tokens × $0.02/1M = $0.04. Negligible.

### D21. Naming del nuevo index

`aeco-kb-es-v{YYYYMMDD}`. Si ya existe (segundo publish mismo día) → `aeco-kb-es-v{YYYYMMDD}-{HHMM}` UTC. Schema clonado desde el index actual del alias (no hardcodeado — flexibilidad para schema evolution en 050+).

### D22. Validación pre-swap (gate)

Antes de `alias create-or-update`:

1. **Doc count**: nuevo index `documentCount >= expected_count * 0.95` (5% tolerancia por skipped chunks). Esperado = sum(chunks loaded) − failures.
2. **Sample query**: query `"IFC OR norma OR construcción"` con `top=5` → al menos 3 results con `@search.score > 0`.
3. **No exceptions**: si publisher acumuló >5% chunks fallidos en upload → abort sin swap.

Si gate falla: NO swap, log error, exit 1, deja nuevo index huérfano para inspección manual.

### D23. Swap atómico + retención

- `az search alias create-or-update --indexes aeco-kb-es-v20260508` — operación atómica server-side.
- Old index **NO se borra** automáticamente. Q2: retención manual. Q3: cron pruner mantiene últimas 3 versiones.

### D24. Rollback

Manual:
```bash
az search alias create-or-update --service-name srch-umbral-kb-prod \
    --name aeco-kb-es-current --indexes aeco-kb-es-v20260501 \
    --resource-group rg-umbral-agents-prod
```

Documentado en `scripts/aeco-kb/README.md` sección "Rollback".

### D25. Empaquetado: 1 image, 2 entrypoints

Una sola Container Apps image `aeco-index-pipeline` con dos comandos via `python -m`:
- `python -m scripts.aeco_kb.version_detector --source-type X`
- `python -m scripts.aeco_kb.index_publisher --source-types X Y`

Bicep define **1 Job** `aeco-index-pipeline` con `command` override por invocación. Q3: split en 2 Jobs si justifica scaling diferente.

## Entregables

1. `scripts/aeco-kb/version_detector.py` — calcula diff parsed vs manifest.
2. `scripts/aeco-kb/index_publisher.py` — clone schema, embed, upload, validate, swap.
3. `infra/docker/aeco-index-pipeline/Dockerfile` — image única.
4. `infra/docker/aeco-index-pipeline/entrypoint.sh` — passthrough a `python -m`.
5. `infra/azure/modules/aeco-index-pipeline-job.bicep` — Container Apps Job manualTrigger.
6. `scripts/aeco-kb/README.md` — secciones version-detector, index-publisher, rollback.
7. `pyproject.toml` — extra `aeco-kb` ya cubre `azure-search-documents`. Agregar opcional nada nuevo.

## Decisiones diferidas

- **Cron orquestador** crawler→parser→detector→publisher: 050 con Service Bus + KEDA.
- **Index pruner** (mantener últimas 3 versiones): Q3.
- **Schema evolution** automático: Q3 (Q2 clona schema actual literalmente).
- **`chunk-quality-eval`** subagent (gate adicional): Q3.

## Notas runtime

- No requiere VPS deploy.
- UAMI role pendiente: `Cognitive Services OpenAI User` en RG donde vive `umbralbim-resource`. Si no está → publisher exit 1 con instrucciones de fix.
- Sponsorship cost: ~$0.04 por publish run. Storage manifest negligible.

## Próximo

→ **050**: pipeline e2e (Service Bus + KEDA + cron) + IRAM/NMX seeds. ≥500 chunks indexados.
