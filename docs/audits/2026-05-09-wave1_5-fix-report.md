# Wave 1.5 Fix — Report

> Date: 2026-05-09 · Operator: Copilot-VPS · Branch: `wave1.5-integration` · PR #400
> Task: [`.agents/tasks/2026-05-09-001-copilot-vps-wave1_5-fix.md`](../../.agents/tasks/2026-05-09-001-copilot-vps-wave1_5-fix.md)
> Reporte mayor: [`./2026-05-08-wave1_5-integration-report.md`](./2026-05-08-wave1_5-integration-report.md)

## Resumen

3 cambios mínimos pre-merge sobre `wave1.5-integration`:

1. **Test failing resuelto** vía inyección de `dedup` por parámetro
   (opción c del integration report §10). Eliminada la dependencia frágil
   de `monkeypatch.setitem(sys.modules, ...)` + atributo cacheado del paquete
   padre. Suite completa pasa de 402/1 a **403 passed / 0 failed**.
2. **Hash contract corregido:** alias semántico `source_content_hash` en
   `lib/dedup.py` + contrato `publication_content_hash` declarado **DIFERIDO
   a Wave 2** en `hash-contract.md §1b`. El uso actual de `content_hash` como
   `source_content_hash` en `register_published` es **guard provisional
   aceptable para Wave 1.5 mientras no exista `publication_content_hash`,
   y NO representa idempotencia final de publicación**. Wave 2 obligatorio
   antes de cualquier publicación real.
3. **Carrusel/video** corregido en el integration report: declarado
   **NO cumplido** (ya no "Postponed Wave 2") con carry-over explícito al
   top del backlog (§12 #1). NO se tocó `variants.py` (rompería los 38 tests
   H5); refactor semántico es scope Wave 2.

## Suite tras fix

```
$ PYTHONPATH=. python -m pytest tests/discovery/ tests/lib/ -q
........................................................................ [ 89%]
...........................................                              [100%]
403 passed in 25.79s
```

Salto neto: +1 test pasando vs baseline `wave1.5-integration` (que tenía
402 passed / 1 failed). 0 tests rotos colateralmente.

## Commits del fix (3 nuevos en `wave1.5-integration`)

```
32067c6 wave1.5-fix(report): mark carousel/video as NOT met + add §10bis fix log + reorder Wave 2 backlog
0f633e6 wave1.5-fix(hash-contract): separate source_content_hash from publication_content_hash
0e111bd wave1.5-fix(test): inject dedup module into publish_one to remove sys.modules dependency
```

`git log main..wave1.5-integration --oneline | wc -l` → **22 commits**
(12 originales de Wave 1.5 + 3 del fix + 7 commits de las 6 PRs originales
embebidos en el merge integrado).

## Decisiones técnicas (literal del task — no re-deliberadas)

1. **Test fix → opción (c):** `publish_one` acepta `dedup_module` parameter
   inyectable (default = `None`, lazy import en runtime). Tests inyectan el
   fake explícito. `assert_can_publish` no se tocó (su path vía
   `_load_module` ya respetaba `sys.modules`).
2. **Hash rename → solo docs + alias en código:**
   - Sin migración SQLite. Sin rename de columnas.
   - Alias en `lib/dedup.py`: `compute_source_content_hash = compute_content_hash`.
   - `hash-contract.md §1` partido en §1a (source identity, implementado
     Wave 1) y §1b (publication content, DIFERIDO Wave 2) con wording
     endurecido sobre el guard provisional.
   - `hash-contract.md §3` upgrade de "estable" a "**riesgo R1 documentado**"
     para colisión sin pubDate.
3. **Carrusel/video → solo reporte:**
   - `variants.py` NO tocado.
   - `2026-05-08-wave1_5-integration-report.md §3 #8`: estado cambiado de
     "Postponed Wave 2" a "**NO cumplido en Wave 1.5 — deuda explícita
     Wave 2**".
   - `§12` reordenado: items 1 y 2 son ahora los carry-overs Wave 1.5
     marcados `[CARRY-OVER WAVE 1.5]`.
   - `§10bis` agregado con tabla pre/post fix + commit hashes.
   - `§11` con prelude resumiendo estado post-fix (suite verde, etc.).

## Restricciones verificadas (literal output VPS)

