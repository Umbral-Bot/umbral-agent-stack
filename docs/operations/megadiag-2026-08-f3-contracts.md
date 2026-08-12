# Mega-diagnóstico general 2026-08 — F3 Contratos, CI y drift Windows (acta de ejecución)

> **Status:** ACTA de ejecución, solo lectura. Fase 3 (F3) del plan
> `docs/operations/megadiag-plan-2026-08-12.md` (PKG-MACRO-MEGADIAG-PLAN, #629).
> **Emitido por:** PKG-MACRO-MEGADIAG-F3 (Claude Code / Opus, Windows).
> **Rama:** `claude/macro-megadiag-f3-20260812`, base `main` @
> `6bc0ce5db880f0b95831c0e09c3f3428030627c7` (#631, acta F2).
> **Ventana de captura:** 2026-08-12, ~02:00–02:20 hora local Windows (UTC-4) =
> ~06:00–06:20 UTC, salvo donde se cita timestamp propio de GitHub Actions.
> **Alcance:** E3 (contratos, CI y tests) + E4-Windows (drift registry↔runtimes Windows).
> E1/E7-Windows los cubrió F1 (#630); E2/E4-VPS/E5/E7-VPS los cubrió F2 (#631); E6 va en F4.
> **Modo:** solo lectura. Cero patches a tests/fixtures, cero `gh auth switch`, cero
> mutación VPS, cero escritura en `umbral-skills-registry`, cero toque a
> `rick/stage7_5-multiformat` ni al worktree `poller-hardening`.
> **PR:** draft docs-only, label `do-not-merge`.

## 1. Resumen ejecutivo

- **El repo tiene exactamente UN gate automático, y lleva 21 días rojo.** De los 5
  workflows registrados en GitHub Actions, solo `Tests` (`.github/workflows/test.yml`)
  dispara solo (push+PR a `main`). El otro `Tests` registrado apunta a
  `.github/workflows/pytest.yml`, **un archivo que ya no existe en `main`** (registro
  fantasma, `active`, último run 2026-03-05). `AECO KB GHCR Images` es
  `workflow_dispatch` puro. Los dos "Copilot" son dinámicos de GitHub, no del repo.
- **Causa A = fixture + test desactualizados, NO contrato roto.** El schema
  `publicaciones.schema.yaml` fue subido a `0.2.0` a propósito el 2026-07-22 (#552, espejo
  del Shortlist vivo) y extendido el 07-23 (#554, #555). El test que exige `'0.1.0'` no se
  toca desde el **2026-04-21**; el fixture, desde el **2026-04-23**. El contrato avanzó y la
  red de tests se quedó tres meses atrás.
- **Causa B NO es una regresión post-#627/#628: es una bomba de tiempo por reloj.**
  `stage3_promote.py` y su test **no cambian desde el 2026-05-06**. El test siembra fechas
  de publicación absolutas (2026-04-29 … 2026-05-05) y el script clasifica contra
  `datetime.now(timezone.utc)` con ventana de 90 días: los ítems "frescos" del fixture
  vencieron entre el 2026-07-28 y el 2026-08-03 y el test empezó a fallar solo. Verificado
  por bisección de CI (verde 07-28 02:25 UTC → rojo 08-02 04:51 UTC, sin ningún commit de
  por medio que toque stage3) y reproducido hoy en local. **Corrige el encuadre de F1 §E7.3.**
- **E4-Windows es la contracara exacta de E4-VPS: acá no hay drift.** Los 106 targets
  `enabled: true` de las 46 skills canónicas del registry **están los 106 desplegados**
  (0 ausentes): 41 byte-idénticos, 63 idénticos salvo EOL (CRLF de checkout Windows) y 2
  derivados por transformer `skill_to_prompt` (por diseño). Último apply del motor de sync:
  2026-08-12 00:38:14, cuatro minutos después del tip del registry.
- **Registry y OpenClaw son dos ecosistemas disjuntos: intersección de slugs = 0.** Las 86
  plantillas de `openclaw/workspace-templates/skills/` (universo del 6/86 de F2) y las 46
  skills del registry (universo de Windows) **no comparten un solo slug**. Las dos métricas
  no son comparables ni el 6/86 es "el mismo drift" visto desde otro lado.
- **`umbral-skills-registry` sí existe** (`C:\GitHub\umbral-skills-registry`, origin/main
  `5a209b4a`); el 404 de F2 es de auth `gh` en el VPS, no ausencia. Y
  `openclaw-vps-operator` **no está en `main` de UAS por decisión explícita**: commit
  `918dbe6` "remove local openclaw-vps-operator stubs after SoT ship (#585)". Lo que quedó
  roto no es la skill: son dos referencias documentales.

`MEGADIAG_F3_CONTRACTS_PASS = Y`

---

## 2. E3 — Contratos, CI y tests

### 2.1 Inventario de workflows (`.github/workflows/` + registro real en GitHub)

| Workflow (id) | Archivo | ¿Existe en `main`? | Trigger | Último run relevante | Estado |
|---|---|---|---|---|---|
| `Tests` (241746553) | `.github/workflows/test.yml` | **Sí** | `push`+`pull_request` a `main`; matriz Python 3.11/3.12 | run `31568236865`, `2026-08-12T05:56:59Z`, `main` | **failure** — único gate automático del repo, rojo |
| `Tests` (241762798) | `.github/workflows/pytest.yml` | **No** — ausente de `origin/main` | — | run `22699009074`, `2026-03-05T02:11:30Z` | `success` histórico. **Registro fantasma**: GitHub lo lista `active` con archivo borrado |
| `AECO KB GHCR Images` (288926632) | `.github/workflows/aeco-ghcr-images.yml` | Sí | **solo `workflow_dispatch`** | run `26932704224`, `2026-06-04T05:26:24Z` | `success` (5/5 últimas). No es gate: nunca dispara solo |
| `Copilot code review` (240503967) | `dynamic/copilot-pull-request-reviewer/…` | n/a — gestionado por GitHub | — | — | Fuera del repo |
| `Copilot cloud agent` (259280035) | `dynamic/copilot-swe-agent/copilot` | n/a — gestionado por GitHub | — | — | Fuera del repo |

`[E]` `gh workflow list --all`; `gh api repos/Umbral-Bot/umbral-agent-stack/actions/workflows/<id>
--jq '"\(.id) | \(.name) | \(.path) | \(.state)"'`; `git ls-tree -r origin/main --name-only --
.github/workflows` → exactamente `aeco-ghcr-images.yml` + `test.yml`; `gh run list
--workflow=pytest.yml --limit 3`. Todo 2026-08-12 ~06:05 UTC.

**Lectura:** el repo tiene una sola red automática y está caída. No hay gate de lint, de
tipos, de contratos de schema fuera de pytest, ni build. Esto es insumo directo de la
columna "logrado con red vs logrado frágil" que E6/F4 necesita.

### 2.2 Línea de tiempo del rojo en `main` (bisección de CI)

| Run | Fecha (UTC) | Commit / PR | Resultado pytest | stage3 en el set |
|---|---|---|---|---|
| `29957536848` | 2026-07-22T21:01:12Z | docs(editorial): hoja de ruta norte P0.5→P3 | **success** | — |
| `29960568960` | 2026-07-22T21:48:09Z | docs(editorial): P1.4 mirror live Shortlist schema (#552) | `10 failed, 4366 passed, 5 skipped, 2 xfailed` | **no** |
| `30323074349` | 2026-07-28T02:25:47Z | fix(skills): make registry sole user-level writer | `10 failed, 4700 passed, 5 skipped, 2 xfailed` | **no** |
| `30733101491` | 2026-08-02T04:51:55Z | docs(ops): frescura runtime Rick (#570) | `13 failed, 4697 passed, 5 skipped, 2 xfailed` | **sí (3)** |
| `31457279110` | 2026-08-11T04:03:28Z | PANEL4-EXEC-THEN-HYGIENE — **anterior a #627** | `13 failed, 4743 passed` | sí (3) |
| `31504946223` | 2026-08-11T15:03:19Z | **#627** dispatcher prefijos windows./browser./gui. | `13 failed, 4752 passed` | sí (3) |
| `31558889068` | 2026-08-12T03:04:06Z | **#628** archive VPS hygiene P5 | `13 failed, 4752 passed` | sí (3) |
| `31568236865` | 2026-08-12T05:56:59Z | #631 acta F2 (tip actual de `main`) | `13 failed, 4752 passed, 5 skipped, 2 xfailed` en 67.19s | sí (3) |

`[E]` `gh run list --workflow=test.yml --branch main --limit 100` (último verde =
`29957536848`); por cada run citado, `gh run view <id> --log-failed` filtrado por
`FAILED tests/` y por la línea de resumen `= N failed, M passed … =`.

**Dos hechos que fija esta tabla:**

1. El rojo **empieza el 2026-07-22 21:48 UTC**, en el commit que sube el schema de
   Publicaciones. 21 días de `main` rojo al momento de esta acta.
2. Los 3 fallos de `stage3_promote` **ya estaban presentes el 2026-08-11 04:03**, once
   horas **antes** del merge de #627 y un día antes de #628. **No son regresión de
   ninguno de los dos.** Su ventana de entrada real es 2026-07-28 02:25 → 2026-08-02 04:51,
   sin ningún run de `main` intermedio (el repo no recibió pushes a `main` entre el 07-28 y
   el 08-02); los únicos commits de esa ventana son `5aab3f9` (#570), `6892783` (#571) y
   `28b4be9` (#572), los tres docs/ops, ninguno toca `scripts/discovery/` ni `tests/`.

### 2.3 Causa A — Publicaciones 0.2.0: **fixture desactualizado**, no contrato roto

10 de los 13 fallos. Dos síntomas, una raíz.

| Ítem | Estado observado | Evidencia [E] | ¿Pide decisión? |
|---|---|---|---|
| `notion/schemas/publicaciones.schema.yaml` | `version: 0.2.0`. Historia: `120ffbe` (2026-07-22, #552 "P1.4 mirror live Shortlist schema (Notion AI, live) + Publicaciones additions") → `6852a22` (2026-07-23, #554) → `92eb503` (2026-07-23, #555 Magnific 5 alternativas) | `Select-String version:` + `git log -3 -- notion/schemas/publicaciones.schema.yaml` | No — el bump es intencional y trazable a 3 PRs mergeados |
| `tests/test_notion_publicaciones_schema.py::TestSchemaLoads::test_database_version` y `…provisioner.py::TestPlanStructure::test_database_version` | `AssertionError: assert '0.2.0' == '0.1.0'`. El archivo de test no se toca desde `48666a7` (**2026-04-21**) | log del run `31568236865`; `git log -3 -- tests/test_notion_publicaciones_schema.py` | **Sí** — subir la constante esperada a 0.2.0 (paso 5) |
| `tests/fixtures/notion/publicaciones_database_valid.json` | Le faltan **12 propiedades** que el schema 0.2.0 ya declara: `Estado imagen`, `imagen_alt_1_url`…`imagen_alt_5_url`, `imagen_cantidad`, `imagen_error`, `imagen_generada_at`, `listo_rrss`, `origen_alternativa`, `Selección imagen`. Último cambio `e609839` (**2026-04-23**) | log del run: verdict `WARN`, `Differences: 12, Blockers: 0, Warnings: 12`, las 12 como `missing_property` | **Sí** — ver la pregunta decisiva abajo |
| `tests/test_notion_readonly_audit.py` (6 tests) | Fallan en cadena porque el auditor devuelve `WARN` donde el test espera `PASS` (`assert 'WARN' == 'PASS'`, `assert 'Verdict: PASS' in …`, `CLI failed (rc=1)` en `test_fail_on_warning_clean`) | mismo log | No — son consecuencia, no causa |

**Veredicto de clasificación: `fixture desactualizado`.** El contrato (`schema.yaml`) es la
pieza que avanzó a propósito, con PR y revisión; el auditor hace exactamente lo que debe
(marca 12 `missing_property` con severidad WARNING, 0 blockers); lo que quedó atrás son la
constante de versión en dos tests y el snapshot JSON. Nada indica ruptura del contrato.

**Pregunta decisiva que F3 no puede cerrar desde Windows (va a paso 5):** el fixture
`publicaciones_database_valid.json` es un **snapshot de la base Notion viva**. Que el
auditor diga WARN admite dos lecturas mutuamente excluyentes:

- **(a)** la base Notion viva **ya tiene** las 12 propiedades → el arreglo es refrescar el
  snapshot y subir la constante. Costo: bajo, mecánico.
- **(b)** la base Notion viva **no las tiene** → el WARN es verdad operativa y lo que falta
  es aprovisionar la base; tocar el fixture escondería un desalineamiento real.

Distinguir (a) de (b) requiere una lectura MCP de la base Publicaciones — superficie E5,
fuera del alcance Windows/solo-lectura de F3. **No se tocó ningún fixture.**

### 2.4 Causa B — `stage3_promote`: **bomba de tiempo por reloj**, no regresión

3 de los 13 fallos: `test_dry_run_does_not_mutate`, `test_commit_mutates_exactly_selected`,
`test_idempotent_commit` (todos en `tests/test_stage3_promote.py::TestRun`).

| Ítem | Estado observado | Evidencia [E] |
|---|---|---|
| Código de producción | `scripts/discovery/stage3_promote.py` **último cambio `a8f4a88`, 2026-05-06** ("recover(stage2-3): restore discovery scripts/tests/reports"). Ningún commit posterior lo toca | `git log --format=… -- scripts/discovery/stage3_promote.py` → 1 sola entrada |
| Test | `tests/test_stage3_promote.py` **mismo commit `a8f4a88`, 2026-05-06**, sin cambios posteriores | `git log --format=… -- tests/test_stage3_promote.py` → 1 sola entrada |
| Mecanismo | `_now_utc()` (línea 329-330) = `datetime.now(timezone.utc)`; `main()` hace `started = _now_utc()` (338) y `classify(it, now=started, max_age_days=args.max_age_days)` (345); `classify` descarta con `fuera_ventana_90d` si `age_days > max_age_days` (146-147). El test siembra fechas **absolutas** (`2026-04-29T22:54:14Z`, `2026-05-01`…`2026-05-05`) y llama con `--max-age-days 90` | `Grep` sobre `stage3_promote.py`; lectura de `tests/test_stage3_promote.py:192-261` |
| Vencimiento aritmético | `2026-04-29T22:54:14Z + 90d = 2026-07-28T22:54:14Z`; `2026-05-05 + 90d = 2026-08-03`. El último run verde de `main` fue el **2026-07-28T02:25:47Z**, veinte horas antes del primer vencimiento; el siguiente run (2026-08-02) ya cae del otro lado | tabla §2.2 + fechas del propio test |
| Reproducción local hoy | `pending=2 eligible=0 promoted=0 overall_pass=True` / `pending=5 eligible=0` / `pending=3 eligible=0` → `assert 0 == 1`, `assert 0 == 3`, `assert (0 == 0 and 0 == 3)` | `python -m pytest tests/test_stage3_promote.py -q --tb=line` → `3 failed, 19 passed in 1.63s`, 2026-08-12 |

**Veredicto de clasificación: test frágil por reloj (`fixture desactualizado` en su variante
temporal), NO contrato roto y NO regresión.** El detalle que lo cierra: en las tres
reproducciones el propio script imprime **`overall_pass=True`** — el contrato dice que la
corrida es válida; lo único que falla es la expectativa hardcodeada del test. Los otros 19
tests del mismo archivo (incluido `test_fuera_ventana`, que sí congela `NOW`) pasan.

La corrección natural (para paso 5, **no aplicada**): inyectar el reloj en `main()`
(`--now` o monkeypatch de `_now_utc`) o generar las fechas del fixture relativas a
`datetime.now()`, como ya hace el resto del archivo con la constante `NOW`.

### 2.5 Corrección explícita al encuadre de F1 §E7.3 y al insumo del orquestador

F1 (#630 §E7.3) registró los 3 fallos de `stage3_promote` como *"la promoción no está
seleccionando/promoviendo los ítems esperados… una causa distinta a la deuda de
Publicaciones"* y el paquete F3 los recibió como *"regresión no citada antes"*, con la
pregunta de si era post-#628/#627.

**Estado real medido en F3:** el hecho de "dos causas distintas" **se confirma**. La
etiqueta de "regresión" **no**: no hubo cambio de código ni de test desde el 2026-05-06, y
los 3 fallos ya estaban en CI once horas antes de #627 y un día antes de #628. La causa es
el paso del tiempo contra fechas hardcodeadas. Ni #627 (dispatcher) ni #628 (docs-only)
tienen relación.

### 2.6 Baseline local Windows vs CI Linux (no son el mismo resultado)

`[E]` `$env:WORKER_TOKEN='test'; python -m pytest tests/ -q` en
`umbral-agent-stack-claude` @ `6bc0ce5d`, Python 3.13, 2026-08-12 ~06:15 UTC:

```
14 failed, 4711 passed, 14 skipped, 2 xfailed, 2 warnings, 31 errors in 116.20s
```

| Diferencia vs CI | Detalle | Naturaleza |
|---|---|---|
| +1 failed | `tests/test_pit_collect_tokens.py::test_update_outcome_populates_billing_truth` — falla en local, pasa en CI | Pendiente de causa; candidata a fila de paso 5 (no investigada: fuera del foco "por qué está roja la CI") |
| +31 errors | Todos en `tests/mission_control/test_pit_preview.py`, con `OSError: [WinError 1314] El cliente no dispone de un privilegio requerido` al crear un **symlink** en el `tmp_path` del fixture | **Brecha de entorno Windows**, no defecto del repo: crear symlinks exige privilegio/Developer Mode. En Linux CI estos tests corren normal |
| +9 skipped | 14 local vs 5 en CI | Consistente con skips condicionados por plataforma |

**Nota de higiene de nombres:** este `WinError 1314` **no tiene nada que ver** con el
`WinError 3` de la banca (path G: de pcrick, F1 §E7.1). Códigos distintos, causas distintas;
se registra aquí para que nadie los cruce en el paso 4.

### 2.7 Suites fuera del gate

`[E]` `git ls-files` filtrado por `test_*.py` / `*_test.py` → **268 archivos**, de los
cuales **24 fuera de `tests/`**:

- **13** dentro de `docs/operations/_archive-hygiene-vps-2026-08-11/**` — copias archivadas
  de packs históricos. Correctamente fuera de la colección de pytest.
- **11** en `scripts/` (`integration_test.py`, `smoke_test.py`, `test_dashboard_payload.py`,
  `test_enqueue.py`, `test_foundry_local.py`, `test_gpt_realtime_audio.py`,
  `test_gpt_rick_agent.py`, …) — **sondas manuales, ningún gate las corre**. Es
  exactamente la categoría "logrado sin red" que E6/F4 tiene que puntuar.

### 2.8 Filas candidatas para el paso 5 (E3) — ninguna aplicada aquí

| # | Fila | Costo estimado | Riesgo de no hacerlo |
|---|---|---|---|
| A1 | Subir a `0.2.0` la constante esperada en los 2 `test_database_version` | trivial | La CI sigue roja por una deuda ya entendida |
| A2 | Resolver la binaria (a)/(b) de §2.3 con una lectura MCP de la base Publicaciones viva, y **después** refrescar el fixture o aprovisionar la base | bajo (a) / medio (b) | Refrescar el fixture sin resolverlo puede tapar un desalineamiento real del schema vivo |
| B1 | Inyectar el reloj en `stage3_promote.main()` (o fechas relativas en el fixture del test) | bajo | La bomba vuelve a estallar con cualquier fixture nuevo de fecha fija; y hoy enmascara 3 tests que ya no verifican nada |
| C1 | Borrar el registro fantasma del workflow `pytest.yml` en GitHub | trivial (UI/API) | `gh workflow list` miente sobre qué gates existen; cualquier auditoría futura lo vuelve a encontrar |
| C2 | Investigar `test_pit_collect_tokens::test_update_outcome_populates_billing_truth` (falla solo en Windows) | bajo | Ruido permanente en cualquier corrida local; erosiona la confianza en el baseline local |
| C3 | Documentar (no arreglar) que `tests/mission_control/test_pit_preview.py` requiere privilegio de symlink en Windows | trivial | Cada corrida local nueva reinvestiga los mismos 31 errors |

---

## 3. E4-Windows — Drift registry ↔ runtimes Windows

### 3.1 Canónico: el registry existe y está fresco (corrige F2 §3, fila `umbral-skills-registry`)

| Ítem | Estado observado | Evidencia [E] |
|---|---|---|
| Ubicación y tip | `C:\GitHub\umbral-skills-registry`; `origin/main` = `5a209b4aaa5a3100e37320a2be3f41b4d6c3e28d` (2026-08-12 00:38:12 -04, "feat(skills): ship mcp-host-wiring v0.2.0"). Working tree **limpio**, local en sync con origin | `git ls-remote origin refs/heads/main`; `git log -1`; `git status -sb` → `## main...origin/main` |
| SHA citado por el plan | `d5dda4d` **existe**: 2026-08-12 00:34:31 -04, "feat(skills): ship cursor-orchestrator v0.9.0". Está exactamente **1 commit** por detrás del tip | `git cat-file -t d5dda4d` → `commit`; `git log --oneline d5dda4d..5a209b4` → 1 línea |
| Contenido | **46 skills**: 33 en `skills/` + 13 en `notion-governance-skills/`. La versión vive en `<slug>/manifest.yaml` (`version:`), **no** en el frontmatter de `SKILL.md` | `Get-ChildItem -Directory` en ambos roots; lectura de `skills/pkg-receiver-protocol/manifest.yaml` |
| Escrituras de esta sesión | **cero**. Solo `git log/status/ls-remote/cat-file` y lecturas de archivo | — |

**Corrección a F2:** F2 concluyó *"`umbral-skills-registry` **no existe** como repo bajo el
org `Umbral-Bot` — `gh api` 404"* y lo marcó `BLOCKED capa acceso-repo`. Desde Windows el
repo es plenamente legible y su tip es verificable. El 404 del VPS es un problema de **auth
`gh` en esa máquina**, no ausencia del repo — misma capa que el `BLOCKED` de F1 §E7-bis.2
con `umbral-bot-2`. La fila de F2 se relee como `capa auth-gh-VPS`, no `acceso-repo`.
(No se intentó ningún `gh auth switch`, prohibido por el paquete.)

### 3.2 Matriz slug → versión canónica vs deploys Windows

Leyenda: `=` byte-idéntico al canónico · `~` idéntico salvo fin de línea (CRLF del checkout
Windows vs LF del canónico) · `→` derivado por transformer no-`identity` (esperado) ·
`≠` diferencia real de contenido · `·` target declarado `enabled: false` y no desplegado ·
`—` plataforma no declarada en el manifest · `ns`: `sk` = `skills/`, `ng` =
`notion-governance-skills/`.

| slug | ver | last_reviewed | ns | claude_desktop | codex | cursor | agents | copilot_cli | antigravity | copilot_chat |
|---|---|---|---|---|---|---|---|---|---|---|
| `adobe-print-file-authoring` | 0.1.3 | 2026-07-29 | sk | ~ | ~ | ~ | — | — | ~ | — |
| `cursor-orchestrator` | 0.9.0 | 2026-08-12 | sk | · | · | ~ | — | — | · | · |
| `dynamo-mcp-tester` | 0.2.3 | 2026-08-06 | sk | ~ | ~ | · | — | — | · | · |
| `linkedin-human-outreach` | 0.1.0 | 2026-08-05 | sk | = | = | · | — | — | · | · |
| `m365-agent-builder-loop` | 0.2.0 | 2026-07-22 | sk | ~ | ~ | ~ | — | — | — | — |
| `magnific-generation` | 0.1.0 | 2026-07-29 | sk | — | ~ | — | — | — | — | — |
| `mcp-host-wiring` | 0.2.0 | 2026-08-12 | sk | — | ~ | — | — | — | — | — |
| `n8n-agents` | 0.1.0 | 2026-07-25 | sk | = | · | · | = | = | · | — |
| `n8n-binary-and-data` | 0.1.0 | 2026-07-25 | sk | = | · | · | = | = | · | — |
| `n8n-code-nodes` | 0.1.0 | 2026-07-25 | sk | = | · | · | = | = | · | — |
| `n8n-credentials-and-security` | 0.2.1 | 2026-07-30 | sk | ~ | ~ | ~ | ~ | ~ | · | — |
| `n8n-data-tables` | 0.1.0 | 2026-07-25 | sk | ~ | · | · | ~ | ~ | · | — |
| `n8n-debugging` | 0.1.1 | 2026-07-29 | sk | ~ | · | · | ~ | ~ | · | — |
| `n8n-error-handling` | 0.1.0 | 2026-07-25 | sk | = | · | · | = | = | · | — |
| `n8n-expressions` | 0.1.0 | 2026-07-25 | sk | ~ | · | · | ~ | ~ | · | — |
| `n8n-extending-mcp` | 0.1.0 | 2026-07-25 | sk | = | · | · | = | = | · | — |
| `n8n-loops` | 0.1.0 | 2026-07-25 | sk | = | · | · | = | = | · | — |
| `n8n-node-configuration` | 0.1.0 | 2026-07-25 | sk | = | · | · | = | = | · | — |
| `n8n-speckle-aec-intake` | 0.2.1 | 2026-07-30 | sk | ~ | ~ | ~ | ~ | ~ | · | — |
| `n8n-subworkflows` | 0.1.0 | 2026-07-25 | sk | = | · | · | = | = | · | — |
| `n8n-webhook-intake-pattern` | 0.1.1 | 2026-07-27 | sk | ~ | · | · | ~ | ~ | · | — |
| `n8n-workflow-lifecycle` | 0.2.2 | 2026-07-29 | sk | ~ | · | · | ~ | ~ | · | — |
| `office-template-authoring` | 0.1.0 | 2026-07-29 | sk | — | ~ | — | — | — | — | — |
| `openclaw-vps-operator` | 0.1.1 | 2026-08-11 | sk | ~ | ~ | ~ | — | — | · | · |
| `pkg-receiver-protocol` | 0.5.0 | 2026-08-11 | sk | ~ | ~ | · | — | — | · | · |
| `rhino-grasshopper-speckle` | 0.2.0 | 2026-07-17 | sk | ~ | ~ | ~ | — | — | · | — |
| `skills-capitalize` | 0.1.10 | 2026-08-11 | sk | ~ | ~ | ~ | — | — | ~ | → |
| `speckle-intelligence-dashboards` | 0.1.0 | 2026-07-15 | sk | = | = | = | — | — | · | → |
| `test-incognitas-plantadas` | 0.1.0 | 2026-07-28 | sk | ~ | · | · | — | — | · | · |
| `umbral-brand-identity` | 0.1.2 | 2026-07-29 | sk | — | ~ | — | — | — | — | — |
| `umbral-rick-runtime` | 0.3.0 | 2026-08-04 | sk | ~ | ~ | ~ | — | — | · | · |
| `using-n8n-skills` | 0.1.4 | 2026-07-30 | sk | ~ | ~ | ~ | ~ | ~ | · | — |
| `visor-user-tester` | 0.1.0 | 2026-08-06 | sk | ~ | ~ | · | — | — | · | · |
| `agents-canonical-registry` | 0.1.0 | 2026-04-30 | ng | — | = | · | — | — | — | — |
| `cursor-hooks-sync` | 0.1.1 | 2026-07-27 | ng | — | = | · | — | — | — | — |
| `notion-context-routing` | 0.1.0 | 2026-04-30 | ng | — | = | · | — | — | — | — |
| `notion-contextual-email-draft` | 0.1.0 | 2026-04-30 | ng | — | = | · | — | — | — | — |
| `notion-duplicate-consolidation` | 0.1.0 | 2026-04-30 | ng | — | = | · | — | — | — | — |
| `notion-governance-expert` | 0.1.0 | 2026-04-30 | ng | — | = | **≠**(off) | — | — | — | — |
| `notion-normalize-page` | 0.1.0 | 2026-04-30 | ng | — | = | · | — | — | — | — |
| `notion-page-audit` | 0.1.0 | 2026-04-30 | ng | — | = | · | — | — | — | — |
| `notion-session-capitalization` | 0.1.0 | 2026-04-30 | ng | — | = | · | — | — | — | — |
| `notion-system-card` | 0.1.0 | 2026-04-30 | ng | — | = | · | — | — | — | — |
| `q-friday-retro` | 0.1.2 | 2026-07-28 | ng | — | = | · | — | — | — | — |
| `read-codex-handoffs` | 0.1.0 | 2026-05-03 | ng | — | = | · | — | — | — | — |
| `secret-output-guard` | 0.2.0 | 2026-07-27 | ng | — | ~ | · | — | — | — | — |

`[E]` script de solo lectura sobre los 46 `manifest.yaml`: resuelve cada `install_path`
(expandiendo `~` → `C:\Users\david` y `%APPDATA%`), compara `SHA256` crudo y `SHA256` del
contenido normalizado (`CRLF→LF`, `TrimEnd`) contra el `SKILL.md` canónico. Corrido
2026-08-12 ~06:10 UTC. Ninguna escritura.

Dos plataformas más quedan declaradas pero **100% `enabled: false`** y por eso no tienen
columna: `claude_code` (13 declaraciones, `install_path` relativo `.claude/skills/{slug}/`,
por-repo) y `cursor_rules` (10 declaraciones, transformer `skill_to_mdc`).

### 3.3 Conteo y naturaleza del "drift": no hay drift real

| Categoría | Conteo | Lectura |
|---|---|---|
| Targets `enabled: true` en los 46 manifests | **106** | universo real del deploy Windows |
| …desplegados y presentes | **106** (`AUSENTES = 0`) | **cobertura 106/106 = 100%** |
| `=` byte-idéntico | **41** | sin observaciones |
| `~` idéntico salvo EOL | **63** | CRLF del checkout Windows vs LF del canónico. **No es drift de contenido**: el hash del texto normalizado coincide exactamente |
| `→` derivado por transformer | **2** (`skills-capitalize` y `speckle-intelligence-dashboards` → `copilot_chat`) | **Esperado por diseño**: `transformer: skill_to_prompt` reescribe el frontmatter (`name` + `description` plegada → `mode: agent` + `description` en una línea) y produce un `.prompt.md`. Verificado leyendo ambas cabeceras |
| `≠` diferencia real de contenido en target `enabled: true` | **0** | — |
| Deploy residual con target `enabled: false` | **1** | `~/.cursor/skills/notion-governance-expert/SKILL.md`, escrito el **2026-03-30 01:02**, anterior a que ese target se deshabilitara; el canónico evolucionó desde entonces |
| Último apply del motor de sync | `2026-08-12 00:38:14` | `.sync-state.json` del registry; backups en `%LOCALAPPDATA%\umbral-skills-sync\20260812T043814Z` (y 043434Z, 035118Z) |

`[E]` mismo script + `Get-Item …LastWriteTime` para el residual + lectura de
`.sync-state.json` (`synced_at`) + `Get-ChildItem %LOCALAPPDATA%\umbral-skills-sync`.

**Lectura:** la superficie Windows del registry está **sana y fresca** — sync aplicado
cuatro minutos después del último ship, cobertura total, cero divergencia de contenido. Es
el contraste exacto con E4-VPS (6/86 con las 6 divergiendo byte a byte). Y el matiz que
importa: una comparación por hash crudo sobre estos mismos 106 targets habría reportado
**65 "DRIFT"** (63 EOL + 2 transformer) — un falso positivo del 61%. La medición válida
normaliza EOL y excluye targets con transformer no-`identity`.

### 3.4 Dos ecosistemas, no dos vistas del mismo: intersección de slugs = 0

| Ecosistema | Fuente canónica | Destino | Tamaño | Motor |
|---|---|---|---|---|
| **Registry** (Windows) | `C:\GitHub\umbral-skills-registry` (`skills/` + `notion-governance-skills/`) | `~/.claude`, `~/.codex`, `~/.cursor`, `~/.agents`, `~/.copilot`, `~/.gemini/antigravity`, `%APPDATA%/Code/User/prompts` | **46 skills / 106 targets ON** | `tools/sync_skills.py` + `ship_skill.py`, con `.sync-state.json` y backups |
| **OpenClaw** (VPS) | `openclaw/workspace-templates/skills/` en `umbral-agent-stack` | `~/.openclaw/skills/` del VPS | **86 plantillas**, 6 desplegadas (F2 §3) | sin motor equivalente documentado |

`[E]` `Get-ChildItem openclaw\workspace-templates\skills -Directory` → 86 ·
`skills/` + `notion-governance-skills/` → 46 · intersección de nombres calculada con
`Where-Object { $reg -contains $_ }` → **0**.

**Consecuencia para el paso 4/5:** el "6/86" de F2 y el "106/106" de F3 **no son el mismo
indicador visto desde dos máquinas**. Miden catálogos disjuntos, con motores distintos y
gobernanza distinta. Cualquier síntesis que los promedie o los contraste como "drift global
de skills" estaría mal. La pregunta real que abren juntos es de arquitectura, no de
medición: **¿por qué hay dos catálogos de skills sin un solo slug en común, y cuál es la
intención de cada uno?** — fila directa para E6/F4.

### 3.5 Fila `openclaw-vps-operator` (registry vs `main` UAS vs rama poller)

| Superficie | Estado observado | Evidencia [E] |
|---|---|---|
| **Registry (canónico)** | `skills/openclaw-vps-operator/` v **0.1.1**, `last_reviewed: 2026-08-11`. Layout completo: `SKILL.md` (5324 B) + `references/reference-diagnose.md` (6399 B) + `reference-mutate.md` (4791 B) + `reference-auth.md` (1942 B) — **el `reference-diagnose.md` que el plan asumía sí existe** | `Get-ChildItem -Recurse` sobre el slug; `manifest.yaml` |
| **Deploys Windows** | Presente y completo (SKILL.md + los 3 `references/`) en `~/.claude/skills/`, `~/.codex/skills/` y `~/.cursor/skills/`; los tres `~` (idénticos salvo EOL) | matriz §3.2 + `Get-ChildItem -Recurse` por destino |
| **`main` de UAS** | **Ausente — y por decisión explícita.** Commit `918dbe6`: *"chore(skills): remove local openclaw-vps-operator stubs after SoT ship (#585)"*. No está en `.claude/skills/` ni en `.agents/skills/` (que sí existe, con otras 4 skills: `openclaw-foundry-activation`, `secret-output-guard`, `vps-deploy-after-edit`, `windows-vps-execution-split`) | `git log -1 -- .claude/skills/openclaw-vps-operator`; `Get-ChildItem .agents\skills` |
| **Rama `rick-delivery/poller-healthcheck-hardening`** | No se tocó en F3 (prohibición del paquete). F2 ya la leyó vía `git show` y encontró una versión más vieja, sin `references/` | — (F2 §3) |
| **Referencias documentales rotas en `main`** | **2 vivas**: `.agents/PROTOCOL.md:178` ("Leer skill `openclaw-vps-operator` (`.agents/skills/openclaw-vps-operator/SKILL.md`)") y `.github/agents/operador-openclaw-vps.agent.md:37` (mismo path, en la definición del custom agent). Más ~6 menciones en tasks/audits históricos, que no son normativas | `Grep` del slug sobre `*.md` en el árbol |

**Reencuadre de la decisión #2 de F2.** F2 la planteó como *"¿restaurar el archivo en `main`
desde la branch poller, o formalizar que vive en otro lugar?"*. Con la evidencia de F3 esa
binaria se disuelve: **la skill ya está formalizada en otro lugar** (registry, v0.1.1,
completa, desplegada en los 3 runtimes Windows) y su salida de `main` fue un paso deliberado
del cierre SoT (#585). Restaurarla en `main` reintroduciría el doble escritor que ese PR
eliminó. Lo único que hay que arreglar es la **referencia documental** en los 2 archivos
normativos. Costo: trivial. Va como fila de paso 5.

### 3.6 Corrección a F2: `CLAUDE.md` no existe en `main`

F2 §3 afirma: *"`CLAUDE.md` (`Working Defaults`) y `.agents/PROTOCOL.md` (§Para Copilot-VPS)
citan `.agents/skills/openclaw-vps-operator/SKILL.md`"*, con [E] "lectura directa de ambos
archivos en `main`@`5b2cc8a`".

`[E]` de F3: `git ls-tree -r origin/main --name-only` filtrado por `(?i)(^|/)claude\.md$` →
**sin resultados**; tampoco existe en el working tree de este clon. Los archivos de contrato
trackeados son `AGENTS.md` (raíz) y `.agents/PROTOCOL.md`.

**Estado real:** la mitad `.agents/PROTOCOL.md:178` de la afirmación **se confirma**. La
mitad `CLAUDE.md` **no**: ese archivo no está en `main`. Si F2 lo leyó, fue un archivo
**untracked local del clon VPS**, no del repo — y en ese caso la corrección debe hacerse en
esa máquina, no en `main`. El segundo archivo normativo con la referencia rota es
`.github/agents/operador-openclaw-vps.agent.md:37`, que F2 no citó.

### 3.7 Filas candidatas para el paso 5 (E4-Windows) — ninguna aplicada aquí

| # | Fila | Costo estimado | Riesgo de no hacerlo |
|---|---|---|---|
| D1 | Corregir la referencia a `.agents/skills/openclaw-vps-operator/SKILL.md` en `.agents/PROTOCOL.md:178` y `.github/agents/operador-openclaw-vps.agent.md:37` → apuntar al registry (o a `~/.claude/skills/…`) | trivial | Todo agente que siga el protocolo al pie va a un path inexistente; ya le pasó a F2 |
| D2 | Decidir el residual `~/.cursor/skills/notion-governance-expert/` (target `off` desde algún punto entre 2026-03-30 y hoy, contenido divergente): borrarlo o rehabilitar el target | trivial | Cursor carga una versión de marzo de una skill de gobernanza que el canónico ya cambió |
| D3 | Declarar la política de EOL del motor de sync (¿LF forzado en destino, o CRLF aceptado como normal en Windows?) y hacer que `--reconcile` normalice antes de comparar | bajo | Cualquier auditoría futura por hash crudo vuelve a reportar 63 falsos "DRIFT" |
| D4 | Verificar si `CLAUDE.md` existe como archivo untracked en el clon VPS y, si sí, corregirlo allí (§3.6) | trivial | La afirmación de F2 queda flotando sin superficie donde arreglarse |
| D5 | **Arquitectura (va a E6/F4 antes que a paso 5):** dos catálogos de skills con intersección 0 — decidir si convergen, si se declaran deliberadamente separados, o si el de OpenClaw se retira | alto (decisión de diseño) | Se mantienen dos gobernanzas paralelas, una con motor y estado (registry) y otra sin él (OpenClaw) |

---

## 4. Gate

```
MEGADIAG_F3_CONTRACTS_PASS = Y
```

`[E]` por eje:

- **E3 — PASS.** Las 5 filas del inventario de workflows con `[E]` (§2.1); la línea de
  tiempo con 8 runs citados por id, fecha y resumen literal de pytest (§2.2); causa A con
  4 filas con `[E]` (§2.3); causa B con 5 filas con `[E]` incluida reproducción local
  (§2.4); baseline local con salida literal (§2.6); suites fuera del gate contadas (§2.7).
  Cero filas afirmadas sin evidencia. Cero `BLOCKED`.
- **E4-Windows — PASS.** 46 filas de la matriz slug→versión con estado por plataforma
  (§3.2), generadas por script de solo lectura sobre los 46 `manifest.yaml`; conteos
  reconciliados contra 106 targets `enabled: true` (§3.3); intersección con el catálogo
  OpenClaw calculada, no estimada (§3.4); fila `openclaw-vps-operator` con las 5 superficies
  (§3.5). Cero `BLOCKED`.

**Prohibiciones del paquete, verificadas:**

- Cero patches a tests o fixtures — el único comando que los tocó fue `pytest` en modo
  lectura; los reportes que genera van a `tmp_path` de pytest, no al repo.
- Cero `gh auth switch` — E7-bis.2 sigue `BLOCKED` como lo dejó F1, sin intento de
  desbloqueo. Todas las llamadas `gh` de F3 fueron contra `Umbral-Bot/umbral-agent-stack`,
  que el token activo sí resuelve.
- Cero mutación VPS: F3 no abrió ninguna sesión remota.
- Cero escritura en `umbral-skills-registry` (solo `git log/status/ls-remote/cat-file` y
  lecturas de archivo). Cero ship de skills.
- `rick/stage7_5-multiformat` y el worktree `poller-hardening`: no referenciados, no leídos,
  no tocados.
- Única escritura en disco de esta sesión: este archivo, la rama que lo contiene y dos
  scripts auxiliares en el scratchpad temporal de la sesión (fuera del repo).

## 5. Decisiones pedidas a David (consolidado F3)

1. **Binaria del fixture de Publicaciones (§2.3):** ¿la base Notion viva ya tiene las 12
   propiedades del schema 0.2.0? Si sí → refrescar snapshot + subir constante (A1+A2a). Si
   no → el WARN es real y lo que falta es aprovisionar la base (A2b). **Es la única de esta
   lista que no se puede responder desde Windows.**
2. **Deuda de CI (§2.7):** ¿se autoriza un pack de paso 5 que ponga `main` en verde con las
   filas A1 + B1 (las dos mecánicas, sin tocar contrato), dejando A2 pendiente de la
   respuesta 1?
3. **Referencias documentales rotas (§3.5, D1):** confirmar que la corrección es "apuntar al
   registry" y **no** restaurar la skill en `main` (lo cual revertiría #585).
4. **Registro fantasma `pytest.yml` (C1)** y **residual Cursor `notion-governance-expert`
   (D2):** dos limpiezas triviales — ¿entran al mismo pack de paso 5?
5. **Arquitectura de dos catálogos de skills (§3.4, D5):** intersección 0 entre registry (46)
   y plantillas OpenClaw (86). ¿Se lleva a F4 como fila de E6, o se decide antes?
