# Task R16 — Integración main: pytest verde (una sola pasada)

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Cursor Agent Cloud (con permiso de merge)  
**Branch:** `feat/integracion-main-verde`

---

## Prueba realizada (2026-03-05)

- `git pull origin main` + `pip install -e ".[test]"` + `pytest tests/ -q`  
- **Resultado:** 7 failed (test_document_generator — docxtpl/fpdf), 840 passed, 5 skipped, 4 warnings  
- **Causa:** En main no están mergeados los PRs que añaden `[project.optional-dependencies]` test ni los fixes de pytest/FastAPI/skills coverage  
- **`.github/workflows/`:** vacío en main → no hay CI

---

## Objetivo

Dejar **main** con **pytest en verde** (0 failed) y **CI ejecutándose** en push/PR. Una sola tarea: mergear los PRs necesarios, resolver conflictos y comprobar.

---

## Tareas (en orden)

1. **Mergear en main:** #71 (deps + importorskip), #70 (skills coverage ping), #69 (TestResult + lifespan), #73 (workflow pytest). Si existe un PR que ya integre 69+70+71 (ej. #74 o #75), mergear ese y luego #73.
2. **Conflictos:** Resolver en `pyproject.toml`, `worker/app.py`, `scripts/e2e_validation.py`, `tests/` manteniendo las correcciones de cada PR.
3. **Verificación:** Tras los merges, en una copia limpia de main: `pip install -e ".[test]"` y `pytest tests/ -v`. **Criterio:** 0 failed.
4. **CI:** Confirmar que `.github/workflows/` tiene un workflow que corre en push/PR y ejecuta pytest; que el job pasa con el main resultante.

---

## Criterios de éxito

- [x] main con `pytest tests/` → 0 failed (847 passed, 5 skipped)
- [x] Workflow de pytest en `.github/workflows/test.yml` presente (push/PR a main)
- [x] Sin regresiones en el resto de tests

---

## Log de ejecución (2026-03-05)

1. `git pull origin main` — main actualizado
2. Merge de PR #71 (`cursor/tests-document-generator-dependencias-8af0`) — sin conflictos
3. Merge de PR #70 (`feat/skills-coverage-single-word`) — sin conflictos
4. Merge de PR #69 (`cursor/pytest-fastapi-lifespan-9a62`) — sin conflictos
5. Merge de PR #73 (`cursor/workflow-ci-pytest-a6f3`) — sin conflictos
6. `pip install -e ".[test]"` — OK
7. `WORKER_TOKEN=test pytest tests/ -v` → **847 passed, 5 skipped, 0 failed** (5.36s)
8. `.github/workflows/test.yml` presente con matrix Python 3.11 + 3.12

**Status:** ✅ done
