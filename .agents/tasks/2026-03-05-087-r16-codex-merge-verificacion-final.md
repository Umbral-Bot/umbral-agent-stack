# Task R16 — Merge ordenado y verificación final (Codex)

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Codex  
**Branch:** `codex/087-merge-verificacion-final` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

Cerrar el ciclo R16 mergeando en `main` los PRs de capitalización/recuperación que sigan abiertos, en orden, y dejar main estable (pytest verde). Actualizar el board con el estado final.

---

## Tareas

1. **Pull:** `git checkout main && git pull origin main`.

2. **Merge ordenado:** Mergear a main (por UI de GitHub o localmente) los PRs en este orden, uno a uno, resolviendo conflictos si aparecen: #85 → #86 → #87 → #88 → #89 → #90. (Omitir los que ya estén mergeados.) Si trabajas localmente: para cada PR, mergear la rama del PR en main, resolver conflictos, push. No crear una rama nueva para esto si usas la UI de GitHub; si trabajas local, puedes hacerlo desde main directamente (checkout main, pull, merge origin/copilot/082-..., push; repetir para cada uno).

3. **Verificación:** Tras tener todos los merges en main, `git pull origin main`, `pip install -e ".[test]"`, `pytest tests/ -q`. Criterio: **0 failed**. Si algo falla, corregir el mínimo necesario en main (o abrir un PR de fix) y volver a ejecutar pytest hasta que pase.

4. **Board:** Actualizar `.agents/board.md`: marcar 084, 085, 086 como completados (PR #90, #89, #88). Añadir una línea tipo "R16 cerrado — PRs mergeados: #85, #86, #87, #88, #89, #90" y el número actual de tests (p. ej. 865 passed). Commit y push del board si lo editaste localmente.

---

## Criterios de éxito

- [ ] PRs #85–#90 (los que sigan abiertos) mergeados en main en orden.
- [ ] `pytest tests/` en main con 0 failed.
- [ ] Board actualizado con 084–086 done y resumen R16 cerrado.

---

## Restricciones

- No revertir ni modificar código recuperado; solo resolver conflictos de merge y fixes mínimos si un test falla por compatibilidad.
- Si no tienes permisos para mergear en el repo, documentar en un comentario o en el board el orden de merge recomendado y el estado de cada PR para que el maintainer lo haga.
