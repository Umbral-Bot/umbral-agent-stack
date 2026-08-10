# Diagnóstico: residual_child_pages creciente en el panel OpenClaw (2026-08-09)

> **Pack:** PKG-UAS-PANEL-RESIDUAL-DIAG · rama `claude/pkg-uas-panel-residual-diag-20260809` ·
> base `2dd0797` (`origin/main`, tip = PR #616)
> **GO citado:** *"Go panel"* (David, 2026-08-09) — diagnosticar el `residual_child_pages`
> creciente (154→178, `validation.ok=false`) observado en `openclaw_panel_cron.log`.
> **Evidencia:** `~/.coord-ag-evidence/uas-panel-residual-diag-20260809/`
> **Nada de Notion fue mutado en este pack** — diagnóstico read-only + fix de código con
> tests, sin archive live.

## F1 — Historia del log

Las 14 corridas exitosas del cron del panel (`/tmp/openclaw_panel_cron.log`) cuentan la
historia completa:

| Era | residual_child_pages | cleaned | ok |
|---|---|---|---|
| Marzo 2026 (antes de que el cron se rompiera por el bug de permisos) | **3** | 0 | false |
| 2026-08-08/09 (cron revivido por PR #615) | **154 → 160 → 166 → 172 → 178** (+6 por corrida de 6h = **+1/hora**) | 0–1 | false |

La cadencia +1/hora fue la primera pista del productor.

## F2 — Inventario live (read-only, mismos helpers del script)

| Métrica | Valor |
|---|---|
| Blocks totales en Control Room | 206 |
| `child_page` totales | 184 |
| ALLOWED (`Dashboard Rick`, `Alertas del Supervisor`) | 2 |
| **Residuales** (criterio `validate_openclaw_shell`) | **182** |
| Residuales que matchean `_RESIDUAL_CHILD_PAGE_PREFIXES` | **0** |
| Residuales que el cleanup nunca tocará | **182** |

Histograma: **178/182 son `Heartbeat Rick — <fecha> HH:33 UTC`**, una por hora
(`created_time` hora a hora, ~24/día desde 2026-08-02; las 2 primeras el 2026-08-01).
Los otros 4: `Bitácora Plan Q2-2026` (abril), `SIM Daily Report 2026-05-07`,
`📊 Pipeline Editorial — Métricas`, `Shortlist editorial guiada — Fases A y B` (julio)
— contenido legítimo movido/creado ahí, decisión humana.

## F3 — Causa raíz: compuesta B + A

### Primaria: B) PRODUCER_LOOP — el heartbeat de `rick-tracker`

Cadena de evidencia:

1. Títulos `Heartbeat Rick — HH:33 UTC` 1:1 con la cadencia del heartbeat de OpenClaw
   (`agents.list`: `heartbeat: every 1h`; los agentes corren al :33).
2. La sesión persistente de **`rick-tracker`** (`bd35d75c-…jsonl`, mtime 21:34 — justo
   tras el :33) contiene 244 menciones de "Heartbeat Rick" y 100 llamadas acumuladas a
   `umbral_notion_create_report_page`.
3. En las líneas recientes de esa sesión, el heartbeat ejecuta **bash con heredoc Python
   que hace `from worker import linear_client, notion_client`** — llama
   `worker.notion_client` **in-process** desde el workspace, bypasseando el worker HTTP.
   Por eso el journal del worker registra **cero** `notion.create_report_page` en 24h
   aunque las páginas aparecen cada hora (verificado: conteo de tasks del worker en 24h
   no incluye esa task).
4. `create_report_page` crea la página como **child de Control Room por default**
   (`worker/tasks/notion.py:460`).
5. Los reports locales gemelos (`reports/heartbeat-rick-*.md`, 451 archivos, ignorados
   por git) existen desde 2026-06-29 con el mismo naming — la **publicación a Notion es
   un comportamiento nuevo desde 2026-08-01**. El acta `user-e2e-p2-notion-2026-08-04.md`
   §4 ya había observado la cadencia sin atribuir productor.

**Gobernanza:** 24 páginas/día de telemetría de heartbeat en el panel David-facing viola
la regla "Notion es David-facing — no emitir telemetría" (CLAUDE.md / gobernanza V2), y
duplica lo que el heartbeat ya escribe localmente en `reports/`.

### Secundaria: A) PREFIX_GAP — cleanup estructuralmente más estrecho que la validación

`validate_openclaw_shell` cuenta como residual **todo** `child_page` fuera del allowed
set; `_cleanup_openclaw_residuals` solo archiva los prefijos `"OODA Weekly Report - "` y
`"[improvement] Workflow: self_improvement_cycle"`. Con 0/182 matches, `cleaned=0` en
cada corrida y `validation.ok=false` permanente — **cualquier productor nuevo genera
divergencia que el cleanup nunca corrige**.

### Descartada: C) CLEANUP_FAIL

El cleanup corre sin errores — simplemente no encuentra nada que matchee. (El único
`cleaned=1` de la primera corrida fue un párrafo vacío.)

## F4 / Fase 2 — Fix aplicado (código + tests, sin mutar Notion)

**Cambio mínimo en `scripts/openclaw_panel_vps.py`:** se agregaron los prefijos
`"Heartbeat Rick — "` (em-dash, formato actual) y `"Heartbeat Rick - "` (hyphen, formato
de los reports viejos) a `_RESIDUAL_CHILD_PAGE_PREFIXES`. Cubre 178/182 residuales; los
4 de contenido legítimo **no** matchean y quedan intactos para decisión humana.

**Tests (`tests/test_openclaw_panel.py`): 25/25 pasan** — 22 existentes + 3 nuevos:
- cleanup archiva páginas Heartbeat (ambas variantes de guion),
- cleanup NO toca las 4 páginas de contenido legítimo,
- guardia anti-regresión: ningún prefijo residual puede matchear los títulos allowed
  (`Dashboard Rick`, `Alertas del Supervisor`).

**Efecto declarado al mergear/deployar:** la primera corrida del cron del panel tras el
deploy archivará (~178) páginas Heartbeat acumuladas. **Archive en Notion es
reversible** (restaurables desde la papelera), a diferencia de un delete. Este pack NO
lo ejecuta — el efecto ocurre solo cuando David mergee y el runtime tome el cambio, y
esa es exactamente la aprobación pedida en TU TURNO.

## Qué queda para un pack siguiente (productor — F2c: no code-fix a ciegas)

El fix de arriba drena el síntoma pero el heartbeat de `rick-tracker` seguirá creando
1 página/hora (que el cleanup archivará cada 6h — ruido API estable, no creciente).
Frenar el productor requiere decidir **dónde debe vivir la trazabilidad del heartbeat**:

| Opción | Qué implica |
|---|---|
| a) Solo local | El heartbeat deja de publicar a Notion (ya escribe `reports/heartbeat-rick-*.md`); cero ruido en Control Room |
| b) Redirigir | Publicar a una página/DB técnica no-David-facing (p. ej. bajo Dashboard Rick) |
| c) Dejar así | Producir + archivar cada 6h — funciona pero gasta ~24 writes/día de API en crear páginas que se archivan |

