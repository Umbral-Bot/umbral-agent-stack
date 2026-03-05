# Task R16 — Cierre Bitácora: documentación y dependencias (GitHub Copilot)

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** GitHub Copilot  
**Branch:** `copilot/088-cierre-bitacora` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

Capitalizar el trabajo de los scripts de Bitácora (PR #89): documentar uso, env vars y las funciones faltantes en `notion_client.py` / `notion.py` para que alguien pueda completarlas o usarlas. Sin tocar worker/dispatcher; solo docs.

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b copilot/088-cierre-bitacora`. (Si PR #89 aún no está mergeado, crear la rama desde main actual; la doc hará referencia a los scripts que entrarán con #89.)

2. **Doc de scripts Bitácora:** Crear `docs/bitacora-scripts.md` (o equivalente) con:
   - Qué hace cada script: `enrich_bitacora_pages.py`, `add_resumen_amigable.py`.
   - Cómo ejecutarlos (comando, desde qué directorio).
   - Variables de entorno necesarias: `NOTION_API_KEY`, `NOTION_BITACORA_DB_ID` (y otras que aparezcan en los scripts).
   - Dependencias faltantes: listar las 6 funciones que faltan en `notion_client.py` y las 3 en `notion.py` (nombre, firma sugerida o descripción de qué deben hacer), para que un PR futuro pueda implementarlas. Puedes extraer esto de los scripts o de los tests recuperados en #89.

3. **README o CONTRIBUTING:** Añadir en README una línea que enlace a `docs/bitacora-scripts.md` (p. ej. "Scripts de enriquecimiento Bitácora: ver docs/bitacora-scripts.md"). O una línea en CONTRIBUTING si ya existe sección de docs.

4. **PR:** Abrir un único PR desde `copilot/088-cierre-bitacora` a main. Solo archivos de documentación; no código de aplicación.

---

## Criterios de éxito

- [ ] `docs/bitacora-scripts.md` con uso, env vars y lista de funciones faltantes.
- [ ] Enlace en README o CONTRIBUTING.
- [ ] PR abierto; sin cambios a worker, dispatcher ni CI.

---

## Restricciones

- No implementar las 6+3 funciones en este PR; solo documentarlas para un PR futuro.
- No tocar código de los scripts de Bitácora; solo documentar.
