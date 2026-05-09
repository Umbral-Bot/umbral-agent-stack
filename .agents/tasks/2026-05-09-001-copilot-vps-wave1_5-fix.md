---
task_id: 2026-05-09-001
title: Wave 1.5 Fix — suite verde + hash contract + carrusel/video reporte
assigned_to: copilot-vps
status: open
priority: high
created: 2026-05-09
branch: wave1.5-integration
pr: 400
depends_on: 2026-05-08-001-copilot-vps-wave1_5-integration
---

# Wave 1.5 Fix — Pre-merge cleanup para PR #400

> **Contexto:** PR #400 (`wave1.5-integration` → `main`) recibió revisión externa.
> Veredicto: "puede reemplazar las 6 PRs originales" pero NO listo para quitar
> `do-not-merge`. Este fix resuelve los blockers identificados sin abrir nuevas
> features ni reabrir las PRs originales.
>
> **Trabajar SOBRE `wave1.5-integration` directo.** No crear branch nueva.
> Push a la misma branch para actualizar PR #400.
>
> **Restricciones no negociables (idénticas a Wave 1.5):**
> - 0 publicaciones reales.
> - 0 writes a Notion.
> - 0 modificaciones a Stage 7.5 (`scripts/discovery/stage7_5_*`).
> - Mantener PRs #394–#399 + #400 todas draft + label `do-not-merge`.
> - No crear DBs en Notion.
> - No escribir gates humanos.

> **Incidente operativo menor (2026-05-09, registrado para trazabilidad):**
> el commit que introdujo este task file en `main` (`8b06a3e`) incluyó por
> error 6 archivos que pertenecían solo a `wave1.5-integration` (residuo
> staged de un temp clone reutilizado). Limpiado inmediatamente con commit
> de revert `b3a2007` en `main`. NO se hizo force-push ni reescritura de
> historia; la branch `wave1.5-integration` quedó intacta con sus 6 archivos
> originales. No requiere acción adicional. Documentado solo como incidente
> operativo.

---

## Decisiones técnicas pre-tomadas (NO re-deliberar)

Las 3 decisiones de arquitectura ya están tomadas por David vía Copilot Chat.
Implementar literal, no abrir alternativas:

1. **Test failing → opción (c) del reporte §10:** inyección de `dedup` por
   parámetro en `publish_one` (o equivalente). Eliminar la dependencia frágil
   de `sys.modules` + atributo cacheado del paquete padre. Es la opción
   alineada literal con el espíritu del criterio #8a del brief original
   ("eliminar dependencia de fakes/lazy assumptions").

2. **Hash rename → solo docs + alias en código.** NO migración SQLite, NO
   rename de columnas. Renombrar conceptualmente:
   - `content_hash` (lo que existe hoy) = `source_content_hash` semánticamente
     (identidad de la señal/fuente: URL+title+excerpt).
   - `publication_content_hash` o `approved_copy_hash` = contrato DIFERIDO
     que se computará sobre el copy final post-S6/S7 cuando ese path exista.
   Implementación mínima: alias en `lib/dedup.py` + actualizar
   `docs/editorial-pipeline/hash-contract.md` para separar los dos contratos.

3. **Carrusel/video → solo reporte.** El brief permite explícitamente:
   "Si no se implementa ahora, entonces el reporte debe decir explícitamente
   NO cumplido / Wave 2, no 'resuelto'." NO tocar `variants.py` (rompería los
   38 tests de H5). Solo corregir el reporte para marcarlo NO cumplido + Wave 2.

---

## Fase 1 — Setup

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
git fetch origin wave1.5-integration:wave1.5-integration
git checkout wave1.5-integration
git pull --ff-only origin wave1.5-integration

# baseline assertion
PYTHONPATH=. python -m pytest tests/discovery/ tests/lib/ -q 2>&1 | tail -5
# Esperado: 402 passed, 1 failed (el test que vamos a arreglar)
```

---

## Fase 2 — Fix del test failing (decisión 1: opción c)

### 2.1 Identificar el callsite

```bash
grep -nE "from scripts\.discovery\.lib import dedup|import dedup as _dedup|publish_one" \
  scripts/discovery/stage9c_linkedin_publish.py scripts/discovery/lib/publish_guard.py
