# Task 013-C — Stage 2 (Fase C): Ingest script discovery via RSSHub + SQLite

- **Date:** 2026-05-06
- **Assigned to:** copilot-vps (codea + ejecuta smoke en VPS, mismo patrón que Task 012)
- **Type:** code + smoke run (Python script + ejecución live read-only)
- **Depends on:**
  - Task 012 GREEN (Stage 1 smoke `overall_pass: true`, commit `90f739c`).
  - Task 013-A GREEN (RSSHub container Up en `127.0.0.1:1200`, commit `02e9191`).
  - Snapshot vendored del registry: `vendor/notion-governance/registry/notion-data-sources.template.yaml` (entry `referencias_referentes`, `data_source_id afc8d960-086c-4878-b562-7511dd02ff76`).
  - Env worker con `NOTION_API_KEY` (mismo que usa Task 012).
- **Plan reference:** `docs/plans/linkedin-publication-pipeline.md` Etapa 1 + §11 items 5-7.
- **Session memory upstream (Copilot Chat):** `/memories/session/stage2-linkedin-pipeline-plan.md` (resumido abajo).
- **Status:** ready
- **Estimated effort:** 60-90 min (codear + smoke + iterar bugs RSSHub edge cases).

---

## Contexto resumido

Stage 2 del pipeline LinkedIn = **descubrir publicaciones nuevas por referente**. Stage 1 ya validó la lectura read-only de los 26 referentes con sus 10 columnas de canales. Fase A ya levantó RSSHub en VPS como adapter unificado.

Este task entrega:
1. **Script Python** `scripts/discovery/stage2_ingest.py` que:
   - Lee los 26 referentes de Notion (read-only, mismo patrón que `referentes_rest_read.py`).
   - Para cada referente, hace fan-out a los canales con URL poblada.
   - Fetch via RSSHub localhost (`http://127.0.0.1:1200/...`) o RSS directo según canal.
   - Escribe SQLite local: `~/.cache/rick-discovery/state.sqlite` (dedup + skip-if-recent).
   - Emite reporte JSON `reports/stage2-discovery-YYYYMMDDTHHMMSSZ.json`.
2. **Smoke live** ejecutado contra los 26 referentes reales, con criterios de gate definidos abajo.

**No-goals (explícitos):**
- NO promueve a candidatos en Notion (eso es Stage 3, separado).
- NO toca LinkedIn (cookie `li_at` viene de Fase B, ese task no existe aún).
- NO emite alertas, no escribe a webhooks, no manda emails.
- NO modifica el container RSSHub.

## Decisiones arquitectónicas (acordadas con David)

1. **Discovery directo cada corrida** + **skip-if-recent** (no re-fetch si el último éxito por (referente_id, canal) fue hace <30 min).
2. **Híbrido transversal**: TODOS los canales escriben a `fetch_log` con el mismo schema. Sin split por plataforma.
3. **Cache SQLite local en VPS** (no DB Notion nueva). Dedup por `url_canonica`.
4. **Canales activos en este task**:
   - `RSS feed` → fetch directo (si la URL ya es feed RSS).
   - `YouTube channel` → fetch via RSSHub `/youtube/channel/:id` (extraer `:id` de la URL del canal; si no se puede parsear, marcar `parse_error`).
   - `Web / Newsletter` → fetch directo SOLO si la URL termina en `/feed`, `/rss`, `.xml`, `.atom`. Si no, marcar `sin_acceso` (no inferir feed URL).
   - `LinkedIn activity feed` → marcar `sin_acceso` (Fase B no completa).
   - `Otros canales` → marcar `sin_acceso` (no estructurado en Stage 2).
5. **Cuando David provisione `YOUTUBE_API_KEY`** → swap futuro del adapter de YouTube. Por ahora todo YouTube va por RSSHub.
6. **No retries duros**: si un fetch falla con timeout o 5xx, marca `error` en `fetch_log` y sigue. El próximo run reintenta naturalmente.

## Schema SQLite (crear en primer run, idempotente)

