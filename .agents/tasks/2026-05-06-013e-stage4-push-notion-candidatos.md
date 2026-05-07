# Task 013-E — Stage 4: Push de candidatos a Notion (idempotente, dry-run first)

- **Date:** 2026-05-06
- **Assigned to:** copilot-vps (codear + smoke en VPS, mismo patrón que 013-C / 013-D)
- **Type:** code + smoke run (Python script + ejecución read+write Notion controlada)
- **Depends on:**
  - **PR #317 mergeado a `main`** (recovery post force-push). Hasta que esté en main, el archivo `scripts/discovery/stage3_promote.py` y los 20 ítems promovidos de Stage 3 no están reconocidos en main y este task no puede empezar.
  - SQLite local `~/.cache/rick-discovery/state.sqlite` con ≥1 ítem `WHERE promovido_a_candidato_at IS NOT NULL`. Verificación obligatoria en Phase 0.
  - `NOTION_API_KEY` disponible en `~/.config/openclaw/env` (Rick scope, integración con permiso sobre la DB destino).
- **Plan reference:** `docs/plans/linkedin-publication-pipeline.md` §"Destino: candidatos de publicacion" + Etapa 1 cierre.
- **Status:** ready (bloqueado por PR #317).
- **Estimated effort:** 90-120 min (registry resolve + schema validate + script + smoke con --limit 5 + smoke bulk + tests).

---

## Contexto

Stage 3 (Task 013-D) marcó **20 ítems** en `discovered_items` con `promovido_a_candidato_at IS NOT NULL` (en SQLite local del VPS). Stage 4 los empuja como **filas nuevas a una database Notion existente** (DB de candidatos editoriales LinkedIn).

Este task **es la primera escritura a Notion del pipeline**. Por eso: dry-run obligatorio por defecto, idempotencia explícita por URL, rate-limit conservador, y registry update antes del primer write real.

## Destino Notion

- **Database URL:** `https://www.notion.so/umbralbim/e6817ec4698a4f0fbbc8fedcf4e52472?v=8ae76db01b7c453aaef3edb8093fb5c8`
- **Database ID:** `e6817ec4-698a-4f0f-bbc8-fedcf4e52472`
- **Data source ID:** **a resolver en Phase 0** (Notion REST `2025-09-03` requiere `data_source_id`, no `database_id`, para `POST /pages`).

## Objetivo

Implementar `scripts/discovery/stage4_push_notion.py` que:

1. Lee de SQLite los ítems con `promovido_a_candidato_at IS NOT NULL AND notion_page_id IS NULL`.
2. Para cada uno: query Notion DB filtrando por `url_canonica == <url>` (idempotencia). Si ya existe → guarda `notion_page_id` en SQLite y skip. Si no → `POST /v1/pages` con payload mapeado al schema Notion + guarda `notion_page_id`.
3. Default **dry-run**: NO consulta Notion (excepto schema fetch en Phase 1 si está cacheado, ver abajo) y NO muta SQLite. Solo con `--commit` ejecuta queries y writes reales.
4. Genera `reports/stage4-push-YYYYMMDDTHHMMSSZ.json` con resumen + samples de creados/skipped/errored.
5. Soporta `--limit N` para corridas controladas.
6. Rate-limit interno: **350 ms entre writes** (~3 req/s, bajo el límite Notion de 3 req/s sostenido).

## No-goals (explícitos)

- NO escribe a LinkedIn ni a ninguna red social.
- NO genera imágenes, ni invoca `nano-banana-2`, ni usa `rick-linkedin-writer` / `rick-qa` / `rick-communication-director`.
- NO modifica el schema de la DB Notion (lectura de schema sí; modificación NO).
- NO modifica el schema de la base de Referentes (que provee la relación `referente`).
- NO toca container RSSHub, Stage 2, ni Stage 3 (`stage3_promote.py` queda intacto).
- NO crea DB Notion nueva ni view nueva.
- NO modifica `notion-governance` (la actualización del registry se hace en una PR aparte en ese repo, NO desde acá).
- NO usa Notion MCP (Notion MCP ≠ Notion REST API; este script usa REST API directa con `NOTION_API_KEY`).

## Phases (autonomía Copilot VPS)

### Phase 0 — Pre-checks (todo abort early)

```bash
cd ~/umbral-agent-stack
git pull --ff-only origin main
# Verificar PR #317 está mergeado:
git log --oneline -1 -- scripts/discovery/stage3_promote.py
# DEBE existir. Si no: ABORT, esperar merge.

source .venv/bin/activate
test -s ~/.cache/rick-discovery/state.sqlite || { echo "ABORT: sqlite vacía"; exit 1; }
sqlite3 ~/.cache/rick-discovery/state.sqlite \
  "SELECT COUNT(*) FROM discovered_items WHERE promovido_a_candidato_at IS NOT NULL;"
# DEBE devolver ≥1. Si 0: ABORT, re-correr Stage 3 commit primero.

# Verificar NOTION_API_KEY disponible
test -n "$(grep -E '^NOTION_API_KEY=' ~/.config/openclaw/env)" || { echo "ABORT: NOTION_API_KEY ausente"; exit 1; }
```

### Phase 1 — Resolver `data_source_id` y leer schema

```bash
source <(grep -E '^(NOTION_API_KEY)=' ~/.config/openclaw/env | sed 's/^/export /')
DB_ID="e6817ec4-698a-4f0f-bbc8-fedcf4e52472"
curl -s https://api.notion.com/v1/databases/${DB_ID} \
  -H "Authorization: Bearer ${NOTION_API_KEY}" \
  -H "Notion-Version: 2025-09-03" \
  | tee /tmp/stage4-db-meta.json | jq '{id, title: .title[0].plain_text, data_sources: .data_sources, properties: (.properties | keys)}'
```

**Esperado:** JSON con `data_sources: [{id: "<UUID>", name: "..."}]` (en API 2025-09-03 cada DB tiene 1+ data_sources). Anotar el `data_source_id` para uso en `POST /pages`.

**Schema validation obligatoria** antes del primer write. Mapear las siguientes propiedades — si alguna falta, **ABORT** y reportar (no asumir, no crear):

| Propósito (script) | Property name esperada en Notion | Tipo esperado | Required en payload |
|---|---|---|---|
| Título principal | `Name` (o `Título` / `Title` — verificar) | `title` | sí |
| URL fuente | `URL` (o `URL canónica`) | `url` | sí |
| Canal | `Canal` | `select` | sí |
| Fecha publicación origen | `Fecha publicación` | `date` | no |
| Fecha promovido a candidato | `Promovido` | `date` | no |
| Referente origen (relation) | `Referente` | `relation` → DB Referentes | no (warn si DB destino lo requiere) |
| Trazabilidad SQLite | `Source SQLite ID` | `rich_text` o `number` | no |
| Estado editorial | `Estado` | `select` | no (default Notion lo maneja) |

Mapeo concreto se ajusta según el schema real devuelto en Phase 1. **Si el nombre exacto de las property difiere → ABORT y registrar en el reporte JSON el schema observado.** No improvisar mapeos.

### Phase 2 — SQLite migration (idempotente)

Antes del primer write, agregar columna para trazabilidad reversa:

```python
# Idempotente: PRAGMA table_info para ver si existe; si no, ALTER TABLE.
ALTER TABLE discovered_items ADD COLUMN notion_page_id TEXT NULL;
CREATE INDEX IF NOT EXISTS idx_discovered_notion_page ON discovered_items(notion_page_id);
```

Test obligatorio: ejecutar 2 veces seguidas → 2do run no falla.

### Phase 3 — Script `scripts/discovery/stage4_push_notion.py`

Estructura mínima:

```text
parse_args() → SqliteCfg, NotionCfg, mode (dry-run|commit), limit, output_path
load_pending(sqlite, limit) → list[Item]   # promovido NOT NULL AND notion_page_id IS NULL
fetch_schema(notion, data_source_id) → SchemaSpec  # cached for the run
validate_schema(schema, REQUIRED_PROPS) → ok | abort
build_payload(item, schema) → dict   # mapping mínimo + voluntary fields
query_existing(notion, data_source_id, url_canonica) → page_id | None
create_page(notion, data_source_id, payload) → page_id
mark_persisted(sqlite, item.id, page_id, mode)
main():
  pre-checks → schema fetch+validate
  for item in items[:limit]:
    sleep(350ms) entre writes (no antes del primer)
    existing = query_existing(...) if mode == 'commit' else None
    if existing: classify 'skipped_existing', mark in sqlite
    elif mode == 'commit': page_id = create_page(...); classify 'created'; mark in sqlite
    else: classify 'would_create' (dry-run, no http call)
  emit report
```

**Reglas duras:**

- Default `dry-run`. En dry-run: **0 HTTP calls a Notion** (ni queries ni writes). El script no consulta nada.
- En `--commit`: query antes de cada create (idempotencia). Si query devuelve hit → no se crea, se persiste el `page_id` existente en SQLite.
- Rate-limit: `time.sleep(0.35)` entre cada par de operaciones HTTP (entre query y create cuenta como 2 ops; entre items consecutivos también). Prefiero ser lento que perder por 429.
- Manejo 429: backoff exponencial (1s, 2s, 4s, 8s, abort tras 4 retries) y log explícito.
- Manejo otros 4xx/5xx: log con status + body, NO marcar `notion_page_id`, classify `errored`, continuar al siguiente ítem (no abort total a menos que sean todos los primeros 3 consecutivos).
- Schema fetch UNA vez al inicio del run (cached). Si schema cambia mid-run → fuera de scope.

### Phase 4 — Smoke runs

**Dry-run primero:**

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p reports
python scripts/discovery/stage4_push_notion.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --database-id e6817ec4-698a-4f0f-bbc8-fedcf4e52472 \
  --output reports/stage4-push-${TS}.json
echo "exit=$?"
```

**Commit run controlado (5 ítems primero):**

```bash
TS2=$(date -u +%Y%m%dT%H%M%SZ)
python scripts/discovery/stage4_push_notion.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --database-id e6817ec4-698a-4f0f-bbc8-fedcf4e52472 \
  --commit \
  --limit 5 \
  --output reports/stage4-push-${TS2}.json
echo "exit=$?"
# VERIFICAR EN NOTION (manual): que aparecieron 5 páginas nuevas con datos correctos.
# VERIFICAR SQLITE: 5 filas con notion_page_id NOT NULL.
```

**Commit bulk (resto):**

Solo si los 5 anteriores son visualmente correctos en Notion (reportar al usuario para go/no-go antes de bulk):

```bash
TS3=$(date -u +%Y%m%dT%H%M%SZ)
python scripts/discovery/stage4_push_notion.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --database-id e6817ec4-698a-4f0f-bbc8-fedcf4e52472 \
  --commit \
  --output reports/stage4-push-${TS3}.json
echo "exit=$?"
```

## Schema reporte JSON

```json
{
  "overall_pass": true,
  "run_started_at": "2026-05-06T...",
  "run_finished_at": "2026-05-06T...",
  "mode": "dry-run",
  "database_id": "e6817ec4-698a-4f0f-bbc8-fedcf4e52472",
  "data_source_id": "<resolved-in-phase-1>",
  "schema_observed": ["Name", "URL", "Canal", "..."],
  "schema_valid": true,
  "limit": null,
  "summary": {
    "pending_total": 20,
    "considered": 20,
    "created": 0,
    "skipped_existing": 0,
    "would_create": 20,
    "errored": 0
  },
  "rate_limit_sleep_ms": 350,
  "samples": {
    "created": [],
    "skipped_existing": [],
    "would_create": [
      {"sqlite_id": 123, "url_canonica": "https://...", "titulo": "..."}
    ],
    "errored": []
  }
}
```

`samples.*` truncados a 10 cada uno.

## Criterios de gate

**Dry-run:**

- exit `0`, `overall_pass: true`, `mode: "dry-run"`.
- `summary.created == 0`, `summary.skipped_existing == 0`, `summary.errored == 0`.
- `summary.would_create == summary.considered == min(pending_total, limit)`.
- `data_source_id` resuelto y registrado en el JSON.
- `schema_valid: true` (si false → ABORT, no progresar a commit).
- 0 mutaciones a SQLite (verificar `notion_page_id` count pre/post sin cambios).
- 0 HTTP calls a Notion en dry-run (verificable por mock en tests).

**Commit run `--limit 5`:**

- exit `0`, `overall_pass: true`, `mode: "commit"`.
- `summary.created + summary.skipped_existing == summary.considered` (idempotencia: ningún item queda sin clasificación).
- `summary.errored == 0` (cualquier error → abort y reporte humano antes de bulk).
- SQLite: 5 filas adicionales con `notion_page_id NOT NULL` (delta == created).
- Notion (verificación visual manual del usuario): 5 páginas nuevas con propiedades correctas.

**Re-run inmediato del mismo `--limit 5`:**

- `summary.created == 0`, `summary.skipped_existing == 5` (idempotencia: las 5 ya existen, query las encuentra, no se duplican).

**Tests unitarios:** `pytest tests/test_stage4_push_notion.py` todos verdes.

## Tests obligatorios (mínimo)

- `build_payload` produce dict con `properties.{Name|URL|Canal}` correctos (mock schema).
- `validate_schema` pasa con todas las required; aborta si falta una.
- `query_existing` con mock de Notion retorna page_id si filter response no vacío; None si vacío.
- `create_page` con mock retorna page_id; raises en 4xx/5xx no-429.
- 429 dispara backoff y reintenta.
- Dry-run NO llama a query_existing ni create_page (verificable: mock contado a 0 calls).
- `mark_persisted` UPDATE correcto en SQLite; no llama UPDATE en dry-run.
- Idempotencia: 2do run inmediato (mismo cache, mismo limit) clasifica todo como `skipped_existing`.
- Migration `ADD COLUMN notion_page_id`: idempotente (2do run no falla).

## Si falla

- **PR #317 no mergeado:** ABORT en Phase 0. No es un bug, es bloqueo.
- **0 ítems con `promovido_a_candidato_at NOT NULL`:** ABORT — re-correr Stage 3 commit. No promover desde acá.
- **Schema mismatch (property name no coincide):** ABORT, dump del schema observado vs el esperado. NO improvisar mapeo. Reportar al usuario para decidir si rename o crear properties faltantes.
- **`data_source_id` no presente en `databases.{id}`:** revisar que la integración Notion tenga permiso sobre la DB. Si no, registrar como `errored: integration_no_access`.
- **Rate-limit 429 persistente:** subir `--rate-limit-ms` a 500 o 1000 y re-run. No bypassear.
- **Notion devuelve schema inesperado para `relation Referente`:** dejar `Referente` vacío en payload, reportar como warning, NO abortar el item completo.

## Restricciones operacionales

- **Default dry-run obligatorio**. Si flag `--commit` ausente: 0 HTTP calls a Notion, 0 escrituras SQLite. Garantizado por código + test.
- **Token desde env var, NUNCA hardcoded ni logged**. `NOTION_API_KEY` solo en headers HTTP. Logs deben mostrar `Bearer ***REDACTED***` si se loggean headers.
- **Rate-limit nunca menor a 350 ms** entre HTTP calls. Configurable hacia arriba con `--rate-limit-ms`.
- **NO usar Notion MCP** — este script usa REST API directa con `NOTION_API_KEY`.
- **NO modificar páginas existentes** — solo crear nuevas. Si query encuentra match → skip + persistir page_id, no PATCH.
- **NO modificar el schema de la DB destino** — solo lee schema.
- **NO loggear payload completo de cada item** (puede contener URLs largas / títulos largos). Loggear solo `sqlite_id` + first 60 chars de título.

## Estructura del PR

Branch sugerida: `copilot-vps/feat-stage4-push-notion`.

Files esperados:

- `scripts/discovery/stage4_push_notion.py` (~350-500 LOC).
- `tests/test_stage4_push_notion.py` (~12-15 casos).
- `reports/stage4-push-<TS>.json` × 2 (dry-run + commit --limit 5). Bulk run JSON queda en una 2da PR si se hace después.
- Update este task file con sección `## Resultado YYYY-MM-DD`.

NO commitear:

- Cambios a SQLite (queda local).
- Modificaciones a `stage3_promote.py` ni a Stage 2.
- `NOTION_API_KEY` ni ningún token.
- Output de schema fetch crudo (`/tmp/stage4-db-meta.json` queda fuera del repo).

## Follow-up obligatorio (separado, NO en este PR)

Después del merge de este PR + bulk run exitoso, abrir issue / handoff para que `notion-governance` registre la DB destino en `vendor/notion-governance/registry/notion-data-sources.template.yaml`:

```yaml
publicaciones_candidatos_linkedin:
  title: "Candidatos publicación LinkedIn"
  database_id: "e6817ec4-698a-4f0f-bbc8-fedcf4e52472"
  data_source_id: "<resolved-in-phase-1>"
  status: "active"
  lifecycle_state: "active"
  layer: "operations_curated"
  runtime_notes:
    row_granularity: "one_candidato_editorial_per_row"
    populated_by:
      - repo: "umbral-agent-stack"
        script: "scripts/discovery/stage4_push_notion.py"
        first_population: "2026-MM-DD"
    consumers:
      - "rick-linkedin-writer (futuro)"
      - "rick-qa (futuro)"
      - "rick-orchestrator (futuro)"
```

Esto **NO bloquea** el merge de este PR — el script funciona sin la entrada en el registry. Es deuda de gobernanza que se cierra después.

## Reporte de cierre

Pegar abajo (sección `## Resultado YYYY-MM-DD`):

1. Hash commit del PR mergeado a main.
2. `data_source_id` resuelto.
3. Schema observado vs schema esperado (diff si hay).
4. Path de los JSON dry-run + commit --limit 5 (+ bulk si aplica).
5. Conteo SQLite pre y post commit-run: `notion_page_id NOT NULL`.
6. Conteo Notion pre y post commit-run (vía `POST /databases/{id}/data_sources/{ds}/query` con filter por fecha de creación, opcional).
7. Tests output.
8. Decisión: `PASS → Stage 4 cerrado, listo para Stage 5 (revisión humana / writer agent)` / `FAIL → razón + acción`.

## Quality gate

- [ ] PR #317 mergeado a main (Phase 0 verifica).
- [ ] `data_source_id` resuelto y registrado en JSON.
- [ ] Schema validado, mapeo concreto documentado.
- [ ] Migration `notion_page_id` aplicada idempotente.
- [ ] Script implementado con tests pasando.
- [ ] Smoke dry-run GREEN, 0 HTTP calls a Notion verificado, 0 mutaciones.
- [ ] Smoke commit `--limit 5` GREEN, 5 páginas creadas, 5 page_ids persistidos en SQLite.
- [ ] Verificación visual manual en Notion → go/no-go antes de bulk.
- [ ] (Si go) Bulk run GREEN, todos los pending procesados, 0 errored.
- [ ] Idempotency check: 2do run inmediato == todo skipped_existing.
- [ ] PR creado a main, mergeado tras review.
- [ ] Reporte pegado en este file.
- [ ] Working tree limpio (excepto cache local + reports JSON commiteados).
