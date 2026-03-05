# Task R16 — Análisis profundo: contenido útil perdido en PRs/commits cerrados (Antigravity)

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Antigravity  
**Branch:** `antigravity/083-analisis-contenido-perdido` ← **trabaja solo en esta rama** (crear desde `main` actualizado; haz `git pull origin main` antes).

---

## Contexto

Tras cerrar muchos PRs sin mergear, parte del trabajo (docs, skills, scripts, mejoras) quedó solo en ramas. Objetivo: **análisis profundo** para localizar todo contenido útil que no está en `main` y proponer cómo capitalizarlo (recuperar a main o documentar para uso futuro).

---

## Tareas

1. **Pull antes de empezar:** Asegurarte de estar al día: `git checkout main && git pull origin main`. Luego crear tu rama: `git checkout -b antigravity/083-analisis-contenido-perdido`.

2. **Ramas con commits no en main:** Para cada rama remota relevante (excluir `main`), ejecutar `git log main..origin/nombre-rama --oneline` y anotar cuántos commits tiene y qué archivos tocaron (`git diff main..origin/nombre-rama --stat`). Priorizar ramas de PRs cerrados: browser automation, Power BI, Bitácora, board, runbook, governance, skills, etc.

3. **Contenido útil por rama:** Por cada rama con commits no mergeados, listar:
   - Archivos **nuevos** (docs, skills, scripts) que no existen en main o que tienen versión más rica.
   - Archivos **modificados** con cambios sustanciales (no solo typo).
   - Valoración en 1 línea: "recuperar a main" / "solo documentar" / "obsoleto".

4. **Informe:** Crear `docs/analisis-contenido-perdido-r16.md` con:
   - Resumen ejecutivo (cuántas ramas, cuántos commits/archivos fuera de main).
   - Tabla: rama | PR (si aplica) | archivos nuevos/modificados relevantes | valoración | acción recomendada.
   - Sección "Prioridad de recuperación" con los 5–10 items más valiosos que convendría cherry-pick o merge selectivo.

5. **No mergear ni tocar main:** Solo análisis y documento. Opcional: en tu rama, añadir al final del informe un checklist para que otro agente o humano ejecute las recuperaciones.

---

## Criterios de éxito

- [ ] Rama `antigravity/083-analisis-contenido-perdido` creada desde main actualizado.
- [ ] Documento `docs/analisis-contenido-perdido-r16.md` con análisis profundo y tabla de contenido perdido.
- [ ] Prioridad de recuperación clara (top 5–10).
- [ ] PR desde `antigravity/083-analisis-contenido-perdido` a main (solo el informe).

---

## Restricciones

- Trabajar **solo** en la rama `antigravity/083-analisis-contenido-perdido`.
- No modificar código de aplicación ni workflows; solo generar el informe de análisis.
