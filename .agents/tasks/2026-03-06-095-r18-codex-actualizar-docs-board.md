# Task R18 — Actualizar docs de cierre y marcar R18 cerrada (Codex)

**Fecha:** 2026-03-06  
**Ronda:** 18  
**Agente:** Codex  
**Branch:** `codex/095-actualizar-docs-board` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

Actualizar `docs/r16-cierre-resumen.md` con el estado real (PRs #89 y #90 mergeados, 900 tests) y marcar **Ronda 18** como cerrada en `.agents/board.md` (tarea 094 done, PR #97 mergeado).

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b codex/095-actualizar-docs-board`.

2. **Actualizar docs/r16-cierre-resumen.md:**
   - En la tabla de PRs, marcar #89 y #90 como ✅ Merged (no "Open").
   - En "Estado final", poner **Tests: 900 passed** (no 536).
   - En "Próximos pasos", ajustar: ya no "Mergear #89 y #90"; dejar borrar ramas, enriquecer Bitácora, y opcionalmente "R17/R18 cerradas".
   - Añadir una línea o párrafo breve: R17 cerrada (PRs #91–#96), R18 tarea 094 (dashboard Notion, PR #97 mergeado).

3. **Actualizar .agents/board.md:**
   - Cambiar el título de la sección "Ronda 18 — En curso" a **"Ronda 18 — Cerrada"**.
   - Dejar 094 como ✅ done (PR #97). Opcional: añadir una línea tipo "R18 cerrada — dashboard Notion actualizado (PR #97)."

4. **PR:** Abrir un único PR desde `codex/095-actualizar-docs-board` a main. Título: "docs(R18-095): actualizar r16-cierre-resumen y marcar R18 cerrada". Solo docs y board; no código.

---

## Criterios de éxito

- [ ] `docs/r16-cierre-resumen.md` con #89/#90 merged, 900 tests, próximos pasos actualizados.
- [ ] Board con "Ronda 18 — Cerrada" y 094 done (PR #97).
- [ ] PR abierto a main.

---

## Restricciones

- Solo editar esos dos archivos. No tocar worker, dispatcher ni scripts.