```

El brief reporte §10 indica `stage9c_linkedin_publish.py:407` como el callsite
problemático. Verificar línea exacta antes de tocar.

### 2.2 Refactor (opción c)

Cambiar `publish_one` (o función equivalente que llame a `register_published`)
para que reciba `dedup` como parámetro inyectable, con default = módulo real:

```python
# scripts/discovery/stage9c_linkedin_publish.py
from scripts.discovery.lib import dedup as _real_dedup

def publish_one(
    *,
    proposal_id,
    state_db,
    notion_fetcher,
    http_client,
    dedup_module=None,   # <-- nuevo parámetro inyectable
    publish_guard_module=None,  # <-- idem si publish_guard.assert_can_publish lo usa
    # ... resto de params existentes ...
):
    dedup = dedup_module if dedup_module is not None else _real_dedup
    # ...
    # En el path donde hoy hace `from scripts.discovery.lib import dedup as _dedup`
    # y luego `_dedup.register_published(...)`, usar la variable local `dedup`.
    dedup.register_published(...)
    # ...
```

**Si `publish_guard.assert_can_publish` también hace `from … import dedup`
internamente (reportado en §10 como callsite alternativo):** o bien
(a) `assert_can_publish` recibe también `dedup_module=None` opcional, o
(b) `publish_one` resuelve el dedup una sola vez y lo pasa a `assert_can_publish`
explícito. Preferir (b) — un solo punto de resolución.

### 2.3 Actualizar tests para inyectar el fake

En `tests/discovery/test_stage9c_idempotency.py` (y cualquier otro test que use
`monkeypatch.setitem(sys.modules, "scripts.discovery.lib.dedup", fake_dedup)`):

- Eliminar el `monkeypatch.setitem(sys.modules, ...)` del fixture si solo se
  usaba para este propósito (no romper otros tests que dependan de él para
  otras razones).
- Pasar el fake explícito: `publish_one(..., dedup_module=fake_dedup)`.

### 2.4 Validación obligatoria

```bash
# Test puntual
PYTHONPATH=. python -m pytest tests/discovery/test_stage9c_idempotency.py -v

# Suite parcial discovery
PYTHONPATH=. python -m pytest tests/discovery/ -q

# Suite completa que el reporte original midió
PYTHONPATH=. python -m pytest tests/discovery/ tests/lib/ -q
```

**Criterio de salida fase 2:** la última línea debe decir `XXX passed` con
**0 failed**. Si hay flakiness o un test colateral rompe, NO seguir hasta
que la suite quede estable. Capturar output literal para el reporte.

### 2.5 Commit

```bash
git add scripts/discovery/stage9c_linkedin_publish.py \
        scripts/discovery/lib/publish_guard.py \
        tests/discovery/test_stage9c_idempotency.py
# Si hubo otros tests tocados por el cambio de firma, agregarlos también.
git commit -m "wave1.5-fix(test): inject dedup module into publish_one to remove sys.modules dependency

Fixes test_stage9c_idempotency::test_successful_post_calls_register_published
failing in full suite (reported in wave1.5 integration report §10).

Root cause: monkeypatch.setitem(sys.modules, ...) did not propagate to the
parent package attribute, so 'from scripts.discovery.lib import dedup' inside
publish_one resolved to the real module instead of the fake.

Fix (option c per integration report): publish_one now accepts dedup_module
parameter (default = real module). Tests inject the fake explicitly.
This eliminates the lazy resolution path that the brief criterion #8a asked
to remove ('eliminar dependencia de fakes/lazy assumptions').

