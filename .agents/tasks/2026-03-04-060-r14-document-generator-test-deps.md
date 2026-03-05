# Task R14 — Fix document_generator test dependencies

**Fecha:** 2026-03-04  
**Ronda:** 14  
**Agente:** Codex / Code Claude / Cursor Agent Cloud  
**Branch:** `feat/document-generator-test-deps`

---

## Contexto

`pytest tests/` reporta **7 fallos** en `tests/test_document_generator.py` por `ModuleNotFoundError: No module named 'docxtpl'` y `No module named 'fpdf'`. Las dependencias sí están en `worker/requirements.txt` (docxtpl, fpdf2, python-pptx, weasyprint) pero no se cargan en el entorno donde se ejecutan los tests.

**Objetivo:** Que los tests de `document_generator` pasen en un entorno típico (venv del proyecto con `pip install -e .` o `pip install -r worker/requirements.txt`).

---

## Tareas requeridas

1. **Verificar `pyproject.toml`** — Si existe `[project.optional-dependencies]` o `[project.dependencies]`, asegurar que docxtpl, fpdf2, python-docx, python-pptx estén incluidos para que `pip install -e ".[dev]"` o similar instale todo lo necesario para tests.

2. **Añadir dependencias de document_generator al grupo de tests** — En `pyproject.toml`, crear (o ampliar) un grupo `test` o `all` que incluya las de `worker/requirements.txt` relacionadas con document generation, de modo que `pytest` disponga de ellas.

3. **Documentar en README o CONTRIBUTING** — Indicar que para ejecutar la suite completa hay que instalar dependencias del worker:
   ```bash
   pip install -r worker/requirements.txt
   # o
   pip install -e ".[test]"
   ```

4. **Opcional — skip condicional** — Si las dependencias no están instaladas, que los tests de `test_document_generator` se salten con `pytest.importorskip("docxtpl")` en lugar de fallar. Solo como respaldo; la prioridad es que se instalen.

5. **Comprobar** — Ejecutar `pip install -r worker/requirements.txt` y luego `pytest tests/test_document_generator.py -v`; debe haber 0 fallos.

---

## Criterios de éxito

- [x] `pytest tests/test_document_generator.py` pasa sin errores
- [x] `pyproject.toml` o README documenta cómo instalar deps para tests
- [x] PR abierto a `main`

---

## Log

**2026-03-05 — cursor-agent-cloud**

1. Añadido `[project]` con dependencias base y `[project.optional-dependencies]` (`docs`, `test`, `all`) en `pyproject.toml`.
2. Añadido `[tool.setuptools.packages.find]` para resolver flat-layout con múltiples paquetes top-level.
3. Añadido `pytest.importorskip` para `docx`, `docxtpl`, `fpdf`, `pptx` en `tests/test_document_generator.py` como fallback graceful.
4. Documentado en `AGENTS.md` cómo instalar dependencias de tests (`pip install -e ".[test]"`).
5. Verificado: 20 passed, 1 skipped en `test_document_generator.py`; 847 passed, 5 skipped en suite completa.
