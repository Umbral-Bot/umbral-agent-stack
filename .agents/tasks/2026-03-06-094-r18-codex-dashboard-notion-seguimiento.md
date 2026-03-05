# Task R18 — Actualizar dashboard de Notion con seguimiento R16/R17 (Codex)

**Fecha:** 2026-03-06  
**Ronda:** 18  
**Agente:** Codex  
**Branch:** `codex/094-dashboard-notion-seguimiento` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

Actualizar el **dashboard de Notion** (Dashboard Rick) con el estado de seguimiento actual: R16 y R17 cerradas, PRs #91–#96 mergeados, 900 tests. La página está en Notion; el Worker tiene el task `notion.update_dashboard` y el script `scripts/dashboard_report_vps.py` genera métricas para esa página. Documentación: `docs/22-notion-dashboard-gerencial.md`. Page ID: `NOTION_DASHBOARD_PAGE_ID` (env, ej. `0fd13978-b220-498e-9465-b4fb2efc5f4a`).

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b codex/094-dashboard-notion-seguimiento`.

2. **Revisar cómo se actualiza el dashboard:** Leer `docs/22-notion-dashboard-gerencial.md` y el código de `worker/tasks/notion.py` (handler `handle_notion_update_dashboard`) y `worker/notion_client.py` (`update_dashboard_page`). Revisar si existe `scripts/dashboard_report_vps.py` y qué métricas envía.

3. **Añadir o actualizar bloque de seguimiento:** Incluir en la actualización del dashboard (vía script o vía payload a `notion.update_dashboard`) una sección o métricas que reflejen:
   - **R16 cerrada** — PRs #85–#90 mergeados.
   - **R17 cerrada** — PRs #91 (bitacora-scripts), #92 (resumen+guía ramas), #93 (script borrado ramas), #94 (changelog README), #95 (runbook), #96 (9 funciones Notion) mergeados.
   - **Tests:** 900 passed.
   - **Última actualización:** fecha/hora del run.

   Si el formato actual del dashboard solo permite métricas clave-valor, añadir filas o bloques con "R16/R17" y el resumen; si el script ya construye bloques ricos, añadir ahí el bloque de seguimiento.

4. **Ejecución (opcional en tu entorno):** Si tienes `NOTION_API_KEY` y `NOTION_DASHBOARD_PAGE_ID` configurados, ejecutar el script o llamar al Worker para verificar que el dashboard se actualiza. Si no, documentar en el PR los pasos para que el maintainer lo ejecute en VPS o local.

5. **PR:** Abrir un único PR desde `codex/094-dashboard-notion-seguimiento` a main. Título: "feat(R18-094): dashboard Notion con seguimiento R16/R17". En la descripción indicar qué se añadió (métricas o bloques) y cómo ejecutar la actualización.

---

## Criterios de éxito

- [ ] Código o script que incluye el estado R16/R17 (y 900 tests) en la actualización del dashboard de Notion.
- [ ] Documentación en el PR de cómo correr la actualización (script o Worker).
- [ ] PR abierto a main. Sin romper la actualización existente del dashboard.

---

## Restricciones

- No cambiar la estructura general del dashboard ni eliminar métricas existentes; solo añadir el seguimiento R16/R17.
- Usar `NOTION_DASHBOARD_PAGE_ID` del entorno; no hardcodear el page_id en el repo.