Suite: tests/discovery/ + tests/lib/ now 0 failed."
```

---

## Fase 3 — Hash contract: alias + docs (decisión 2)

### 3.1 Agregar alias en código (zero schema change)

En `scripts/discovery/lib/dedup.py`, agregar al final del archivo:

```python
# --- Wave 1.5 Fix: contract aliases ---
# `content_hash` semánticamente representa identidad de la fuente/señal
# (URL + title + excerpt del referente origen). Por contrato, NO representa
# el copy final que se publicaría — ese hash (publication_content_hash) se
# computará en S10 sobre el copy aprobado y NO existe en Wave 1.5.
# Ver: docs/editorial-pipeline/hash-contract.md §1bis.
compute_source_content_hash = compute_content_hash
"""Alias semántico de compute_content_hash. Identidad de la fuente/señal,
NO del copy final aprobado para publicación."""
```

**No tocar callsites existentes.** El alias permite que código futuro use el
nombre correcto sin romper el actual.

### 3.2 Actualizar `docs/editorial-pipeline/hash-contract.md`

Reemplazar/extender §1 con dos secciones:

**§1a — Hashes de identidad de señal (implementados Wave 1):**

| Hash | Inputs | Stage | Purpose |
|---|---|---|---|
| `dedup_hash` (alias `signal_hash`) | `sha256(canonical_url + "\n" + (published_at or ""))` | S1 (H2) | Discovery dedup |
| `content_hash` (alias semántico `source_content_hash`) | `sha256(canonical_url + "\n" + normalize(title) + "\n" + normalize(excerpt))` | S2 (H3) | **Identidad de la fuente/señal**, no del copy publicable |
| `idempotency_key` | `sha256(canonical_url + "\n" + content_hash)` | S2 (H3) | Idempotencia downstream sobre la **señal**, no sobre el copy final |

**§1b — Hash de contenido publicable (DIFERIDO, no implementado en Wave 1.5):**

> **Contrato pendiente.** `publication_content_hash` (o `approved_copy_hash`)
> debe computarse sobre el copy final aprobado en S6/S7, NO sobre los inputs
> de la señal origen. Este hash es el que `register_published` debería
> consultar para idempotencia REAL del POST a LinkedIn. Hoy
> `register_published` usa `content_hash` (= `source_content_hash`); esto
> constituye un **guard provisional aceptable para Wave 1.5 mientras no
> exista `publication_content_hash`, y NO representa idempotencia final
> de publicación**. Cualquier divergencia entre la señal origen y el copy
> final aprobado (variantes editoriales en S6/S7, ediciones humanas) hará
> que la idempotencia actual proteja la identidad equivocada.
>
> **Wave 2 ticket (obligatorio antes de cualquier publicación real):**
> definir, computar y persistir `publication_content_hash` en
> `published_history` separado de `content_hash`. Migrar
> `register_published` para consultar el nuevo hash.

Reemplazar/extender §3 (edge case `published_at` ausente): añadir nota
explícita de que la "estabilidad" del `dedup_hash` con `published_at=None`
NO previene colisión entre dos URLs idénticos sin pubDate (caso real RSS).
Marcar como **riesgo R1 documentado**, no como problema resuelto.

### 3.3 Commit

```bash
git add scripts/discovery/lib/dedup.py docs/editorial-pipeline/hash-contract.md
git commit -m "wave1.5-fix(hash-contract): separate source_content_hash from publication_content_hash

External review flagged that 'content_hash' was documented as 'identity of
the content that would be published', but is actually computed over the
source signal (canonical_url + title + excerpt), NOT over the approved copy
that would be POSTed to LinkedIn.

Changes:
- Add semantic alias compute_source_content_hash = compute_content_hash in
  lib/dedup.py (zero schema change, zero callsite change).
- hash-contract.md §1 split into:
  - §1a: source-identity hashes (dedup_hash, content_hash/source_content_hash,
    idempotency_key) — implemented in Wave 1.
  - §1b: publication_content_hash (a.k.a. approved_copy_hash) — DEFERRED.
    Wave 2 must define, compute and persist it separately, and migrate
    register_published to use it.
- §3 edge case 'published_at ausente' upgraded from 'stable' to 'documented
  risk R1' (collision possible between two URLs with no pubDate)."