| Check | Output |
|---|---|
| Suite completa | `403 passed in 25.79s` |
| Stage 7.5 freeze | `git diff main wave1.5-integration -- 'scripts/discovery/stage7_5_*' \| wc -l` → **0** |
| Stage 7.5 commits | `git log main..wave1.5-integration --oneline -- 'scripts/discovery/stage7_5_*'` → **vacío** |
| Sin migraciones SQLite nuevas | `git diff main wave1.5-integration --stat -- 'scripts/discovery/migrations/'` → solo 0001 + 0002 (ya existentes) |
| Sin write paths nuevos | `git diff … \| grep -E "PATCH https://api\.notion\.com\|POST https://api\.linkedin\.com"` → **OK: no new write paths added** |
| `variants.py` no tocado | confirmado en `git diff --stat 0e111bd^..HEAD` (solo dedup.py + stage9c + tests + 2 docs) |
| 6 PRs originales | draft + `do-not-merge` (no se tocaron) |
| PR #400 | draft + `do-not-merge` (verificado en Fase 6) |

## Recomendación

PR #400 listo para review final por David. Si David aprueba:

- Quitar `do-not-merge` de #400.
- Mergear #400 a `main` (Squash recomendado por las 22 commits).
- Cerrar #394–#399 sin mergear (con comentario apuntando a #400).

**Wave 2 carry-overs prioritarios** (top del backlog del integration report
§12, marcados `[CARRY-OVER WAVE 1.5]`):

1. **Canal vs Formato** — refactor `variants.py` (separar `PLATFORMS` de
   `FORMATS`) + 38 tests H5.
2. **`publication_content_hash`** separado de `source_content_hash` —
   definir, computar sobre copy final post-S6/S7, persistir en
   `published_history`, migrar `register_published` para usarlo.
   **Obligatorio antes de cualquier publicación real a LinkedIn.**

## Log "Repo dice X vs VPS muestra Y"

| Fase | Repo dice | VPS muestra |
|---|---|---|
| 1 (baseline) | suite debe tener 402/1 según integration report §10 | `402 passed, 1 failed in 26.71s` ✓ idéntico |
| 2 (target test) | `test_successful_post_calls_register_published` failing | confirmado: `assert 0 == 1 … register_calls=[]`. Post-fix: `2 passed in 0.46s` ✓ |
| 5.1 (suite full) | criterio = 0 failed | `403 passed in 25.79s` ✓ |
| 5.2 (Stage 7.5 freeze) | esperado 0 cambios | `wc -l = 0` ✓ |
| 5.3 (write paths) | esperado ningún POST/PATCH nuevo | `OK: no new write paths added` ✓ |
| 5.4 (migraciones) | esperado solo 0001+0002 | confirmado, no 0003+ ✓ |

## Cierre de task

Task file: [`.agents/tasks/2026-05-09-001-copilot-vps-wave1_5-fix.md`](../../.agents/tasks/2026-05-09-001-copilot-vps-wave1_5-fix.md).

Frontmatter `status:` deliberadamente **NO** se modifica desde
`wave1.5-integration` (sigue convención observada con task `2026-05-08-001`,
que permaneció `status: assigned` aún tras completarse Wave 1.5). El cierre
operativo del task se registra acá, en este reporte. Si se requiere reflejar
`status: done` en `main`, hacerlo en una PR de housekeeping separada después
del merge de #400.

**Estado de ejecución del task:** **TERMINADO** — todas las fases 1-7
completadas con criterios de aceptación cumplidos. Anti-criterios: ninguno
disparado (no se tocó Stage 7.5, no se creó migración 0003, no se tocó
`variants.py`, no se rompieron tests H5 ni hash-contract, ningún write
real a Notion/LinkedIn).

## Checklist final

- [x] `PYTHONPATH=. python -m pytest tests/discovery/ tests/lib/ -q` termina con `0 failed` (`403 passed`).
- [x] `publish_one` acepta `dedup_module` parameter; test inyecta fake explícito.
- [x] `compute_source_content_hash` alias presente en `lib/dedup.py` con docstring.
- [x] `hash-contract.md` separa §1a (source identity) y §1b (publication content, DIFERIDO).
- [x] `hash-contract.md` §3 marca colisión sin pubDate como "riesgo R1 documentado".
- [x] Reporte §3 cross-conflict #8: estado = "NO cumplido + Wave 2 carry-over".
- [x] Reporte §12 backlog: items #1 y #2 son los carry-overs Wave 1.5 con tag explícito.
- [x] Reporte §10bis: tabla pre/post fix con commit hashes.
- [x] Stage 7.5 `git diff main` = 0 (re-confirmado).
- [x] Sin migraciones SQLite nuevas (solo 0001 + 0002).
- [x] Sin escritura nueva a Notion ni LinkedIn (verificable por `git diff`).
- [x] PR #400 sigue draft + `do-not-merge` (Fase 6).
- [x] PRs #394–#399 sin tocar.
- [x] Task file frontmatter `status:` **NO modificado** desde `wave1.5-integration`.