```sql
-- ~/.cache/rick-discovery/state.sqlite
CREATE TABLE IF NOT EXISTS discovered_items (
  url_canonica       TEXT PRIMARY KEY,
  referente_id       TEXT NOT NULL,
  referente_nombre   TEXT NOT NULL,
  canal              TEXT NOT NULL,           -- 'rss' | 'youtube' | 'web_rss'
  titulo             TEXT,
  publicado_en       TEXT,                    -- ISO 8601, nullable si feed no expone
  primera_vez_visto  TEXT NOT NULL,           -- ISO 8601 UTC
  promovido_a_candidato_at TEXT                -- NULL en Stage 2
);

CREATE INDEX IF NOT EXISTS idx_discovered_referente ON discovered_items(referente_id, canal);

CREATE TABLE IF NOT EXISTS fetch_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  referente_id  TEXT NOT NULL,
  canal         TEXT NOT NULL,                -- 'rss' | 'youtube' | 'web_rss' | 'linkedin' | 'otros'
  fetched_at    TEXT NOT NULL,                -- ISO 8601 UTC
  status        TEXT NOT NULL,                -- 'ok' | 'skip_recent' | 'sin_acceso' | 'parse_error' | 'http_error' | 'timeout'
  items_found   INTEGER DEFAULT 0,
  error         TEXT                          -- mensaje resumido si status != ok
);

CREATE INDEX IF NOT EXISTS idx_fetch_log_recent ON fetch_log(referente_id, canal, fetched_at);
```

## URL canónica (dedup key)

Para evitar duplicados por variantes de URL (`?utm_*`, fragmentos, trailing slash), normalizar antes de insertar:

- Lowercase scheme + host.
- Strip query params que empiecen con `utm_`, `fbclid`, `gclid`, `ref`.
- Strip trailing slash en path (excepto path `/`).
- Strip fragment (`#...`).
- Para YouTube videos: usar siempre `https://www.youtube.com/watch?v=ID` aunque el feed devuelva `youtu.be/ID`.

## Comando de ejecución (smoke gate)

```bash
cd ~/umbral-agent-stack
source .venv/bin/activate
set -a && source ~/.config/openclaw/env && set +a
mkdir -p reports ~/.cache/rick-discovery
TS=$(date -u +%Y%m%dT%H%M%SZ)
python scripts/discovery/stage2_ingest.py \
  --registry vendor/notion-governance/registry/notion-data-sources.template.yaml \
  --rsshub-base http://127.0.0.1:1200 \
  --sqlite ~/.cache/rick-discovery/state.sqlite \
  --skip-recent-minutes 30 \
  --output reports/stage2-discovery-${TS}.json
echo "exit=$?"
```

## Schema reporte JSON

```json
{
  "overall_pass": true,
  "run_started_at": "2026-05-06T...",
  "run_finished_at": "2026-05-06T...",
  "registry": { "data_source_id": "afc8d960-086c-4878-b562-7511dd02ff76", "row_count": 26 },
  "rsshub_base": "http://127.0.0.1:1200",
  "skip_recent_minutes": 30,
  "summary": {
    "referentes_processed": 26,
    "channels_attempted": 0,
    "channels_ok": 0,
    "channels_skip_recent": 0,
    "channels_sin_acceso": 0,
    "channels_error": 0,
    "items_total_seen": 0,
    "items_new_this_run": 0
  },
  "per_referente": [
    {
      "referente_id_tail": "98249eb0",
      "nombre": "Alex Freberg",
      "channels": [
        {"canal": "rss", "status": "ok", "items_found": 12, "items_new": 12},
        {"canal": "youtube", "status": "ok", "items_found": 30, "items_new": 30},
        {"canal": "web_rss", "status": "sin_acceso", "items_found": 0, "items_new": 0},
        {"canal": "linkedin", "status": "sin_acceso", "items_found": 0, "items_new": 0}
      ]
    }
  ],
  "errors_sample": [
    {"referente_nombre": "...", "canal": "youtube", "error": "RSSHub HTTP 503 transient"}
  ]
}
```

(Truncar `per_referente` no es necesario — 26 filas es OK.)

## Criterios de gate (smoke GREEN)

- **Exit code:** `0`
- **`overall_pass`:** `true`
- **`registry.row_count`:** `26` (sanity check vs Stage 1).
- **`summary.referentes_processed`:** `26`.
- **`summary.channels_ok ≥ 5`** en el primer run (al menos 5 canales devolvieron ≥1 item; típicamente RSS + varios YouTube).
- **`summary.items_new_this_run ≥ 10`** en el primer run (cache vacía, primer fetch debe traer items).
- **NO excepciones no manejadas** (toda excepción debe terminar en `fetch_log.status = 'http_error'` o `'parse_error'` o `'timeout'`, no propagar).
- **SQLite creado** en `~/.cache/rick-discovery/state.sqlite` con ambas tablas.

## Criterios secundarios (informativos, no bloquean GREEN)

