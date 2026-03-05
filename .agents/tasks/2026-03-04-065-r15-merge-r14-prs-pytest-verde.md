# Task R15 — Integrar PRs R14 y dejar pytest en verde

**Fecha:** 2026-03-05  
**Ronda:** 15  
**Agente:** Cursor Agent Cloud / Codex  
**Branch:** `feat/merge-r14-pytest-verde`

---

## Contexto

Los agentes entregaron PRs para las tareas R14-060, 061 y 062:
- **#71** — document_generator test deps (pyproject.toml + importorskip)
- **#70** — skills coverage para tareas de una palabra (ping)
- **#69** — PytestCollectionWarning (TestResult → E2ETestResult) y FastAPI lifespan

En `main` actual: **7 fallos** en `test_document_generator` (docxtpl/fpdf no instalados), **4 warnings** (TestResult, on_event, skills coverage ping). Los PRs corrigen esto pero no están mergeados.

**Objetivo:** Mergear los PRs #69, #70 y #71 en `main`, resolver conflictos si los hay, y verificar que `pytest tests/ -v` quede en verde (0 fallos).

---

## Tareas requeridas

1. **Mergear #71** — Aceptar el PR que añade dependencias en pyproject.toml y importorskip en test_document_generator. Si hay conflictos con pyproject.toml o con tests, resolverlos (mantener las opciones `[project.optional-dependencies]` test/all).

2. **Mergear #70** — Aceptar el PR que hace que skills coverage detecte tareas de una palabra (ping). Resolver conflictos en tests/test_skills_coverage.py o scripts/skills_coverage_report.py si los hay.

3. **Mergear #69** — Aceptar el PR que renombra TestResult a E2ETestResult (o similar) y migra worker/app.py a lifespan. Resolver conflictos en worker/app.py, scripts/e2e_validation.py, tests/test_e2e_validation.py.

4. **Verificación local** — Tras los tres merges:
   ```bash
   pip install -e ".[test]"
   pytest tests/ -v --tb=short
   ```
   Debe haber **0 failed**. Warnings aceptables si son menores; idealmente también reducidos.

5. **Actualizar board o task files** — Marcar 060, 061, 062 como completadas en .agents/tasks o board si aplica.

---

## Criterios de éxito

- [ ] PRs #69, #70, #71 mergeados en main
- [ ] `pytest tests/` con 0 fallos
- [ ] Sin regresiones en tests existentes
- [ ] PR de integración abierto/mergeado o cambios aplicados en main
