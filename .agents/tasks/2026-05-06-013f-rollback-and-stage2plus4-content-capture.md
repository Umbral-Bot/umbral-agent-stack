# Task 013-F — Rollback Stage 4 + Stage 2 content capture + Stage 4 retarget

- **Date:** 2026-05-06
- **Assigned to:** copilot-vps (codear, testear, ejecutar smoke en VPS).
- **Type:** rollback + code (Stage 2 extension) + code (Stage 4 refactor) + smoke runs.
- **Depends on:**
  - Task 013-E mergeada (PR #323 de 013-E NO se mergea — se cierra).
  - SQLite local `~/.cache/rick-discovery/state.sqlite` con los 20 ítems promovidos y 5 con `notion_page_id` poblado.
  - `NOTION_API_KEY` disponible en `~/.config/openclaw/env` (Rick scope).
- **Plan reference:** `docs/plans/linkedin-publication-pipeline.md` (Etapa 1 — replanteo del destino).
- **Status:** ready.
- **Estimated effort:** 4–6 h (Stage 2 schema migration + content extractor + Stage 4 refactor + tests + 3 smoke runs).

---

## Contexto y motivación

Task 013-E entregó un script Stage 4 funcional, pero **el output fue rechazado por el owner** porque:

1. **DB destino equivocada**: las 5 páginas creadas aterrizaron en `Publicaciones` (DB editorial humana, workflow Idea→Publicado). Esa DB es para **propuestas elaboradas por David**, no para **referencias externas** descubiertas por el pipeline. Mezcla pollution editorial con discovery.
2. **Canal hardcodeado**: el script puso `Canal=linkedin` en todos los ítems aunque varios son YouTube. Stage 3 promovió contenido heterogéneo y el mapeo del 013-E no leyó el campo `canal` real desde SQLite.
3. **Notas con formato improvisado**: `[ref: X | sqlite: Y]` mete metadatos en un campo libre. La nueva DB tiene properties dedicadas.
4. **idempotency_key como rich_text duplicando URL**: ruido visual y redundante.
5. **Páginas sin contenido útil**: solo título + propiedades. El owner necesita revisar el material adentro de Notion sin tener que abrir cada link externo. **El cuerpo de página debe contener el texto completo de la publicación** (post LinkedIn, transcript YouTube, body blog, descripción podcast), no solo el título.

## Decisión del owner (ya tomada, no re-discutir)

- DB destino correcta: **`📰 Publicaciones de Referentes`** — creada como hermana de `👤 Referentes` bajo la página `Referencias`.
  - **database_id**: `b9d3d8677b1e4247bafdcb0cc6f53024`
  - **data_source_id**: `9d4dbf65-664f-41b4-a7f6-ce378c274761`
  - **URL**: https://www.notion.so/b9d3d8677b1e4247bafdcb0cc6f53024
- **Schema** (ya creado, NO modificar):

  | Property | Tipo | Notas |
  |---|---|---|
  | `Título` | `title` | required |
  | `Enlace` | `url` | required, URL canónica del item |
  | `Canal` | `select` | options: `youtube`, `linkedin`, `x`, `blog`, `podcast`, `newsletter`, `otro` |
  | `Referente` | `relation → Referentes (afc8d960-086c-4878-b562-7511dd02ff76)` | resolver por nombre |
  | `Fecha publicación` | `date` | opcional |
  | `Estado revisión` | `select` | constante `Sin revisar` al crear |
  | `Sqlite ID` | `number` | trazabilidad reversa |
  | `Creado por sistema` | `checkbox` | `true` |
  | `idempotency_key` | `rich_text` | URL canónica para lookup; campo "interno" — el owner lo va a ocultar en la UI |

- **Cuerpo de página**: contenido completo de la publicación, capturado por Stage 2 desde el feed RSS y volcado en Stage 4 como bloques markdown.

## Páginas a archivar (rollback)

Las 5 páginas creadas por 013-E en la DB equivocada deben ser **archivadas** (PATCH `archived: true`, NO delete duro — quedan recuperables 30 días):

| sqlite_id | notion_page_id |
|---|---|
| 31 | `3595f443-fb5c-816b-8970-c7be73118f1a` |
| 33 | `3595f443-fb5c-817e-8f17-ebcd2d88be56` |
| 32 | `3595f443-fb5c-8100-ab5f-c7e80512e925` |
| 1  | `3595f443-fb5c-8177-9fac-d45e6013b036` |
| 408 | `3595f443-fb5c-8122-af4b-d55812ae388c` |

URLs (verificación visual antes/después):

- https://www.notion.so/Nuevo-Episodio-La-universidad-ya-no-sirve-para-esto-3595f443fb5c816b8970c7be73118f1a
- https://www.notion.so/Nuevo-Episodio-Si-la-IA-es-tan-buena-para-qu-servimos-los-humanos-3595f443fb5c817e8f17ebcd2d88be56
- https://www.notion.so/Quisiera-Ser-Yo-Resumen-Resumido-179-3595f443fb5c8100ab5fc7e80512e925
- https://www.notion.so/SWDchallenge-human-AI-3595f443fb5c81779facd45e6013b036
- https://www.notion.so/Existen-Fisuras-en-el-Universo-3595f443fb5c8122af4bd55812ae388c

## No-goals (explícitos)

- NO modificar el schema de la DB nueva `📰 Publicaciones de Referentes` (ya creada por el coordinador). Si Phase 1 detecta diff vs el schema documentado arriba → ABORT.
- NO tocar `Publicaciones` (DB editorial humana) — solo archivar las 5 páginas listadas.
- NO escribir a LinkedIn ni redes sociales.
- NO usar Notion MCP (REST API directa con `NOTION_API_KEY`).
- NO modificar `notion-governance` (registry update va en PR aparte).
- NO promover ítems nuevos en Stage 3 (los 20 actuales ya promovidos son la cohorte de prueba).
- NO mergear PR #323 (cerrar sin merge).

---

## Phases

### Phase 0 — Pre-checks (abort early)

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main

source .venv/bin/activate
test -s ~/.cache/rick-discovery/state.sqlite || { echo "ABORT: sqlite vacía"; exit 1; }

# Confirmar 20 promovidos y 5 con notion_page_id
sqlite3 ~/.cache/rick-discovery/state.sqlite "SELECT COUNT(*) FROM discovered_items WHERE promovido_a_candidato_at IS NOT NULL;"
# Esperado: 20
sqlite3 ~/.cache/rick-discovery/state.sqlite "SELECT COUNT(*) FROM discovered_items WHERE notion_page_id IS NOT NULL;"
# Esperado: 5

test -n "$(grep -E '^NOTION_API_KEY=' ~/.config/openclaw/env)" || { echo "ABORT: NOTION_API_KEY ausente"; exit 1; }

# Schema check de la DB nueva
source <(grep -E '^NOTION_API_KEY=' ~/.config/openclaw/env | sed 's/^/export /')
DB_NEW="b9d3d8677b1e4247bafdcb0cc6f53024"
DS_NEW="9d4dbf65-664f-41b4-a7f6-ce378c274761"
curl -s "https://api.notion.com/v1/databases/${DB_NEW}" \
  -H "Authorization: Bearer ${NOTION_API_KEY}" \
  -H "Notion-Version: 2025-09-03" \
  | jq '{id, title: .title[0].plain_text, data_sources: [.data_sources[].id], properties: (.properties | keys)}'
# Esperado: data_sources contiene "9d4dbf65-664f-41b4-a7f6-ce378c274761"
# Esperado: properties incluye exactamente: Título, Enlace, Canal, Referente, Fecha publicación, Estado revisión, Sqlite ID, Creado por sistema, idempotency_key
# Si diff → ABORT, reportar al coordinador.
```

### Phase 1 — Rollback de las 5 páginas en DB equivocada

Branch dedicada: `copilot-vps/rollback-013e-and-013f-content-capture`.

```bash
git checkout -b copilot-vps/rollback-013e-and-013f-content-capture

# Script one-shot (NO commitear, ejecutar inline)
PAGES=(
  "3595f443-fb5c-816b-8970-c7be73118f1a"
  "3595f443-fb5c-817e-8f17-ebcd2d88be56"
  "3595f443-fb5c-8100-ab5f-c7e80512e925"
  "3595f443-fb5c-8177-9fac-d45e6013b036"
  "3595f443-fb5c-8122-af4b-d55812ae388c"
)
for pid in "${PAGES[@]}"; do
  echo "Archiving ${pid}..."
  curl -s -X PATCH "https://api.notion.com/v1/pages/${pid}" \
    -H "Authorization: Bearer ${NOTION_API_KEY}" \
    -H "Notion-Version: 2025-09-03" \
    -H "Content-Type: application/json" \
    -d '{"archived": true}' \
    | jq '{id, archived}'
  sleep 0.4
done

# Reset SQLite
sqlite3 ~/.cache/rick-discovery/state.sqlite \
  "UPDATE discovered_items SET notion_page_id = NULL WHERE rowid IN (1, 31, 32, 33, 408);"
sqlite3 ~/.cache/rick-discovery/state.sqlite \
  "SELECT COUNT(*) FROM discovered_items WHERE notion_page_id IS NOT NULL;"
# Esperado: 0
```

**Cierre de PR #323 (desde la VPS con `gh`):**

```bash
gh pr close 323 --comment "Closing without merge — Stage 4 retargeted to new DB '📰 Publicaciones de Referentes' in task 013-F. The 5 pages created by this PR's run have been archived in Notion and notion_page_id reset in SQLite."
```

### Phase 2 — Stage 2 extension: capturar contenido completo

Objetivo: agregar columna `contenido_html` (texto completo del item, lo que el feed expone) a `discovered_items`, y poblarla en cada nuevo fetch + backfill para los 20 actuales.

#### 2.1 — SQLite migration (idempotente)

```python
# En stage2_ingest.py o script de migration dedicado:
ALTER TABLE discovered_items ADD COLUMN contenido_html TEXT NULL;
ALTER TABLE discovered_items ADD COLUMN contenido_extraido_at TEXT NULL;  -- ISO-8601
```

PRAGMA-guard idéntico al de `notion_page_id` en 013-E.

#### 2.2 — Extractor

En `scripts/discovery/stage2_ingest.py` (o módulo helper nuevo `scripts/discovery/content_extractor.py`):

- Para cada item RSS leído:
  - Si el feed expone `<content:encoded>` → usar ese (HTML).
  - Else si expone `<description>` → usar ese.
  - Else fallback: solo `titulo` (campo queda NULL, marcar `contenido_extraido_at` igual con `null` source).
- Persistir como **HTML crudo** en `contenido_html`. Stage 4 hace la conversión a markdown (separación de responsabilidades).
- **NO** hacer scraping HTTP de la URL canónica — solo lo que el feed entregue. (Si el item no tiene contenido en el feed, queda NULL y Stage 4 inserta solo el link sin body.)

#### 2.3 — Backfill de los 20 actuales

Script one-shot `scripts/discovery/backfill_content_for_promoted.py`:

- Lee los 20 ítems con `promovido_a_candidato_at IS NOT NULL AND contenido_html IS NULL`.
- Re-fetchea el feed correspondiente (mismo path RSSHub o RSS directo que Stage 2 usó).
- Match por `url_canonica` con los items del feed; copia `<content:encoded>` o `<description>` a `contenido_html`.
- Si no hay match (item rotado fuera del feed): deja NULL y reporta en el JSON output como `backfill_missed`.

Ejecutar **una sola vez** post-merge de este PR.

### Phase 3 — Stage 4 refactor

Reescritura mínima de `scripts/discovery/stage4_push_notion.py` con cambios:

#### Cambios a la lógica

| Aspecto | 013-E (viejo) | 013-F (nuevo) |
|---|---|---|
| `--database-id` default | `e6817ec4-…` | `b9d3d8677b1e4247bafdcb0cc6f53024` |
| `--data-source-id` flag | resuelto por curl | acepta override; default `9d4dbf65-664f-41b4-a7f6-ce378c274761` |
| Property `Título` | `titulo` | `titulo` (igual) |
| Property `URL` | `Fuente primaria` | `Enlace` (renombrada) |
| Property `Canal` | constante `linkedin` | `item.canal` real desde SQLite |
| Property `Referente` | omitida (rich_text en Notas) | **relation lookup por nombre** (ver §3.1) |
| Property `Fecha publicación` | sí | sí (igual) |
| Property `Notas` | `[ref: X \| sqlite: Y]` | **eliminada del payload** (sqlite_id va en property dedicada) |
| Property `Sqlite ID` | no | `item.sqlite_id` (number) |
| Property `Estado` (status) | `Idea` | **NO se escribe** (la DB nueva usa `Estado revisión` select, no status) |
| Property `Estado revisión` | no | constante `Sin revisar` |
| Property `Creado por sistema` | `true` | `true` (igual) |
| Property `idempotency_key` | `url_canonica` | `url_canonica` (igual, para lookup) |
| Cuerpo de página | vacío | **contenido_html convertido a markdown** (ver §3.2) |
| Lookup idempotente | filter `idempotency_key` exact-match | **igual** (sigue siendo el mecanismo más confiable) |

#### 3.1 — Resolución de relation `Referente`

- Cache UNA vez al inicio del run: `data_source_referentes_id = afc8d960-086c-4878-b562-7511dd02ff76`.
- `POST /v1/data_sources/{id}/query` paginando hasta agotar; construir dict `{ nombre.lower().strip(): page_id }`.
- Para cada item: `match = referentes_dict.get(item.referente_nombre.lower().strip())`.
  - Si match → `properties.Referente = {"relation": [{"id": match}]}`.
  - Si no match → log warning, dejar `Referente` vacío, **no abortar** el item. Reportar en samples como `referente_unmatched`.

#### 3.2 — Conversión `contenido_html` → bloques Notion

Notion API acepta `children` en `POST /pages` (max 100 bloques por request).

- Si `item.contenido_html` es NULL → solo crear página con properties (sin children).
- Si NO NULL:
  - Convertir HTML → markdown con `markdownify` (agregar a `pyproject.toml` si no está).
  - Convertir markdown → bloques Notion. Helper mínimo aceptable:
    - Párrafos `<p>` → `paragraph` block.
    - `<h1>/<h2>/<h3>` → `heading_1/2/3`.
    - `<ul>/<ol>` → `bulleted_list_item` / `numbered_list_item`.
    - `<a href="X">text</a>` → rich_text con `link.url = X`.
    - `<img src="X">` → `image` block (external URL).
    - Resto → degradar a `paragraph` con texto plano.
  - **Truncar a 90 bloques** (margen de 10 sobre el límite 100); si se excede, último bloque es `paragraph` con texto literal `[…contenido truncado, ver enlace original…]`.
  - **Chunkear cada `rich_text` a 1900 caracteres** (límite Notion 2000, margen).

Si la conversión falla (excepción): log warning + crear página solo con properties + 1 paragraph block con `Contenido no disponible (error de conversión, ver Enlace).` Classificar como `created_no_body`.

#### 3.3 — Reglas duras (sin cambios vs 013-E)

- Default dry-run obligatorio. En dry-run: 0 HTTP calls a Notion (incluyendo el query a Referentes).
- Rate-limit: 350 ms entre HTTP calls.
- 429 backoff: 1s/2s/4s/8s, abort tras 4 retries.
- 4xx/5xx no-429: log + continuar; abort total tras 3 errores consecutivos.
- Schema fetch UNA vez al inicio (cached).
- Token redacted en logs.

### Phase 4 — Smoke runs

#### 4.1 — Dry-run

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p reports
python scripts/discovery/stage4_push_notion.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --database-id b9d3d8677b1e4247bafdcb0cc6f53024 \
  --data-source-id 9d4dbf65-664f-41b4-a7f6-ce378c274761 \
  --output reports/stage4-push-${TS}-dryrun.json
```

Esperado: `would_create == 20`, `created == 0`, `errored == 0`, 0 HTTP calls.

#### 4.2 — Backfill content (one-shot)

```bash
TS_BF=$(date -u +%Y%m%dT%H%M%SZ)
python scripts/discovery/backfill_content_for_promoted.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --output reports/backfill-content-${TS_BF}.json
sqlite3 ~/.cache/rick-discovery/state.sqlite \
  "SELECT COUNT(*) FROM discovered_items WHERE promovido_a_candidato_at IS NOT NULL AND contenido_html IS NOT NULL;"
# Esperado: cerca de 20 (algunos pueden quedar sin contenido si el feed rotó).
```

#### 4.3 — Commit run controlado (5 ítems primero)

Re-pushear los 5 que fueron archivados (sus SQLite rows ya tienen `notion_page_id = NULL` post-rollback):

```bash
TS2=$(date -u +%Y%m%dT%H%M%SZ)
python scripts/discovery/stage4_push_notion.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --database-id b9d3d8677b1e4247bafdcb0cc6f53024 \
  --data-source-id 9d4dbf65-664f-41b4-a7f6-ce378c274761 \
  --commit \
  --limit 5 \
  --output reports/stage4-push-${TS2}-commit5.json
```

**STOP aquí. Reportar al coordinador con:**

- Las 5 URLs nuevas creadas en `📰 Publicaciones de Referentes`.
- Conteo de bloques en cada página (vía `GET /v1/blocks/{page_id}/children` o visual).
- Sample de cómo se ven Canal + Referente + Fecha publicación + body.

**No avanzar a 4.4 sin go/no-go del coordinador.**

#### 4.4 — Commit bulk (los 15 restantes)

Solo tras go/no-go:

```bash
TS3=$(date -u +%Y%m%dT%H%M%SZ)
python scripts/discovery/stage4_push_notion.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --database-id b9d3d8677b1e4247bafdcb0cc6f53024 \
  --data-source-id 9d4dbf65-664f-41b4-a7f6-ce378c274761 \
  --commit \
  --output reports/stage4-push-${TS3}-bulk.json
```

#### 4.5 — Re-run idempotencia

```bash
python scripts/discovery/stage4_push_notion.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --database-id b9d3d8677b1e4247bafdcb0cc6f53024 \
  --data-source-id 9d4dbf65-664f-41b4-a7f6-ce378c274761 \
  --commit \
  --output reports/stage4-push-rerun-idempotency.json
# Esperado: created == 0, skipped_existing == 20.
```

---

## Tests obligatorios

Reescribir `tests/test_stage4_push_notion.py` cubriendo:

- `build_payload`:
  - Property names del schema nuevo (`Título`, `Enlace`, `Canal`, `Referente`, `Fecha publicación`, `Estado revisión`, `Sqlite ID`, `Creado por sistema`, `idempotency_key`).
  - `Canal` se lee de `item.canal`, NO hardcoded.
  - `Referente` con relation cuando hay match; vacío cuando no hay match.
  - `Estado revisión = "Sin revisar"`, `Creado por sistema = true`.
- `validate_schema`:
  - Aborta si falta cualquiera de las 9 properties.
  - Aborta si `Canal` no tiene la option correspondiente al `item.canal`.
- `build_referentes_index`: dict construido correctamente desde mock paginado.
- `html_to_blocks`:
  - Párrafos, headings, listas, links, images.
  - Truncado a 90 bloques.
  - Chunkeado de rich_text a 1900 chars.
  - Fallback a `created_no_body` si excepción.
- `query_existing` por `idempotency_key` exact-match.
- 429 backoff.
- Dry-run NO llama HTTP (mock counter == 0).
- `mark_persisted`: UPDATE solo en commit.
- Migration `ADD COLUMN contenido_html` y `contenido_extraido_at`: idempotente.

Stage 2 extension:

- `tests/test_stage2_content_extraction.py`: extractor lee `<content:encoded>` preferentemente, fallback a `<description>`, fallback a NULL.

---

## Schema reporte JSON (sin cambios estructurales vs 013-E)

Agregar al `summary`:

```json
{
  "summary": {
    "pending_total": 20,
    "considered": 20,
    "created": 5,
    "created_no_body": 0,
    "skipped_existing": 0,
    "would_create": 0,
    "errored": 0,
    "referente_unmatched": 0
  }
}
```

---

## Estructura del PR

Branch: `copilot-vps/rollback-013e-and-013f-content-capture`.

Files esperados:

- `scripts/discovery/stage2_ingest.py` (extension content_html + migration).
- `scripts/discovery/content_extractor.py` (helper opcional).
- `scripts/discovery/backfill_content_for_promoted.py` (one-shot).
- `scripts/discovery/stage4_push_notion.py` (refactor).
- `scripts/discovery/html_to_notion_blocks.py` (helper conversión).
- `tests/test_stage4_push_notion.py` (reescrito).
- `tests/test_stage2_content_extraction.py` (nuevo).
- `tests/test_html_to_notion_blocks.py` (nuevo).
- `reports/stage4-push-<TS>-dryrun.json`.
- `reports/backfill-content-<TS>.json`.
- `reports/stage4-push-<TS>-commit5.json`.
- `reports/stage4-push-<TS>-bulk.json` (si Phase 4.4 ejecutada).
- `pyproject.toml` (agregar `markdownify` como dep).
- Update este task file con sección `## Resultado YYYY-MM-DD`.

NO commitear:

- Cambios SQLite (queda local en VPS).
- `NOTION_API_KEY` ni nada que la contenga.
- Schema dump crudo en `/tmp/`.

---

## Reporte de cierre

Pegar abajo (sección `## Resultado YYYY-MM-DD`):

1. Hash commit del PR mergeado a main.
2. Confirmación de las 5 páginas archivadas (output del PATCH para cada una).
3. Confirmación cierre PR #323 (link al close comment).
4. Conteo SQLite: `notion_page_id NOT NULL` pre y post; `contenido_html NOT NULL` pre y post backfill.
5. Schema observado de la DB nueva vs documentado (diff si hay).
6. Path de los 4 JSON reports.
7. Las 5 URLs creadas en Phase 4.3 + sample de body rendering.
8. Resultado de Phase 4.5 (re-run idempotencia: skipped == 20 esperado).
9. Tests output (`pytest tests/test_stage4_push_notion.py tests/test_stage2_content_extraction.py tests/test_html_to_notion_blocks.py -v`).
10. Decisión: PASS / FAIL + acción.

---

## Quality gate

- [ ] 5 páginas archivadas en `Publicaciones`, verificado por GET (archived: true).
- [ ] PR #323 cerrado sin merge.
- [ ] Stage 2 captura `contenido_html` en runs futuros.
- [ ] Backfill llenó contenido_html para ≥80% de los 20 promovidos.
- [ ] Schema validation aborta cleanly si DB nueva tiene drift.
- [ ] Dry-run con 0 HTTP calls.
- [ ] Commit --limit 5 crea 5 páginas con body markdown legible.
- [ ] Owner aprueba sample antes de bulk.
- [ ] Bulk run completa los 20 sin errores no recuperables.
- [ ] Re-run idempotencia: 20 skipped, 0 created.
- [ ] Todos los tests verdes.
- [ ] Coordinador (Copilot Chat Windows) puede actualizar `notion-governance/registry/` con la nueva DB en PR aparte (follow-up, no bloqueante).