```

---

## Fase 4 — Carrusel/video: corregir reporte (decisión 3)

### 4.1 Editar `docs/audits/2026-05-08-wave1_5-integration-report.md`

**§3 cross-conflict #8** — cambiar columna "Estado":

```diff
-| 8 | Ambigüedad Canal vs Tipo de contenido/Formato (carrusel/video) | review externa | docs vagos | scripts/discovery/lib/variants.py define PLATFORMS = ("linkedin","x","blog","newsletter","carousel","video") → carrusel/video son tratados como plataformas, no formatos | **Postponed Wave 2 (junto con D2)** |
+| 8 | Ambigüedad Canal vs Tipo de contenido/Formato (carrusel/video) | review externa | docs vagos | scripts/discovery/lib/variants.py define PLATFORMS = ("linkedin","x","blog","newsletter","carousel","video") → carrusel/video son tratados como plataformas, no formatos | **NO cumplido en Wave 1.5 — deuda explícita Wave 2.** Brief original pedía confirmar carrusel/video como `formato`, no como `Canal`. Implementación H5 dejó ambos como plataformas. No se corrige en este fix porque rompería 38 tests H5; corrección semántica + refactor de tests es scope Wave 2. |
```

**§12 backlog** — reordenar item 4 (Canal vs Formato) al **top de la lista**
con tag `[CARRY-OVER WAVE 1.5]` para que sea inmediatamente visible:

```markdown
## 12. Wave 2 backlog

1. **[CARRY-OVER WAVE 1.5]** Ambigüedad Canal vs Formato — separar
   `PLATFORMS = (linkedin, x, blog, newsletter)` de
   `FORMATS = (carousel, video, thread, post_largo, post_corto, ...)` en
   `variants.py`. Refactor de los 38 tests H5 que asumen el shape actual.
   **Brief original Wave 1.5 lo pidió como criterio §7a; quedó NO cumplido.**
2. **[CARRY-OVER WAVE 1.5]** `publication_content_hash` separado de
   `source_content_hash` — definir, computar sobre copy final post-S6/S7,
   persistir en `published_history`, migrar `register_published` para usarlo.
   **Brief original Wave 1.5 lo pidió como criterio §8c; quedó NO cumplido.**
3. D2 — definir canónico de S6 (...). [resto del backlog original sin cambios]
```

**§11 recomendación final por PR** — añadir nota arriba de la tabla:

```markdown
> **Estado post-Wave 1.5 Fix (2026-05-09):** suite verde, hash contract
> corregido, carrusel/video documentado como deuda Wave 2 explícita.
> PR #400 listo para review final antes de quitar `do-not-merge`.
```

### 4.2 Reflejar correcciones en sección §10

Añadir bloque al final de §10:

```markdown
## 10bis. Wave 1.5 Fix (2026-05-09)

| Item | Estado pre-fix | Estado post-fix | Commit |
|---|---|---|---|
| `test_stage9c_idempotency::test_successful_post_calls_register_published` | 1 failed en suite completa | **PASSED** en suite completa | <hash commit fase 2> |
| Suite total tests/discovery/ + tests/lib/ | 402 passed / 1 failed | **XXX passed / 0 failed** | <ídem> |
| `content_hash` documentado como "contenido final" (engañoso) | sí | corregido — alias `source_content_hash` + contrato `publication_content_hash` diferido explícito | <hash commit fase 3> |
| Carrusel/video declarado "Postponed Wave 2" sin admitir incumplimiento | sí | **corregido — declarado NO cumplido + carry-over backlog top** | <hash commit fase 4> |
```

### 4.3 Commit

```bash
git add docs/audits/2026-05-08-wave1_5-integration-report.md
git commit -m "wave1.5-fix(report): mark carousel/video as NOT met + add §10bis fix log + reorder Wave 2 backlog

External review flagged two cases of 'Postponed Wave 2' being too lenient:
- §3 cross-conflict #8 (carousel/video as Canal vs Formato): brief criterion
  §7a explicitly required confirming carousel/video as 'formato'. Implementation
  left them as platforms in variants.PLATFORMS. Now declared NOT met + Wave 2
  carry-over with explicit reference to original brief criterion.
- §1 hash contract (content_hash as 'final publishable content'): brief
  criterion §8c. Implementation computes over source signal. Now corrected
  via dedup.py alias (Fase 3) + this report references both as carry-over.

