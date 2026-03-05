# Task R17 — Changelog / Estado R16 en README (GitHub Copilot)

**Fecha:** 2026-03-06  
**Ronda:** 17  
**Agente:** GitHub Copilot  
**Branch:** `copilot/092-changelog-r16` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

Añadir al README (o a un doc visible) una sección corta **"Changelog reciente"** o **"Estado R16"** que resuma en 2–4 líneas qué se recuperó y enlace a los docs clave: Bitácora scripts, browser automation, guía de ramas. Así quien abre el repo ve el estado actual sin ir al board.

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b copilot/092-changelog-r16`.

2. **Sección en README:** Añadir una subsección (p. ej. "Changelog reciente" o "Estado del proyecto — R16") con:
   - Una línea: recuperación R16 (rate limiter, scripts Bitácora, plan browser automation, inventarios).
   - Enlaces a: `docs/bitacora-scripts.md`, `docs/64-browser-automation-vm-plan.md`, `docs/r16-cierre-resumen.md`, `docs/guia-borrar-ramas-r16.md` (si existen en main).
   - Opcional: "Tests: 866 passed. Board: `.agents/board.md`."

3. **No duplicar:** Si ya existe una sección similar, ampliarla o actualizarla; no crear bloques repetidos.

4. **PR:** Abrir un único PR desde `copilot/092-changelog-r16` a main. Solo README (o un doc nuevo enlazado desde README).

---

## Criterios de éxito

- [ ] README con sección de changelog/estado R16 y enlaces a los 4 docs.
- [ ] PR abierto. Sin cambios a código de aplicación.

---

## Restricciones

- Solo documentación (README o docs/). No tocar worker, dispatcher ni CI.
