# Task R16 — Resumen de cierre y guía de limpieza de ramas (Antigravity)

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Antigravity  
**Branch:** `antigravity/089-resumen-limpieza` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

Cerrar documentalmente R16: un resumen ejecutivo de qué se recuperó y el estado final de main, y una guía clara para borrar las ramas listadas en `docs/ramas-recomendadas-borrar-r16.md` (sin ejecutar el borrado; solo documentar el proceso).

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b antigravity/089-resumen-limpieza`. (Si los PRs #85–#90 no están todos mergeados, basar el resumen en "tras mergear #85–#90".)

2. **Resumen de cierre:** Crear o actualizar `docs/r16-cierre-resumen.md` con:
   - **Qué se recuperó:** por cada PR (#85–#90), una línea: número, título breve, qué aporta a main (ej. "Inventario PRs cerrados", "Rate limiter por provider", "Scripts Bitácora", "Plan browser automation + skill", etc.).
   - **Estado final:** número de tests que pasan en main (ej. 865), CI (sí/no), enlace al board actualizado.
   - **Próximos pasos opcionales:** enlace a `docs/bitacora-scripts.md` para completar dependencias Notion; enlace a `docs/ramas-recomendadas-borrar-r16.md` para limpieza de ramas.

3. **Guía de borrado de ramas:** En `docs/ramas-recomendadas-borrar-r16.md` (o en un nuevo `docs/guia-borrar-ramas-r16.md`), añadir al inicio o al final una sección "Cómo borrar estas ramas": instrucciones para el maintainer (ej. revisar que la rama no tenga nada único no mergeado; luego `git push origin --delete nombre-rama` por cada una, o un listado de comandos). **No ejecutar** `git push origin --delete` tú mismo; solo dejar la guía para que el usuario lo haga cuando quiera.

4. **Board:** En `.agents/board.md`, en la sección R16, añadir que la tarea 089 (resumen y limpieza) está en curso o completada según corresponda, y la referencia a `docs/r16-cierre-resumen.md`.

5. **PR:** Abrir un único PR desde `antigravity/089-resumen-limpieza` a main. Solo docs; no código ni borrado real de ramas.

---

## Criterios de éxito

- [ ] `docs/r16-cierre-resumen.md` con resumen ejecutivo y estado final.
- [ ] Guía de borrado de ramas (en ramas-recomendadas-borrar o en guia-borrar-ramas-r16.md) sin ejecutar borrados.
- [ ] Board actualizado con 089 y enlace al resumen.
- [ ] PR abierto a main.

---

## Restricciones

- No borrar ramas remotas; solo documentar el proceso.
- No tocar worker, dispatcher ni CI; solo documentación y board.
