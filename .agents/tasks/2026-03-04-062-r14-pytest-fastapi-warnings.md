# Task R14 — Arreglar warnings de pytest y FastAPI

**Fecha:** 2026-03-04  
**Ronda:** 14  
**Agente:** GitHub Copilot / Code Claude / Cursor Agent Cloud  
**Branch:** `feat/pytest-fastapi-warnings`

---

## Contexto

`pytest tests/` reporta varios warnings:

1. **PytestCollectionWarning:** `cannot collect test class 'TestResult' because it has a __init__ constructor` — En `scripts/e2e_validation.py` hay una clase `TestResult` (dataclass). Pytest intenta recolectarla como test porque su nombre empieza por `Test`.

2. **DeprecationWarning (FastAPI):** `on_event is deprecated, use lifespan event handlers instead` — En `worker/app.py` se usa `@app.on_event("shutdown")` (y posiblemente `startup`).

**Objetivo:** Eliminar o mitigar estos warnings sin romper funcionalidad.

---

## Tareas requeridas

### 1. Renombrar TestResult en e2e_validation

En `scripts/e2e_validation.py`:
- Renombrar la clase `TestResult` a algo como `E2ETestResult` o `ValidationResult` para que pytest no intente recolectarla.
- Actualizar todas las referencias en ese archivo.
- Actualizar `tests/test_e2e_validation.py` si importa `TestResult`.

### 2. Migrar FastAPI on_event a lifespan

En `worker/app.py`:
- Sustituir `@app.on_event("startup")` y `@app.on_event("shutdown")` por un context manager `lifespan` conforme a la documentación de FastAPI: https://fastapi.tiangolo.com/advanced/events/
- Ejemplo:
  ```python
  from contextlib import asynccontextmanager

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # startup
      yield
      # shutdown

  app = FastAPI(lifespan=lifespan)
  ```

### 3. Verificar

- `pytest tests/ -v` — reducir o eliminar los warnings relacionados.
- El Worker debe seguir arrancando y apagándose correctamente (verificar con un smoke test si existe).

---

## Criterios de éxito

- [ ] No aparece PytestCollectionWarning por TestResult
- [ ] No aparece DeprecationWarning por on_event (o queda documentado como pendiente menor si hay dependencias)
- [ ] `pytest tests/` ejecuta sin regresiones
- [ ] PR abierto a `main`