Added §10bis as fix log mapping pre/post status with commit hashes."
```

---

## Fase 5 — Re-validación end-to-end

### 5.1 Suite completa

```bash
PYTHONPATH=. python -m pytest tests/discovery/ tests/lib/ -q 2>&1 | tee /tmp/wave15-fix-suite.log
tail -3 /tmp/wave15-fix-suite.log
```

**Criterio:** última línea = `XXX passed in Y.Ys` con **0 failed**.
Si falla → STOP. Reportar y NO pushear hasta resolver.

### 5.2 Stage 7.5 freeze re-confirmado

```bash
git diff main wave1.5-integration -- 'scripts/discovery/stage7_5_*' | wc -l
# Esperado: 0
```

### 5.3 No-write asserts (sin re-correr smoke completo)

```bash
git diff main wave1.5-integration -- scripts/ | grep -E "PATCH https://api\.notion\.com|POST https://api\.linkedin\.com" || echo "OK: no new write paths added"
```

### 5.4 Stage 7.5, Notion DBs, gates humanos: sin tocar

```bash
git log main..wave1.5-integration --oneline -- 'scripts/discovery/stage7_5_*'
# Esperado: vacío

# Verificar que el fix no creó archivos de migración SQLite nuevos
git diff main wave1.5-integration --stat -- 'scripts/discovery/migrations/' | tail -5
# Esperado: solo los archivos 0001 y 0002 ya existentes en la branch
```

---

## Fase 6 — Push + actualizar PR #400

```bash
git push origin wave1.5-integration

# Actualizar body del PR con link al §10bis del reporte
gh pr edit 400 --body-file docs/audits/2026-05-08-wave1_5-integration-report.md

# Mantener draft + label
gh pr view 400 --json isDraft,labels
# Esperado: isDraft=true, labels incluye "do-not-merge"
```

**NO quitar `do-not-merge`. NO marcar ready for review.** David revisa primero.

---

## Fase 7 — Reporte de fix

Crear `docs/audits/2026-05-09-wave1_5-fix-report.md` (corto, 1 página):

```markdown
# Wave 1.5 Fix — Report
> Date: 2026-05-09 · Operator: Copilot-VPS · Branch: wave1.5-integration · PR #400

## Resumen
3 cambios mínimos pre-merge sobre `wave1.5-integration`:
1. Test failing resuelto vía inyección de `dedup` por parámetro (opción c).
2. Hash contract: alias `source_content_hash` + contrato `publication_content_hash` diferido explícito.
3. Reporte corregido: carrusel/video declarado NO cumplido + carry-over Wave 2 con prioridad top.

## Suite tras fix
[pegar literal `tail -3` de `/tmp/wave15-fix-suite.log`]

## Commits del fix
[pegar `git log main..wave1.5-integration --oneline | head -5` (los 3 commits del fix más los 9 originales debajo)]

## Restricciones verificadas
- Stage 7.5 freeze: `git diff` = 0 (re-confirmado).
- Sin migraciones SQLite nuevas.
- Sin gates humanos escritos.
- Sin DBs Notion creadas.
- Sin escritura a Notion / LinkedIn (sin paths nuevos de write en `git diff`).
- 6 PRs originales: draft + do-not-merge (sin tocar).
- PR #400: draft + do-not-merge (sin tocar).

## Recomendación
PR #400 listo para review final por David. Si David aprueba:
- Quitar `do-not-merge` de #400.
- Mergear #400 a main (Squash recomendado por las 12+ commits).
- Cerrar #394–#399 sin mergear (con comentario apuntando a #400).

Wave 2 carry-overs prioritarios (top del backlog del reporte principal):
1. Canal vs Formato (variants.py refactor + 38 tests H5).
2. publication_content_hash separado + migración register_published.

## Log de "Repo dice X vs VPS muestra Y"

