---
id: 2026-05-07-048
title: O16.2 sub-task 048 — aeco-source-crawler (parametrizado por source_type, smoke 50 docs)
status: open
priority: P1 (deadline duro Sponsorship 2026-06-30)
assigned_to: copilot-chat
created_at: 2026-05-08
created_by: copilot-chat (descomposición desde 045)
parent: 2026-05-07-045 (O16.2 kickoff)
relates_to: scripts/aeco-kb/, infra/docker/aeco-source-crawler/, infra/azure/modules/aeco-source-crawler-job.bicep
depends_on: O16.1 ✅ (Storage `stumbralagentsprod` + UAMI con `Storage Blob Data Contributor`)
blocks: 049 (publisher consume `aeco/raw/`), 050 (e2e + 3 LATAM restantes), 051 (smoke final)
---

# 048 — aeco-source-crawler (Container Apps Job, smoke buildingSMART + MINVU)

## Objetivo

Container Apps Job parametrizado por `--source-type` que descarga PDFs/HTMLs de fuentes públicas AECO, los normaliza a PDF cuando es necesario (HTML simple → PDF deferido a Q3), aplica rate-limit + dedupe por SHA-256, y los persiste en `crudos/aeco/raw/{source_type}/{doc_id}.pdf`.

**Q2 smoke target**: 2 fuentes — buildingSMART (intl) + MINVU (cl) — ≥50 documentos totales en `crudos/aeco/raw/`. Las 2 LATAM restantes (IRAM, NMX) se cablean en **050**.

**No incluye**: parsing (047), embedding/indexado (049), trigger Event Grid downstream (050), conversión HTML→PDF compleja (Q3).

## Criterio de éxito (DoD)

```bash
# Smoke buildingSMART
az containerapp job start --name aeco-source-crawler --resource-group rg-umbral-agents-prod \
    --env-vars "SOURCE_TYPE=buildingsmart" "MAX_DOCS=30"

# Smoke MINVU
az containerapp job start --name aeco-source-crawler --resource-group rg-umbral-agents-prod \
    --env-vars "SOURCE_TYPE=minvu" "MAX_DOCS=20"

# Verificar
az storage blob list --account-name stumbralagentsprod --container-name crudos \
    --prefix aeco/raw/buildingsmart/ --auth-mode login --query "length(@)" -o tsv
# Esperado: >=20

az storage blob list --account-name stumbralagentsprod --container-name crudos \
    --prefix aeco/raw/minvu/ --auth-mode login --query "length(@)" -o tsv
# Esperado: >=15

# Manifest dedupe:
az storage blob download --account-name stumbralagentsprod --container-name crudos \
    --name aeco/raw/_manifest/buildingsmart.jsonl --auth-mode login --file -
# Esperado: 1 línea por doc, con sha256 + source_url + downloaded_at
```

## Decisiones lockeadas en 048

### D12. Seeds estáticos por source_type (Q2 conservador)

Seeds versionados en repo (`scripts/aeco-kb/seeds/{source_type}.yaml`). Q3 evaluar discovery dinámico (sitemap.xml crawl). Q2 enumera URLs explícitas para evitar:
- crawl loops involuntarios.
- ban por scraping agresivo.
- burn de DI budget en docs irrelevantes.

```yaml
# scripts/aeco-kb/seeds/buildingsmart.yaml
source_type: buildingsmart
jurisdiction: intl
doc_type: spec
default_lang: en  # buildingSMART original; traducción ES diferida a Q3
seeds:
  - url: https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/IFC4_3_2_0/IFC4_3_2_0.pdf
    doc_id: IFC-4.3.2.0
    version: IFC-4.3.2.0
    valid_from: "2024-04-01"
  - url: https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/IFC4_3_1_0/IFC4_3_1_0.pdf
    doc_id: IFC-4.3.1.0
    version: IFC-4.3.1.0
    valid_from: "2023-08-01"
  # ... más seeds
```

Si el repo no tiene seeds para `--source-type X`, el job falla rápido con exit 2.

### D13. Rate limit + politeness

- **1 request por segundo por host** (sleep entre downloads).
- **User-Agent**: `umbral-aeco-crawler/0.1 (+contacto@umbralbim.cl)` — identificable, contacto para opt-out.
- **Respeto robots.txt**: best-effort vía `urllib.robotparser` para cada host. Si robots.txt bloquea: skip + log. NO override.
- **Timeout HTTP**: 60s connect + read.
- **Retry**: 3 intentos con backoff exponencial (1s, 4s, 16s) en 5xx + 429. NO retry en 4xx (excepto 429).

### D14. Dedupe vía SHA-256 + manifest JSONL

