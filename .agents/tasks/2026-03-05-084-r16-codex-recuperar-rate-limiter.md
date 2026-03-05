# Task R16 — Recuperar rate limiter por provider (Codex)

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Codex  
**Branch:** `codex/084-recuperar-rate-limiter` ← **trabaja solo en esta rama**. Pull de main antes de crear la rama.

---

## Objetivo

Recuperar el código del **rate limiter por provider** que identificó el análisis de Antigravity (PR #87 / `docs/analisis-contenido-perdido-r16.md`): `worker/rate_limit.py` y tests asociados en dispatcher. Ese contenido está en alguna rama no mergeada; traerlo a main vía esta rama y abrir PR.

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b codex/084-recuperar-rate-limiter`.

2. **Localizar el contenido:** Revisar `docs/analisis-contenido-perdido-r16.md` (o las ramas listadas en `docs/informe-ramas-pendientes.md` / `docs/branches-cerrados-inventario.md`) para identificar la rama que contiene `worker/rate_limit.py` y los tests de dispatcher del rate limiter por provider. Si hace falta, inspeccionar ramas remotas con `git log main..origin/nombre-rama --stat` hasta encontrar los archivos.

3. **Recuperar en tu rama:** Traer solo los cambios del rate limiter por provider: ya sea cherry-pick de commits concretos de esa rama, o copiar/adaptar los archivos relevantes (`worker/rate_limit.py`, tests en dispatcher, y cambios mínimos necesarios para que no rompan main). No incluir otros cambios de esa rama (ni refactors ni features ajenos).

4. **Verificar:** Ejecutar `pip install -e ".[test]"` y `pytest tests/` (o al menos los tests del dispatcher y los que toquen rate limit). Si algo falla, ajustar solo lo imprescindible para que pasen.

5. **PR:** Abrir un único PR desde `codex/084-recuperar-rate-limiter` a `main` con título tipo "Recuperar rate limiter por provider (R16-084)". En la descripción indicar de qué rama se recuperó.

---

## Criterios de éxito

- [ ] Rama `codex/084-recuperar-rate-limiter` creada desde main actualizado.
- [ ] Rate limiter por provider (y tests relevantes) presentes en la rama y pasando tests.
- [ ] PR abierto a main; sin cambios ajenos al rate limiter.

---

## Restricciones

- No tocar otras partes del worker/dispatcher (Granola, Figma, etc.). Solo rate limiter y lo que dependa de él para tests.
- Si la rama fuente tiene cambios destructivos o incompatibles con main, documentar en el PR qué se recuperó y qué se dejó fuera; no mergear código roto.
