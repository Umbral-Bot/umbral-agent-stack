# PKG-UAS-PANEL-4-CLOSEOUT — Clasificación de las 4 child_pages de contenido (2026-08-10)

> **Pack:** PKG-UAS-PANEL-4-CLOSEOUT · rama `claude/pkg-uas-panel-4-closeout-20260810` ·
> base `adba424` (`origin/main`, tip = PR #621)
> **Evidencia:** `~/.coord-ag-evidence/uas-panel-4-closeout-20260810/` (sin secretos)
> **Read-only:** nada de Notion fue mutado en este pack. Solo GETs + un query de DB
> (lectura). Las 4 páginas siguen intactas; la decisión final es de David, fila a fila.

## Contexto

Tras el drenaje de Heartbeats (#617/#618) y el corte del productor (#619, opción a),
el residual esperado del panel Control Room son exactamente **4 child_pages de
contenido legítimo** que el cleanup no toca por diseño (no matchean
`_RESIDUAL_CHILD_PAGE_PREFIXES` — test explícito en `tests/test_openclaw_panel.py`).
Este pack las inventaría en profundidad y propone destino; no ejecuta ninguno.

Método: mismos helpers del panel (`scripts/openclaw_panel_vps.py`:
`OPENCLAW_PAGE_ID`, `_list_children`, `_is_residual_child_page`,
`_is_allowed_nav_child_page`, `validate_openclaw_shell`) vía probe read-only
(`panel4_probe.py`, copia en evidencia). Sin client nuevo.

## Fase A — Snapshot live del panel (2026-08-10T21:03:23Z)

| Métrica | Valor |
|---|---|
| Blocks totales en Control Room | 29 |
| `child_page` totales | 7 |
| Allowed nav (`Dashboard Rick`, `Alertas del Supervisor`) | 2 |
| Residuales (criterio `validate_openclaw_shell`) | **5** |
| — de contenido (no matchean prefijo) | **4** |
| — Heartbeat (matchea prefijo, pendiente de cleanup) | 1 (`Heartbeat Rick — 2026-08-10 16:33 UTC`, id `3b85f443-fb5c-81ae-9cab-d1ecbe05666e`) |
| `validation.ok` | `false` (solo por residuales) |

Evidencia: `panel_children_summary.json`, `content_pages_detail.json`,
`bitacora_child_db_rows.json`, `cron_schedule_analysis.txt`.

## Fase A — Tabla de clasificación 4/4

Las cuatro comparten: `archived = N`, `in_trash = N`, parent = Control Room
(`30c5f443-fb5c-80ee-b721-dc5727b20dca`) = **Y**, en allowed set hoy = **N**
(el allowed set es `{Dashboard Rick, Alertas del Supervisor}`), matchean prefijo
residual = **N** (por eso el cleanup nunca las archivará — comportamiento correcto).

### 1. Bitácora Plan Q2-2026 — RECOMENDACIÓN: **MOVE** → child de `Dashboard Rick`

| Campo | Valor |
|---|---|
| page_id | `0d4aa522-77f1-428f-8002-6ee33082f69e` |
| created / last_edited | 2026-04-30T10:18Z / 2026-04-30T10:29Z |

Qué es: registro append-only del Plan Q2-2026 (espejo declarado de
`docs/roadmap/12-q2-2026-platform-first-plan.md` del repo `notion-governance`).
Contiene la child_database **"Entradas Bitácora" con 23 filas reales** (cierres de
O1–O4, skills-registry, backups del registry — historial de gobernanza genuino) más
un checklist Q2 espejo con toggles por objetivo.

Links/backlinks: referenciada por `docs/audits/sys-diag-inputs/2026-07-17/02-notion-ai.md`
(diagnóstico de sistema de julio) — el único de los 4 con backlink en los repos.

Justificación (una frase): historial de gobernanza con datos reales que merece seguir
accesible, pero es material técnico/histórico, no panel David-facing — moverlo bajo
`Dashboard Rick` (`3265f443-fb5c-816d-9ce8-c5d6cf075f9c`) limpia Control Room sin
perder el registro.

- Evidencia: 23 filas en la DB (`bitacora_child_db_rows.json`); backlink del audit.
- Inferencia: dormida desde abril (last_edited del page container; las ediciones de
  filas de la child DB no actualizan ese campo, pero los títulos de las filas cierran
  en O1–O4/Q2, coherente con quarter terminado).
- Mecánica: mover parent es ejecutable vía Notion MCP `notion-move-pages` en el pack
  de ejecución (la API pública clásica no cambia parents; el MCP sí lo soporta).

### 2. SIM Daily Report 2026-05-07 — RECOMENDACIÓN: **ARCHIVE**

| Campo | Valor |
|---|---|
| page_id | `3595f443-fb5c-8110-9ab8-c2e9efd37a5c` |
| created / last_edited | 2026-05-07T21:39Z / 2026-05-07T21:39Z (nunca editada) |

Qué es: snapshot one-shot de telemetría SIM — conteos de `research.web` /
`llm.generate` (274/136 en ventana 168h), lista de URLs de research y un resumen LLM
de tendencias BIM. Producida por `scripts/sim_daily_report.py`.

Links/backlinks: ninguno hacia la página; el script y sus tests viven en el repo.

Justificación: telemetría pura fechada (mayo) en superficie David-facing — viola la
regla "no telemetría en Notion" y su valor informativo ya expiró; archive es
reversible desde la papelera.

- Evidencia: contenido 100% telemetría/telaraña de URLs; sin ediciones desde creación;
  `sim_daily_report` no aparece en el crontab actual.
- Inferencia: productor inactivo (ausencia en crontab; podría existir trigger ad-hoc,
  no encontrado).

### 3. 📊 Pipeline Editorial — Métricas — RECOMENDACIÓN: **ARCHIVE**

| Campo | Valor |
|---|---|
| page_id | `35a5f443-fb5c-8195-9d7f-d87fa96e36d1` |
| created / last_edited | 2026-05-08T03:22Z / 2026-05-21T10:15Z |

Qué es: dashboard auto-generado de métricas del pipeline editorial (217 proposals,
breakdowns de status, "Cron 15 */6 * * * UTC", "Copy review pending (Stage 7.5)").
Título con emoji 📊 confirmado en el título real.

Links/backlinks: ninguno por page_id; "Pipeline Editorial" aparece en docs históricos
del repo como concepto, no como link a esta página.

Justificación: métricas congeladas desde 2026-05-21 (~3 meses) — un dashboard stale
desinforma más de lo que aporta; si las métricas vuelven, regenerarlas bajo
`Dashboard Rick`, no en Control Room.

- Evidencia: "Última corrida: 2026-05-21T10:15:04+00:00" impreso en la propia página;
  su cron (`15 */6`) no existe en el crontab actual.
- Inferencia: productor muerto ~3 meses (mismo criterio de ausencia en crontab).

### 4. Shortlist editorial guiada — Fases A y B — RECOMENDACIÓN: **ARCHIVE**

| Campo | Valor |
|---|---|
| page_id | `3a55f443-fb5c-811d-9d1a-d17fe29d4da0` |
| created / last_edited | 2026-07-22T07:27Z / 2026-07-22T20:09Z |

Qué es: curación editorial guiada del ciclo Ola-3 (shortlist de fuentes/referentes con
ángulo, alineación, canal y riesgo por ítem; Fases A y B, sin Fase C ejecutada).

Links/backlinks: ninguno por page_id en los repos.

Justificación: la propia página se declara obsoleta — callout primero:
*"LEGACY — la cola canónica es la DB Alternativas / Shortlist. No usar esta página
para nuevas señales."* — archivar es coherente con su propio aviso y reversible.

- Evidencia: callout LEGACY literal como primer block; cola canónica nombrada.
- Inferencia: el ciclo Ola-3 ya capitalizó lo útil (candidato CAND-OLA3-03 existente);
  el residuo es histórico.

## Resumen de recomendaciones

| # | Página | Recomendación |
|---|---|---|
| 1 | Bitácora Plan Q2-2026 | **MOVE** → child de Dashboard Rick |
| 2 | SIM Daily Report 2026-05-07 | **ARCHIVE** (papelera, reversible) |
| 3 | 📊 Pipeline Editorial — Métricas | **ARCHIVE** (papelera, reversible) |
| 4 | Shortlist editorial guiada — Fases A y B | **ARCHIVE** (papelera, reversible) |

Si David aprueba las 4 tal cual, **no hace falta tocar el allowed set**: al ejecutarse
(pack siguiente, GO fila a fila) el residual queda en 0 y `validation.ok` pasa a
`true` sin cambio de código.

## Apéndice — Patch propuesto SOLO si alguna fila termina en ALLOWLIST (NO aplicado)

No usar `_ALLOWED_NAV_CHILD_PAGES` (es semántica de navegación y alimenta renames
canónicos). Propuesta por **page_id** (robusta a renames de título):

```diff
--- a/scripts/openclaw_panel_vps.py
+++ b/scripts/openclaw_panel_vps.py
@@
 _ALLOWED_NAV_CHILD_PAGES = {
     TECHNICAL_DASHBOARD_TITLE,
     SUPERVISOR_ALERTS_TITLE,
 }
+# Contenido aprobado por David para vivir como child de Control Room sin contar
+# como residual (acta: docs/ops/uas-panel-4-content-classify-20260810.md).
+_ALLOWED_CONTENT_CHILD_PAGE_IDS = {
+    # "<page_id sin guiones>",  # <título> — GO David YYYY-MM-DD
+}
@@ def validate_openclaw_shell(...)
     residual_child_pages = [
         block["id"]
         for block in children
-        if block.get("type") == "child_page" and not _is_allowed_nav_child_page(block)
+        if block.get("type") == "child_page"
+        and not _is_allowed_nav_child_page(block)
+        and _normalize_page_id(block["id"]) not in _ALLOWED_CONTENT_CHILD_PAGE_IDS
     ]
```

Con test acompañante (página allowlisteada no cuenta como residual; guardia de que el
set no puede contener los IDs de nav). Mutación del allowlist = pack siguiente con GO.

## Fase B — Residual post-cron: **PENDING_CRON**

- `NOW_UTC` inicio: 2026-08-10T21:02:08Z · probe: 21:03:23Z · cierre: ver REPORT.
- 21:03 < 22:25 → **no se espera al cron**; baseline contado ahora.
- **Baseline:** `residual_child_pages = 5` = las 4 de contenido + `Heartbeat Rick —
  2026-08-10 16:33 UTC` (matchea el prefijo `"Heartbeat Rick "` → el próximo cleanup
  la archiva).
- **Corrección de reloj del pack:** el crontab del panel es `0 */6 * * *` en hora
  local del VPS (**−04**), es decir corridas a 04/10/16/**22:00 UTC** — no 22:20. La
  última corrió 16:00 UTC (mtime del log), *antes* del Heartbeat 16:33: que siga viva
  a las 21:03 es lo esperado, no un fallo. Próximo cleanup: **22:00 UTC**; el re-check
  "go residual4" post-22:25 UTC sigue siendo el timing correcto.
- Señal positiva del productor (#619): **no existen Heartbeats 17:33–20:33** — el
  corte de publicación funcionó; 16:33 fue la última página antes de que el fix
  tomara efecto (evidencia: listado de residuales; inferencia: atribución al fix).
- Esperado post-cron: `residual_child_pages = 4`, Heartbeats = 0. Si el Heartbeat
  16:33 sobrevive al ciclo de 22:00 UTC → BLOCKED en el re-check.

## Gates

- **`UAS_PANEL_4_CLASSIFY_PASS = Y`** — tabla 4/4 con page_id, metadata, resumen,
  recomendación única y justificación; evidencia separada de inferencia; acta + PR.
- **`UAS_PANEL_RESIDUAL4_PASS = PENDING_CRON`** — baseline 5 (4 contenido + 1
  Heartbeat pre-cleanup) a las 21:03 UTC; el cron de 22:00 UTC aún no corría.
- **Gate compuesto del pack: PASS** (classify = Y, residual ≠ BLOCKED).

## TU TURNO (≤3)

1. Cursor mergea la PR de este acta si la clasificación está OK.
2. David da GO fila a fila: ALLOWLIST / MOVE / ARCHIVE (recomendado: MOVE la Bitácora,
   ARCHIVE las otras 3 — ejecutar en pack siguiente, nada mutado aún).
3. Post-22:25 UTC: re-pegar "go residual4" para el verify residual=4.
