# Task R15 — Integración main: pytest verde + CI

**Fecha:** 2026-03-05  
**Ronda:** 15  
**Agente:** Cursor Agent Cloud / quien tenga permisos de merge  
**Branch:** `feat/integracion-main-pytest-ci`

---

## Contexto

En `main` hay **7 fallos** en `test_document_generator` (docxtpl/fpdf no instalados) y **4 warnings**. Existen PRs que lo corrigen pero no están mergeados:

- **#69** — PytestCollectionWarning (TestResult) + FastAPI lifespan
- **#70** — skills coverage para tareas de una palabra (ping)
- **#71** — document_generator deps en pyproject.toml + importorskip
- **#74** — merge de 69+70+71 en uno
- **#73** — GitHub Actions workflow para pytest

**Objetivo:** Dejar `main` con **pytest en verde** (0 failed) y **CI ejecutándose** en cada push/PR.

---

## Tareas requeridas

1. **Mergear en main** (en orden recomendado para evitar conflictos):
   - Primero #69, luego #70, luego #71; **o** mergear directamente #74 si ya integra los tres.
   - Luego #73 (CI).

2. **Resolver conflictos** si aparecen (p. ej. en `pyproject.toml`, `worker/app.py`, `tests/`), manteniendo las mejoras de cada PR.

3. **Verificar localmente** (o en CI tras el merge):
   ```bash
   pip install -e ".[test]"
   pytest tests/ -v --tb=short
   ```
   Resultado esperado: **0 failed**. Warnings aceptables si son menores.

4. **Comprobar el workflow de CI** — Tras mergear #73, un push a main o un PR debe disparar el job y ejecutar pytest; el job debe pasar (verde).

---

## Criterios de éxito

- [ ] PRs #69, #70, #71 (o #74) y #73 mergeados en main
- [ ] `pytest tests/` con 0 fallos
- [ ] Workflow de GitHub Actions corre en push/PR y pasa
