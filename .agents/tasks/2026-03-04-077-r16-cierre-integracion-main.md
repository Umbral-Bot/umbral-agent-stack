# Task R16 — Cierre de integración: main en verde

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Cursor Agent Cloud  
**Branch:** `feat/cierre-integracion-main`

---

## Contexto

En main siguen **7 fallos** en `test_document_generator` y **4 warnings**. Existen PRs que lo corrigen (#69, #70, #71, #73) y PRs de integración (#80, #79). Ninguno está mergeado en main.

**Objetivo:** Dejar **main** con **pytest en verde** (0 failed) y **CI ejecutándose** en push/PR. Una sola tarea de cierre: mergear los PRs necesarios, resolver conflictos y comprobar.

---

## Tareas

1. **Mergear en main** (en orden): #71, #70, #69, #73. O mergear #80 si integra 69+70+71 y luego #73; o #79 si ya incluye workflow + instrucciones de tests.
2. **Conflictos:** Resolver en `pyproject.toml`, `worker/app.py`, `scripts/e2e_validation.py`, `tests/` manteniendo las correcciones de cada PR.
3. **Verificación:** Tras los merges, `pip install -e ".[test]"` y `pytest tests/ -v`. **Criterio:** 0 failed.
4. **CI:** Confirmar que existe workflow en `.github/workflows/` que corre en push/PR y que el job pasa.

---

## Criterios de éxito

- [ ] main con `pytest tests/` → 0 failed
- [ ] Workflow de pytest presente y pasando
- [ ] PR abierto/mergeado según corresponda
