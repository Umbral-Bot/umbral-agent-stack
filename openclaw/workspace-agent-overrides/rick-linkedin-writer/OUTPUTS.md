# OUTPUTS — Contrato de salida `rick-linkedin-writer`

> **Status:** design-only. Implementación viva: Stage 5. Stages 6 y 7 son stubs.

## Stage 5 — Ranking JSON

### Reporte (siempre, dry-run o commit)

**Path:** `reports/stage5-ranking-{timestamp}-{dryrun|commit}.json`

**Shape:**

```json
{
  "stage": "stage5_rank_candidates",
  "version": "v0-deterministic",
  "timestamp_utc": "2026-05-07T18:30:00Z",
  "mode": "dry-run",
  "config": {
    "weights": {
      "w1_core_aec": 0.4,
      "w2_adyacente": 0.3,
      "w3_recency": 0.2,
      "w4_referente": 0.1
    },
    "buckets_loaded": {
      "core_aec_count": 15,
      "adyacente_count": 8,
      "voz_david_count": 4
    }
  },
  "stats": {
    "candidates_total": 16,
    "candidates_eligible": 16,
    "candidates_skipped_no_text": 0,
    "score_min": 0.04,
    "score_median": 0.21,
    "score_max": 0.74
  },
  "top_n": 10,
  "items": [
    {
      "rank": 1,
      "url_canonica": "https://www.youtube.com/watch?v=...",
      "referente_id": "ref_xxx",
      "referente_nombre": "...",
      "canal": "youtube",
      "titulo": "...",
      "publicado_en": "2026-05-01T12:00:00Z",
      "ranking_score": 0.74,
      "ranking_reason": {
        "core_aec": {
          "matches": ["BIM", "Revit"],
          "raw_count": 5,
          "normalized": 0.5,
          "weighted": 0.20
        },
        "adyacente": {
          "matches": ["productividad profesional"],
          "raw_count": 1,
          "normalized": 0.125,
          "weighted": 0.0375
        },
        "recency": {
          "days_old": 6,
          "normalized": 0.94,
          "weighted": 0.188
        },
        "referente": {
          "canal": "youtube",
          "weight_canal": 1.0,
          "weighted": 0.1
        },
        "total": 0.526
      }
    }
  ]
}
```

### Mutación SQLite (sólo si `--commit`)

```sql
ALTER TABLE discovered_items ADD COLUMN ranking_score REAL;       -- idempotente
ALTER TABLE discovered_items ADD COLUMN ranking_reason TEXT;
ALTER TABLE discovered_items ADD COLUMN ranking_at TEXT;

UPDATE discovered_items SET
  ranking_score = ?,
  ranking_reason = ?,   -- JSON string
  ranking_at = ?         -- ISO8601 UTC
WHERE url_canonica = ?;
```

**Idempotencia:** segundo `--commit` sin `--rerank` no escribe nada (filtro `ranking_score IS NULL` ya excluye). Con `--rerank` sobrescribe todo.

### Exit codes

| Code | Significado |
|---|---|
| 0 | OK (incluso si 0 items) |
| 2 | SQLite no existe |
| 3 | YAML config malformado |
| 4 | Error de escritura en commit mode |

## Stage 6 — Combinación AEC

### Output esperado (cuando se implemente)

**Path:** `reports/stage6-combine-{timestamp}.json`

```json
{
  "stage": "stage6_aec_combine",
  "version": "stub",
  "timestamp_utc": "...",
  "decision": "single | combined",
  "primary": {
    "url_canonica": "...",
    "ranking_score": 0.74
  },
  "partner": {
    "url_canonica": "...",
    "ranking_score": 0.61,
    "bridge_type": "mecanismo | problema | consecuencia_operativa | contraste",
    "bridge_justification": "1-2 frases explicando por qué el puente es real"
  },
  "transformation_path": "(si single) cómo aterrizar el item solo en voz David"
}
```

**Hoy:** `main()` raise `NotImplementedError("Fase LLM, próximo PR")`.

## Stage 7 — Candidato Notion

> **Pendiente. No implementado en este PR.**

Output: payload tipo `editorial-candidate-payload` (ver `rick-linkedin-writer/ROLE.md` §"Output contract") con `canal=linkedin`, listo para escritura en `Publicaciones` (DB `e6817ec4698a4f0fbbc8fedcf4e52472`) **bajo gate humano**.

## Side effects

| Stage | SQLite | Notion | Filesystem |
|---|---|---|---|
| Stage 5 dry-run | ❌ | ❌ | ✅ `reports/stage5-*.json` |
| Stage 5 commit | ✅ (3 columnas) | ❌ | ✅ `reports/stage5-*.json` |
| Stage 6 (futuro) | ❌ | ❌ | ✅ `reports/stage6-*.json` |
| Stage 7 (futuro) | ❌ | ✅ (con human gate) | ✅ `reports/stage7-*.json` |

## Garantías

- **Determinismo:** Stage 5 con misma `state.sqlite` + misma `config/aec_keywords.yaml` produce **bit-for-bit el mismo output**. Verificado por `tests/discovery/test_stage5_ranking.py::test_reproducibilidad_bit_for_bit`.
- **Sin LLM en Stage 5:** validable bit-for-bit. Stage 6/7 sí pueden invocar LLM.
- **Sin escrituras Notion** en ningún Stage cubierto por este PR.
- **Reversibilidad:** las 3 columnas nuevas se pueden borrar con `UPDATE discovered_items SET ranking_score=NULL, ranking_reason=NULL, ranking_at=NULL`.
