# Task R15 — CI: GitHub Actions para pytest

**Fecha:** 2026-03-05  
**Ronda:** 15  
**Agente:** Cursor Agent Cloud / Antigravity  
**Branch:** `feat/ci-pytest-actions`

---

## Contexto

No existe un workflow de CI que ejecute la suite de tests en cada push o PR. Para evitar regresiones (p. ej. document_generator sin deps, o tests rotos tras un merge), conviene tener un job que instale dependencias e ejecute pytest.

**Objetivo:** Añadir un workflow de GitHub Actions que, en cada push a `main` y en cada pull request, instale el proyecto con dependencias de tests y ejecute `pytest tests/`.

---

## Tareas requeridas

1. **Crear `.github/workflows/test.yml`** (o nombre equivalente) con:
   - Trigger: `push` a `main`, `pull_request` a `main`.
   - Job con Python 3.11 o 3.12 (matrix opcional).
   - Pasos:
     - checkout
     - `pip install -e ".[test]"` (si pyproject.toml tiene optional-dependencies test) **o** `pip install -r worker/requirements.txt` y `pip install -e .`
     - `pytest tests/ -v --tb=short` (o con junitxml para reportes si se desea).
   - El job debe **fallar** si pytest devuelve exit code distinto de 0.

2. **Variables de entorno** — Si algún test requiere env (ej. `WORKER_TOKEN=test`), definirlo en el workflow con valores de prueba, sin secretos reales.

3. **Documentar** — En README o CONTRIBUTING, indicar que los tests se ejecutan en CI y cómo ejecutarlos en local (`pip install -e ".[test]"` y `pytest tests/`).

---

## Criterios de éxito

- [x] Workflow en `.github/workflows/` que ejecute pytest
- [x] Se dispara en push a main y en PRs hacia main
- [x] El job falla cuando hay tests fallidos
- [x] README o CONTRIBUTING actualizado con instrucciones de tests
- [x] PR abierto a `main`

## Log

### [cursor-agent-cloud] 2026-03-05 12:00

**Archivos creados/modificados:**
- `.github/workflows/test.yml` — workflow CI con matrix Python 3.11 + 3.12
- `README.md` — sección Tests actualizada con mención de CI
- `CONTRIBUTING.md` — nuevo, con instrucciones de tests locales y CI

**Tests:** 847 passed, 5 skipped, 0 failed (local, Python 3.12)
