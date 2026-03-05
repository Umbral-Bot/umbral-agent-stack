# Task R16 — Limpieza de PRs y documentación

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Cursor Agent Cloud / Antigravity  
**Branch:** `chore/limpieza-prs-docs`

---

## Contexto

Hay muchos PRs abiertos (69–83). Tras el merge de integración a main, algunos quedarán obsoletos. Se pide ordenar el estado y dejar documentación clara para quien contribuya.

---

## Tareas

1. **Revisar PRs abiertos:** Listar PRs abiertos. Si ya existe un merge a main que incluye los cambios de #69, #70, #71, #73, cerrar esos PRs con un comentario tipo "Incluido en PR #XX mergeado a main".
2. **README:** Asegurar que el README tenga (o añadir): sección "Ejecutar tests" con `pip install -e ".[test]"` y `pytest tests/`; mención al CI (GitHub Actions) y enlace al board (`.agents/board.md` o su equivalente).
3. **CONTRIBUTING (opcional):** Si existe `CONTRIBUTING.md`, añadir 2–3 líneas sobre: branch desde main, tests antes de PR, referencia al board para tareas. Si no existe, un párrafo en README basta.
4. **Board:** Actualizar `.agents/board.md` con el estado de tareas 077–080 (completadas si sus PRs están mergeados o cerrados).

---

## Criterios de éxito

- [ ] PRs obsoletos cerrados con comentario
- [ ] README con instrucciones de tests y mención a CI/board
- [ ] Board actualizado (077–080)