La gobernanza ("no telemetría en superficies David-facing") apunta a **a** o **b**. Es
un cambio de prompt/workspace del agente `rick-tracker` (superficie viva de OpenClaw),
no de este repo — por eso va en pack aparte con su propio GO.

Los 4 residuales de contenido (Bitácora, SIM Daily, Métricas, Shortlist) también
esperan decisión: ¿moverlos a su lugar canónico, allowlistearlos, o archivarlos a mano?

## Deploy y drenaje ejecutado (PKG-UAS-PANEL-DEPLOY-617, 2026-08-10)

GO citado: *"GO sí"* (David, 2026-08-10) — merge #617 (`2c20b99`) = aprobar el drenaje.
Evidencia: `~/.coord-ag-evidence/uas-panel-deploy-617-20260810/`.

**El grueso del drenaje ocurrió solo antes del deploy formal:** el cron del panel corre
desde el working tree del canónico, que había quedado en la rama del pack #617 (con el
fix) tras el diagnóstico — las corridas nocturnas de 00:20/06:20 archivaron ~157
Heartbeats. El deploy formal (pull `main` @ `2c20b99` + corrida controlada
`--trigger deploy.617`) drenó el resto:

| Punto | residual_child_pages | de los cuales Heartbeat |
|---|---|---|
| Diagnóstico (2026-08-09) | 182 | 178 |
| Before deploy (2026-08-10) | 25 | 5 (+16 ocultos, ver abajo) |
| Tras corrida 1 | 20 | 0 matcheables… |
| Tras fix v2 + corrida 2 | **4** | **0 (todas las variantes)** |

**Hallazgo del deploy — tercera variante de título:** 16 páginas de la ventana
2026-08-03/04 usaban `Heartbeat Rick 2026-08-0X …` **sin guion** — no matcheaban
ninguno de los 2 prefijos con guion del fix #617. Fix v2 (este pack): el prefijo se
consolidó a `"Heartbeat Rick "` (sin exigir separador — cubre em-dash, hyphen y
sin-guion). Test actualizado con las 3 variantes; 25/25 pasan. La guardia
anti-regresión confirma que `Dashboard Rick` / `Alertas del Supervisor` no pueden
matchear.

**Estado final verificado:** `residual_child_pages = 4` — exactamente las 4 páginas de
contenido legítimo (Bitácora, SIM Daily, Métricas, Shortlist; prohibido archivarlas,
intactas). Allowed nav 2/2 intactos. `validation.ok` sigue `false` solo por esas 4 —
estado honesto hasta que David decida su destino. `cleaned_blocks=16` en la corrida
final. rick-tracker sigue produciendo ~1 página/hora (pack productor pendiente); el
cleanup ahora las archiva en cada ciclo de 6h, cualquiera sea la variante del título.

**Gate deploy: `UAS_PANEL_DEPLOY_617_PASS = Y`.**

## Gate

**`UAS_PANEL_RESIDUAL_DIAG_PASS = Y`** — Fase 1 completa con causa compuesta B+A y
evidencia; fix de código+tests para el componente A (25/25 verde); productor identificado
con evidencia para el componente B con pack siguiente propuesto; nada de Notion mutado;
sin secretos en evidencia ni en este doc.
