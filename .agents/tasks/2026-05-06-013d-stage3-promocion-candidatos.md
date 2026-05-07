# Task 013-D — Stage 3: Promoción a candidatos (local, dry-run first)

- **Date:** 2026-05-06
- **Assigned to:** copilot-vps (codear + smoke en VPS, mismo patrón que Task 013-C)
- **Type:** code + smoke run (Python script + ejecución read-safe)
- **Depends on:**
  - Task 013-C GREEN (Stage 2 ingest cerrado, commit `81f8116`, PR #309 mergeado).
  - SQLite local poblada en `~/.cache/rick-discovery/state.sqlite` (≥400 items en `discovered_items`).
  - Schema actual: `discovered_items.promovido_a_candidato_at` nullable (definido en 013-C).
- **Plan reference:** `docs/plans/linkedin-publication-pipeline.md` Etapa 1 + §11 items 8-10.
- **Status:** ready
- **Estimated effort:** 60-90 min (codear + smoke dry-run + smoke commit + tests).

---

## Contexto

Stage 2 entregó descubrimiento de 437 items vía RSSHub + RSS directo, cacheados en SQLite local. **Stage 3 = filtrar y marcar candidatos elegibles** para revisión humana, sin escribir a Notion ni a sistemas externos.

Este task NO promueve a Notion (eso es Stage 4 separado). Solo trabaja sobre el cache local en VPS.

## Objetivo

Implementar `scripts/discovery/stage3_promote.py` que:

1. Lee items pendientes de `discovered_items` (`promovido_a_candidato_at IS NULL`).
2. Aplica reglas de elegibilidad v1 (definidas abajo).
3. Genera reporte JSON `reports/stage3-candidates-YYYYMMDDTHHMMSSZ.json` con candidatos + descartes clasificados.
4. **Default dry-run**: NO muta SQLite. Solo con flag explícito `--commit` marca `promovido_a_candidato_at = now()` para los elegibles.
5. Soporta `--limit N` para corridas controladas.

## No-goals (explícitos)

- NO escribe a Notion (ni read ni write — este task es 100% local).
- NO toca LinkedIn ni cookies.
- NO emite alertas ni mails ni webhooks.
- NO modifica el container RSSHub ni infra de Stage 2.
- NO modifica el schema SQLite (solo UPDATE en columna ya existente).
- NO crea DB nueva ni tabla nueva.

## Reglas de elegibilidad v1

Un item es **elegible** si cumple TODAS:

1. `publicado_en` parseable a datetime UTC (acepta RFC822 y ISO 8601; naive → asumir UTC).
2. `publicado_en` dentro de los últimos **90 días** desde now UTC.
3. `titulo` no vacío (después de `.strip()`).
4. `canal IN ('youtube', 'rss')` (otros canales no son válidos en v1).
5. `url_canonica` no vacía (ya garantizado por PK + dedup en Stage 2, sanity check).

Si alguna falla, el item se descarta con `reason` clasificado (whitelist cerrada):

- `fecha_invalida` — `publicado_en` no parseable o nulo.
- `fuera_ventana_90d` — fecha parseable pero > `max-age-days` desde now UTC.
- `titulo_vacio` — `titulo` nulo o vacío tras strip.
- `canal_no_elegible` — `canal` fuera de `{youtube, rss}`.
- `ya_promovido` — `promovido_a_candidato_at IS NOT NULL` (defensivo: el SELECT base ya filtra, pero clasificamos si se cuela).

## Comando de ejecución (smoke gate)

**Dry-run (default, gate primario):**

```bash
cd ~/umbral-agent-stack
source .venv/bin/activate
mkdir -p reports
TS=$(date -u +%Y%m%dT%H%M%SZ)
python scripts/discovery/stage3_promote.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --max-age-days 90 \
  --output reports/stage3-candidates-${TS}.json
echo "exit=$?"
```

**Commit run (gate secundario, valida mutación):**

```bash
TS2=$(date -u +%Y%m%dT%H%M%SZ)
python scripts/discovery/stage3_promote.py \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --max-age-days 90 \
  --commit \
  --limit 20 \
  --output reports/stage3-candidates-${TS2}.json
echo "exit=$?"
```

## Schema reporte JSON

```json
{
  "overall_pass": true,
  "run_started_at": "2026-05-06T...",
  "run_finished_at": "2026-05-06T...",
  "mode": "dry-run",
  "max_age_days": 90,
  "limit": null,
  "summary": {
    "pending_total": 437,
    "eligible": 0,
    "promoted_this_run": 0,
    "discarded_total": 0,
    "discarded_by_reason": {
      "fecha_invalida": 0,
      "fuera_ventana_90d": 0,
      "titulo_vacio": 0,
      "canal_no_elegible": 0,
      "ya_promovido": 0
    }
  },
  "candidates_sample": [
    {
      "url_canonica": "https://...",
      "referente_nombre": "...",
      "canal": "youtube",
      "titulo": "...",
      "publicado_en_iso": "2026-04-29T22:54:14Z",
      "age_days": 7
    }
  ],
  "discarded_sample": [
    {"url_canonica": "...", "reason": "stale", "age_days": 2500}
  ]
}
```

`candidates_sample` y `discarded_sample` truncados a 10 cada uno.

## Criterios de gate (smoke GREEN)

**Dry-run:**

- Exit code: `0`
- `overall_pass: true`
- `mode: "dry-run"`
- Consistencia interna: `summary.eligible + summary.discarded_total == summary.pending_total`.
- `summary.promoted_this_run == 0` (dry-run no muta).
- Cada item descartado tiene `reason ∈ {fecha_invalida, fuera_ventana_90d, titulo_vacio, canal_no_elegible, ya_promovido}`.
- Verificación post-run: `SELECT COUNT(*) FROM discovered_items WHERE promovido_a_candidato_at IS NOT NULL` == valor pre-run (sin cambios).
- Sin excepciones no manejadas.

**Commit run (`--commit --limit 20`):**

- Exit `0`, `overall_pass: true`, `mode: "commit"`.
- `summary.promoted_this_run == len(eligible_seleccionados)` (= min(eligible, limit)).
- Verificación post-run: delta de promovidos en SQLite == `summary.promoted_this_run`.
- Re-run con `--commit --limit 20`: NO re-promueve los ya marcados (idempotencia por SELECT base).

**Tests unitarios:** `pytest tests/test_stage3_promote.py` todos verdes.

## Si falla

- **SQLite no existe / vacía:** abortar con exit ≠0 antes de mutar nada.
- **Schema drift** (columna `promovido_a_candidato_at` ausente): abortar, NO crear schema.
- **`overall_pass: false`**: pegar JSON, no commitear si los bugs son del script.
- **0 elegibles**: investigar — puede ser parsing de fechas roto. Pegar 5 ejemplos de `publicado_en` raw del cache.

## Restricciones operacionales

- **Default dry-run obligatorio**: si el flag `--commit` no está, el script DEBE garantizar 0 escrituras.
- **NO** acceso a Notion (ni read ni write).
- **NO** acceso a red externa (script es 100% local sobre SQLite).
- **NO** loggear contenido sensible (no hay tokens en este flow, pero por hábito).
- **NO** modificar items con `promovido_a_candidato_at IS NOT NULL` (idempotencia: no re-promueve).
- **NO** dejar `git status` sucio (excepto reporte JSON y script nuevo, que se commitean).

## Estructura del PR

Branch sugerida: `copilot-vps/feat-stage3-promote`.

Files esperados:

- `scripts/discovery/stage3_promote.py` (nuevo, ~250-350 LOC).
- `tests/test_stage3_promote.py` (unit tests, 8-12 casos).
- `reports/stage3-candidates-YYYYMMDDTHHMMSSZ.json` (output del smoke dry-run).
- (Opcional) reporte adicional del commit-run con `--limit 20`.
- Update este task file con sección `## Resultado YYYY-MM-DD`.

NO commitear:

- Cambios a `~/.cache/rick-discovery/state.sqlite` (queda local).
- Cambios a `scripts/discovery/stage2_ingest.py` (no se toca).

Tests obligatorios (mínimo):

- `parse_pub_date` parsea RFC822 (`Wed, 29 Apr 2026 22:54:14 GMT`) → datetime UTC.
- `parse_pub_date` parsea ISO 8601 con/sin timezone.
- `parse_pub_date` devuelve None para input inválido.
- `is_eligible` true para item válido fresco; false para stale, no_title, unsupported_channel, no_pub_date.
- `select_pending` retorna solo items con `promovido_a_candidato_at IS NULL`.
- `mark_promoted` (modo commit) UPDATE correcto; dry-run no llama UPDATE.
- Idempotencia: 2do run dry-run inmediato produce mismo `eligible` count.

## Reporte de cierre

Pegar abajo (sección `## Resultado YYYY-MM-DD`):

1. Hash commit del PR mergeado a main.
2. Path del JSON dry-run + JSON commit-run.
3. Conteo SQLite pre y post commit-run: pending vs promovidos.
4. Tests output.
5. Decisión: `PASS → Stage 3 cerrado, listo para Stage 4 (push a Notion)` / `FAIL → razón + acción`.

## Quality gate

- [ ] Pre-checks (SQLite existe, schema OK, ≥400 pending).
- [ ] Script implementado con tests pasando (`pytest tests/test_stage3_promote.py`).
- [ ] Smoke dry-run GREEN, JSON generado, 0 mutaciones verificadas.
- [ ] Smoke commit-run GREEN con `--limit 20`, mutaciones verificadas.
- [ ] PR creado a main, mergeado tras review.
- [ ] Reporte pegado en este file.
- [ ] Working tree limpio (excepto cache local).

---

## Resultado 2026-05-06

**PASS — gate GREEN (dry-run + commit)**

- Branch: `copilot-vps/feat-stage3-promote`
- Commit feat: `479a20b` (squash merge en main: `d9e1fc5`)
- PR código: https://github.com/Umbral-Bot/umbral-agent-stack/pull/313 (MERGED)
- Reportes JSON:
  - Dry-run: `reports/stage3-candidates-20260506T232547Z.json`
  - Commit (--limit 20): `reports/stage3-candidates-20260506T232556Z.json`
- Tests unitarios: **22 passed** (`tests/test_stage3_promote.py`)

### Gate criteria

| criterio | run dry-run | run commit (--limit 20) | resultado |
|---|---|---|---|
| exit code | 0 | 0 | PASS |
| overall_pass | true | true | PASS |
| mode | dry-run | commit | PASS |
| pending_total | 437 | 437 | OK |
| eligible | 161 | 161 | OK |
| discarded_total | 276 | 276 | OK |
| eligible + discarded == pending | 437 == 437 | 437 == 437 | PASS |
| promoted_this_run | 0 | 20 | PASS |
| promoted_this_run == len(seleccionados) | 0 == 0 | 20 == min(161,20) | PASS |
| reasons whitelist cerrada | sí | sí | PASS |
| SQLite delta promovidos pre→post | 0 → 0 | 0 → 20 (delta 20) | PASS |

### Discarded by reason (idénticos en ambos runs)

| reason | count |
|---|---|
| `fecha_invalida` | 0 |
| `fuera_ventana_90d` | 276 |
| `titulo_vacio` | 0 |
| `canal_no_elegible` | 0 |
| `ya_promovido` | 0 |

Los 276 descartes son items históricos (publicados antes de feb 2026) — esperable dado que el cache traía feeds RSS/YouTube con histórico largo.

### SQLite verification

```
pre  commit run: SELECT COUNT(*) WHERE promovido_a_candidato_at IS NOT NULL → 0
post commit run: SELECT COUNT(*) WHERE promovido_a_candidato_at IS NOT NULL → 20
delta = 20 (== summary.promoted_this_run)
```

### Notas

- Dry-run es estrictamente read-only: verificado con `SELECT COUNT(...) IS NOT NULL` pre y post (ambos == 0).
- `--limit 20` aplica DESPUÉS del filtro de elegibilidad y del orden determinista (`publicado_en DESC, url_canonica ASC`).
- Idempotencia validada por test `test_idempotent_commit`: 2do `--commit` ve 0 pending → 0 promoted.
- Drift defensa: `assert_schema` aborta con `Stage3Error` si falta la columna `promovido_a_candidato_at` (test `test_drift_missing_column_aborts`).
- Restricciones respetadas: 0 escrituras a Notion, 0 acceso a red, RSSHub no tocado, Stage 2 intacto.
- Working tree del VPS: 2 archivos ajenos pre-existentes (`docs/ops/notion-poll-comments-sev1-triage-2026-05-05.md`, `scripts/vps/check-notion-poller.sh`) — no tocados.

**Decisión:** PASS → Stage 3 cerrado. Listo para Stage 4 (push a Notion de los 20 candidatos ya marcados localmente, o re-run con `--limit` mayor antes de Stage 4).