- Por cada download: `sha256(content)`.
- Si el blob `aeco/raw/{source_type}/{doc_id}.pdf` ya existe **y** su MD5 metadata coincide con el sha256 calculado del nuevo: skip.
- Manifest `aeco/raw/_manifest/{source_type}.jsonl` se actualiza append-only:
  ```json
  {"doc_id":"IFC-4.3.2.0","sha256":"...","source_url":"...","content_type":"application/pdf","size_bytes":12345,"downloaded_at":"2026-05-08T03:00:00Z","status":"new|skipped|updated"}
  ```
- Política de updates: si `sha256` difiere de la última entrada del manifest → sobrescribir blob + nueva entrada manifest con `status=updated`. Re-parse y re-index lo dispara 049 vía manifest watcher (Q2 manual; Q3 Event Grid).

### D15. Cap operativo + kill switch budget

- `MAX_DOCS` env (default 100) limita docs por invocación. Smoke Q2 usa 30+20=50.
- **Pre-flight cost check**: antes de descargar, llama `az consumption budget show` (vía REST + UAMI) para `budget-document-intelligence`. Si `currentSpend.amount / amount > 0.85`: skip + exit 0 con log warning. Esto protege ROI: aunque DI no se llama acá (el parser sí), el crawler downstream genera carga DI.
- Q3: agregar `BUDGET_THRESHOLD` env override + Slack/Teams alert.

### D16. Tipos de contenido soportados Q2

| Content-Type | Acción Q2 |
|---|---|
| `application/pdf` | ✅ download directo |
| `text/html` | ⚠️ Q2: download raw HTML a `aeco/raw/{source}/{doc_id}.html` (parser 047 no maneja HTML — ese caso queda EXCLUIDO del smoke 048; emitido a manifest con `status=skipped_html`) |
| `application/json`, `application/xml` | ⏸ Diferido Q3 |
| Otros | ❌ skip + log warning |

Para Q2 smoke: priorizar seeds **PDF directo**. MINVU publica DDU como PDF, buildingSMART IFC schemas como PDF. Cumple.

### D17. Scheduling

Q2: invocación **manual** (`az containerapp job start`). Cron diario 03:00 UTC se cablea en **050**. Bicep deja `triggerType: 'Schedule'` comentado para Q3 enable rápido.

### D18. Container image: misma estrategia que 047

`ghcr.io/umbral-bot/aeco-source-crawler:latest`. Build vía GHA en CI/CD (Q3). Q2: build local + push manual aceptable para smoke.

## Entregables

1. `scripts/aeco-kb/source_crawler.py` — módulo + CLI con argparse.
2. `scripts/aeco-kb/seeds/buildingsmart.yaml` — seeds Q2 (3-5 PDFs IFC).
3. `scripts/aeco-kb/seeds/minvu.yaml` — seeds Q2 (3-5 PDFs DDU recientes).
4. `scripts/aeco-kb/seeds/iram.yaml` — placeholder Q2 (puebla 050).
5. `scripts/aeco-kb/seeds/nmx.yaml` — placeholder Q2 (puebla 050).
6. `infra/docker/aeco-source-crawler/Dockerfile` — Python 3.12-slim + httpx + pyyaml + azure SDKs.
7. `infra/docker/aeco-source-crawler/entrypoint.sh`.
8. `infra/azure/modules/aeco-source-crawler-job.bicep` — Container Apps Job manualTrigger.
9. `pyproject.toml` — agregar `httpx` ya está; agregar `pyyaml` ya está. Confirmar `aeco-kb` opt-dep cubre `azure-storage-blob` (sí desde 047). Sin cambios.
10. `scripts/aeco-kb/README.md` — sección "source-crawler".

## Decisiones diferidas (no bloquean 048)

- **HTML→PDF/markdown** conversion: Q3 con `playwright` o `markdownify` (ya en deps).
- **Sitemap discovery**: Q3 — Q2 seeds explícitos.
- **Cron schedule**: Q3 — Q2 manual.
- **Slack/Teams alert** cuando budget >85%: Q3.
- **Trigger downstream parser**: 050 cablea Event Grid blob created → SB topic → KEDA scales 047.

## Notas runtime

- No requiere VPS deploy.
- Image pull desde GHCR (público Q2).
- Sponsorship cost: storage egress (download externos a Azure) gratis. Storage write tier Hot: ~$0.05 / 10k operations + $0.018/GB-mo. Smoke 50 PDFs ~500MB total = $0.01/mes negligible.

## Próximo

→ **049**: `version-detector` + `index-publisher` (alias swap atómico, gated by health). Lee `aeco/parsed/`, embebe con text-embedding-3-small del Foundry productivo, indexa a `aeco-kb-es-vYYYYMMDD`, valida count + sample query, swap alias.
