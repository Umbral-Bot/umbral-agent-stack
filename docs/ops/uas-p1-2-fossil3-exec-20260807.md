# P1.2 — Ejecución de las 3 recomendaciones FOSSIL3 (2026-08-07)

> **Pack:** PKG-UAS-P1-2-FOSSIL3-EXEC · rama `claude/pkg-uas-p1-2-fossil3-exec-20260807` ·
> base `c83dbae6`
> **GO de David (verbatim):** "go a todo lo que indicas en orden" — filas 2→1→3 del acta FOSSIL3.
> **SoT:** [uas-p1-2-fossil3-eval-20260807.md](uas-p1-2-fossil3-eval-20260807.md),
> [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.2.

Reconfirmación previa a tocar nada: los 3 tips coincidieron exactamente con los esperados por el
pack y ninguno tenía merge-base con `origin/main` (`git merge-base` exit 1 en los 3).

---

## 0. Resultado en una línea por paso

| Paso | Fila | Rama fuente | Acción | Estado |
|---|---|---|---|---|
| 1 | 2 | `cursor/regression-test-coverage-b904` @ `de318aff` | RESCUE_SELECTIVE (4 tests + helper) | **DONE** + rama **KILL** |
| 2 | 1 | `cursor/power-bi-libraries-formats-5c1b` @ `6a64515c` | RESCUE_SELECTIVE (1 doc + nota de vigencia) | **DONE** + rama **KILL** |
| 3 | 3 | `feat/bitacora-populate` @ `fe5d3393` | KILL_BRANCH | **DONE** |

---

## 1. Paso 1 — RESCUE fila 2 (tests de seguridad)

Delta puntual sobre `tests/test_security_regression.py` (473 líneas en el tip → 473 líneas en
`main` tras el patch, exacto), sin tocar ningún archivo de producción. Confirmado antes de empezar:
`worker/app.py` de `main` conserva la feature `error_classification` que el tip no tenía — el patch
se aplicó **solo** sobre el archivo de tests, verificado con `git diff --stat` limitado a ese path.

Bloques traídos (imports `sys`, `types`, `get_tier_config` + los 4 bloques de test citados en el
acta):
- `test_free_client_over_daily_limit_gets_429` (dentro de `TestEnqueueTierEnforcement`).
- Helper `_install_fake_azure_modules` + `test_source_filter_with_single_quote` (versión más
  fuerte, ejercita `worker/rag/retriever.py` real) + `test_vector_mode_uses_vector_query` (dentro
  de `TestODataInjection`, reemplazando el test trivial anterior).
- `test_client_limiters_lru_eviction` (dentro de `TestLimiterBounds`, junto al
  `test_client_limiters_are_bounded` preexistente, sin removerlo).

**Validación:**

```
WORKER_TOKEN=test python -m pytest tests/test_security_regression.py -v
============================= 19 passed in 1.46s ==============================
```

19/19 PASS al primer intento — no hizo falta ciclo ajustar→testear, los 15 tests preexistentes de
`main` siguen pasando sin modificación.

**Cierre de código:** no había PR abierto todavía en este punto del pack para invocar el
`/code-review` automatizado basado en GitHub (ese flujo necesita un PR ya publicado). Se hizo un
review manual del diff completo: imports ordenados alfabéticamente, espaciado PEP8 consistente (2
líneas en blanco en los 3 puntos de inserción, igual que el resto del archivo), aislamiento correcto
de estado global (`monkeypatch.setattr`/`setitem` con reversión automática, `try/finally` en el test
de LRU eviction que limpia `_client_limiters` incluso si el assert falla), cero código de producción
tocado. Sin hallazgos.

**Post-check delete:** `gh pr list --head cursor/regression-test-coverage-b904 --state open` → `[]`
→ `git push origin --delete` → `git ls-remote --heads` vacío, confirmado.

---

## 2. Paso 2 — RESCUE fila 1 (doc Power BI)

Path destino: `docs/63-powerbi-librerias-formatos-pbix-pbip.md` — confirmado sin colisión
(`git ls-tree origin/main -- 'docs/63-*'` vacío antes de aterrizarlo).

**Nota de vigencia** insertada bajo el H1 (2026-08-07), verificada con `WebSearch` contra el blog
oficial de Microsoft Power BI en vez de solo marcar "sin revalidar":
- El default en Power BI Service (ene–feb 2026) llegó según lo previsto.
- El default en Desktop **se retrasó a mayo 2026** (la investigación original de marzo-2026 decía
  "marzo 2026") — corrección documentada en la nota.
- GA (Q3 2026, en curso a la fecha de este pack) **no tiene confirmación pública** de haber
  ocurrido ya — se deja marcado explícitamente para revalidar antes de tratarla como hecho
  consumado, tal como exigía el pack.
- Fuente citada: [PBIR will become the default Power BI Report Format — Microsoft Power BI Blog](https://powerbi.microsoft.com/en-us/blog/pbir-will-become-the-default-power-bi-report-format-get-ready-for-the-transition/).

No se creó skill nueva ni se tocó `openclaw/workspace-templates/skills/power-bi/` ni
`speckle-dalux-powerbi/` (confirmado: `git status --porcelain` sobre esos dos paths, vacío antes y
después del commit).

**Post-check delete:** `gh pr list --head cursor/power-bi-libraries-formats-5c1b --state open` →
`[]` → `git push origin --delete` → `git ls-remote --heads` vacío, confirmado.

---

## 3. Paso 3 — KILL fila 3 (bitácora populate)

Sin rescate: el acta FOSSIL3 encontró que R14 ya evaluó y descartó el enfoque `append_bitacora`
que proponía `scripts/populate_bitacora.py`, a favor de `enrich_bitacora_page` (ya construido y
documentado en `docs/bitacora-scripts.md` de `main`). No se portó `scripts/populate_bitacora.py`
ni `tests/test_notion_bitacora.py`, ni se inventó `append_bitacora` en `worker/` — tal como exigía
el pack.

`gh pr list --head feat/bitacora-populate --state open` → `[]` → `git push origin --delete` →
`git ls-remote --heads` vacío, confirmado.

---

## 4. Post-check consolidado

```
Borradas (3, confirmado ls-remote vacío):
cursor/regression-test-coverage-b904
cursor/power-bi-libraries-formats-5c1b
feat/bitacora-populate

Excluidas, verificadas sin tocar:
rick/stage7_5-multiformat   a2635398   (KEEP_INDEFINITE, decisión de producto previa)
#541 OPEN (claude/plan-sys-diag-openclaw-worksystem-2026-07-17)
#521 OPEN (copilot/docs-openclaw-models-hygiene-20260704)
```

## 5. Prohibido (respetado)

- Cero merge/ff de las 3 ramas fuente — todo por `git show`/patch puntual sobre archivos concretos.
- Cero checkout de rama completa sobre el working tree.
- Cero touch a `rick/stage7_5-multiformat`, `#541`, `#521`, VPS, Notion live.
- Cero ampliación a clones P1.3.
- Cero `git add -f` de paths gitignoreados (no aplicó — ninguno de los 2 paths rescatados está en
  `.gitignore`).

---

## 6. Cierre del eje P1.2

Con este pack, las **90 ramas huérfanas originales** de P1.2 quedan resueltas en su totalidad:
mergeadas-kill (192, incluye duplicados de otros ejes), huérfanas-con-merge-base (32: 28 kill + 1
rescue + 3 keep), orphan58 sin merge-base (58: 49 kill_safe + 5 cherry evaluadas y ejecutadas + 4
keep_fossil, de las cuales 3 evaluadas y ejecutadas aquí + 1 `stage7_5` KEEP_INDEFINITE por decisión
de producto explícita). No queda ninguna rama huérfana de P1.2 sin decisión documentada.

## 7. Actualización norte §5 P1.2

Ver [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.2: **fossil3 EXEC
DONE** (2 RESCUE + 1 KILL). Residuales fuera de este eje: `rick/stage7_5-multiformat`
KEEP_INDEFINITE, `#541`/`#521` sin relación, clones P1.3 (fila propia del norte, sin tocar).
