# P1.2 — Evaluación de las 3 KEEP_FOSSIL residuales (2026-08-07)

> **Pack:** PKG-UAS-P1-2-FOSSIL3-EVAL · rama `claude/pkg-uas-p1-2-fossil3-eval-20260807` ·
> base `9272310e`
> **GO de David:** evaluar las 3 `KEEP_FOSSIL` residuales post-cierre CHERRY (opción
> segura/higiénica/trazable) — solo recomendación por fila, **cero deletes, cero cherry-pick a
> superficies vivas en este pack**.
> **SoT:** [uas-p1-2-orphan58-analyze-capx-20260806.md](uas-p1-2-orphan58-analyze-capx-20260806.md) §2.2,
> [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.2.

Eje CHERRY de P1.2 cerrado (PRs #600–#601, más el pack anterior que no numero aquí por no tener
su PR a mano en este hilo — ver norte). #58 ya `KILL`. Estas son las últimas 3 ramas huérfanas sin
merge-base pendientes de decisión en todo el barrido de 90 originales.

Fuera de alcance (no tocado): `rick/stage7_5-multiformat` (KEEP_INDEFINITE, decisión de producto ya
tomada), PRs #541/#521, clones P1.3, evento calendar E2E.

---

## 0. Resumen ejecutivo

| # | Rama | Tip | Recomendación | Esfuerzo | Riesgo |
|---|---|---|---|---|---|
| 1 | `cursor/power-bi-libraries-formats-5c1b` | `6a64515c` | **RESCUE_SELECTIVE** (1 doc) | bajo | bajo — verificar vigencia del timeline PBIR antes de citarlo |
| 2 | `cursor/regression-test-coverage-b904` | `de318aff` | **RESCUE_SELECTIVE** (4 tests + helper, mismo archivo) | bajo | bajo — código de producción idéntico a `main`, patch de tests puro |
| 3 | `feat/bitacora-populate` | `fe5d3393` | **KILL_BRANCH** | ninguno | bajo — el enfoque que proponía ya fue descartado en R14 a favor de `enrich_bitacora_page` |

**Corrección a evidencia previa (importante):** el acta original del 2026-08-06 daba la fila 1 como
"tema no aparece en ningún otro lugar del proyecto activo" y la fila 2 como diferenciada del swarm
sin comparar contenido. Ambas lecturas quedan corregidas abajo con evidencia nueva — ver §1 y §2.

Reconfirmación previa a evaluar: los 3 tips coinciden exactamente con los esperados por el pack y
ninguno tiene merge-base con `origin/main` (`git merge-base` exit 1 en las 3).

**Nada se ejecutó en este pack** — cero cherry-pick, cero delete. Es evaluación con evidencia para
que un GO posterior de David sea selectivo por fila.

---

## 1. `cursor/power-bi-libraries-formats-5c1b` → RESCUE_SELECTIVE

Commit único, **2026-03-05**. Único path real (sin ruido `.claude/.codex/.cursor`, no hay ninguno
en esta rama): `docs/63-powerbi-librerias-formatos-pbix-pbip.md`.

**Contenido:** investigación sustancial y accionable — compara los 4 formatos Power BI
(`.pbix/.pbit/.pbip/.pbir`), documenta el timeline de Microsoft hacia PBIR como default (Service
ene-2026, Desktop mar-2026, GA Q3-2026), tabula ~20 librerías/herramientas (Python: `powerbpy`,
`pbir-utils`, `pypbireport`; .NET: `pbi-tools`, `Tabular Editor`; APIs REST de Fabric/Power BI) con
capacidad y limitaciones de cada una, y concluye con recomendación explícita: **"Formato
recomendado: PBIP/PBIR"** + pipeline propuesto.

**El encargo original existe en `main`:** `.agents/tasks/2026-03-04-073-r16-research-powerbi-librerias-formatos.md`
pedía exactamente este entregable con criterio de éxito "PR abierto a `main`" — el PR nunca se
mergeó, el doc quedó huérfano solo en esta rama cola.

**Corrección a la nota KEEP_FOSSIL previa:** el tema **no** está ausente del proyecto activo. `main`
tiene dos skills runtime vivas — `openclaw/workspace-templates/skills/power-bi/SKILL.md` (DAX/Power
Query/REST API) y `speckle-dalux-powerbi/SKILL.md` (BIM Speckle+Dalux→Power BI, dominio central
AEC) — pero **ninguna menciona `.pbix/.pbip/.pbir`** (grep vacío): el contenido de este doc
(generación programática de archivos) no está duplicado, complementa directamente esos dos skills.

**Recomendación:** RESCUE_SELECTIVE del único archivo a `main` (destino: mismo path,
`docs/63-powerbi-librerias-formatos-pbix-pbip.md`, o bajo un índice de docs si `main` usa uno —
verificar convención de `docs/NN-*.md` antes de aterrizarlo). **Antes de aterrizarlo**, re-verificar
si el timeline PBIR GA Q3-2026 citado ya se cumplió (estamos en agosto 2026) para no publicar un
dato potencialmente obsoleto como vigente sin nota.

**Esfuerzo:** bajo. **Riesgo:** bajo. **Qué NO hacer:** no fusionar la rama completa (1564+ archivos
de historia disjunta ya cubiertos por `main`); no crear el skill nuevo que el doc sugiere sin GO de
producto aparte — eso es un paso posterior.

---

## 2. `cursor/regression-test-coverage-b904` → RESCUE_SELECTIVE

0 paths únicos por nombre (el path relevante, `tests/test_security_regression.py`, ya existe en
`main` con el mismo nombre) — la evaluación fue de **contenido**, no de presencia.

**Línea count:** tip = 473 líneas, `main` = 324 líneas. Producción: `worker/app.py` difiere 18
líneas, pero es `main` quien tiene *más* (una feature de `error_classification` posterior que el
tip no tiene — no hay nada que rescatar ahí, al revés). `worker/rag/retriever.py`,
`worker/client_auth.py`, `worker/rag/indexer.py`: sin diff, idénticos.

**main SÍ cubre hoy:** privilege escalation admin tasks (5 tests), enqueue tier bypass (1),
limiter bounded + `OrderedDict` (sin probar eviction real), duplicate-parse, chunk_text safety (4),
E2E lifecycle. Incluye un test de OData escaping, pero **débil**: solo valida el `.replace()` de
comillas inline, sin ejercitar `retriever.py` real.

**Delta real que aporta el tip (ausente en `main`), 3 funciones + 1 helper:**
1. `test_free_client_over_daily_limit_gets_429` — prueba el 429 "Daily limit exceeded" vía
   `/enqueue`; `main` no tiene ningún test de este límite (solo de tier bypass).
2. `test_source_filter_with_single_quote` (rehecho) + `test_vector_mode_uses_vector_query` —
   mockea `azure.search.documents` completo y llama `retriever.search()` real, verificando el
   string OData exacto y el modo vector (`VectorizedQuery`, `k_nearest_neighbors`, `fields`).
3. `test_client_limiters_lru_eviction` — prueba la eviction LRU real (4 clientes, límite 3) vía
   HTTP real; `main` solo verifica que el dict es `OrderedDict`, no que la eviction funcione.
4. Helper `_install_fake_azure_modules` + imports `sys`, `types`, `get_tier_config` que esas
   funciones requieren.

Verificado: el código de producción que estos 3 tests ejercitan (`_MAX_CLIENT_LIMITERS`, la
eviction `while len(_client_limiters) > _MAX_CLIENT_LIMITERS`, el 429 "Daily limit exceeded") ya
existe intacto y sin cambios en `main` — el delta es puro test, cero riesgo de incompatibilidad de
producción.

**Corrección a la nota KEEP_FOSSIL previa:** `main` **no** es superset de este tip, como asumía
implícitamente el acta previa al no comparar contenido — le faltan 3 funciones de test con
cobertura real más fuerte que las equivalentes actuales.

**Recomendación:** RESCUE_SELECTIVE — traer a `main` únicamente el bloque de las 4 funciones +
helper de `tests/test_security_regression.py` (patch puntual sobre ese único archivo, sin tocar
producción). No fusionar la rama completa: revertiría la feature `error_classification` de
`worker/app.py` que `main` ya tiene y no tiene el tip.

**Esfuerzo:** bajo (~15 min, patch aplica limpio, contexto alrededor sin cambios). **Riesgo:** bajo.
**Qué NO hacer:** `git merge`/checkout de la rama completa; marcarla KILL_BRANCH sin rescatar antes
estos 4 tests.

---

## 3. `feat/bitacora-populate` → KILL_BRANCH

290 archivos en el árbol de la rama; confirmado que no hay más paths huérfanos que los 2 ya
señalados: `scripts/populate_bitacora.py` + `tests/test_notion_bitacora.py`.

**`scripts/populate_bitacora.py`:** CLI (`--dry-run`, `--tasks-only`, `--skip-inferred`) que combina
~20 `BitacoraEntry` hardcodeadas (historia Hackathon→R13) con entradas inferidas de
`.agents/tasks/*.md`, e inserta páginas nuevas en la DB Notion `NOTION_BITACORA_DB_ID` (default
`85f89758684744fb9f14076e7ba0930e`) vía `notion.append_bitacora`. Es un poblador **one-shot
histórico** con fechas fijas de marzo, **sin idempotencia** — re-ejecutarlo hoy duplicaría filas en
la DB real de gobernanza.

**`tests/test_notion_bitacora.py`:** todo mockeado, sin pegar contra Notion real; cubre funciones
(`append_bitacora` en `notion_client.py`/`tasks/notion.py`, `NOTION_BITACORA_DB_ID` en config) que
**no existen en `main`**.

**¿"Bitácora" sigue viva?** Sí, pero por otra vía ya construida y documentada: `worker/tasks/notion.py`
registra `notion.enrich_bitacora_page` (no `append_bitacora`), y
`scripts/enrich_bitacora_pages.py` + `scripts/add_resumen_amigable.py` + `docs/bitacora-scripts.md`
operan sobre la misma DB ID pero **solo enriquecen páginas existentes** (asumen que ya están
creadas). El propio task `.agents/tasks/2026-03-04-063-r14-...md` en `main` documenta la
bifurcación: *"Task `notion.enrich_bitacora_page` (o extender `append_bitacora`)"* — R14 evaluó
extender `append_bitacora` y en su lugar construyó `enrich_bitacora_page`. `append_bitacora` nunca
se implementó pese a 5+ rondas posteriores de trabajo sobre bitácora (R14–R21).

**Recomendación:** KILL_BRANCH. No es DEFER_PRODUCT — no hay ambigüedad pendiente, la bifurcación
ya se resolvió en R14 sin adoptar este script. No es ARCHIVE_DOCS_ONLY tampoco:
`docs/bitacora-scripts.md` y los task files de `main` ya documentan esta historia suficientemente;
un archivo nuevo sería redundante.

**Esfuerzo:** ninguno (cerrar/borrar la rama). **Riesgo:** bajo; el riesgo real está en ejecutar el
script (generaría filas duplicadas en la DB de gobernanza), no en borrar la rama. **Qué NO hacer:**
no portar `append_bitacora` tal cual, no escribir doc de archivo nuevo.

---

## 4. Pack de ejecución sugerido (orden, si David da GO)

1. **RESCUE_SELECTIVE fila 2** (tests) — menor esfuerzo, mayor valor inmediato (cobertura de
   seguridad real hoy ausente en `main`), cero riesgo de producción.
2. **RESCUE_SELECTIVE fila 1** (doc Power BI) — bajo esfuerzo, valor de referencia para las 2 skills
   Power BI vivas. Verificar vigencia del timeline PBIR antes de aterrizarlo.
3. **KILL_BRANCH fila 3** — sin dependencias de las otras dos, puede ejecutarse en cualquier
   momento u orden.

---

## 5. Prohibido (respetado)

- Cero `git checkout` de paths a `main` — toda lectura vía `git show`/`git ls-tree`/`git cat-file`/
  `git diff` de 2 puntos sobre refs remotos.
- Cero `git push --delete` de las 3 ramas ni de `rick/stage7_5-multiformat`.
- Cero `git add -f` de paths gitignoreados (no aplicó en este pack — ninguno de los paths
  evaluados está en `.gitignore`).
- Cero touch a `#541`/`#521`.
- Cero ampliación de alcance a clones P1.3.
- Cero touch a VPS/Notion live (se leyó únicamente el contenido de los blobs para juzgar valor).

---

## 6. Actualización norte §5 P1.2

Ver [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.2: se agrega
"fossil3 eval **DONE**" — 2 RESCUE_SELECTIVE + 1 KILL_BRANCH recomendados con evidencia. Ejecución
queda `PENDING` GO de David por fila.
