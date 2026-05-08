# 050 — O16.2 Pipeline e2e + IRAM/NMX seeds (≥500 chunks)

**Fecha:** 2026-05-08  
**Sub-task de:** [`2026-05-07-045-o16-2-kickoff-aeco-kb-pilot.md`](./2026-05-07-045-o16-2-kickoff-aeco-kb-pilot.md)  
**Smoke target:** Friday retro 2026-06-26 — bot Umbral cita KB con `aeco-kb-es-vYYYYMMDD` visible.  
**Owner:** Copilot Chat (autónomo bajo mandato).

## Scope

Cierra el pipeline e2e cableando los 4 jobs (046 schema, 047 parser, 048 crawler, 049 publisher) en un orquestador secuencial Q2 + completa seeds IRAM/NMX + verifica que la KB final tenga ≥500 chunks indexados con cobertura mínima por jurisdicción.

## Decisiones autónomas (D26-D32)

| ID | Decisión | Default |
|---|---|---|
| D26 | Orquestación Q2 | Bash script local `run_pipeline.sh` que arranca los 3 ACA Jobs vía `az containerapp job start` secuencialmente y espera con `az containerapp job execution show`. Q3 upgrade → Service Bus chained. |
| D27 | IRAM seeds | 2 PDFs públicos (SISCO Estrategia BIM AR, IRAM ISO 19650-1 resumen). Validar HEAD pre-crawl. |
| D28 | NMX seeds | 2 PDFs públicos vía DOF/SHCP (Estrategia BIM MX, NMX-R-098-SCFI-2018). |
| D29 | Gate ≥500 chunks | `verify_kb.py` consulta `$count` del alias activo + sample query por jurisdicción (≥1 hit por `ar`, `cl`, `mx`, `intl`). Exit 1 si falla. |
| D30 | Image | Reusar las 3 imágenes ya construidas (047, 048, 049). 050 NO agrega imagen, solo orquesta. |
| D31 | Bicep umbrella | Nuevo `infra/azure/aeco-kb-pipeline.bicep` que referencia los 3 módulos existentes + outputs con job names para el script. |
| D32 | Schedule Q2 | Manual trigger only. Cron upgrade en Q3 (épica O16.4). |

## Deliverables

1. ✅ `scripts/aeco-kb/seeds/iram.yaml` — populated (2 seeds).
2. ✅ `scripts/aeco-kb/seeds/nmx.yaml` — populated (2 seeds).
3. `scripts/aeco-kb/run_pipeline.sh` — bash orquestador secuencial (4 sources).
4. `scripts/aeco-kb/verify_kb.py` — gate ≥500 chunks + cobertura por jurisdicción.
5. `infra/azure/aeco-kb-pipeline.bicep` — umbrella que referencia los 3 jobs.
6. `scripts/aeco-kb/README.md` — sección "Sub-task 050 — pipeline e2e".

## Smoke (cuando UAMI/imágenes estén live, ya en 051)

```bash
bash scripts/aeco-kb/run_pipeline.sh buildingsmart minvu iram nmx
python scripts/aeco-kb/verify_kb.py --min-chunks 500 --jurisdictions ar,cl,mx,intl
```

## Out of scope

- Live Azure deploy → 051 (junto con AgenteUB File Search wiring).
- Cron schedule → Q3.
- Service Bus / KEDA chaining → Q3.