| Fase | Repo dice | VPS muestra |
|---|---|---|
| 2 | Test failing aislado vs suite | [resultado real] |
| 5.1 | suite verde | [literal tail] |
| 5.2 | Stage 7.5 frozen | [literal wc -l] |
```

```bash
git add docs/audits/2026-05-09-wave1_5-fix-report.md
git commit -m "wave1.5-fix(report): summary report 2026-05-09"
git push origin wave1.5-integration
```

---

## Fase 8 — Cierre de task (NO modificar status desde feature branch)

**Convención observada en este repo:** los task files NO se marcan `status: done`
desde la branch de trabajo del PR. El task previo `2026-05-08-001` quedó en
`status: assigned` aún después de completarse Wave 1.5. Marcar `done` desde
`wave1.5-integration` desalinearía el archivo entre la branch del PR y `main`,
y tampoco hay garantía de cuándo el task file llegará a `main` (depende del
merge de #400, que David autoriza después).

**Acción correcta:**

- NO editar el frontmatter `status:` del task file desde `wave1.5-integration`.
- NO commitear cambios al task file en esta branch.
- Registrar el cierre operativo del task **dentro de**
  `docs/audits/2026-05-09-wave1_5-fix-report.md` (sección "Cierre de task").
- Si David quiere actualizar el frontmatter a `status: done`, lo hará él
  mismo en `main` después de mergear #400 (o en una PR separada de
  housekeeping).

```bash
# Solo verificación, sin escribir:
git show wave1.5-integration:.agents/tasks/2026-05-09-001-copilot-vps-wave1_5-fix.md \
  | head -10
# Esperado: status: open (sin cambios)
```

En el reporte de Fase 7 añadir bloque:

```markdown
## Cierre de task

Task file: `.agents/tasks/2026-05-09-001-copilot-vps-wave1_5-fix.md`.

Frontmatter `status:` deliberadamente NO se modifica desde
`wave1.5-integration` (sigue convención observada con task `2026-05-08-001`,
que permaneció `status: assigned` aún tras completarse Wave 1.5). El cierre
operativo del task se registra acá, en este reporte. Si se requiere reflejar
`status: done` en `main`, hacerlo en una PR de housekeeping separada después
del merge de #400.

Estado de ejecución del task: **TERMINADO** — todas las fases 1-7 completadas
con criterios de aceptación cumplidos (ver checklist al final de este reporte).
```

---

## Criterios de aceptación (checklist final)

- [ ] `PYTHONPATH=. python -m pytest tests/discovery/ tests/lib/ -q` termina con `0 failed`.
- [ ] `publish_one` (o equivalente) acepta `dedup_module` parameter; tests inyectan fake explícito.
- [ ] `compute_source_content_hash` alias presente en `lib/dedup.py` con docstring.
- [ ] `hash-contract.md` separa §1a (source identity, implementado) y §1b (publication content, diferido).
- [ ] `hash-contract.md` §3 marca colisión sin pubDate como "riesgo R1 documentado", no "estable".
- [ ] Reporte §3 cross-conflict #8: estado = "NO cumplido + Wave 2 carry-over".
- [ ] Reporte §12 backlog: items #1 y #2 son los 2 carry-overs Wave 1.5 con tag explícito.
- [ ] Reporte §10bis: tabla pre/post fix con commit hashes.
- [ ] Stage 7.5 `git diff main` = 0 (re-confirmado).
- [ ] Sin migraciones SQLite nuevas (solo 0001 + 0002 existentes).
- [ ] Sin escritura a Notion ni LinkedIn (verificable por `git diff`).
- [ ] PR #400 sigue draft + label `do-not-merge`.
- [ ] PRs #394–#399 sin tocar (siguen draft + `do-not-merge`).
- [ ] `docs/audits/2026-05-09-wave1_5-fix-report.md` creado con resumen + log "Repo dice X vs VPS muestra Y" + sección "Cierre de task".
- [ ] Task file frontmatter `status:` **NO modificado** desde `wave1.5-integration` (sigue convención observada con task `2026-05-08-001`).

## Anti-criterios (si pasa cualquiera de estos, ABORT y reportar)

- ❌ Suite no llega a 0 failed después de la opción (c). Reportar diff de tests rotos.
- ❌ Tener que tocar `scripts/discovery/stage7_5_*` para que algo funcione.
- ❌ Tener que crear migración 0003 SQLite. NO hacerlo. Reportar y pedir guidance.
- ❌ Tener que tocar `variants.py` para que algo funcione. NO hacerlo. Reportar.
- ❌ Romper tests de H5 (38 tests) o de hash contract (9 tests).
- ❌ Cualquier write real a Notion o LinkedIn aparecido durante la verificación.

---

## Log

(Completar fase a fase con "Repo dice X vs VPS muestra Y" cuando ejecutes.)
