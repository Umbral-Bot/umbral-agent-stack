# Wave1 H2 — Stage 1 Discovery Smoke Run

**Date:** 2026-05-08  
**Branch:** `copilot/feat-s0-s1-discovery`  
**Run:** real fetch against live `👤 Referentes` data source.

## Stage 0 — Load Referentes from Notion

```json
{
  "total_in_notion": 26,
  "activos_seleccionados": 17,
  "excluidos": 1,
  "pausados": 8,
  "channels_fan_out": 70,
  "by_canal": {"rss": 11, "web": 16, "youtube": 11, "linkedin": 32},
  "snapshot_at": "2026-05-08T22:33:55+00:00"
}
```

- **Excluidos (1)**: 1 referente con `Confianza canales = DUPLICADO` o `Flags canales ∋ DUP`.
- **Pausados (8)**: 8 referentes con `Flags canales ∋ REQUIERE_VERIFICACION_MANUAL`.
- **Activos (17)**: pasaron a snapshot con fan-out completo a SQLite.

## Stage 1 — Discover Signals (RSS + Web only; LinkedIn skipped; YouTube out-of-scope)

CLI:

```bash
python -m scripts.discovery.stage1_discover_signals \
  --sqlite /tmp/wave1h2-state.sqlite \
  --canal all --max-per-canal 20 --min-interval 1.0
```

Result:

```json
{
  "snapshot_rows": 70,
  "referentes_processed": 17,
  "domains_count": 17,
  "signals_unique": 97,
  "signals_duplicate": 0,
  "linkedin_skips": 32,
  "robots_disallow": 0,
  "rate_limit_hits": 7,
  "errors_by_status": {"http_404": 5, "http_error": 3}
}
```

### `signals_raw` breakdown by canal × source_status

| canal_tipo | source_status         | count |
|------------|-----------------------|-------|
| linkedin   | linkedin_skip         | 32    |
| rss        | ok                    | 50    |
| rss        | http_404              | 5     |
| rss        | http_error            | 2     |
| web        | ok                    | 15    |
| web        | http_error            | 1     |
| youtube    | out_of_scope_stage1   | 11    |
| **TOTAL**  |                       | **116** |

### Top 4 RSS referentes (signals OK)

| referente_id                           | RSS items |
|----------------------------------------|-----------|
| ce16d299-843e-4094-a97c-cad9eda67db7   | 20        |
| d7c9538e-d7ee-4147-8dd2-2a4b902d2e6a   | 15        |
| d7c794b6-a61f-4739-b7fb-10e0bdc61ae0   | 10        |
| e10c6269-11d9-481d-b96b-f7951610d37f   | 5         |

≥ 3 referentes RSS reales con señales — criterio cumplido.

### Domains touched (17)

aelion.io, balkanarchitect.com, bernardmarr.com, curbal.com, dionhinchcliffe.com, mastermind.ac, pascalbornet.com, pascalbornet.substack.com, rojo.me, ruben.substack.com, thecodingtrain.com, www.3blue1brown.com, www.alextheanalyst.com, www.deeplearning.ai, www.goingdigital.in, www.storytellingwithdata.com, www.theb1m.com.

## LinkedIn safety verification

```bash
$ grep -iE "Request.*linkedin\.com" /tmp/s1_smoke.log
# (empty — 0 HTTP requests to linkedin.com)
```

32 LinkedIn channels (15 `LinkedIn` + 17 `LinkedIn activity feed`, after dedup) were registered in `signals_raw` with `source_status = linkedin_skip` and a structured WARN log — never fetched. Two-layer guard verified live.

## Errors (acceptable for first run)

- **http_404 × 5** (RSS): feeds han movido / no existen — candidatos a `pausado` en próxima iteración.
- **http_error × 3**: una mezcla de redirecciones rotas / cert / 4xx no-404. Detalle se guarda en `signals_raw.source_status` y se puede triaging luego.

## Robots & rate-limit

- `robots_disallow = 0` — todos los hosts permiten al bot.
- `rate_limit_hits = 7` — el limiter durmió 7 veces para respetar `--min-interval 1.0` (algunos referentes comparten dominio: `pascalbornet.com` + `pascalbornet.substack.com`, etc.).

## Idempotencia

`signals_duplicate = 0` en la primera corrida (esperado). En tests unitarios (`test_rss_parses_n_signals_and_idempotent_rerun`) la segunda corrida arroja `signals_unique = 0` y `signals_duplicate = N`, validando el `dedup_hash` en el UNIQUE constraint.
