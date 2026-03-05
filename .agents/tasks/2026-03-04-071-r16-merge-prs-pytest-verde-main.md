# Task R16 — Mergear PRs pendientes y dejar pytest en verde en main

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Cursor Agent Cloud  
**Branch:** `feat/merge-prs-pytest-verde`

---

## Contexto

En `main` siguen **7 fallos** en `test_document_generator` (docxtpl/fpdf no instalados) y **4 warnings**. Hay PRs listos que lo corrigen pero no están mergeados en main:

- **#69** — PytestCollectionWarning + FastAPI lifespan
- **#70** — skills coverage para tareas de una palabra (ping)
- **#71** — document_generator deps en pyproject.toml + importorskip
- **#73** — GitHub Actions workflow para pytest
- **#74** o **#75** — integración de 69+70+71

**Objetivo:** Mergear estos PRs en `main` (resolviendo conflictos si los hay) y verificar que `pytest tests/` quede con **0 failed**. Si #73 está mergeado, comprobar que el workflow de CI pasa.

---

## Tareas requeridas

1. Mergear en main, en orden (para minimizar conflictos): #69, #70, #71; luego #73. O mergear #74/#75 si ya integran 69+70+71 y luego #73.
2. Resolver conflictos en `pyproject.toml`, `worker/app.py`, `tests/`, etc., manteniendo las correcciones de cada PR.
3. Tras los merges, ejecutar localmente (o esperar a CI): `pip install -e ".[test]"` y `pytest tests/ -v`. Resultado esperado: **0 failed**.
4. Si el board (#76) o la integración (#75) están listos, valorar mergearlos después.

---

## Criterios de éxito

- [x] main con pytest 0 failed — ✅ 847 passed, 5 skipped, 0 failed
- [x] CI (workflow pytest) incluido via PR #73/#75
- [x] PR abierto: branch `cursor/integraci-n-de-prs-y-pruebas-1084`

## Log

- **2026-03-05 cursor-agent-cloud**: Mergeó PR #75 (que integra #74 → #69+#70+#71 + #73 + mejora CI). Merge limpio sin conflictos. pytest: 847 passed, 5 skipped, 0 failed.