- 2do run inmediato (sin esperar 30 min): debe mostrar **`channels_skip_recent` alto** y `items_new_this_run` ≈ 0. Esto valida el skip-if-recent.
- 3er run con `--skip-recent-minutes 0`: debe re-fetchar todo y `items_new_this_run` ≈ 0 (todo ya en cache, dedup activo).

Estos 2 sub-runs son OPCIONALES en este task (se pueden hacer si hay tiempo, no son gate).

## Si falla

- **Notion auth fail (401/403):** mismo procedimiento que Task 012 (verificar env, no tocar Notion).
- **RSSHub no responde (`curl http://127.0.0.1:1200/` falla):** abortar, NO levantar el container desde este script (eso es Task 013-A). Notificar.
- **YouTube channel ID no parseable** desde URL: marcar `parse_error` por canal, seguir con los otros. NO bloquea overall si quedan ≥5 OK globales.
- **`overall_pass: false`**: pegar JSON completo, NO commitear el script si los bugs son del script. Si los bugs son data drift (URL inválida en Referentes), pegar y dejar a David.
- **Items cero en todos los canales:** muy raro post-Stage 1. Puede ser que las URLs de RSS feed sean inválidas (404/HTML en lugar de XML). Pegar 3 ejemplos en el reporte.

## Restricciones operacionales

- **NO** PATCH/POST/DELETE contra Notion (script read-only).
- **NO** escribir a Notion en este task (incluye no crear DB nueva, no tocar Publicaciones).
- **NO** abrir el puerto 1200 a la red pública (el bind debe seguir siendo `127.0.0.1`).
- **NO** loggear el `NOTION_API_KEY` ni cookies, ni emitirlo en el reporte.
- **NO** hacer >2 retries por canal en una corrida.
- **NO** dejar `git status` sucio al cerrar (excepto el reporte JSON y el script nuevo, que sí se commitean).

## Estructura del PR (qué commitear)

Branch sugerida: `copilot-vps/feat-stage2-ingest`.

Files esperados:
- `scripts/discovery/stage2_ingest.py` (nuevo, ~300-400 LOC).
- `scripts/discovery/__init__.py` (vacío, marca paquete si no existe).
- `tests/test_stage2_ingest_url_canonical.py` (unit tests para `canonicalize_url()` — 5-10 casos).
- `reports/stage2-discovery-YYYYMMDDTHHMMSSZ.json` (output del smoke).
- Update este task file con sección `## Resultado YYYY-MM-DD`.

NO commitear:
- `~/.cache/rick-discovery/state.sqlite` (queda local en VPS).
- Cambios a `vendor/notion-governance/`.
- Cambios al container RSSHub o a `worker/`.

Tests obligatorios (mínimo):
- `canonicalize_url` strip utm_*, fbclid, fragment, trailing slash.
- `canonicalize_url` normaliza youtu.be → youtube.com/watch?v=.
- `parse_youtube_channel_id` extrae ID de URLs `/channel/UC...` y `/c/Name` y `/@handle` (este último puede devolver None y emitir `parse_error`, OK).
- `should_skip_recent(last_fetched_at, threshold_minutes)` true/false según delta.
- Schema SQLite se crea idempotente (segunda llamada no falla).

## Reporte de cierre

Pegar abajo (sección `## Resultado YYYY-MM-DD`):

1. Hash del commit del PR mergeado a `main`.
2. Path del JSON generado.
3. JSON completo del reporte (puede ser largo, OK).
4. Conteo SQLite tras run: `sqlite3 ~/.cache/rick-discovery/state.sqlite "SELECT COUNT(*) FROM discovered_items; SELECT COUNT(*) FROM fetch_log;"`
5. Decisión: `PASS → Stage 2 cerrado, listo para Stage 3 (promoción a candidatos)` / `FAIL → razón + acción`.

## Quality gate

- [ ] Pre-checks (RSSHub Up, NOTION_API_KEY presente, SQLite path creable).
- [ ] Script implementado con tests unit pasando (`pytest tests/test_stage2_ingest_url_canonical.py`).
- [ ] Smoke live ejecutado, JSON generado, todos los criterios primarios GREEN.
- [ ] PR creado a `main`, mergeado tras review.
- [ ] Reporte pegado en este file.
- [ ] Repo VPS en `main`, working tree limpio (excepto cache local en `~/.cache/`).

---

## Resultado YYYY-MM-DD

(pendiente — completar tras ejecutar)
