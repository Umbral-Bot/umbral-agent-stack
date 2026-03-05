# Task R16 — Verificación CI y README/CONTRIBUTING

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Cursor Agent Cloud  
**Branch:** `feat/ci-readme-verificacion`

---

## Contexto

Tras la integración (task 074), debe quedar comprobado que: (1) el CI está en el repo y pasa, (2) un desarrollador nuevo sabe cómo ejecutar tests. Esta tarea es de **verificación y completar documentación** si falta algo.

---

## Tareas

1. **CI:** Confirmar que existe un workflow en `.github/workflows/` que se dispara en push a main y en pull_request a main, instala dependencias (p. ej. `pip install -e ".[test]"` o `pip install -r worker/requirements.txt` + `-e .`) y ejecuta `pytest tests/`. Si no existe, crearlo (un solo archivo YAML). Si existe pero falla, corregir hasta que pase.
2. **README o CONTRIBUTING:** Que figure una sección breve "Cómo ejecutar tests" con:  
   `pip install -e ".[test]"` (o el comando correcto según pyproject.toml) y `pytest tests/`. Opcional: enlace al workflow de GitHub Actions. Si ya está en otro PR mergeado, solo verificar y cerrar.
3. **Comprobación final:** Ejecutar localmente los mismos pasos que el CI (install + pytest) y anotar en el PR que la verificación se hizo.

---

## Criterios de éxito

- [x] CI presente y pasando en main (o en el PR que lo añade)  
- [x] README o CONTRIBUTING con instrucciones de tests  
- [x] PR abierto a main (o tarea cerrada si todo ya está mergeado)  

---

## Log

### 2026-03-05 — cursor-agent-cloud

1. **CI creado**: `.github/workflows/pytest.yml` — triggers en push/PR a main, Python 3.12, instala deps de worker + dispatcher + fakeredis, ejecuta `pytest tests/ -v` con `WORKER_TOKEN=test`.
2. **README actualizado**: Badge de CI añadido al inicio. Sección Tests ampliada con instrucciones completas (install deps + fakeredis + pytest) y enlace al workflow.
3. **Verificación local**: 847 passed, 5 skipped, 4 warnings en 5.52s.
