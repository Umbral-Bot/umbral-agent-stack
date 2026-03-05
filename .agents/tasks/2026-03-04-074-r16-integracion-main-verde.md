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

- [ ] main con `pytest tests/` → 0 failed  
- [ ] Workflow de pytest en `.github/workflows/` y pasando  
- [ ] Sin regresiones en el resto de tests  
