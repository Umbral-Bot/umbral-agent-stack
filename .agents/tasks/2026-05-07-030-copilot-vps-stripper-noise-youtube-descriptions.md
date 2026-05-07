# Task 030 — Stripper determinístico de noise en YouTube descriptions

**Owner:** Copilot VPS (cuando David apruebe)
**Origen:** Auditoría Hilo 2 / scope inferido de la (no existente) task 029, ejecutada 2026-05-08.
**Prioridad:** Media — ataca el feedback principal de David post canary 013-K ("falta análisis del contenido") sin LLM ni cambio de schema Notion.

## Contexto

Auditoría sobre 3 items YouTube ya publicados en Notion (sqlite_id 52, 81, 291) confirmó:

1. **NO existe Stage 3 LLM enrichment** en la pipeline discovery. Las "stages" son: 2 (ingest) → 2.5 (backfill_youtube_content) → 3 (promote por reglas, no LLM) → 4 (push Notion).
2. El "ruido" en las páginas Notion publicadas no viene de falta de análisis — viene de que la `Descripción` cruda de YouTube es **60-80% sponsors + boilerplate de canal + disclaimers + redes sociales**.
3. Métricas observadas (señal/ruido por item):
   - sqlite_id=52 (Alex Freberg, ETL Databricks): 28 blocks, ~5 con valor real, 23 boilerplate.
   - sqlite_id=81 (Nate Gentile, Linux): 8 blocks, ~0 con valor sustantivo (todo sponsor + redes + #linux).
   - sqlite_id=291 (The B1M, Chrysler Building): 26 blocks, ~3 con valor, 23 boilerplate.
4. Header con metadata (duración/views/likes) y bloques de Capítulos parseados **funcionan muy bien**. No tocar.

## Hipótesis a validar

Un stripper determinístico aplicado en `backfill_youtube_content.py` (o módulo nuevo `dispatcher/extractors/youtube_description_cleaner.py`) que filtre patrones de ruido conocidos puede reducir 28→~6 blocks y ~26→~5 blocks **sin LLM, sin schema nuevo, costo $0**, mejorando drásticamente la legibilidad humana en las páginas Notion.

## Patrones candidatos a strip (lista inicial — refinar en spike corto)

- Bloques con marcadores `BECOME A MEMBER`, `RESOURCES:`, `Websites:`, `Redes Sociales:`, `Series de este canal:`.
- Líneas con `discount code`, `código X`, `promo code`, `sponsor`, `paid promotion`.
- Líneas con dominios sponsor frecuentes: `bit.ly`, `surfshark`, `nordvpn`, `coursera.pxf.io`, `amazon.to/`, `surfshark.com/`, redes (`instagram`, `twitter`, `twitch`, `patreon`).
- Disclaimers legales: `All opinions or statements`, `T&Cs`, `copyright`, `do not reflect the opinion`.
- Bloques con `→` o `:` como separador de listas largas de promo.
- Hashtags al final del cuerpo (#linux, #bim, etc.) — opcionalmente preservar como tags Notion.

## Acción

1. **Spike read-only** sobre los ~16 items YouTube enriquecidos en SQLite (sqlite ids del backlog actual):
   - Aplicar regex stripper candidato.
   - Reportar para cada item: blocks_pre, blocks_post, líneas removidas (sample 5).
   - **No tocar SQLite. No tocar Notion.** Solo análisis.
2. Refinar regex con base en falsos positivos observados (palabras clave útiles que se barren).
3. Implementación opt-in conservadora:
   - Flag `--clean-description` en `backfill_youtube_content.py`.
   - Default: OFF (preservar comportamiento actual).
   - Cuando ON: aplica stripper sobre `description` antes de armar `<h2>Descripción</h2>` block.
4. Re-run backfill `--commit --clean-description` sobre los 16 items y validar render Notion humano (sample 3-4).
5. Si validación humana OK → flip default a ON en una PR siguiente.

## Quality gates

- 0 LLM calls.
- 0 cambios en schema Notion.
- 0 cambios en stages 2/3/4 (solo backfill 2.5).
- 0 escrituras Notion durante spike.
- A/B reportable: blocks_pre vs blocks_post sobre ≥10 items.
- Validación humana sobre ≥3 items por David antes de flip default.

## Decisión deferred (NO parte de esta task)

- Resumen ejecutivo IA / tags semánticos / takeaways → solo si después de 030 David evalúa que aún falta resumen. Eso requiere LLM (spike aparte) + schema Notion nuevo (ADR `notion-governance/docs/adr/`).
- Transcripciones (captions / Whisper) → backlog congelado. La premisa "Stage 3 LLM necesita transcripción" cae porque no hay Stage 3 LLM.

## Referencias

- Reporte auditoría Hilo 2 (en mensaje de David, no persistido en repo).
- Items canary publicados: `reports/stage4-push-20260507T165744Z-commit2.json`.
- Items bulk publicados: `reports/stage4-push-20260507T170310Z-commit.json`.
- Backfill actual: `scripts/discovery/backfill_youtube_content.py` (PR #343, `7352cfa`).
- HTML→blocks transformer: `scripts/discovery/html_to_notion_blocks.py`.
