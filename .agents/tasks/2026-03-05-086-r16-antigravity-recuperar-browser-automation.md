# Task R16 — Recuperar plan browser automation + skill (Antigravity)

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Antigravity  
**Branch:** `antigravity/086-recuperar-browser-automation` ← **trabaja solo en esta rama**. Pull de main antes de crear la rama.

---

## Objetivo

Recuperar el **plan de browser automation en VM** y el **skill de OpenClaw** asociado que identificó el análisis (PR #87). Ese contenido está en ramas como `feat/browser-automation-vm-research` o similares. Traer docs y skill a main vía esta rama y abrir PR. Opcional: añadir lista de ramas recomendadas para borrar (según `docs/analisis-contenido-perdido-r16.md`).

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b antigravity/086-recuperar-browser-automation`.

2. **Localizar el contenido:** Revisar `docs/analisis-contenido-perdido-r16.md` y los inventarios para identificar la rama que contiene el plan de browser automation y el skill (p. ej. `feat/browser-automation-vm-research`). Listar archivos con `git diff main..origin/rama --name-only` y elegir solo docs (p. ej. `docs/64-browser-automation-vm-plan.md` o similar) y el skill en `openclaw/workspace-templates/skills/` o equivalente.

3. **Recuperar en tu rama:** Traer solo documentación y skill: copiar o cherry-pick los archivos de plan/docs y el SKILL.md (o carpeta del skill) de browser automation. No traer código de aplicación (Playwright/Selenium en worker) a menos que esté ya estable y documentado en esa rama; prioridad: docs + skill.

4. **Opcional — ramas a borrar:** Añadir en `docs/` un archivo corto (p. ej. `docs/ramas-recomendadas-borrar-r16.md`) con la lista de ramas que el análisis #87 marcó como vacías, obsoletas o destructivas, para que alguien pueda borrarlas más adelante. Una línea por rama + razón breve.

5. **PR:** Abrir un único PR desde `antigravity/086-recuperar-browser-automation` a `main` con título tipo "Recuperar plan browser automation + skill (R16-086)". En la descripción indicar de qué rama se recuperó y, si aplica, que se incluye la lista de ramas recomendadas para borrar.

---

## Criterios de éxito

- [ ] Rama `antigravity/086-recuperar-browser-automation` creada desde main actualizado.
- [ ] Plan/docs de browser automation y skill OpenClaw presentes en la rama.
- [ ] Opcional: doc con ramas recomendadas para borrar.
- [ ] PR abierto a main; sin cambios ajenos a browser automation + skill.

---

## Restricciones

- No tocar worker, dispatcher ni CI. Solo docs y skill. Si se incluye código de automatización (Playwright, etc.), debe ser el mínimo y estar documentado.
- Prioridad: recuperar lo que está perdido; la lista de ramas a borrar es secundaria.
