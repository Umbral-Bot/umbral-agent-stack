# Mega-diagnóstico general 2026-08 — REPORT consolidado (F4: E6 + síntesis F1–F3)

> **Status:** ACTA ÚNICA del mega-diagnóstico (paso 3 del programa macro 2026-08-11).
> Ejecuta la Fase 4 (F4) del plan `docs/operations/megadiag-plan-2026-08-12.md`
> (PKG-MACRO-MEGADIAG-PLAN, #629) y consolida las actas F1 (#630), F2 (#631) y F3 (#632).
> **Emitido por:** PKG-MACRO-MEGADIAG-F4 (Claude Fable, 2026-08-12).
> **Rama:** `claude/macro-megadiag-f4-20260812`, base `main` @
> `080ef6a5eb98bd09511669babde574cc7ae0f50a` (#632, acta F3).
> **Ventana de captura F4:** 2026-08-12 ~03:20–04:10 hora local Windows (UTC-4).
> **Superficie:** Windows (docs + probes git/filesystem de solo lectura) + resultados
> F1–F3 ya mergeados en `main`. Cero mutación, cero fixes, cero ship de skills,
> cero `gh auth switch`, cero toque a `rick/stage7_5-multiformat` ni al worktree
> `poller-hardening`.
> **PR:** draft docs-only, label `do-not-merge`.

## 0. Resumen ejecutivo

- **Las 4 fases del mega-diagnóstico cerraron en PASS** (§1): F1 inventario Windows
  (#630), F2 runtime VPS (#631), F3 contratos CI + drift Windows (#632), F4 esta
  síntesis. Ningún hallazgo de la semilla de mayo se citó como actual sin re-probe
  de agosto.
- **El núcleo del runtime VPS está VIVO y sano** — gateway, worker (health 200/2ms),
  dispatcher (hotfixes #625–#627 desplegados), mission-control, auto-heal por cron,
  y el camino tailnet hacia el worker pcrick (587 polls 200/día). Lo que está
  degradado no es el motor: son los **bordes** (panel stale, poller con smoke
  pendiente, n8n B1/B3 inverificable por instancia MCP ajena) y la **red de
  verificación** (un solo gate automático, rojo 21 días).
- **La matriz E6 (§3) clasifica 42 sistemas declarados + 1 fila de cola**:
  **10 VIVO, 8 VIVO° (programado con efecto sin muestrear), 13 DEGRADADO,
  6 FÓSIL, 2 NUNCA_ACTIVADO, 2 PENDING, 1 BLOCKED con capa nombrada**.
  El patrón dominante no es "cosas muertas": es **capacidad cargada sin
  ejercitación verificable** — decenas de tareas registradas en un worker vivo,
  contratos integrados en servicios activos, pero con gates apagados
  (`gates=false`, fail-closed default-off), smokes sin cerrar y una sola red
  automática caída.
- **Hallazgo de arquitectura (de F3, confirmado como fila E6):** hay **dos
  catálogos de skills disjuntos** — registry Windows (46 skills, 106/106 targets
  sanos, motor de sync con estado) y plantillas OpenClaw (86, solo 6 desplegadas y
  las 6 divergentes, sin motor). Intersección de slugs = **0**. El "106/106" y el
  "6/86" **no son el mismo KPI** y no se promedian.
- **"Logrado con red" es una columna casi vacía (§5):** el único gate automático es
  `test.yml`, rojo desde 2026-07-22 por dos causas ya entendidas (fixture
  Publicaciones 0.2.0 + bomba de reloj en `stage3_promote`), más ~11 sondas
  manuales en `scripts/` que ningún gate corre. No existe "red de CI" más allá de
  eso; esta acta no la inventa.
- **Cadena de correcciones entre fases (§2.9):** F3 corrigió el encuadre de F1
  ("regresión" stage3 → bomba de reloj), y dos afirmaciones de F2 (el registry SÍ
  existe — el 404 era auth `gh` del VPS; `CLAUDE.md` NO está en `main`). La
  binaria de F2 sobre `openclaw-vps-operator` quedó disuelta: su ausencia de
  `main` es la decisión #585 (SoT = registry), lo roto son 2 referencias
  documentales.

```
MEGADIAG_F4_SYNTHESIS_PASS = Y
MEGADIAG_EXEC_PASS = Y
```

---

## 1. Gates F1–F4 (gate global del paso 3)

| Fase | Gate | Estado | Evidencia [E] |
|---|---|---|---|
| PLAN | — | mergeado | PR #629, `main` @ `5b2cc8a1` (docs/operations/megadiag-plan-2026-08-12.md) |
| F1 — Inventario mecánico (E1 + E7-probes + E7-bis) | `MEGADIAG_F1_INVENTORY_PASS` | **Y** | PR #630, commit `f2d07285`, acta `megadiag-2026-08-f1-inventory.md` |
| F2 — Runtime VPS (E2 + E4-VPS + E5 + E7-VPS) | `MEGADIAG_F2_RUNTIME_PASS` | **Y** | PR #631, commit `6bc0ce5d`, acta `megadiag-2026-08-f2-runtime.md` |
| F3 — Contratos CI + drift Windows (E3 + E4-Windows) | `MEGADIAG_F3_CONTRACTS_PASS` | **Y** | PR #632, commit `080ef6a5`, acta `megadiag-2026-08-f3-contracts.md` |
| F4 — Síntesis (E6 + consolidado) | `MEGADIAG_F4_SYNTHESIS_PASS` | **Y** | esta acta; matriz §3 con [E] por fila |
| **Global** | `MEGADIAG_EXEC_PASS` | **Y** | las 4 fases en PASS; los BLOCKED internos (E7-bis.2, n8n B1/B3, registry-desde-VPS) tienen capa nombrada y no bloquean fase alguna |

---

## 2. Consolidado por eje (E1–E7 + E7-bis)

Resumen de veredictos; el detalle fila a fila vive en las actas F1–F3 (citadas por
SHA/PR — no se duplican aquí).

### 2.1 E1 — Workspace y git post-higiene (F1 §E1)

**Veredicto: PASS con 1 residual nuevo.** Origin UAS exacto (2 heads: `main` +
`rick/stage7_5-multiformat`); 39 carpetas en `C:\GitHub` reconciliadas contra la
línea base; `_wt` vacío; stashes KEEP intactos. **Residual:** el criterio 3 del
paso 1 ("solo main + rama activa") ya no se sostiene en la familia `umbral-bot-*`
(drift 2→9 / 1→6 / 2→3 ramas locales + 8 dirty nuevos en `-codex`) — trabajo
activo post-higiene, inventariado sin tocar, pide un pack de clasificación nuevo.
Criterio 6 (roots del workspace Cursor) sigue `PENDING` (no verificable desde
git/fs). [E] F1 §E1.1–E1.6.

### 2.2 E2 — Runtime VPS (F2 §2)

**Veredicto: PASS — núcleo sano.** 4 servicios `systemd --user` ACTIVE (gateway
v2026.6.10 up 4d, worker 0.4.0 up 2s3d, dispatcher up ~14h consistente con
#625–#627, mission-control up ~3sem); worker `/health` 200 en 2ms con ~150 tasks
registradas; `openclaw status --all` sin secretos expuestos; crontab = 14 entradas
todas del repo canónico; 1 warning trivial (`plugins.load.paths` redundante,
candidata paso 5). [E] F2 §2.

### 2.3 E3 — Contratos, CI y tests (F3 §2)

**Veredicto: un solo gate automático, rojo 21 días, dos causas entendidas.**
`test.yml` es el único workflow que dispara solo; rojo desde 2026-07-22 21:48 UTC.
Causa A (10/13): fixture+constante de tests de Publicaciones tres meses detrás del
schema 0.2.0 intencional — **fixture desactualizado, no contrato roto**. Causa B
(3/13): bomba de reloj en `test_stage3_promote` (fechas absolutas + ventana 90d),
verificada por bisección de CI y reproducción local — **no es regresión**. Además:
registro fantasma `pytest.yml` en GitHub, baseline local Windows ≠ CI Linux
(+31 errors por symlink sin privilegio), y 11 sondas en `scripts/` que ningún gate
corre. [E] F3 §2.1–2.7.

### 2.4 E4 — Skills y drift repo↔runtime (F2 §3 + F3 §3)

**Veredicto: dos ecosistemas disjuntos con salud opuesta.**

| Ecosistema | Salud | [E] |
|---|---|---|
| Registry Windows (46 skills → 106 targets ON en 7 runtimes) | **106/106 presentes, 0 drift real** (41 byte-idénticos, 63 solo-EOL, 2 transformer por diseño); sync 4 min después del tip del registry | F3 §3.2–3.3 |
| OpenClaw templates (86 en `openclaw/workspace-templates/skills/`) | **6/86 desplegadas (~7%), las 6 divergentes** del template, sin motor de sync documentado | F2 §3 |

Intersección de slugs entre ambos catálogos = **0** (F3 §3.4). El drift "42/86 de
julio" quedó re-medido como 6/86 en agosto **dentro del catálogo OpenClaw**; no es
comparable con el 106/106 del registry. `openclaw-vps-operator`: canónico en
registry v0.1.1 completo (con `reference-diagnose.md`), desplegado en los 3
runtimes Windows; su ausencia de `main` UAS es la decisión #585, no una pérdida —
lo roto son 2 refs documentales (`.agents/PROTOCOL.md:178`,
`.github/agents/operador-openclaw-vps.agent.md:37`). [E] F3 §3.5.

### 2.5 E5 — Superficies Notion + n8n (F2 §4)

**Veredicto: Notion legible y vivo; n8n inverificable desde esta sesión.** Fetch
directo del Control Room (página real "OpenClaw") OK con contenido reciente
(panel actualizado 2026-08-10 22:00 UTC; la búsqueda semántica por "Control Room"
no la indexa — usar ID). n8n B1/B3: **BLOCKED capa permiso-cliente/instancia** —
el conector MCP de la sesión F2 apuntaba a un workspace AEC ajeno (0 matches
B1/B3); el estado runtime real no se adivinó. [E] F2 §4.

### 2.6 E6 — Intención vs realidad documental

**La matriz completa está en §3** (es el corazón de esta acta y el borrador del
paso 4).

### 2.7 E7 — Banca y riesgos abiertos (F1 §E7 + F2 §5)

| Ítem de banca | Estado re-probado agosto | Costo de cierre | [E] |
|---|---|---|---|
| Path G: WinError 3 (cron embudo pcrick) | **Vigente**: `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas` no existe también desde esta máquina (`Test-Path` False); el lado VPS/tailnet está sano y no lo ve | trivial (crear carpeta o corregir path) — decisión binaria | F1 §E7.1 + F2 §5 |
| `VM_URL` vestigial | **Vigente**: 0 lectores en código (17 menciones, 100% en `docs/`); la var real es `WORKER_URL_VM` | trivial (borrar o alinear env) | F1 §E7.2 |
| CI roja de `main` | **Vigente y ahora entendida**: 2 causas (A fixture, B reloj), filas A1/A2/B1 costeadas en F3 §2.8 | A1+B1 mecánicas (bajo); A2 pide lectura MCP de la base viva | F1 §E7.3 corregido por F3 §2.5 |
| Transcripts ~16 GB | **Re-medido con desglose**: 9.2G transcripts reales (`agents/`, mayor: `rick-ops` 4.4G) + 5.1G caché npm (no transcripts) + 22M ops_log | medio (poda autorizada por David, paso 5) | F2 §5 |

### 2.8 E7-bis — `umbral-bot-2` (bot IN por GO de David)

**Producto VIVO, CI del repo inverificable desde esta sesión.** `origin/main` @
`8230213f`; `umbralbim.io` y `beta.umbralbim.io` responden 200. `gh run list` /
`workflow list` del repo: **BLOCKED capa permiso-cliente** — el PAT fine-grained
activo no resuelve el repo vía API/GraphQL aunque el protocolo git puro funciona;
**sigue sin OAuth** al cierre de F4 (F3 lo re-verificó sin intentar
`gh auth switch`, prohibido). La binaria (autorizar cuenta OAuth bot-2 / ampliar
PAT / diferir) sigue abierta en TU TURNO. [E] F1 §E7-bis + F3 §4.

### 2.9 Correcciones entre fases (registro explícito)

| Afirmación original | Corrección | Estado final |
|---|---|---|
| F1 §E7.3: fallos `stage3_promote` = "causa distinta… la promoción no selecciona" (leído aguas arriba como posible regresión post-#627/#628) | F3 §2.4–2.5: **bomba de reloj** — código y test sin cambios desde 2026-05-06; el rojo entró solo entre 07-28 y 08-02 por vencimiento aritmético de fechas fixture | Dos causas confirmadas; etiqueta "regresión" retirada |
| F2 §3: "`umbral-skills-registry` no existe bajo el org (404)" → `BLOCKED capa acceso-repo` | F3 §3.1: el repo existe y está fresco en `C:\GitHub\umbral-skills-registry` (`origin/main` `5a209b4a`); el 404 es **auth `gh` del VPS** | Fila releída como `BLOCKED capa auth-gh-VPS` |
| F2 §3: "`CLAUDE.md` y `.agents/PROTOCOL.md` en `main` citan el path roto" | F3 §3.6: `CLAUDE.md` **no está en `main`** (sería untracked local del clon VPS); el segundo archivo normativo real es `.github/agents/operador-openclaw-vps.agent.md:37` | Refs rotas confirmadas = 2, pero en otros archivos |
| F2 decisión #2: "¿restaurar `openclaw-vps-operator` en `main` o formalizar que vive en otro lado?" | F3 §3.5: **ya está formalizada** en el registry (v0.1.1, completa, desplegada 3 runtimes); salió de `main` por #585 (`918dbe6`). Restaurarla reintroduciría el doble escritor | Binaria disuelta; queda solo el fix documental D1 |

---

## 3. Matriz E6 — Intención declarada vs realidad observada (42 sistemas + cola)

**Leyenda de estados** (definiciones operativas de esta acta):

- **VIVO** — runtime observable hoy: servicio ACTIVE, endpoint 200, cron instalado
  con efecto verificado, o capacidad cargada Y ejercitada con evidencia de agosto.
- **VIVO°** — la superficie de programación está verificada (cron instalado,
  código cargado en servicio vivo), pero el **efecto** no se muestreó en F1–F3;
  el ° marca "salida sin verificar", no sospecha de fallo.
- **DEGRADADO** — runtime existe pero parcial: gates apagados, drift, stale
  medido, smoke sin cerrar, o alcance recortado respecto a lo declarado.
- **FÓSIL** — tuvo vida verificable (evidencia histórica en repo/CI); hoy sin
  runtime que lo ejecute (o retirado por diseño).
- **NUNCA_ACTIVADO** — declarado en docs/código, sin evidencia de haber corrido
  jamás como sistema en producción.
- **PENDING / BLOCKED** — sin [E] suficiente para afirmar estado (PENDING) o
  sonda imposible desde las sesiones del diagnóstico, con capa nombrada (BLOCKED).

Toda fila lleva ≥1 probe [E]. "F1/F2/F3 §…" cita las actas mergeadas
(`f2d07285`/`6bc0ce5d`/`080ef6a5`); los probes nuevos de F4 citan comando.

### A. Contratos supervisor / OODA (docs 70–77)

| # | Sistema (docs) | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 1 | Gobernanza de agentes + routing supervisor (70, 71, 72) | **VIVO** | El contrato corre dentro del dispatcher vivo: `dispatcher/service.py:27` importa `TeamRouter`; `dispatcher/router.py:21-22` importa `supervisor_observability` + `supervisor_resolution`; `ambiguity_signal.py` presente. Servicio ACTIVE PID 2930054 (F2 §2). [E] Grep imports F4 + F2 §2 | No |
| 2 | Supervisor resolution contract (73) | **VIVO** | `dispatcher/supervisor_resolution.py` cargado vía router en el servicio activo (mismo [E] fila 1) | No |
| 3 | Closed OODA loop + reporte semanal (74) | **VIVO°** | Cron semanal declarado (`install-cron.sh:15`, lunes 07:00 UTC) dentro de las 14 entradas observadas en F2 §2; script `ooda-report-cron.sh` sin cambios desde 2026-05-19 (`git log`). Salida del reporte no muestreada en F1–F3 | Re-probe puntual en paso 4 |
| 4 | Improvement supervisor fase 6: activación + monitoreo (75, 76, 77) | **DEGRADADO** | La observability está integrada al dispatcher vivo (fila 1), pero el monitor dedicado `scripts/monitor_supervisor_observability.py` no tiene cron ni servicio (ausente de `install-cron.sh`) y no se toca desde 2026-04-20 (`git log`). El playbook de activación quedó en evidencia documental | Sí — ¿la fase 6 sigue siendo intención vigente? |

### B. Cadena copilot-cli F1–F8 (docs copilot-cli-*)

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 5 | F1–F5: capability, sandbox, task, mission contracts, rick-tech-agent | **VIVO°** | Capacidad cargada en runtime real: `worker/tasks/copilot_cli.py` registrado en el worker 0.4.0 activo (~150 tasks, health 200 — F2 §2); Drop-In `copilot-cli.conf` presente en `umbral-worker.service` (F2 §2, contenido no auditado). Ejercitación reciente sin probe | No |
| 6 | F6: token plumbing → egress → live deploy (steps 1–6c4f) | **VIVO°** | Desplegado según cadena de evidencia docs F6 + código de contención vigente: `scripts/copilot_egress_resolver.py` último cambio 2026-06-22 (#481 "require GitHub Meta for egress activation"); verificadores `verify_copilot_cli_env_contract.py` / `verify_copilot_egress_contract.py` presentes (fuera de gate, F3 §2.7) | No |
| 7 | F7 rehearsals + F8/F8a real execution path | **DEGRADADO** | Los rehearsals live tienen evidencia histórica (docs `copilot-cli-f7-*-live-evidence.md`); no hay gate que los re-corra ni probe de agosto de la ruta F8a. La capacidad sigue cargada (fila 5) pero la verificación es puntual y vieja | Sí — decidir si F8a merece smoke recurrente o se congela |

### C. Pipeline Granola (docs 50–61, 64–65, 78)

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 8 | Ingest raw local/VM (51, 64-granola, 65-granola) | **FÓSIL** | La ruta de captura local quedó descartada por cifrado (ruta R1 documentada — fix declarado = API oficial/MCP/CSV) y la VM host fue retirada (E6 fila 38). Sin cron granola en `install-cron.sh` ([E] lectura F4); último commit familia granola 2026-07-15 (#532, `git log`) | Sí — activar ruta oficial API o cerrar la intención |
| 9 | Catch-up Drive→Notion P1.1b (#532) | **FÓSIL** (one-shot completado) | Batch de recuperación mergeado 2026-07-15 (#532 "Drive->Notion Granola transcript catch-up (P1.1b Phase 0-3)", `git log`); diseño puntual, sin recurrencia programada — correcto que no tenga runtime hoy | No |
| 10 | Promoción raw→curated→operational (53–61) | **VIVO°** | Capacidad cargada en el worker vivo: `worker/tasks/granola.py`, `granola_capitalization.py`, `granola_task_capitalize.py` registrados ([E] ls F4 + F2 §2 health/tasks). Sin cron; operación bajo demanda; ejercitación de agosto sin probe | No |
| 11 | Finality reconciliation (78) + gap-check | **VIVO°** | `worker/tasks/granola_finality.py` cargado (ls F4); `granola-gap-check.sh` y `scripts/granola_gap_check.py` existen pero **fuera** del cron instalado ([E] `install-cron.sh` no los incluye) | Sí — ¿el gap-check debía ser recurrente? |

### D. Pipeline editorial (docs 67–68, editorial-pipeline/, scripts/discovery, scripts/editorial)

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 12 | Discovery stages 0–6 (`scripts/discovery/stage0…stage6`) | **DEGRADADO** | Código presente y contenido (último cambio 2026-07-20, #544 contención Ola 2); `discovery-publish-cron.sh` existe pero **no** está en `install-cron.sh` → sin recurrencia declarada; su única red de test (stage3) está rota por la bomba de reloj (F3 §2.4) | Sí — filas A1/B1 de F3 §2.8 lo ponen en verde |
| 13 | Stage 7.5 copy writer + multiformato | **DEGRADADO** | Writer de producción en `main` (`stage7_5_copy_writer.py`); la variante multiformato vive solo en la rama KEEP `rick/stage7_5-multiformat` @ `a263539` (head vivo en origin, F1 §E1.2) — decisión de producto pendiente desde el brief KEEP3 (#593/#596) | Sí — mergear, acotar o matar la rama KEEP |
| 14 | Stage 8 imagen (Magnific) + stage 9 LinkedIn publish | **DEGRADADO** | Contención Ola 2 vigente: stage9c/stage8 **fail-closed con flags default-off** desde #544 (`136a1a4`, `git log` — último cambio del dir); la clave Magnific en VPS no se verificó en F1–F3 (el merge de #555 no la implica) | Sí — ¿abrir flags? requiere smoke aparte |
| 15 | Puente HITL-2 → publish blog (P2.6, `scripts/editorial`) | **NUNCA_ACTIVADO** (en producción) | Mergeado 2026-07-23 con triple gate D3, dry-run y `gates=false` a propósito (#559, `git log`); la tarea `web.publish_editorial_post` está registrada en el worker (target del B1) pero el camino productivo nunca se abrió | Sí — GO de producción es decisión de David |
| 16 | Skills editoriales del runtime OpenClaw (`n8n-editorial-orchestrator`, `editorial-source-curation`) | **DEGRADADO** | 2 de las 6 skills desplegadas en `~/.openclaw/skills/` — ambas divergen byte-a-byte de su plantilla en `main` (F2 §3) | Cubierta por la decisión de arquitectura fila 27 |

### E. Torneos (docs 69, 79)

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 17 | Tournament over branches (69, `d3.1–d3.3`) | **FÓSIL** | Última corrida documentada D3.3 fase 0 el 2026-06-02 (`git log scripts/vps/d3*`); scripts fuera de cron; sin evidencia de uso posterior | No — evidencia histórica correcta |
| 18 | Tournament OpenClaw-native / PIT (79) | **FÓSIL** | Capacidad residual cargada (`worker/tasks/tournament*.py`, `pit_runner.py` — ls F4) pero: docs PIT v2 archivados HISTÓRICO (#594), colas residuales de torneos ~1–2M en `agents/` del VPS (F2 §5), y sin cron/servicio que los dispare | Sí — retirar las tasks del worker o declarar el sistema en pausa |

### F. Dispatcher / panel (#617–#627)

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 19 | `openclaw-dispatcher.service` (prefijos windows./browser./gui.) | **VIVO** | ACTIVE PID 2930054, up ~14h consistente con el ciclo de hotfixes #625–#627 (F2 §2); último commit del dir 2026-08-11 (#627, `git log`) | No |
| 20 | `mission-control.service` (panel web) | **VIVO** | ACTIVE PID 3313840 up ~3 semanas (F2 §2); app real en `mission_control/` (app.py + routes + templates, ls F4) | No |
| 21 | Panel OpenClaw en Notion (openclaw-panel-cron 6h) | **DEGRADADO** | El callout del panel decía "Actualizado: 2026-08-10 22:00 UTC" al momento de la captura F2 (2026-08-12 ~05:00 UTC) — ~31h stale pese al cron cada 6h (`install-cron.sh:7`). Causa sin diagnosticar (puede ser "solo escribe si hay cambios") | Sí — diagnóstico causal barato en paso 4/5 |
| 22 | Dashboard Rick (dashboard-rick-cron horario) | **PENDING** | Cron horario declarado (`install-cron.sh:6`) dentro de las 14 entradas (F2 §2) y script tocado el 2026-08-08 (#615 executable fix); la frescura de la página Notion destino no se leyó en F2 | Re-probe de frescura en paso 4 |

### G. Poller Control Room

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 23 | Notion poller daemon (smart replies, alcance solo-Control-Room) | **DEGRADADO** | Keepalive por cron */5m instalado (`install-cron.sh:10` + conteo 14 F2 §2); el daemon usa el código del dispatcher (`notion-poller-daemon.py:105` importa `dispatcher.notion_poller._do_poll` — Grep F4); reactivado con alcance recortado (solo Control Room, V2 off) y el smoke del reply-path sigue esperando un comentario humano de David — nunca cerrado | Sí — David comenta en Control Room para cerrar el smoke, o se degrada la intención |

### H. n8n bordes (B1/B3) + RRSS

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 24 | B1 `telegram-ok-publica` + B3 `worker-health-cron` | **BLOCKED** (capa permiso-cliente/instancia-MCP) | Runtime real inverificable desde las sesiones del diagnóstico: el conector MCP de F2 apuntaba a un workspace AEC ajeno — 0 matches B1/B3 (F2 §4). Último estado **repo-declarado** (no runtime): "ACTIVO con bot TEST desde 2026-07-25" (`infra/n8n/README.md`, último commit del dir #566 2026-07-25). No se adivina el estado actual | Sí — reconectar el MCP n8n correcto (dmbutic/umbralbim) o declarar B1/B3 fuera del alcance de probes agénticos |
| 25 | Pipeline RRSS n8n (60-rrss) | **NUNCA_ACTIVADO** | Solo existen 2 exports en `infra/n8n/workflows/` (B1 y B3 — ls F4); por la doctrina del propio README ("un workflow que existe solo en el VPS no existe"), el pipeline RRSS declarado en el doc 60 no tiene existencia versionada | Sí — ¿la intención RRSS-vía-n8n sigue vigente? |

### I. Skills — dos ecosistemas (filas separadas por mandato)

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 26 | Ecosistema **registry** (46 skills → 7 runtimes Windows) | **VIVO** | 106/106 targets ON presentes, 0 drift real de contenido, sync aplicado 4 min después del último ship (F3 §3.2–3.3); motor con estado (`.sync-state.json` + backups) | No — es el sistema más sano del diagnóstico |
| 27 | Ecosistema **OpenClaw templates** (86 plantillas → `~/.openclaw/skills/`) | **DEGRADADO** | 6/86 desplegadas y las 6 divergentes; sin motor de sync documentado (F2 §3). Intersección de slugs con el registry = **0** (F3 §3.4): son catálogos disjuntos con gobernanzas distintas, no dos vistas del mismo KPI | **Sí — decisión de arquitectura D5**: converger, declarar separados a propósito, o retirar el catálogo OpenClaw |

### J. Núcleo runtime VPS

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 28 | Gateway OpenClaw | **VIVO** | ACTIVE up 4d, v2026.6.10, 8 agents/31 sesiones, secrets none; 1 warning trivial de config (F2 §2) | Warning → paso 5 (doctor --fix) |
| 29 | Worker VPS (`umbral-worker` 0.4.0) | **VIVO** | health 200 en 2ms, ~150 tasks registradas, up 2sem3d (F2 §2) | No |
| 30 | Worker Windows pcrick (vía tailnet) | **VIVO** | 587 polls 200 hoy desde el monitor del dispatcher hacia `100.109.16.40:8088`, 0 fallos en 3 días (F2 §5) | No |
| 31 | Auto-heal (supervisor.sh */5m + health-check */30m) | **VIVO** | Cron confirmado en crontab; `supervisor.log` reporta "Worker: OK / Dispatcher: OK" sin restarts (F2 §5) | No |

### K. Infra programada auxiliar (cron VPS)

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 32 | scheduled-tasks (cada min) + quota-guard (*/15m) | **VIVO°** | Ambos declarados en `install-cron.sh:16-17` dentro de las 14 entradas observadas (F2 §2); efecto no muestreado en F1–F3 (el quota-guard protege el freeze por cuota — su silencio es compatible con "no hizo falta") | No |
| 33 | runtime-snapshot (*/6h) + daily-digest (22:00) | **VIVO°** | Declarados (`install-cron.sh:12,18`), conteo consistente (F2 §2); salidas no muestreadas | No |
| 34 | e2e-validation diaria (06:00) | **VIVO°** | Declarada (`install-cron.sh:14`); `scripts/e2e_validation.py` sin cambios desde 2026-06-03 (`git log`); resultado diario no muestreado en F1–F3 | Re-probe barato en paso 4 (leer `/tmp/e2e_validation.log`) |
| 35 | SIM (sim-report 3×/día + sim-to-make 3×/día; docs 39, 60-rrss lado Make) | **PENDING** | Única certeza de agosto: crons declarados (`install-cron.sh:11,13`) dentro del conteo 14 (F2 §2) y scripts sin cambios desde 2026-05-19 (`git log`). La señal "SIM=DISABLE" del sys-diag de julio es histórica y **no se re-probó**; el efecto real (¿escribe a Notion/Make?) queda sin verificar | Sí — re-probe del log SIM o retiro del cron |

### L. Red de verificación

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 36 | Gate automático `test.yml` (+ ~11 sondas sin gate) | **DEGRADADO** | Único gate automático del repo, rojo 21 días por causas A+B entendidas (F3 §2); registro fantasma `pytest.yml` en GitHub; 11 sondas manuales en `scripts/` fuera de toda colección (F3 §2.7). **No existe más "red de CI" que esto** | Sí — pack "main en verde" (A1+B1) ya costeado en F3 §2.8 |

### M. Banca, legacy y satélites

| # | Sistema | Estado | Estado observado + [E] | ¿Decisión? |
|---|---|---|---|---|
| 37 | Cron embudo pcrick → G: (WinError 3) | **DEGRADADO** | Path destino inexistente confirmado desde Windows (F1 §E7.1); el transporte tailnet está sano (F2 §5) — falla el último tramo, no el camino | Sí — binaria: crear carpeta o corregir path |
| 38 | VM legacy + browser automation VM (13, 20, 21, 33, 64-browser) | **FÓSIL** | VM retirada (migración 20/21 completada — su punto final es histórico); `VM_URL` con 0 lectores en código (F1 §E7.2); el nombre sobrevive solo en `WORKER_URL_VM`, que hoy apunta al worker pcrick | Limpieza de env → paso 5 |
| 39 | Dashboard gerencial legacy + kanban (22, 27) | **FÓSIL** | `install-cron.sh:22` **filtra activamente** `dashboard-cron.sh` del crontab (reemplazado por el split Dashboard Rick/panel); `cleanup_kanban_residues.py` existe como herramienta de limpieza, no de operación | No |
| 40 | Azure/Foundry audio + GPT Rick agent (40–43) | **DEGRADADO** | Hubo vida real (hackathon marzo, docs 40–41); la capacidad sigue cargada (`worker/tasks/azure_audio.py`, `google_audio.py` — ls F4) pero las sondas (`test_foundry_local.py`, `test_gpt_realtime_audio.py`, `test_gpt_rick_agent.py`) están en la lista de 11 sin gate (F3 §2.7) y no hay evidencia de uso de agosto | Sí — ¿la intención de audio/agente Foundry sigue viva? |
| 41 | Linear-first operating model (30, 34, 67-linear) | **DEGRADADO** | Triple presencia sin ejercitación verificada: 3 de las 6 skills VPS son `linear-*` (divergentes — F2 §3); `worker/tasks/linear.py` + `worker/linear_team_router.py` cargados (ls/Grep F4); sondas `_test_linear_live.py`/`audit_linear_worker.py` sin gate (F3 §2.7) | Sí — confirmar si Linear sigue siendo superficie operativa o se congela |
| 42 | `umbral-bot-2` (producto, E7-bis) | **VIVO** | apex + beta HTTP 200; `origin/main` @ `8230213f` (F1 §E7-bis); su CI es **BLOCKED capa permiso-cliente** (PAT sin el repo; sin OAuth aún — re-verificado en F3 sin `auth switch`) | Sí — binaria OAuth bot-2 (TU TURNO) |

### N. Cola sin clasificar (fila explícita — no silencio)

| # | Contenido | Por qué queda en cola | [E] |
|---|---|---|---|
| 43 | (a) Docs 00–49 de setup/audits/migraciones históricas ya superadas por los packs de higiene (00–21, 26, 28–38 salvo lo ya filado); (b) canal Telegram core (04) — declarado como transporte del B1 con bot TEST, sin re-probe propio; (c) Gmail/Calendar/Drive Google (35x) — `worker/tasks/gmail.py`, `google_calendar.py`, `google_drive.py` cargados, scripts gd51/gd52 presentes, sin probe de tokens/uso; (d) PowerBI (63); (e) dominios Umbral (65-dominios, 66) — indirectamente vivos vía 200 de umbralbim.io pero sin fila propia; (f) tasks del worker sin doc-sistema mapeado (`figma.py`, `rag.py`, `research.py`, `document_generator.py`, `client_admin.py`, `make_webhook.py`, `windows_fs*.py`, `gui.py`, `browser.py`); (g) `mcp_server/`, `aeco-kb` (workflow GHCR manual, 5/5 success, último 2026-06-04 — F3 §2.1); (h) repos satélite (`notion-governance`, `dynamo-mcp`, `visor-ifc`) — su estado git lo cubrió F1 §E1.4, su runtime declarado no se probeó | El plan acota E6 a ~40 sistemas; estos ítems no tienen doc-sistema con intención operativa clara o su probe excede las superficies de F1–F3. **El paso 4 decide cuáles de esta cola merecen fila propia** | ls/Grep F4 + F1/F3 citados |

### Conteo de la matriz

| Estado | Filas |
|---|---|
| VIVO | 10 (1, 2, 19, 20, 26, 28, 29, 30, 31, 42) |
| VIVO° (programado, efecto sin muestrear) | 8 (3, 5, 6, 10, 11, 32, 33, 34) |
| DEGRADADO | 13 (4, 7, 12, 13, 14, 16, 21, 23, 27, 36, 37, 40, 41) |
| FÓSIL | 6 (8, 9, 17, 18, 38, 39) |
| NUNCA_ACTIVADO | 2 (15, 25) |
| PENDING | 2 (22, 35) |
| BLOCKED (capa nombrada) | 1 (24) |
| Cola sin clasificar | 1 (43) |

---

## 4. Lectura transversal (síntesis Fable)

1. **El motor está vivo; los bordes no cierran el circuito.** Todo lo que es
   servicio-systemd + cron core está ACTIVE y auto-curado. Pero casi cada camino
   que termina en un humano o una red social está recortado: publish editorial
   `gates=false` (15), stage8/9 fail-closed (14), poller con smoke sin cerrar
   (23), B1/B3 con bot TEST y runtime inverificable (24), panel stale (21). La
   pregunta del paso 4 no es "¿qué está roto?" sino **"¿cuáles de estos gates
   apagados queremos encender, y cuáles eran intenciones que ya no valen?"**
2. **"Capacidad cargada" ≠ "sistema vivo".** El worker registra ~150 tasks que
   cubren 8 familias de sistemas; eso hace que casi nada califique de
   NUNCA_ACTIVADO, pero solo un puñado tiene ejercitación verificable de agosto.
   El VIVO° existe como categoría precisamente para no inflar el conteo de VIVO.
3. **La red de verificación es un punto único de fallo, y está caído.** Un solo
   gate automático (rojo 21 días por deuda entendida y barata: A1+B1), 11 sondas
   manuales sin dueño, y los smokes live (F7, editorial, poller) son puntuales y
   viejos. Antes de encender cualquier gate de producto conviene pagar el pack
   "main en verde" — es la fila más barata con mayor retorno de todo el
   diagnóstico.
4. **Hay una decisión de arquitectura que bloquea las demás sobre skills:** dos
   catálogos disjuntos (26 vs 27) con salud opuesta. Resolver D5 (converger /
   separar a propósito / retirar) define qué significa "drift" en el futuro; sin
   eso, cualquier re-sync del lado OpenClaw es esfuerzo a ciegas.
5. **Las intenciones fósiles están bien enterradas.** Torneos D3/PIT, VM, ingest
   local Granola, dashboards legacy: todos tienen evidencia histórica correcta y
   cero runtime colgando (salvo tasks residuales del worker, fila 18). No hay
   "muertos que caminan" — hay decisiones de retiro que faltan formalizar en una
   línea de docs cada una.

## 5. Columna "logrado con red" (insumo E3 → paso 4)

Regla de puntuación para el reconteo: **con red** = lo cubre el único gate
automático (`test.yml`) en verde; **frágil** = funciona con evidencia pero ningún
gate lo re-verifica; **sin red** = ni gate ni sonda.

- Hoy la columna "con red" está **vacía en la práctica**: el gate existe pero
  lleva 21 días rojo (F3 §2.2). Con A1+B1 pagados, ~4750 tests vuelven a ser red
  real para: contratos Notion/schemas, discovery stages, worker tasks con suite.
- "Frágil": todo lo marcado VIVO/VIVO° en la matriz que depende de sondas de
  `scripts/` (11 archivos, F3 §2.7) o de smokes puntuales históricos (F7, D3).
- "Sin red": los bordes NUNCA_ACTIVADO (15, 25) y los caminos BLOCKED (24,
  CI bot-2).

## 6. Filas candidatas consolidadas para el paso 5 (ninguna aplicada)

Consolida F2 §7 + F3 §2.8/§3.7 + nuevas de F4. Solo lectura: nada de esto se tocó.

| # | Fila | Origen | Costo |
|---|---|---|---|
| P5-1 | Pack "main en verde": A1 (constante 0.2.0) + B1 (reloj inyectable en stage3) | F3 §2.8 | bajo |
| P5-2 | Binaria fixture Publicaciones (a)/(b) — requiere lectura MCP de la base viva | F3 §2.3 | bajo/medio |
| P5-3 | Refs documentales rotas de `openclaw-vps-operator` (D1: PROTOCOL.md:178 + operador-openclaw-vps.agent.md:37 → registry) | F3 §3.5 | trivial |
| P5-4 | Decisión de arquitectura D5: dos catálogos de skills (converger/separar/retirar) | F3 §3.4 + filas 26–27 | alto (diseño) |
| P5-5 | Re-sync o aceptación documentada del drift OpenClaw 6/86 (depende de P5-4) | F2 §7.1 | medio |
| P5-6 | `openclaw doctor --fix` (warning plugins.load.paths) | F2 §7.6 | trivial |
| P5-7 | Poda transcripts: `agents/rick-ops` 4.4G + identidades inactivas + caché npm 5.1G | F2 §7.5 | medio (GO David) |
| P5-8 | Conector MCP n8n correcto (dmbutic/umbralbim) para poder probear B1/B3 | F2 §7.4 + fila 24 | bajo |
| P5-9 | Registro fantasma `pytest.yml` (C1) + residual Cursor `notion-governance-expert` (D2) | F3 §2.8/§3.7 | trivial |
| P5-10 | Binaria WinError 3: crear carpeta G: o corregir path del cron embudo | F1 §E7.1 | trivial |
| P5-11 | Limpiar `VM_URL` vestigial del env | F1 §E7.2 | trivial |
| P5-12 | Pack de clasificación de ramas nuevas `umbral-bot-*` (drift post-higiene) | F1 §E1.6 | bajo |
| P5-13 | Smoke reply-path del poller (un comentario de David en Control Room) | fila 23 | trivial (humano) |
| P5-14 | Diagnóstico causal del panel stale 31h (¿escribe-si-cambia o cron caído?) | fila 21 | bajo |
| P5-15 | Re-probe SIM (log + destino) o retiro de sus 2 crons | fila 35 | bajo |
| P5-16 | Retirar/pausar formalmente tasks residuales de torneos en el worker | fila 18 | bajo |

## 7. Cómo alimenta el paso 4 (reconteo de funciones)

La matriz §3 **es** el borrador del reconteo: 43 filas con estado observado y
evidencia. Lo que el paso 4 agrega por fila es la dimensión que ningún probe
puede responder — **"¿la intención sigue vigente para el sistema de trabajo
actual de David?"** — y la decisión {mantener, acotar, cambiar, matar}:

- Las filas **VIVO** piden solo confirmación de vigencia (barato).
- Las **VIVO°** piden un muestreo de efecto de una línea cada una (logs ya
  existentes en `/tmp/*.log` del VPS) antes de puntuar.
- Las **DEGRADADO** son donde vive la decisión real: cada una tiene un gate
  apagado o un recorte que David enciende, acota o mata.
- Las **FÓSIL/NUNCA_ACTIVADO** piden una línea de formalización (retiro o
  reactivación consciente), no trabajo técnico.
- La **cola (fila 43)** se triaje en el propio paso 4: qué ítem merece fila y
  cuál se declara fuera del sistema de trabajo.

## 8. Gate y prohibiciones

```
MEGADIAG_F4_SYNTHESIS_PASS = Y
MEGADIAG_EXEC_PASS = Y
```

- Matriz E6: 43 filas + cola, todas con ≥1 [E] (comando F4 o cita F1/F2/F3 por
  SHA/PR); los PENDING/BLOCKED están declarados como tales, nunca afirmados.
- Los 7 ejes + E7-bis consolidados en §2 con sus veredictos y la cadena de
  correcciones explícita (§2.9) — ningún marcador viejo quedó en pie en silencio.
- Cero mutación: sin fixes, sin ship de skills, sin `gh auth switch`, sin tocar
  `rick/stage7_5-multiformat` ni `poller-hardening`, sin escritura en
  `umbral-skills-registry`, sin abrir WIP ajeno. Filas del paso 5 = candidatas,
  no aplicadas. Única escritura: este archivo y su rama/PR.
- Semilla de mayo: usada solo como forma; cero hallazgo de mayo citado como
  actual sin re-probe de agosto (las señales de julio sin re-probe quedaron
  explícitamente PENDING — filas 22, 35).
