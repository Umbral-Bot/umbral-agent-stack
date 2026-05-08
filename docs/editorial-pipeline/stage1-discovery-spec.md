# Stage 0 / Stage 1 — Discovery Spec (Wave1 H2)

> Read-only against Notion. Writes only to local SQLite at `~/.cache/rick-discovery/state.sqlite` (configurable). LinkedIn discovery deliberately skipped (escalado a David). YouTube canal: snapshot only — fetch fuera de alcance H2.

## Decisión D1 — Naming

Implementación dividida en dos scripts dedicados, ambos nuevos:

- [scripts/discovery/stage0_load_referentes.py](../../scripts/discovery/stage0_load_referentes.py) — lee `👤 Referentes`, filtra y persiste el snapshot.
- [scripts/discovery/stage1_discover_signals.py](../../scripts/discovery/stage1_discover_signals.py) — fan-out a RSS/Web por dominio con robots+rate-limit, persiste `signals_raw`.

Justificación:

- Testing aislado por canal y por etapa.
- Cobertura por archivo (`stage0` vs `stage1`).
- Cada etapa puede reintentarse de manera independiente sin re-leer Notion.
- Conservar [scripts/discovery/stage2_ingest.py](../../scripts/discovery/stage2_ingest.py) intacto (otra fase del pipeline editorial pre-existente).

## Schema `👤 Referentes` (Notion)

| Campo                      | Tipo Notion       | Lectura                               |
|----------------------------|-------------------|---------------------------------------|
| `Nombre`                   | title             | string                                |
| `RSS feed`                 | url               | string \| None                        |
| `Web / Newsletter`         | url               | string \| None                        |
| `YouTube channel`          | url               | string \| None                        |
| `LinkedIn activity feed`   | url               | string \| None                        |
| `LinkedIn`                 | url               | string \| None                        |
| `Confianza canales`        | select            | name \| None                          |
| `Flags canales`            | multi_select      | tuple[str, ...]                       |

> El DS no tiene un boolean `Activo` ni `Pausado` explícito. Estado derivado:

- **Excluido** (no se procesa) ⇔ `Confianza canales = DUPLICADO` **o** `Flags canales ∋ DUP`.
- **Pausado** (skip, log INFO) ⇔ `Flags canales ∋ REQUIERE_VERIFICACION_MANUAL`.
- **Activo** ⇔ no excluido y no pausado.

Bloqueante levantado: si Wave1 H4 (schema audit) introduce campos `Activo`/`Pausado` formales, S0 debe leerlos y la lógica derivada se vuelve fallback.

## Channel fan-out

Por cada referente activo, S0 emite hasta 5 filas en `referentes_snapshot`:

| canal_tipo | source                              |
|------------|-------------------------------------|
| `rss`      | `RSS feed`                          |
| `web`      | `Web / Newsletter`                  |
| `youtube`  | `YouTube channel`                   |
| `linkedin` | `LinkedIn activity feed` y/o `LinkedIn` (deduped si coinciden) |

## Schema SQLite — migración 0001

Archivo: [scripts/discovery/migrations/0001_referentes_signals.sql](../../scripts/discovery/migrations/0001_referentes_signals.sql).

### `referentes_snapshot`

```sql
PRIMARY KEY (referente_id, canal_tipo, canal_url)
```

Idempotente: `INSERT … ON CONFLICT(referente_id, canal_tipo, canal_url) DO UPDATE SET snapshot_at = excluded.snapshot_at, nombre = excluded.nombre`.

### `signals_raw`

```sql
signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
referente_id, canal_tipo, url, canonical_url, title, excerpt, published_at,
discovered_at,
dedup_hash TEXT NOT NULL UNIQUE,
source_status TEXT NOT NULL
```

`source_status ∈ { ok | http_404 | http_5xx | http_error | timeout | robots_disallow | parse_error | linkedin_skip | out_of_scope_stage1 }`.

Dedup: `sha256(canonical_url + "\n" + (iso_pub or ""))` UNIQUE.

## Stage 1 — fetch policy

- User-Agent: `UmbralBIM-Editorial-Bot/1.0 (+contacto@umbralbim.cl)`.
- Timeout: 10 s.
- Retries: 1 s + 3 s backoff sólo en 5xx y timeouts (404 no se reintenta).
- Robots: `urllib.robotparser`. Cache por host. Fail-open ante error de red.
- Rate-limit: `--min-interval` por dominio (default 2 s, real run usó 1 s).
- LinkedIn: **dos guards** antes de cualquier IO:
  1. `canal_tipo == "linkedin"`.
  2. `host` matchea `linkedin.com` (incluyendo `*.linkedin.com`).
  Cualquier match → WARN log + insert con `source_status = linkedin_skip`. **Nunca** se hace HTTP a `*.linkedin.com`.
- YouTube y otros canales no-rss/no-web: snapshot only, `source_status = out_of_scope_stage1`.

## Canonicalización de URL

`canonicalize_url(url)`:
- Lowercase scheme + host.
- Strip `utm_*`, `fbclid`, `gclid`, `ref`, `ref_src`.
- Strip trailing `/` si path no es raíz.
- Mantiene puerto si no es default.

## Contrato downstream para S2

Wave1 H3 (S2 Source Verification) leerá `signals_raw WHERE source_status = 'ok'`. La columna `dedup_hash` permite dedupe lateral entre S1 y la futura `signals_verified`.

## CLI

### Stage 0

```bash
python -m scripts.discovery.stage0_load_referentes \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  [--data-source-id <ds>] [--dry-run] [--limit N] \
  [--referente-id <id>] [--verbose]
```

### Stage 1

```bash
python -m scripts.discovery.stage1_discover_signals \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  [--canal {rss,web,all}] [--max-per-canal N] \
  [--min-interval 2.0] [--snapshot-max-age-hours N] \
  [--dry-run] [--verbose]
```

## Env vars

- `NOTION_API_KEY` — token Notion (S0).
- `UMBRAL_DISCOVERY_REFERENTES_DS_ID` — data source id (S0; o `--data-source-id`).

## Tests

31 tests, 86% coverage promedio (`notion_read.py` 92%, `stage1_discover_signals.py` 87%, `stage0_load_referentes.py` 73%).

Cubren: filtrado activo/pausado, fan-out, paginación Notion + 401, parsing RSS+Atom, parse_error, canonicalize/dedup_hash, robots disallow → 0 requests, rate-limit ≥ min_interval, retries 5xx (3 calls), 404/timeout, web title+excerpt, LinkedIn double-guard (2 tests dedicados a verificar 0 HTTP requests).

## Smoke run

Ver [reports/2026-05-08-stage1-smoke-run.md](../../reports/2026-05-08-stage1-smoke-run.md): 17 referentes activos, 70 fan-out rows, 97 unique signals, 32 LinkedIn skips, 0 HTTP a linkedin.com.
